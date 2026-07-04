"""Minority Game (Challet & Zhang 1997) — a faithful agent-based reproduction.

Source: Challet, D., Zhang, Y.-C. (1997) "Emergence of cooperation and
organization in an evolutionary game", Physica A 246:407-418.
doi:10.1016/S0378-4371(97)00419-6.

Rules (verified against the paper):
  * N agents (odd, default 301). At each round every agent chooses one of two
    sides (action 0 or 1). The side chosen by the MINORITY of agents wins; the
    agents on the winning (minority) side are rewarded.
  * Each agent has a MEMORY of length ``m``: the global "history" is the last
    ``m`` winning sides encoded as an m-bit string, so there are ``P = 2**m``
    distinct histories.
  * Each agent holds ``S`` (default 2) FIXED strategies. A strategy is a random
    lookup table assigning, to every one of the ``P`` possible histories, an
    action in {0, 1}. The tables are drawn once at construction and never change.
  * Each round:
      1. Each agent reads the current history, looks it up in its currently
         best-scoring strategy, and plays that action.
      2. Attendance ``A`` = the number of agents that chose side 1. The MINORITY
         side wins: side 1 wins iff ``A < N/2`` (N odd → no ties), else side 0.
      3. Every strategy of every agent updates its VIRTUAL score by +1 if the
         action THAT strategy WOULD have played for the current history equals the
         winning (minority) side — whether or not the strategy was actually used.
         (This is the defining "minority payoff": a strategy that predicts the
         minority is rewarded.)
      4. The history is updated by prepending the winning side (the m-bit window
         slides: drop the oldest bit, push the newest winning side).
  * Ties in an agent's strategy scores are broken DETERMINISTICALLY (lowest index
    wins), so a run is fully reproducible given a seed.

Control parameter:  α = P / N = 2**m / N.  Sweeping ``m`` at fixed ``N`` (or ``N``
at fixed ``m``) moves α.

Outcome (the LOCKED metric):  volatility  σ²/N = Var(A − N/2) / N  measured over a
post-transient window. ``Var(A − N/2) == Var(A)`` (a constant shift), i.e. the
variance of the attendance about its mean N/2. The coin-flipping random benchmark
gives σ²/N = 1 (Binomial(N, 1/2) variance N/4, and the excess demand 2A−N has
variance N, so Var(2A−N)/N = 1; we report the equivalent on the one-side
attendance scale, Var(A)/(N/4) ... see ``volatility`` for the exact convention).

Determinism / locality: the only global object an agent reads is the public
history string (the shared sequence of past winning sides) — exactly as in the
paper; no agent reads the population attendance directly when choosing. One seeded
RNG chain builds every strategy table and the initial history, so the whole run
replays bit-for-bit from a seed.

Built on the neutral platform (``abm_auto._platform``): each agent is an
``MGAgent`` carrying its fixed strategy tables + virtual scores; ``MinorityGameModel``
drives the rounds over the ``AgentSet`` roster and records (via a ``DataCollector``)
the per-round attendance so the post-transient volatility can be computed.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class MGAgent(Agent):
    """One Minority-Game agent holding ``S`` fixed strategies and their virtual
    scores.

    A strategy is a lookup table: ``table[history_index] -> action (0/1)`` where
    ``history_index`` is the integer value of the m-bit history string. The tables
    are drawn once at construction (from the model RNG) and never change; only the
    integer ``scores`` evolve. The agent's *active* strategy each round is the one
    with the highest score (ties → lowest index)."""

    def __init__(self, agent_id: int, model: "MinorityGameModel", *,
                 strategies: List[List[int]]) -> None:
        super().__init__(agent_id, model)
        self.strategies = strategies            # S tables, each length P (= 2**m)
        self.scores = [0] * len(strategies)     # virtual score per strategy

    def best_strategy_index(self) -> int:
        """Index of the highest-scoring strategy; ties broken to the LOWEST index
        (deterministic)."""
        best_i = 0
        best_score = self.scores[0]
        for i in range(1, len(self.scores)):
            if self.scores[i] > best_score:
                best_score = self.scores[i]
                best_i = i
        return best_i

    def choose(self, history_index: int) -> int:
        """Play the action of the currently best-scoring strategy for the current
        history."""
        return self.strategies[self.best_strategy_index()][history_index]

    def update_scores(self, history_index: int, winning_side: int) -> None:
        """Virtual update: +1 to EVERY strategy that would have played the winning
        (minority) side for the current history — used or not."""
        for i, table in enumerate(self.strategies):
            if table[history_index] == winning_side:
                self.scores[i] += 1

    def step(self) -> None:  # pragma: no cover - MG ticks the whole population at once
        """The Minority Game round couples all agents through the shared
        attendance + history, so a single agent's autonomous ``step`` is a no-op;
        the model's ``step`` (one full round) is the tick."""
        return None


# -- Model --------------------------------------------------------------------

class MinorityGameModel(AgentModel):
    """Drives the Minority Game for a fixed number of rounds.

    Construct with ``n`` (odd), memory length ``m``, strategies per agent ``s``,
    and a seed. ``run`` plays ``transient + rounds`` rounds, records the per-round
    attendance, and returns a summary including the post-transient volatility
    σ²/N (the LOCKED metric)."""

    def __init__(self, n: int = 301, *, m: int = 5, s: int = 2, seed: int = 0,
                 rounds: int = 10_000, transient: int = 1_000) -> None:
        if n % 2 == 0:
            raise ValueError(f"N must be odd (got {n}) so the minority is unambiguous")
        super().__init__(seed=seed, schedule="sequential")
        self.seed_value = seed
        self.n = n
        self.m = m
        self.s = s
        self.rounds = rounds
        self.transient = transient
        self.p = 1 << m                       # number of distinct histories = 2**m

        # Initial history: a random m-bit value (the integer index into the tables).
        self.history_index = self.rng.randrange(self.p)
        self._history_mask = self.p - 1       # keep the low m bits when sliding

        # Build agents with fixed random strategy tables.
        self.agent_list: List[MGAgent] = []
        for i in range(n):
            strategies = [[self.rng.randint(0, 1) for _ in range(self.p)]
                          for _ in range(s)]
            agent = MGAgent(i, self, strategies=strategies)
            self.agent_list.append(agent)
            self.add_agent(agent)

        #: Attendance (count choosing side 1) of the round just committed.
        self.attendance = 0

        self.reporter = DataCollector({
            "attendance": lambda mdl: mdl.attendance,
            "history": lambda mdl: mdl.history_index,
        })

    # -- one Minority Game round --
    def step(self) -> None:
        """One round: every agent chooses via its best strategy; the minority side
        wins; all strategies get the virtual update; the history slides."""
        h = self.history_index
        choices = [agent.choose(h) for agent in self.agent_list]
        attendance = sum(choices)             # number choosing side 1
        # Minority side wins. N odd → attendance != n/2, so this never ties.
        winning_side = 1 if attendance < self.n / 2 else 0

        for agent in self.agent_list:
            agent.update_scores(h, winning_side)

        # Slide the history window: drop the oldest bit, push the winning side as
        # the new low bit. (Encoding direction is a fixed convention; what matters
        # is that all P histories are reachable and agents share one window.)
        self.history_index = ((h << 1) | winning_side) & self._history_mask

        self.attendance = attendance
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Play ``transient + rounds`` rounds; compute σ²/N over the post-transient
        window and return the run summary."""
        total = self.transient + self.rounds
        for _ in range(total):
            self.step()
        att = self.reporter.series("attendance")
        window = att[self.transient:]
        return {
            "n": self.n,
            "m": self.m,
            "s": self.s,
            "seed": self.seed_value,
            "alpha": alpha(self.n, self.m),
            "rounds": self.rounds,
            "transient": self.transient,
            "p": self.p,
            "attendance_window": window,
            "mean_attendance": (sum(window) / len(window)) if window else 0.0,
            "volatility": volatility(window, self.n),
        }


# -- metrics / analytic helpers -----------------------------------------------

def alpha(n: int, m: int) -> float:
    """Control parameter α = P/N = 2**m / N."""
    return (1 << m) / n


def variance(xs: Sequence[float]) -> float:
    """Population variance Var(x) = E[x²] − E[x]² of a series."""
    k = len(xs)
    if k == 0:
        return 0.0
    mean = sum(xs) / k
    return sum((x - mean) ** 2 for x in xs) / k


def volatility(attendance: Sequence[float], n: int) -> float:
    """Volatility σ²/N on the LOCKED convention.

    The "excess demand" is ``D = 2A − N`` (number on side 1 minus number on side
    0), so ``Var(D) = 4·Var(A)`` and the locked metric is

        σ²/N = Var(D) / N = 4·Var(A) / N .

    For coin-flipping random agents A ~ Binomial(N, 1/2), Var(A) = N/4, hence
    σ²/N = 4·(N/4)/N = 1 — the random benchmark. (Equivalently Var(A − N/2)/N
    times 4; the factor-4 is fixed here so the random baseline is exactly 1, the
    convention used throughout Challet & Zhang.)"""
    if not attendance:
        return 0.0
    return 4.0 * variance(attendance) / n


def random_benchmark() -> float:
    """The coin-flipping benchmark σ²/N = 1 (agents choosing each side at random)."""
    return 1.0


# -- run orchestration --------------------------------------------------------

def run_single(n: int = 301, *, m: int = 5, s: int = 2, seed: int = 0,
               rounds: int = 10_000, transient: int = 1_000) -> Dict[str, Any]:
    """One Minority Game run at a given (n, m, s, seed)."""
    return MinorityGameModel(n, m=m, s=s, seed=seed, rounds=rounds,
                             transient=transient).run()


def run_many_seeds(n: int = 301, *, m: int = 5, s: int = 2, n_seeds: int = 10,
                   seed_base: int = 0, rounds: int = 10_000,
                   transient: int = 1_000) -> Dict[str, Any]:
    """Run ``n_seeds`` Minority Game runs (seed ``seed_base + i``) at fixed
    (n, m, s) and summarise σ²/N across seeds.

    Returns the per-seed volatility σ²/N, its mean + min + max (the cross-seed
    spread), the control α = 2**m / N, and the random benchmark for comparison.
    """
    runs = [run_single(n, m=m, s=s, seed=seed_base + i, rounds=rounds,
                       transient=transient)
            for i in range(n_seeds)]
    per_seed_vol = [r["volatility"] for r in runs]
    k = len(per_seed_vol)
    mean_vol = sum(per_seed_vol) / k
    return {
        "n": n,
        "m": m,
        "s": s,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "rounds": rounds,
        "transient": transient,
        "alpha": alpha(n, m),
        "per_seed_volatility": per_seed_vol,
        "mean_volatility": mean_vol,
        "min_volatility": min(per_seed_vol),
        "max_volatility": max(per_seed_vol),
        "std_volatility": variance(per_seed_vol) ** 0.5,
        "random_benchmark": random_benchmark(),
    }


def sweep_alpha(points: Sequence[Tuple[int, int]], *, s: int = 2, n_seeds: int = 10,
                seed_base: int = 0, rounds: int = 10_000,
                transient: int = 1_000) -> List[Dict[str, Any]]:
    """Sweep a list of (n, m) points, returning one ``run_many_seeds`` summary per
    point, sorted by α. Each ``(n, m)`` fixes a control α = 2**m / n; passing
    points with different ``n`` lets the sweep reach α ≥ 2 (e.g. a small-N point)."""
    rows = [run_many_seeds(n, m=m, s=s, n_seeds=n_seeds, seed_base=seed_base,
                           rounds=rounds, transient=transient)
            for (n, m) in points]
    rows.sort(key=lambda r: r["alpha"])
    return rows
