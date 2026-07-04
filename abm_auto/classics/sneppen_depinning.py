"""Sneppen interface depinning (1992, model "A") — a faithful self-organized-criticality
(SOC) reproduction of a self-affine interface in a quenched random medium.

Source: Sneppen, K. (1992) "Self-organized pinning and interface growth in a random
medium", Phys. Rev. Lett. 69:3539-3542. doi:10.1103/PhysRevLett.69.3539.

IMPORTANT (honesty, binds the FINDINGS): this is a CELLULAR AUTOMATON / EXTREMAL-DYNAMICS
SOC model, framing **CA (disclosed)** — NOT an agent-stepping ABM. There is no scheduler
over an agent roster, no per-agent perceive/decide/act, no autonomous local stepping. Each
step is *model-orchestrated*: it selects the GLOBAL minimum-pinning column across the whole
interface and advances it, then enforces a bounded-slope constraint on its neighbours. The
global-min selection is a centralized operation. We disclose this exactly as the BTW
sandpile, Bak-Sneppen, and ER/WS network-generation reproductions disclose that they are not
agent-based. The lock-first + honest-verdict + L3-bundle discipline still fully applies.

Rules (Sneppen model "A", 1D interface in a quenched random medium — verified vs the paper):
  * An interface height ``h[x]`` (integer) over a PERIODIC 1D substrate of ``L`` columns.
  * QUENCHED PINNING: each column ``x`` carries a current random pinning value
    ``eta[x] ~ U[0, 1)`` — the random pinning force at the interface front of that column. It
    is re-drawn (a fresh, independent quenched value) whenever that column advances.
  * EXTREMAL UPDATE with a bounded-slope constraint. One "advance" =
      1. find the column ``x*`` with the GLOBAL MINIMUM pinning ``eta`` (the weakest-pinned
         front point);
      2. advance it: ``h[x*] += 1`` and redraw ``eta[x*] ~ U[0, 1)``;
      3. enforce the nearest-neighbour SLOPE CONSTRAINT ``|h[x] - h[x+-1]| <= 1``: if
         advancing ``x*`` leaves a periodic neighbour lagging by 2, pull that neighbour up
         too (``h += 1``, redraw its ``eta``) and PROPAGATE until no bond violates the
         constraint everywhere. The forced pulls are part of the SAME advance (they are the
         local relaxation the extremal move triggers).
  * Iterating grows a SELF-AFFINE interface. From a flat start the width ``W = std(h)``
    grows and then SATURATES at a value ``W_sat(L)`` set by the system size; the acted-on
    pinning value ``eta_min`` self-organizes to a critical ceiling ``f_c`` (finite-size).

Measurements (all FIXED before the run; see the module helpers):
  * SATURATED WIDTH ``W_sat(L) = std(h)`` averaged over the stationary (post-transient)
    phase, swept over ``L`` — the roughness exponent ``chi`` is the log-log slope
    ``W_sat ~ L^chi`` (P1).
  * AVALANCHE / JUMP SIZE (P2): the standard Sneppen "signal" is the sequence of acted-on
    minima ``eta_min`` at each advance. The running "global-minimum threshold" is the
    RUNNING MAXIMUM (record) of that signal; an avalanche = the number of advance events
    between successive INCREASES of that record threshold (a maximal run of advances during
    which no new record is set). Measured over the full run (records are dense early, rare
    late), giving a broad, scale-free size distribution.
  * ADJACENT-SLOPE CORRELATION (P3): the nearest-neighbour spatial correlation of the
    interface height DIFFERENCES ``dh[x] = h[x+1] - h[x]`` (periodic), i.e.
    ``corr(dh[x], dh[x+1])`` — the sign of the correlation of adjacent height differences.

Determinism: the whole run is reproducible given an integer seed (a single
``numpy.random.default_rng(seed)`` draws every pinning value). NumPy is used to make the
argmin fast; the result is the canonical extremal-dynamics outcome for that seed.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


# -- core extremal dynamics: a single interface --------------------------------

class SneppenInterface:
    """A 1D Sneppen interface: integer heights ``h[x]`` over ``L`` periodic columns, each
    column carrying a current quenched pinning value ``eta[x] ~ U[0,1)``.

    ``advance`` performs ONE extremal move: it advances the global-minimum-pinning column by
    one unit, redraws its pinning, and enforces the ``|dh| <= 1`` slope constraint by pulling
    up any neighbour that would lag by 2 (propagating). It returns the acted-on minimum
    pinning value (the Sneppen "signal" for that advance). The update is centralized /
    model-orchestrated, not agent-autonomous (disclosed in the docstring + FINDINGS).
    """

    def __init__(self, L: int, rng: np.random.Generator) -> None:
        if L < 3:
            raise ValueError("L must be >= 3 (the slope constraint couples ring neighbours)")
        self.L = int(L)
        self.rng = rng
        self.h = np.zeros(self.L, dtype=np.int64)
        self.eta = rng.random(self.L)

    def advance(self) -> float:
        """One extremal advance. Returns the acted-on minimum pinning value ``eta_min``
        (BEFORE its redraw). Advances that column, redraws its pinning, then enforces the
        bounded-slope constraint by pulling up (and redrawing) any neighbour lagging by 2,
        propagating until every periodic bond satisfies ``|h[x]-h[x+-1]| <= 1``."""
        h = self.h
        eta = self.eta
        L = self.L
        xs = int(np.argmin(eta))
        eta_min = float(eta[xs])
        h[xs] += 1
        eta[xs] = self.rng.random()
        # Enforce the slope constraint. A column that was just raised may now sit 2 above a
        # periodic neighbour; that neighbour must be pulled up (and its pinning redrawn), which
        # can in turn violate the constraint further along, so we propagate with a stack.
        stack = [xs]
        while stack:
            x = stack.pop()
            for nb in ((x - 1) % L, (x + 1) % L):
                if h[x] - h[nb] >= 2:
                    h[nb] += 1
                    eta[nb] = self.rng.random()
                    stack.append(nb)
        return eta_min

    def width(self) -> float:
        """Current interface width W = std(h) (population standard deviation of heights)."""
        return float(np.std(self.h))

    def slopes(self) -> np.ndarray:
        """Periodic nearest-neighbour height differences dh[x] = h[(x+1)%L] - h[x]."""
        return (np.roll(self.h, -1) - self.h).astype(np.float64)


# -- drive loop ----------------------------------------------------------------

def run_interface(
    L: int,
    *,
    n_advance: int,
    seed: int = 0,
    transient_frac: float = 0.5,
    width_samples: int = 400,
    snapshot_samples: int = 200,
) -> Dict[str, Any]:
    """Grow a Sneppen interface of width ``L`` for ``n_advance`` extremal advances.

    Records:
      * ``signal`` — the acted-on minimum pinning value at EVERY advance (length
        ``n_advance``); the full Sneppen signal the record-run avalanches are built from.
      * ``stationary_widths`` — W = std(h) sampled over the POST-transient phase (the first
        ``transient_frac`` of advances are discarded as the roughening transient), used for
        ``W_sat``.
      * ``slope_snapshots`` — periodic slope arrays ``dh`` sampled over the stationary phase
        (for the adjacent-slope correlation).

    ``transient_frac`` (fraction of advances discarded before measuring the saturated
    quantities), ``width_samples`` and ``snapshot_samples`` are FIXED measurement windows,
    not tuned. Deterministic given ``seed``.
    """
    if not (0.0 <= transient_frac < 1.0):
        raise ValueError("transient_frac must be in [0, 1)")
    if n_advance <= 0:
        raise ValueError("n_advance must be positive")
    rng = np.random.default_rng(seed)
    iface = SneppenInterface(L, rng)

    signal = np.empty(n_advance, dtype=np.float64)
    record_start = int(n_advance * transient_frac)
    n_stationary = n_advance - record_start
    width_every = max(1, n_stationary // max(1, width_samples))
    snap_every = max(1, n_stationary // max(1, snapshot_samples))

    widths: List[float] = []
    snapshots: List[np.ndarray] = []
    for t in range(n_advance):
        signal[t] = iface.advance()
        if t >= record_start:
            k = t - record_start
            if k % width_every == 0:
                widths.append(iface.width())
            if k % snap_every == 0:
                snapshots.append(iface.slopes())

    return {
        "L": L,
        "n_advance": n_advance,
        "seed": seed,
        "transient_frac": transient_frac,
        "record_start": record_start,
        "signal": signal,
        "stationary_widths": widths,
        "w_sat": float(np.mean(widths)) if widths else iface.width(),
        "slope_snapshots": snapshots,
        "final_width": iface.width(),
        "final_heights": iface.h.copy(),
    }


# -- analysis: P1 (roughness exponent) -----------------------------------------

def fit_chi(Ls: Sequence[int], w_sats: Sequence[float]) -> Dict[str, Any]:
    """Fit the roughness exponent ``chi`` as the slope of ``log W_sat`` vs ``log L`` (OLS).

    ``W_sat(L) ~ L^chi`` <=> ``log W_sat = chi * log L + const``. Also reports ``r2`` of the
    log-log fit and whether ``W_sat`` is monotone increasing in ``L`` across the sweep (both
    required by P1). No tuning: the sweep ``Ls`` and the fit are fixed."""
    Ls_a = np.asarray(Ls, dtype=np.float64)
    w_a = np.asarray(w_sats, dtype=np.float64)
    if Ls_a.size < 2 or np.any(w_a <= 0):
        return {"chi": float("nan"), "intercept": float("nan"), "r2": float("nan"),
                "monotone_increasing": False}
    x = np.log(Ls_a)
    y = np.log(w_a)
    chi, intercept = np.polyfit(x, y, 1)
    yhat = chi * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    monotone = bool(np.all(np.diff(w_a) > 0))
    return {
        "chi": float(chi),
        "intercept": float(intercept),
        "r2": float(r2),
        "monotone_increasing": monotone,
    }


# -- analysis: P2 (record-run avalanches / jump sizes) -------------------------

def record_run_avalanches(signal: Sequence[float]) -> np.ndarray:
    """Sneppen record-run avalanche sizes (FIXED definition, matches the spec):

    The Sneppen "signal" is the acted-on minimum pinning ``eta_min`` at each advance. The
    running "global-minimum threshold" is the RUNNING MAXIMUM (record) of that signal. An
    avalanche = the number of advance events BETWEEN successive INCREASES of the record
    threshold — i.e. a maximal run of advances during which no new record is set. Counting
    starts at the first record; each new record closes the current avalanche and opens the
    next; the trailing run (advances after the last record) is included. Returns the list of
    avalanche sizes (>= 0), in time order."""
    sizes: List[int] = []
    rec = -math.inf
    count = 0
    started = False
    for v in signal:
        if v > rec:
            if started:
                sizes.append(count)
            rec = v
            count = 0
            started = True
        else:
            count += 1
    if started:
        sizes.append(count)
    return np.asarray(sizes, dtype=np.int64)


def heavy_tail_stats(sizes: Sequence[int]) -> Dict[str, Any]:
    """Heavy-tail descriptors for P2 over the NONZERO avalanche sizes: how many decades the
    sizes span (``log10(max) - log10(min_nonzero)``), the max, the median nonzero, and the
    ``max / median_nonzero`` ratio."""
    arr = np.asarray(sizes, dtype=np.float64)
    pos = arr[arr >= 1]
    if pos.size == 0:
        return {"n_nonzero": 0, "max": 0.0, "min_nonzero": 0.0,
                "median_nonzero": 0.0, "decades": 0.0, "max_over_median": 0.0}
    smax = float(pos.max())
    smin = float(pos.min())
    median = float(np.median(pos))
    decades = math.log10(smax) - math.log10(smin) if smin > 0 else 0.0
    max_over_median = smax / median if median > 0 else float("inf")
    return {
        "n_nonzero": int(pos.size),
        "max": smax,
        "min_nonzero": smin,
        "median_nonzero": median,
        "decades": decades,
        "max_over_median": max_over_median,
    }


def avalanche_size_histogram(sizes: Sequence[int], *, n_bins: int = 30) -> List[Dict[str, float]]:
    """Logarithmically-binned histogram of nonzero avalanche sizes (for the heavy-tail
    visual). Geometric bins from 1 to max size; raw counts. Mirrors the BTW/Bak-Sneppen
    helpers."""
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


# -- analysis: P3 (adjacent-slope correlation) ---------------------------------

def adjacent_slope_correlation(slopes: np.ndarray) -> float:
    """Nearest-neighbour spatial correlation of the interface height differences.

    Given a periodic slope array ``dh[x] = h[x+1] - h[x]``, returns the Pearson correlation
    of ``dh[x]`` with its neighbour ``dh[x+1]`` (both taken periodically). This is the
    "correlation of adjacent height differences" the P3 clause tests; a NEGATIVE value means
    adjacent slopes tend to have opposite sign (anticorrelated / faceted), a POSITIVE value
    means a rising region keeps rising (a smooth self-affine interface). Returns 0.0 for a
    degenerate (flat) slope field."""
    dh = np.asarray(slopes, dtype=np.float64)
    a = dh - dh.mean()
    b = np.roll(dh, -1)
    b = b - b.mean()
    denom = math.sqrt(float((a * a).mean()) * float((b * b).mean()))
    if denom == 0.0:
        return 0.0
    return float((a * b).mean() / denom)


def mean_adjacent_slope_correlation(snapshots: Sequence[np.ndarray]) -> float:
    """Mean adjacent-slope correlation over a set of interface slope snapshots."""
    if not len(snapshots):
        return float("nan")
    return float(np.mean([adjacent_slope_correlation(s) for s in snapshots]))


# -- random-deposition baseline (P3 contrast) ----------------------------------

def random_deposition_slope_correlation(
    L: int, *, n_advance: int, seed: int = 0, transient_frac: float = 0.5,
    snapshot_samples: int = 200,
) -> Dict[str, Any]:
    """Baseline: uncorrelated RANDOM DEPOSITION (no extremal rule, no slope constraint) —
    each advance drops one unit on a uniformly random column. Returns the mean adjacent-slope
    correlation over stationary snapshots, the contrast the P3 clause draws against Sneppen's
    self-organized depinning. Deterministic given ``seed``."""
    rng = np.random.default_rng(seed)
    h = np.zeros(L, dtype=np.int64)
    cols = rng.integers(0, L, size=n_advance)
    record_start = int(n_advance * transient_frac)
    n_stationary = n_advance - record_start
    snap_every = max(1, n_stationary // max(1, snapshot_samples))
    snaps: List[np.ndarray] = []
    for t in range(n_advance):
        h[cols[t]] += 1
        if t >= record_start:
            k = t - record_start
            if k % snap_every == 0:
                snaps.append((np.roll(h, -1) - h).astype(np.float64))
    return {
        "L": L,
        "n_advance": n_advance,
        "seed": seed,
        "mean_adjacent_slope_correlation": mean_adjacent_slope_correlation(snaps),
        "n_snapshots": len(snaps),
    }


# -- multi-seed, multi-L sweep experiment --------------------------------------

def run_sweep(
    Ls: Sequence[int],
    *,
    advances_per_L: int = 400,
    n_seeds: int = 4,
    seed_base: int = 0,
    transient_frac: float = 0.5,
    width_samples: int = 400,
    snapshot_samples: int = 200,
    avalanche_L: Optional[int] = None,
) -> Dict[str, Any]:
    """Full Sneppen experiment: sweep interface size over ``Ls``, ``n_seeds`` seeds each,
    running ``advances_per_L * L`` extremal advances per (L, seed) so each size reaches
    saturation. Aggregates:

      * ``w_sat[L]`` — mean saturated width over seeds (P1: chi = log-log slope, monotone).
      * record-run avalanche sizes POOLED over the seeds of the largest L (or ``avalanche_L``
        if given) (P2: heavy tail).
      * mean adjacent-slope correlation over the seeds of the largest L (P3), plus the
        matched random-deposition baseline.

    All windows/seeds/sizes are fixed here; nothing is tuned to make a clause pass.
    Deterministic given the seed set."""
    Ls = list(Ls)
    seeds = [seed_base + i for i in range(n_seeds)]
    aval_L = avalanche_L if avalanche_L is not None else max(Ls)

    per_L_w: Dict[int, List[float]] = {L: [] for L in Ls}
    aval_sizes_pooled: List[int] = []
    aval_seed_stats: List[Dict[str, Any]] = []
    slope_corrs: List[float] = []
    example_signal_head: List[float] = []
    example_heights: List[int] = []

    for L in Ls:
        n_adv = advances_per_L * L
        for si, seed in enumerate(seeds):
            res = run_interface(
                L, n_advance=n_adv, seed=seed, transient_frac=transient_frac,
                width_samples=width_samples, snapshot_samples=snapshot_samples)
            per_L_w[L].append(res["w_sat"])
            if L == aval_L:
                sizes = record_run_avalanches(res["signal"])
                aval_sizes_pooled.extend(int(s) for s in sizes)
                aval_seed_stats.append(heavy_tail_stats(sizes))
                slope_corrs.append(mean_adjacent_slope_correlation(res["slope_snapshots"]))
                if si == 0:
                    example_signal_head = [float(v) for v in res["signal"][:50]]
                    example_heights = [int(v) for v in res["final_heights"]]

    w_sat = {L: float(np.mean(per_L_w[L])) for L in Ls}
    w_sat_list = [w_sat[L] for L in Ls]
    chi_fit = fit_chi(Ls, w_sat_list)

    tail = heavy_tail_stats(aval_sizes_pooled)

    baseline = random_deposition_slope_correlation(
        aval_L, n_advance=advances_per_L * aval_L, seed=seed_base,
        transient_frac=transient_frac, snapshot_samples=snapshot_samples)

    return {
        "Ls": Ls,
        "seeds": seeds,
        "advances_per_L": advances_per_L,
        "transient_frac": transient_frac,
        "avalanche_L": aval_L,
        "per_L_w_sat": {int(L): per_L_w[L] for L in Ls},
        "w_sat": {int(L): w_sat[L] for L in Ls},
        "w_sat_list": w_sat_list,
        "chi": chi_fit["chi"],
        "chi_r2": chi_fit["r2"],
        "chi_intercept": chi_fit["intercept"],
        "w_sat_monotone_increasing": chi_fit["monotone_increasing"],
        "avalanche_tail": tail,
        "avalanche_per_seed": aval_seed_stats,
        "n_avalanches_pooled": len(aval_sizes_pooled),
        "avalanche_histogram": avalanche_size_histogram(aval_sizes_pooled),
        "mean_adjacent_slope_correlation": float(np.mean(slope_corrs)) if slope_corrs else float("nan"),
        "per_seed_adjacent_slope_correlation": slope_corrs,
        "baseline_random_deposition_slope_correlation": baseline["mean_adjacent_slope_correlation"],
        "example_signal_head": example_signal_head,
        "example_final_heights": example_heights,
    }
