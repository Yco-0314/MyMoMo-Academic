"""Faithful-rule + determinism tests for the El Farol Bar (Arthur 1994)
reproduction.

These pin the defining rules — GO iff the active predictor forecasts BELOW
capacity, the active predictor is the lowest recent-error one (deterministic
tie-break), every predictor is re-scored against the realized attendance each week,
the public attendance history slides over a bounded window, and the predictor
repertoire functions compute what their labels say — plus determinism (same seed ->
identical run). They are faithfulness tests, NOT prediction tests (P1-P3 are
evaluated by examples/repro_el_farol/run.py).
"""
from __future__ import annotations

from abm_auto.classics.el_farol import (
    BarAgent,
    ElFarolModel,
    default_repertoire,
    mean,
    run_single,
    std,
    variance,
    _average,
    _fixed,
    _last,
    _mirror,
    _trend,
)


# -- predictor repertoire rules ----------------------------------------------

def test_predictor_functions_compute_their_labels():
    hist = [10, 20, 30, 40, 50]
    assert _last(hist) == 50.0
    assert _mirror(100)(hist) == 50.0          # 100 - 50
    assert _mirror(100)([0, 0, 70]) == 30.0
    assert _average(3)(hist) == (30 + 40 + 50) / 3
    assert _average(2)(hist) == 45.0
    assert _fixed(60)(hist) == 60.0
    # trend over 3 weeks: slope = (50-30)/2 = 10 -> forecast = 50 + 10 = 60
    assert _trend(3)(hist) == 60.0
    # trend with too-short history falls back to last
    assert _trend(5)([10, 20]) == 20.0


def test_default_repertoire_is_fixed_and_nonempty():
    rep = default_repertoire(100)
    rep2 = default_repertoire(100)
    assert len(rep) >= 6                         # enough to deal k>=5
    labels = [lab for lab, _ in rep]
    labels2 = [lab for lab, _ in rep2]
    assert labels == labels2                     # identical across calls (fixed)
    assert len(set(labels)) == len(labels)       # distinct labels
    assert "mirror_around_half" in labels and "same_as_last_week" in labels


# -- agent rules --------------------------------------------------------------

def _agent(predictors, memory=0.3):
    # A throwaway model just to satisfy BarAgent's back-reference.
    m = ElFarolModel(n=1, k=1, weeks=0, transient=0, seed=0)
    a = BarAgent(0, m, predictors=predictors, memory=memory)
    return a


def test_best_predictor_breaks_ties_to_lowest_index():
    a = _agent([("p0", _last), ("p1", _last), ("p2", _last)])
    a.errors = [5.0, 5.0, 3.0]
    assert a.best_predictor_index() == 2         # unique min
    a.errors = [3.0, 3.0, 9.0]
    assert a.best_predictor_index() == 0         # tie at 3 -> lowest index
    a.errors = [4.0, 2.0, 2.0]
    assert a.best_predictor_index() == 1         # tie at 2 -> lowest index (1)


def test_decide_goes_iff_forecast_below_capacity():
    # Two fixed predictors: one forecasts 40 (< 60 -> go), one forecasts 80.
    a = _agent([("lo", _fixed(40)), ("hi", _fixed(80))])
    a.errors = [0.0, 5.0]                         # 'lo' is best -> forecast 40 -> GO
    assert a.decide([50], capacity=60) is True
    a.errors = [5.0, 0.0]                         # 'hi' is best -> forecast 80 -> STAY
    assert a.decide([50], capacity=60) is False
    # Forecast exactly at capacity is NOT below -> stay home (strict <).
    a2 = _agent([("at", _fixed(60))])
    assert a2.decide([50], capacity=60) is False


def test_rescore_rewards_accurate_predictors_lower_error():
    # 'good' forecasts 60, 'bad' forecasts 0; realized = 60.
    a = _agent([("good", _fixed(60)), ("bad", _fixed(0))], memory=0.5)
    a.rescore(history=[55], realized=60)
    # good: err contribution 0 -> stays 0; bad: (0-60)^2=3600 * 0.5 = 1800
    assert a.errors[0] == 0.0
    assert a.errors[1] == 0.5 * 3600
    # good is now the lowest-error predictor.
    assert a.best_predictor_index() == 0


# -- model week rules ---------------------------------------------------------

def test_attendance_counts_only_agents_below_threshold():
    m = ElFarolModel(n=4, k=1, capacity=60, weeks=0, transient=0, seed=0)
    # Force decisions: two agents forecast 40 (go), two forecast 90 (stay).
    m.agent_list[0].predictors = [("lo", _fixed(40))]
    m.agent_list[1].predictors = [("lo", _fixed(40))]
    m.agent_list[2].predictors = [("hi", _fixed(90))]
    m.agent_list[3].predictors = [("hi", _fixed(90))]
    for a in m.agent_list:
        a.errors = [0.0]
    m.step()
    assert m.attendance == 2                      # exactly the two 'lo' agents went
    assert m.history[-1] == 2                     # realized attendance appended


def test_history_window_is_bounded():
    m = ElFarolModel(n=11, k=3, history_len=10, weeks=50, transient=0, seed=1)
    for _ in range(40):
        m.step()
        assert len(m.history) == 10               # never grows past history_len


def test_rescore_uses_pre_append_history():
    # The realized attendance must be scored against the history the agents
    # forecast from (i.e. NOT yet containing this week's attendance).
    m = ElFarolModel(n=3, k=1, capacity=60, weeks=0, transient=0, seed=0)
    for a in m.agent_list:
        a.predictors = [("last", _last)]          # forecast = last week's count
        a.errors = [0.0]
    pre_last = m.history[-1]
    m.step()
    realized = m.attendance
    expected_err = (pre_last - realized) ** 2     # default memory folds it in
    # memory=0.30 default: error = 0.3 * (pre_last - realized)^2
    assert abs(m.agent_list[0].errors[0] - 0.30 * expected_err) < 1e-9


# -- metrics ------------------------------------------------------------------

def test_mean_variance_std_match_definitions():
    xs = [2, 4, 6]
    assert mean(xs) == 4.0
    assert abs(variance(xs) - 8 / 3) < 1e-12      # ((-2)^2+0+2^2)/3
    assert abs(std(xs) - (8 / 3) ** 0.5) < 1e-12
    assert mean([]) == 0.0
    assert variance([]) == 0.0
    assert std([5, 5, 5]) == 0.0


def test_run_window_excludes_transient():
    res = run_single(weeks=80, transient=30, seed=0)
    assert len(res["attendance_window"]) == 80
    assert res["transient"] == 30
    assert res["weeks"] == 80
    # attendance always in [0, N]
    assert all(0 <= x <= res["n"] for x in res["attendance_window"])


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(seed=42, weeks=120, transient=40)
    b = run_single(seed=42, weeks=120, transient=40)
    assert a["attendance_window"] == b["attendance_window"]
    assert a["mean_attendance"] == b["mean_attendance"]
    assert a["std_attendance"] == b["std_attendance"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(seed=1, weeks=120, transient=40)
    b = run_single(seed=2, weeks=120, transient=40)
    for res in (a, b):
        assert all(0 <= x <= res["n"] for x in res["attendance_window"])
        assert len(res["attendance_window"]) == 120
        assert res["std_attendance"] >= 0.0
