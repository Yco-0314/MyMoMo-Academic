"""Statistical fidelity tests for runtime topology adapters.

Compares Python output to a committed NetLogo oracle fixture
(`tests/fixtures/netlogo/output/`). Tests skip cleanly when the oracle
isn't reachable (e.g. on a fresh dev box without NetLogo installed) but
the fixture files are committed so the comparison is reproducible
without re-running NetLogo.

To regenerate fixtures:
    JAVA_HOME=/opt/homebrew/opt/openjdk@17 \
      /path/to/NetLogo/netlogo-headless.sh \
      --model tests/fixtures/netlogo/Virus_on_a_Network.nlogo \
      --experiment oracle_network_topology \
      --table tests/fixtures/netlogo/output/network_topology.csv
"""
from __future__ import annotations

import csv
import random
import statistics
from pathlib import Path

import pytest
from scipy.stats import ks_2samp

from abm_auto.runtime import topologies
from abm_auto.verification.netlogo_oracle import parse_table

REPO = Path(__file__).parent.parent
FIXTURE_DIR = REPO / "tests" / "fixtures" / "netlogo" / "output"
TOPOLOGY_FIXTURE = FIXTURE_DIR / "network_topology.csv"
TRAJECTORY_FIXTURE = FIXTURE_DIR / "sir_trajectories.csv"


def _python_topology_stats(n_seeds: int = 30, avg_degree: int = 6, n_nodes: int = 150) -> list[dict]:
    """Generate n_seeds graphs from netlogo_spatially_clustered, return per-run stats."""
    build = topologies.netlogo_spatially_clustered(avg_degree=avg_degree)
    rows = []
    for seed in range(n_seeds):
        G = build(n_nodes, random.Random(seed))
        deg = [d for _, d in G.degree()]
        rows.append({
            "mean":  statistics.mean(deg),
            "max":   max(deg),
            "min":   min(deg),
            "std":   statistics.stdev(deg),
            "edges": G.number_of_edges(),
        })
    return rows


def _netlogo_topology_stats() -> list[dict]:
    """Parse the committed NetLogo fixture into per-run stats dicts."""
    with open(TOPOLOGY_FIXTURE) as f:
        lines = f.readlines()
    header_idx = next(i for i, l in enumerate(lines) if l.startswith('"[run number]"'))
    reader = csv.DictReader(lines[header_idx:])
    return [
        {
            "mean":  float(row["mean [count link-neighbors] of turtles"]),
            "max":   float(row["max [count link-neighbors] of turtles"]),
            "min":   float(row["min [count link-neighbors] of turtles"]),
            "std":   float(row["standard-deviation [count link-neighbors] of turtles"]),
            "edges": float(row["count links"]),
        }
        for row in reader
    ]


@pytest.mark.skipif(
    not TOPOLOGY_FIXTURE.exists(),
    reason="NetLogo topology fixture missing — see module docstring to regenerate",
)
def test_netlogo_spatially_clustered_matches_oracle_topology():
    """KS test on per-run degree summary stats. p > 0.05 on all comparable metrics."""
    nl = _netlogo_topology_stats()
    py = _python_topology_stats(n_seeds=len(nl))

    # Edges and mean degree are deterministic (n * d / 2 and d exactly)
    assert all(r["edges"] == 450 for r in nl)
    assert all(r["edges"] == 450 for r in py)
    assert all(r["mean"] == 6.0 for r in nl)
    assert all(r["mean"] == 6.0 for r in py)

    # std and max are stochastic — require KS-consistent distributions
    for key in ("std", "max"):
        ks_stat, ks_p = ks_2samp([r[key] for r in nl], [r[key] for r in py])
        assert ks_p > 0.05, (
            f"Python {key} distribution differs significantly from NetLogo "
            f"(KS={ks_stat:.3f}, p={ks_p:.3f}); netlogo_spatially_clustered "
            f"may have drifted from the NetLogo reference algorithm."
        )


@pytest.mark.skipif(
    not TRAJECTORY_FIXTURE.exists(),
    reason="NetLogo trajectory fixture missing — see module docstring to regenerate",
)
def test_netlogo_virus_sim_final_R_matches_oracle():
    """Per-run final-R values are KS-consistent between NetLogo and our handcrafted sim.

    NB: this test depends on tools/scripts/regen_sir_trajectories.py (or equivalent)
    having produced the Python trajectory fixture. If only the NetLogo fixture is
    present, we skip without failing — the network-topology test above is the
    primary fidelity gate.
    """
    py_traj_fixture = FIXTURE_DIR / "python_sir_trajectories.csv"
    if not py_traj_fixture.exists():
        pytest.skip(
            "Python SIR trajectory fixture missing — regenerate to enable this test"
        )

    nl_df = parse_table(TRAJECTORY_FIXTURE)
    nl_finals = nl_df[nl_df["[step]"] == nl_df["[step]"].max()][
        "count turtles with [resistant?]"
    ].values

    import pandas as pd
    py_df = pd.read_csv(py_traj_fixture)
    py_finals = py_df[py_df["tick"] == py_df["tick"].max()]["R"].values

    ks_stat, ks_p = ks_2samp(nl_finals, py_finals)
    assert ks_p > 0.05, (
        f"Python sim final-R distribution differs significantly from NetLogo "
        f"(KS={ks_stat:.3f}, p={ks_p:.3f}). Documented difference: Python's "
        f"`random.random() < recovery_chance/100` is exact, NetLogo's "
        f"`random 100 < recovery-chance` rounds up at non-integer thresholds; "
        f"that 12-17% effective rate gap shifts the epidemic timing."
    )
