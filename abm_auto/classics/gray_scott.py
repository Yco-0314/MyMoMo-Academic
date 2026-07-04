"""Gray-Scott reaction-diffusion (Pearson 1993) — a faithful grid-PDE reproduction.

Source: Pearson, J. E. (1993) "Complex patterns in a simple system", Science
261(5118):189-192. doi:10.1126/science.261.5118.189.

IMPORTANT (honesty, binds the FINDINGS): this is a two-species reaction-diffusion
PARTIAL-DIFFERENTIAL-EQUATION integrated on a grid — a CELLULAR / grid-PDE model, NOT an
agent-stepping ABM. There are no agents that perceive, decide and act; no scheduler over
an agent roster; no per-agent step. It is a single synchronous update (explicit Euler with
a 5-point Laplacian) applied to every grid cell of the two concentration fields at once.
We disclose this exactly as the game_of_life / forest_fire reproductions disclose they are
cellular automata. The lock-first + honest-verdict + L3-bundle discipline still applies in
full.

The model (Pearson 1993; the "Gray-Scott" cubic-autocatalysis system U + 2V -> 3V):

    dU/dt = Du * lap(U) - U * V^2 + F * (1 - U)
    dV/dt = Dv * lap(V) + U * V^2 - (F + k) * V

on an L x L PERIODIC (toroidal) grid.  U is the substrate (fed in at rate F toward U=1),
V is the autocatalyst (removed at rate F+k).  The nonlinear reaction U*V^2 converts one U
and two V into three V (cubic autocatalysis).  Du > Dv (here Du/Dv = 2): the differential
diffusion of the two species is what makes the uniform state unstable to patterns (Turing
morphogenesis).  ``lap`` is the 5-point Laplacian with wrap-around (periodic) boundaries.

Numerics (FIXED, locked before running; not tuned):
  * 256 x 256 grid, physical domain side 2.5, so the grid spacing is dx = 2.5 / 256.
  * Du = 2e-5, Dv = 1e-5 (Du/Dv = 2).
  * Explicit forward Euler in time with step dt.  The diffusive stability limit of the
    5-point Laplacian is dt < dx^2 / (4 * Du); with dx = 2.5/256 (dx^2 ~ 9.5e-5) and
    Du = 2e-5 that limit is ~ 1.19, so dt = 1.0 is comfortably stable (and the reaction
    terms are O(F,k) ~ 0.06, far below any reaction-stiffness limit at dt = 1).
  * Initial condition: U = 1, V = 0 everywhere (the trivial fed state) EXCEPT a small
    central square perturbation where U is knocked down and V bumped up (the standard
    Pearson seed).  A tiny amount of seeded noise breaks the perfect symmetry so patterns
    can nucleate; this is the only randomness, and it is deterministic given ``seed``.

The (F, k) pair selects the morphology (Pearson's phase diagram): different (F, k) on the
SAME equations give spots, stripes/labyrinths, self-replicating spots, or a homogeneous
(flat) state.  Canonical points used by the runner (Pearson 1993 / Pearson's plane):
  * spots            (F=0.035, k=0.065)
  * stripes / maze   (F=0.030, k=0.060)
  * self-replicating (F=0.026, k=0.060)   (Pearson's lambda/theta "mitosis" region)
  * homogeneous      (F=0.030, k=0.070)   (V decays away, field goes flat)

Metrics (the locked grading quantities; all deterministic given seed):
  * ``count_spots`` / ``spot_stats``: connected-component analysis of the high-V mask
    (threshold on V), giving the number of blobs and the median aspect ratio of their
    bounding boxes — separates SPOTS (many compact blobs, aspect ~1) from STRIPES
    (few elongated blobs, aspect >> 1).
  * ``max_spot_count`` over the run: the peak number of blobs reached — self-replication
    shows up as a peak >= 4 (a single seed dividing >= 2 rounds).
  * ``field_std(V)``: spatial standard deviation of V — ~0 in the homogeneous regime.

Connected components are labelled with a self-contained 4-connectivity flood fill on the
PERIODIC grid (no SciPy dependency), verified against hand-built masks in the tests.
NumPy holds the two fields and does the vectorised Laplacian (np.roll) + reaction; the
result is the bit-for-bit deterministic Gray-Scott orbit for a given (F, k, seed).
"""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# Fixed physical / numerical constants (locked; PREDICTIONS-locked.md).
DU = 2e-5            # substrate diffusion
DV = 1e-5            # autocatalyst diffusion (Du/Dv = 2)
DOMAIN_SIDE = 2.5    # physical side length of the (square, periodic) domain
GRID_N = 256         # cells per side


# -- the 5-point periodic Laplacian ------------------------------------------------

def laplacian(field: np.ndarray, dx: float) -> np.ndarray:
    """5-point discrete Laplacian of ``field`` on a PERIODIC (toroidal) grid.

    lap(f)_{ij} = (f_{i+1,j} + f_{i-1,j} + f_{i,j+1} + f_{i,j-1} - 4 f_{ij}) / dx^2.
    Implemented with np.roll (which wraps the edges, giving the periodic stencil exactly).
    """
    return (
        np.roll(field, 1, axis=0)
        + np.roll(field, -1, axis=0)
        + np.roll(field, 1, axis=1)
        + np.roll(field, -1, axis=1)
        - 4.0 * field
    ) / (dx * dx)


# -- connected components on a periodic grid (4-connectivity flood fill) ----------

def connected_components(mask: np.ndarray) -> List[List[Tuple[int, int]]]:
    """Label the 4-connected components of a boolean ``mask`` on a PERIODIC grid.

    Returns a list of components, each a list of (row, col) cells. Connectivity wraps
    across the grid edges (toroidal), matching the periodic dynamics. Self-contained flood
    fill (BFS) — no SciPy — so the component metric is transparent and hand-testable.
    """
    m = np.asarray(mask, dtype=bool)
    rows, cols = m.shape
    seen = np.zeros_like(m, dtype=bool)
    components: List[List[Tuple[int, int]]] = []
    for r0 in range(rows):
        for c0 in range(cols):
            if not m[r0, c0] or seen[r0, c0]:
                continue
            comp: List[Tuple[int, int]] = []
            q = deque([(r0, c0)])
            seen[r0, c0] = True
            while q:
                r, c = q.popleft()
                comp.append((r, c))
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    if m[nr, nc] and not seen[nr, nc]:
                        seen[nr, nc] = True
                        q.append((nr, nc))
            components.append(comp)
    return components


def _component_aspect_ratio(comp: Sequence[Tuple[int, int]], rows: int, cols: int) -> float:
    """Aspect ratio (long side / short side, >= 1) of a component's bounding box.

    Computed on the PERIODIC grid: the extent along each axis is the SMALLEST arc that
    contains all the component's cells on that circular axis (so a blob that straddles the
    wrap seam still gets a compact box, not the full width). A single-cell component has
    aspect ratio 1.
    """
    rs = sorted({r for r, _ in comp})
    cs = sorted({c for _, c in comp})
    row_extent = _periodic_extent(rs, rows)
    col_extent = _periodic_extent(cs, cols)
    lo, hi = sorted((row_extent, col_extent))
    return hi / lo if lo > 0 else 1.0


def _periodic_extent(sorted_coords: Sequence[int], size: int) -> float:
    """Smallest number of cells spanning ``sorted_coords`` on a circular axis of length
    ``size`` (>= 1). Finds the largest gap between consecutive occupied coordinates (with
    wrap) and returns size minus that gap."""
    if not sorted_coords:
        return 1.0
    if len(sorted_coords) == 1:
        return 1.0
    max_gap = 0
    n = len(sorted_coords)
    for i in range(n):
        a = sorted_coords[i]
        b = sorted_coords[(i + 1) % n]
        gap = (b - a) % size
        if i == n - 1:
            gap = (sorted_coords[0] + size - sorted_coords[-1]) % size
        if gap > max_gap:
            max_gap = gap
    extent = size - max_gap
    return float(max(extent, 1))


# -- Model ------------------------------------------------------------------------

class GrayScottModel:
    """Gray-Scott reaction-diffusion (Pearson 1993) on an L x L periodic grid.

    Construct with the feed rate F and kill rate k (these select the morphology), plus the
    grid size, domain side, diffusions, time step, seed strength and seed. ``step`` performs
    one explicit-Euler update of both fields; ``run`` integrates a fixed number of steps and
    records the spot count + V-field std at regular intervals. Deterministic given ``seed``.

    This is a grid PDE (disclosed), not an agent model, so there is no AgentSet / scheduler;
    the "tick" is the synchronous field update.
    """

    def __init__(self, *, F: float, k: float, n: int = GRID_N, side: float = DOMAIN_SIDE,
                 Du: float = DU, Dv: float = DV, dt: float = 1.0,
                 seed_half: int = 10, noise: float = 0.02, seed: int = 0) -> None:
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if side <= 0:
            raise ValueError(f"need side > 0 (got {side})")
        if Du <= 0 or Dv <= 0:
            raise ValueError(f"need Du>0, Dv>0 (got Du={Du}, Dv={Dv})")
        if dt <= 0:
            raise ValueError(f"need dt > 0 (got {dt})")
        if seed_half <= 0 or 2 * seed_half > n:
            raise ValueError(f"need 0 < seed_half and 2*seed_half <= n (got {seed_half}, n={n})")
        self.F = float(F)
        self.k = float(k)
        self.n = int(n)
        self.side = float(side)
        self.Du = float(Du)
        self.Dv = float(Dv)
        self.dt = float(dt)
        self.dx = self.side / self.n
        self.seed_half = int(seed_half)
        self.noise = float(noise)
        self.seed = int(seed)
        self.t = 0

        # Stability guard: explicit-Euler diffusion needs dt < dx^2 / (4*max(Du,Dv)).
        self.diffusion_dt_limit = self.dx * self.dx / (4.0 * max(self.Du, self.Dv))
        if self.dt >= self.diffusion_dt_limit:
            raise ValueError(
                f"dt={self.dt} violates the diffusion stability limit "
                f"dx^2/(4*max(Du,Dv))={self.diffusion_dt_limit:.4g}")

        self._rng = np.random.default_rng(seed)
        self.U, self.V = self._initial_condition()

    def _initial_condition(self) -> Tuple[np.ndarray, np.ndarray]:
        """The standard Pearson seed: U=1, V=0 everywhere, except a small central square
        where U is knocked to ~0.5 and V bumped to ~0.25, with a little seeded noise so the
        pattern can nucleate off the perfectly symmetric state."""
        U = np.ones((self.n, self.n), dtype=np.float64)
        V = np.zeros((self.n, self.n), dtype=np.float64)
        c = self.n // 2
        h = self.seed_half
        sl = (slice(c - h, c + h), slice(c - h, c + h))
        U[sl] = 0.50
        V[sl] = 0.25
        # Small symmetry-breaking noise inside the seed (seeded, deterministic).
        noise_block = self.noise * self._rng.standard_normal((2 * h, 2 * h))
        U[sl] += noise_block
        V[sl] += self.noise * self._rng.standard_normal((2 * h, 2 * h))
        np.clip(U, 0.0, 1.0, out=U)
        np.clip(V, 0.0, 1.0, out=V)
        return U, V

    # -- one synchronous explicit-Euler update of both fields --
    def step(self) -> None:
        """Advance both concentration fields one time step (forward Euler).

        Uses one shared start-of-step snapshot for the Laplacians and the reaction, so the
        update is synchronous (both fields advance together off the same current state)."""
        U, V = self.U, self.V
        lu = laplacian(U, self.dx)
        lv = laplacian(V, self.dx)
        uvv = U * V * V
        dU = self.Du * lu - uvv + self.F * (1.0 - U)
        dV = self.Dv * lv + uvv - (self.F + self.k) * V
        self.U = U + self.dt * dU
        self.V = V + self.dt * dV
        self.t += 1

    # -- metrics --
    def high_v_mask(self, threshold: float = 0.25) -> np.ndarray:
        """Boolean mask of cells whose V exceeds ``threshold`` (the pattern / high-V
        regions). The default 0.25 sits between the near-zero background of the fed state
        and the ~0.3-0.4 plateau inside spots/stripes."""
        return self.V > threshold

    def count_spots(self, threshold: float = 0.25, min_size: int = 3) -> int:
        """Number of connected high-V components with at least ``min_size`` cells.

        ``min_size`` discards single-cell numerical speckle so the count reflects genuine
        blobs, not lone pixels."""
        comps = connected_components(self.high_v_mask(threshold))
        return sum(1 for comp in comps if len(comp) >= min_size)

    def spot_stats(self, threshold: float = 0.25, min_size: int = 3) -> Dict[str, Any]:
        """Connected-component summary of the high-V field: number of blobs (>= min_size),
        their sizes, and the MEDIAN bounding-box aspect ratio. Median aspect ~1 => compact
        spots; median aspect >> 1 => elongated stripes/labyrinths."""
        comps = [c for c in connected_components(self.high_v_mask(threshold))
                 if len(c) >= min_size]
        if not comps:
            return {"n_components": 0, "median_aspect": 0.0, "max_aspect": 0.0,
                    "sizes": [], "aspects": []}
        aspects = [_component_aspect_ratio(c, self.n, self.n) for c in comps]
        sizes = [len(c) for c in comps]
        return {
            "n_components": len(comps),
            "median_aspect": float(np.median(aspects)),
            "max_aspect": float(np.max(aspects)),
            "mean_aspect": float(np.mean(aspects)),
            "sizes": sizes,
            "aspects": aspects,
        }

    def field_std(self) -> float:
        """Spatial standard deviation of the V field over the whole grid. ~0 means a flat
        (homogeneous) field; a patterned field has a substantial std."""
        return float(np.std(self.V))

    def field_mean_v(self) -> float:
        """Spatial mean of the V field (how much autocatalyst survives)."""
        return float(np.mean(self.V))

    # -- run --
    def run(self, n_steps: int = 10000, *, record_every: int = 200,
            threshold: float = 0.25, min_size: int = 3) -> Dict[str, Any]:
        """Integrate ``n_steps`` explicit-Euler steps, recording the spot count and V-std
        every ``record_every`` steps (and at t=0 and the final step).

        Returns the final field metrics, the peak spot count reached during the run
        (``max_spot_count`` — the self-replication signature), and the recorded series.
        Deterministic given the construction seed."""
        if n_steps < 0:
            raise ValueError(f"need n_steps >= 0 (got {n_steps})")
        if record_every <= 0:
            raise ValueError(f"need record_every > 0 (got {record_every})")
        step_series: List[int] = []
        spot_series: List[int] = []
        std_series: List[float] = []
        meanv_series: List[float] = []

        def record() -> None:
            step_series.append(self.t)
            spot_series.append(self.count_spots(threshold, min_size))
            std_series.append(self.field_std())
            meanv_series.append(self.field_mean_v())

        record()  # t=0 baseline
        for i in range(n_steps):
            self.step()
            if (i + 1) % record_every == 0 or (i + 1) == n_steps:
                record()

        final_stats = self.spot_stats(threshold, min_size)
        return {
            "F": self.F, "k": self.k, "n": self.n, "side": self.side,
            "Du": self.Du, "Dv": self.Dv, "dt": self.dt, "dx": self.dx,
            "seed": self.seed, "seed_half": self.seed_half, "noise": self.noise,
            "n_steps": n_steps, "record_every": record_every,
            "threshold": threshold, "min_size": min_size,
            "final_n_components": final_stats["n_components"],
            "final_median_aspect": final_stats["median_aspect"],
            "final_max_aspect": final_stats["max_aspect"],
            "final_mean_aspect": final_stats.get("mean_aspect", 0.0),
            "final_sizes": final_stats["sizes"],
            "final_std_v": self.field_std(),
            "final_mean_v": self.field_mean_v(),
            "max_spot_count": max(spot_series) if spot_series else 0,
            "step_series": step_series,
            "spot_series": spot_series,
            "std_series": std_series,
            "mean_v_series": meanv_series,
        }


# -- run helpers ------------------------------------------------------------------

def run_regime(F: float, k: float, *, n: int = GRID_N, side: float = DOMAIN_SIDE,
               Du: float = DU, Dv: float = DV, dt: float = 1.0, seed_half: int = 10,
               noise: float = 0.02, seed: int = 0, n_steps: int = 10000,
               record_every: int = 200, threshold: float = 0.25,
               min_size: int = 3) -> Dict[str, Any]:
    """Integrate one Gray-Scott regime at a given (F, k) and the fixed numerics; return the
    run summary (final morphology metrics + the peak spot count + series)."""
    return GrayScottModel(
        F=F, k=k, n=n, side=side, Du=Du, Dv=Dv, dt=dt, seed_half=seed_half,
        noise=noise, seed=seed).run(
        n_steps, record_every=record_every, threshold=threshold, min_size=min_size)
