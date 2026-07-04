"""Faithful-rule + determinism tests for the Minority Game (Challet & Zhang 1997)
reproduction.

These pin the defining rules — minority wins (N odd, no ties), virtual scoring of
ALL strategies, deterministic best-strategy tie-break, history sliding over 2**m
states, the σ²/N volatility convention (random benchmark = 1), and the α = 2**m/N
control — plus determinism (same seed -> identical run). They are faithfulness
tests, NOT prediction tests (P1-P3 are evaluated by examples/repro_minority_game/run.py).
"""
from __future__ import annotations

from abm_auto.classics.minority_game import (
    MGAgent,
    MinorityGameModel,
    alpha,
    random_benchmark,
    run_single,
    variance,
    volatility,
)


# -- agent rules --------------------------------------------------------------

def _model(n=3, m=1, s=2, seed=0):
    return MinorityGameModel(n, m=m, s=s, seed=seed, rounds=1, transient=0)


def test_best_strategy_breaks_ties_to_lowest_index():
    m = _model()
    a = m.agent_list[0]
    a.scores = [5, 5, 3]
    a.strategies = [[0], [0], [0]]  # length matches scores for safety
    assert a.best_strategy_index() == 0     # tie at 5 -> lowest index
    a.scores = [3, 7, 7]
    assert a.best_strategy_index() == 1     # tie at 7 -> lowest index (1)
    a.scores = [3, 4, 9]
    assert a.best_strategy_index() == 2     # unique max


def test_choose_uses_best_strategy_table_at_history():
    m = _model(m=1)  # P = 2 histories
    a = m.agent_list[0]
    a.strategies = [[0, 1], [1, 0]]
    a.scores = [10, 0]                       # strategy 0 is best
    assert a.choose(0) == 0                  # strategy0[history=0]
    assert a.choose(1) == 1                  # strategy0[history=1]
    a.scores = [0, 10]                       # now strategy 1 is best
    assert a.choose(0) == 1                  # strategy1[history=0]
    assert a.choose(1) == 0


def test_update_scores_rewards_every_strategy_predicting_minority():
    m = _model(m=1)
    a = m.agent_list[0]
    # At history index 0: strategy0 plays 1, strategy1 plays 0.
    a.strategies = [[1, 0], [0, 0]]
    a.scores = [0, 0]
    # Winning (minority) side = 1: only strategies playing 1 at history 0 are rewarded.
    a.update_scores(history_index=0, winning_side=1)
    assert a.scores == [1, 0]
    # Winning side = 0: both strategies that play 0 at history 0 get +1 (here only s1).
    a.update_scores(history_index=0, winning_side=0)
    assert a.scores == [1, 1]


# -- model round rules --------------------------------------------------------

def test_minority_side_wins_side1_when_attendance_below_half():
    # Force a known set of choices: N=3, two agents choose 0, one chooses 1 ->
    # attendance (side 1) = 1 < 1.5 -> side 1 is the minority -> side 1 wins.
    m = MinorityGameModel(3, m=1, s=1, seed=0, rounds=1, transient=0)
    h = m.history_index
    # Override strategies so choices are deterministic at the current history.
    m.agent_list[0].strategies = [[0, 0]]
    m.agent_list[1].strategies = [[0, 0]]
    m.agent_list[2].strategies = [[1, 1]]
    for a in m.agent_list:
        a.scores = [0]
    m.step()
    assert m.attendance == 1
    # Side 1 (the singleton) is the minority and wins -> scores of side-1 players +1.
    assert m.agent_list[2].scores == [1]
    assert m.agent_list[0].scores == [0]
    # History slid: new low bit = winning side (1).
    assert (m.history_index & 1) == 1


def test_minority_side_wins_side0_when_attendance_above_half():
    # Two choose 1, one chooses 0 -> attendance = 2 > 1.5 -> side 0 is minority -> wins.
    m = MinorityGameModel(3, m=1, s=1, seed=0, rounds=1, transient=0)
    m.agent_list[0].strategies = [[1, 1]]
    m.agent_list[1].strategies = [[1, 1]]
    m.agent_list[2].strategies = [[0, 0]]
    for a in m.agent_list:
        a.scores = [0]
    m.step()
    assert m.attendance == 2
    assert m.agent_list[2].scores == [1]    # the lone side-0 player wins
    assert m.agent_list[0].scores == [0]
    assert (m.history_index & 1) == 0       # winning side 0 pushed into history


def test_n_must_be_odd():
    raised = False
    try:
        MinorityGameModel(300, m=2, s=2, seed=0)
    except ValueError:
        raised = True
    assert raised


def test_history_stays_within_2_to_the_m_states():
    m = MinorityGameModel(301, m=3, s=2, seed=1, rounds=50, transient=0)
    seen = set()
    for _ in range(200):
        m.step()
        seen.add(m.history_index)
        assert 0 <= m.history_index < m.p   # always in [0, 2**m)
    assert m.p == 8


def test_strategy_tables_have_one_entry_per_history():
    m = MinorityGameModel(11, m=4, s=2, seed=3, rounds=1, transient=0)
    assert m.p == 16
    for a in m.agent_list:
        assert len(a.strategies) == 2
        for table in a.strategies:
            assert len(table) == 16
            assert all(v in (0, 1) for v in table)


# -- metric conventions -------------------------------------------------------

def test_alpha_is_two_to_the_m_over_n():
    assert alpha(301, 5) == 32 / 301
    assert alpha(301, 2) == 4 / 301
    assert abs(alpha(64, 8) - 4.0) < 1e-12   # the N=64,m=8 -> α=4 point


def test_variance_matches_definition():
    xs = [2, 4, 6]
    # mean = 4; var = ((-2)^2 + 0 + 2^2)/3 = 8/3
    assert abs(variance(xs) - 8 / 3) < 1e-12
    assert variance([]) == 0.0
    assert variance([5, 5, 5]) == 0.0


def test_volatility_convention_random_benchmark_is_one():
    # Var(A)=N/4 (coin flips) must give sigma^2/N = 1 under the locked convention.
    n = 100
    # Construct a series with exact variance N/4 = 25 -> attendance alternating
    # mean +/- 5 has variance 25.
    series = [55, 45] * 500
    assert abs(variance(series) - 25.0) < 1e-9
    assert abs(volatility(series, n) - 1.0) < 1e-9
    assert random_benchmark() == 1.0
    # A constant attendance (everyone perfectly anti-correlated) -> zero volatility.
    assert volatility([50] * 10, n) == 0.0


def test_volatility_scales_four_times_attendance_variance_over_n():
    n = 200
    series = [60, 40, 60, 40]
    assert abs(volatility(series, n) - 4.0 * variance(series) / n) < 1e-12


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(301, m=4, s=2, seed=42, rounds=300, transient=100)
    b = run_single(301, m=4, s=2, seed=42, rounds=300, transient=100)
    assert a["volatility"] == b["volatility"]
    assert a["attendance_window"] == b["attendance_window"]
    assert a["mean_attendance"] == b["mean_attendance"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(301, m=4, s=2, seed=1, rounds=300, transient=100)
    b = run_single(301, m=4, s=2, seed=2, rounds=300, transient=100)
    for res in (a, b):
        # attendance always in [0, N]; volatility positive and finite.
        assert all(0 <= x <= 301 for x in res["attendance_window"])
        assert res["volatility"] > 0.0
        assert len(res["attendance_window"]) == 300


def test_run_window_excludes_transient():
    res = run_single(301, m=3, s=2, seed=0, rounds=200, transient=50)
    assert len(res["attendance_window"]) == 200   # only the post-transient rounds
    assert res["transient"] == 50
    assert res["rounds"] == 200
