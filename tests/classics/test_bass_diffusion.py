"""Faithful-rule + determinism tests for the Bass (1969) diffusion reproduction.

These pin the agent-level Bass hazard (p + q*F clamped to [0,1]), the synchronous
frozen-F update, irreversibility, the analytic peak-time formula, and determinism
(same seed -> identical result). They are faithfulness tests, NOT prediction tests
(the locked predictions P1-P3 are evaluated by examples/repro_bass_diffusion/run.py).
"""
from __future__ import annotations

import math

from abm_auto.classics.bass_diffusion import (
    BassModel,
    analytic_peak_time,
    is_sigmoid,
    run_many_seeds,
    run_single,
)


def test_adoption_probability_is_bass_hazard():
    m = BassModel(10, p=0.03, q=0.38, seed=0)
    assert m.adoption_probability(0.0) == 0.03          # innovation only at F=0
    assert abs(m.adoption_probability(0.5) - (0.03 + 0.38 * 0.5)) < 1e-12
    # clamps to [0, 1].
    assert m.adoption_probability(10.0) == 1.0
    m_neg = BassModel(10, p=-1.0, q=0.0, seed=0)
    assert m_neg.adoption_probability(0.0) == 0.0


def test_pure_innovation_p_one_adopts_everyone_first_tick():
    # p=1 => every non-adopter adopts on tick 1 regardless of RNG; irreversible.
    res = run_single(50, p=1.0, q=0.0, seed=3, stop_fraction=0.99)
    assert res["final_adopter_fraction"] == 1.0
    assert res["steps"] == 1
    # new[0] is the t=0 baseline (0); all 50 adopt in tick 1.
    assert res["new_series"][0] == 0
    assert res["new_series"][1] == 50


def test_zero_rates_never_adopt():
    # p=0, q=0 => probability 0 forever; nobody ever adopts (stops at max_steps).
    res = run_single(20, p=0.0, q=0.0, seed=1, stop_fraction=0.99, max_steps=5)
    assert res["final_adopter_count"] == 0
    assert res["steps"] == 5


def test_adoption_is_irreversible_and_cumulative_monotone():
    res = run_single(2000, p=0.03, q=0.38, seed=7)
    cum = res["cumulative_series"]
    # cumulative adopters never decrease.
    assert all(cum[i + 1] >= cum[i] for i in range(len(cum) - 1))
    # new adoptions sum to the final cumulative count.
    assert sum(res["new_series"]) == res["final_adopter_count"]


def test_synchronous_frozen_F_within_tick():
    # All agents in a tick decide against the SAME frozen F (the start-of-tick
    # fraction). With p=0, q=1 and exactly half pre-seeded as adopters, the frozen
    # F is 0.5, so each remaining non-adopter adopts with prob 0+1*0.5 = 0.5 — none
    # see the others' same-tick adoptions (which would raise F mid-tick).
    m = BassModel(100, p=0.0, q=1.0, seed=0)
    for a in m.agent_list[:50]:
        a.adopted = True
    m.reporter.collect(m)                 # t=0 baseline
    m.step()                              # one synchronous tick
    # F was frozen at 0.5 for every decision; the model exposes that frozen value.
    assert m.tick_fraction == 0.5


def test_determinism_same_seed_identical_result():
    a = run_single(3000, p=0.03, q=0.38, seed=42)
    b = run_single(3000, p=0.03, q=0.38, seed=42)
    assert a["cumulative_series"] == b["cumulative_series"]
    assert a["new_series"] == b["new_series"]
    assert a["final_adopter_count"] == b["final_adopter_count"]


def test_different_seeds_differ_but_converge():
    a = run_single(3000, p=0.03, q=0.38, seed=1)
    b = run_single(3000, p=0.03, q=0.38, seed=2)
    # Stochastic paths differ...
    assert a["new_series"] != b["new_series"]
    # ...but both reach near-full adoption.
    assert a["final_adopter_fraction"] >= 0.99
    assert b["final_adopter_fraction"] >= 0.99


def test_analytic_peak_time_formula():
    # t* = ln(q/p)/(p+q); for p=0.03, q=0.38 -> ~6.19.
    t_star = analytic_peak_time(0.03, 0.38)
    assert abs(t_star - math.log(0.38 / 0.03) / (0.03 + 0.38)) < 1e-12
    assert 6.0 < t_star < 6.4


def test_is_sigmoid_detects_interior_inflection():
    # A clean logistic-like cumulative curve: increments rise then fall.
    cum = [0.0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.0]
    s = is_sigmoid(cum)
    assert s["monotone"] is True
    assert s["inflection_interior"] is True
    # A purely concave (monotone-decreasing increments) curve has its peak increment
    # at the FIRST step -> not interior (this is the q=0 pure-innovation shape).
    concave = [0.0, 0.4, 0.6, 0.7, 0.75, 0.78]
    s2 = is_sigmoid(concave)
    assert s2["monotone"] is True
    assert s2["inflection_interior"] is False


def test_q_zero_control_rate_monotonically_decreasing():
    # Pure innovation (q=0): each tick a constant fraction p of the REMAINING
    # non-adopters adopt, so the EXPECTED per-tick new adoptions decay monotonically
    # (no interior peak). A single noisy seed can jitter the early ties, so the
    # control is evaluated on the seed-averaged rate curve (as the runner does for P3).
    res = run_many_seeds(10000, p=0.03, q=0.0, n_seeds=20, seed_base=0,
                         stop_fraction=0.99, max_steps=1000)
    mean_new = res["mean_new_fraction"][1:]   # drop t=0 baseline
    # the FIRST tick is the busiest; argmax of the mean rate is the first tick.
    assert mean_new.index(max(mean_new)) == 0
    s = is_sigmoid(res["mean_cumulative_fraction"])
    assert s["inflection_interior"] is False


def test_run_many_seeds_shapes_and_deterministic():
    a = run_many_seeds(2000, p=0.03, q=0.38, n_seeds=5, seed_base=0)
    b = run_many_seeds(2000, p=0.03, q=0.38, n_seeds=5, seed_base=0)
    assert a["mean_cumulative_fraction"] == b["mean_cumulative_fraction"]
    assert a["per_seed_peak_tick"] == b["per_seed_peak_tick"]
    assert len(a["per_seed_peak_tick"]) == 5
    assert a["final_cumulative_fraction"] >= 0.99
