"""Faithful-rule + determinism tests for the Maki-Thompson rumor reproduction.

These pin the three directed-contact rules (S->I informs the ignorant; S->S and
S->R both age out the INITIATOR to Stifler), the single-seed initialisation, the
O(1) counters agreeing with the roster, absorption (run to S=0), the CTMC clock
rescaling under the absolute rate, determinism (same seed -> identical run), the
analytic fixed point theta=exp(-2(1-theta))=0.2032, and the conditional-on-outbreak
ensemble helper. They are faithfulness tests, NOT prediction tests (the locked
predictions P1-P3 are evaluated by examples/repro_maki_thompson_rumor/run.py).
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.maki_thompson_rumor import (
    ANALYTIC_PEAK_SPREADER,
    IGNORANT,
    SPREADER,
    STIFLER,
    MakiThompsonModel,
    RumorAgent,
    analytic_i_inf,
    run_many_seeds,
    run_single,
)


def test_initial_seeding_and_baseline_counts():
    m = MakiThompsonModel(n=1000, initial_spreaders=1, seed=0)
    assert m.n_spreader == 1
    assert m.n_ignorant == 999
    assert m.n_stifler == 0
    # O(1) counters agree with the live roster.
    assert m.count(SPREADER) == 1
    assert m.count(IGNORANT) == 999
    assert m.count(STIFLER) == 0


def test_counters_track_roster_through_a_run():
    m = MakiThompsonModel(n=500, initial_spreaders=1, seed=3)
    res = m.run()
    # Conservation: I + S + R = N at every point, and S = 0 at absorption.
    assert m.n_ignorant + m.n_spreader + m.n_stifler == 500
    assert m.n_spreader == 0
    # Counters equal the roster scan.
    assert m.count(IGNORANT) == m.n_ignorant
    assert m.count(SPREADER) == 0
    assert m.count(STIFLER) == m.n_stifler
    assert res["absorbed"] is True


def test_rule_S_to_I_informs_the_ignorant():
    # Force the contacted partner to be an ignorant: set counts so the whole
    # "other" mass is ignorant, then fire one contact — S must grow by 1.
    m = MakiThompsonModel(n=100, initial_spreaders=1, seed=0)
    # 1 spreader, 99 ignorants. From the initiator's view the other 99 are all
    # ignorant (n_spreader-1 = 0 spreaders, 0 stiflers), so ANY draw lands S->I.
    s_before = m.n_spreader
    m._fire_one_contact()
    assert m.n_spreader == s_before + 1      # ignorant became a spreader
    assert m.n_ignorant == 98
    assert m.n_stifler == 0


def test_rule_S_to_S_ages_out_only_the_initiator():
    # Two spreaders, no ignorants left: every contact lands on another informed
    # agent, so the initiator ages out -> Stifler (only ONE state change).
    m = MakiThompsonModel(n=3, initial_spreaders=2, seed=1)
    # Remove the lone ignorant so the ONLY possible contact target is the other
    # spreader (an S->S contact); the third agent is that other spreader.
    for p in m.persons:
        if p.state == IGNORANT:
            p.state = STIFLER
    m.n_stifler += m.n_ignorant
    m.n_ignorant = 0
    assert m.n_ignorant == 0 and m.n_spreader == 2 and m.n_stifler == 1
    m._fire_one_contact()
    # Exactly one spreader aged out -> Stifler; the other spreader is untouched.
    assert m.n_spreader == 1
    assert m.n_stifler == 2
    assert m.n_ignorant == 0


def test_rule_S_to_R_ages_out_the_initiator():
    # One spreader among stiflers (no ignorants): the only possible contact is
    # S->R, which ages out the initiator -> absorption in one event.
    m = MakiThompsonModel(n=3, initial_spreaders=1, seed=0)
    # Manually convert the two ignorants to stiflers to isolate an S->R contact.
    for p in m.persons:
        if p.state == IGNORANT:
            p.state = STIFLER
    m.n_stifler += m.n_ignorant
    m.n_ignorant = 0
    assert m.n_spreader == 1 and m.n_stifler == 2 and m.n_ignorant == 0
    m._fire_one_contact()
    assert m.n_spreader == 0          # initiator aged out
    assert m.n_stifler == 3


def test_peak_spreader_is_tracked_exactly():
    res = run_single(n=2000, initial_spreaders=1, seed=2)
    # Peak spreader count >= the seed count and <= N; fraction consistent.
    assert res["peak_spreader_count"] >= 1
    assert res["peak_spreader_count"] <= 2000
    assert res["peak_spreader_fraction"] == pytest.approx(
        res["peak_spreader_count"] / 2000)


def test_run_reaches_absorption_and_conserves_population():
    res = run_single(n=3000, initial_spreaders=1, seed=5)
    assert res["s_inf"] == 0.0        # no spreaders left (absorbed)
    # I + R = N at the end (S=0).
    assert res["final_ignorant"] + res["final_stifler"] == 3000
    assert res["i_inf"] + res["r_inf"] == pytest.approx(1.0)


def test_determinism_same_seed_identical_run():
    a = run_single(n=3000, initial_spreaders=1, seed=7)
    b = run_single(n=3000, initial_spreaders=1, seed=7)
    assert a["i_inf"] == b["i_inf"]
    assert a["r_inf"] == b["r_inf"]
    assert a["events"] == b["events"]
    assert a["peak_spreader_count"] == b["peak_spreader_count"]
    assert a["S_series"] == b["S_series"]


def test_different_seeds_can_differ():
    outs = {run_single(n=3000, initial_spreaders=1, seed=s)["i_inf"]
            for s in range(8)}
    assert len(outs) > 1               # stochastic across seeds


def test_rate_only_rescales_time_not_composition():
    # THE discriminating signature: scaling the absolute contact rate leaves the
    # event SEQUENCE (hence the final composition) identical — only the CTMC clock
    # rescales. Same seed, different rate => same i_inf/events, clock scaled ~1/rate.
    base = run_single(n=4000, rate=1.0, initial_spreaders=1, seed=11)
    fast = run_single(n=4000, rate=4.0, initial_spreaders=1, seed=11)
    assert fast["i_inf"] == base["i_inf"]
    assert fast["events"] == base["events"]
    assert fast["peak_spreader_count"] == base["peak_spreader_count"]
    # Clock scales inversely with the rate (~ base/4), within RNG-shared tolerance.
    assert fast["clock"] == pytest.approx(base["clock"] / 4.0, rel=1e-9)


def test_analytic_fixed_point_rho1_is_0203():
    theta = analytic_i_inf(1.0)
    assert theta == pytest.approx(0.2031878, abs=1e-5)
    # It genuinely solves theta = exp(-2 (1 - theta)).
    assert theta == pytest.approx(math.exp(-2.0 * (1.0 - theta)), abs=1e-9)


def test_analytic_fixed_point_general_rho():
    # theta = exp(-(1+rho)(1-theta)); larger rho => smaller never-hear fraction.
    t_half = analytic_i_inf(0.5)
    t_one = analytic_i_inf(1.0)
    t_two = analytic_i_inf(2.0)
    assert t_two < t_one < t_half
    for rho, t in ((0.5, t_half), (1.0, t_one), (2.0, t_two)):
        assert t == pytest.approx(math.exp(-(1.0 + rho) * (1.0 - t)), abs=1e-9)


def test_analytic_peak_spreader_constant():
    assert ANALYTIC_PEAK_SPREADER == pytest.approx(1.0 - math.log(2.0))
    assert ANALYTIC_PEAK_SPREADER == pytest.approx(0.30685, abs=1e-4)


def test_run_many_seeds_conditions_on_outbreak():
    out = run_many_seeds(n=3000, initial_spreaders=1, n_seeds=30, seed_base=0)
    assert out["n_seeds"] == 30
    assert 0 <= out["n_takeoff"] <= 30
    # Determinism of the ensemble.
    out2 = run_many_seeds(n=3000, initial_spreaders=1, n_seeds=30, seed_base=0)
    assert out["i_infs"] == out2["i_infs"]
    assert out["mean_i_inf"] == out2["mean_i_inf"]
    # Conditional mean i_inf sits near the analytic constant when take-off happens.
    if out["n_takeoff"] > 0:
        assert 0.15 < out["mean_i_inf"] < 0.26
        # Every taken-off run has a large stifler fraction (not a fizzle).
        assert out["min_i_inf"] > 0.0


def test_agent_step_is_noop():
    m = MakiThompsonModel(n=10, initial_spreaders=1, seed=0)
    before = (m.n_ignorant, m.n_spreader, m.n_stifler)
    for p in m.persons:
        p.step()
    assert (m.n_ignorant, m.n_spreader, m.n_stifler) == before


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        MakiThompsonModel(n=1, initial_spreaders=1)          # n too small
    with pytest.raises(ValueError):
        MakiThompsonModel(n=100, rate=0.0, initial_spreaders=1)   # rate <= 0
    with pytest.raises(ValueError):
        MakiThompsonModel(n=100, initial_spreaders=0)        # no seed
    with pytest.raises(ValueError):
        MakiThompsonModel(n=100, initial_spreaders=100)      # all spreaders
    with pytest.raises(ValueError):
        analytic_i_inf(0.0)                                  # rho <= 0
