"""Faithful-rule + determinism tests for the Deffuant (2000) bounded-confidence
reproduction.

These pin the elementary interaction (move toward each other by mu*diff when within
eps; no change otherwise), the cluster-counting rule, the ⌊1/(2eps)⌋ helper, a tiny
hand-verifiable convergence, and determinism (same seed -> identical result). They are
faithfulness tests, NOT prediction tests (the predictions P1-P3 are evaluated by
examples/repro_deffuant_bounded_confidence/run.py).
"""
from __future__ import annotations

from abm_auto.classics.deffuant import (
    DeffuantModel,
    cluster_centers,
    cluster_sizes,
    count_clusters,
    major_cluster_count,
    predicted_clusters,
    run_single,
)


def _two_agent_model(xa: float, xb: float, *, eps: float, mu: float) -> DeffuantModel:
    """A 2-agent model with the two opinions set by hand (bypasses the RNG init)."""
    m = DeffuantModel(2, eps=eps, mu=mu, seed=0)
    m.agent_list[0].x = xa
    m.agent_list[1].x = xb
    return m


def test_interaction_moves_pair_together_when_within_eps():
    # |0.5 - 0.3| = 0.2 < eps=0.3 -> they meet in the middle for mu=0.5.
    m = _two_agent_model(0.5, 0.3, eps=0.3, mu=0.5)
    a, b = m.agent_list
    move = m.interact(a, b)
    assert a.x == 0.4 and b.x == 0.4          # both at the midpoint
    assert abs(move - 0.1) < 1e-12            # |mu * diff| = 0.5 * 0.2 = 0.1


def test_interaction_partial_step_for_small_mu():
    # mu=0.1: a moves 10% of the way toward b, b 10% toward a.
    m = _two_agent_model(0.2, 0.6, eps=0.5, mu=0.1)
    a, b = m.agent_list
    move = m.interact(a, b)
    # diff = +0.4 (b - a); delta = 0.1*0.4 = 0.04. a += delta, b -= delta.
    assert abs(a.x - 0.24) < 1e-12
    assert abs(b.x - 0.56) < 1e-12
    assert abs(move - 0.04) < 1e-12


def test_interaction_no_change_outside_eps():
    # |0.9 - 0.2| = 0.7 >= eps=0.3 -> no influence, opinions untouched.
    m = _two_agent_model(0.2, 0.9, eps=0.3, mu=0.5)
    a, b = m.agent_list
    move = m.interact(a, b)
    assert a.x == 0.2 and b.x == 0.9
    assert move == 0.0


def test_interaction_at_exact_eps_boundary_is_no_change():
    # |diff| == eps is NOT < eps -> no change (strict bounded confidence).
    m = _two_agent_model(0.1, 0.4, eps=0.3, mu=0.5)
    a, b = m.agent_list
    move = m.interact(a, b)
    assert a.x == 0.1 and b.x == 0.4
    assert move == 0.0


def test_two_close_agents_converge_to_consensus():
    # Two agents WITHIN eps (set by hand) must converge to a single cluster at the
    # mean of their initial opinions (mu=0.5 -> they meet in the middle in one step).
    m = _two_agent_model(0.30, 0.50, eps=0.5, mu=0.5)
    res = m.run()
    assert res["n_clusters"] == 1
    assert res["converged"] is True
    assert abs(res["cluster_centers"][0] - 0.40) < 1e-9   # mean(0.30, 0.50)


def test_two_distant_agents_stay_two_clusters():
    # Build a population that is two tight, far-apart groups; with small eps they
    # never interact across the gap -> two clusters, and converge immediately.
    m = DeffuantModel(4, eps=0.1, mu=0.5, seed=0)
    for agent, x in zip(m.agent_list, [0.10, 0.11, 0.90, 0.91]):
        agent.x = x
    res = m.run()
    assert res["n_clusters"] == 2


def test_count_clusters_groups_within_tolerance():
    # Three tight groups separated by gaps > tol=0.01.
    xs = [0.100, 0.101, 0.500, 0.5005, 0.900]
    assert count_clusters(xs, tol=0.01) == 3
    # One group when everything is within tol.
    assert count_clusters([0.30, 0.301, 0.302], tol=0.01) == 1
    assert count_clusters([], tol=0.01) == 0
    assert count_clusters([0.5], tol=0.01) == 1


def test_cluster_sizes_and_major_count():
    # One big cluster (3 agents) + two strays, gaps > tol.
    xs = [0.100, 0.101, 0.102, 0.500, 0.900]
    assert cluster_sizes(xs, tol=0.01) == [3, 1, 1]
    # Total = 3 clusters; major (>= 2 agents) = 1 (only the size-3 group).
    assert count_clusters(xs, tol=0.01) == 3
    assert major_cluster_count(xs, tol=0.01, min_size=2) == 1
    # With min_size=1 every cluster is "major".
    assert major_cluster_count(xs, tol=0.01, min_size=1) == 3
    assert cluster_sizes([], tol=0.01) == []


def test_run_reports_total_and_major_clusters():
    # Two tight groups (within eps, will fully merge) + two far-apart strays. After
    # convergence: two size-3 major clusters and two size-1 minor strays.
    m = DeffuantModel(8, eps=0.05, mu=0.5, seed=0, major_min_size=2)
    for agent, x in zip(m.agent_list,
                        [0.100, 0.101, 0.102, 0.500, 0.501, 0.502, 0.900, 0.300]):
        agent.x = x
    res = m.run()
    # 0.30 and 0.90 are isolated strays (size 1); the two triples merge to a point.
    assert res["n_clusters"] == 4
    assert res["n_major_clusters"] == 2
    assert res["cluster_sizes"] == [3, 3, 1, 1]


def test_cluster_centers_are_group_means():
    xs = [0.10, 0.12, 0.80]
    centers = cluster_centers(xs, tol=0.05)
    assert len(centers) == 2
    assert abs(centers[0] - 0.11) < 1e-12   # mean(0.10, 0.12)
    assert abs(centers[1] - 0.80) < 1e-12


def test_predicted_clusters_law():
    # ⌊1/(2eps)⌋
    assert predicted_clusters(0.1) == 5      # floor(5.0)
    assert predicted_clusters(0.15) == 3     # floor(3.33)
    assert predicted_clusters(0.2) == 2      # floor(2.5)
    assert predicted_clusters(0.3) == 1      # floor(1.66)
    assert predicted_clusters(0.5) == 1      # floor(1.0)


def test_determinism_same_seed_identical_result():
    a = run_single(200, eps=0.2, mu=0.5, seed=42)
    b = run_single(200, eps=0.2, mu=0.5, seed=42)
    assert a["n_clusters"] == b["n_clusters"]
    assert a["final_opinions"] == b["final_opinions"]
    assert a["sweeps"] == b["sweeps"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(200, eps=0.2, mu=0.5, seed=1)
    b = run_single(200, eps=0.2, mu=0.5, seed=2)
    # Both are valid runs in [0,1] with a sane cluster count.
    for res in (a, b):
        assert all(0.0 <= x <= 1.0 for x in res["final_opinions"])
        assert 1 <= res["n_clusters"] <= 200


def test_initial_opinions_are_uniform_in_unit_interval():
    m = DeffuantModel(500, eps=0.2, mu=0.5, seed=7)
    xs = m.opinions()
    assert len(xs) == 500
    assert all(0.0 <= x < 1.0 for x in xs)
    assert 0.4 < sum(xs) / len(xs) < 0.6     # mean near 0.5 for Uniform[0,1]


def test_mu_changes_speed_not_cluster_count_at_fixed_eps():
    # Deffuant's claim is that mu sets convergence SPEED, not the #clusters. At fixed
    # eps the slower mu must take more sweeps; the cluster count is the SAME up to the
    # cross-seed variance of this stochastic model (here: within 1 at a single seed,
    # exactly equal in the run.py mean-over-seeds evaluation of P3).
    fast = run_single(300, eps=0.2, mu=0.5, seed=3)
    slow = run_single(300, eps=0.2, mu=0.1, seed=3)
    assert abs(fast["n_clusters"] - slow["n_clusters"]) <= 1
    # mu=0.1 should take strictly more sweeps than mu=0.5 (slower convergence).
    assert slow["sweeps"] > fast["sweeps"]
