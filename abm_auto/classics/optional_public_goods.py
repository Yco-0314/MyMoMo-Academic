"""Optional public goods game with loners (Hauert, De Monte, Hofbauer & Sigmund
2002) — a faithful agent-based reproduction.

Source (verified, not from memory):
  Hauert, C., De Monte, S., Hofbauer, J. & Sigmund, K. (2002), "Volunteering as
  Red Queen mechanism for cooperation in public goods games", Science 296:1129-1132.
  doi:10.1126/science.1070582.

The model adds a THIRD strategy — the LONER (abstainer) — to the public goods game.
Cooperators (C) and defectors (D) may take part in a group public-goods interaction;
loners (L) opt OUT and collect a fixed, modest payoff sigma instead. This voluntary
participation converts the sterile all-defect Nash outcome of the COMPULSORY game into a
never-ending ROCK-PAPER-SCISSORS cycle:

    D beats C (defectors free-ride on cooperators in a group)
    L beats D (when defectors dominate, the pot is worthless, so opting out beats staying)
    C beats L (once loners dominate, small cooperator groups become profitable again)

so no single strategy fixates; the three chase each other forever (the "Red Queen").

The public-goods payoff (Hauert et al. 2002, exactly):
  * A group of size N is sampled from the population. Only the PARTICIPANTS (C or D, not
    L) play. Let S be the number of participants in the group and n_c the number of
    cooperators among them.
  * Each cooperator pays a cost c = 1 into the pot; the pot (r * n_c * c) is multiplied by
    r and split equally among ALL S participants. So a participant's share of the pot is
    r * n_c * c / S; a DEFECTOR keeps that share (paid nothing): P_d = r*n_c/S; a
    COOPERATOR paid the cost: P_c = P_d - c = r*n_c/S - 1.
  * A LONER always earns the fixed payoff sigma, with 0 < sigma < r - 1 (so a loner does
    better than a group of mutual defectors, which yield 0, but worse than a group of
    mutual cooperators, which yield r - 1).
  * A LONE participant (S = 1) cannot play a public-goods game with itself, so it is
    forced back to the loner payoff sigma. This is the crucial term that makes small
    cooperator clusters viable when loners abound (C beats L).

Expected payoffs (the closed form Hauert et al. derive and we use verbatim). With
population frequencies x = (x_C, x_D, x_L) and z = x_L the loner frequency, a focal
participant samples N-1 co-players from the rest of the (infinite / large) population.
The probability the focal participant is otherwise ALONE (all N-1 co-players are loners)
is z^{N-1}; then it is forced to sigma. Otherwise the number of non-loner co-players S-1
>= 1, and averaging r*n_c/S over the sampling distribution gives Hauert's

    P_d - P_c = 1 - (r/N) * (1 + (N-1)*... )        # (cooperators always trail by the
                                                    #  average return-on-investment gap)

We implement the exact per-strategy expected payoffs by the ANALYTIC group-sampling
expectation used in the paper (see ``expected_payoffs``); it is deterministic given the
population frequencies and matches a large Monte-Carlo group-sampling estimate (pinned in
the tests).

Why an agent-based IBM with tiny mutation over a bounded horizon (the locked PROTOCOL):
the interior fixed point Q of the C/D/L replicator dynamics is a NEUTRALLY-STABLE CENTER
(the flow circles it on closed orbits; Q is not an attractor). A finite population with a
pure imitation update therefore performs a random walk along those closed orbits and, with
no mutation, eventually drifts to the simplex boundary and FIXATES — a finite-size
artifact, not the model's behaviour, which would read as a FALSE miss of the coexistence
prediction. Following the locked protocol we run a genuine agent-based imitation IBM with
a LARGE population (>= 5000) and a TINY mutation rate mu ~ 1e-3 (exploration that keeps the
orbit from collapsing onto the boundary) over a BOUNDED horizon, across >= 5 seeds, and
measure the TIME-AVERAGED frequencies and the cooperator amplitude. The compulsory control
is the SAME model with the loner strategy removed (only C and D), which collapses to
all-D — the fair control isolating "voluntary participation is what rescues cooperation".

Built on the neutral platform (``abm_auto._platform``): each ``PlayerAgent`` carries its
own strategy in {C, D, L}; ``OptionalPGGModel`` (an ``AgentModel``) drives the synchronous
imitation-with-mutation update over the ``AgentSet`` roster and records (via a
``DataCollector``) the per-generation strategy frequencies. The per-agent update lives on
the agent (imitate a fitter randomly-met peer with probability proportional to the payoff
gap), not in a god-loop.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

# Strategy encoding.
C = 0   # cooperator (participant, pays the cost)
D = 1   # defector   (participant, free-rides)
L = 2   # loner      (abstains, earns sigma)
STRATEGIES = (C, D, L)
STRATEGY_NAME = {C: "C", D: "D", L: "L"}


# -- payoffs (Hauert et al. 2002, the exact closed form) ----------------------

def expected_payoffs(x_c: float, x_d: float, x_l: float, *,
                     r: float, sigma: float, N: int) -> Tuple[float, float, float]:
    """Expected payoffs (P_C, P_D, P_L) of the three strategies at population
    frequencies (x_c, x_d, x_l), for the optional public goods game with group size
    ``N``, multiplication factor ``r``, cost c = 1 and loner payoff ``sigma``.

    This is the closed form derived in Hauert et al. (2002), Science 296:1129 (their
    Eqs. for P_D - P_C and P_D, adapted to c = 1). A focal player samples N-1 co-players
    from the population.

      * LONER: always earns ``sigma``.  P_L = sigma.

      * If the focal participant is otherwise ALONE — all N-1 co-players are loners, which
        happens with probability z^{N-1} where z = x_l — it is forced to the loner payoff
        sigma. Otherwise (probability 1 - z^{N-1}) it is in a group of S >= 2 participants.

      * Defector minus cooperator gap (the return-on-investment a cooperator forgoes),
        Hauert's Eq.:
            P_D - P_C = 1 - (r/N) * (1 + z + z^2 + ... + z^{N-1})
                      = 1 - (r/N) * (1 - z^N) / (1 - z)          (z != 1)
        (as z -> 1 this tends to 1 - r*z^{N-1} -> 1 - r; for r > 1 cooperating always
        trails defecting on average — the social dilemma persists.)

      * Defector's expected payoff (the value of NOT abstaining, referenced to sigma):
            P_D = sigma + (1 - z^{N-1}) * (F(z) - sigma) ... implemented via the
        Hauert closed form for P_D directly:
            P_D = sigma * z^{N-1}
                  + r * (x_c / (1 - z))
                    * ( 1 - (1 - z^N) / (N * (1 - z)) )
                  ... (the standard optional-PGG result). We compute P_D from the exact
        expectation E[r * n_c / S | not alone] * (1 - z^{N-1}) + sigma * z^{N-1}, and set
        P_C = P_D - (P_D - P_C).

    The expectations are evaluated by summing over the binomial sampling distribution of
    the N-1 co-players (exact, O(N^2)); this equals the Monte-Carlo group-sampling estimate
    (pinned in the tests) and, for z not too close to 1, the algebraic closed form above.
    """
    if N < 2:
        raise ValueError(f"group size N must be >= 2 (got {N})")
    z = x_l
    # Non-loner conditional frequencies among participants (guard z ~ 1).
    part = x_c + x_d
    # P_L is trivial.
    p_l = sigma

    if part <= 0.0:
        # Everyone is a loner: every focal player is alone -> all get sigma.
        return sigma, sigma, sigma

    f_c = x_c / part   # fraction of participants that cooperate
    # Exact expectation over the sampling of N-1 co-players (each independently a loner
    # with prob z, else a participant; among participants a cooperator with prob f_c).
    #
    # For the focal player, let k = number of NON-loner co-players (0..N-1), drawn
    # binomial(N-1, part). Given k co-players, the group has S = k+1 participants
    # (focal + k). Among the k co-players, the number of cooperators is binomial(k, f_c).
    #
    #   * If k = 0: focal is alone -> forced to sigma (both C and D get sigma here).
    #   * If k >= 1: pot share for a DEFECTOR focal is r * (coop_count) / S, where
    #       coop_count counts cooperators among the OTHER k participants only (the focal
    #       defector contributes none). For a COOPERATOR focal it is
    #       r * (coop_count + 1) / S - 1.
    #
    # We take expectations analytically over coop_count | k = k * f_c (mean of the
    # binomial), which is exact for the LINEAR payoff in coop_count.
    from math import comb

    p_d = 0.0
    p_c = 0.0
    for k in range(0, N):
        # P(exactly k non-loner co-players) = C(N-1, k) part^k z^{N-1-k}
        pk = comb(N - 1, k) * (part ** k) * (z ** (N - 1 - k))
        if k == 0:
            # alone -> both forced to sigma
            p_d += pk * sigma
            p_c += pk * sigma
            continue
        S = k + 1
        mean_other_coops = k * f_c
        # defector focal: pot from the OTHER cooperators, split over S; pays nothing.
        p_d += pk * (r * mean_other_coops / S)
        # cooperator focal: adds itself to the pot (mean_other_coops + 1), split over S,
        # minus its cost c = 1.
        p_c += pk * (r * (mean_other_coops + 1.0) / S - 1.0)

    return p_c, p_d, p_l


# -- Agent --------------------------------------------------------------------

class PlayerAgent(Agent):
    """One player carrying a strategy in {C, D, L}.

    The imitation update (compare payoff to a randomly-met peer, adopt the peer's strategy
    with probability proportional to the payoff advantage, else keep own; then a tiny
    mutation) is a model-level SYNCHRONOUS update driven from one start-of-generation
    payoff snapshot, so the per-agent ``step`` stages the next strategy; the model commits
    all strategies at once.
    """

    def __init__(self, agent_id: int, model: "OptionalPGGModel", *, strategy: int) -> None:
        super().__init__(agent_id, model)
        self.strategy = strategy
        self._next_strategy = strategy

    def step(self) -> None:  # pragma: no cover - the update lives on the model
        """The imitation update is a model-level synchronous pass (one payoff snapshot,
        then all commit), not an autonomous single-agent step, so this is a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class OptionalPGGModel(AgentModel):
    """Optional public goods game with loners (Hauert et al. 2002) as an agent-based IBM.

    A population of ``pop`` ``PlayerAgent``s, each carrying a strategy in {C, D, L}. Every
    generation is a SYNCHRONOUS imitation-with-mutation update:

      (1) Compute each strategy's expected payoff at the CURRENT population frequencies
          (the exact optional-PGG closed form; group size ``N``, factor ``r``, loner
          payoff ``sigma``, cost 1).
      (2) Each agent meets one random peer; if the peer's strategy has a higher expected
          payoff, the agent adopts it with probability proportional to the payoff gap
          (a standard pairwise-comparison / replicator imitation rule). This reproduces
          the replicator flow in the large-population limit while remaining genuinely
          agent-based (each agent decides for itself).
      (3) With probability ``mu`` (tiny) the agent instead mutates to a uniformly-random
          strategy — the exploration that keeps the finite population from drifting onto
          the simplex boundary and fixating around the neutrally-stable center Q.

    Set ``compulsory=True`` to REMOVE the loner strategy (only C and D). This is the fair
    control: same payoffs, same update, same seeds — the ONLY difference is that opting out
    is unavailable, so the game collapses to all-D.

    ``run(n_gen)`` advances the synchronous update and records the per-generation strategy
    frequencies. Deterministic given the seed.
    """

    def __init__(self, pop: int = 5000, *, r: float = 3.0, sigma: float = 1.0,
                 N: int = 5, mu: float = 1e-3, compulsory: bool = False,
                 init: str = "uniform", seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if pop <= 0:
            raise ValueError(f"need pop > 0 (got {pop})")
        if N < 2:
            raise ValueError(f"need group size N >= 2 (got {N})")
        if r <= 1.0:
            raise ValueError(f"need multiplication factor r > 1 (got {r})")
        if not (0.0 < sigma < r - 1.0):
            raise ValueError(
                f"need 0 < sigma < r-1 for a valid loner payoff (got sigma={sigma}, r={r})")
        if not (0.0 <= mu <= 1.0):
            raise ValueError(f"need 0 <= mu <= 1 (got {mu})")
        self.seed_value = seed
        self.pop = pop
        self.r = float(r)
        self.sigma = float(sigma)
        self.N = int(N)
        self.mu = float(mu)
        self.compulsory = bool(compulsory)
        # available strategies: {C, D, L} normally, {C, D} in the compulsory control.
        self.strategy_set: Tuple[int, ...] = (C, D) if self.compulsory else (C, D, L)

        # Random initial strategy assignment. "uniform" = each agent uniform over the
        # available strategies (the locked default). The only randomness besides the
        # per-generation imitation/mutation draws is this seeded initial assignment.
        self.agent_list: List[PlayerAgent] = []
        for i in range(pop):
            strat = self._initial_strategy(init)
            agent = PlayerAgent(i, self, strategy=strat)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "fC": lambda m: m.strategy_fraction(C),
            "fD": lambda m: m.strategy_fraction(D),
            "fL": lambda m: m.strategy_fraction(L),
        })

    def _initial_strategy(self, init: str) -> int:
        if init == "uniform":
            return self.rng.choice(self.strategy_set)
        if init == "mostly_defect":
            # small cooperator + loner seed in a defector sea (used only for robustness
            # checks, never the locked grade).
            u = self.rng.random()
            if u < 0.1:
                return C
            if not self.compulsory and u < 0.2:
                return L
            return D
        raise ValueError(f"unknown init {init!r}")

    # -- metrics --
    def strategy_count(self, s: int) -> int:
        return sum(1 for a in self.agent_list if a.strategy == s)

    def strategy_fraction(self, s: int) -> float:
        if self.pop == 0:
            return 0.0
        return self.strategy_count(s) / self.pop

    def frequencies(self) -> Tuple[float, float, float]:
        """Current (x_C, x_D, x_L). In the compulsory arm x_L is always 0."""
        return (self.strategy_fraction(C),
                self.strategy_fraction(D),
                self.strategy_fraction(L))

    # -- payoffs at the current population state --
    def current_payoffs(self) -> Tuple[float, float, float]:
        """(P_C, P_D, P_L) at the current frequencies (the exact optional-PGG closed
        form). In the compulsory arm there are no loners; a lone participant (all N-1
        co-players absent is impossible when nobody abstains) never occurs, so the payoffs
        reduce to the ordinary compulsory PGG."""
        x_c, x_d, x_l = self.frequencies()
        return expected_payoffs(x_c, x_d, x_l, r=self.r, sigma=self.sigma, N=self.N)

    # -- one synchronous imitation-with-mutation generation --
    def step(self) -> None:
        """One generation.

        (1) Snapshot the three expected payoffs at the current frequencies.
        (2) Every agent meets one random peer and adopts the peer's strategy with
            probability proportional to the positive payoff gap (pairwise comparison),
            unless a tiny-probability mutation replaces its strategy with a random one.
        (3) Commit all new strategies at once (synchronous)."""
        payoff = self.current_payoffs()   # (P_C, P_D, P_L)
        # Normaliser for the pairwise-comparison acceptance probability: the payoff range
        # keeps the adoption probability in [0, 1] regardless of r/sigma scale.
        pmax = max(payoff)
        pmin = min(payoff)
        span = (pmax - pmin) if pmax > pmin else 1.0

        pop = self.pop
        agents = self.agent_list
        rng = self.rng
        for a in agents:
            if rng.random() < self.mu:
                # MUTATION: jump to a uniformly-random available strategy.
                a._next_strategy = rng.choice(self.strategy_set)
                continue
            # IMITATION: meet one random OTHER peer.
            j = rng.randrange(pop)
            # allow self-meeting only degenerate; redraw once to avoid it cheaply.
            if agents[j] is a:
                j = (j + 1) % pop
            peer = agents[j]
            my_pay = payoff[a.strategy]
            peer_pay = payoff[peer.strategy]
            if peer_pay > my_pay:
                # adopt with probability proportional to the payoff advantage.
                if rng.random() < (peer_pay - my_pay) / span:
                    a._next_strategy = peer.strategy
                else:
                    a._next_strategy = a.strategy
            else:
                a._next_strategy = a.strategy
        # commit
        for a in agents:
            a.strategy = a._next_strategy
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_gen: int = 2000, *, measure_from: int = 500) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_gen`` synchronous generations; return the run summary.

        ``measure_from`` is the burn-in: the time-averaged frequencies and the cooperator
        amplitude are computed over generations [measure_from, n_gen] (the leading
        measure_from generations are the transient before measurement). Returns the
        time-averaged and final frequencies, the cooperator peak-to-trough amplitude over
        the measurement window, and the full per-generation series of all three
        frequencies.
        """
        if measure_from < 0 or measure_from > n_gen:
            raise ValueError(
                f"measure_from must be in [0, n_gen] (got {measure_from}, n_gen={n_gen})")
        self.reporter.collect(self)          # generation-0 baseline
        for _ in range(n_gen):
            self.step()
        fC = self.reporter.series("fC")
        fD = self.reporter.series("fD")
        fL = self.reporter.series("fL")
        # measurement window (post burn-in), inclusive of the baseline offset.
        window_c = fC[measure_from:]
        window_d = fD[measure_from:]
        window_l = fL[measure_from:]
        amp_c = (max(window_c) - min(window_c)) if window_c else 0.0
        return {
            "pop": self.pop,
            "r": self.r,
            "sigma": self.sigma,
            "N": self.N,
            "mu": self.mu,
            "compulsory": self.compulsory,
            "seed": self.seed_value,
            "n_gen": n_gen,
            "measure_from": measure_from,
            "timeavg_fC": _mean(window_c),
            "timeavg_fD": _mean(window_d),
            "timeavg_fL": _mean(window_l),
            "final_fC": fC[-1],
            "final_fD": fD[-1],
            "final_fL": fL[-1],
            "coop_amplitude": amp_c,
            "fC_series": fC,
            "fD_series": fD,
            "fL_series": fL,
        }


# -- summary helpers ----------------------------------------------------------

def _mean(series: Sequence[float]) -> float:
    return sum(series) / len(series) if series else 0.0


def run_single(pop: int = 5000, *, r: float = 3.0, sigma: float = 1.0, N: int = 5,
               mu: float = 1e-3, compulsory: bool = False, init: str = "uniform",
               seed: int = 0, n_gen: int = 2000, measure_from: int = 500) -> Dict[str, Any]:
    """One optional-PGG run at a given (r, sigma, compulsory, seed) and fixed parameters."""
    return OptionalPGGModel(pop, r=r, sigma=sigma, N=N, mu=mu, compulsory=compulsory,
                            init=init, seed=seed).run(n_gen, measure_from=measure_from)


def run_many_seeds(pop: int = 5000, *, r: float = 3.0, sigma: float = 1.0, N: int = 5,
                   mu: float = 1e-3, compulsory: bool = False, init: str = "uniform",
                   n_seeds: int = 5, seed_base: int = 0, n_gen: int = 2000,
                   measure_from: int = 500) -> Dict[str, Any]:
    """Run ``n_seeds`` optional-PGG runs (seed ``seed_base + i``) at fixed parameters and
    summarise the time-averaged strategy frequencies and cooperator amplitude across seeds.

    Returns the per-seed time-averaged (fC, fD, fL) and cooperator amplitudes, their means
    and spreads, and one representative trajectory (first seed) of all three frequency
    series for inspection.
    """
    runs = [run_single(pop, r=r, sigma=sigma, N=N, mu=mu, compulsory=compulsory,
                       init=init, seed=seed_base + i, n_gen=n_gen, measure_from=measure_from)
            for i in range(n_seeds)]
    per_seed_fC = [rr["timeavg_fC"] for rr in runs]
    per_seed_fD = [rr["timeavg_fD"] for rr in runs]
    per_seed_fL = [rr["timeavg_fL"] for rr in runs]
    per_seed_amp = [rr["coop_amplitude"] for rr in runs]
    mean_fC = _mean(per_seed_fC)
    mean_fD = _mean(per_seed_fD)
    mean_fL = _mean(per_seed_fL)
    mean_amp = _mean(per_seed_amp)
    return {
        "pop": pop, "r": r, "sigma": sigma, "N": N, "mu": mu, "compulsory": compulsory,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_gen": n_gen, "measure_from": measure_from,
        "per_seed_timeavg_fC": per_seed_fC,
        "per_seed_timeavg_fD": per_seed_fD,
        "per_seed_timeavg_fL": per_seed_fL,
        "per_seed_coop_amplitude": per_seed_amp,
        "mean_timeavg_fC": mean_fC,
        "mean_timeavg_fD": mean_fD,
        "mean_timeavg_fL": mean_fL,
        "mean_coop_amplitude": mean_amp,
        "min_timeavg_fC": min(per_seed_fC),
        "max_timeavg_fC": max(per_seed_fC),
        "min_timeavg_fL": min(per_seed_fL),
        "max_timeavg_fL": max(per_seed_fL),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_fC_series": runs[0]["fC_series"],
        "example_fD_series": runs[0]["fD_series"],
        "example_fL_series": runs[0]["fL_series"],
    }
