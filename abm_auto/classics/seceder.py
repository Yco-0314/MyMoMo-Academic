"""Seceder model (Dittrich, Liljeros, Soulier & Banzhaf 2000) — a faithful
agent-based reproduction.

Source: Dittrich, P., Liljeros, F., Soulier, A. & Banzhaf, W. (2000),
"Spontaneous group formation in the Seceder model", Phys. Rev. Lett.
84(14):3205-3208. doi:10.1103/PhysRevLett.84.3205.

The seceder model is the canonical demonstration that a *single* "select the
outlier to reproduce" rule spontaneously splits a structureless population into
several stable groups — diversity is created and maintained by the same local
move, with no global coordination and no externally imposed niches.

Mechanism (one trait dimension, the standard 1D model):

  * N ``EntityAgent``s, each carrying a real-valued trait ``x`` (initialised
    ~ N(0, 1) — a single structureless blob).
  * REPRODUCTION EVENT (repeated many times): draw 3 DISTINCT entities uniformly
    at random; compute their mean ``m``. The "seceder" is the one of the 3 whose
    trait is FARTHEST from m (max |x - m|). The seceder reproduces: a mutated
    offspring with trait ``x_seceder + N(0, sigma_mut)`` is created and REPLACES a
    uniformly random entity in the population (so N is constant).

Selecting the *outlier* of a sampled triple to reproduce is what drives
diversification: the population keeps moving AWAY from its own local centre, so a
single blob splits and the sub-groups push apart until they reach a dynamic
balance — neither merging back nor drifting apart without bound. The standard 1D
model settles into ~3 groups.

Locked grading metrics (fixed BEFORE running; see PREDICTIONS-locked.md):

  * CLUSTER COUNT — sort the N trait values; declare a cluster boundary wherever
    the gap between consecutive sorted values exceeds ``gap_factor * sigma_mut``
    (``gap_factor`` fixed at 3, so a boundary is a gap > 0.6 at sigma_mut=0.2).
    A run of values between boundaries is a candidate cluster; it COUNTS as a
    cluster only if it holds at least ``min_occupancy`` entities (fixed at 5 — a
    floor of N*0.025 — so a lone mutation-noise straggler does not inflate the
    count). This rule is deterministic and parameter-locked.
  * POPULATION VARIANCE — the variance of the N traits. The mutation floor is the
    per-offspring mutation scale ``sigma_mut**2`` (= 0.04 here); a collapsed
    single-point population would sit at that floor, so "diversity persists" means
    variance stays MANY TIMES larger than ``sigma_mut**2``.

Built on the neutral platform (``abm_auto._platform``): each entity is an
``EntityAgent`` carrying its own trait; ``SecederModel`` owns the trait array and
drives reproduction events over the roster, recording (via a ``DataCollector``) a
late-run time series of (cluster count, variance) so P3 (stability, not a
transient) can be graded at several late time points. Deterministic given seed
(the only randomness is the seeded init draw + the seeded reproduction events).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- locked cluster-counting rule ---------------------------------------------

def count_clusters(traits: Sequence[float], *, sigma_mut: float,
                   gap_factor: float = 3.0, min_occupancy: int = 5) -> int:
    """Number of clusters on the 1D trait line, by the LOCKED rule.

    Sort the traits; a cluster boundary is any consecutive gap exceeding
    ``gap_factor * sigma_mut``. A maximal run of values between boundaries is a
    candidate cluster, and it counts only if it holds at least ``min_occupancy``
    entities (so single mutation-noise stragglers do not inflate the count).

    ``gap_factor`` (=3) and ``min_occupancy`` (=5) are fixed before running.
    Returns 0 for an empty population.
    """
    vals = sorted(float(v) for v in traits)
    if not vals:
        return 0
    threshold = gap_factor * sigma_mut
    # Partition the sorted values into maximal runs separated by large gaps.
    sizes: List[int] = []
    run = 1
    for prev, cur in zip(vals, vals[1:]):
        if cur - prev > threshold:
            sizes.append(run)
            run = 1
        else:
            run += 1
    sizes.append(run)
    return sum(1 for s in sizes if s >= min_occupancy)


def population_variance(traits: Sequence[float]) -> float:
    """Population variance (divide by N) of the trait values. 0 for <2 entities."""
    n = len(traits)
    if n < 2:
        return 0.0
    mean = sum(traits) / n
    return sum((x - mean) ** 2 for x in traits) / n


# -- Agent --------------------------------------------------------------------

class EntityAgent(Agent):
    """One entity carrying a real-valued 1D trait ``x``.

    Reproduction is a model-level event (sample a triple, pick + clone the
    seceder, replace a random entity), not an autonomous per-agent step, so the
    per-agent ``step`` is intentionally a no-op."""

    def __init__(self, agent_id: int, model: "SecederModel", *, x: float) -> None:
        super().__init__(agent_id, model)
        self.x = float(x)

    def step(self) -> None:  # pragma: no cover - reproduction lives on the model
        """The reproduction event is a model-level update, not an autonomous
        single-agent step, so this is a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class SecederModel(AgentModel):
    """Drives the Dittrich et al. (2000) seceder dynamics on a 1D trait.

    Construct with N, the mutation scale ``sigma_mut``, the initial trait spread
    ``init_sigma`` (~N(0, init_sigma)), the locked cluster rule parameters, and a
    seed. ``run(...)`` performs reproduction events and records a late-run time
    series of (cluster count, variance).
    """

    def __init__(self, n: int = 200, *, sigma_mut: float = 0.2,
                 init_sigma: float = 1.0, gap_factor: float = 3.0,
                 min_occupancy: int = 5, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n < 3:
            raise ValueError(f"need n >= 3 (a reproduction event samples 3) (got {n})")
        if sigma_mut <= 0:
            raise ValueError(f"need sigma_mut > 0 (got {sigma_mut})")
        if init_sigma < 0:
            raise ValueError(f"need init_sigma >= 0 (got {init_sigma})")
        if gap_factor <= 0:
            raise ValueError(f"need gap_factor > 0 (got {gap_factor})")
        if min_occupancy < 1:
            raise ValueError(f"need min_occupancy >= 1 (got {min_occupancy})")
        self.seed_value = seed
        self.n = n
        self.sigma_mut = float(sigma_mut)
        self.init_sigma = float(init_sigma)
        self.gap_factor = float(gap_factor)
        self.min_occupancy = int(min_occupancy)

        # Initial population: one structureless blob ~ N(0, init_sigma). This
        # seeded draw is the only init randomness; reproduction events draw from
        # the same seeded RNG chain, so the whole run is deterministic given seed.
        self.agent_list: List[EntityAgent] = []
        for i in range(n):
            x = self.rng.gauss(0.0, self.init_sigma)
            agent = EntityAgent(i, self, x=x)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "clusters": lambda m: m.cluster_count(),
            "variance": lambda m: m.variance(),
        })

    # -- trait views --
    def traits(self) -> List[float]:
        """The current trait values, in roster order."""
        return [a.x for a in self.agent_list]

    # -- metrics --
    def cluster_count(self) -> int:
        """Cluster count by the locked gap-cut + minimum-occupancy rule."""
        return count_clusters(self.traits(), sigma_mut=self.sigma_mut,
                              gap_factor=self.gap_factor,
                              min_occupancy=self.min_occupancy)

    def variance(self) -> float:
        """Population variance of the current trait values."""
        return population_variance(self.traits())

    @property
    def mutation_floor(self) -> float:
        """The mutation-noise variance scale ``sigma_mut**2`` — the variance a
        fully collapsed (single-point) population would sit near. P2 requires the
        real variance to stay many times larger than this."""
        return self.sigma_mut ** 2

    # -- the elementary event: one reproduction --
    def reproduction_event(self) -> Tuple[int, int]:
        """One seceder reproduction event.

        Sample 3 DISTINCT entities uniformly at random; the seceder is the one of
        the 3 farthest (max |x - mean|) from their 3-mean. A mutated offspring
        ``x_seceder + N(0, sigma_mut)`` replaces a uniformly random entity (any of
        the N, so N is constant). Returns (seceder roster index, replaced roster
        index) for inspection/tests.
        """
        n = self.n
        # 3 distinct entities (rng.sample is without replacement).
        idx = self.rng.sample(range(n), 3)
        xs = [self.agent_list[i].x for i in idx]
        m = (xs[0] + xs[1] + xs[2]) / 3.0
        # The seceder = farthest from the triple's mean (ties: first max, stable).
        sec_local = max(range(3), key=lambda k: abs(xs[k] - m))
        sec_idx = idx[sec_local]
        offspring = self.agent_list[sec_idx].x + self.rng.gauss(0.0, self.sigma_mut)
        # Replace a uniformly random entity (keeps N constant). Drawn over all N;
        # may coincide with a sampled entity — that is the faithful model.
        rep_idx = self.rng.randrange(n)
        self.agent_list[rep_idx].x = offspring
        return sec_idx, rep_idx

    def step(self) -> None:
        """One model 'tick' = N reproduction events (a generation-equivalent
        sweep), then advance ``t`` and collect the (cluster count, variance)
        sample. A tick is the natural measurement granularity for the late-run
        stability series."""
        for _ in range(self.n):
            self.reproduction_event()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, generations: int = 400, *,  # type: ignore[override]
            measure_last: int = 100) -> Dict[str, Any]:
        """Run ``generations`` ticks (each = N reproduction events); return the
        run summary.

        ``measure_last`` is the trailing window of ticks over which the late-run
        cluster count and variance are summarised (P1/P2 read the steady values,
        P3 reads the late-window series for stability). Returns the final trait
        array, final + steady cluster count and variance, and the full per-tick
        series of both.
        """
        if generations <= 0:
            raise ValueError(f"need generations > 0 (got {generations})")
        if measure_last <= 0 or measure_last > generations + 1:
            raise ValueError(
                f"measure_last must be in [1, generations+1] "
                f"(got {measure_last}, generations={generations})")
        self.reporter.collect(self)              # t=0 baseline (the initial blob)
        for _ in range(generations):
            self.step()
        cluster_series = self.reporter.series("clusters")
        var_series = self.reporter.series("variance")
        # Late-window (trailing measure_last ticks) summaries.
        late_clusters = cluster_series[-measure_last:]
        late_var = var_series[-measure_last:]
        # Mode (most common) cluster count over the late window — the "steady" count.
        steady_clusters = _mode_int(late_clusters)
        steady_var = sum(late_var) / len(late_var)
        return {
            "n": self.n,
            "sigma_mut": self.sigma_mut,
            "init_sigma": self.init_sigma,
            "gap_factor": self.gap_factor,
            "min_occupancy": self.min_occupancy,
            "mutation_floor": self.mutation_floor,
            "seed": self.seed_value,
            "generations": generations,
            "measure_last": measure_last,
            "final_traits": self.traits(),
            "final_clusters": cluster_series[-1],
            "final_variance": var_series[-1],
            "steady_clusters": steady_clusters,
            "steady_variance": steady_var,
            "late_cluster_counts": list(late_clusters),
            "late_variances": list(late_var),
            "min_late_clusters": min(late_clusters),
            "max_late_clusters": max(late_clusters),
            "cluster_series": cluster_series,
            "variance_series": var_series,
        }


# -- summary helpers ----------------------------------------------------------

def _mode_int(values: Sequence[int]) -> int:
    """Most-common integer in a sequence (ties: the smallest such value). 0 for
    empty. Used for the 'steady' cluster count over the late window — the count
    the late run spends most of its time at."""
    if not values:
        return 0
    counts: Dict[int, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    best = max(counts.values())
    return min(k for k, c in counts.items() if c == best)


def run_single(n: int = 200, *, sigma_mut: float = 0.2, init_sigma: float = 1.0,
               gap_factor: float = 3.0, min_occupancy: int = 5, seed: int = 0,
               generations: int = 400, measure_last: int = 100) -> Dict[str, Any]:
    """One seceder run at a given seed and the fixed model + cluster parameters."""
    return SecederModel(n, sigma_mut=sigma_mut, init_sigma=init_sigma,
                        gap_factor=gap_factor, min_occupancy=min_occupancy,
                        seed=seed).run(generations, measure_last=measure_last)


def run_many_seeds(n: int = 200, *, sigma_mut: float = 0.2, init_sigma: float = 1.0,
                   gap_factor: float = 3.0, min_occupancy: int = 5,
                   n_seeds: int = 5, seed_base: int = 0, generations: int = 400,
                   measure_last: int = 100) -> Dict[str, Any]:
    """Run ``n_seeds`` seceder runs (seed ``seed_base + i``) at fixed parameters and
    summarise the steady cluster count and variance across seeds.

    Returns the per-seed steady cluster counts + steady variances, their spread,
    the mutation floor, the worst-case late-window cluster stability (so P3 can be
    graded as 'count constant over the late run, every seed'), and one
    representative trajectory (first seed) of both series for inspection.
    """
    runs = [run_single(n, sigma_mut=sigma_mut, init_sigma=init_sigma,
                       gap_factor=gap_factor, min_occupancy=min_occupancy,
                       seed=seed_base + i, generations=generations,
                       measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_clusters = [rr["steady_clusters"] for rr in runs]
    per_seed_final_clusters = [rr["final_clusters"] for rr in runs]
    per_seed_var = [rr["steady_variance"] for rr in runs]
    per_seed_final_var = [rr["final_variance"] for rr in runs]
    # Late-window cluster spread per seed (max - min over the trailing window):
    # 0 means the count never moved in the late run for that seed.
    per_seed_late_spread = [rr["max_late_clusters"] - rr["min_late_clusters"]
                            for rr in runs]
    mutation_floor = sigma_mut ** 2
    mean_clusters = sum(per_seed_clusters) / n_seeds
    mean_var = sum(per_seed_var) / n_seeds
    var_of_var = sum((s - mean_var) ** 2 for s in per_seed_var) / n_seeds
    return {
        "n": n, "sigma_mut": sigma_mut, "init_sigma": init_sigma,
        "gap_factor": gap_factor, "min_occupancy": min_occupancy,
        "mutation_floor": mutation_floor,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "generations": generations, "measure_last": measure_last,
        "per_seed_steady_clusters": per_seed_clusters,
        "per_seed_final_clusters": per_seed_final_clusters,
        "per_seed_steady_variance": per_seed_var,
        "per_seed_final_variance": per_seed_final_var,
        "per_seed_late_cluster_spread": per_seed_late_spread,
        "mean_steady_clusters": mean_clusters,
        "min_steady_clusters": min(per_seed_clusters),
        "max_steady_clusters": max(per_seed_clusters),
        "mean_steady_variance": mean_var,
        "std_steady_variance": var_of_var ** 0.5,
        "min_steady_variance": min(per_seed_var),
        "max_steady_variance": max(per_seed_var),
        "max_late_cluster_spread": max(per_seed_late_spread),
        # variance / mutation-floor ratio across seeds (the P2 quantity).
        "mean_variance_over_floor": (mean_var / mutation_floor
                                     if mutation_floor > 0 else float("inf")),
        "min_variance_over_floor": (min(per_seed_var) / mutation_floor
                                    if mutation_floor > 0 else float("inf")),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_cluster_series": runs[0]["cluster_series"],
        "example_variance_series": runs[0]["variance_series"],
    }
