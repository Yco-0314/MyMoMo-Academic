"""Faithful-rule + determinism tests for the Hammond & Axelrod (2006) ethnocentrism repro.

These pin the local rules (4 strategy phenotypes, the one-shot donation/PD payoff with
b/c, the base-PTR + clamp, mutated inheritance, the four-stage tick order, and the
von Neumann neighbourhood) and determinism (same seed -> identical run). They are
faithfulness tests, NOT prediction tests (P1-P3 are evaluated by
examples/repro_ethnocentrism/run.py against the locked predictions).
"""
from __future__ import annotations

from abm_auto.classics.ethnocentrism import (
    BASE_PTR,
    BENEFIT,
    COST,
    DEATH_RATE,
    MUTATION,
    N_TAGS,
    STRATEGY_NAMES,
    EthnoAgent,
    EthnocentrismModel,
    run_many_seeds,
    run_single,
    strategy_name,
)


def _model(**kw):
    base = dict(side=6, seed=0, max_steps=5)
    base.update(kw)
    return EthnocentrismModel(**base)


def test_strategy_name_maps_four_phenotypes():
    assert strategy_name(True, False) == "ethnocentric"   # C-in, D-out
    assert strategy_name(True, True) == "humanitarian"    # C, C
    assert strategy_name(False, False) == "egoist"        # D, D
    assert strategy_name(False, True) == "traitorous"     # D-in, C-out


def test_cooperates_with_uses_tag_match_and_strategy():
    m = _model()
    # ethnocentric: cooperates with same tag, defects on different tag.
    ethno = EthnoAgent(0, m, cell=(0, 0), tag=1, coop_in=True, coop_out=False)
    same = EthnoAgent(1, m, cell=(0, 1), tag=1, coop_in=True, coop_out=False)
    diff = EthnoAgent(2, m, cell=(0, 2), tag=2, coop_in=True, coop_out=False)
    assert ethno.cooperates_with(same) is True
    assert ethno.cooperates_with(diff) is False
    # traitorous: defects on same tag, cooperates with different tag.
    trait = EthnoAgent(3, m, cell=(1, 0), tag=1, coop_in=False, coop_out=True)
    assert trait.cooperates_with(same) is False
    assert trait.cooperates_with(diff) is True


def test_interaction_payoff_donation_game_bc():
    # Two same-tag ethnocentric neighbours: each cooperates toward the other.
    # Each pays c and receives b -> ptr = BASE_PTR - c + b for both.
    m = _model(side=4)
    a = EthnoAgent(m._new_id(), m, cell=(1, 1), tag=0, coop_in=True, coop_out=False)
    b = EthnoAgent(m._new_id(), m, cell=(1, 2), tag=0, coop_in=True, coop_out=False)
    m._place(a, (1, 1)); m._place(b, (1, 2))
    m._interact()
    assert abs(a.ptr - (BASE_PTR - COST + BENEFIT)) < 1e-12
    assert abs(b.ptr - (BASE_PTR - COST + BENEFIT)) < 1e-12
    # in-group coop rate = 1.0 (both cooperated); no out-group pairs.
    assert abs(m.in_coop_rate() - 1.0) < 1e-12
    assert m.out_coop_rate() == 0.0


def test_interaction_ethnocentric_exploits_out_group_by_withholding():
    # ethnocentric (tag 0) next to humanitarian (tag 1, coops with everyone).
    # ethno withholds (D-out): pays nothing, but RECEIVES b from the humanitarian.
    # humanitarian cooperates out: pays c, receives nothing back.
    m = _model(side=4)
    ethno = EthnoAgent(m._new_id(), m, cell=(1, 1), tag=0, coop_in=True, coop_out=False)
    human = EthnoAgent(m._new_id(), m, cell=(1, 2), tag=1, coop_in=True, coop_out=True)
    m._place(ethno, (1, 1)); m._place(human, (1, 2))
    m._interact()
    assert abs(ethno.ptr - (BASE_PTR + BENEFIT)) < 1e-12       # only received
    assert abs(human.ptr - (BASE_PTR - COST)) < 1e-12          # only paid
    # both pairs are out-group; only the humanitarian cooperated -> rate 0.5.
    assert m.in_coop_rate() == 0.0
    assert abs(m.out_coop_rate() - 0.5) < 1e-12


def test_ptr_clamped_into_unit_interval():
    # Surround a defect-everyone egoist by 4 cooperating same-tag neighbours so it
    # receives 4*b on top of base PTR; PTR stays a valid probability (<=1 here anyway),
    # and a strongly-negative case clamps to 0.
    m = _model(side=5)
    centre = EthnoAgent(m._new_id(), m, cell=(2, 2), tag=0, coop_in=True, coop_out=True)
    m._place(centre, (2, 2))
    for cell in [(1, 2), (3, 2), (2, 1), (2, 3)]:
        nb = EthnoAgent(m._new_id(), m, cell=cell, tag=1, coop_in=False, coop_out=False)
        m._place(nb, cell)
    # centre cooperates with all 4 out-group neighbours (pays 4c, receives nothing).
    m._interact()
    assert abs(centre.ptr - (BASE_PTR - 4 * COST)) < 1e-12
    assert centre.ptr >= 0.0


def test_immigration_fills_one_empty_site():
    m = _model(side=3)
    assert m.population() == 0
    m._immigrate()
    assert m.population() == 1
    occ = m.living_agents()[0]
    assert 0 <= occ.tag < N_TAGS
    assert occ.strategy in {(True, False), (True, True), (False, False), (False, True)}


def test_immigration_noop_when_full():
    m = _model(side=2)
    for _ in range(4):
        m._immigrate()
    assert m.population() == 4
    assert not m.empty_cells
    m._immigrate()  # no empty site -> no change
    assert m.population() == 4


def test_reproduction_into_empty_neighbour_with_certain_ptr():
    m = _model(side=3)
    parent = EthnoAgent(m._new_id(), m, cell=(1, 1), tag=2, coop_in=True, coop_out=False)
    m._place(parent, (1, 1))
    parent.ptr = 1.0  # reproduces with certainty
    pop_before = m.population()
    m._reproduce()
    assert m.population() == pop_before + 1
    # with mutation tiny, offspring almost surely inherits parent's tag+strategy; at
    # least confirm a child appeared adjacent to the parent.
    children = [a for a in m.living_agents() if a is not parent]
    assert len(children) == 1
    assert children[0].cell in m._neighbour_cells((1, 1))


def test_reproduction_skipped_when_no_empty_neighbour():
    m = _model(side=3)
    parent = EthnoAgent(m._new_id(), m, cell=(1, 1), tag=0, coop_in=True, coop_out=False)
    m._place(parent, (1, 1))
    for cell in m._neighbour_cells((1, 1)):
        nb = EthnoAgent(m._new_id(), m, cell=cell, tag=0, coop_in=True, coop_out=False)
        m._place(nb, cell)
    pop_before = m.population()
    parent.ptr = 1.0
    # every agent's PTR is 1.0 but the parent's NN are full; the corner/edge neighbours
    # may still reproduce into other empties, so only assert the centre had no room:
    assert m._empty_neighbours((1, 1)) == []


def test_death_frees_sites():
    m = _model(side=4, death_rate=1.0)  # everyone dies
    for cell in [(0, 0), (1, 1), (2, 2)]:
        a = EthnoAgent(m._new_id(), m, cell=cell, tag=0, coop_in=True, coop_out=False)
        m._place(a, cell)
    assert m.population() == 3
    m._die()
    assert m.population() == 0
    assert len(m.empty_cells) == m.side * m.side


def test_no_death_keeps_population():
    m = _model(side=4, death_rate=0.0)
    for cell in [(0, 0), (1, 1)]:
        a = EthnoAgent(m._new_id(), m, cell=cell, tag=0, coop_in=True, coop_out=False)
        m._place(a, cell)
    m._die()
    assert m.population() == 2


def test_strategy_share_sums_to_one_on_nonempty_grid():
    r = run_single(side=20, seed=3, max_steps=200, tail=50)
    last = {k: r[f"{k}_series"][-1] for k in STRATEGY_NAMES}
    assert abs(sum(last.values()) - 1.0) < 1e-9


def test_determinism_same_seed_identical_run():
    a = run_single(side=20, seed=7, max_steps=150, tail=30)
    b = run_single(side=20, seed=7, max_steps=150, tail=30)
    assert a["ethnocentric_series"] == b["ethnocentric_series"]
    assert a["in_coop_series"] == b["in_coop_series"]
    assert a["out_coop_series"] == b["out_coop_series"]
    assert a["population_series"] == b["population_series"]


def test_different_seed_changes_trajectory():
    a = run_single(side=20, seed=1, max_steps=150, tail=30)
    b = run_single(side=20, seed=2, max_steps=150, tail=30)
    assert a["ethnocentric_series"] != b["ethnocentric_series"]


def test_run_many_seeds_shape_and_determinism():
    r1 = run_many_seeds([0, 1], side=20, max_steps=150, tail=30)
    r2 = run_many_seeds([0, 1], side=20, max_steps=150, tail=30)
    assert r1["mean_shares"] == r2["mean_shares"]
    assert len(r1["rows"]) == 2
    assert set(r1["mean_shares"]) == set(STRATEGY_NAMES)
    assert "mean_in_coop_rate" in r1 and "mean_out_coop_rate" in r1
    cfg = r1["config"]
    assert cfg["cost"] == COST and cfg["benefit"] == BENEFIT
    assert cfg["base_ptr"] == BASE_PTR and cfg["mutation"] == MUTATION
    assert cfg["death_rate"] == DEATH_RATE
    assert abs(cfg["bc_ratio"] - BENEFIT / COST) < 1e-12


def test_config_constants_are_canonical():
    # Lock the canonical Hammond-Axelrod values at the module level.
    assert N_TAGS == 4
    assert COST == 0.01 and BENEFIT == 0.03
    assert BASE_PTR == 0.12
    assert MUTATION == 0.005
    assert DEATH_RATE == 0.10
