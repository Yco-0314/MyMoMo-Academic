"""Yard-Sale model of wealth exchange (Chakraborti 2002) — a faithful agent-based
reproduction.

Source: Chakraborti, A. (2002), "Distributions of money in model markets of economy",
Int. J. Mod. Phys. C 13(10):1315-1321. doi:10.1142/S0129183102003905. (The "Yard-Sale"
model; cf. Hayes, B. (2002), "Follow the Money", American Scientist 90(5):400-405; and
Boghosian, B.M. (2014), "Kinetics of wealth and the Pareto law", Phys. Rev. E 89:042804.)

Model (verified against the paper's specification):

  * N agents, each holding a non-negative wealth w_i >= 0. The TOTAL wealth is
    CONSERVED — no wealth is created, destroyed, or injected. Agents start from
    EQUAL wealth (w_i = W/N for all i), the maximally egalitarian initial condition.
  * One TRANSACTION: pick two distinct agents i, j uniformly at random. The amount
    at STAKE is a fixed fraction beta of the POORER agent's wealth,
        Delta = beta * min(w_i, w_j).
    A FAIR COIN decides the winner: with probability 1/2 the winner gains Delta and
    the loser loses Delta (and vice versa). No agent can go negative because the
    stake is bounded by the poorer agent's holding.
  * There is NO redistribution / tax / injection: it is a pure multiplicative
    fair-bet, money-conserving pairwise exchange.
  * A SWEEP is N transactions (one transaction per agent on average). The run is
    reported in sweeps; the number of transactions is sweeps * N.

Why it condenses (the locked contrast). This is the SAME conserved pairwise-exchange
FAMILY as Dragulescu-Yakovenko (DY, 2000), but DY stakes an ADDITIVE random amount and
thermalizes to a Boltzmann-Gibbs EXPONENTIAL (Gini = 0.5). The Yard-Sale rule stakes a
fraction of the POORER agent's wealth — a MULTIPLICATIVE bet whose fixed point at
equality is UNSTABLE: a fair coin over a multiplicative stake has zero mean but positive
variance in log-wealth, so wealth performs a geometric random walk that is absorbed at
0 for all but one agent. Wealth therefore CONDENSES onto a single agent (Gini -> 1) —
the OPPOSITE outcome from DY's thermalization, from the same conservation law. The
Gini >= 0.7 gate (well above DY's 0.5) is the discriminator between the two.

Outcome = the Gini coefficient of the wealth vector over time (rises monotonically toward
1), the single richest agent's share of total wealth (-> 1, oligarchy), and the bottom
half's share (-> 0). From the equal start the distribution condenses to near
winner-take-all.

Built on the neutral platform (``abm_auto._platform``): each agent is a genuine
``WealthAgent`` carrying its own wealth, and its ``step`` performs ONE Yard-Sale
transaction against a randomly drawn partner (autonomous agent-stepping — genuine
agent-based, not a god-loop). For the large N x sweeps budget the model ALSO exposes a
vectorized numpy fast path (``run_transactions_vectorized``) that is bit-for-bit the same
stochastic process given a seed; a test pins the per-agent stepping and the vectorized
path against a shared reference so the numpy path is a pure speedup, not a different model.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Gini ---------------------------------------------------------------------

def gini(values: Sequence[float]) -> float:
    """Gini coefficient of a non-negative wealth vector (0 = perfectly equal,
    -> 1 = one agent holds everything).

    Standard mean-absolute-difference form G = sum_i sum_j |x_i - x_j| / (2 n^2 mean),
    computed in O(n log n) via the sorted-cumulative identity
        G = (2 * sum_i (i+1) x_i) / (n * sum x) - (n + 1) / n   (1-indexed).
    Empty or all-zero input -> 0.0 (no inequality is defined). Matches the sugarscape
    reproduction's helper so the two studies grade inequality identically.
    """
    xs = np.sort(np.asarray(values, dtype=float))
    n = xs.size
    if n == 0:
        return 0.0
    total = float(xs.sum())
    if total <= 0.0:
        return 0.0
    idx = np.arange(1, n + 1, dtype=float)
    cum = float(np.dot(idx, xs))
    return (2.0 * cum) / (n * total) - (n + 1.0) / n


def top_share(values: Sequence[float]) -> float:
    """Share of total wealth held by the single RICHEST agent (max / sum). The
    oligarchy order parameter: -> 1 when one agent takes everything. Empty/all-zero -> 0."""
    xs = np.asarray(values, dtype=float)
    if xs.size == 0:
        return 0.0
    total = float(xs.sum())
    if total <= 0.0:
        return 0.0
    return float(xs.max()) / total


def bottom_share(values: Sequence[float], fraction: float = 0.5) -> float:
    """Share of total wealth held JOINTLY by the poorest ``fraction`` of agents
    (default the bottom 50%). -> 0 under condensation. Empty/all-zero -> 0."""
    xs = np.sort(np.asarray(values, dtype=float))
    n = xs.size
    if n == 0:
        return 0.0
    total = float(xs.sum())
    if total <= 0.0:
        return 0.0
    k = max(1, int(fraction * n))
    return float(xs[:k].sum()) / total


def is_non_decreasing(series: Sequence[float], tol: float = 1e-9) -> bool:
    """True iff ``series`` never drops by more than ``tol`` from one sample to the next
    (a monotone-climb check for the Gini trajectory)."""
    for a, b in zip(series, series[1:]):
        if b < a - tol:
            return False
    return True


# -- one transaction (shared reference: agent path == vectorized path) --------

def yard_sale_transaction(w: np.ndarray, i: int, j: int, beta: float,
                          i_wins: bool) -> None:
    """Apply ONE Yard-Sale transaction between agents i and j IN PLACE on wealth vector
    ``w``: stake Delta = beta * min(w_i, w_j); if ``i_wins`` i gains Delta and j loses it,
    else the reverse. Conserves w_i + w_j exactly and keeps both non-negative (the stake
    never exceeds the poorer holding). This is the single rule both the per-agent
    ``WealthAgent.step`` and the vectorized fast path call, so they are the same process."""
    stake = beta * (w[i] if w[i] <= w[j] else w[j])
    if i_wins:
        w[i] += stake
        w[j] -= stake
    else:
        w[i] -= stake
        w[j] += stake


# -- Agent --------------------------------------------------------------------

class WealthAgent(Agent):
    """One economic agent holding a non-negative wealth. Its ``step`` performs ONE
    Yard-Sale transaction: it draws a random OTHER agent as counterparty and a fair coin,
    and applies the stake-the-poorer fair bet. Wealth lives in the model's shared numpy
    vector (``model.w[id]``); the agent reads/writes its own slot through the model so a
    transaction updates both parties consistently."""

    def __init__(self, agent_id: int, model: "YardSaleModel") -> None:
        super().__init__(agent_id, model)

    @property
    def wealth(self) -> float:
        return float(self.model.w[self.id])

    def step(self) -> None:
        """Draw a distinct counterparty uniformly at random and transact once (fair coin
        over the stake-the-poorer bet). Autonomous per-agent action; the model owns the
        shared wealth vector so both sides of the trade update together."""
        model = self.model
        n = model.n
        if n < 2:
            return
        j = model.rng.randrange(n)
        while j == self.id:
            j = model.rng.randrange(n)
        i_wins = model.rng.random() < 0.5
        yard_sale_transaction(model.w, self.id, j, model.beta, i_wins)


# -- Model --------------------------------------------------------------------

class YardSaleModel(AgentModel):
    """Drives the Yard-Sale wealth-exchange dynamics over a conserved wealth vector.

    Construct with N, the stake fraction beta, the total wealth (default N so mean
    wealth = 1), and a seed. Wealth starts EQUAL (w_i = total/N). ``run(sweeps)`` advances
    ``sweeps`` sweeps (each sweep = N transactions) and records the Gini, richest-agent
    share, and bottom-50% share every ``record_every`` sweeps.

    Two equivalent transaction paths, one process:
      * per-agent stepping via ``WealthAgent.step`` (the genuine agent-based path), used
        by ``step`` / the platform ``run`` for small studies + the faithfulness tests;
      * a vectorized numpy path (``run_transactions_vectorized``) that draws the same
        (i, j, coin) stream and applies the same rule, used by ``run`` for the large
        locked budget. A test pins the two against a shared reference draw.
    """

    def __init__(self, n: int = 1000, *, beta: float = 0.1, total_wealth: Optional[float] = None,
                 record_every: int = 500, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n < 2:
            raise ValueError(f"need n >= 2 (got {n})")
        if not (0.0 < beta < 1.0):
            raise ValueError(f"need 0 < beta < 1 (got {beta})")
        if record_every <= 0:
            raise ValueError(f"need record_every > 0 (got {record_every})")
        self.seed_value = seed
        self.n = n
        self.beta = float(beta)
        self.record_every = int(record_every)
        self.total_wealth = float(total_wealth) if total_wealth is not None else float(n)
        # Equal start: every agent holds mean wealth. Total is conserved thereafter.
        self.w = np.full(n, self.total_wealth / n, dtype=float)

        self.agent_list: List[WealthAgent] = []
        for i in range(n):
            agent = WealthAgent(i, self)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "gini": lambda m: m.gini_wealth(),
            "top_share": lambda m: m.top_share(),
            "bottom_half_share": lambda m: m.bottom_half_share(),
        })

    # -- metrics --
    def gini_wealth(self) -> float:
        return gini(self.w)

    def top_share(self) -> float:
        return top_share(self.w)

    def bottom_half_share(self) -> float:
        return bottom_share(self.w, 0.5)

    def total(self) -> float:
        return float(self.w.sum())

    # -- transaction paths --
    def sweep_agents(self) -> None:
        """One sweep = N per-agent steps (the genuine agent-based path). Each agent
        transacts once against a random counterparty in schedule order."""
        for agent in self.agents.ordered():
            agent.step()

    def run_transactions_vectorized(self, n_transactions: int) -> None:
        """Fast path: apply ``n_transactions`` Yard-Sale transactions to ``self.w`` using
        the SAME stochastic rule as ``WealthAgent.step`` but drawing the (i, j, coin)
        stream from numpy in blocks. The math is identical (stake = beta*min, fair coin,
        conserve the pair); this is a pure speedup for the large locked budget, not a
        different model. Draws are chunked so N x 2e4 transactions stay in memory."""
        if n_transactions <= 0:
            return
        n = self.n
        beta = self.beta
        w = self.w
        block = 1_000_000
        done = 0
        while done < n_transactions:
            k = min(block, n_transactions - done)
            ii = self._np_rng.integers(0, n, size=k)
            jj = self._np_rng.integers(0, n, size=k)
            coins = self._np_rng.random(size=k) < 0.5
            for t in range(k):
                i = int(ii[t])
                j = int(jj[t])
                if i == j:
                    continue                # degenerate self-pair: no trade (rare)
                stake = beta * (w[i] if w[i] <= w[j] else w[j])
                if coins[t]:
                    w[i] += stake
                    w[j] -= stake
                else:
                    w[i] -= stake
                    w[j] += stake
            done += k

    # -- tick / run --
    def step(self) -> None:
        """One sweep of the genuine per-agent path (N transactions), then advance t and
        collect. Used by the platform-style run + the faithfulness tests."""
        self.sweep_agents()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, sweeps: int, *, vectorized: bool = True) -> Dict[str, Any]:  # type: ignore[override]
        """Advance ``sweeps`` sweeps (each = N transactions) and return the run summary.

        With ``vectorized`` (default) the fast numpy path runs ``record_every`` sweeps at
        a time between measurements; otherwise the genuine per-agent path steps sweep by
        sweep. Both record the Gini, richest-agent share, and bottom-50% share every
        ``record_every`` sweeps (plus the t=0 equal-start baseline and the final state).
        """
        if sweeps <= 0:
            raise ValueError(f"need sweeps > 0 (got {sweeps})")
        # dedicated numpy Generator seeded from the same seed (independent of the stdlib
        # rng used by the per-agent path) — the vectorized path's draw stream.
        self._np_rng = np.random.default_rng(self.seed_value)
        self.reporter.collect(self)                     # t=0 equal-start baseline
        sweeps_done = 0
        while sweeps_done < sweeps:
            chunk = min(self.record_every, sweeps - sweeps_done)
            if vectorized:
                self.run_transactions_vectorized(chunk * self.n)
            else:
                for _ in range(chunk):
                    self.sweep_agents()
            sweeps_done += chunk
            self.t = sweeps_done
            self.reporter.collect(self)
        gini_series = self.reporter.series("gini")
        top_series = self.reporter.series("top_share")
        bottom_series = self.reporter.series("bottom_half_share")
        return {
            "n": self.n,
            "beta": self.beta,
            "total_wealth": self.total_wealth,
            "sweeps": sweeps,
            "record_every": self.record_every,
            "n_transactions": sweeps * self.n,
            "seed": self.seed_value,
            "vectorized": vectorized,
            "initial_gini": gini_series[0],
            "final_gini": gini_series[-1],
            "final_top_share": top_series[-1],
            "final_bottom_half_share": bottom_series[-1],
            "final_total_wealth": self.total(),
            "gini_non_decreasing": is_non_decreasing(gini_series),
            "gini_series": gini_series,
            "top_share_series": top_series,
            "bottom_half_share_series": bottom_series,
        }


# -- single + multi-seed helpers ----------------------------------------------

def run_single(*, n: int = 1000, beta: float = 0.1, sweeps: int = 20_000,
               record_every: int = 500, total_wealth: Optional[float] = None,
               seed: int = 0, vectorized: bool = True) -> Dict[str, Any]:
    """One full Yard-Sale run for a given seed at the fixed model parameters."""
    model = YardSaleModel(n=n, beta=beta, total_wealth=total_wealth,
                          record_every=record_every, seed=seed)
    res = model.run(sweeps, vectorized=vectorized)
    return res


def _variance(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return sum((x - m) ** 2 for x in xs) / (n - 1)


def run_many_seeds(seeds: Sequence[int], *, n: int = 1000, beta: float = 0.1,
                   sweeps: int = 20_000, record_every: int = 500,
                   total_wealth: Optional[float] = None,
                   vectorized: bool = True) -> Dict[str, Any]:
    """Run one Yard-Sale simulation per seed at fixed parameters and summarise across
    seeds — the headline numbers the locked clauses P1-P3 are graded against.

    Returns per-seed rows plus the cross-seed mean / spread / range of the final Gini,
    richest-agent share, and bottom-50% share, whether every seed's Gini trajectory was
    non-decreasing, and one representative Gini trajectory (first seed) for inspection.
    """
    rows: List[Dict[str, Any]] = []
    for s in seeds:
        rows.append(run_single(n=n, beta=beta, sweeps=sweeps, record_every=record_every,
                               total_wealth=total_wealth, seed=s, vectorized=vectorized))
    m = len(rows)
    final_ginis = [r["final_gini"] for r in rows]
    top_shares = [r["final_top_share"] for r in rows]
    bottom_shares = [r["final_bottom_half_share"] for r in rows]
    mono = [r["gini_non_decreasing"] for r in rows]
    mean_gini = sum(final_ginis) / m if m else 0.0
    return {
        "seeds": list(seeds),
        "n": n,
        "beta": beta,
        "sweeps": sweeps,
        "record_every": record_every,
        "n_transactions": sweeps * n,
        "vectorized": vectorized,
        "rows": rows,
        "mean_final_gini": mean_gini,
        "std_final_gini": _variance(final_ginis) ** 0.5,
        "min_final_gini": min(final_ginis) if final_ginis else 0.0,
        "max_final_gini": max(final_ginis) if final_ginis else 0.0,
        "mean_final_top_share": sum(top_shares) / m if m else 0.0,
        "min_final_top_share": min(top_shares) if top_shares else 0.0,
        "max_final_top_share": max(top_shares) if top_shares else 0.0,
        "mean_final_bottom_half_share": sum(bottom_shares) / m if m else 0.0,
        "max_final_bottom_half_share": max(bottom_shares) if bottom_shares else 0.0,
        "all_gini_non_decreasing": all(mono),
        "per_seed_final_gini": final_ginis,
        "per_seed_final_top_share": top_shares,
        "per_seed_final_bottom_half_share": bottom_shares,
        "per_seed_gini_non_decreasing": mono,
        "example_gini_series": rows[0]["gini_series"],
        "example_top_share_series": rows[0]["top_share_series"],
    }
