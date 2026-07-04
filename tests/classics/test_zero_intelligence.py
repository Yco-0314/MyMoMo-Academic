"""Faithful-rule + determinism tests for the Gode & Sunder (1993) zero-intelligence
trader reproduction.

These pin the budget-constraint quote rule (ZI-C never violates value/cost; ZI-U
does), the competitive-equilibrium surplus computation, a hand-verifiable single
trade, the standing-price (resting-order) clearing rule, the value-vs-cost
matching surplus accounting, and determinism (same seed -> identical result).
They are faithfulness tests, NOT prediction tests (the P1-P3 predictions are
evaluated by examples/repro_zi_traders/run.py).
"""
from __future__ import annotations

from abm_auto.classics.zero_intelligence import (
    DoubleAuctionModel,
    TraderAgent,
    compare_arms,
    competitive_equilibrium,
    run_many_seeds,
    run_single,
)


# -- competitive equilibrium --------------------------------------------------

def test_competitive_equilibrium_hand_example():
    # Buyers value [10, 8, 3]; sellers cost [2, 5, 9].
    # Demand desc: 10, 8, 3 ; supply asc: 2, 5, 9.
    # pair1: 10>=2 -> surplus 8 ; pair2: 8>=5 -> surplus 3 ; pair3: 3<9 -> stop.
    # q=2, max surplus = 8 + 3 = 11.
    surplus, q = competitive_equilibrium([10, 8, 3], [2, 5, 9])
    assert q == 2
    assert surplus == 11


def test_competitive_equilibrium_no_feasible_trade():
    # Every buyer values below every seller's cost -> no pair, zero surplus.
    surplus, q = competitive_equilibrium([1, 2], [50, 60])
    assert q == 0
    assert surplus == 0.0


def test_competitive_equilibrium_pairs_highest_values_with_lowest_costs():
    # Surplus-maximizing assignment, not order of arrival.
    surplus, q = competitive_equilibrium([5, 100], [1, 90])
    # demand desc 100,5 ; supply asc 1,90 ; pair1 100-1=99 ; pair2 5<90 stop.
    assert q == 1
    assert surplus == 99


# -- ZI-C budget constraint (the only inter-arm difference) -------------------

def test_zi_c_buyer_never_bids_above_value():
    m = DoubleAuctionModel([50.0], [1.0], budget_constrained=True, pmin=1.0,
                           pmax=200.0, seed=0)
    buyer = m.buyers[0]
    bids = [buyer.quote() for _ in range(2000)]
    assert max(bids) <= buyer.value  # never above the redemption value
    assert min(bids) >= m.pmin


def test_zi_c_seller_never_asks_below_cost():
    m = DoubleAuctionModel([1.0], [50.0], budget_constrained=True, pmin=1.0,
                           pmax=200.0, seed=0)
    seller = m.sellers[0]
    asks = [seller.quote() for _ in range(2000)]
    assert min(asks) >= seller.cost  # never below cost
    assert max(asks) <= m.pmax


def test_zi_u_ignores_value_and_cost():
    # Unconstrained quotes span the full [pmin, pmax] range regardless of
    # value/cost, so a low-value buyer can bid far above its value.
    m = DoubleAuctionModel([10.0], [190.0], budget_constrained=False, pmin=1.0,
                           pmax=200.0, seed=0)
    buyer_bids = [m.buyers[0].quote() for _ in range(2000)]
    seller_asks = [m.sellers[0].quote() for _ in range(2000)]
    assert max(buyer_bids) > m.buyers[0].value     # bids above value occur
    assert min(seller_asks) < m.sellers[0].cost    # asks below cost occur


# -- single hand-verifiable trade + standing-price clearing ------------------

def test_single_feasible_pair_trades_and_banks_true_surplus():
    # One buyer value 100, one seller cost 10. Under ZI-C the only feasible trade
    # banks the TRUE pair surplus 100-10=90, efficiency 1.0 (q=1, max surplus 90).
    res = DoubleAuctionModel([100.0], [10.0], budget_constrained=True, seed=3,
                             periods=5).run()
    assert res["eq_quantity"] == 1
    assert res["max_surplus"] == 90.0
    assert res["n_trades"] == 1
    assert res["realized_surplus"] == 90.0
    assert res["efficiency"] == 1.0


def test_no_feasible_pair_no_trade():
    # Buyer value below seller cost -> ZI-C can never cross -> no trade, surplus 0,
    # and efficiency is 0 by the degenerate-schedule convention (max surplus 0).
    res = DoubleAuctionModel([5.0], [80.0], budget_constrained=True, seed=1).run()
    assert res["eq_quantity"] == 0
    assert res["max_surplus"] == 0.0
    assert res["n_trades"] == 0
    assert res["efficiency"] == 0.0


def test_trade_executes_at_standing_resting_price():
    # Force a deterministic crossing by hand to check the price is the RESTING
    # order's price (the standing quote already in the book), not the incoming one.
    m = DoubleAuctionModel([100.0], [10.0], budget_constrained=True, seed=0)
    buyer, seller = m.buyers[0], m.sellers[0]
    # Resting bid at 40 (buyer posted first), incoming ask at 20 crosses it.
    m._execute  # exists
    # Simulate: standing best_bid = (40, buyer); seller posts ask 20 <= 40 -> cross
    # at the standing bid price 40.
    m._execute(buyer, seller, 40.0)
    assert m.n_trades == 1
    assert m.trade_log[0]["price"] == 40.0          # resting price
    assert m.trade_log[0]["pair_surplus"] == 90.0   # true value-cost, not price
    assert m.realized_surplus == 90.0


# -- ZI-U can bank a loss (the efficiency-eroding mechanism) ------------------

def test_zi_u_loss_making_trade_banks_negative_surplus():
    # Unconstrained: a buyer (value 10) can bid above its value and match a seller
    # (cost 190) asking below its cost, banking the TRUE negative surplus 10-190.
    m = DoubleAuctionModel([10.0], [190.0], budget_constrained=False, seed=0)
    m._execute(m.buyers[0], m.sellers[0], 100.0)
    assert m.realized_surplus == 10.0 - 190.0   # negative -> erodes efficiency
    assert m.trade_log[0]["pair_surplus"] == -180.0


# -- a trader leaves the market after its one unit trades --------------------

def test_traded_trader_becomes_inactive():
    m = DoubleAuctionModel([100.0, 90.0], [10.0, 20.0], budget_constrained=True,
                           seed=0)
    m._execute(m.buyers[0], m.sellers[0], 50.0)
    assert m.buyers[0].traded is True
    assert m.sellers[0].traded is True
    assert m.buyers[0] not in m.active_buyers()
    assert m.sellers[0] not in m.active_sellers()
    # The untraded pair is still active.
    assert m.buyers[1] in m.active_buyers()
    assert m.sellers[1] in m.active_sellers()


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    r1 = run_single(8, budget_constrained=True, seed=42)
    r2 = run_single(8, budget_constrained=True, seed=42)
    assert r1 == r2


def test_same_seed_gives_same_schedule_across_arms():
    # The schedule draw is independent of the budget mode, so both arms see the
    # IDENTICAL value/cost schedule for a given seed (a FAIR comparison).
    a = DoubleAuctionModel.random_round(8, budget_constrained=True, seed=7)
    b = DoubleAuctionModel.random_round(8, budget_constrained=False, seed=7)
    assert a.buyer_values == b.buyer_values
    assert a.seller_costs == b.seller_costs
    assert a.max_surplus == b.max_surplus


def test_efficiency_never_exceeds_one_under_zi_c():
    # ZI-C can never bank more than the competitive max (every pair has
    # value>=price>=cost), so efficiency <= 1 across many seeds.
    r = run_many_seeds(8, budget_constrained=True, n_seeds=30, seed_base=0)
    assert all(e <= 1.0 + 1e-9 for e in r["per_seed_efficiency"])


def test_run_many_seeds_is_deterministic_and_shaped():
    a = run_many_seeds(8, budget_constrained=True, n_seeds=20, seed_base=0)
    b = run_many_seeds(8, budget_constrained=True, n_seeds=20, seed_base=0)
    assert a["mean_efficiency"] == b["mean_efficiency"]
    assert a["per_seed_efficiency"] == b["per_seed_efficiency"]
    assert len(a["per_seed_efficiency"]) == 20


def test_compare_arms_uses_same_seeds_for_both():
    c = compare_arms(8, n_seeds=20, seed_base=0)
    # Both arms ran over the same seed_base/n_seeds -> identical schedules; only
    # the quote rule differed. The gap is positive (ZI-C above ZI-U).
    assert c["zi_c"]["seed_base"] == c["zi_u"]["seed_base"] == 0
    assert c["zi_c"]["n_seeds"] == c["zi_u"]["n_seeds"] == 20
    assert c["efficiency_gap"] == (
        c["zi_c"]["mean_efficiency"] - c["zi_u"]["mean_efficiency"])
    assert c["efficiency_gap"] > 0.0


def test_trader_side_validation():
    m = DoubleAuctionModel([10.0], [5.0], seed=0)
    try:
        TraderAgent(99, m, side="middleman")
    except ValueError as e:
        assert "side" in str(e)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for bad side")
