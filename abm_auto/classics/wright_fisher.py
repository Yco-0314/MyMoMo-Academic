"""Wright-Fisher neutral genetic drift (Wright 1931 / Fisher 1930) — a faithful
agent-based reproduction.

Source: Wright, S. (1931) "Evolution in Mendelian populations", Genetics 16:97-159;
Fisher, R.A. (1930) "The Genetical Theory of Natural Selection". The Wright-Fisher
model is the canonical NON-overlapping-generation neutral-drift process: a population
of fixed size N reproduces in discrete generations by random sampling.

The classic neutral results this study reproduces:
  * FIXATION PROBABILITY of an allele equals its INITIAL FREQUENCY: an allele A at
    frequency p0 fixes (reaches frequency 1) with probability p0 (the rest of the time
    it is lost). This is the martingale property of neutral drift — E[p(t+1) | p(t)] = p(t).
  * HETEROZYGOSITY H = 2*p*(1-p) decays geometrically. For a haploid Wright-Fisher
    population of N gene copies the expected per-generation decay factor is

            E[H(t+1)] = (1 - 1/N) * E[H(t)].

    (The textbook "1 - 1/(2N)" is the DIPLOID statement with 2N gene copies; for a
    haploid population of N copies the corresponding factor is 1 - 1/N. We measure the
    realised decay and report it against the 1/N law honestly.)
  * NEUTRALITY: there is no selection bias — every individual is equally likely to be a
    parent, so E[Delta p] = 0 and the mean allele frequency across runs stays at p0 until
    a run is absorbed.

Rules (the classic Wright-Fisher generational resample, verified against the source):
  * A population of N haploid ``AlleleAgent``s, each carrying a single allele: ``A`` or
    ``a``. The population size N is CONSTANT across generations.
  * Start with a fraction p0 of agents carrying ``A`` (deterministic placement: the first
    round(p0*N) agents are ``A``, the rest ``a`` — the layout is irrelevant in a
    well-mixed model; only the count #A matters).
  * Each GENERATION builds the NEXT generation from scratch: for each of the N offspring
    slots, sample a parent UNIFORMLY at random WITH REPLACEMENT from the CURRENT
    generation (neutral — every individual equally likely, no fitness), and the offspring
    inherits that sampled parent's allele. The whole next generation is then installed.
  * Run until FIXATION: #A == 0 (A lost) or #A == N (A fixed).
  * Outcome of one run = whether A fixed (#A reached N). Over many independent runs (each
    a fresh population at p0, a different seed) the fixation FRACTION estimates the neutral
    fixation probability, which the theory says equals p0.

Why this is genuinely agent-based (no analytic result is fed into the dynamics):
  Each individual is an agent holding its OWN discrete heritable allele. The model forms
  the next generation by drawing N parents uniformly from the actual roster and copying
  each drawn parent's allele into the corresponding offspring — a pure neutral Monte-Carlo
  resample over N interacting individuals. The analytic fixation-prob (= p0) and the 1/N
  heterozygosity law are computed ONLY as comparison anchors; the agents never see them.
  Given a seed the whole run is reproducible (one seeded RNG chain on the model).

Built on the neutral platform (``abm_auto._platform``): each individual is an
``AlleleAgent`` carrying its discrete allele; ``WrightFisherModel`` owns the seeded RNG,
the generational resample over the ``AgentSet`` roster, and the fixation stop rule.

NOTE — Wright-Fisher is GENERATIONAL (the whole population is replaced each step),
distinct from the Moran process (one birth-death event per step). They share the neutral
fixation-prob = initial-frequency result but differ in the per-step dynamics and time scale.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel

ALLELE_A = "A"
ALLELE_a = "a"


# -- analytic anchors ---------------------------------------------------------

def analytic_fixation(p0: float) -> float:
    """Neutral Wright-Fisher fixation probability of an allele = its initial frequency p0.

    This is the COMPARISON anchor (the martingale property E[p(t+1)|p(t)] = p(t) makes the
    absorption probability at the all-A boundary equal p0). It is never fed into the agent
    dynamics."""
    if not (0.0 <= p0 <= 1.0):
        raise ValueError(f"p0 must be in [0, 1] (got {p0})")
    return p0


def heterozygosity_decay_factor(n: int) -> float:
    """The neutral per-generation expected heterozygosity decay factor for a HAPLOID
    Wright-Fisher population of N gene copies: E[H(t+1)] = (1 - 1/N) E[H(t)].

    (The diploid textbook factor is 1 - 1/(2N) for 2N copies.) Comparison anchor only —
    never fed into the dynamics."""
    if n <= 0:
        raise ValueError(f"N must be positive (got {n})")
    return 1.0 - 1.0 / n


def heterozygosity(p: float) -> float:
    """Expected heterozygosity H = 2 p (1 - p) at allele-A frequency p."""
    return 2.0 * p * (1.0 - p)


# -- Agent --------------------------------------------------------------------

class AlleleAgent(Agent):
    """One haploid individual carrying a single discrete heritable ``allele`` (``A`` or
    ``a``). The allele is the only state; under neutrality it carries no fitness."""

    def __init__(self, agent_id: int, model: "WrightFisherModel", *, allele: str) -> None:
        super().__init__(agent_id, model)
        self.allele = allele

    def is_A(self) -> bool:
        return self.allele == ALLELE_A

    def step(self) -> None:  # pragma: no cover - resample lives on the model
        """The Wright-Fisher generational resample (sample N parents with replacement,
        copy alleles) is a model-level step over the whole roster, not an autonomous
        single-agent step, so the per-agent ``step`` is intentionally a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class WrightFisherModel(AgentModel):
    """Drives the neutral Wright-Fisher generational drift.

    Construct with N, the initial A-fraction p0, and a seed. The first round(p0*N) agents
    start as ``A`` (the rest ``a``). ``run`` iterates generational resamples until fixation
    (#A == 0 or #A == N) and returns a summary dict (whether A fixed, #generations, the
    per-generation #A trajectory, and the heterozygosity trajectory).
    """

    def __init__(self, n: int = 100, *, p0: float = 0.5, seed: int = 0,
                 max_generations: Optional[int] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 1:
            raise ValueError(f"N must be > 1 (got {n})")
        if not (0.0 <= p0 <= 1.0):
            raise ValueError(f"p0 must be in [0, 1] (got {p0})")
        self.seed_value = seed
        self.n = n
        self.p0 = p0
        # Safety cap on generation count: neutral drift fixes a.s., but a finite cap keeps
        # a run bounded. Default is generous (scales with N) and is NOT a tuning knob —
        # fixation is essentially always reached well within it.
        self.max_generations = (max_generations if max_generations is not None
                                 else 2000 * n)

        # Seed the population: the first round(p0*N) agents are A, the rest a. Which
        # specific individuals carry A is irrelevant in a well-mixed model (only #A
        # matters), so deterministic placement keeps init seed-independent.
        n_A0 = round(p0 * n)
        self.agent_list: List[AlleleAgent] = []
        for i in range(n):
            allele = ALLELE_A if i < n_A0 else ALLELE_a
            agent = AlleleAgent(i, self, allele=allele)
            self.agent_list.append(agent)
            self.add_agent(agent)

    # -- metrics --
    def n_A(self) -> int:
        return sum(1 for a in self.agent_list if a.is_A())

    def fraction_A(self) -> float:
        return self.n_A() / self.n if self.n else 0.0

    def heterozygosity(self) -> float:
        return heterozygosity(self.fraction_A())

    def is_fixed(self) -> bool:
        """Absorbing state reached: all-A or all-a."""
        m = self.n_A()
        return m == 0 or m == self.n

    # -- one Wright-Fisher generation --
    def generation_step(self) -> None:
        """One generational resample:

          For each of the N offspring slots, sample a parent UNIFORMLY at random WITH
          replacement from the CURRENT generation (neutral — every individual equally
          likely), and the offspring inherits that parent's allele. The next generation
          replaces the current one in place (N constant).

        Reads only the actual agent roster (their alleles) — no analytic fixation-prob,
        no global-fraction oracle. Each offspring is an independent uniform draw, so this
        is exactly the binomial Wright-Fisher transition #A(t+1) ~ Binomial(N, #A(t)/N)
        realised one Bernoulli parent-draw at a time."""
        current_alleles = [a.allele for a in self.agent_list]
        n = self.n
        next_alleles = [current_alleles[self.rng.randrange(n)] for _ in range(n)]
        for agent, allele in zip(self.agent_list, next_alleles):
            agent.allele = allele

    # -- run to fixation --
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate generational resamples until fixation (#A == 0 or #A == N) or the
        safety cap; return the run summary (fixed?, #generations, the #A and H
        trajectories including the t=0 baseline)."""
        n_A_traj: List[int] = [self.n_A()]
        h_traj: List[float] = [self.heterozygosity()]
        generations = 0
        while not self.is_fixed() and generations < self.max_generations:
            self.generation_step()
            generations += 1
            n_A_traj.append(self.n_A())
            h_traj.append(self.heterozygosity())
        self.t = generations
        m_final = self.n_A()
        return {
            "n": self.n,
            "p0": self.p0,
            "seed": self.seed_value,
            "generations": generations,
            "final_A": m_final,
            "fixed": m_final == self.n,
            "absorbed": self.is_fixed(),
            "n_A_trajectory": n_A_traj,
            "h_trajectory": h_traj,
            "analytic_fixation": analytic_fixation(self.p0),
        }


# -- run drivers --------------------------------------------------------------

def run_single(n: int = 100, *, p0: float = 0.5, seed: int = 0,
               max_generations: Optional[int] = None) -> Dict[str, Any]:
    """One Wright-Fisher run (a fresh population at p0) at a given seed; runs to fixation."""
    return WrightFisherModel(n, p0=p0, seed=seed,
                             max_generations=max_generations).run()


def fixation_fraction(n: int = 100, *, p0: float = 0.5, n_runs: int = 2000,
                      seed_base: int = 0,
                      max_generations: Optional[int] = None) -> Dict[str, Any]:
    """Run ``n_runs`` independent Wright-Fisher runs (seed ``seed_base + i``; each a fresh
    population at p0) at fixed (N, p0) and estimate the fixation probability = fraction of
    runs in which allele A fixed.

    Returns the measured fixation fraction, its binomial standard error
    sqrt(p(1-p)/n_runs), the count of fixations, the analytic neutral fixation prob (= p0),
    the measured-minus-analytic error, and per-run generation counts (mean) for context.

    Also returns drift-neutrality diagnostics aggregated across runs:
      * ``mean_final_A_fraction`` — the mean of the final A-fraction across runs (an
        estimate of the fixation prob, equal to the mean over the {0,1} fixation indicator
        scaled — here returned as #A/N at absorption, i.e. exactly the fixation fraction);
      * ``mean_delta_p`` — the mean ONE-GENERATION increment Delta p = p(t+1) - p(t)
        over every pre-absorption (polymorphic, 0 < #A < N) step, pooled across runs. This
        is the DIRECT neutrality statement E[Delta p] = 0 (the Wright-Fisher martingale):
        a uniform parent draw gives E[#A(t+1) | #A(t)] = #A(t), so each step's expected
        change is zero. It is ~0 to Monte-Carlo precision for a faithful neutral model.
      * ``ensemble_mean_p_early`` — the mean A-fraction ACROSS RUNS at a fixed early
        generation (here generation ``ensemble_gen``, with runs absorbed before then
        contributing their absorbed 0/1 value). The martingale gives E[p(t)] = p0 for all
        t, so this should sit at ~p0. (Pooling the frequency over ALL polymorphic
        generations instead — ``mean_pre_absorption_fraction`` — is a DIFFERENT,
        conditioned quantity that is biased toward 0.5 by the absorption-time asymmetry
        of the conditioned process, and is NOT the neutrality statement; it is reported
        for transparency but is not the E[Delta p]=0 measure.)
      * ``mean_pre_absorption_fraction`` — the mean A-fraction averaged over every
        pre-absorption generation of every run (a CONDITIONED time-average; reported for
        transparency, NOT the neutrality grade — see ``mean_delta_p`` above);
      * ``decay_factor`` — the measured per-generation heterozygosity decay factor. This
        estimates the quantity the neutral LAW describes: E[H(t+1)] = (1-1/N) E[H(t)],
        i.e. the decay of the MEAN heterozygosity across the ensemble of runs. We pool
        H(t) across all runs at each generation index (absorbed runs contribute H=0),
        form the mean-H trajectory mean_H(t), and take the geometric mean of the
        consecutive ratios mean_H(t+1)/mean_H(t) over the early regime (the first
        ``decay_window`` generations, where most runs are still segregating so the mean
        is well sampled). NOTE: a per-RUN geometric mean of H(t+1)/H(t) is the WRONG
        estimator here — it is biased low (Jensen, on a ratio of correlated random
        variables); the law is about the ratio of EXPECTED H, which is the across-run
        ratio computed here.
    """
    import math
    fixations = 0
    n_absorbed = 0
    gens_list: List[int] = []
    # Drift-neutrality (transparency): pool every pre-absorption A-fraction across runs.
    pre_frac_sum = 0.0
    pre_frac_count = 0
    # Drift-neutrality (the GRADE): pool every one-generation Delta p over polymorphic
    # steps -> E[Delta p] (the martingale statement).
    delta_p_sum = 0.0
    delta_p_count = 0
    # Ensemble mean p at a fixed early generation (E[p(t)] = p0 statement). Runs absorbed
    # before this generation contribute their absorbed 0/1 value.
    ensemble_gen = 5
    ensemble_p_sum = 0.0
    # Heterozygosity decay (across-run): sum H(t) over runs at each generation index.
    # Absorbed runs contribute H=0 at every index past their absorption, so dividing by
    # ``n_runs`` gives the ensemble mean E[H(t)] including the lost-mass to fixation.
    decay_window = 100  # early regime; FIXED, not tuned (depends on N-scale, not on data)
    h_sum_by_gen: List[float] = [0.0] * (decay_window + 2)
    for i in range(n_runs):
        res = run_single(n, p0=p0, seed=seed_base + i,
                         max_generations=max_generations)
        if res["fixed"]:
            fixations += 1
        if res["absorbed"]:
            n_absorbed += 1
        gens_list.append(res["generations"])
        traj = res["n_A_trajectory"]
        h_traj = res["h_trajectory"]
        # Pre-absorption generations = every step t where the state was still polymorphic
        # (0 < #A < N). The trajectory's last entry is the absorbed state; everything
        # before it is pre-absorption.
        for t in range(len(traj) - 1):
            m = traj[t]
            if 0 < m < n:
                pre_frac_sum += m / n
                pre_frac_count += 1
                delta_p_sum += (traj[t + 1] - m) / n
                delta_p_count += 1
        # Ensemble mean p at the fixed early generation: absorbed-before-then runs
        # contribute their absorbed value (the last trajectory entry).
        ensemble_p_sum += (traj[ensemble_gen] if ensemble_gen < len(traj)
                           else traj[-1]) / n
        # Accumulate H(t) over the decay window (a run absorbed early has H=0 thereafter,
        # which we add explicitly so the ensemble mean reflects mass lost to fixation).
        for t in range(len(h_sum_by_gen)):
            h_sum_by_gen[t] += h_traj[t] if t < len(h_traj) else 0.0
    p = fixations / n_runs if n_runs else 0.0
    se = (p * (1.0 - p) / n_runs) ** 0.5 if n_runs else 0.0
    rho = analytic_fixation(p0)
    mean_h_by_gen = [s / n_runs for s in h_sum_by_gen] if n_runs else h_sum_by_gen
    log_ratio_sum = 0.0
    log_ratio_count = 0
    for t in range(decay_window):
        a, b = mean_h_by_gen[t], mean_h_by_gen[t + 1]
        if a > 1e-9 and b > 1e-9:
            log_ratio_sum += math.log(b / a)
            log_ratio_count += 1
    decay = math.exp(log_ratio_sum / log_ratio_count) if log_ratio_count else float("nan")
    mean_pre_frac = pre_frac_sum / pre_frac_count if pre_frac_count else float("nan")
    mean_delta_p = delta_p_sum / delta_p_count if delta_p_count else float("nan")
    ensemble_mean_p = ensemble_p_sum / n_runs if n_runs else float("nan")
    return {
        "n": n,
        "p0": p0,
        "n_runs": n_runs,
        "seed_base": seed_base,
        "fixations": fixations,
        "measured_fixation": p,
        "binomial_se": se,
        "analytic_fixation": rho,
        "error": p - rho,
        "abs_error": abs(p - rho),
        "n_absorbed": n_absorbed,
        "all_absorbed": n_absorbed == n_runs,
        "mean_generations": sum(gens_list) / n_runs if n_runs else 0.0,
        "max_generations_observed": max(gens_list) if gens_list else 0,
        "mean_final_A_fraction": p,  # final A-fraction is 1 iff fixed, 0 otherwise -> = p
        "mean_delta_p": mean_delta_p,
        "ensemble_mean_p_early": ensemble_mean_p,
        "ensemble_gen": ensemble_gen,
        "mean_pre_absorption_fraction": mean_pre_frac,
        "measured_decay_factor": decay,
        "analytic_decay_factor": heterozygosity_decay_factor(n),
        "decay_window": decay_window,
        "n_decay_ratios": log_ratio_count,
        "mean_h_by_gen": mean_h_by_gen,
        "n_pre_absorption_generations": pre_frac_count,
    }
