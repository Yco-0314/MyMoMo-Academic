"""Faithful-rule + determinism tests for the Hegselmann–Krause (2002)
bounded-confidence reproduction.

These pin the defining HK behaviour — SYNCHRONOUS update where every agent
simultaneously averages its confidence set (all opinions within ``eps``, inclusive,
INCLUDING itself) from one shared snapshot — plus the inclusive boundary, the
cluster-counting rule, a couple of hand-verifiable convergences, and determinism
(same seed -> identical result). They are faithfulness tests, NOT prediction tests
(the predictions P1-P3 are evaluated by examples/repro_hegselmann_krause/run.py).
"""
from __future__ import annotations

from abm_auto.classics.hegselmann_krause import (
    HegselmannKrauseModel,
    _confidence_mean,
    cluster_centers,
    cluster_sizes,
    count_clusters,
    run_single,
)


def _model_with(opinions, *, eps: float) -> HegselmannKrauseModel:
    """A model whose opinions are set by hand (bypasses the RNG init)."""
    m = HegselmannKrauseModel(len(opinions), eps=eps, seed=0)
    for agent, x in zip(m.agent_list, opinions):
        agent.x = x
    return m


# -- the elementary HK update -------------------------------------------------

def test_confidence_mean_includes_self_and_within_eps():
    # xi=0.50, snapshot has 0.45, 0.50, 0.55 within eps=0.06 and 0.70 out (eps=0.06
    # avoids the float boundary at 0.05 where |0.55-0.50| rounds just over 0.05).
    snap = [0.45, 0.50, 0.55, 0.70]
    # mean(0.45, 0.50, 0.55) = 0.50 (0.70 is |0.70-0.50|=0.20 > 0.06, excluded).
    assert abs(_confidence_mean(0.50, snap, 0.06) - 0.50) < 1e-12


def test_confidence_mean_boundary_is_inclusive():
    # |xi - xj| == eps is INCLUDED (HK closed confidence interval), unlike Deffuant.
    snap = [0.20, 0.30]      # |0.20 - 0.30| = 0.10 == eps
    # both included -> mean(0.20, 0.30) = 0.25.
    assert abs(_confidence_mean(0.20, snap, 0.10) - 0.25) < 1e-12
    # just over the bound -> only self.
    assert abs(_confidence_mean(0.20, snap, 0.0999) - 0.20) < 1e-12


def test_confidence_mean_isolated_agent_keeps_own_opinion():
    # No neighbour within eps -> the agent averages only itself -> unchanged.
    snap = [0.10, 0.90]
    assert _confidence_mean(0.10, snap, 0.05) == 0.10


def test_synchronous_update_uses_shared_snapshot_not_sequential():
    # Three agents: 0.0, 0.1, 0.2 with eps=0.1 (inclusive).
    # Agent 0 sees {0.0, 0.1}      -> 0.05
    # Agent 1 sees {0.0, 0.1, 0.2} -> 0.10
    # Agent 2 sees {0.1, 0.2}      -> 0.15
    # All computed from the SAME pre-step snapshot, then committed together.
    m = _model_with([0.0, 0.1, 0.2], eps=0.1)
    m.step()
    xs = m.opinions()
    assert abs(xs[0] - 0.05) < 1e-12
    assert abs(xs[1] - 0.10) < 1e-12
    assert abs(xs[2] - 0.15) < 1e-12


def test_close_population_converges_to_single_consensus():
    # All within eps of each other along a chain that connects -> one cluster at the
    # global mean (HK contracts a connected confidence chain to consensus).
    m = _model_with([0.10, 0.20, 0.30, 0.40, 0.50], eps=0.2)
    res = m.run()
    assert res["n_clusters"] == 1
    assert res["is_consensus"] is True
    assert res["converged"] is True
    assert abs(res["cluster_centers"][0] - 0.30) < 1e-9   # mean of the five


def test_two_far_groups_stay_two_clusters():
    # Two tight groups far apart; with small eps no one bridges the gap -> 2 clusters.
    m = _model_with([0.10, 0.11, 0.12, 0.88, 0.89, 0.90], eps=0.05)
    res = m.run()
    assert res["n_clusters"] == 2


def test_isolated_population_stays_put():
    # Every agent is more than eps from every other -> all confidence sets are
    # singletons -> nothing moves, stationary immediately, N clusters.
    m = _model_with([0.0, 0.5, 1.0], eps=0.1)
    res = m.run()
    assert res["n_clusters"] == 3
    assert res["sweeps"] == 1            # one sweep registers max_move 0 -> stop


# -- cluster helpers ----------------------------------------------------------

def test_count_clusters_groups_within_tolerance():
    xs = [0.100, 0.101, 0.500, 0.5005, 0.900]
    assert count_clusters(xs, tol=0.01) == 3
    assert count_clusters([0.30, 0.301, 0.302], tol=0.01) == 1
    assert count_clusters([], tol=0.01) == 0
    assert count_clusters([0.5], tol=0.01) == 1


def test_cluster_sizes_and_centers():
    xs = [0.100, 0.101, 0.102, 0.500, 0.900]
    assert cluster_sizes(xs, tol=0.01) == [3, 1, 1]
    centers = cluster_centers([0.10, 0.12, 0.80], tol=0.05)
    assert len(centers) == 2
    assert abs(centers[0] - 0.11) < 1e-12
    assert abs(centers[1] - 0.80) < 1e-12


# -- distribution + determinism ----------------------------------------------

def test_initial_opinions_are_uniform_in_unit_interval():
    m = HegselmannKrauseModel(500, eps=0.2, seed=7)
    xs = m.opinions()
    assert len(xs) == 500
    assert all(0.0 <= x < 1.0 for x in xs)
    assert 0.4 < sum(xs) / len(xs) < 0.6     # mean near 0.5 for Uniform[0,1]


def test_determinism_same_seed_identical_result():
    a = run_single(200, eps=0.15, seed=42)
    b = run_single(200, eps=0.15, seed=42)
    assert a["n_clusters"] == b["n_clusters"]
    assert a["final_opinions"] == b["final_opinions"]
    assert a["sweeps"] == b["sweeps"]


def test_high_eps_drives_consensus_low_eps_fragments():
    # Faithfulness of the qualitative HK claim at a single seed (the run.py grades it
    # over >=20 seeds): a large confidence bound merges the population to consensus;
    # a tiny one leaves multiple clusters.
    big = run_single(200, eps=0.3, seed=1)
    small = run_single(200, eps=0.05, seed=1)
    assert big["n_clusters"] == 1
    assert small["n_clusters"] >= 2


def test_run_reaches_stationary_state():
    res = run_single(200, eps=0.2, seed=3)
    assert res["converged"] is True
    assert all(0.0 <= x <= 1.0 for x in res["final_opinions"])
