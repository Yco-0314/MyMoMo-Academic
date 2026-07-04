"""Diffusion-Limited Aggregation (Witten & Sander 1981) — a faithful ON-LATTICE reproduction.

Source: Witten, T.A. & Sander, L.M. (1981), "Diffusion-Limited Aggregation, a Kinetic Critical
Phenomenon", Phys. Rev. Lett. 47, 1400. doi:10.1103/PhysRevLett.47.1400.

A single seed particle occupies the centre cell of a square lattice. Particles are released one at
a time from a birth circle just outside the current cluster and perform an unbiased nearest-neighbour
(von Neumann, 4-direction) random walk. A walker STICKS permanently + irreversibly in its current
cell the moment any of its 4 neighbour cells is already occupied by the cluster; then the next
particle is launched. A walker that strays beyond a kill circle (a few × the cluster radius) is
relaunched (the 2D walk is recurrent, so un-killed walkers waste enormous time far away).

On-lattice is the cleanest FAITHFUL realization for a reproduction: each cell is occupied or empty,
so particles can NEVER overlap and every stuck particle sits at exactly one lattice step (the contact
distance) from the cluster — no fiddly off-lattice tangent geometry, no overlap bug. The lock permits
on-lattice and asks us to disclose its (mild) square-lattice ANISOTROPY: the measured mass dimension
is ~1.67-1.71 at accessible cluster sizes (canonical off-lattice value 1.71), drifting slowly toward
the Kesten bound 3/2 only for enormous clusters with cross-shaped arms.

The aggregate is a self-similar branched/dendritic fractal: the enclosed mass scales as a power law
M(r) ~ r^D with non-integer D < 2 (Witten & Sander's central claim), and growth is tip-dominated by
diffusive screening (walkers are absorbed at protruding tips; deep interior fjords are starved).

Built on the neutral platform (``abm_auto._platform``): each walker is a ``WalkerAgent`` carrying its
lattice position; ``DLAModel`` launches walkers over the ``AgentSet`` roster and records each stuck
particle's cell + attachment radius. Nearest-occupied lookup is O(1) via a set of occupied cells.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel


NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class WalkerAgent(Agent):
    """One diffusing particle: a nearest-neighbour random walker with a lattice position (i, j).

    The walk is driven by the model (launch → step until it sticks), so the per-agent ``step`` is a
    no-op; the walker's position lives in ``i, j``."""

    def __init__(self, agent_id: int, model: "DLAModel", *, i: int, j: int) -> None:
        super().__init__(agent_id, model)
        self.i = i
        self.j = j

    def step(self) -> None:  # pragma: no cover - the walk lives on the model
        return None


class DLAModel(AgentModel):
    """Drives on-lattice Witten-Sander DLA.

    Construct with the target particle count ``n`` and a ``seed``. ``grow()`` launches walkers one at
    a time until ``n`` particles have stuck, recording each stuck cell (``cells``) and its radius from
    the seed (``attach_r``). ``contact`` is the lattice step (=1) at which a walker sticks.
    """

    def __init__(self, n: int = 4000, *, birth_gap: int = 3, kill_factor: float = 3.0,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if birth_gap < 1:
            raise ValueError(f"need birth_gap >= 1 (got {birth_gap})")
        if kill_factor <= 1.0:
            raise ValueError(f"need kill_factor > 1 (got {kill_factor})")
        self.seed_value = seed
        self.n = int(n)
        self.birth_gap = int(birth_gap)
        self.kill_factor = float(kill_factor)
        self.contact = 1.0                       # lattice step = contact distance (never overlap)

        # cluster state
        self.occupied: set[Tuple[int, int]] = set()
        self.xs: List[int] = []                  # per-particle lattice coords (seed first)
        self.ys: List[int] = []
        self.attach_r: List[float] = []          # per-particle radius from the seed
        self.r_max = 0.0                          # current max cluster radius

        # seed at the origin
        self._add((0, 0))
        self.agent_list: List[WalkerAgent] = []

    # -- cluster bookkeeping --
    def _add(self, cell: Tuple[int, int]) -> None:
        i, j = cell
        self.occupied.add(cell)
        self.xs.append(i)
        self.ys.append(j)
        r = math.hypot(i, j)
        self.attach_r.append(r)
        if r > self.r_max:
            self.r_max = r

    @property
    def size(self) -> int:
        return len(self.xs)

    def _touches_cluster(self, i: int, j: int) -> bool:
        occ = self.occupied
        for di, dj in NEIGHBOURS:
            if (i + di, j + dj) in occ:
                return True
        return False

    # -- growth --
    def grow_one(self) -> WalkerAgent:
        """Launch ONE walker and walk it (von Neumann steps) until a neighbour cell is occupied;
        stick it in its current cell and return the stuck walker. Relaunch on the birth circle if it
        strays beyond the kill radius."""
        rng = self.rng
        r_birth = self.r_max + self.birth_gap
        r_kill = self.kill_factor * r_birth + self.birth_gap

        def launch() -> Tuple[int, int]:
            theta = rng.uniform(0.0, 2.0 * math.pi)
            return (int(round(r_birth * math.cos(theta))),
                    int(round(r_birth * math.sin(theta))))

        i, j = launch()
        while True:
            if self._touches_cluster(i, j) and (i, j) not in self.occupied:
                self._add((i, j))
                walker = WalkerAgent(self.size - 1, self, i=i, j=j)
                self.agent_list.append(walker)
                self.add_agent(walker)
                return walker
            di, dj = NEIGHBOURS[rng.randrange(4)]
            i += di
            j += dj
            if math.hypot(i, j) > r_kill:
                i, j = launch()

    def grow(self, n: Optional[int] = None) -> None:
        """Grow the cluster to ``n`` particles (default: the constructed ``self.n``)."""
        target = self.n if n is None else int(n)
        while self.size < target:
            self.grow_one()

    # -- metrics --
    def mass_dimension(self, *, n_bins: int = 24, r_min_frac: float = 0.06,
                       r_max_frac: float = 0.65) -> Dict[str, Any]:
        """Fit the mass (fractal) dimension from the enclosed-mass scaling M(r) ~ r^D.

        M(r) = number of cluster particles within radius r of the seed. Fit log M vs log r by OLS
        over the middle window r ∈ [r_min_frac, r_max_frac] · R_max (dropping the innermost few
        shells, where the seed disk is compact, and the noisy outer shell). Returns the slope D and
        R²."""
        rs = sorted(self.attach_r)
        r_max = rs[-1] if rs else 0.0
        if r_max <= 0:
            return {"D": 0.0, "r2": 0.0, "n_points": 0}
        lo, hi = r_min_frac * r_max, r_max_frac * r_max
        # log-spaced radii in the window
        radii = [lo * (hi / lo) ** (t / (n_bins - 1)) for t in range(n_bins)] if hi > lo else []
        pts: List[Tuple[float, float]] = []
        for r in radii:
            m = sum(1 for rr in rs if rr <= r)
            if m > 0:
                pts.append((math.log(r), math.log(m)))
        if len(pts) < 3:
            return {"D": 0.0, "r2": 0.0, "n_points": len(pts)}
        n = len(pts)
        sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
        sxx = sum(p[0] * p[0] for p in pts); sxy = sum(p[0] * p[1] for p in pts)
        denom = n * sxx - sx * sx
        slope = (n * sxy - sx * sy) / denom if denom != 0 else 0.0
        intercept = (sy - slope * sx) / n
        # R^2
        mean_y = sy / n
        ss_tot = sum((p[1] - mean_y) ** 2 for p in pts)
        ss_res = sum((p[1] - (slope * p[0] + intercept)) ** 2 for p in pts)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return {"D": slope, "r2": r2, "n_points": n}

    def density_decreasing(self, *, n_shells: int = 8) -> bool:
        """True if the average interior density (mass within r / area of disk r) DECREASES from the
        inner to the outer window — the porous/screened-interior signature of a fractal (vs a
        compact disk, whose density is ~constant)."""
        rs = sorted(self.attach_r)
        r_max = rs[-1] if rs else 0.0
        if r_max <= 0:
            return False
        inner_r = 0.25 * r_max
        outer_r = 0.75 * r_max
        m_in = sum(1 for rr in rs if rr <= inner_r)
        m_out = sum(1 for rr in rs if rr <= outer_r)
        dens_in = m_in / (math.pi * inner_r * inner_r) if inner_r > 0 else 0.0
        dens_out = m_out / (math.pi * outer_r * outer_r) if outer_r > 0 else 0.0
        return dens_out < dens_in

    def outer_shell_attachment_fraction(self, *, shell_frac: float = 0.75) -> float:
        """Fraction of NON-SEED particles that stuck at a radius > shell_frac · R_final — the
        tip-attachment / diffusive-screening signature (a uniform-area disk would put ~0.44 in the
        outer r∈[0.75,1.0] annulus; screening pushes it higher)."""
        if self.size <= 1:
            return 0.0
        r_final = self.r_max
        thr = shell_frac * r_final
        outer = sum(1 for r in self.attach_r[1:] if r > thr)   # skip the seed (index 0)
        return outer / (self.size - 1)


# -- run helpers --------------------------------------------------------------

def run_single(n: int = 4000, *, seed: int = 0) -> Dict[str, Any]:
    """Grow one DLA cluster and return its fractal-dimension + screening metrics."""
    m = DLAModel(n=n, seed=seed)
    m.grow()
    md = m.mass_dimension()
    return {
        "n": m.size,
        "seed": seed,
        "D": md["D"],
        "D_r2": md["r2"],
        "r_max": m.r_max,
        "density_decreasing": m.density_decreasing(),
        "outer_shell_fraction": m.outer_shell_attachment_fraction(),
    }


def run_many_seeds(n: int = 4000, *, n_seeds: int = 4, seed_base: int = 0) -> Dict[str, Any]:
    """Grow ``n_seeds`` DLA clusters and summarise the fractal dimension + screening metrics."""
    runs = [run_single(n, seed=seed_base + s) for s in range(n_seeds)]
    Ds = [r["D"] for r in runs]
    mean_D = sum(Ds) / len(Ds)
    var_D = sum((d - mean_D) ** 2 for d in Ds) / len(Ds)
    return {
        "n": n, "n_seeds": n_seeds, "seed_base": seed_base,
        "per_seed_D": Ds,
        "per_seed_r2": [r["D_r2"] for r in runs],
        "per_seed_outer_fraction": [r["outer_shell_fraction"] for r in runs],
        "per_seed_density_decreasing": [r["density_decreasing"] for r in runs],
        "mean_D": mean_D,
        "std_D": var_D ** 0.5,
        "min_D": min(Ds),
        "max_D": max(Ds),
        "mean_outer_fraction": sum(r["outer_shell_fraction"] for r in runs) / len(runs),
        "all_density_decreasing": all(r["density_decreasing"] for r in runs),
    }
