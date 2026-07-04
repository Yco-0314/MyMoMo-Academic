"""Hawk-Dove ESS (Maynard Smith & Price 1973) — a faithful agent-based reproduction.

Source: Maynard Smith, J. & Price, G.R. (1973) "The logic of animal conflict",
Nature 246:15-18. The Hawk-Dove game has a mixed evolutionarily stable strategy
(ESS) when the cost of escalation exceeds the resource value (V < C): a population
fraction p* = V/C plays Hawk at equilibrium.

Rules (the classic cost model, verified against the source):
  * Pairwise contest payoffs for the row player:
        (Hawk, Hawk) = (V - C) / 2     (split the resource, pay the fight cost)
        (Hawk, Dove) = V               (Hawk takes the whole resource)
        (Dove, Hawk) = 0               (Dove yields)
        (Dove, Dove) = V / 2           (share the resource peacefully)
    with V < C (escalation is collectively costly).
  * A well-mixed population of N StrategyAgents, each pure Hawk or pure Dove.
  * Each GENERATION (one tick):
      1. agents are randomly paired (a shuffle, then adjacent pairs play once);
      2. each agent accumulates its contest payoff (its *fitness* this generation);
      3. strategy update by PAYOFF-PROPORTIONAL IMITATION (Schlag 1998 /
         proportional-imitation, the agent-level micro-rule whose mean field is the
         replicator dynamic): every agent meets one random *model* agent and, iff the
         model scored strictly higher, copies the model's strategy with probability
         proportional to the (normalised) payoff gap.
  * Outcome = the steady-state fraction of Hawks. The ESS prediction is p* = V/C.

Why this is genuinely agent-based (no replicator ODE is integrated):
  Each agent holds its OWN discrete strategy and its OWN realised payoff; the update
  reads exactly two agents (self + one random model) and never consults the global
  hawk fraction or an analytic fitness. The well-known result (Helbing 1992; Schlag
  1998) is that proportional imitation's expected change reproduces the replicator
  equation dx/dt = x(1-x)(f_H - f_D), so the population fraction flows to the same
  fixed point p* = V/C — but here that emerges from N interacting agents, it is not
  imposed. Given a seed the whole run is reproducible.

Built on the neutral platform (``abm_auto._platform``): each individual is a
``StrategyAgent`` carrying its discrete strategy + realised payoff; ``HawkDoveModel``
drives the pairings and the imitation update over the ``AgentSet`` roster and records
(via a ``DataCollector``) the per-generation hawk fraction.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from abm_auto._platform import Agent, AgentModel, DataCollector

HAWK = "H"
DOVE = "D"


# -- payoffs ------------------------------------------------------------------

def payoff(strategy: str, opponent: str, *, V: float, C: float) -> float:
    """Row-player contest payoff in the Hawk-Dove cost model.

    (H,H)=(V-C)/2, (H,D)=V, (D,H)=0, (D,D)=V/2. Reads only the two strategies and
    the (V, C) constants — no population state."""
    if strategy == HAWK:
        return (V - C) / 2.0 if opponent == HAWK else V
    # Dove
    return 0.0 if opponent == HAWK else V / 2.0


# -- Agent --------------------------------------------------------------------

class StrategyAgent(Agent):
    """One individual playing a pure strategy (Hawk or Dove).

    ``strategy`` is the discrete heritable trait; ``payoff`` is the fitness realised
    in the current generation (reset and re-accumulated each tick). ``_next_strategy``
    stages the imitation update so the whole generation updates from a consistent
    snapshot (synchronous reproduction — order-independent, hence deterministic given
    the RNG draw sequence)."""

    def __init__(self, agent_id: int, model: "HawkDoveModel", *, strategy: str) -> None:
        super().__init__(agent_id, model)
        self.strategy = strategy
        self.payoff = 0.0
        self._next_strategy = strategy

    def is_hawk(self) -> bool:
        return self.strategy == HAWK

    def step(self) -> None:  # pragma: no cover - generation logic lives on the model
        """The generation (pair -> accumulate payoff -> imitate) is a model-level
        tick over pairs/model-agents, not an autonomous single-agent step, so the
        per-agent ``step`` is intentionally a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class HawkDoveModel(AgentModel):
    """Drives Hawk-Dove evolutionary dynamics by payoff-proportional imitation.

    Construct with N, the game constants (V, C with V < C), the initial hawk fraction
    ``x0``, and a seed. ``run`` iterates generations until the hawk fraction is
    stationary (mean change over a trailing window < ``tol``) or ``max_generations``
    is reached, then returns a summary dict (steady hawk fraction + the per-generation
    hawk-fraction series).
    """

    def __init__(self, n: int = 1000, *, V: float = 2.0, C: float = 4.0,
                 x0: float = 0.5, seed: int = 0,
                 tol: float = 5e-3, settle_window: int = 50,
                 max_generations: int = 5000) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if not (V < C):
            raise ValueError(f"Hawk-Dove ESS needs V < C (got V={V}, C={C})")
        self.seed_value = seed
        self.n = n
        self.V = V
        self.C = C
        self.x0 = x0
        self.tol = tol
        self.settle_window = settle_window
        self.max_generations = max_generations

        # Payoff-proportional imitation needs a normaliser so the copy probability
        # lands in [0, 1]: the widest possible per-game payoff spread. Max single-game
        # payoff is V (Hawk vs Dove); min is min((V-C)/2, 0) (a losing Hawk fight, or
        # a yielding Dove). The realised per-generation payoff is one game, so this
        # bounds the gap. FIXED from (V, C); not tuned.
        self.payoff_span = max(V, 0.0) - min((V - C) / 2.0, 0.0)

        # Seed the population: the first ``round(x0 * n)`` agents are Hawks. (Which
        # specific agents are Hawks is irrelevant in a well-mixed model; the fraction
        # is what matters. Deterministic placement keeps the init seed-independent.)
        self.agent_list: List[StrategyAgent] = []
        n_hawks = int(round(x0 * n))
        for i in range(n):
            strat = HAWK if i < n_hawks else DOVE
            agent = StrategyAgent(i, self, strategy=strat)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({"hawk_fraction": lambda m: m.hawk_fraction()})

    # -- metrics --
    def n_hawks(self) -> int:
        return sum(1 for a in self.agent_list if a.is_hawk())

    def hawk_fraction(self) -> float:
        return self.n_hawks() / self.n if self.n else 0.0

    # -- generation stages --
    def play_round(self) -> None:
        """Random pairing: shuffle the roster, then adjacent agents play one contest
        each. Resets and accumulates each agent's realised payoff this generation.
        An odd agent out (if N is odd) sits out this generation with payoff 0."""
        for a in self.agent_list:
            a.payoff = 0.0
        order = list(self.agent_list)
        self.rng.shuffle(order)
        for k in range(0, len(order) - 1, 2):
            a, b = order[k], order[k + 1]
            a.payoff = payoff(a.strategy, b.strategy, V=self.V, C=self.C)
            b.payoff = payoff(b.strategy, a.strategy, V=self.V, C=self.C)

    def imitate(self) -> None:
        """Payoff-proportional imitation (Schlag 1998). Each agent draws one random
        *model* agent; iff the model scored strictly higher, the agent stages a switch
        to the model's strategy with probability (model.payoff - self.payoff) /
        payoff_span. Staged into ``_next_strategy`` then committed, so the whole
        generation reproduces from one consistent snapshot.

        Reads exactly two agents per update (self + the drawn model) — no global
        hawk-fraction oracle."""
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
        """One generation: pair + accumulate payoffs, then imitate. Record the new
        hawk fraction."""
        self.play_round()
        self.imitate()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def _is_settled(self, series: Sequence[float]) -> bool:
        """Stationary iff the hawk fraction has stopped DRIFTING toward its attractor.

        A finite stochastic population does not freeze at the fixed point; it settles
        into a stationary distribution that keeps fluctuating with O(1/sqrt(N)) noise.
        So the honest convergence test is on the trailing-window MEAN, not the raw
        range: the model is settled when the mean of the last ``settle_window``
        generations differs from the mean of the preceding ``settle_window`` by less
        than ``tol`` (the trend has flattened). Requires two full windows of data."""
        w = self.settle_window
        if len(series) < 2 * w:
            return False
        recent = series[-w:]
        prior = series[-2 * w:-w]
        recent_mean = sum(recent) / w
        prior_mean = sum(prior) / w
        return abs(recent_mean - prior_mean) < self.tol

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate generations until the hawk fraction is stationary (trailing-window
        range < tol) or ``max_generations``; return the run summary."""
        self.reporter.collect(self)              # generation 0 baseline (= x0)
        for _ in range(self.max_generations):
            self.step()
            if self._is_settled(self.reporter.series("hawk_fraction")):
                break
        series = self.reporter.series("hawk_fraction")
        steady = steady_value(series, window=self.settle_window)
        return {
            "n": self.n,
            "V": self.V,
            "C": self.C,
            "x0": self.x0,
            "seed": self.seed_value,
            "ess_p_star": ess_hawk_fraction(self.V, self.C),
            "generations": self.t,
            "settled": self._is_settled(series),
            "steady_hawk_fraction": steady,
            "final_hawk_fraction": series[-1],
            "hawk_fraction_series": series,
        }


# -- analytic + summary helpers ----------------------------------------------

def ess_hawk_fraction(V: float, C: float) -> float:
    """The mixed-ESS Hawk fraction p* = V/C (valid for the cost model with V < C).

    This is the analytic anchor the run is COMPARED against — it is not fed into the
    dynamics (the agents never see it)."""
    return V / C


def steady_value(series: Sequence[float], *, window: int = 50) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of the series (or the
    whole series if shorter). Averaging the tail smooths the residual finite-N
    sampling jitter around the fixed point."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(n: int = 1000, *, V: float = 2.0, C: float = 4.0, x0: float = 0.5,
               seed: int = 0, tol: float = 5e-3, settle_window: int = 50,
               max_generations: int = 5000) -> Dict[str, Any]:
    """One Hawk-Dove evolutionary run at a given seed."""
    return HawkDoveModel(n, V=V, C=C, x0=x0, seed=seed, tol=tol,
                         settle_window=settle_window,
                         max_generations=max_generations).run()


def run_many_seeds(n: int = 1000, *, V: float = 2.0, C: float = 4.0, x0: float = 0.5,
                   n_seeds: int = 10, seed_base: int = 0, tol: float = 5e-3,
                   settle_window: int = 50, max_generations: int = 5000) -> Dict[str, Any]:
    """Run ``n_seeds`` Hawk-Dove runs (seed ``seed_base + i``) at fixed (V, C, x0) and
    summarise the steady hawk fraction across seeds (mean + spread).

    Returns the per-seed steady hawk fractions, their mean and min/max, the ESS anchor
    p* = V/C, and the per-seed generation counts (convergence time).
    """
    runs = [run_single(n, V=V, C=C, x0=x0, seed=seed_base + i, tol=tol,
                       settle_window=settle_window, max_generations=max_generations)
            for i in range(n_seeds)]
    per_seed_steady = [r["steady_hawk_fraction"] for r in runs]
    per_seed_final = [r["final_hawk_fraction"] for r in runs]
    per_seed_gens = [r["generations"] for r in runs]
    mean_steady = sum(per_seed_steady) / n_seeds
    var_steady = sum((s - mean_steady) ** 2 for s in per_seed_steady) / n_seeds
    return {
        "n": n,
        "V": V,
        "C": C,
        "x0": x0,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "ess_p_star": ess_hawk_fraction(V, C),
        "per_seed_steady": per_seed_steady,
        "per_seed_final": per_seed_final,
        "per_seed_generations": per_seed_gens,
        "mean_steady_hawk_fraction": mean_steady,
        "var_steady_hawk_fraction": var_steady,
        "std_steady_hawk_fraction": var_steady ** 0.5,
        "min_steady_hawk_fraction": min(per_seed_steady),
        "max_steady_hawk_fraction": max(per_seed_steady),
        "mean_generations": sum(per_seed_gens) / n_seeds,
        "all_settled": all(r["settled"] for r in runs),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_series": runs[0]["hawk_fraction_series"],
    }
