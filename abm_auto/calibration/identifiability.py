"""Identifiability diagnostics — detect multimodal posteriors.

After main NM refinement lands on one local minimum, this module
runs K=5 random restarts of NM from different priors and clusters
the terminal points. Multiple distinct clusters → the calibration
problem is NOT identifiable from the observation: many different
parameter combinations fit equally well.

Why this matters
----------------
Today's dogfood reported:
  recovery_chance: 4.269 vs truth 2.5 (71% err — at prior upper)
  gain_resistance: 13.697 vs truth 25  (45% err)

These large errors look like calibration failure but are actually
identifiability: the LLM-written environment.py has a μ×α (recovery ×
resistance) coupling, where many (μ, α) pairs produce the same
trajectory. Calibrator silently picks ONE point on the ridge; the
user can't tell from `best_params` whether it's an isolated peak or
one of many equally-good fits.

Without this signal, users see "calibration found best_params" and
trust them as point estimates. WITH this signal, users get
"warning: 3 distinct optima clusters detected — parameters NOT
individually identifiable; trajectories nearly identical across
basins" and can decide to report posterior ranges instead of points.

This addresses ADR-006 Open Question #3.

How it works
------------
1. K = 5 random starts sampled from priors (separate from screening's
   N=100 — these are extra cost beyond the main fit).
2. NM refine from each start, max_evals=20 (tighter than main since
   we only need basin identification, not pinpoint).
3. Cluster terminal points by parameter-space distance (simple
   single-linkage with a relative threshold).
4. If >1 cluster, emit warning + render markdown report listing each
   basin (params + objective value).

Run after main NM refinement; never before — it's diagnostic, not
optimization.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from abm_auto.calibration.refiners import nelder_mead_refine
from abm_auto.calibration.summary_stats import SummaryStats, full_trajectory
from abm_auto.calibration.types import CalibrationResult


# Default cluster threshold: two points in same cluster if every param
# differs by < 15% of that param's prior range. Conservative — would
# rather over-merge than over-split.
DEFAULT_CLUSTER_REL_THRESHOLD = 0.15

# Default restart count. K=5 gives 99% chance of revisiting any basin
# with prior mass > 20% (assuming uniform prior covers all basins).
DEFAULT_N_RESTARTS = 5

# Per-restart NM eval budget. Tighter than main refinement (we want
# basin location, not pinpoint).
DEFAULT_EVALS_PER_RESTART = 20


@dataclass
class Basin:
    """One local minimum found by an NM restart."""
    params: dict[str, float]
    objective: float   # ||sim - obs|| at this point
    restart_idx: int


@dataclass
class IdentifiabilityReport:
    """Output of identify_basins."""
    n_restarts: int
    n_basins: int
    basins: list[Basin]
    cluster_assignment: list[int]   # which cluster each restart landed in
    is_multimodal: bool
    warning: str = ""

    def to_markdown(self) -> str:
        """Render as a markdown section for the calibration report."""
        lines = ["## Identifiability diagnostic", ""]
        lines.append(f"- Restarts run: **{self.n_restarts}**")
        lines.append(f"- Distinct basins found: **{self.n_basins}**")
        lines.append("")
        if self.warning:
            lines.append(f"> **⚠ {self.warning}**")
            lines.append("")
        # Table of basins, sorted by objective
        lines.append("### Basins (sorted by fit quality)")
        lines.append("")
        sorted_basins = sorted(self.basins, key=lambda b: b.objective)
        if sorted_basins:
            param_names = list(sorted_basins[0].params.keys())
            header = "| Rank | objective | " + " | ".join(param_names) + " |"
            sep = "|" + "|".join("---" for _ in range(len(param_names) + 2)) + "|"
            lines.append(header)
            lines.append(sep)
            for i, b in enumerate(sorted_basins, start=1):
                row = (
                    f"| {i} | {b.objective:.2f} | "
                    + " | ".join(f"{b.params[n]:.4f}" for n in param_names)
                    + " |"
                )
                lines.append(row)
        return "\n".join(lines) + "\n"


def identify_basins(
    simulator,
    priors: dict[str, dict],
    targets: list[str],
    obs_stats: np.ndarray,
    n_restarts: int = DEFAULT_N_RESTARTS,
    evals_per_restart: int = DEFAULT_EVALS_PER_RESTART,
    cluster_rel_threshold: float = DEFAULT_CLUSTER_REL_THRESHOLD,
    rng: Optional[np.random.Generator] = None,
    summary_fn: SummaryStats = full_trajectory,
) -> IdentifiabilityReport:
    """K random restarts of NM + cluster terminal points to detect multimodality.

    Args:
        simulator: same SimulatorWrapper-like used by `fit()`
        priors: same {name: {min, max}} mapping
        targets: column names to score against
        obs_stats: pre-computed observed summary vector
        n_restarts: K — number of random starts (default 5)
        evals_per_restart: per-NM eval budget (default 20, tighter than main)
        cluster_rel_threshold: two basins merge if every param differs by
            less than this fraction of the param's prior range
        rng: numpy Generator for restart sampling; None uses default
        summary_fn: should match what main calibration used

    Returns:
        IdentifiabilityReport with basin list + multimodality verdict.
    """
    if rng is None:
        rng = np.random.default_rng()

    param_names = list(priors.keys())

    # Sample K starts uniformly from priors
    basins: list[Basin] = []
    for k in range(n_restarts):
        start = {
            n: float(rng.uniform(priors[n]["min"], priors[n]["max"]))
            for n in param_names
        }
        result = nelder_mead_refine(
            start_params=start,
            priors=priors,
            targets=targets,
            obs_stats=obs_stats,
            simulator=simulator,
            max_evals=evals_per_restart,
        )
        if not result.ok:
            continue
        # Compute objective at terminal point
        sim_stats = simulator.simulate(result.best_params, targets)
        if sim_stats is None:
            continue
        objective = float(np.linalg.norm(sim_stats - obs_stats))
        basins.append(Basin(
            params=result.best_params,
            objective=objective,
            restart_idx=k,
        ))

    if not basins:
        return IdentifiabilityReport(
            n_restarts=n_restarts,
            n_basins=0,
            basins=[],
            cluster_assignment=[],
            is_multimodal=False,
            warning="All NM restarts failed — could not assess identifiability.",
        )

    # Cluster by param-space distance: single-linkage with relative threshold
    clusters = _single_link_cluster(basins, priors, cluster_rel_threshold)
    n_clusters = len(set(clusters))

    is_multimodal = n_clusters > 1
    warning = ""
    if is_multimodal:
        warning = (
            f"Posterior appears MULTIMODAL — {n_clusters} distinct basins found "
            f"across {len(basins)} successful restarts. Parameters are NOT "
            f"individually identifiable from this observation; many parameter "
            f"combinations fit equally well. Treat `best_params` as ONE point "
            f"on a ridge, not THE estimate. Consider reporting posterior "
            f"distribution ranges instead of point values."
        )

    return IdentifiabilityReport(
        n_restarts=n_restarts,
        n_basins=n_clusters,
        basins=basins,
        cluster_assignment=clusters,
        is_multimodal=is_multimodal,
        warning=warning,
    )


def _single_link_cluster(
    basins: list[Basin],
    priors: dict[str, dict],
    rel_threshold: float,
) -> list[int]:
    """Assign each basin a cluster id via single-link agglomerative clustering.

    Two basins go in the same cluster if their params differ by less than
    `rel_threshold * prior_range` for EVERY parameter. Single-link, so
    chains of close-but-not-identical basins merge transitively.

    Returns a list where index = basin position, value = cluster id (0-indexed).
    """
    param_names = list(priors.keys())
    ranges = {n: priors[n]["max"] - priors[n]["min"] for n in param_names}

    def _close(a: Basin, b: Basin) -> bool:
        for n in param_names:
            rng_n = ranges[n] or 1.0
            if abs(a.params[n] - b.params[n]) / rng_n >= rel_threshold:
                return False
        return True

    # Union-find
    parent = list(range(len(basins)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(len(basins)):
        for j in range(i + 1, len(basins)):
            if _close(basins[i], basins[j]):
                union(i, j)

    # Re-label cluster roots as 0..K-1
    roots = sorted({find(i) for i in range(len(basins))})
    root_to_id = {r: i for i, r in enumerate(roots)}
    return [root_to_id[find(i)] for i in range(len(basins))]


__all__ = [
    "Basin",
    "IdentifiabilityReport",
    "identify_basins",
    "DEFAULT_N_RESTARTS",
    "DEFAULT_EVALS_PER_RESTART",
    "DEFAULT_CLUSTER_REL_THRESHOLD",
]
