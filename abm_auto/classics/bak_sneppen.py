"""Bak-Sneppen evolution model (1993) — a faithful self-organized-criticality (SOC)
reproduction.

Source: Bak, P. & Sneppen, K. (1993) "Punctuated equilibrium and criticality in a
simple model of evolution", Phys. Rev. Lett. 71:4083-4086.
doi:10.1103/PhysRevLett.71.4083.

IMPORTANT (honesty, binds the FINDINGS): this is EXTREMAL DYNAMICS / an SOC model,
NOT an agent-stepping ABM. Each step is *model-orchestrated*: it selects the GLOBAL
minimum-fitness species across the whole ring and updates it together with its two
ring-neighbours. There is no scheduler over an agent roster, no per-agent perceive/
decide/act, no autonomous local stepping — the global-min selection is a centralized
operation. We disclose this exactly as the BTW sandpile and ER/WS network-generation
reproductions disclose that they are not agent-based. The lock-first + honest-verdict +
L3-bundle discipline still fully applies.

Rules (the canonical 1D Bak-Sneppen model, verified against the paper):
  * A ring of N species (periodic boundary), each carrying a fitness (barrier) drawn
    ~ U[0, 1). N = 200 here.
  * EXTREMAL UPDATE: at each step find the species with the GLOBAL minimum fitness;
    replace its fitness AND the fitnesses of its two ring-neighbours (i-1, i+1 mod N)
    with three fresh, independent U[0, 1) draws.
  * Iterate for a large number of steps. After a transient the fitness distribution
    self-organizes to a STATIONARY critical state: fitnesses become ~uniform on
    (f_c, 1) with a sharp lower cutoff f_c ~ 0.667, and the activity (the location/
    value of the running minimum) is intermittent — long quiet spells punctuated by
    bursts (avalanches), with a power-law avalanche-size distribution.

Avalanche definition (FIXED before running — see ``avalanches_below``): given a
threshold ``f_c``, an avalanche is a MAXIMAL run of consecutive steps whose active
minimum fitness is < f_c. Its size is the number of steps in that run. (This is the
standard "f_c-avalanche" / "f0-avalanche" of Paczuski, Maslov & Bak 1996.) The
threshold used for the avalanche measurement is the EMPIRICAL stationary cutoff f_c
estimated from the recorded fitness distribution, fixed once and not tuned.

Determinism: the whole run is reproducible given an integer seed (a single
``numpy.random.default_rng(seed)`` draws every fitness). NumPy is used to make the
draws fast; the result is the canonical extremal-dynamics outcome for that seed.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


# -- core extremal dynamics: a single ring ------------------------------------

class BakSneppenRing:
    """A ring of N species fitnesses with the Bak-Sneppen extremal update.

    ``fitness`` is an (N,) float array in [0, 1). ``step`` performs one extremal
    update (find the global min, replace it + its two ring-neighbours with fresh
    U[0,1) draws) and returns the value of the minimum that was just acted on (the
    "active min" for that step). The update is centralized / model-orchestrated, not
    agent-autonomous (disclosed in the module docstring + FINDINGS).
    """

    def __init__(self, n: int, rng: np.random.Generator) -> None:
        if n < 3:
            raise ValueError("N must be >= 3 (each update touches a site + 2 neighbours)")
        self.n = n
        self.rng = rng
        self.fitness = rng.random(n)

    def step(self) -> float:
        """One extremal update. Returns the global-minimum fitness BEFORE replacement
        (the active min for this step). Replaces that site and its two ring-neighbours
        (periodic) with three fresh independent U[0,1) draws."""
        f = self.fitness
        i = int(np.argmin(f))
        active_min = float(f[i])
        n = self.n
        # Periodic ring neighbours.
        left = (i - 1) % n
        right = (i + 1) % n
        f[i] = self.rng.random()
        f[left] = self.rng.random()
        f[right] = self.rng.random()
        return active_min

    def min_fitness(self) -> float:
        return float(self.fitness.min())


# -- drive loop ---------------------------------------------------------------

def run_bak_sneppen(
    n: int = 200,
    *,
    transient: int = 100_000,
    n_steps: int = 1_000_000,
    seed: int = 0,
    fitness_samples: int = 200_000,
) -> Dict[str, Any]:
    """Full SOC experiment: evolve a ring of ``n`` species for ``transient`` burn-in
    steps (discarded), then record ``n_steps`` measured steps.

    Records, over the measured phase:
      * ``active_min`` — the active minimum fitness at each measured step (length
        ``n_steps``; this is the running-minimum time series the avalanche definition
        and the punctuation evidence are built from).
      * ``fitness_snapshots`` — the full ring fitness array sampled every
        ``n_steps // fitness_samples`` steps (concatenated into one pooled sample of
        the STATIONARY fitness distribution, used to estimate f_c and the histogram).

    Deterministic given ``seed`` (one RNG stream draws transient + measured phase).
    Returns a summary dict (no analysis — analysis is done by the runner).
    """
    rng = np.random.default_rng(seed)
    ring = BakSneppenRing(n, rng)

    # Burn through the transient (do not record).
    for _ in range(transient):
        ring.step()

    # Record the stationary phase.
    active_min = np.empty(n_steps, dtype=np.float64)
    sample_every = max(1, n_steps // max(1, fitness_samples))
    snapshots: List[np.ndarray] = []
    for t in range(n_steps):
        active_min[t] = ring.step()
        if t % sample_every == 0:
            snapshots.append(ring.fitness.copy())

    pooled_fitness = (
        np.concatenate(snapshots) if snapshots else ring.fitness.copy()
    )
    return {
        "n": n,
        "transient": transient,
        "n_steps": n_steps,
        "seed": seed,
        "sample_every": sample_every,
        "active_min": active_min,
        "pooled_fitness": pooled_fitness,
        "n_fitness_snapshots": len(snapshots),
        "final_min": ring.min_fitness(),
    }


# -- analysis -----------------------------------------------------------------

def estimate_fc(pooled_fitness: Sequence[float], *, low_percentile: float = 5.0) -> float:
    """Estimate the stationary critical threshold f_c as a LOW PERCENTILE of the pooled
    stationary fitness distribution.

    Rationale (FIXED before the run): in the stationary state most fitnesses lie ~uniform
    on (f_c, 1) with a sharp lower edge at f_c; below f_c the density is strongly
    suppressed. The ``low_percentile``-th percentile of the pooled fitnesses sits just
    above that lower edge and is a robust, tuning-free estimator of where the bulk of the
    distribution begins. We lock the 5th percentile. (We also report the bulk-edge via the
    histogram so the reader can cross-check.) Returns the percentile value in [0,1]."""
    arr = np.asarray(pooled_fitness, dtype=np.float64)
    if arr.size == 0:
        return float("nan")
    return float(np.percentile(arr, low_percentile))


def fitness_histogram(pooled_fitness: Sequence[float], *, n_bins: int = 50) -> List[Dict[str, float]]:
    """Uniform [0,1] histogram of the pooled stationary fitnesses, as density (so a flat
    region integrates to ~1/(1-f_c) above the cutoff). Returns a list of
    {lo, hi, density, count} bins. Lets the reader see the sharp lower edge + the flat
    plateau above it."""
    arr = np.asarray(pooled_fitness, dtype=np.float64)
    if arr.size == 0:
        return []
    counts, edges = np.histogram(arr, bins=n_bins, range=(0.0, 1.0), density=False)
    width = 1.0 / n_bins
    total = float(arr.size)
    out: List[Dict[str, float]] = []
    for i in range(n_bins):
        out.append({
            "lo": float(edges[i]),
            "hi": float(edges[i + 1]),
            "count": int(counts[i]),
            "density": float(counts[i] / (total * width)),
        })
    return out


def avalanches_below(active_min: Sequence[float], f_c: float) -> List[int]:
    """f_c-avalanche sizes (FIXED definition): given the time series of per-step active
    minima and a threshold ``f_c``, an avalanche is a MAXIMAL run of CONSECUTIVE steps
    whose active min is < f_c. Its size is the number of steps in that run. Returns the
    list of avalanche sizes (one int per avalanche), in time order.

    (Standard Paczuski-Maslov-Bak f0-avalanche: the activity drops below f_c, stays
    below for some duration — that burst is one avalanche — then the running min recovers
    above f_c, ending it.)"""
    arr = np.asarray(active_min, dtype=np.float64)
    below = arr < f_c
    sizes: List[int] = []
    run = 0
    for b in below:
        if b:
            run += 1
        elif run > 0:
            sizes.append(run)
            run = 0
    if run > 0:
        sizes.append(run)
    return sizes


def avalanche_size_histogram(sizes: Sequence[int], *, n_bins: int = 30) -> List[Dict[str, float]]:
    """Logarithmically-binned histogram of avalanche sizes (for the heavy-tail visual).
    Geometric bins from 1 to max size; raw counts. Mirrors the BTW sandpile helper."""
    arr = np.asarray(sizes, dtype=np.float64)
    pos = arr[arr >= 1]
    if pos.size == 0:
        return []
    smax = float(pos.max())
    if smax <= 1:
        return [{"lo": 1.0, "hi": 1.0, "count": int(pos.size)}]
    edges = np.unique(np.floor(np.geomspace(1.0, smax, n_bins + 1)).astype(np.int64))
    edges = edges.astype(np.float64)
    out: List[Dict[str, float]] = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == len(edges) - 2:
            count = int(np.sum((pos >= lo) & (pos <= hi)))
        else:
            count = int(np.sum((pos >= lo) & (pos < hi)))
        out.append({"lo": float(lo), "hi": float(hi), "count": count})
    return out


def heavy_tail_stats(sizes: Sequence[int]) -> Dict[str, Any]:
    """Heavy-tail descriptors for P2: decades spanned by the avalanche sizes, the max
    size, the median, and the max/median ratio. 'Decades spanned' = log10(max) -
    log10(min) over the avalanches (min is >= 1 by construction)."""
    arr = np.asarray(sizes, dtype=np.float64)
    pos = arr[arr >= 1]
    if pos.size == 0:
        return {"n": 0, "max": 0.0, "min": 0.0, "median": 0.0, "decades": 0.0,
                "max_over_median": 0.0}
    smax = float(pos.max())
    smin = float(pos.min())
    median = float(np.median(pos))
    decades = math.log10(smax) - math.log10(smin) if smin > 0 else 0.0
    return {
        "n": int(pos.size),
        "max": smax,
        "min": smin,
        "median": median,
        "decades": decades,
        "max_over_median": (smax / median) if median > 0 else float("inf"),
    }


def fit_tau(sizes: Sequence[int], *, kmin: int = 1,
            tau_bracket: Tuple[float, float] = (1.001, 6.0)) -> Dict[str, Any]:
    """Discrete power-law MLE for the avalanche-size tail exponent tau (reporting only;
    NOT a locked clause). Exact discrete MLE for P(s) = s^{-tau}/zeta(tau, kmin) over
    s >= kmin (Clauset, Shalizi & Newman 2009): tau solves
    -zeta'(tau,kmin)/zeta(tau,kmin) = mean_i ln(s_i), solved by Brent root-find. This
    mirrors the BTW sandpile estimator. Returns tau, its asymptotic stderr, and n_tail.
    SciPy is imported lazily so the module has no hard SciPy dependency for the core run."""
    from scipy.optimize import brentq
    from scipy.special import zeta

    arr = np.asarray(sizes, dtype=np.float64)
    tail = arr[arr >= kmin]
    n = int(tail.size)
    if n == 0:
        return {"tau": float("nan"), "stderr": float("nan"), "n_tail": 0, "kmin": kmin}
    mean_log = float(np.mean(np.log(tail)))
    h = 1e-6

    def score(tau: float) -> float:
        dln_zeta = (math.log(zeta(tau + h, kmin)) - math.log(zeta(tau - h, kmin))) / (2 * h)
        return -dln_zeta - mean_log

    lo, hi = tau_bracket
    try:
        tau = float(brentq(score, lo, hi, xtol=1e-8))
    except ValueError:
        denom = float(np.sum(np.log(tail / (kmin - 0.5)))) if kmin != 0.5 else float("nan")
        tau = 1.0 + n / denom if denom else float("nan")
    stderr = (tau - 1.0) / math.sqrt(n)
    return {"tau": tau, "stderr": stderr, "n_tail": n, "kmin": kmin}


def punctuation_stats(active_min: Sequence[float], f_c: float) -> Dict[str, Any]:
    """Evidence for P3 (punctuated equilibrium / intermittency): over the active-min time
    series, count how many times the running minimum DIPS below f_c and how many times it
    RECOVERS above f_c (up/down crossings of the threshold), the fraction of steps spent
    below f_c, and the number of distinct avalanches (= number of below-runs). Repeated
    dip/recover crossings (not a single sustained excursion) are the signature of
    intermittent, punctuated activity."""
    arr = np.asarray(active_min, dtype=np.float64)
    below = arr < f_c
    if arr.size == 0:
        return {"n_below_runs": 0, "n_recoveries": 0, "frac_below": 0.0,
                "n_steps": 0, "longest_below_run": 0, "longest_above_run": 0}
    # Count maximal below-runs (= dips) and above-runs.
    n_below_runs = 0
    n_above_runs = 0
    longest_below = 0
    longest_above = 0
    run = 0
    cur = bool(below[0])
    for b in below:
        b = bool(b)
        if b == cur:
            run += 1
        else:
            if cur:
                n_below_runs += 1
                longest_below = max(longest_below, run)
            else:
                n_above_runs += 1
                longest_above = max(longest_above, run)
            cur = b
            run = 1
    # close the final run
    if cur:
        n_below_runs += 1
        longest_below = max(longest_below, run)
    else:
        n_above_runs += 1
        longest_above = max(longest_above, run)
    return {
        "n_below_runs": n_below_runs,       # number of dips below f_c (= # avalanches)
        "n_recoveries": n_above_runs,       # number of recoveries above f_c
        "frac_below": float(below.mean()),
        "n_steps": int(arr.size),
        "longest_below_run": int(longest_below),
        "longest_above_run": int(longest_above),
    }
