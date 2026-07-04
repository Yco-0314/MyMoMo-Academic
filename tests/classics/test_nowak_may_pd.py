"""Faithful-rule + determinism tests for the Nowak & May (1992) spatial PD.

These pin the payoff matrix (T=b, R=1, P=0, S=0), the self-interaction convention,
the Moore-8 periodic neighbourhood, the synchronous best-response update, a
hand-verifiable single-defector invasion, and determinism (same seed -> identical
result). They are faithfulness tests, NOT prediction tests (P1-P3 are evaluated by
examples/repro_nowak_may_pd/run.py).
"""
from __future__ import annotations

from abm_auto.classics.nowak_may_pd import (
    COOPERATE,
    DEFECT,
    NowakMayModel,
    WellMixedPDModel,
    run_spatial_seeds,
    run_wellmixed_seeds,
    steady_state_fraction,
)


def _all_strategy(model, strat):
    for a in model.agent_by_id.values():
        a.strategy = strat
        a._next_strategy = strat


def test_moore_neighborhood_is_8_with_periodic_wrap():
    m = NowakMayModel(5, 5, b=1.85, seed=0)
    # interior site (2,2) -> id 12: 8 neighbours, none wrapping.
    assert len(m.neighbors[12]) == 8
    # corner site (0,0) -> id 0: still 8 neighbours thanks to the torus.
    assert len(m.neighbors[0]) == 8
    # corner (0,0) wraps to the opposite corner (4,4)=id 24 and edges.
    assert 24 in m.neighbors[0]   # (-1,-1) wraps to (4,4)
    assert 4 in m.neighbors[0]    # (-1, 0) wraps along x to (4,0)? -> id 4
    assert 20 in m.neighbors[0]   # ( 0,-1) wraps along y to (0,4) -> id 20


def test_payoff_all_cooperators_with_self_interaction():
    # All-C lattice: a cooperator plays 8 C neighbours + itself = 9 partners, each R=1.
    m = NowakMayModel(5, 5, b=1.85, self_interaction=True, seed=0)
    _all_strategy(m, COOPERATE)
    a = m.agent_by_id[12]
    assert a.compute_payoff() == 9.0  # 8 neighbours + self, all R=1


def test_payoff_all_cooperators_without_self_interaction():
    m = NowakMayModel(5, 5, b=1.85, self_interaction=False, seed=0)
    _all_strategy(m, COOPERATE)
    a = m.agent_by_id[12]
    assert a.compute_payoff() == 8.0  # 8 neighbours only, no self


def test_defector_payoff_in_sea_of_cooperators():
    # A lone defector in an all-C lattice scores T=b per cooperating neighbour (8),
    # and the self-game adds P=0 (defector vs itself). With b=1.85 -> 8*1.85 = 14.8.
    m = NowakMayModel(5, 5, b=1.85, self_interaction=True, seed=0)
    _all_strategy(m, COOPERATE)
    d = m.agent_by_id[12]
    d.strategy = DEFECT
    assert abs(d.compute_payoff() - 8 * 1.85) < 1e-12  # 14.8
    # An ADJACENT cooperator now has 7 C neighbours + 1 D neighbour + self(C):
    # 7*R + 0(S vs the defector) + 1*R(self) = 8.
    c = m.agent_by_id[11]  # left neighbour of site 12
    assert c.strategy == COOPERATE
    assert c.compute_payoff() == 8.0  # 7 C-neighbours + self, the D-neighbour gives S=0


def test_defector_payoff_matrix_values():
    # Both-defect gives P=0; cooperate-vs-defect gives S=0. Build a 2-strategy check.
    m = NowakMayModel(5, 5, b=2.0, self_interaction=False, seed=0)
    _all_strategy(m, DEFECT)
    d = m.agent_by_id[12]
    assert d.compute_payoff() == 0.0  # all-D: every game is P=0
    c = m.agent_by_id[12]
    c.strategy = COOPERATE
    assert c.compute_payoff() == 0.0  # C surrounded by D: every game is S=0


def test_single_defector_invades_neighbourhood_one_tick():
    # Canonical local move: a lone D in an all-C sea with self-interaction and b>1.
    # The defector scores 8b; each of its 8 cooperating neighbours scores 8 (7 C
    # neighbours + self). Since 8b > 8 for b>1, on the synchronous update every
    # neighbour of the defector (whose local best is the defector) turns D, and the
    # defector itself stays D. So one D becomes a 3x3 block of 9 D's.
    m = NowakMayModel(7, 7, b=1.85, self_interaction=True, seed=0)
    _all_strategy(m, COOPERATE)
    center = 3 * 7 + 3  # site (3,3)
    m.agent_by_id[center].strategy = DEFECT
    m.step()
    defectors = {i for i, a in m.agent_by_id.items() if a.strategy == DEFECT}
    expected = {m_id for m_id in m.neighbors[center]} | {center}
    assert defectors == expected
    assert len(defectors) == 9  # the 3x3 block


def test_synchronous_update_is_order_independent():
    # Two runs with different scheduler orders must give the same lattice, because
    # payoffs are read from a frozen snapshot and strategies commit all at once.
    m1 = NowakMayModel(11, 11, b=1.85, seed=7)
    m2 = NowakMayModel(11, 11, b=1.85, seed=7)
    m1.agents.schedule = "sequential"
    m2.agents.schedule = "random_order"
    for _ in range(10):
        m1.step()
        m2.step()
    s1 = [m1.agent_by_id[i].strategy for i in range(m1.n)]
    s2 = [m2.agent_by_id[i].strategy for i in range(m2.n)]
    assert s1 == s2


def test_imitation_copies_highest_scoring_neighbour():
    # Construct a tiny configuration where one neighbour clearly out-scores self.
    m = NowakMayModel(5, 5, b=1.85, self_interaction=True, seed=0)
    _all_strategy(m, COOPERATE)
    # Make site 12 a defector so an adjacent C sees a high-scoring D neighbour.
    m.agent_by_id[12].strategy = DEFECT
    for a in m.agent_by_id.values():
        a.payoff = a.compute_payoff()
    neighbour = m.agent_by_id[11]  # a cooperator adjacent to the defector
    neighbour.choose_next_strategy()
    # Defector payoff 8b=14.8 beats any cooperator's <=9, so the neighbour copies D.
    assert neighbour._next_strategy == DEFECT


def test_determinism_same_seed_identical_series():
    r1 = NowakMayModel(31, 31, b=1.85, seed=3).run(40)
    r2 = NowakMayModel(31, 31, b=1.85, seed=3).run(40)
    assert r1["coop_series"] == r2["coop_series"]
    assert r1["final_coop_fraction"] == r2["final_coop_fraction"]


def test_different_seed_changes_initial_placement():
    a = NowakMayModel(31, 31, b=1.85, seed=1).run(0)
    b = NowakMayModel(31, 31, b=1.85, seed=2).run(0)
    # t=0 baselines differ because the random C/D placement differs.
    assert a["coop_series"][0] != b["coop_series"][0]


def test_init_density_controls_baseline_fraction():
    # Large lattice -> initial cooperator fraction ~ init_coop_fraction.
    m = NowakMayModel(99, 99, b=1.85, init_coop_fraction=0.9, seed=0)
    assert abs(m.cooperator_fraction() - 0.9) < 0.02
    m2 = NowakMayModel(99, 99, b=1.85, init_coop_fraction=0.1, seed=0)
    assert abs(m2.cooperator_fraction() - 0.1) < 0.02


def test_wellmixed_redraws_neighbours_each_tick():
    m = WellMixedPDModel(200, b=1.85, k=8, seed=0)
    before = dict(m.neighbors)
    m._redraw_neighbors()
    after = m.neighbors
    # Each agent has exactly k distinct partners, none equal to itself.
    for site, nbrs in after.items():
        assert len(nbrs) == 8
        assert site not in nbrs
        assert len(set(nbrs)) == 8
    # The draw actually changed (overwhelmingly likely with 200 agents).
    assert any(before[s] != after[s] for s in before)


def test_wellmixed_determinism_same_seed():
    r1 = WellMixedPDModel(500, b=1.85, seed=5).run(20)
    r2 = WellMixedPDModel(500, b=1.85, seed=5).run(20)
    assert r1["coop_series"] == r2["coop_series"]


def test_steady_state_fraction_averages_tail():
    series = [0.0] * 10 + [0.3, 0.3, 0.3, 0.3]
    assert abs(steady_state_fraction(series, last=4) - 0.3) < 1e-12
    # Shorter-than-last falls back to the whole series.
    assert abs(steady_state_fraction([0.5, 0.5], last=50) - 0.5) < 1e-12


def test_run_spatial_seeds_shape_and_determinism():
    a = run_spatial_seeds(21, 21, b=1.85, n_steps=30, seeds=(0, 1), last=10)
    b = run_spatial_seeds(21, 21, b=1.85, n_steps=30, seeds=(0, 1), last=10)
    assert a["mean_steady_state"] == b["mean_steady_state"]
    assert len(a["per_seed"]) == 2
    assert 0.0 <= a["mean_steady_state"] <= 1.0


def test_run_wellmixed_seeds_shape():
    a = run_wellmixed_seeds(400, b=1.85, n_steps=30, seeds=(0, 1), last=10)
    assert len(a["per_seed"]) == 2
    assert 0.0 <= a["mean_steady_state"] <= 1.0
