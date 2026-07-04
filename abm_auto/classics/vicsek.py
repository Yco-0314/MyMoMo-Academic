"""Vicsek flocking (Vicsek et al. 1995) — a faithful agent-based reproduction.

Source: Vicsek, T., Czirok, A., Ben-Jacob, E., Cohen, I. & Shochet, O. (1995),
"Novel type of phase transition in a system of self-driven particles",
Phys. Rev. Lett. 75:1226-1229. doi:10.1103/PhysRevLett.75.1226.

Rules (verified against the paper; the standard scalar-noise SPP model):
  * N self-propelled ``ParticleAgent``s live in an L x L PERIODIC box. Each carries a
    position (x, y) and a heading angle theta. Every particle moves at the SAME constant
    speed ``v`` (here 0.03); only its DIRECTION changes.
  * Interaction radius ``r`` (here 1). At each tick a particle's new heading is the
    argument of the AVERAGE of the unit heading vectors e^{i*theta_j} over all particles
    j within distance r of it (PERIODIC distance), INCLUDING itself, PLUS a uniform random
    angular perturbation in [-eta/2, +eta/2]:
        theta_i(t+1) = Arg( sum_{j in N_r(i)} e^{i*theta_j(t)} ) + Delta,  Delta ~ U(-eta/2, eta/2)
  * Then every particle moves:  x_i(t+1) = x_i(t) + v*cos(theta_i(t+1)),  similarly y,
    with periodic wrap into [0, L).
  * The update is SYNCHRONOUS: every particle's new heading is computed from the SAME
    start-of-tick snapshot, then all particles move. (Order-independent, hence the run is
    deterministic given the seeded RNG draw sequence.)

Order parameter (the locked grading metric):
    phi = | (1/N) * sum_i e^{i*theta_i} |   in [0, 1].
phi ~ 1 is an ordered, coherently moving flock; phi ~ 0 is disordered motion. Vicsek's
result: a noise-driven order-disorder transition — phi falls from ~1 to ~0 as the noise
eta increases. phi is measured as the mean over the tail of the run (after the transient).

Built on the neutral platform (``abm_auto._platform``): each particle is a
``ParticleAgent`` carrying its own (x, y, theta); ``VicsekModel`` drives the synchronous
heading + move update over the ``AgentSet`` roster and records (via a ``DataCollector``)
the per-tick order parameter phi. Neighbour lookup uses a periodic cell list (bucket grid
of cell size >= r) so a tick is O(N) rather than O(N^2); the result is identical to the
brute-force all-pairs computation, only faster.
"""
from __future__ import annotations

import cmath
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class ParticleAgent(Agent):
    """One self-propelled particle: position (x, y) and heading ``theta`` (radians).

    The Vicsek update is a model-level synchronous tick (all new headings from one
    snapshot, then all move), so the per-agent ``step`` is intentionally a no-op; the
    ``_next_theta`` field stages the heading computed this tick before the model commits
    the moves.
    """

    def __init__(self, agent_id: int, model: "VicsekModel", *,
                 x: float, y: float, theta: float) -> None:
        super().__init__(agent_id, model)
        self.x = x
        self.y = y
        self.theta = theta
        self._next_theta = theta

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        """The Vicsek tick (align headings from a snapshot, then move) is a model-level
        synchronous update, not an autonomous single-agent step, so this is a no-op."""
        return None


# -- periodic geometry helpers ------------------------------------------------

def periodic_delta(a: float, b: float, L: float) -> float:
    """Minimum-image signed displacement a-b on a periodic line of length L, in
    (-L/2, L/2]."""
    d = a - b
    d -= L * round(d / L)
    return d


def periodic_dist2(x1: float, y1: float, x2: float, y2: float, L: float) -> float:
    """Squared minimum-image (toroidal) distance between two points in an L x L box."""
    dx = periodic_delta(x1, x2, L)
    dy = periodic_delta(y1, y2, L)
    return dx * dx + dy * dy


# -- Model --------------------------------------------------------------------

class VicsekModel(AgentModel):
    """Drives the scalar-noise Vicsek self-propelled-particle dynamics.

    Construct with N, box size L, speed v, interaction radius r, noise amplitude eta,
    and a seed. ``run(n_ticks)`` advances the synchronous heading+move update and records
    the per-tick order parameter phi; ``order_parameter`` reads the current phi.
    """

    def __init__(self, n: int = 300, *, L: float = 12.0, v: float = 0.03, r: float = 1.0,
                 eta: float = 0.5, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if L <= 0 or v < 0 or r <= 0:
            raise ValueError(f"need L>0, v>=0, r>0 (got L={L}, v={v}, r={r})")
        if eta < 0:
            raise ValueError(f"need eta >= 0 (got {eta})")
        self.seed_value = seed
        self.n = n
        self.L = float(L)
        self.v = float(v)
        self.r = float(r)
        self.r2 = self.r * self.r
        self.eta = float(eta)
        self.density = n / (self.L * self.L)

        # Periodic cell list: square cells of side >= r so a particle's r-neighbours all
        # lie in its own cell or the 8 adjacent ones (with wrap). With L=12, r=1 this is
        # a 12x12 grid. n_cells>=1 (degenerate small box falls back to one cell == brute
        # force, still correct).
        self.n_cells = max(1, int(math.floor(self.L / self.r)))
        self.cell_size = self.L / self.n_cells

        # Random initial state: positions uniform in the box, headings uniform in
        # [0, 2*pi). (Seed-dependent; the only randomness besides the per-tick noise.)
        self.agent_list: List[ParticleAgent] = []
        for i in range(n):
            x = self.rng.uniform(0.0, self.L)
            y = self.rng.uniform(0.0, self.L)
            theta = self.rng.uniform(0.0, 2.0 * math.pi)
            agent = ParticleAgent(i, self, x=x, y=y, theta=theta)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({"phi": lambda m: m.order_parameter()})

    # -- metrics --
    def order_parameter(self) -> float:
        """phi = | (1/N) sum_i e^{i theta_i} |, the normalised average velocity
        direction coherence, in [0, 1]."""
        if self.n == 0:
            return 0.0
        acc = 0j
        for a in self.agent_list:
            acc += cmath.exp(1j * a.theta)
        return abs(acc) / self.n

    # -- neighbour lookup (periodic cell list) --
    def _cell_of(self, x: float, y: float) -> Tuple[int, int]:
        cx = int(x / self.cell_size) % self.n_cells
        cy = int(y / self.cell_size) % self.n_cells
        return cx, cy

    def _build_cells(self) -> Dict[Tuple[int, int], List[ParticleAgent]]:
        cells: Dict[Tuple[int, int], List[ParticleAgent]] = {}
        for a in self.agent_list:
            key = self._cell_of(a.x, a.y)
            cells.setdefault(key, []).append(a)
        return cells

    def _neighbor_sum(self, a: ParticleAgent,
                      cells: Dict[Tuple[int, int], List[ParticleAgent]]) -> complex:
        """Sum of unit heading vectors e^{i theta_j} over all particles j within r of a
        (periodic distance), INCLUDING a itself. Scans a's cell and its 8 neighbours
        (with wrap); the cell side >= r guarantees no in-range neighbour is missed."""
        cx, cy = self._cell_of(a.x, a.y)
        acc = 0j
        nc = self.n_cells
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                key = ((cx + dx) % nc, (cy + dy) % nc)
                bucket = cells.get(key)
                if not bucket:
                    continue
                for b in bucket:
                    if b is a:
                        acc += cmath.exp(1j * b.theta)
                    elif periodic_dist2(a.x, a.y, b.x, b.y, self.L) <= self.r2:
                        acc += cmath.exp(1j * b.theta)
        return acc

    def _neighbor_sum_bruteforce(self, a: ParticleAgent) -> complex:
        """O(N) reference neighbour sum (all pairs, periodic distance, incl. self). Used
        only to validate the cell-list path in tests; the model uses the cell list."""
        acc = 0j
        for b in self.agent_list:
            if b is a or periodic_dist2(a.x, a.y, b.x, b.y, self.L) <= self.r2:
                acc += cmath.exp(1j * b.theta)
        return acc

    # -- tick --
    def step(self) -> None:
        """One synchronous Vicsek tick.

        (1) From the start-of-tick snapshot, every particle's new heading = arg of the
            average neighbour heading-vector + a fresh uniform noise in [-eta/2, eta/2].
        (2) Then every particle moves a step ``v`` along its NEW heading and wraps into
            [0, L). Headings are staged in ``_next_theta`` so the alignment reads a
            consistent snapshot (synchronous update)."""
        cells = self._build_cells()
        half_eta = self.eta / 2.0
        for a in self.agent_list:
            acc = self._neighbor_sum(a, cells)
            # arg(0) is undefined; an empty/cancelling sum keeps the current heading
            # before noise. (With self always included this is effectively unreachable,
            # but it keeps the rule total.)
            mean_angle = cmath.phase(acc) if acc != 0 else a.theta
            noise = self.rng.uniform(-half_eta, half_eta)
            a._next_theta = mean_angle + noise
        for a in self.agent_list:
            a.theta = a._next_theta
            a.x = (a.x + self.v * math.cos(a.theta)) % self.L
            a.y = (a.y + self.v * math.sin(a.theta)) % self.L
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_ticks: int = 500, *, measure_last: int = 100) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_ticks`` synchronous Vicsek ticks; return the run summary.

        ``measure_last`` is the trailing window over which the steady-state order
        parameter is averaged (the transient is the leading n_ticks - measure_last
        ticks). Returns the steady phi, the final phi, and the full per-tick phi series.
        """
        if measure_last <= 0 or measure_last > n_ticks + 1:
            raise ValueError(
                f"measure_last must be in [1, n_ticks+1] (got {measure_last}, n_ticks={n_ticks})")
        self.reporter.collect(self)              # t=0 baseline
        for _ in range(n_ticks):
            self.step()
        series = self.reporter.series("phi")
        steady = steady_phi(series, window=measure_last)
        return {
            "n": self.n,
            "L": self.L,
            "v": self.v,
            "r": self.r,
            "eta": self.eta,
            "density": self.density,
            "seed": self.seed_value,
            "n_ticks": n_ticks,
            "measure_last": measure_last,
            "steady_phi": steady,
            "final_phi": series[-1],
            "phi_series": series,
        }


# -- summary helpers ----------------------------------------------------------

def steady_phi(series: Sequence[float], *, window: int = 100) -> float:
    """Steady-state order parameter = mean of the trailing ``window`` of the phi series
    (or the whole series if shorter). Averaging the tail smooths the finite-N jitter and
    discards the transient before measurement."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(n: int = 300, *, L: float = 12.0, v: float = 0.03, r: float = 1.0,
               eta: float = 0.5, seed: int = 0, n_ticks: int = 500,
               measure_last: int = 100) -> Dict[str, Any]:
    """One Vicsek run at a given (eta, seed)."""
    return VicsekModel(n, L=L, v=v, r=r, eta=eta, seed=seed).run(
        n_ticks, measure_last=measure_last)


def run_many_seeds(n: int = 300, *, L: float = 12.0, v: float = 0.03, r: float = 1.0,
                   eta: float = 0.5, n_seeds: int = 10, seed_base: int = 0,
                   n_ticks: int = 500, measure_last: int = 100) -> Dict[str, Any]:
    """Run ``n_seeds`` Vicsek runs (seed ``seed_base + i``) at fixed parameters and
    summarise the steady order parameter phi across seeds (mean + spread).

    Returns the per-seed steady phi values, their mean / std / min / max, and one
    representative phi trajectory (first seed) for plotting/inspection.
    """
    runs = [run_single(n, L=L, v=v, r=r, eta=eta, seed=seed_base + i,
                       n_ticks=n_ticks, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_steady = [rr["steady_phi"] for rr in runs]
    per_seed_final = [rr["final_phi"] for rr in runs]
    mean_steady = sum(per_seed_steady) / n_seeds
    var_steady = sum((s - mean_steady) ** 2 for s in per_seed_steady) / n_seeds
    return {
        "n": n,
        "L": L,
        "v": v,
        "r": r,
        "eta": eta,
        "density": n / (L * L),
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "n_ticks": n_ticks,
        "measure_last": measure_last,
        "per_seed_steady": per_seed_steady,
        "per_seed_final": per_seed_final,
        "mean_steady_phi": mean_steady,
        "var_steady_phi": var_steady,
        "std_steady_phi": var_steady ** 0.5,
        "min_steady_phi": min(per_seed_steady),
        "max_steady_phi": max(per_seed_steady),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_series": runs[0]["phi_series"],
    }
