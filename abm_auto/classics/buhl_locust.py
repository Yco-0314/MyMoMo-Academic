"""Buhl et al. marching locusts (2006) — the Czirok 1D self-propelled-particle variant.

Source: Buhl, J., Sumpter, D. J. T., Couzin, I. D., Hale, J. J., Despland, E.,
Miller, E. R. & Simpson, S. J. (2006), "From disorder to order in marching
locusts", Science 312(5778):1402-1406. doi:10.1126/science.1125142. The 1D
alignment dynamics are the Czirok-Barabasi-Vicsek self-propelled-particle model:
Czirok, A., Barabasi, A.-L. & Vicsek, T. (1999), "Collective motion of
self-propelled particles: kinetic phase transition in one dimension",
Phys. Rev. Lett. 82:209. doi:10.1103/PhysRevLett.82.209.

FRAMING (disclosed): genuine-agent (self-propelled particles, 1D ring, disclosed).
Each locust is an autonomous ``LocustAgent`` carrying its own continuous position on a
periodic ring and a discrete heading s in {-1, +1}. There is no field/grid/mean-field
shortcut: neighbour averaging is computed per agent over the real ring geometry.

Rules (the Czirok 1D self-propelled-particle update):
  * N agents on a periodic ring of circumference ``Lr``. Agent i carries a position
    ``x[i]`` in [0, Lr) and a heading ``s[i]`` in {-1, +1} (dimensionless velocity
    +/- ``speed``).
  * SYNCHRONOUS tick (all new headings computed from one start-of-tick snapshot, then
    all commit, then all move):
      1. Each agent computes the LOCAL AVERAGE velocity of the neighbours within
         interaction range ``R`` on the ring (periodic distance <= R), INCLUDING itself:
             u_i = mean_{ j : dist_ring(x_j, x_i) <= R } s_j        (in [-1, +1])
      2. Czirok piecewise/sigmoid alignment response G pushes the heading toward the
         sign of u_i, then heading noise of amplitude ``eta`` is added and the sign is
         taken:
             s_i(t+1) = sign( G(u_i) + eta * xi_i ),   xi_i ~ Uniform(-1/2, +1/2)
         with the Czirok response G(u) = tanh(beta * u) (a smooth monotone push toward
         the local mean; sign(G(u)) = sign(u), and |G| saturates so a strong local
         consensus resists noise while a weak one does not). ``sign(0) := +1`` (a lone,
         perfectly-balanced agent keeps a definite heading rather than freezing).
      3. Each agent then MOVES at fixed speed in its (new) heading direction and wraps:
             x_i(t+1) = ( x_i(t) + speed * s_i(t+1) ) mod Lr

    This is a genuine per-agent update over the real ring geometry; the neighbour
    average is the actual local average, not an all-to-all mean-field field.

Control parameter = DENSITY = N / Lr (agents per ring length). Swept by varying the ring
length ``Lr`` at FIXED N (fewer agents per unit ring == lower density). Low density ->
neighbourhoods are usually empty (an agent sees only itself), so noise dominates and the
population stays disordered; high density -> neighbourhoods are crowded, local consensus
overwhelms noise, and the population marches together.

Order parameter (the locked grading metric):
    phi = | (1/N) * sum_i s_i |   in [0, 1].
phi ~ 0 is a disordered band (headings cancel); phi ~ 1 is a coherent marching band (all
one way). The NET DIRECTION is sign( sum_i s_i ); over a long run near the critical
density this sign flips intermittently (the empirical Buhl-et-al. signature of
near-critical locust bands), whereas deep in the ordered phase it locks and never flips.

Built on the neutral platform (``abm_auto._platform``): each locust is a ``LocustAgent``
carrying its own (x, s); ``LocustModel`` drives the synchronous align+move update over the
``AgentSet`` roster and records (via a ``DataCollector``) the per-tick order parameter phi
and the signed net direction. Neighbour lookup uses a periodic bucket grid (cells of side
>= R) so a tick is O(N) rather than O(N^2); the result is identical to the brute-force
all-pairs neighbour average (verified in tests).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- periodic ring geometry ---------------------------------------------------

def ring_delta(a: float, b: float, L: float) -> float:
    """Minimum-image signed displacement a-b on a periodic ring of circumference L,
    in (-L/2, L/2]."""
    d = a - b
    d -= L * round(d / L)
    return d


def ring_dist(a: float, b: float, L: float) -> float:
    """Minimum-image (periodic) distance between two points on a ring of circumference L."""
    return abs(ring_delta(a, b, L))


# -- Agent --------------------------------------------------------------------

class LocustAgent(Agent):
    """One marching locust: continuous ring position ``x`` and heading ``s`` in {-1, +1}.

    The Czirok tick is a model-level synchronous update (all new headings from one
    snapshot, then all commit and move), so the per-agent ``step`` is intentionally a
    no-op; ``_next_s`` stages the heading computed this tick before the model commits.
    """

    def __init__(self, agent_id: int, model: "LocustModel", *, x: float, s: int) -> None:
        super().__init__(agent_id, model)
        self.x = x
        self.s = s
        self._next_s = s

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        """The Czirok tick (align from a snapshot, then move) is a model-level
        synchronous update, not an autonomous single-agent step, so this is a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class LocustModel(AgentModel):
    """Drives the Buhl et al. (2006) Czirok 1D self-propelled-particle dynamics.

    Construct with N, ring length ``Lr`` (=> density N/Lr), interaction range ``R``,
    heading-noise amplitude ``eta``, alignment gain ``beta``, speed, and a seed.
    ``run(n_steps, measure_last=...)`` advances the synchronous align+move update and
    records the per-tick order parameter phi and the signed net direction.
    """

    def __init__(self, n: int = 60, *, Lr: float = 60.0, R: float = 1.0,
                 eta: float = 0.6, beta: float = 4.0, speed: float = 0.1,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if Lr <= 0:
            raise ValueError(f"need Lr > 0 (got {Lr})")
        if R <= 0:
            raise ValueError(f"need R > 0 (got {R})")
        if eta < 0:
            raise ValueError(f"need eta >= 0 (got {eta})")
        if beta <= 0:
            raise ValueError(f"need beta > 0 (got {beta})")
        if speed <= 0:
            raise ValueError(f"need speed > 0 (got {speed})")
        if 2.0 * R > Lr:
            raise ValueError(
                f"need 2R <= Lr so the ring is larger than one neighbourhood "
                f"(got R={R}, Lr={Lr})")
        self.seed_value = seed
        self.n = n
        self.Lr = float(Lr)
        self.R = float(R)
        self.eta = float(eta)
        self.beta = float(beta)
        self.speed = float(speed)
        self.density = n / self.Lr

        # Periodic bucket grid: cells of side >= R so an agent's R-neighbours all lie in
        # its own cell or the 2 adjacent ones (with wrap). n_cells>=1 (a small ring falls
        # back to one cell == brute force, still correct).
        self.n_cells = max(1, int(math.floor(self.Lr / self.R)))
        self.cell_size = self.Lr / self.n_cells

        # Random initial state: positions uniform on the ring; headings +/-1 with equal
        # probability. This seeded draw is the ONLY randomness in the initial condition;
        # per-tick heading noise is drawn from the same seeded rng during the run.
        self.agent_list: List[LocustAgent] = []
        for i in range(n):
            x = self.rng.uniform(0.0, self.Lr)
            s = 1 if self.rng.random() < 0.5 else -1
            agent = LocustAgent(i, self, x=x, s=s)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "phi": lambda m: m.order_parameter(),
            "net_sign": lambda m: m.net_sign(),
        })

    # -- metrics --
    def order_parameter(self) -> float:
        """phi = | (1/N) sum_i s_i |, the alignment / marching order, in [0, 1]."""
        if self.n == 0:
            return 0.0
        return abs(sum(a.s for a in self.agent_list)) / self.n

    def net_direction(self) -> int:
        """Signed net heading sum_i s_i (an integer; sign gives the marching direction)."""
        return sum(a.s for a in self.agent_list)

    def net_sign(self) -> int:
        """Sign of the net direction: +1, -1, or 0 (exact tie). Deep in the ordered
        phase this is stable; near the critical density it flips intermittently."""
        net = self.net_direction()
        return 1 if net > 0 else (-1 if net < 0 else 0)

    # -- neighbour lookup (periodic bucket grid) --
    def _cell_of(self, x: float) -> int:
        return int(x / self.cell_size) % self.n_cells

    def _build_cells(self) -> Dict[int, List[LocustAgent]]:
        cells: Dict[int, List[LocustAgent]] = {}
        for a in self.agent_list:
            cells.setdefault(self._cell_of(a.x), []).append(a)
        return cells

    def _local_mean(self, a: LocustAgent, cells: Dict[int, List[LocustAgent]]) -> float:
        """Local average velocity over the neighbours within range R of ``a`` (periodic
        distance <= R), INCLUDING ``a`` itself. Scans a's cell and its 2 neighbours (with
        wrap); cell side >= R guarantees no in-range neighbour is missed. Returns a value
        in [-1, +1]."""
        cx = self._cell_of(a.x)
        nc = self.n_cells
        total = 0
        count = 0
        for dc in (-1, 0, 1):
            bucket = cells.get((cx + dc) % nc)
            if not bucket:
                continue
            for b in bucket:
                if ring_dist(a.x, b.x, self.Lr) <= self.R:
                    total += b.s
                    count += 1
        # ``a`` itself is always in its own cell and at distance 0 <= R, so count >= 1.
        return total / count if count else float(a.s)

    def _local_mean_bruteforce(self, a: LocustAgent) -> float:
        """O(N) reference local mean (all pairs, periodic distance), including ``a``. Used
        only to validate the bucket-grid path in tests; the model uses the bucket grid."""
        total = 0
        count = 0
        for b in self.agent_list:
            if ring_dist(a.x, b.x, self.Lr) <= self.R:
                total += b.s
                count += 1
        return total / count if count else float(a.s)

    # -- Czirok alignment response --
    def response(self, u: float) -> float:
        """The Czirok alignment response G(u) = tanh(beta * u): a smooth monotone push of
        the heading toward the local mean u in [-1, +1]. sign(G(u)) = sign(u), and |G|
        saturates toward 1 as |u| grows, so a strong local consensus resists the additive
        heading noise while a weak one does not."""
        return math.tanh(self.beta * u)

    def _new_heading(self, a: LocustAgent, cells: Dict[int, List[LocustAgent]]) -> int:
        """The Czirok heading update for agent ``a``:
            s' = sign( G(u) + eta * xi ),  u = local mean, xi ~ Uniform(-1/2, +1/2).
        ``sign(0) := +1`` (an exact tie keeps a definite heading rather than freezing)."""
        u = self._local_mean(a, cells)
        drive = self.response(u) + self.eta * (self.rng.random() - 0.5)
        return 1 if drive >= 0.0 else -1

    # -- tick --
    def step(self) -> None:
        """One synchronous Czirok tick.

        (1) From the start-of-tick snapshot, every agent's new heading = sign of its
            alignment response to the local mean plus heading noise (staged in
            ``_next_s`` so all neighbour averages read one consistent snapshot).
        (2) Then every agent commits the new heading and MOVES at fixed speed in that
            direction, wrapping into [0, Lr) (synchronous update)."""
        cells = self._build_cells()
        for a in self.agent_list:
            a._next_s = self._new_heading(a, cells)
        for a in self.agent_list:
            a.s = a._next_s
            a.x = (a.x + self.speed * a.s) % self.Lr
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_steps: int = 4000, *, measure_last: int = 2000) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_steps`` synchronous Czirok ticks; return the run summary.

        ``measure_last`` is the trailing window over which the steady-state order
        parameter phi is averaged (the transient is the leading n_steps - measure_last
        ticks) and over which direction reversals are counted. Returns steady + final phi,
        the number of net-direction sign flips over the measurement window, and the full
        per-tick phi and net-sign series.
        """
        if measure_last <= 0 or measure_last > n_steps + 1:
            raise ValueError(
                f"measure_last must be in [1, n_steps+1] (got {measure_last}, "
                f"n_steps={n_steps})")
        self.reporter.collect(self)              # t=0 baseline
        for _ in range(n_steps):
            self.step()
        phi_series = self.reporter.series("phi")
        sign_series = self.reporter.series("net_sign")
        n_flips = count_sign_flips(sign_series, window=measure_last)
        return {
            "n": self.n,
            "Lr": self.Lr,
            "R": self.R,
            "eta": self.eta,
            "beta": self.beta,
            "speed": self.speed,
            "density": self.density,
            "seed": self.seed_value,
            "n_steps": n_steps,
            "measure_last": measure_last,
            "steady_phi": tail_mean(phi_series, window=measure_last),
            "final_phi": phi_series[-1],
            "n_direction_flips": n_flips,
            "phi_series": phi_series,
            "net_sign_series": sign_series,
        }


# -- summary helpers ----------------------------------------------------------

def tail_mean(series: Sequence[float], *, window: int = 2000) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of a series (or the whole
    series if shorter). Averaging the tail smooths finite-N jitter and discards the
    transient before measurement."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def count_sign_flips(sign_series: Sequence[int], *, window: int = 2000) -> int:
    """Number of NET-DIRECTION reversals in the trailing ``window`` of a net-sign series.

    A flip is a transition from a definite +1 to a definite -1 (or vice-versa) between
    consecutive recorded ticks; exact ties (0) are skipped so they neither create nor mask
    a reversal (the direction is compared against the last non-zero sign). This is the
    empirical Buhl-et-al. switching-rate signal: > 0 near the critical density, ~ 0 deep
    in the ordered phase.
    """
    tail = list(sign_series[-window:]) if len(sign_series) >= window else list(sign_series)
    flips = 0
    last = 0
    for s in tail:
        if s == 0:
            continue
        if last != 0 and s != last:
            flips += 1
        last = s
    return flips


def run_single(n: int = 60, *, Lr: float = 60.0, R: float = 1.0, eta: float = 0.6,
               beta: float = 4.0, speed: float = 0.1, seed: int = 0,
               n_steps: int = 4000, measure_last: int = 2000) -> Dict[str, Any]:
    """One locust run at a given (Lr, seed) and the fixed rule parameters."""
    return LocustModel(n, Lr=Lr, R=R, eta=eta, beta=beta, speed=speed, seed=seed).run(
        n_steps, measure_last=measure_last)


def run_many_seeds(n: int = 60, *, Lr: float = 60.0, R: float = 1.0, eta: float = 0.6,
                   beta: float = 4.0, speed: float = 0.1, n_seeds: int = 5,
                   seed_base: int = 0, n_steps: int = 4000,
                   measure_last: int = 2000) -> Dict[str, Any]:
    """Run ``n_seeds`` locust runs (seed ``seed_base + i``) at fixed parameters and one
    ring length ``Lr`` (=> density N/Lr); summarise the steady order parameter phi and the
    direction-flip count across seeds (mean + spread).

    Returns the per-seed steady phi and flip counts, their mean / std / min / max, the
    total flips over all seeds, and one representative trajectory (first seed) of both the
    phi and net-sign series for plotting/inspection.
    """
    runs = [run_single(n, Lr=Lr, R=R, eta=eta, beta=beta, speed=speed,
                       seed=seed_base + i, n_steps=n_steps, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_phi = [rr["steady_phi"] for rr in runs]
    per_seed_final_phi = [rr["final_phi"] for rr in runs]
    per_seed_flips = [rr["n_direction_flips"] for rr in runs]
    mean_phi = sum(per_seed_phi) / n_seeds
    var_phi = sum((s - mean_phi) ** 2 for s in per_seed_phi) / n_seeds
    return {
        "n": n,
        "Lr": Lr,
        "R": R,
        "eta": eta,
        "beta": beta,
        "speed": speed,
        "density": n / Lr,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "n_steps": n_steps,
        "measure_last": measure_last,
        "per_seed_steady_phi": per_seed_phi,
        "per_seed_final_phi": per_seed_final_phi,
        "per_seed_flips": per_seed_flips,
        "mean_steady_phi": mean_phi,
        "var_steady_phi": var_phi,
        "std_steady_phi": var_phi ** 0.5,
        "min_steady_phi": min(per_seed_phi),
        "max_steady_phi": max(per_seed_phi),
        "total_flips": sum(per_seed_flips),
        "max_flips": max(per_seed_flips),
        "n_seeds_with_flip": sum(1 for f in per_seed_flips if f > 0),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_phi_series": runs[0]["phi_series"],
        "example_net_sign_series": runs[0]["net_sign_series"],
    }


def sweep_density(n: int = 60, *, ring_lengths: Sequence[float] = (600.0, 240.0, 120.0,
                  80.0, 60.0), R: float = 1.0, eta: float = 0.6, beta: float = 4.0,
                  speed: float = 0.1, n_seeds: int = 5, seed_base: int = 0,
                  n_steps: int = 4000, measure_last: int = 2000) -> List[Dict[str, Any]]:
    """Sweep the density N/Lr by varying the ring length ``Lr`` at FIXED N; at each ring
    length run the ``n_seeds``-seed experiment. Returns one summary dict per ring length,
    ordered as ``ring_lengths`` is given (so pass it low-density -> high-density).
    """
    return [run_many_seeds(n, Lr=Lr, R=R, eta=eta, beta=beta, speed=speed,
                           n_seeds=n_seeds, seed_base=seed_base, n_steps=n_steps,
                           measure_last=measure_last)
            for Lr in ring_lengths]
