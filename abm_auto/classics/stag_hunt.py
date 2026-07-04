"""Stag Hunt coordination game (Skyrms 2004; Maynard Smith lineage) — a faithful
agent-based reproduction.

Source: Skyrms, B. (2004) *The Stag Hunt and the Evolution of Social Structure*,
Cambridge University Press. The stag hunt is the canonical coordination game: two
hunters each choose to hunt Stag (S) — which requires the OTHER to cooperate — or the
safe solitary Hare (H). Its evolutionary signature is BISTABILITY: two strict pure
evolutionarily stable strategies, all-Stag (payoff-dominant) and all-Hare (risk-
dominant), separated by an UNSTABLE interior fixed point. Which equilibrium a population
reaches is a basin-of-attraction question, not a mixing question.

Rules (the classic symmetric 2x2 coordination payoffs, R>T>P>S_):
  * Pairwise contest payoffs for the row player:
        (Stag, Stag) = R      (both hunt the stag: the payoff-dominant reward)
        (Stag, Hare) = S_     (you went for the stag, partner defected: the sucker payoff)
        (Hare, Stag) = T      (you took the safe hare while partner chased the stag)
        (Hare, Hare) = P      (both took the hare: the safe, risk-dominant outcome)
    with **R > T > P > S_** (stag-stag is best; hare is safe; being the lone stag-hunter
    is worst). This ordering makes BOTH (S,S) and (H,H) strict Nash / pure ESS, with an
    unstable interior mixed point.
  * A well-mixed population of N StrategyAgents, each pure Stag or pure Hare.
  * Each GENERATION (one tick):
      1. agents are randomly paired (a shuffle, then adjacent pairs play once);
      2. each agent accumulates its contest payoff (its *fitness* this generation);
      3. strategy update by PAYOFF-PROPORTIONAL IMITATION (Schlag 1998 /
         proportional-imitation, the agent-level micro-rule whose mean field is the
         replicator dynamic): every agent meets one random *model* agent and, iff the
         model scored strictly higher, copies the model's strategy with probability
         proportional to the (normalised) payoff gap.
  * Outcome = the fixation state. From a start x0 below the interior fixed point the
    population flows to ALL-HARE; from x0 above it, to ALL-STAG.

The analytic anchor (COMPARED against, never fed into the dynamics):
  Interior unstable fixed point x* = (P - S_) / ((R - T) + (P - S_)), the fraction of
  Stag at which the expected payoffs of Stag and Hare are equal. It is the SEPARATRIX of
  the two basins: x0 > x* -> all-Stag, x0 < x* -> all-Hare. Because the risk-dominant
  Hare strategy has the larger basin whenever x* > 1/2 (which holds for the canonical
  payoffs, x*=0.667), a uniformly random x0 fixates on Hare with probability x* and on
  Stag with probability 1 - x*.

Why this is genuinely agent-based (no replicator ODE is integrated):
  Each agent holds its OWN discrete strategy and its OWN realised payoff; the update
  reads exactly two agents (self + one random model) and never consults the global stag
  fraction or an analytic fitness. The well-known result (Helbing 1992; Schlag 1998) is
  that proportional imitation's expected change reproduces the replicator equation
  dx/dt = x(1-x)(f_S - f_H), so a finite population flows to whichever pure ESS owns the
  basin containing x0 — but here that fixation EMERGES from N interacting agents, it is
  not imposed. Given a seed the whole run is reproducible.

Distinctness from Hawk-Dove (same platform, opposite geometry): Hawk-Dove has a single
STABLE interior mixed ESS p*=V/C where both strategies coexist forever; the stag hunt's
interior point is UNSTABLE and the population always fixates on ONE pure strategy. A
Hawk-Dove rerun converges to its interior mix; a stag-hunt rerun never does.

Built on the neutral platform (``abm_auto._platform``): each individual is a
``StrategyAgent`` carrying its discrete strategy + realised payoff; ``StagHuntModel``
drives the pairings and the imitation update over the roster and records (via a
``DataCollector``) the per-generation stag fraction.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from abm_auto._platform import Agent, AgentModel, DataCollector

STAG = "S"
HARE = "H"


# -- payoffs ------------------------------------------------------------------

def payoff(strategy: str, opponent: str, *, R: float, T: float, P: float, S_: float) -> float:
    """Row-player contest payoff in the symmetric stag-hunt coordination game.

    (S,S)=R, (S,H)=S_, (H,S)=T, (H,H)=P, with R>T>P>S_. Reads only the two strategies
    and the payoff constants — no population state."""
    if strategy == STAG:
        return R if opponent == STAG else S_
    # Hare
    return T if opponent == STAG else P


# -- Agent --------------------------------------------------------------------

class StrategyAgent(Agent):
    """One hunter playing a pure strategy (Stag or Hare).

    ``strategy`` is the discrete heritable trait; ``payoff`` is the fitness realised in
    the current generation (reset and re-accumulated each tick). ``_next_strategy``
    stages the imitation update so the whole generation updates from a consistent
    snapshot (synchronous reproduction)."""

    def __init__(self, agent_id: int, model: "StagHuntModel", *, strategy: str) -> None:
        super().__init__(agent_id, model)
        self.strategy = strategy
        self.payoff = 0.0
        self._next_strategy = strategy

    def is_stag(self) -> bool:
        return self.strategy == STAG

    def step(self) -> None:  # pragma: no cover - generation logic lives on the model
        """The generation (pair -> accumulate payoff -> imitate) is a model-level tick
        over pairs/model-agents, not an autonomous single-agent step, so the per-agent
        ``step`` is intentionally a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class StagHuntModel(AgentModel):
    """Drives stag-hunt evolutionary dynamics by payoff-proportional imitation.

    Construct with N, the payoff constants (R>T>P>S_), the initial stag fraction ``x0``,
    and a seed. ``run`` iterates generations until the population FIXATES (the stag
    fraction hits 0 or 1, the two absorbing pure states) or the fraction is stationary /
    ``max_generations`` is reached, then returns a summary dict.
    """

    def __init__(self, n: int = 1000, *, R: float = 4.0, T: float = 3.0,
                 P: float = 2.0, S_: float = 0.0, x0: float = 0.5, seed: int = 0,
                 tol: float = 5e-3, settle_window: int = 50,
                 max_generations: int = 5000) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if not (R > T > P > S_):
            raise ValueError(
                f"stag hunt needs R>T>P>S_ (got R={R}, T={T}, P={P}, S_={S_})")
        self.seed_value = seed
        self.n = n
        self.R = R
        self.T = T
        self.P = P
        self.S_ = S_
        self.x0 = x0
        self.tol = tol
        self.settle_window = settle_window
        self.max_generations = max_generations

        # Payoff-proportional imitation needs a normaliser so the copy probability lands
        # in [0, 1]: the widest possible per-game payoff spread. Max single-game payoff
        # is R (best); min is S_ (worst). The realised per-generation payoff is one game,
        # so this bounds the gap. FIXED from the payoff constants; not tuned.
        self.payoff_span = R - S_

        # Seed the population: the first ``round(x0 * n)`` agents are Stag hunters. (Which
        # specific agents are Stag is irrelevant in a well-mixed model; the fraction is
        # what matters. Deterministic placement keeps init seed-independent.)
        self.agent_list: List[StrategyAgent] = []
        n_stags = int(round(x0 * n))
        for i in range(n):
            strat = STAG if i < n_stags else HARE
            agent = StrategyAgent(i, self, strategy=strat)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({"stag_fraction": lambda m: m.stag_fraction()})

    # -- metrics --
    def n_stags(self) -> int:
        return sum(1 for a in self.agent_list if a.is_stag())

    def stag_fraction(self) -> float:
        return self.n_stags() / self.n if self.n else 0.0

    def is_fixated(self) -> bool:
        """True once the population is entirely Stag or entirely Hare (an absorbing
        state under imitation: with no strategy diversity nobody has a strictly-better
        model to copy, so the population never leaves)."""
        s = self.n_stags()
        return s == 0 or s == self.n

    # -- generation stages --
    def play_round(self) -> None:
        """Random pairing: shuffle the roster, then adjacent agents play one contest
        each. Resets and accumulates each agent's realised payoff this generation. An
        odd agent out (if N is odd) sits out this generation with payoff 0."""
        for a in self.agent_list:
            a.payoff = 0.0
        order = list(self.agent_list)
        self.rng.shuffle(order)
        for k in range(0, len(order) - 1, 2):
            a, b = order[k], order[k + 1]
            a.payoff = payoff(a.strategy, b.strategy, R=self.R, T=self.T, P=self.P, S_=self.S_)
            b.payoff = payoff(b.strategy, a.strategy, R=self.R, T=self.T, P=self.P, S_=self.S_)

    def imitate(self) -> None:
        """Payoff-proportional imitation (Schlag 1998). Each agent draws one random
        *model* agent; iff the model scored strictly higher, the agent stages a switch to
        the model's strategy with probability (model.payoff - self.payoff) / payoff_span.
        Staged into ``_next_strategy`` then committed, so the whole generation reproduces
        from one consistent snapshot.

        Reads exactly two agents per update (self + the drawn model) — no global
        stag-fraction oracle."""
        for a in self.agent_list:
            a._next_strategy = a.strategy
        span = self.payoff_span if self.payoff_span > 0 else 1.0
        for a in self.agent_list:
            j = self.rng.randrange(self.n)
            while j == a.id:
                j = self.rng.randrange(self.n)
            model_agent = self.agent_list[j]
            gap = model_agent.payoff - a.payoff
            if gap > 0.0:
                p_switch = gap / span
                if self.rng.random() < p_switch:
                    a._next_strategy = model_agent.strategy
        for a in self.agent_list:
            a.strategy = a._next_strategy

    # -- tick (one generation) --
    def step(self) -> None:
        """One generation: pair + accumulate payoffs, then imitate. Record the new stag
        fraction."""
        self.play_round()
        self.imitate()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def _is_settled(self, series: Sequence[float]) -> bool:
        """Stationary iff the stag fraction has stopped drifting. A finite stochastic
        population settles into a stationary regime; the honest convergence test is on
        the trailing-window MEAN, not the raw range: settled when the mean of the last
        ``settle_window`` generations differs from the mean of the preceding
        ``settle_window`` by less than ``tol``. Requires two full windows of data."""
        w = self.settle_window
        if len(series) < 2 * w:
            return False
        recent = series[-w:]
        prior = series[-2 * w:-w]
        recent_mean = sum(recent) / w
        prior_mean = sum(prior) / w
        return abs(recent_mean - prior_mean) < self.tol

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate generations until the population FIXATES (0 or 1 — the natural
        stopping point for the bistable dynamics), or the stag fraction is stationary,
        or ``max_generations``; return the run summary (which pure ESS it reached)."""
        self.reporter.collect(self)              # generation 0 baseline (= x0)
        for _ in range(self.max_generations):
            self.step()
            if self.is_fixated():
                break
            if self._is_settled(self.reporter.series("stag_fraction")):
                break
        series = self.reporter.series("stag_fraction")
        steady = steady_value(series, window=self.settle_window)
        final = series[-1]
        # Classify the fixation outcome. A finite run may stop just shy of 0/1 if it
        # settled; classify by which pure state the tail is closest to.
        if final >= 0.5:
            fixed_on = STAG
        else:
            fixed_on = HARE
        return {
            "n": self.n,
            "R": self.R, "T": self.T, "P": self.P, "S_": self.S_,
            "x0": self.x0,
            "seed": self.seed_value,
            "interior_fixed_point": interior_fixed_point(self.R, self.T, self.P, self.S_),
            "generations": self.t,
            "fixated": self.is_fixated(),
            "settled": self._is_settled(series),
            "fixed_on": fixed_on,
            "fixed_on_stag": fixed_on == STAG,
            "steady_stag_fraction": steady,
            "final_stag_fraction": final,
            "stag_fraction_series": series,
        }


# -- analytic + summary helpers ----------------------------------------------

def interior_fixed_point(R: float, T: float, P: float, S_: float) -> float:
    """The unstable interior fixed point x* = (P - S_) / ((R - T) + (P - S_)), the
    fraction of Stag at which Stag and Hare have equal expected payoff.

    This is the SEPARATRIX of the two basins and the analytic anchor the run is COMPARED
    against — it is never fed into the dynamics (the agents never see it). It is also the
    probability that a uniformly random x0 lands in the Hare basin, so it doubles as the
    predicted P(fixate Hare)."""
    denom = (R - T) + (P - S_)
    return (P - S_) / denom if denom != 0 else 0.5


def steady_value(series: Sequence[float], *, window: int = 50) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of the series (or the
    whole series if shorter). Averaging the tail smooths residual sampling jitter (for a
    fixated run the tail is a constant 0 or 1)."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(n: int = 1000, *, R: float = 4.0, T: float = 3.0, P: float = 2.0,
               S_: float = 0.0, x0: float = 0.5, seed: int = 0, tol: float = 5e-3,
               settle_window: int = 50, max_generations: int = 5000) -> Dict[str, Any]:
    """One stag-hunt evolutionary run at a given seed and initial stag fraction."""
    return StagHuntModel(n, R=R, T=T, P=P, S_=S_, x0=x0, seed=seed, tol=tol,
                         settle_window=settle_window,
                         max_generations=max_generations).run()


def run_basin(n: int = 1000, *, R: float = 4.0, T: float = 3.0, P: float = 2.0,
              S_: float = 0.0, n_replicates: int = 500, seed_base: int = 0,
              tol: float = 5e-3, settle_window: int = 50,
              max_generations: int = 5000) -> Dict[str, Any]:
    """Basin-of-attraction sweep: ``n_replicates`` runs, each with a fresh x0 drawn
    uniformly on (0,1) (replicate ``i`` uses seed ``seed_base + i`` for BOTH the x0 draw
    and the dynamics), at fixed payoffs. Summarises the fixation outcomes.

    Returns P(fixate Stag), P(fixate Hare), the empirical basin threshold x*_emp (the
    largest x0 that fixated on Hare / the smallest that fixated on Stag, i.e. the
    crossover), the per-replicate outcomes, and the analytic anchor x*.
    """
    import random as _random

    x0s: List[float] = []
    outcomes: List[bool] = []          # True = fixated on Stag
    fixated_flags: List[bool] = []
    for i in range(n_replicates):
        draw_rng = _random.Random(seed_base + i)
        x0 = draw_rng.uniform(0.0, 1.0)
        res = run_single(n, R=R, T=T, P=P, S_=S_, x0=x0, seed=seed_base + i, tol=tol,
                         settle_window=settle_window, max_generations=max_generations)
        x0s.append(x0)
        outcomes.append(res["fixed_on_stag"])
        fixated_flags.append(res["fixated"])

    n_stag = sum(1 for o in outcomes if o)
    n_hare = n_replicates - n_stag
    p_stag = n_stag / n_replicates
    p_hare = n_hare / n_replicates

    # Empirical separatrix: the crossover between the Hare-basin and Stag-basin starts.
    # highest x0 that still fixated on Hare, and lowest x0 that fixated on Stag; the
    # threshold is their midpoint (a monotone basin would have all-Hare below and
    # all-Stag above a single x*).
    hare_x0s = [x for x, o in zip(x0s, outcomes) if not o]
    stag_x0s = [x for x, o in zip(x0s, outcomes) if o]
    if hare_x0s and stag_x0s:
        x_star_emp = (max(hare_x0s) + min(stag_x0s)) / 2.0
    elif hare_x0s:            # everything fixated Hare
        x_star_emp = 1.0
    else:                     # everything fixated Stag
        x_star_emp = 0.0

    return {
        "n": n,
        "R": R, "T": T, "P": P, "S_": S_,
        "n_replicates": n_replicates,
        "seed_base": seed_base,
        "interior_fixed_point": interior_fixed_point(R, T, P, S_),
        "p_fixate_stag": p_stag,
        "p_fixate_hare": p_hare,
        "n_fixate_stag": n_stag,
        "n_fixate_hare": n_hare,
        "x_star_emp": x_star_emp,
        "all_fixated": all(fixated_flags),
        "frac_fixated": sum(fixated_flags) / n_replicates,
        "x0s": x0s,
        "outcomes_stag": outcomes,
    }


def run_threshold(n: int = 1000, *, R: float = 4.0, T: float = 3.0, P: float = 2.0,
                  S_: float = 0.0, x0_grid: Sequence[float] = tuple(i / 20 for i in range(1, 20)),
                  seed_base: int = 0, tol: float = 5e-3, settle_window: int = 50,
                  max_generations: int = 5000) -> Dict[str, Any]:
    """Measure the empirical basin threshold for a fixed payoff set by sweeping a grid of
    initial stag fractions x0 (one deterministic run per x0) and locating the crossover
    from Hare-fixation to Stag-fixation.

    x*_emp = midpoint between the highest x0 that fixated on Hare and the lowest x0 that
    fixated on Stag. Used by P3 (does the threshold TRACK the payoff formula?).
    """
    x0s = list(x0_grid)
    outcomes: List[bool] = []   # True = fixated on Stag
    for i, x0 in enumerate(x0s):
        res = run_single(n, R=R, T=T, P=P, S_=S_, x0=x0, seed=seed_base + i, tol=tol,
                         settle_window=settle_window, max_generations=max_generations)
        outcomes.append(res["fixed_on_stag"])

    hare_x0s = [x for x, o in zip(x0s, outcomes) if not o]
    stag_x0s = [x for x, o in zip(x0s, outcomes) if o]
    if hare_x0s and stag_x0s:
        x_star_emp = (max(hare_x0s) + min(stag_x0s)) / 2.0
    elif hare_x0s:
        x_star_emp = 1.0
    else:
        x_star_emp = 0.0

    return {
        "n": n,
        "R": R, "T": T, "P": P, "S_": S_,
        "interior_fixed_point": interior_fixed_point(R, T, P, S_),
        "x0_grid": x0s,
        "outcomes_stag": outcomes,
        "x_star_emp": x_star_emp,
        "highest_hare_x0": max(hare_x0s) if hare_x0s else None,
        "lowest_stag_x0": min(stag_x0s) if stag_x0s else None,
    }
