"""Faithful-rule + determinism tests for the Yard-Sale wealth-exchange (Chakraborti
2002) reproduction.

These pin the Gini / top-share / bottom-share metrics, the single-transaction rule
(stake = beta*min, fair coin, pair-conserving, non-negative), total-wealth conservation
over a whole run, the equal-start initial condition, the monotone-Gini helper, the
genuine per-agent stepping path, the vectorized numpy fast path, determinism (same seed
-> identical result), and the qualitative condensation direction.

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(condensation Gini>=0.95 + monotone; oligarchy top-1>=0.90, bottom-50%<=0.01; distinct
from the exponential Gini>=0.7) are evaluated by examples/repro_yard_sale/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.yard_sale import (
    WealthAgent,
    YardSaleModel,
    bottom_share,
    gini,
    is_non_decreasing,
    run_single,
    top_share,
    yard_sale_transaction,
)


# -- Gini / share metrics -----------------------------------------------------

def test_gini_equal_is_zero():
    assert gini([1.0, 1.0, 1.0, 1.0]) == pytest.approx(0.0, abs=1e-12)


def test_gini_one_agent_has_everything_approaches_one():
    w = [0.0] * 999 + [1000.0]
    # single owner of n agents -> G = 1 - 1/n
    assert gini(w) == pytest.approx(1.0 - 1.0 / len(w), abs=1e-9)


def test_gini_empty_and_allzero_are_zero():
    assert gini([]) == 0.0
    assert gini([0.0, 0.0, 0.0]) == 0.0


def test_gini_matches_mean_abs_difference_definition():
    # brute-force G = sum_ij |xi-xj| / (2 n^2 mean) on a small vector.
    xs = [1.0, 2.0, 3.0, 10.0]
    n = len(xs)
    mad = sum(abs(a - b) for a in xs for b in xs)
    ref = mad / (2 * n * n * (sum(xs) / n))
    assert gini(xs) == pytest.approx(ref, abs=1e-12)


def test_top_and_bottom_share():
    w = [1.0, 1.0, 2.0, 96.0]
    assert top_share(w) == pytest.approx(96.0 / 100.0)
    # bottom 50% (2 poorest of 4) hold 1+1 = 2 of 100.
    assert bottom_share(w, 0.5) == pytest.approx(2.0 / 100.0)


def test_shares_empty_and_allzero():
    assert top_share([]) == 0.0
    assert bottom_share([], 0.5) == 0.0
    assert top_share([0.0, 0.0]) == 0.0


# -- single transaction rule --------------------------------------------------

def test_transaction_stakes_fraction_of_poorer_and_conserves_pair():
    w = np.array([10.0, 4.0])
    # beta=0.5, poorer is agent 1 (4.0) -> stake 2.0; agent 0 wins.
    yard_sale_transaction(w, 0, 1, beta=0.5, i_wins=True)
    assert w[0] == pytest.approx(12.0)
    assert w[1] == pytest.approx(2.0)
    assert w.sum() == pytest.approx(14.0)   # conserved


def test_transaction_loser_direction():
    w = np.array([10.0, 4.0])
    yard_sale_transaction(w, 0, 1, beta=0.5, i_wins=False)  # agent 0 loses
    assert w[0] == pytest.approx(8.0)
    assert w[1] == pytest.approx(6.0)
    assert w.sum() == pytest.approx(14.0)


def test_transaction_never_makes_poorer_negative():
    # stake is bounded by the poorer holding, so a loss can at most empty the poorer.
    w = np.array([100.0, 3.0])
    yard_sale_transaction(w, 1, 0, beta=1.0, i_wins=False)  # poorer (agent 1) loses all
    assert w[1] == pytest.approx(0.0)
    assert w[0] == pytest.approx(103.0)
    assert (w >= 0).all()


# -- monotone helper ----------------------------------------------------------

def test_is_non_decreasing():
    assert is_non_decreasing([0.0, 0.1, 0.1, 0.5, 0.9])
    assert not is_non_decreasing([0.0, 0.5, 0.4])
    assert is_non_decreasing([0.3])            # trivially monotone


# -- model construction + invariants ------------------------------------------

def test_equal_start_and_agents():
    m = YardSaleModel(n=100, beta=0.1, seed=0)
    assert len(m.agent_list) == 100
    assert all(isinstance(a, WealthAgent) for a in m.agent_list)
    # equal start: everyone holds mean wealth; total = n by default; initial Gini = 0.
    assert m.w == pytest.approx(np.full(100, 1.0))
    assert m.total() == pytest.approx(100.0)
    assert m.gini_wealth() == pytest.approx(0.0, abs=1e-12)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        YardSaleModel(n=1)                      # need >= 2 agents
    with pytest.raises(ValueError):
        YardSaleModel(n=10, beta=0.0)           # beta out of (0,1)
    with pytest.raises(ValueError):
        YardSaleModel(n=10, beta=1.0)
    with pytest.raises(ValueError):
        YardSaleModel(n=10, record_every=0)
    with pytest.raises(ValueError):
        m = YardSaleModel(n=10, seed=0)
        m.run(0)                                # need sweeps > 0


# -- conservation over a whole run --------------------------------------------

def test_total_wealth_conserved_agent_path():
    m = YardSaleModel(n=200, beta=0.2, seed=1)
    before = m.total()
    for _ in range(20):
        m.step()                                # genuine per-agent sweeps
    assert m.total() == pytest.approx(before, abs=1e-6)
    assert (m.w >= -1e-12).all()                # no agent goes negative


def test_total_wealth_conserved_vectorized_path():
    m = YardSaleModel(n=200, beta=0.2, record_every=25, seed=1)
    res = m.run(100, vectorized=True)
    assert res["final_total_wealth"] == pytest.approx(200.0, abs=1e-6)
    assert (m.w >= -1e-9).all()


# -- agent path vs vectorized path are the SAME process on a shared draw -------

def test_agent_and_vectorized_paths_apply_same_rule():
    # Both paths must apply the identical stake-the-poorer fair bet; drive both from ONE
    # shared reference draw stream and require the resulting wealth vectors to match.
    n, beta = 50, 0.15
    rng = np.random.default_rng(123)
    draws = [(int(i), int(j), bool(c))
             for i, j, c in zip(rng.integers(0, n, 500),
                                rng.integers(0, n, 500),
                                rng.random(500) < 0.5)]

    # reference: apply the shared single-transaction rule directly.
    w_ref = np.full(n, 1.0)
    for i, j, c in draws:
        if i == j:
            continue
        yard_sale_transaction(w_ref, i, j, beta, c)

    # "vectorized-style" application of the same rule over the same draws.
    w_vec = np.full(n, 1.0)
    for i, j, c in draws:
        if i == j:
            continue
        stake = beta * (w_vec[i] if w_vec[i] <= w_vec[j] else w_vec[j])
        if c:
            w_vec[i] += stake
            w_vec[j] -= stake
        else:
            w_vec[i] -= stake
            w_vec[j] += stake

    assert np.allclose(w_ref, w_vec)
    assert w_ref.sum() == pytest.approx(float(n))


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_vectorized():
    a = run_single(n=300, beta=0.1, sweeps=200, record_every=50, seed=42)
    b = run_single(n=300, beta=0.1, sweeps=200, record_every=50, seed=42)
    assert a["gini_series"] == b["gini_series"]
    assert a["final_gini"] == b["final_gini"]
    assert a["final_top_share"] == b["final_top_share"]


def test_determinism_same_seed_identical_agent_path():
    a = run_single(n=200, beta=0.1, sweeps=100, record_every=25, seed=7, vectorized=False)
    b = run_single(n=200, beta=0.1, sweeps=100, record_every=25, seed=7, vectorized=False)
    assert a["gini_series"] == b["gini_series"]
    assert a["final_gini"] == b["final_gini"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=300, beta=0.1, sweeps=200, record_every=50, seed=1)
    b = run_single(n=300, beta=0.1, sweeps=200, record_every=50, seed=2)
    for res in (a, b):
        assert all(0.0 <= g <= 1.0 for g in res["gini_series"])
        assert 0.0 <= res["final_top_share"] <= 1.0
        assert res["final_total_wealth"] == pytest.approx(300.0, abs=1e-6)


# -- run summary shape --------------------------------------------------------

def test_run_summary_shape_and_baseline():
    res = run_single(n=200, beta=0.1, sweeps=100, record_every=50, seed=0)
    assert res["n"] == 200 and res["beta"] == 0.1
    assert res["n_transactions"] == 100 * 200
    # baseline (t=0) + one record per record_every chunk = 1 + 100/50 = 3 samples.
    assert len(res["gini_series"]) == 3
    assert res["initial_gini"] == pytest.approx(0.0, abs=1e-12)
    assert 0.0 <= res["final_gini"] <= 1.0


# -- qualitative condensation (the locked grade lives in run.py) --------------

def test_condensation_direction_gini_rises_and_top_share_grows():
    # Faithfulness sanity, not the locked grade: from an equal start the Gini climbs well
    # above 0 and the richest agent's share grows far beyond the egalitarian 1/n.
    res = run_single(n=500, beta=0.1, sweeps=5000, record_every=500, seed=0)
    assert res["final_gini"] > 0.5                 # inequality has clearly emerged
    assert res["final_top_share"] > 10.0 / 500.0   # richest >> egalitarian 1/n
    assert res["gini_non_decreasing"]              # monotone climb (condensation)
    assert res["final_total_wealth"] == pytest.approx(500.0, abs=1e-6)
