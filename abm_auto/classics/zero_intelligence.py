"""Gode & Sunder (1993) zero-intelligence traders — a faithful agent-based
reproduction in a continuous double auction (CDA).

Source: Gode, D.K., Sunder, S. (1993) "Allocative Efficiency of Markets with
Zero-Intelligence Traders: Market as a Partial Substitute for Individual
Rationality", Journal of Political Economy 101(1):119-137.
doi:10.1086/261868.

The central result: traders who submit RANDOM bids/asks (no profit motive, no
learning, no memory) nonetheless drive a continuous double auction to near-100%
allocative efficiency — *provided* they respect their budget constraint (a buyer
never bids above its value; a seller never asks below its cost). It is the market
INSTITUTION, not individual rationality, that produces the efficiency. Remove the
budget constraint (ZI-U traders bid/ask over the whole price range, ignoring
value/cost) and efficiency drops well below.

Rules (verified against the paper):
  * A market round has M buyers, each holding ONE unit to buy with a private
    redemption value v_i, and M sellers, each holding ONE unit to sell at a
    private cost c_j. (We use the classic single-unit-per-trader schedule; the
    aggregate demand/supply schedules are the sorted values and costs.) Values
    and costs are drawn i.i.d. uniformly from [1, pmax].
  * Competitive equilibrium: sort buyer values DESCENDING (the demand schedule)
    and seller costs ASCENDING (the supply schedule). The equilibrium quantity is
    the largest q such that the q-th highest value >= the q-th lowest cost; the
    maximum extractable surplus is sum_{k<q} (value_sorted[k] - cost_sorted[k])
    over those q intramarginal pairs. This is the theoretical ceiling against
    which realized gains-from-trade are graded (allocative efficiency).
  * Continuous double auction over a period:
      - Repeatedly pick a random ACTIVE trader (a buyer or seller who has not yet
        traded its one unit). That trader submits a quote:
          ZI-C buyer:  bid ~ U(1, value)        (never above its value)
          ZI-C seller: ask ~ U(cost, pmax)       (never below its cost)
          ZI-U buyer:  bid ~ U(1, pmax)          (ignores its value)
          ZI-U seller: ask ~ U(1, pmax)          (ignores its cost)
      - Maintain the standing best bid and best ask. A trade executes when a new
        bid >= the standing best ask (the buyer crosses the seller) OR a new ask
        <= the standing best bid (the seller crosses the buyer). The trade price
        is the STANDING (earlier-posted) quote — the quote that was already in the
        book — matching Gode & Sunder's CDA where an incoming order that crosses
        transacts at the resting order's price.
      - On a trade, the two counterparties are removed (each had one unit), the
        realized surplus (value - cost of the matched pair) is banked, and the
        book (best bid / best ask) is cleared. A non-crossing quote that improves
        the book replaces the standing bid/ask; a non-crossing quote that does not
        improve is discarded (standard CDA price-improvement rule).
      - The period ends after a fixed number of quote attempts or when no further
        trade is possible (no buyer-seller pair can still cross).
  * Multiple periods per round re-draw nothing (values/costs are fixed for the
    round, as in G&S) — fresh random quoting each period lets late trades clean
    up. Efficiency is measured on the realized surplus accumulated over the round.

Allocative efficiency = realized surplus / max competitive surplus, in [0, 1]
(it cannot exceed 1 because no pair trades at a loss under ZI-C; under ZI-U a
loss-making trade is possible, so realized surplus — counted on the TRUE value
and cost of the matched pair — can fall well below the ceiling, even negative for
a single pair, which is exactly the mechanism that erodes ZI-U efficiency).

Built on the neutral platform (``abm_auto._platform``): each trader is a
``TraderAgent`` carrying its private value/cost and budget mode; the
``DoubleAuctionModel`` drives the period over the ``AgentSet`` roster and tallies
the realized surplus. One seeded RNG chain draws the schedules AND every quote, so
a run replays bit-for-bit from a seed. The ONLY difference between the ZI-C and
ZI-U arms is the budget constraint on the quote draw (a FAIR comparison).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class TraderAgent(Agent):
    """One single-unit trader.

    ``side`` is "buyer" or "seller"; ``value`` is the buyer's private redemption
    value (the most it would pay) and ``cost`` is the seller's private cost (the
    least it would accept) — exactly one is meaningful per side. ``traded`` flips
    to True once its one unit changes hands (then the trader is inactive).
    """

    def __init__(self, agent_id: int, model: "DoubleAuctionModel", *, side: str,
                 value: float = 0.0, cost: float = 0.0) -> None:
        super().__init__(agent_id, model)
        if side not in ("buyer", "seller"):
            raise ValueError(f"side must be 'buyer' or 'seller' (got {side!r})")
        self.side = side
        self.value = value          # buyer's redemption value
        self.cost = cost            # seller's cost
        self.traded = False

    def quote(self) -> float:
        """Draw this trader's random bid (buyer) or ask (seller).

        ZI-C respects the budget constraint (buyer bids in [1, value], seller asks
        in [cost, pmax]); ZI-U ignores it (uniform over the whole [1, pmax] price
        range). This single branch is the ONLY behavioural difference between the
        two arms."""
        rng = self.model.rng
        pmax = self.model.pmax
        budget = self.model.budget_constrained
        if self.side == "buyer":
            hi = self.value if budget else pmax
            lo = self.model.pmin
            if hi < lo:
                hi = lo
            return rng.uniform(lo, hi)
        # seller
        lo = self.cost if budget else self.model.pmin
        hi = pmax
        if lo > hi:
            lo = hi
        return rng.uniform(lo, hi)

    def step(self) -> None:  # pragma: no cover - the CDA matches quotes at model level
        """No-op: a trade requires a counterparty, so matching is owned by the
        model's continuous double auction, not an autonomous per-agent step."""
        return None


# -- Model --------------------------------------------------------------------

class DoubleAuctionModel(AgentModel):
    """A continuous double auction over single-unit ZI traders for one round.

    Construct with a buyer-value schedule and a seller-cost schedule (already
    drawn) plus the price range and the budget mode; or use :func:`random_round`
    to draw fresh schedules from a seed. ``run`` plays ``periods`` periods of up to
    ``quotes_per_period`` quote attempts each, banks the realized surplus, and
    returns a summary including the allocative efficiency against the
    competitive-equilibrium ceiling.
    """

    def __init__(self, buyer_values: Sequence[float], seller_costs: Sequence[float],
                 *, budget_constrained: bool = True, pmin: float = 1.0,
                 pmax: float = 200.0, periods: int = 5,
                 quotes_per_period: Optional[int] = None, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.seed_value = seed
        self.budget_constrained = budget_constrained
        self.pmin = pmin
        self.pmax = pmax
        self.periods = periods
        self.buyer_values = list(buyer_values)
        self.seller_costs = list(seller_costs)
        self.m_buyers = len(self.buyer_values)
        self.m_sellers = len(self.seller_costs)
        # Default quote budget: enough attempts that the random walk reliably
        # finds the crossing pairs (scales with the number of traders).
        self.quotes_per_period = (
            quotes_per_period if quotes_per_period is not None
            else 50 * (self.m_buyers + self.m_sellers))

        self.buyers: List[TraderAgent] = []
        self.sellers: List[TraderAgent] = []
        aid = 0
        for v in self.buyer_values:
            a = TraderAgent(aid, self, side="buyer", value=v)
            self.buyers.append(a)
            self.add_agent(a)
            aid += 1
        for c in self.seller_costs:
            a = TraderAgent(aid, self, side="seller", cost=c)
            self.sellers.append(a)
            self.add_agent(a)
            aid += 1

        self.realized_surplus = 0.0
        self.n_trades = 0
        self.trade_log: List[Dict[str, float]] = []
        self.max_surplus, self.eq_quantity = competitive_equilibrium(
            self.buyer_values, self.seller_costs)

        self.reporter = DataCollector({
            "n_trades": lambda m: m.n_trades,
            "realized_surplus": lambda m: m.realized_surplus,
        })

    # -- construction helper --
    @classmethod
    def random_round(cls, m: int, *, budget_constrained: bool = True,
                     pmin: float = 1.0, pmax: float = 200.0, periods: int = 5,
                     quotes_per_period: Optional[int] = None, seed: int = 0
                     ) -> "DoubleAuctionModel":
        """Draw M buyer values and M seller costs i.i.d. ~U(pmin, pmax) from the
        seed, then build the model. The schedule draw uses a dedicated RNG so the
        SAME schedule is produced for a given seed regardless of the budget mode —
        the only thing the mode changes is how quotes are drawn (a FAIR arm)."""
        import random as _random
        draw = _random.Random(seed)
        buyer_values = [draw.uniform(pmin, pmax) for _ in range(m)]
        seller_costs = [draw.uniform(pmin, pmax) for _ in range(m)]
        # Quote RNG is seeded separately (offset) so quoting noise is shared
        # across arms too (same seed -> same quote-draw stream given same book).
        model = cls(buyer_values, seller_costs, budget_constrained=budget_constrained,
                    pmin=pmin, pmax=pmax, periods=periods,
                    quotes_per_period=quotes_per_period, seed=seed + 1)
        return model

    # -- active rosters --
    def active_buyers(self) -> List[TraderAgent]:
        return [b for b in self.buyers if not b.traded]

    def active_sellers(self) -> List[TraderAgent]:
        return [s for s in self.sellers if not s.traded]

    def trade_still_possible(self) -> bool:
        """A trade can still happen iff some active buyer's value >= some active
        seller's cost (otherwise no surplus-feasible pair remains). Under ZI-U a
        trade can still occur between a value<cost pair, so we only use this as a
        FAST-EXIT when no active trader of either side remains."""
        ab = self.active_buyers()
        sa = self.active_sellers()
        if not ab or not sa:
            return False
        return True

    # -- one continuous-double-auction period --
    def run_period(self) -> None:
        """Play one CDA period: repeatedly a random active trader posts a random
        quote; a crossing quote transacts at the standing (resting) price and both
        counterparties leave the market. The standing best bid / best ask form the
        order book; a non-crossing quote that improves the book replaces it."""
        best_bid: Optional[Tuple[float, TraderAgent]] = None   # (price, buyer)
        best_ask: Optional[Tuple[float, TraderAgent]] = None   # (price, seller)
        for _ in range(self.quotes_per_period):
            if not self.trade_still_possible():
                break
            actives = self.active_buyers() + self.active_sellers()
            if not actives:
                break
            trader = self.rng.choice(actives)
            price = trader.quote()
            if trader.side == "buyer":
                # New bid. Does it cross the standing best ask?
                if best_ask is not None and price >= best_ask[0]:
                    # Trade at the standing (resting) ask price.
                    self._execute(trader, best_ask[1], best_ask[0])
                    best_bid = None
                    best_ask = None
                    continue
                # No cross: improve the book if this is the new highest bid.
                if best_bid is None or price > best_bid[0]:
                    best_bid = (price, trader)
            else:
                # New ask. Does it cross the standing best bid?
                if best_bid is not None and price <= best_bid[0]:
                    # Trade at the standing (resting) bid price.
                    self._execute(best_bid[1], trader, best_bid[0])
                    best_bid = None
                    best_ask = None
                    continue
                # No cross: improve the book if this is the new lowest ask.
                if best_ask is None or price < best_ask[0]:
                    best_ask = (price, trader)

    def _execute(self, buyer: TraderAgent, seller: TraderAgent, price: float) -> None:
        """Settle a trade between ``buyer`` and ``seller`` at ``price``. The
        realized surplus is the TRUE gains-from-trade of the matched pair
        (value - cost), independent of the transaction price (which only splits
        the surplus between the two). Under ZI-C value>=bid>=ask>=cost so the pair
        surplus is >= 0; under ZI-U a value<cost pair can match, banking NEGATIVE
        surplus — the mechanism that erodes ZI-U efficiency."""
        buyer.traded = True
        seller.traded = True
        pair_surplus = buyer.value - seller.cost
        self.realized_surplus += pair_surplus
        self.n_trades += 1
        self.trade_log.append({
            "buyer_value": buyer.value, "seller_cost": seller.cost,
            "price": price, "pair_surplus": pair_surplus,
        })

    # -- metrics --
    def efficiency(self) -> float:
        """Allocative efficiency = realized surplus / max competitive surplus.
        Returns 0.0 if the equilibrium surplus is zero (degenerate schedule)."""
        if self.max_surplus <= 0.0:
            return 0.0
        return self.realized_surplus / self.max_surplus

    # -- run --
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Play ``periods`` CDA periods and return the round summary (efficiency,
        realized vs max surplus, trade count, per-trade log)."""
        self.reporter.collect(self)  # t=0 baseline
        for _ in range(self.periods):
            self.run_period()
            self.t += 1
            self.reporter.collect(self)
            if not self.trade_still_possible():
                break
        return {
            "budget_constrained": self.budget_constrained,
            "m_buyers": self.m_buyers,
            "m_sellers": self.m_sellers,
            "pmin": self.pmin,
            "pmax": self.pmax,
            "periods": self.periods,
            "quotes_per_period": self.quotes_per_period,
            "seed": self.seed_value,
            "eq_quantity": self.eq_quantity,
            "max_surplus": self.max_surplus,
            "realized_surplus": self.realized_surplus,
            "n_trades": self.n_trades,
            "efficiency": self.efficiency(),
        }


# -- competitive equilibrium --------------------------------------------------

def competitive_equilibrium(buyer_values: Sequence[float],
                            seller_costs: Sequence[float]) -> Tuple[float, int]:
    """Maximum extractable surplus and equilibrium quantity for single-unit
    schedules.

    Demand = buyer values sorted DESCENDING; supply = seller costs sorted
    ASCENDING. The surplus-maximizing assignment pairs the highest values with the
    lowest costs; the equilibrium quantity q is the number of pairs with
    value >= cost (intramarginal units), and the max surplus is the sum of their
    (value - cost). Returns (max_surplus, q)."""
    demand = sorted(buyer_values, reverse=True)
    supply = sorted(seller_costs)
    q = 0
    surplus = 0.0
    for v, c in zip(demand, supply):
        if v >= c:
            surplus += (v - c)
            q += 1
        else:
            break  # once value < cost, no further pair adds positive surplus
    return surplus, q


# -- metrics / stats helpers --------------------------------------------------

def mean(xs: Sequence[float]) -> float:
    """Arithmetic mean of a series (0.0 if empty)."""
    return (sum(xs) / len(xs)) if xs else 0.0


def variance(xs: Sequence[float]) -> float:
    """Population variance Var(x) = E[x^2] - E[x]^2 of a series."""
    k = len(xs)
    if k == 0:
        return 0.0
    m = sum(xs) / k
    return sum((x - m) ** 2 for x in xs) / k


def std(xs: Sequence[float]) -> float:
    """Population standard deviation."""
    return variance(xs) ** 0.5


# -- run orchestration --------------------------------------------------------

def run_single(m: int, *, budget_constrained: bool = True, pmin: float = 1.0,
               pmax: float = 200.0, periods: int = 5,
               quotes_per_period: Optional[int] = None, seed: int = 0
               ) -> Dict[str, Any]:
    """One ZI round at M traders/side, a given budget mode, and a seed."""
    return DoubleAuctionModel.random_round(
        m, budget_constrained=budget_constrained, pmin=pmin, pmax=pmax,
        periods=periods, quotes_per_period=quotes_per_period, seed=seed).run()


def run_many_seeds(m: int, *, budget_constrained: bool = True, pmin: float = 1.0,
                   pmax: float = 200.0, periods: int = 5,
                   quotes_per_period: Optional[int] = None, n_seeds: int = 20,
                   seed_base: int = 0) -> Dict[str, Any]:
    """Run ``n_seeds`` ZI rounds (seed ``seed_base + i``: fresh value/cost schedule
    AND fresh quoting per seed) for one arm (budget mode) and summarise the LOCKED
    metric (allocative efficiency) across seeds with its mean + spread."""
    runs = [run_single(m, budget_constrained=budget_constrained, pmin=pmin,
                       pmax=pmax, periods=periods,
                       quotes_per_period=quotes_per_period, seed=seed_base + i)
            for i in range(n_seeds)]
    effs = [r["efficiency"] for r in runs]
    return {
        "m": m,
        "budget_constrained": budget_constrained,
        "pmin": pmin,
        "pmax": pmax,
        "periods": periods,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "per_seed_efficiency": effs,
        "per_seed_max_surplus": [r["max_surplus"] for r in runs],
        "per_seed_realized_surplus": [r["realized_surplus"] for r in runs],
        "per_seed_n_trades": [r["n_trades"] for r in runs],
        "per_seed_eq_quantity": [r["eq_quantity"] for r in runs],
        "mean_efficiency": mean(effs),
        "std_efficiency": std(effs),
        "min_efficiency": min(effs),
        "max_efficiency": max(effs),
    }


def compare_arms(m: int, *, pmin: float = 1.0, pmax: float = 200.0, periods: int = 5,
                 quotes_per_period: Optional[int] = None, n_seeds: int = 20,
                 seed_base: int = 0) -> Dict[str, Any]:
    """Run BOTH arms (ZI-C budget-constrained and ZI-U unconstrained) over the SAME
    seeds — so each arm sees the identical value/cost schedules; the only
    difference is the budget constraint on the quote draw (a FAIR comparison).
    Returns both summaries plus the efficiency gap."""
    zi_c = run_many_seeds(m, budget_constrained=True, pmin=pmin, pmax=pmax,
                          periods=periods, quotes_per_period=quotes_per_period,
                          n_seeds=n_seeds, seed_base=seed_base)
    zi_u = run_many_seeds(m, budget_constrained=False, pmin=pmin, pmax=pmax,
                          periods=periods, quotes_per_period=quotes_per_period,
                          n_seeds=n_seeds, seed_base=seed_base)
    return {
        "zi_c": zi_c,
        "zi_u": zi_u,
        "efficiency_gap": zi_c["mean_efficiency"] - zi_u["mean_efficiency"],
    }
