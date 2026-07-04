"""Tag-based cooperation (Riolo, Cohen & Axelrod 2001) — a faithful agent-based
reproduction.

Source: Riolo, R.L., Cohen, M.D. & Axelrod, R. (2001), "Evolution of cooperation
without reciprocity", Nature 414:441-443. doi:10.1038/35106555.

The question the paper answers: can cooperation evolve among agents that share an
arbitrary, observable *tag* (a heritable colour/marker with no intrinsic meaning),
WITHOUT any reciprocity, memory, reputation, or repeated interaction? The answer is
yes — tag similarity alone, coupled with a heritable *tolerance*, sustains substantial
donation, and it does so in characteristic WAVES rather than a steady plateau.

Rules (verified against the paper's canonical model):

  * A well-mixed population of ``N`` = 100 agents. Each agent carries two heritable
    continuous traits: a TAG ``tau`` in [0, 1] (an arbitrary observable marker) and a
    TOLERANCE ``T`` >= 0. Both are initialised uniformly on [0, 1].
  * Each GENERATION has two phases:
      (1) DONATION (payoff). Each agent, as a potential DONOR, is paired with ``P`` = 3
          RANDOM recipients drawn WITH REPLACEMENT from the other agents. For each such
          pairing the donor donates to the recipient iff the recipient's tag is within
          the donor's tolerance of the donor's own tag:  |tau_recip - tau_donor| <= T_donor.
          A donation costs the donor ``c`` = 0.1 and gives the recipient ``b`` = 1.0.
          An agent's fitness this generation is the accumulated payoff (benefits received
          as a recipient minus costs paid as a donor). (This is the paper's "P pairings
          per agent" protocol: N*P ordered donor->recipient trials per generation.)
      (2) REPRODUCTION (selection + mutation). The next generation is formed by
          TOURNAMENT: for each of the N slots, one agent is compared with one other
          RANDOM agent and the FITTER of the two is copied (ties -> the challenger, i.e.
          the second agent, by convention). The copy is then MUTATED: with a fixed
          per-offspring probability the tag gets Gaussian noise (sd ``sigma``) reflected/
          clamped into [0, 1] and the tolerance gets Gaussian noise (sd ``sigma``) and is
          truncated at 0 (never negative). Mutation rate and sd are FIXED.
  * Run for ``generations`` = 30,000 generations over >= 10 seeds.

Signature dynamics (what distinguishes this model, and the locked predictions):

  * A DOMINANT TAG CLUSTER forms: the population collapses onto a narrow band of tags
    (an in-group that donates to itself), so a large share of agents share (almost
    exactly) one modal tag.
  * Cooperation is INTERMITTENT — waves, not a plateau. Tolerance drifts upward under
    neutral/near-neutral drift while a cluster dominates (donating within-cluster is
    cheap and beneficial); rising tolerance eventually lets tolerant agents donate to
    dissimilar "free-riders" (agents just outside the cluster who receive but rarely
    give), which crashes cooperation; a new tighter cluster then invades and cooperation
    recovers. This tolerance-drift-then-invasion cycle is the paper's characteristic
    wave, absent from a fixed-plateau model.

Distinct from Hammond-Axelrod ethnocentrism (also tag-based): that model is SPATIAL
(a lattice with local interaction and 4 discrete tag-strategies); THIS model is
WELL-MIXED (random pairing, no space), with a CONTINUOUS tag + a CONTINUOUS tolerance,
and its signature is the tolerance-drift wave — not a spatial in-group/out-group split.

Built on the neutral platform (``abm_auto._platform``): each agent is a state-carrying
``TagAgent`` on an ``AgentSet`` roster; ``TagCooperationModel`` drives the two-phase
generation (donation then tournament reproduction) at the model level and records, via a
``DataCollector``, the per-generation donation rate and the dominant-tag-cluster share.
The per-generation donation + reproduction arithmetic is vectorised with numpy (N*P
donations and N tournaments per generation over 30,000 generations); the vectorised path
is the model, and a small pure-Python reference (:func:`donation_rate_reference`) pins it
in the tests.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from abm_auto._platform import Agent, AgentModel, DataCollector

# Riolo-Cohen-Axelrod canonical constants (FIXED — see PREDICTIONS-locked.md; NOT tuned).
N_AGENTS = 100         # population size
PAIRINGS = 3           # P: potential recipients per donor per generation (with replacement)
COST = 0.1             # c: cost to the donor of a donation
BENEFIT = 1.0          # b: benefit to the recipient of a donation
MUTATION_RATE = 0.1    # per-offspring probability of mutating (each trait mutated)
MUTATION_SIGMA = 0.01  # sd of the Gaussian mutation on tag and on tolerance
GENERATIONS = 30_000   # generations per run
CLUSTER_EPS = 0.01     # |tau - modal tau| <= this counts as "in the dominant cluster"


# -- Agent --------------------------------------------------------------------

class TagAgent(Agent):
    """One agent: a heritable continuous tag ``tau`` in [0, 1] and a heritable
    tolerance ``T`` >= 0, plus a per-generation fitness accumulator.

    The Riolo-Cohen-Axelrod generation (all-pairs donation, then a population-wide
    tournament) is a model-level synchronous update over the whole roster, so the
    per-agent ``step`` is intentionally a no-op — the agent is a typed state carrier
    (tau, T, fitness) and the two-phase generation lives on the model."""

    def __init__(self, agent_id: int, model: "TagCooperationModel", *,
                 tau: float, tolerance: float) -> None:
        super().__init__(agent_id, model)
        self.tau = tau
        self.tolerance = tolerance
        self.fitness = 0.0

    def step(self) -> None:  # pragma: no cover - the generation lives on the model
        """The generation (all-pairs donation + tournament reproduction) is a
        model-level synchronous update, not an autonomous single-agent step."""
        return None


# -- pure-Python reference (pins the vectorised donation arithmetic in tests) ---

def donates(tau_donor: float, tolerance_donor: float, tau_recipient: float) -> bool:
    """The donation predicate: a donor donates to a recipient iff the recipient's tag
    is within the donor's tolerance of the donor's own tag."""
    return abs(tau_recipient - tau_donor) <= tolerance_donor


def donation_rate_reference(tau: Sequence[float], tol: Sequence[float],
                            partners: Sequence[Sequence[int]]) -> float:
    """Pure-Python reference donation rate for a fixed partner assignment.

    ``partners[i]`` is the list of recipient indices agent ``i`` is paired with this
    generation. The donation rate is the fraction of all (donor, recipient) trials in
    which the donor actually donated. Used only to validate the vectorised model path in
    the tests; the model itself uses the numpy path (identical result)."""
    donated = 0
    total = 0
    for i, recips in enumerate(partners):
        for j in recips:
            total += 1
            if donates(tau[i], tol[i], tau[j]):
                donated += 1
    return donated / total if total else 0.0


# -- Model --------------------------------------------------------------------

class TagCooperationModel(AgentModel):
    """Drives the Riolo-Cohen-Axelrod (2001) tag-based cooperation dynamics.

    Construct with N, the donation parameters (P, cost, benefit), the mutation
    parameters (rate, sigma), the number of generations, and a seed. ``run()`` advances
    the two-phase generation (donation payoff, then tournament reproduction with
    mutation) and records the per-generation donation rate and dominant-tag-cluster
    share.

    The state of generation ``g`` lives in two numpy arrays (``self.tau``, ``self.tol``)
    that the ``TagAgent`` roster mirrors (each agent's ``tau``/``tolerance`` is synced
    from the arrays each generation so the roster stays a faithful, inspectable view of
    the population). All randomness flows from the single seeded ``numpy`` Generator so a
    run is fully reproducible given its seed.
    """

    def __init__(self, n: int = N_AGENTS, *, pairings: int = PAIRINGS,
                 cost: float = COST, benefit: float = BENEFIT,
                 mutation_rate: float = MUTATION_RATE, mutation_sigma: float = MUTATION_SIGMA,
                 generations: int = GENERATIONS, cluster_eps: float = CLUSTER_EPS,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 1:
            raise ValueError(f"need n > 1 (got {n})")
        if pairings <= 0:
            raise ValueError(f"need pairings > 0 (got {pairings})")
        if cost < 0 or benefit < 0:
            raise ValueError(f"need cost>=0, benefit>=0 (got cost={cost}, benefit={benefit})")
        if not (0.0 <= mutation_rate <= 1.0):
            raise ValueError(f"need 0<=mutation_rate<=1 (got {mutation_rate})")
        if mutation_sigma < 0:
            raise ValueError(f"need mutation_sigma>=0 (got {mutation_sigma})")
        if generations < 0:
            raise ValueError(f"need generations>=0 (got {generations})")
        self.seed_value = seed
        self.n = n
        self.pairings = pairings
        self.cost = float(cost)
        self.benefit = float(benefit)
        self.mutation_rate = float(mutation_rate)
        self.mutation_sigma = float(mutation_sigma)
        self.generations = generations
        self.cluster_eps = float(cluster_eps)

        # Single seeded numpy Generator — the only source of randomness in the run.
        self.gen = np.random.default_rng(seed)

        # Initial population: tag and tolerance both ~ U[0, 1].
        self.tau = self.gen.random(n)
        self.tol = self.gen.random(n)

        # Mirror the arrays onto a TagAgent roster (a faithful, inspectable population
        # view; the arithmetic runs on the arrays for speed).
        self.agent_list: List[TagAgent] = []
        for i in range(n):
            agent = TagAgent(i, self, tau=float(self.tau[i]), tolerance=float(self.tol[i]))
            self.agent_list.append(agent)
            self.add_agent(agent)

        # Last-generation realized donation rate (filled by the donation phase).
        self._last_donation_rate = 0.0

        self.reporter = DataCollector({
            "donation_rate": lambda m: m._last_donation_rate,
            "cluster_share": lambda m: m.dominant_cluster_share(),
            "mean_tolerance": lambda m: float(np.mean(m.tol)),
        })

    # -- one generation: donation payoff, then tournament reproduction --
    def _donate_and_score(self) -> np.ndarray:
        """Donation phase. Each of the ``n`` donors is paired with ``pairings`` random
        recipients drawn WITH REPLACEMENT from the OTHER agents; a donation happens iff
        the recipient's tag is within the donor's tolerance of the donor's own tag.

        Returns the per-agent fitness (benefits received minus costs paid) and stores the
        realized donation rate (fraction of the n*pairings trials that were donations)
        in ``self._last_donation_rate``."""
        n, P = self.n, self.pairings
        # recipients[i, k] = the k-th recipient index for donor i, drawn from the OTHER
        # agents (self-donation excluded). Draw an offset in [1, n-1] and add mod n so a
        # donor is never paired with itself, uniform over the other n-1 agents.
        offsets = self.gen.integers(1, n, size=(n, P))
        recipients = (np.arange(n)[:, None] + offsets) % n

        tau_donor = self.tau[:, None]                 # (n, 1)
        tol_donor = self.tol[:, None]                 # (n, 1)
        tau_recip = self.tau[recipients]              # (n, P)
        donate = np.abs(tau_recip - tau_donor) <= tol_donor   # (n, P) bool

        self._last_donation_rate = float(donate.mean())

        fitness = np.zeros(n, dtype=float)
        # donor pays cost for each donation it makes
        np.add.at(fitness, np.arange(n), -self.cost * donate.sum(axis=1))
        # each recipient receives benefit for each donation aimed at it
        np.add.at(fitness, recipients[donate], self.benefit)
        return fitness

    def _reproduce(self, fitness: np.ndarray) -> None:
        """Reproduction phase. Form the next generation by TOURNAMENT: for each of the n
        slots, one focal agent is compared with one random OTHER agent and the fitter is
        copied; the copy is then mutated (tag Gaussian, reflected into [0,1]; tolerance
        Gaussian, truncated at 0), each trait mutated with prob ``mutation_rate``.

        Ties resolve to the challenger (the random opponent) — a fixed, seed-independent
        convention. The winners' (tau, tol) become the parents of the next generation."""
        n = self.n
        focal = np.arange(n)
        offsets = self.gen.integers(1, n, size=n)     # opponent != focal
        opponent = (focal + offsets) % n
        # winner = fitter of (focal, opponent); tie -> opponent (challenger).
        focal_wins = fitness[focal] > fitness[opponent]
        winners = np.where(focal_wins, focal, opponent)

        new_tau = self.tau[winners].copy()
        new_tol = self.tol[winners].copy()

        # Mutation: each trait mutated independently with prob mutation_rate.
        mut_tau = self.gen.random(n) < self.mutation_rate
        mut_tol = self.gen.random(n) < self.mutation_rate
        new_tau[mut_tau] += self.gen.normal(0.0, self.mutation_sigma, size=int(mut_tau.sum()))
        new_tol[mut_tol] += self.gen.normal(0.0, self.mutation_sigma, size=int(mut_tol.sum()))

        # tag reflected into [0, 1]; tolerance truncated at 0 (never negative).
        new_tau = _reflect_unit_interval(new_tau)
        new_tol = np.maximum(new_tol, 0.0)

        self.tau = new_tau
        self.tol = new_tol
        self._sync_roster()

    def _sync_roster(self) -> None:
        """Copy the current population arrays back onto the TagAgent roster so the agents
        stay a faithful view of (tau, tolerance)."""
        for i, a in enumerate(self.agent_list):
            a.tau = float(self.tau[i])
            a.tolerance = float(self.tol[i])

    # -- metrics --
    def dominant_cluster_share(self) -> float:
        """Share of the population within ``cluster_eps`` of the MODAL tag.

        The modal tag is estimated by the densest fine bin (bin width = cluster_eps) of
        the tag distribution; the share is the fraction of agents whose tag lies within
        cluster_eps of that bin's centre. A high share means the population has collapsed
        onto one narrow tag band (a dominant in-group cluster)."""
        tau = self.tau
        eps = self.cluster_eps
        # bin the tags at resolution eps; the fullest bin centres the modal cluster.
        nb = max(1, int(round(1.0 / eps)))
        counts, edges = np.histogram(tau, bins=nb, range=(0.0, 1.0))
        k = int(np.argmax(counts))
        modal = 0.5 * (edges[k] + edges[k + 1])
        return float(np.mean(np.abs(tau - modal) <= eps))

    # -- tick (one generation) --
    def step(self) -> None:  # type: ignore[override]
        """One Riolo-Cohen-Axelrod generation: donation payoff, then tournament
        reproduction with mutation, then record the per-generation series."""
        fitness = self._donate_and_score()
        self._reproduce(fitness)
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``generations`` generations; return the run summary.

        The recorded series has one entry per generation (the donation rate is the rate
        realized in that generation's donation phase, and the cluster share / mean
        tolerance are measured on the post-reproduction population). Returns the config,
        the per-generation donation-rate, cluster-share and mean-tolerance series.
        """
        # No t=0 baseline row: the donation rate is only defined after a donation phase,
        # so the series is exactly one entry per generation.
        for _ in range(self.generations):
            self.step()
        return {
            "n": self.n,
            "pairings": self.pairings,
            "cost": self.cost,
            "benefit": self.benefit,
            "mutation_rate": self.mutation_rate,
            "mutation_sigma": self.mutation_sigma,
            "generations": self.generations,
            "cluster_eps": self.cluster_eps,
            "seed": self.seed_value,
            "donation_rate_series": self.reporter.series("donation_rate"),
            "cluster_share_series": self.reporter.series("cluster_share"),
            "mean_tolerance_series": self.reporter.series("mean_tolerance"),
        }


# -- helpers ------------------------------------------------------------------

def _reflect_unit_interval(x: np.ndarray) -> np.ndarray:
    """Reflect values back into [0, 1] (a Gaussian tag mutation that overshoots a
    boundary bounces off it, keeping the tag a valid marker in [0, 1] without the
    distortion of hard clamping to a wall). Idempotent for x already in [0, 1]."""
    y = np.abs(x)                       # reflect at 0
    y = np.where(y > 1.0, 2.0 - y, y)   # reflect at 1
    # a single reflection handles the mutation-scale overshoots we ever see; clamp any
    # pathological far-overshoot as a final guard.
    return np.clip(y, 0.0, 1.0)


def _mean(xs: Sequence[float]) -> float:
    return float(np.mean(xs)) if len(xs) else 0.0


def _std(xs: Sequence[float]) -> float:
    return float(np.std(xs, ddof=0)) if len(xs) else 0.0


def _cv(xs: Sequence[float]) -> float:
    """Coefficient of variation (sd/mean) of a series; 0 if the mean is ~0."""
    m = _mean(xs)
    if abs(m) < 1e-12:
        return 0.0
    return _std(xs) / m


def has_crash_and_recover(series: Sequence[float], *, window: int = 200,
                          crash_frac: float = 0.5, recover_frac: float = 0.9) -> bool:
    """Detect at least one CRASH-AND-RECOVER event in a donation-rate series.

    A crash-and-recover: the series drops below ``crash_frac`` x its running mean, then
    later returns above ``recover_frac`` x its (updated) running mean. The running mean
    is a trailing window of length ``window`` (a local baseline, so a slow global drift
    does not mask a local wave). This is the locked P3 event detector (drop below
    0.5x running-mean, then back above 0.9x running-mean)."""
    xs = np.asarray(series, dtype=float)
    if xs.size == 0:
        return False
    crashed = False
    for i in range(xs.size):
        lo = max(0, i - window + 1)
        rmean = float(np.mean(xs[lo:i + 1]))
        if rmean <= 1e-12:
            continue
        if not crashed:
            if xs[i] < crash_frac * rmean:
                crashed = True
        else:
            if xs[i] > recover_frac * rmean:
                return True
    return False


# -- summary + multi-seed drivers ---------------------------------------------

def summarize_run(res: Dict[str, Any], *, burn_in: int = 100,
                  cv_window: int = 200) -> Dict[str, Any]:
    """Post-transient summary of one run (the locked measurement window is gen>burn_in).

    Returns the mean donation rate, the time-averaged cluster share, the within-run CV of
    the donation rate, and whether the run has >=1 crash-and-recover event — all over the
    post-burn-in series (the locked P1/P2/P3 quantities)."""
    dr = res["donation_rate_series"][burn_in:]
    cs = res["cluster_share_series"][burn_in:]
    return {
        "seed": res.get("seed"),
        "mean_donation_rate": _mean(dr),
        "mean_cluster_share": _mean(cs),
        "cv_donation_rate": _cv(dr),
        "has_crash_recover": has_crash_and_recover(dr, window=cv_window),
        "mean_tolerance_tail": _mean(res["mean_tolerance_series"][burn_in:]),
    }


def run_single(*, n: int = N_AGENTS, pairings: int = PAIRINGS, cost: float = COST,
               benefit: float = BENEFIT, mutation_rate: float = MUTATION_RATE,
               mutation_sigma: float = MUTATION_SIGMA, generations: int = GENERATIONS,
               cluster_eps: float = CLUSTER_EPS, seed: int = 0) -> Dict[str, Any]:
    """One full tag-cooperation run at the given parameters + seed."""
    return TagCooperationModel(
        n, pairings=pairings, cost=cost, benefit=benefit, mutation_rate=mutation_rate,
        mutation_sigma=mutation_sigma, generations=generations, cluster_eps=cluster_eps,
        seed=seed).run()


def run_many_seeds(seeds: Sequence[int], *, n: int = N_AGENTS, pairings: int = PAIRINGS,
                   cost: float = COST, benefit: float = BENEFIT,
                   mutation_rate: float = MUTATION_RATE, mutation_sigma: float = MUTATION_SIGMA,
                   generations: int = GENERATIONS, cluster_eps: float = CLUSTER_EPS,
                   burn_in: int = 100, cv_window: int = 200,
                   keep_series_for_seed: Optional[int] = None) -> Dict[str, Any]:
    """Run one simulation per seed at a FIXED config and summarise the post-transient
    donation rate, dominant-cluster share, donation-rate CV, and crash-and-recover
    incidence across seeds.

    Returns per-seed summary rows plus cross-seed aggregates (mean donation rate + its
    spread, mean cluster share, fraction of seeds with a crash-and-recover event, and the
    mean within-run CV). One representative run's full series (the first seed, or
    ``keep_series_for_seed``) is kept for plotting/inspection.
    """
    rows: List[Dict[str, Any]] = []
    kept_series: Optional[Dict[str, Any]] = None
    keep = seeds[0] if (keep_series_for_seed is None and seeds) else keep_series_for_seed
    for s in seeds:
        res = run_single(n=n, pairings=pairings, cost=cost, benefit=benefit,
                         mutation_rate=mutation_rate, mutation_sigma=mutation_sigma,
                         generations=generations, cluster_eps=cluster_eps, seed=s)
        rows.append(summarize_run(res, burn_in=burn_in, cv_window=cv_window))
        if s == keep:
            kept_series = {
                "seed": s,
                "donation_rate_series": res["donation_rate_series"],
                "cluster_share_series": res["cluster_share_series"],
                "mean_tolerance_series": res["mean_tolerance_series"],
            }

    donation = [r["mean_donation_rate"] for r in rows]
    cluster = [r["mean_cluster_share"] for r in rows]
    cvs = [r["cv_donation_rate"] for r in rows]
    crash = [r["has_crash_recover"] for r in rows]
    return {
        "config": {
            "n": n, "pairings": pairings, "cost": cost, "benefit": benefit,
            "mutation_rate": mutation_rate, "mutation_sigma": mutation_sigma,
            "generations": generations, "cluster_eps": cluster_eps,
            "burn_in": burn_in, "cv_window": cv_window,
        },
        "seeds": list(seeds),
        "rows": rows,
        "mean_donation_rate": _mean(donation),
        "std_donation_rate": _std(donation),
        "min_donation_rate": min(donation) if donation else 0.0,
        "max_donation_rate": max(donation) if donation else 0.0,
        "mean_cluster_share": _mean(cluster),
        "std_cluster_share": _std(cluster),
        "min_cluster_share": min(cluster) if cluster else 0.0,
        "mean_cv_donation_rate": _mean(cvs),
        "min_cv_donation_rate": min(cvs) if cvs else 0.0,
        "frac_seeds_crash_recover": (sum(1 for c in crash if c) / len(crash)) if crash else 0.0,
        "n_seeds_crash_recover": sum(1 for c in crash if c),
        "example_series": kept_series,
    }
