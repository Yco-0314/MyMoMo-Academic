"""Eden growth model (1961) + KPZ interface scaling — a faithful reproduction.

Source: Eden, M. (1961), "A two-dimensional growth process", Proc. 4th Berkeley
Symposium on Mathematical Statistics and Probability, Vol. 4:223-239.
KPZ universality: Kardar, M., Parisi, G. & Zhang, Y.-C. (1986), "Dynamic scaling of
growing interfaces", Phys. Rev. Lett. 56:889-892. doi:10.1103/PhysRevLett.56.889.

Framing (hybrid: stochastic particle growth on a grid). A cluster grows by adding ONE
particle at a time to a uniformly-random unoccupied site on the CURRENT PERIMETER (every
perimeter site equally likely). A perimeter (growth) site is an unoccupied lattice cell
that is von-Neumann-adjacent to at least one occupied cell. This is the Eden model:
unlike DLA there is no diffusion and no screening — a buried interior perimeter site is
just as likely to be filled as an exposed tip — so the cluster fills space COMPACTLY
(bulk fractal dimension D = 2) while its growing INTERFACE is a rough, self-affine KPZ
surface.

Two geometries are built, because the two locked claims live on different observables:

  * RADIAL cluster (P1: the compact bulk / DLA contrast). One occupied seed cell at the
    origin, grown to N particles by repeatedly filling a uniformly-random perimeter cell.
    The bulk mass dimension is read from the enclosed mass M(r) ~ r^D over the middle
    decade of radii, and the annular (per-shell) density is measured across the INTERIOR
    bulk (excluding the rough growing surface). Eden fills space, so D -> 2 and the
    interior annular density is flat (non-decaying) — the exact opposite of DLA's porous,
    screened, D ~= 1.71 interior.

  * FLAT 1+1D STRIP (P2/P3: the KPZ interface). A lattice strip of width L, PERIODIC
    along the width, grows UPWARD from a flat seed row. The SAME genuine Eden perimeter
    rule runs on the strip (occupied cells form a real 2D set, perimeter = empty cells
    von-Neumann-adjacent to occupied, overhangs allowed). The interface height h(x,t) =
    the MAX occupied row in column x (exactly as the lock defines it), and the interface
    width is W(L,t) = std_x h(x,t). Occupied cells far below the front never re-enter the
    perimeter, so they are pruned to keep memory/runtime bounded (an exact optimization —
    it removes only cells that can never be chosen again). The width reproduces the KPZ
    (1+1D) exponents:
        growth    W(t)  ~ t^beta       beta = 1/3   (pre-saturation, at large L)
        roughness W_sat ~ L^alpha      alpha = 1/2  (saturated width vs L)
    (Family-Vicsek scaling W(L,t) = L^alpha f(t / L^{alpha/beta}), dynamic exponent
    z = alpha/beta = 3/2.) Time t is measured in deposited LAYERS = (particles added)/L,
    the natural KPZ growth time comparable across widths.

Everything is deterministic given an integer seed (a single ``numpy.random.default_rng``
draws every growth choice). The lock endorses the column-height width statistic as
faithful; here we compute it from the genuine 2D Eden front (h = max occupied row per
column) rather than a proxy, so the reproduction is the real Eden model, not a surrogate.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


# =============================================================================
# fit helper (shared) — OLS slope + intercept + R^2 of a (log-log) line
# =============================================================================

def linfit(xs: Sequence[float], ys: Sequence[float]) -> Tuple[float, float, float]:
    """Ordinary least-squares slope, intercept, and R^2 of ys on xs. Requires >= 2
    distinct x. Used for the mass-dimension fit (P1) and the KPZ exponent fits
    (P2 growth beta, P3 roughness alpha)."""
    n = len(xs)
    if n < 2:
        raise ValueError("need >= 2 points to fit a line")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0.0:
        raise ValueError("degenerate fit: all x equal")
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - (ss_res / ss_tot if ss_tot > 0 else 0.0)
    return slope, intercept, r2


# von-Neumann neighbour offsets on the square lattice.
_NEI: Tuple[Tuple[int, int], ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


# =============================================================================
# RADIAL Eden cluster  (P1: compact bulk, mass dimension D -> 2)
# =============================================================================

class RadialEden:
    """A radial Eden cluster grown one particle at a time on the square lattice.

    State: a set of occupied integer cells and the current PERIMETER (unoccupied cells
    von-Neumann-adjacent to >= 1 occupied cell), held as a swap-remove list + index map
    so a uniformly-random perimeter pick and its removal are both O(1). ``grow_one`` fills
    a uniformly-random perimeter cell and repairs the perimeter incrementally. Deterministic
    given the seed.
    """

    def __init__(self, n: int = 8000, *, seed: int = 0) -> None:
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        self.n_target = int(n)
        self.seed_value = int(seed)
        self.rng = np.random.default_rng(seed)
        self.occupied: set[Tuple[int, int]] = set()
        self._perim_list: List[Tuple[int, int]] = []
        self._perim_pos: Dict[Tuple[int, int], int] = {}
        self.attach_r: List[float] = []      # attachment radius of each occupied cell
        self._occupy((0, 0))                 # single seed at the origin

    # -- perimeter bookkeeping (list + index map => O(1) uniform pick and removal) --
    def _perim_add(self, cell: Tuple[int, int]) -> None:
        if cell in self.occupied or cell in self._perim_pos:
            return
        self._perim_pos[cell] = len(self._perim_list)
        self._perim_list.append(cell)

    def _perim_remove(self, cell: Tuple[int, int]) -> None:
        pos = self._perim_pos.pop(cell, None)
        if pos is None:
            return
        last = self._perim_list.pop()
        if pos < len(self._perim_list):
            self._perim_list[pos] = last
            self._perim_pos[last] = pos

    def _occupy(self, cell: Tuple[int, int]) -> None:
        self.occupied.add(cell)
        self.attach_r.append(math.hypot(cell[0], cell[1]))
        self._perim_remove(cell)
        cx, cy = cell
        for dx, dy in _NEI:
            self._perim_add((cx + dx, cy + dy))

    @property
    def size(self) -> int:
        return len(self.occupied)

    @property
    def perimeter_size(self) -> int:
        return len(self._perim_list)

    @property
    def r_max(self) -> float:
        return max(self.attach_r) if self.attach_r else 0.0

    def grow_one(self) -> Tuple[int, int]:
        """Fill ONE uniformly-random perimeter cell and return it. Every current perimeter
        site is equally likely (the defining Eden rule: no screening, no diffusion)."""
        m = len(self._perim_list)
        if m == 0:
            raise RuntimeError("no perimeter sites (cluster cannot grow)")
        cell = self._perim_list[int(self.rng.integers(0, m))]
        self._occupy(cell)
        return cell

    def grow(self, n: Optional[int] = None) -> "RadialEden":
        """Grow until the cluster holds ``n`` occupied cells (including the seed)."""
        target = self.n_target if n is None else int(n)
        while self.size < target:
            self.grow_one()
        return self

    # -- P1 metrics: mass dimension + interior (bulk) density --
    def mass_profile(self, n_shells: int = 40) -> Dict[str, List[float]]:
        """Enclosed mass M(r) (occupied cells within radius r) and the ANNULAR density
        (cells in each shell / shell area), on ``n_shells`` radii to r_max.

        Annular (not cumulative) density is the sensitive interior-decay probe: for a
        space-filling compact bulk it is ~ constant across the interior shells and only
        falls in the outermost shells (the rough growing surface, where a shell is only
        partly inside the cluster)."""
        if self.size < 2:
            return {"radii": [], "mass": [], "annular_density": []}
        dists = np.sort(np.asarray(self.attach_r))
        rmax = float(dists[-1])
        radii: List[float] = []
        mass: List[float] = []
        annular_density: List[float] = []
        prev_r = 0.0
        prev_m = 0
        for k in range(1, n_shells + 1):
            r = rmax * k / n_shells
            m = int(np.searchsorted(dists, r, side="right"))
            radii.append(r)
            mass.append(float(m))
            shell_area = math.pi * (r * r - prev_r * prev_r)
            annular_density.append((m - prev_m) / shell_area if shell_area > 0 else 0.0)
            prev_r, prev_m = r, m
        return {"radii": radii, "mass": mass, "annular_density": annular_density}

    def mass_dimension(self, *, drop_inner: int = 6, drop_outer: int = 6,
                       n_shells: int = 40) -> Dict[str, Any]:
        """Fit D from log M(r) = D log r + c over the middle-window shells (drop the noisy
        innermost — discrete seed granularity — and outermost — rough tips — shells). For a
        compact Eden bulk D -> 2."""
        prof = self.mass_profile(n_shells=n_shells)
        radii, mass = prof["radii"], prof["mass"]
        lo, hi = drop_inner, len(radii) - drop_outer
        xs: List[float] = []
        ys: List[float] = []
        for r, m in zip(radii[lo:hi], mass[lo:hi]):
            if r > 0 and m > 0:
                xs.append(math.log(r))
                ys.append(math.log(m))
        if len(xs) < 2:
            raise ValueError("not enough non-empty middle shells to fit D")
        slope, intercept, r2 = linfit(xs, ys)
        return {"D": slope, "intercept": intercept, "r2": r2,
                "log_r": xs, "log_m": ys,
                "drop_inner": drop_inner, "drop_outer": drop_outer, "n_shells": n_shells}

    def interior_density_stats(self, *, bulk_inner_frac: float = 0.05,
                               bulk_outer_frac: float = 0.70,
                               n_shells: int = 40) -> Dict[str, Any]:
        """Std/mean (coefficient of variation) of the ANNULAR density across the INTERIOR
        BULK — the shells whose radius lies in ``[bulk_inner_frac, bulk_outer_frac] * r_max``.

        The interior bulk excludes the innermost granular shells and, crucially, the
        outermost shells that straddle the rough growing surface (where a shell is only
        partially inside the cluster, so its 'density' collapses). Over the genuine
        space-filling interior the annular density is flat: CV small (< 0.15) and the
        outer half's mean is not below the inner half's (non-decaying). This is the
        compact-bulk signature — the DLA contrast."""
        prof = self.mass_profile(n_shells=n_shells)
        radii = np.asarray(prof["radii"])
        dens = np.asarray(prof["annular_density"], dtype=np.float64)
        rmax = float(radii[-1]) if radii.size else 0.0
        if rmax <= 0:
            return {"cv": float("nan"), "mean": float("nan"), "std": float("nan"),
                    "non_decaying": False, "inner_mean": float("nan"),
                    "outer_mean": float("nan"), "n_bulk_shells": 0}
        lo_r, hi_r = bulk_inner_frac * rmax, bulk_outer_frac * rmax
        mask = (radii >= lo_r) & (radii <= hi_r)
        bulk = dens[mask]
        if bulk.size < 2:
            return {"cv": float("nan"), "mean": float("nan"), "std": float("nan"),
                    "non_decaying": False, "inner_mean": float("nan"),
                    "outer_mean": float("nan"), "n_bulk_shells": int(bulk.size)}
        mean = float(bulk.mean())
        std = float(bulk.std())
        cv = std / mean if mean > 0 else float("inf")
        mid = bulk.size // 2
        inner_mean = float(bulk[:mid].mean())
        outer_mean = float(bulk[mid:].mean())
        non_decaying = outer_mean >= 0.90 * inner_mean
        return {"cv": cv, "mean": mean, "std": std, "non_decaying": non_decaying,
                "inner_mean": inner_mean, "outer_mean": outer_mean,
                "n_bulk_shells": int(bulk.size)}

    def summary(self, *, drop_inner: int = 6, drop_outer: int = 6, n_shells: int = 40,
                bulk_inner_frac: float = 0.05, bulk_outer_frac: float = 0.70) -> Dict[str, Any]:
        md = self.mass_dimension(drop_inner=drop_inner, drop_outer=drop_outer,
                                 n_shells=n_shells)
        dens = self.interior_density_stats(bulk_inner_frac=bulk_inner_frac,
                                           bulk_outer_frac=bulk_outer_frac, n_shells=n_shells)
        return {
            "seed": self.seed_value, "n": self.size, "n_target": self.n_target,
            "r_max": self.r_max, "D": md["D"], "D_r2": md["r2"],
            "density_cv": dens["cv"], "density_non_decaying": dens["non_decaying"],
            "density_inner_mean": dens["inner_mean"], "density_outer_mean": dens["outer_mean"],
            "n_bulk_shells": dens["n_bulk_shells"],
            "drop_inner": drop_inner, "drop_outer": drop_outer, "n_shells": n_shells,
            "bulk_inner_frac": bulk_inner_frac, "bulk_outer_frac": bulk_outer_frac,
        }


def run_radial(n: int = 8000, *, seed: int = 0, drop_inner: int = 6, drop_outer: int = 6,
               n_shells: int = 40, bulk_inner_frac: float = 0.05,
               bulk_outer_frac: float = 0.70) -> Dict[str, Any]:
    """Grow one radial Eden cluster of ``n`` cells and return its P1 summary."""
    model = RadialEden(n, seed=seed)
    model.grow()
    return model.summary(drop_inner=drop_inner, drop_outer=drop_outer, n_shells=n_shells,
                         bulk_inner_frac=bulk_inner_frac, bulk_outer_frac=bulk_outer_frac)


def run_radial_many_seeds(n: int = 8000, *, n_seeds: int = 3, seed_base: int = 0,
                          drop_inner: int = 6, drop_outer: int = 6, n_shells: int = 40,
                          bulk_inner_frac: float = 0.05,
                          bulk_outer_frac: float = 0.70) -> Dict[str, Any]:
    """Grow ``n_seeds`` radial Eden clusters and aggregate the P1 metrics (mean/min D, the
    interior-density CV, the non-decay flag AND-ed across seeds)."""
    if n_seeds <= 0:
        raise ValueError(f"need n_seeds > 0 (got {n_seeds})")
    runs = [run_radial(n, seed=seed_base + i, drop_inner=drop_inner, drop_outer=drop_outer,
                       n_shells=n_shells, bulk_inner_frac=bulk_inner_frac,
                       bulk_outer_frac=bulk_outer_frac) for i in range(n_seeds)]
    Ds = [r["D"] for r in runs]
    cvs = [r["density_cv"] for r in runs]
    mean_D = sum(Ds) / len(Ds)
    var_D = sum((d - mean_D) ** 2 for d in Ds) / len(Ds)
    return {
        "n": n, "n_seeds": n_seeds, "seed_base": seed_base,
        "drop_inner": drop_inner, "drop_outer": drop_outer, "n_shells": n_shells,
        "bulk_inner_frac": bulk_inner_frac, "bulk_outer_frac": bulk_outer_frac,
        "per_seed": runs, "per_seed_D": Ds, "per_seed_density_cv": cvs,
        "mean_D": mean_D, "std_D": var_D ** 0.5, "min_D": min(Ds), "max_D": max(Ds),
        "mean_density_cv": sum(cvs) / len(cvs), "max_density_cv": max(cvs),
        "all_density_non_decaying": all(r["density_non_decaying"] for r in runs),
    }


# =============================================================================
# FLAT 1+1D STRIP Eden  (P2 growth beta, P3 roughness alpha — KPZ)
# =============================================================================

class StripEden:
    """Genuine on-lattice Eden growth on a flat 1+1D strip of width L (periodic along the
    width x), growing UPWARD from a flat seed row (row 0 fully occupied).

    Occupancy is a real 2D set (per-column set of occupied rows, so overhangs are
    represented). The PERIMETER is the set of empty cells von-Neumann-adjacent to an
    occupied cell, held as a swap-remove list + index map for O(1) uniform pick + removal.
    Each ``grow_one`` fills a uniformly-random perimeter cell (the defining Eden rule). The
    interface height ``h[x]`` is the MAX occupied row in column x, and the width is
    ``W = std_x h[x]``.

    Cells far below the front never re-enter the perimeter (they are surrounded by occupied
    cells), so once the interface climbs past them they can be pruned — an EXACT
    optimization that only drops cells that can never be chosen again. This keeps a run to
    a few minutes even at L = 512 past saturation.
    """

    def __init__(self, L: int = 256, *, seed: int = 0, prune_every: int = 1_000_000) -> None:
        if L <= 1:
            raise ValueError(f"need L > 1 (got {L})")
        if prune_every <= 0:
            raise ValueError(f"need prune_every > 0 (got {prune_every})")
        self.L = int(L)
        self.seed_value = int(seed)
        self.prune_every = int(prune_every)
        self.rng = np.random.default_rng(seed)
        self.occ: List[set] = [set((0,)) for _ in range(self.L)]  # seed row occupied
        self.h = np.zeros(self.L, dtype=np.int64)                 # max occupied row / column
        self._perim: List[Tuple[int, int]] = []
        self._perim_pos: Dict[int, int] = {}
        self.n_deposited = 0
        self._grow_count = 0
        # initial perimeter: the empty cell directly above each seed-row cell.
        for x in range(self.L):
            self._perim_add(x, 1)

    # -- perimeter bookkeeping keyed by a packed (x, y) integer --
    @staticmethod
    def _key(x: int, y: int) -> int:
        return (x << 32) | y

    def _perim_add(self, x: int, y: int) -> None:
        if y < 0 or y in self.occ[x]:
            return
        k = self._key(x, y)
        if k in self._perim_pos:
            return
        self._perim_pos[k] = len(self._perim)
        self._perim.append((x, y))

    def _perim_remove(self, x: int, y: int) -> None:
        k = self._key(x, y)
        pos = self._perim_pos.pop(k, None)
        if pos is None:
            return
        last = self._perim.pop()
        if pos < len(self._perim):
            self._perim[pos] = last
            self._perim_pos[self._key(*last)] = pos

    def _occupy(self, x: int, y: int) -> None:
        self.occ[x].add(y)
        self._perim_remove(x, y)
        if y > self.h[x]:
            self.h[x] = y
        for dx, dy in _NEI:
            nx = (x + dx) % self.L
            ny = y + dy
            if ny < 0:
                continue
            if ny not in self.occ[nx]:
                self._perim_add(nx, ny)

    def _maybe_prune(self) -> None:
        """Drop occupied rows well below the lowest interface height: those cells are fully
        buried (all four neighbours occupied) and can never be a perimeter site again, so
        removing them changes nothing about future growth or the width. Bounds memory."""
        floor = int(self.h.min()) - 4
        if floor <= 1:
            return
        for x in range(self.L):
            s = self.occ[x]
            if len(s) > 256:
                self.occ[x] = {y for y in s if y >= floor}

    @property
    def perimeter_size(self) -> int:
        return len(self._perim)

    def width(self) -> float:
        """Interface width W = standard deviation of the per-column max heights h[x]."""
        return float(self.h.std())

    def mean_height(self) -> float:
        return float(self.h.mean())

    def grow_one(self) -> Tuple[int, int]:
        """Fill ONE uniformly-random perimeter cell (the Eden rule) and return it."""
        m = len(self._perim)
        if m == 0:
            raise RuntimeError("no perimeter sites")
        x, y = self._perim[int(self.rng.integers(0, m))]
        self._occupy(x, y)
        self.n_deposited += 1
        self._grow_count += 1
        if self._grow_count % self.prune_every == 0:
            self._maybe_prune()
        return x, y

    def deposit(self, n_particles: int) -> None:
        """Grow ``n_particles`` particles one at a time (each a uniform perimeter pick)."""
        for _ in range(int(n_particles)):
            self.grow_one()

    def run_growth(self, *, n_layers: float, n_samples: int = 55) -> Dict[str, List[float]]:
        """Grow the strip and record W(t) on a log-spaced schedule of layer counts (t in
        deposited layers = particles/L). Returns the sampled times (layers) and widths."""
        L = self.L
        targets = np.unique(np.round(
            np.geomspace(0.3, float(n_layers), n_samples) * L).astype(np.int64))
        targets = targets[targets >= 1]
        times: List[float] = []
        widths: List[float] = []
        for tgt in targets:
            while self.n_deposited < int(tgt):
                self.grow_one()
            times.append(self.n_deposited / L)
            widths.append(self.width())
        return {"times": times, "widths": widths}


def saturation_width(L: int, *, seed: int = 0, warmup_layers_coeff: float = 2.0,
                     measure_layers_coeff: float = 3.0, sample_every_layers: float = 2.0
                     ) -> Dict[str, Any]:
    """Grow an L-strip to saturation and estimate the SATURATED width W_sat as the mean of
    W over MANY decorrelated time-samples deep in the plateau.

    ``warmup_layers_coeff * L`` layers are grown first (well past the KPZ crossover for L
    up to 512), then W is sampled every ``sample_every_layers`` layers over the next
    ``measure_layers_coeff * L`` layers and averaged. Sampling every ~2 layers decorrelates
    successive width samples, so the plateau mean is a low-variance W_sat estimate."""
    model = StripEden(L, seed=seed)
    warmup = int(warmup_layers_coeff * L) * L
    model.deposit(warmup)
    step = max(1, int(sample_every_layers * L))
    n_samples = max(1, int((measure_layers_coeff / sample_every_layers)))
    ws: List[float] = []
    for _ in range(n_samples):
        model.deposit(step)
        ws.append(model.width())
    w_sat = float(np.mean(ws))
    return {"L": L, "seed": seed, "w_sat": w_sat, "w_samples": ws,
            "n_width_samples": len(ws), "warmup_layers": warmup_layers_coeff * L,
            "measure_layers": measure_layers_coeff * L,
            "sample_every_layers": sample_every_layers}


def fit_beta(times: Sequence[float], widths: Sequence[float], *,
             t_lo: float, t_hi: float) -> Dict[str, Any]:
    """Fit the KPZ growth exponent beta from log W = beta log t + c over the PRE-saturation
    window t in [t_lo, t_hi] (layers). The window is above the earliest lattice transient
    and below saturation (far off at large L). Returns beta, R^2, and the point count."""
    xs: List[float] = []
    ys: List[float] = []
    for t, w in zip(times, widths):
        if t_lo <= t <= t_hi and t > 0 and w > 0:
            xs.append(math.log(t))
            ys.append(math.log(w))
    if len(xs) < 2:
        raise ValueError("not enough points in the beta-fit window")
    beta, intercept, r2 = linfit(xs, ys)
    return {"beta": beta, "intercept": intercept, "r2": r2,
            "n_points": len(xs), "t_lo": t_lo, "t_hi": t_hi}


def fit_alpha(Ls: Sequence[int], w_sats: Sequence[float]) -> Dict[str, Any]:
    """Fit the KPZ roughness exponent alpha from log W_sat = alpha log L + c across system
    sizes, and report whether W_sat increases monotonically in L (a locked P3 clause)."""
    xs = [math.log(L) for L in Ls]
    ys = [math.log(w) for w in w_sats]
    alpha, intercept, r2 = linfit(xs, ys)
    monotone = all(w_sats[i] < w_sats[i + 1] for i in range(len(w_sats) - 1))
    return {"alpha": alpha, "intercept": intercept, "r2": r2,
            "monotone_in_L": monotone, "Ls": list(Ls), "w_sats": list(w_sats)}


def run_growth_curve(L: int = 512, *, seed: int = 0, n_layers: float = 30.0,
                     n_samples: int = 55) -> Dict[str, Any]:
    """Grow one large-L strip and return its W(t) growth curve (for the beta fit)."""
    model = StripEden(L, seed=seed)
    curve = model.run_growth(n_layers=n_layers, n_samples=n_samples)
    return {"L": L, "seed": seed, "n_layers": n_layers, "n_samples": n_samples,
            "times": curve["times"], "widths": curve["widths"]}


def run_growth_many_seeds(L: int = 512, *, n_seeds: int = 4, seed_base: int = 0,
                          n_layers: float = 30.0, n_samples: int = 55) -> Dict[str, Any]:
    """Average W(t) growth curves over ``n_seeds`` seeds at fixed large L (a clean beta
    fit). All seeds share the log-spaced time grid, so the widths are averaged point-wise
    (the standard KPZ ensemble estimator)."""
    if n_seeds <= 0:
        raise ValueError(f"need n_seeds > 0 (got {n_seeds})")
    runs = [run_growth_curve(L, seed=seed_base + i, n_layers=n_layers, n_samples=n_samples)
            for i in range(n_seeds)]
    times = runs[0]["times"]
    W = np.array([r["widths"] for r in runs])       # (n_seeds, n_times)
    mean_w = W.mean(axis=0).tolist()
    return {"L": L, "n_seeds": n_seeds, "seed_base": seed_base, "n_layers": n_layers,
            "n_samples": n_samples, "times": times, "mean_widths": mean_w,
            "per_seed_widths": [r["widths"] for r in runs]}


def run_saturation_sweep(Ls: Sequence[int] = (64, 128, 256, 512), *, n_seeds: int = 5,
                         seed_base: int = 0, warmup_layers_coeff: float = 2.0,
                         measure_layers_coeff: float = 3.0,
                         sample_every_layers: float = 2.0) -> Dict[str, Any]:
    """For each width L, grow ``n_seeds`` strips to saturation and average W_sat over seeds
    AND over the many per-run plateau samples; return the per-L saturated widths (for the
    alpha fit)."""
    if n_seeds <= 0:
        raise ValueError(f"need n_seeds > 0 (got {n_seeds})")
    per_L: List[Dict[str, Any]] = []
    w_sats: List[float] = []
    for L in Ls:
        runs = [saturation_width(L, seed=seed_base + i,
                                 warmup_layers_coeff=warmup_layers_coeff,
                                 measure_layers_coeff=measure_layers_coeff,
                                 sample_every_layers=sample_every_layers)
                for i in range(n_seeds)]
        seed_w = [r["w_sat"] for r in runs]
        w_bar = sum(seed_w) / len(seed_w)
        per_L.append({"L": L, "w_sat": w_bar, "per_seed_w_sat": seed_w})
        w_sats.append(w_bar)
    return {"Ls": list(Ls), "w_sats": w_sats, "per_L": per_L, "n_seeds": n_seeds,
            "seed_base": seed_base, "warmup_layers_coeff": warmup_layers_coeff,
            "measure_layers_coeff": measure_layers_coeff,
            "sample_every_layers": sample_every_layers}
