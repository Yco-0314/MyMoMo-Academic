"""Indirect reciprocity by image scoring (Nowak & Sigmund 1998) — a faithful
agent-based reproduction.

Source: Nowak, M. A. & Sigmund, K. (1998) "Evolution of indirect reciprocity by
image scoring", Nature 393:573-577. doi:10.1038/31225.

The central idea: cooperation can evolve WITHOUT repeated pairings between the same
two individuals — the hallmark of DIRECT reciprocity (Axelrod's IPD / tit-for-tat).
Instead a donor decides whether to help a recipient it may never meet again by
conditioning on the recipient's IMAGE SCORE — a public reputation that rises when an
individual helps others and falls when it refuses. Helping strangers who have helped
OTHERS is INDIRECT reciprocity, and image scoring is its simplest realisation.

Distinct from direct reciprocity (axelrod_ipd) and from peer-punishment public goods:
a discriminator strategy here conditions its move on the recipient's THIRD-PARTY image
(what the recipient did to others), which neither the repeated-pairing TFT world nor a
within-group punishment model has any representation of. There are no repeated pairings
in this model — donor and recipient are drawn independently each interaction.

The model (the fixed rules, locked before running — see PREDICTIONS-locked.md):
  * n ``PlayerAgent``s. Each carries:
      - an IMAGE SCORE ``s`` (an integer public reputation) bounded to [S_MIN, S_MAX]
        = [-5, +5]; everyone starts at s = 0 (neutral reputation).
      - a STRATEGY = an integer threshold ``k`` in [K_MIN, K_MAX] = [-5, +6]. A donor
        with threshold k HELPS a recipient iff the recipient's image score s >= k.
        k = -5 always helps (unconditional cooperator, since s >= -5 always);
        k = +6 never helps (defector, since s <= +5 < 6 always);
        k = 0 is the "stern discriminator" — help only those with a non-negative image.
  * DONATION GAME. Within a generation, ``m`` = interactions_per_agent * n interactions
    are played (m ~ 10n). Each interaction draws a DONOR and a distinct RECIPIENT
    uniformly at random (independent each time — NO repeated pairing). The donor helps
    iff recipient.s >= donor.k:
      - HELP: donor pays cost c (= 0.1); recipient gains benefit b (= 1.0); c < b.
      - REFUSE: no payoff change.
  * IMAGE UPDATE with observation probability q. A fraction q of the population observes
    each interaction; equivalently the donor's new image becomes public knowledge with
    probability q. With probability q the donor's image score is updated:
      + helping raises it by +1 (capped at S_MAX);
      - refusing lowers it by -1 (capped at S_MIN).
    With probability 1 - q the interaction is unobserved and the donor's image is
    UNCHANGED (no one learns what it did). q is the information parameter: at q = 1
    every act is seen; at q = 0 image scores never move and discrimination is blind.
  * REPRODUCTION (payoff-proportional, once per generation). Payoffs accumulate over the
    generation's m interactions. A new generation of n strategies is drawn by fitness-
    proportional (roulette) selection over the current strategies' total payoffs — the
    replicator/Moran-style update used throughout the cooperation-evolution literature.
    Payoffs are shifted so the least-fit strategy has weight >= 0 (only DIFFERENCES in
    payoff matter). With MUTATION probability ``mu`` a reproduced strategy is instead
    replaced by a fresh uniform-random threshold (mutation explores the strategy space;
    the no-mutation runs set mu = 0). Image scores reset to 0 at the start of each
    generation (a newborn has a neutral reputation).
  * OUTCOME METRICS (locked): the strategy distribution over thresholds k (for P1's
    fixation to k = 0), the fraction of interactions that were cooperative acts (for P2's
    information threshold), and the "cooperative-strategy fraction" = fraction of the
    population whose threshold is DISCRIMINATING-or-cooperative (k <= S_MAX, i.e. a
    strategy that will help at least the best-image recipients; the pure defector k = 6
    never helps) — the coop-strategy share used by P2/P3.

Why this is genuinely agent-based: every player is an agent holding its OWN image score
and threshold; the donation game reads the actual recipient's actual image and the
donor's actual threshold; reproduction samples over the realised per-agent payoffs. No
analytic result is fed into the dynamics. Deterministic given a seed (one seeded RNG
chain on the model).

Built on the neutral platform (``abm_auto._platform``): each player is a ``PlayerAgent``;
``ImageScoringModel`` owns the seeded RNG, the donation-game interaction round, the
generational payoff-proportional reproduction with optional mutation, and a
``DataCollector`` recording the per-generation cooperative-act fraction and the
cooperative-strategy fraction.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

# Image-score bounds and strategy-threshold range (FIXED before running; NOT tuned).
S_MIN, S_MAX = -5, 5          # image score s in [-5, +5]; everyone starts at 0
K_MIN, K_MAX = -5, 6          # threshold k in [-5, +6]: -5 = always help, +6 = never help
K_VALUES: Tuple[int, ...] = tuple(range(K_MIN, K_MAX + 1))   # the 12 possible strategies


# -- Agent --------------------------------------------------------------------

class PlayerAgent(Agent):
    """One player in the population.

    ``k`` is the discrimination threshold (the heritable strategy): the player HELPS a
    recipient iff that recipient's image score s >= k. ``s`` is the player's own public
    image score (its reputation, in [S_MIN, S_MAX]); it starts each generation at 0 and
    moves with the player's own donation decisions (observed with probability q).
    ``payoff`` accumulates the generation's donation-game payoffs (benefits received
    minus costs paid)."""

    def __init__(self, agent_id: int, model: "ImageScoringModel", *, k: int) -> None:
        super().__init__(agent_id, model)
        self.k = k
        self.s = 0
        self.payoff = 0.0

    def helps(self, recipient: "PlayerAgent") -> bool:
        """A donor helps iff the recipient's image score meets the donor's threshold."""
        return recipient.s >= self.k

    def step(self) -> None:  # pragma: no cover - the round lives on the model
        """The donation game + generational reproduction are model-level updates over the
        whole roster, not an autonomous single-agent step, so this is a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class ImageScoringModel(AgentModel):
    """Drives the Nowak-Sigmund 1998 image-scoring dynamics.

    Construct with the population size ``n``, the donation-game payoffs (cost ``c``,
    benefit ``b``), the observation probability ``q``, the number of interactions per
    agent per generation (m = interactions_per_agent * n), the mutation probability
    ``mu``, and a seed. ``run`` iterates generations of
    (reset images + payoffs -> m donation-game interactions -> payoff-proportional
    reproduction with optional mutation) and records the per-generation cooperative-act
    fraction and cooperative-strategy fraction.
    """

    def __init__(self, n: int = 100, *, b: float = 1.0, c: float = 0.1, q: float = 1.0,
                 interactions_per_agent: int = 10, mu: float = 0.0,
                 init_strategy: Optional[str] = None, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 1:
            raise ValueError(f"n must be > 1 (got {n})")
        if not (b > c > 0.0):
            raise ValueError(f"need benefit b > cost c > 0 (got b={b}, c={c})")
        if not (0.0 <= q <= 1.0):
            raise ValueError(f"observation probability q must be in [0, 1] (got {q})")
        if interactions_per_agent <= 0:
            raise ValueError(f"interactions_per_agent must be > 0 (got {interactions_per_agent})")
        if not (0.0 <= mu <= 1.0):
            raise ValueError(f"mutation probability mu must be in [0, 1] (got {mu})")
        self.seed_value = seed
        self.n = n
        self.b = float(b)
        self.c = float(c)
        self.q = float(q)
        self.interactions_per_agent = int(interactions_per_agent)
        self.m = self.interactions_per_agent * n          # interactions per generation
        self.mu = float(mu)
        # Per-generation running counts for the cooperative-act fraction.
        self._n_help = 0
        self._n_interactions = 0

        # Initial strategy assignment. Default: thresholds drawn UNIFORMLY at random over
        # the full range K_VALUES (a fair, un-rigged start that seeds the whole strategy
        # space — NOT pre-loaded with the stern discriminator). ``init_strategy`` can pin
        # a specific starting threshold for characterisation, but the locked runs use the
        # uniform-random default.
        self.init_strategy = init_strategy
        self.agent_list: List[PlayerAgent] = []
        for i in range(n):
            k = self._initial_threshold()
            agent = PlayerAgent(i, self, k=k)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "coop_act_fraction": lambda mdl: mdl.last_coop_act_fraction,
            "coop_strategy_fraction": lambda mdl: mdl.coop_strategy_fraction(),
            "mean_k": lambda mdl: mdl.mean_k(),
            "freq_k0": lambda mdl: mdl.strategy_frequency(0),
        })
        # cooperative-act fraction of the most recent completed generation (0 before any).
        self.last_coop_act_fraction = 0.0

    # -- setup helpers --
    def _initial_threshold(self) -> int:
        """Draw one initial strategy threshold (uniform over K_VALUES by default, or the
        pinned ``init_strategy`` if given)."""
        if self.init_strategy is not None:
            k = int(self.init_strategy)
            if k not in K_VALUES:
                raise ValueError(f"init_strategy {k} not in {K_VALUES}")
            return k
        return self.rng.choice(K_VALUES)

    # -- metrics --
    def strategy_counts(self) -> Dict[int, int]:
        """Count of players holding each threshold value k (all K_VALUES keyed, zeros
        included)."""
        counts = {k: 0 for k in K_VALUES}
        for a in self.agent_list:
            counts[a.k] += 1
        return counts

    def strategy_frequency(self, k: int) -> float:
        """Fraction of the population currently holding threshold ``k``."""
        return sum(1 for a in self.agent_list if a.k == k) / self.n if self.n else 0.0

    def mean_k(self) -> float:
        """Mean strategy threshold over the population."""
        return sum(a.k for a in self.agent_list) / self.n if self.n else 0.0

    def coop_strategy_fraction(self) -> float:
        """Fraction of the population whose strategy is DISCRIMINATING-or-cooperative,
        i.e. a threshold k <= S_MAX (so the strategy will help at least the best-image
        recipients). The pure defector k = K_MAX (= +6 > S_MAX) never helps anyone and is
        the only non-cooperative strategy in this sense — this is the coop-strategy share
        the locked P2/P3 clauses grade."""
        return sum(1 for a in self.agent_list if a.k <= S_MAX) / self.n if self.n else 0.0

    @property
    def last_coop_act_fraction_value(self) -> float:
        return self.last_coop_act_fraction

    # -- one donation-game interaction --
    def _donation_interaction(self) -> None:
        """One donation-game interaction: draw a donor and a distinct recipient uniformly
        at random; the donor helps iff recipient.s >= donor.k. Helping pays c and gives b;
        with probability q the donor's image is updated (+1 help, -1 refuse, capped)."""
        n = self.n
        i = self.rng.randrange(n)
        j = self.rng.randrange(n)
        while j == i:
            j = self.rng.randrange(n)
        donor = self.agent_list[i]
        recipient = self.agent_list[j]
        helped = donor.helps(recipient)
        if helped:
            donor.payoff -= self.c
            recipient.payoff += self.b
        # Image update, observed with probability q (else the act is unseen: image held).
        if self.rng.random() < self.q:
            if helped:
                if donor.s < S_MAX:
                    donor.s += 1
            else:
                if donor.s > S_MIN:
                    donor.s -= 1
        self._n_interactions += 1
        if helped:
            self._n_help += 1

    # -- one generation --
    def play_generation(self) -> None:
        """Reset every player's image to 0 and payoff to 0, then play m donation-game
        interactions against the CURRENT population, tallying the cooperative-act
        fraction of the generation."""
        for a in self.agent_list:
            a.s = 0
            a.payoff = 0.0
        self._n_help = 0
        self._n_interactions = 0
        for _ in range(self.m):
            self._donation_interaction()
        self.last_coop_act_fraction = (
            self._n_help / self._n_interactions if self._n_interactions else 0.0)

    def reproduce(self) -> None:
        """Payoff-proportional (roulette) reproduction with optional mutation.

        Each of the n offspring copies a parent chosen with probability proportional to
        the parent's total generation payoff, after shifting all payoffs so the minimum
        is 0 (only payoff DIFFERENCES matter; this handles the negative costs cleanly).
        If every payoff is equal (degenerate flat fitness), parents are chosen uniformly.
        With probability ``mu`` an offspring's threshold is instead a fresh uniform-random
        strategy (mutation). The new thresholds are committed synchronously as the next
        generation's strategies; image scores are reset at the start of the next
        generation."""
        payoffs = [a.payoff for a in self.agent_list]
        lo = min(payoffs)
        weights = [p - lo for p in payoffs]           # shift so min weight == 0
        total = sum(weights)
        new_ks: List[int] = []
        for _ in range(self.n):
            if self.mu > 0.0 and self.rng.random() < self.mu:
                new_ks.append(self.rng.choice(K_VALUES))
                continue
            if total <= 0.0:
                parent = self.agent_list[self.rng.randrange(self.n)]
            else:
                parent = self._roulette_parent(weights, total)
            new_ks.append(parent.k)
        for a, k in zip(self.agent_list, new_ks):
            a.k = k

    def _roulette_parent(self, weights: List[float], total: float) -> PlayerAgent:
        """Fitness-proportional parent selection: a uniform draw on [0, total) picks a
        parent by accumulating the (shifted) payoff weights over the roster."""
        threshold = self.rng.random() * total
        cum = 0.0
        chosen = self.agent_list[-1]
        for a, w in zip(self.agent_list, weights):
            cum += w
            if threshold < cum:
                chosen = a
                break
        return chosen

    # -- tick (one generation) --
    def step(self) -> None:
        """One generation: play m donation-game interactions against the current
        population, then reproduce payoff-proportionally (with optional mutation), then
        record the generation's cooperative-act fraction and the new strategy
        distribution."""
        self.play_generation()
        self.reproduce()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_generations: int = 500) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate ``n_generations`` generations; return a run summary with the full
        per-generation cooperative-act and cooperative-strategy series, the mean-k and
        k=0-frequency series, and the final strategy distribution.

        NOTE on ordering: each recorded generation's ``coop_act_fraction`` is measured on
        the population that PLAYED it, and the strategy metrics (coop-strategy fraction,
        mean k, k=0 freq) reflect the population AFTER that generation's reproduction —
        i.e. the strategies that will play the next generation. The t=0 baseline records
        the initial (pre-play) strategy distribution with a 0 cooperative-act fraction."""
        self.reporter.collect(self)              # t=0 baseline (initial mix, no acts yet)
        for _ in range(n_generations):
            self.step()
        return {
            "n": self.n,
            "b": self.b, "c": self.c, "q": self.q,
            "interactions_per_agent": self.interactions_per_agent,
            "m": self.m, "mu": self.mu,
            "seed": self.seed_value,
            "n_generations": n_generations,
            "coop_act_series": self.reporter.series("coop_act_fraction"),
            "coop_strategy_series": self.reporter.series("coop_strategy_fraction"),
            "mean_k_series": self.reporter.series("mean_k"),
            "freq_k0_series": self.reporter.series("freq_k0"),
            "final_strategy_counts": self.strategy_counts(),
            "final_mean_k": self.mean_k(),
            "final_freq_k0": self.strategy_frequency(0),
            "final_coop_strategy_fraction": self.coop_strategy_fraction(),
        }


# -- summary helpers ----------------------------------------------------------

def tail_mean(series: List[float], *, last: int = 100) -> float:
    """Steady-state estimate = mean of the trailing ``last`` of a series (or the whole
    series if shorter). Averages out the finite-population generational jitter."""
    if not series:
        return 0.0
    tail = series[-last:] if len(series) >= last else list(series)
    return sum(tail) / len(tail)


def run_single(n: int = 100, *, b: float = 1.0, c: float = 0.1, q: float = 1.0,
               interactions_per_agent: int = 10, mu: float = 0.0,
               init_strategy: Optional[str] = None, seed: int = 0,
               n_generations: int = 500) -> Dict[str, Any]:
    """One image-scoring run at a given (q, mu, seed) and the fixed payoffs."""
    return ImageScoringModel(
        n, b=b, c=c, q=q, interactions_per_agent=interactions_per_agent, mu=mu,
        init_strategy=init_strategy, seed=seed).run(n_generations)


def run_many_seeds(n: int = 100, *, b: float = 1.0, c: float = 0.1, q: float = 1.0,
                   interactions_per_agent: int = 10, mu: float = 0.0,
                   n_seeds: int = 20, seed_base: int = 0,
                   n_generations: int = 500, last: int = 100) -> Dict[str, Any]:
    """Run ``n_seeds`` image-scoring runs (seed ``seed_base + i``) at fixed parameters and
    summarise, across seeds:

      * the steady-state cooperative-act fraction (mean over the last ``last`` gens),
      * the steady-state cooperative-strategy fraction,
      * the steady-state k = 0 frequency and mean |k| (for P1),
      * the modal final strategy (for P1's "k = 0 modal in >= 90% of seeds").

    Returns the per-seed values, their aggregate mean/min/max, the count of seeds whose
    modal final strategy is k = 0, and one representative trajectory (first seed).
    """
    runs = [run_single(n, b=b, c=c, q=q, interactions_per_agent=interactions_per_agent,
                        mu=mu, seed=seed_base + i, n_generations=n_generations)
            for i in range(n_seeds)]

    per_seed_coop_act = [tail_mean(r["coop_act_series"], last=last) for r in runs]
    per_seed_coop_strat = [tail_mean(r["coop_strategy_series"], last=last) for r in runs]
    per_seed_freq_k0 = [tail_mean(r["freq_k0_series"], last=last) for r in runs]
    per_seed_mean_k = [tail_mean(r["mean_k_series"], last=last) for r in runs]
    per_seed_final_freq_k0 = [r["final_freq_k0"] for r in runs]
    per_seed_final_mean_k = [r["final_mean_k"] for r in runs]

    # Modal final strategy per seed (which threshold has the most players at the end).
    per_seed_modal_k = [modal_strategy(r["final_strategy_counts"]) for r in runs]
    n_modal_k0 = sum(1 for mk in per_seed_modal_k if mk == 0)

    def _agg(vals: List[float]) -> Dict[str, float]:
        mean = sum(vals) / len(vals) if vals else 0.0
        var = sum((v - mean) ** 2 for v in vals) / len(vals) if vals else 0.0
        return {"mean": mean, "std": var ** 0.5, "min": min(vals) if vals else 0.0,
                "max": max(vals) if vals else 0.0}

    return {
        "n": n, "b": b, "c": c, "q": q,
        "interactions_per_agent": interactions_per_agent, "mu": mu,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_generations": n_generations, "last": last,
        "per_seed_coop_act": per_seed_coop_act,
        "per_seed_coop_strategy": per_seed_coop_strat,
        "per_seed_freq_k0": per_seed_freq_k0,
        "per_seed_mean_k": per_seed_mean_k,
        "per_seed_final_freq_k0": per_seed_final_freq_k0,
        "per_seed_final_mean_k": per_seed_final_mean_k,
        "per_seed_modal_k": per_seed_modal_k,
        "coop_act": _agg(per_seed_coop_act),
        "coop_strategy": _agg(per_seed_coop_strat),
        "freq_k0": _agg(per_seed_freq_k0),
        "mean_k": _agg(per_seed_mean_k),
        "mean_abs_k": (sum(abs(v) for v in per_seed_mean_k) / n_seeds) if n_seeds else 0.0,
        "n_modal_k0": n_modal_k0,
        "frac_modal_k0": n_modal_k0 / n_seeds if n_seeds else 0.0,
        "example_coop_act_series": runs[0]["coop_act_series"],
        "example_coop_strategy_series": runs[0]["coop_strategy_series"],
        "example_mean_k_series": runs[0]["mean_k_series"],
        "example_freq_k0_series": runs[0]["freq_k0_series"],
        "example_final_strategy_counts": runs[0]["final_strategy_counts"],
    }


def modal_strategy(counts: Dict[int, int]) -> int:
    """The threshold value with the most players (ties broken toward the smaller |k|, then
    the smaller k — deterministic)."""
    if not counts:
        return K_MIN
    best_k = None
    best_count = -1
    for k in K_VALUES:
        cnt = counts.get(k, 0)
        if cnt > best_count or (cnt == best_count and best_k is not None
                                and (abs(k), k) < (abs(best_k), best_k)):
            best_count = cnt
            best_k = k
    return best_k if best_k is not None else K_MIN
