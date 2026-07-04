"""Faithful-rule + determinism tests for the Epstein (2002) civil-violence reproduction.

These pin the local rules (grievance G=H(1-L), arrest prob P=1-exp(-k*floor(C/A)),
activation iff G-R*P>T), the jail mechanic (off-grid for J ticks then released), the
movement-into-empty-vision-cell rule, and determinism (same seed -> identical run). They
are faithfulness tests, NOT prediction tests (the predictions are evaluated by
examples/repro_epstein_civil_violence/run.py).
"""
from __future__ import annotations

import math

from abm_auto.classics.epstein_civil_violence import (
    K,
    THRESHOLD,
    CitizenAgent,
    CivilViolenceModel,
    burstiness,
    run_many_seeds,
    run_single,
)


def _model(**kw):
    base = dict(nrows=10, ncols=10, vision=1, legitimacy=0.5, cop_density=0.0,
                citizen_density=0.0, max_jail_term=5, seed=0, max_steps=10)
    base.update(kw)
    return CivilViolenceModel(**base)


def test_grievance_is_hardship_times_one_minus_legitimacy():
    m = _model(legitimacy=0.7)
    c = CitizenAgent(0, m, cell=(0, 0), hardship=0.5, risk_aversion=0.5)
    assert abs(c.grievance() - 0.5 * (1 - 0.7)) < 1e-12
    # L=0 -> grievance equals hardship; L=1 -> grievance 0.
    m.legitimacy = 0.0
    assert abs(c.grievance() - 0.5) < 1e-12
    m.legitimacy = 1.0
    assert c.grievance() == 0.0


def test_arrest_probability_no_cop_is_zero_one_cop_is_about_0_9():
    # vision 1, a citizen alone -> floor(C/A)=floor(0/1)=0 -> P=0.
    m = _model(vision=1)
    c = CitizenAgent(0, m, cell=(5, 5), hardship=0.9, risk_aversion=0.5)
    m._place(c, (5, 5))
    m.citizens.append(c)
    assert c.arrest_probability() == 0.0
    # Put one cop adjacent: floor(1/1)=1 -> P = 1-exp(-k) ≈ 0.90.
    from abm_auto.classics.epstein_civil_violence import CopAgent
    cop = CopAgent(1, m, cell=(5, 6))
    m._place(cop, (5, 6))
    m.cops.append(cop)
    expected = 1.0 - math.exp(-K * 1)
    assert abs(c.arrest_probability() - expected) < 1e-12
    assert abs(expected - 0.8997) < 1e-3


def test_floor_ratio_two_cops_one_active_uses_floor():
    # Two cops, one active (self) -> floor(2/1)=2 -> P=1-exp(-2k).
    m = _model(vision=1)
    c = CitizenAgent(0, m, cell=(5, 5), hardship=0.9, risk_aversion=0.5)
    m._place(c, (5, 5)); m.citizens.append(c)
    from abm_auto.classics.epstein_civil_violence import CopAgent
    for i, cell in enumerate([(5, 6), (5, 4)], start=1):
        cop = CopAgent(i, m, cell=cell)
        m._place(cop, cell); m.cops.append(cop)
    assert abs(c.arrest_probability() - (1.0 - math.exp(-K * 2))) < 1e-12


def test_activation_rule_threshold():
    # No cops -> P=0 -> active iff grievance > T. High hardship, low legitimacy -> active.
    m = _model(vision=1, legitimacy=0.0)
    c = CitizenAgent(0, m, cell=(5, 5), hardship=0.9, risk_aversion=0.9)
    m._place(c, (5, 5)); m.citizens.append(c)
    c.decide_activation()
    assert c.active is True  # G=0.9 > 0.1, no deterrence
    # Low hardship -> grievance below threshold -> quiescent.
    c2 = CitizenAgent(1, m, cell=(1, 1), hardship=0.05, risk_aversion=0.9)
    m._place(c2, (1, 1)); m.citizens.append(c2)
    c2.decide_activation()
    assert c2.active is False  # G=0.05 < 0.1


def test_deterrence_one_cop_suppresses_a_marginal_rebel():
    # A citizen whose grievance just clears T can be pushed back below it by a visible cop.
    m = _model(vision=1, legitimacy=0.0)
    # G = H = 0.6 (>0.1). With one cop: net risk = R*0.8997. Choose R so G - R*P <= T.
    c = CitizenAgent(0, m, cell=(5, 5), hardship=0.6, risk_aversion=0.9)
    m._place(c, (5, 5)); m.citizens.append(c)
    c.decide_activation()
    assert c.active is True  # rebels with no cop in view
    from abm_auto.classics.epstein_civil_violence import CopAgent
    cop = CopAgent(1, m, cell=(5, 6))
    m._place(cop, (5, 6)); m.cops.append(cop)
    c.decide_activation()
    # G - R*P = 0.6 - 0.9*0.8997 = 0.6 - 0.8097 < 0.1 -> deterred.
    assert c.active is False


def test_cop_arrest_jails_active_citizen_off_grid():
    m = _model(vision=1, max_jail_term=3)
    from abm_auto.classics.epstein_civil_violence import CopAgent
    c = CitizenAgent(0, m, cell=(5, 5), hardship=1.0, risk_aversion=0.0)
    m._place(c, (5, 5)); m.citizens.append(c)
    c.active = True
    cop = CopAgent(1, m, cell=(5, 6))
    m._place(cop, (5, 6)); m.cops.append(cop)
    cop.enforce()
    assert c.jailed is True
    assert 1 <= c.jail_term <= 3
    assert c.active is False
    assert m.grid[5][5] is None          # left the grid
    assert (5, 5) in m.empty_cells


def test_jailed_citizen_released_after_term_and_excluded_while_jailed():
    m = _model(nrows=6, ncols=6, vision=1, cop_density=0.0, citizen_density=0.0,
               max_jail_term=2, max_steps=5)
    c = CitizenAgent(0, m, cell=(2, 2), hardship=1.0, risk_aversion=0.0)
    m._place(c, (2, 2)); m.citizens.append(c); m.add_agent(c); m.n_citizens = 1
    c.jail_term = 2
    # While jailed it must not be counted active even if flagged.
    c.active = True
    assert m.active_count() == 0
    assert m.jailed_count() == 1
    # Two ticks decrement the term to 0 and return it to the grid.
    m.step()
    assert c.jail_term == 1
    m.step()
    assert c.jail_term == 0
    assert c.jailed is False
    assert m.grid[c.cell[0]][c.cell[1]] is c  # back on the grid


def test_movement_only_into_empty_vision_cell():
    m = _model(nrows=3, ncols=3, vision=1, cop_density=0.0, citizen_density=0.0)
    c = CitizenAgent(0, m, cell=(1, 1), hardship=0.5, risk_aversion=0.5)
    m._place(c, (1, 1)); m.citizens.append(c)
    # Surround (1,1) by filling every other cell so no empty vision cell exists.
    others = []
    for i, cell in enumerate([(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)], start=1):
        o = CitizenAgent(i, m, cell=cell, hardship=0.0, risk_aversion=1.0)
        m._place(o, cell); m.citizens.append(o); others.append(o)
    assert not m.empty_cells
    m.move_agent(c)
    assert c.cell == (1, 1)  # nowhere empty to go -> stays put


def test_active_fraction_denominator_is_total_population():
    m = _model(nrows=8, ncols=8, vision=1, cop_density=0.0, citizen_density=0.0, max_steps=2)
    for i in range(4):
        c = CitizenAgent(i, m, cell=(i, 0), hardship=1.0, risk_aversion=0.0)
        m._place(c, (i, 0)); m.citizens.append(c)
    m.n_citizens = 4
    m.citizens[0].active = True
    m.citizens[1].active = True
    # 2 active out of 4 total citizens -> 0.5.
    assert m.active_count() == 2
    assert abs(m.active_fraction() - 0.5) < 1e-12


def test_burstiness_calm_vs_punctuated():
    # Flat series -> burstiness ~1. A rare spike -> burstiness >> 1.
    assert abs(burstiness([0.2, 0.2, 0.2, 0.2]) - 1.0) < 1e-12
    spike = [0.0] * 99 + [0.5]
    assert burstiness(spike) > 40
    # All-zero (totally calm) -> reported 0, NOT +inf (cannot spuriously pass P2).
    assert burstiness([0.0, 0.0, 0.0]) == 0.0


def test_determinism_same_seed_identical_run():
    a = run_single(nrows=20, ncols=20, vision=3, legitimacy=0.5, cop_density=0.04,
                   citizen_density=0.7, max_jail_term=15, seed=11, max_steps=40)
    b = run_single(nrows=20, ncols=20, vision=3, legitimacy=0.5, cop_density=0.04,
                   citizen_density=0.7, max_jail_term=15, seed=11, max_steps=40)
    assert a["active_fraction_series"] == b["active_fraction_series"]
    assert a["jailed_series"] == b["jailed_series"]
    assert a["mean_active_fraction"] == b["mean_active_fraction"]


def test_different_seed_changes_trajectory():
    a = run_single(nrows=20, ncols=20, vision=3, legitimacy=0.5, seed=1, max_steps=40)
    b = run_single(nrows=20, ncols=20, vision=3, legitimacy=0.5, seed=2, max_steps=40)
    assert a["active_fraction_series"] != b["active_fraction_series"]


def test_run_many_seeds_shape_and_determinism():
    r1 = run_many_seeds([0, 1, 2], nrows=20, ncols=20, vision=3, legitimacy=0.5,
                        max_steps=30, burn_in=5)
    r2 = run_many_seeds([0, 1, 2], nrows=20, ncols=20, vision=3, legitimacy=0.5,
                        max_steps=30, burn_in=5)
    assert r1["mean_active_fraction"] == r2["mean_active_fraction"]
    assert len(r1["rows"]) == 3
    assert r1["config"]["k"] == K and r1["config"]["threshold"] == THRESHOLD
    assert "mean_active_fraction_sd" in r1


def test_high_legitimacy_is_calmer_than_low_legitimacy():
    # Sanity (not a locked clause): L=0.9 should be much calmer than L=0.5 on the same seeds.
    hi = run_many_seeds([0, 1, 2], legitimacy=0.9, max_steps=60, burn_in=10)
    lo = run_many_seeds([0, 1, 2], legitimacy=0.5, max_steps=60, burn_in=10)
    assert hi["mean_active_fraction"] < lo["mean_active_fraction"]
