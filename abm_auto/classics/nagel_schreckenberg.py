"""Nagel-Schreckenberg traffic (Nagel & Schreckenberg 1992) — a faithful
agent-based reproduction.

Source: Nagel, K., Schreckenberg, M. (1992) "A cellular automaton model for
freeway traffic", J. Physique I 2(12):2221-2229. doi:10.1051/jp1:1992277.

Rules (verified against the paper):
  * A single-lane road is a 1D RING (periodic) of ``L`` cells (default 1000).
    Each cell holds at most one car. ``rho * L`` cars are placed; each is a
    ``CarAgent`` carrying an integer position ``x`` in [0, L) and an integer
    velocity ``v`` in [0, vmax] (vmax default 5).
  * Each tick the four NaSch update steps are applied IN PARALLEL — every car's
    NEW velocity is computed from the CURRENT global state (all positions /
    velocities of this tick), and only AFTER all new velocities are computed do
    all cars move. (Parallel / synchronous update is the defining feature of
    NaSch; a sequential update produces a DIFFERENT, less jammy model.)
        1. Accelerate:  v <- min(v + 1, vmax)
        2. Brake:       v <- min(v, gap)   where gap = number of empty cells
                        ahead to the next car (so cars never overlap).
        3. Randomize:   with probability ``p`` (default 0.3),  v <- max(v - 1, 0).
        4. Move:        x <- (x + v) mod L.
  * The randomization step is the only stochasticity; it is what makes jams
    emerge SPONTANEOUSLY (no obstacle) at high density — turn p to 0 and the
    model is deterministic and jam-free above the free-flow branch.

Outcome (the LOCKED metrics):
  * mean velocity  <v>  = average car velocity over all cars and all measured
    ticks (post-transient).
  * flow  q = rho * <v>  = mean number of cars crossing a fixed point per tick
    (the fundamental-diagram observable).
  * stopped fraction = fraction of (car, tick) samples with v == 0 (the jam
    metric).
The "fundamental diagram" is q vs density rho: it rises from 0, peaks at an
INTERIOR critical density (rho_c ~ 0.1 for vmax=5, p=0.3), then falls back to 0
as the road jams.

Determinism / locality: each car reads only the gap to the car ahead (a local
neighbourhood on the ring); the only global coupling is the shared occupancy of
the ring. One seeded RNG chain places the cars and drives every randomization
draw, so a run replays bit-for-bit from a seed. The per-tick randomization draws
are taken in a FIXED car order (by ascending position index) so parallel updates
stay reproducible.

Built on the neutral platform (``abm_auto._platform``): each car is a
``CarAgent``; ``NagelSchreckenbergModel`` drives the ticks over the ``AgentSet``
roster and records (via a ``DataCollector``) the per-tick mean velocity and
stopped fraction so the post-transient observables can be computed.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class CarAgent(Agent):
    """One car on the ring: an integer position ``x`` in [0, L) and an integer
    velocity ``v`` in [0, vmax].

    The NaSch update is parallel, so a single car cannot autonomously ``step``
    (its new velocity depends on the gap to the car ahead, which depends on the
    whole current configuration). The model computes every car's new velocity
    from the frozen current state, then moves them; ``CarAgent.step`` is a no-op.
    """

    def __init__(self, agent_id: int, model: "NagelSchreckenbergModel", *,
                 x: int, v: int = 0) -> None:
        super().__init__(agent_id, model)
        self.x = x
        self.v = v

    def step(self) -> None:  # pragma: no cover - NaSch ticks the whole road at once
        """No-op: the NaSch tick is a synchronous (parallel) update owned by the
        model, not an autonomous per-agent step."""
        return None


# -- Model --------------------------------------------------------------------

class NagelSchreckenbergModel(AgentModel):
    """Drives the Nagel-Schreckenberg model on a ring of ``length`` cells.

    Construct with the ring ``length`` (L), the number of cars ``n_cars`` (or use
    :func:`from_density`), ``vmax``, slowdown probability ``p``, and a seed.
    ``run`` advances ``transient + measure`` ticks, records the per-tick mean
    velocity and stopped fraction, and returns a summary with the post-transient
    mean velocity, flow, and stopped fraction (the LOCKED metrics)."""

    def __init__(self, *, length: int = 1000, n_cars: int = 100, vmax: int = 5,
                 p: float = 0.3, seed: int = 0, transient: int = 500,
                 measure: int = 500) -> None:
        if n_cars < 0:
            raise ValueError(f"n_cars must be >= 0 (got {n_cars})")
        if n_cars > length:
            raise ValueError(
                f"n_cars ({n_cars}) cannot exceed the number of cells ({length})")
        if not (0.0 <= p <= 1.0):
            raise ValueError(f"p must be in [0, 1] (got {p})")
        super().__init__(seed=seed, schedule="sequential")
        self.seed_value = seed
        self.length = length
        self.n_cars = n_cars
        self.vmax = vmax
        self.p = p
        self.transient = transient
        self.measure = measure

        # Place cars at n_cars DISTINCT cells chosen by the seeded RNG, then keep
        # them sorted by position so "the car ahead" is the next index on the ring
        # (one stable ordering for reproducible parallel updates).
        cells = self.rng.sample(range(length), n_cars) if n_cars else []
        cells.sort()
        self.cars: List[CarAgent] = []
        for i, x in enumerate(cells):
            car = CarAgent(i, self, x=x, v=0)
            self.cars.append(car)
            self.add_agent(car)

        self.reporter = DataCollector({
            "mean_velocity": lambda mdl: mdl.mean_velocity(),
            "stopped_fraction": lambda mdl: mdl.stopped_fraction(),
        })

    # -- construction helper --
    @classmethod
    def from_density(cls, rho: float, *, length: int = 1000, vmax: int = 5,
                     p: float = 0.3, seed: int = 0, transient: int = 500,
                     measure: int = 500) -> "NagelSchreckenbergModel":
        """Build a model at density ``rho`` (cars = round(rho * length))."""
        n_cars = round(rho * length)
        return cls(length=length, n_cars=n_cars, vmax=vmax, p=p, seed=seed,
                   transient=transient, measure=measure)

    # -- ring geometry --
    def gap_ahead(self, i: int) -> int:
        """Empty cells between car ``i`` (sorted index) and the next car ahead on
        the ring. With ``self.cars`` kept sorted by position the next car is
        ``(i + 1) % n``; the gap wraps around the ring for the last car."""
        n = len(self.cars)
        if n <= 1:
            return self.length - 1  # a lone car never blocks itself
        nxt = self.cars[(i + 1) % n]
        ahead = (nxt.x - self.cars[i].x) % self.length
        return ahead - 1  # cells strictly between the two cars

    # -- one parallel NaSch tick --
    def step(self) -> None:
        """One synchronous (parallel) NaSch update of the whole road.

        New velocities for ALL cars are computed from the CURRENT (frozen)
        configuration first; only then does every car move. This is the defining
        parallel update — interleaving move with velocity computation would be a
        different (sequential) model."""
        n = len(self.cars)
        new_v: List[int] = [0] * n
        for i, car in enumerate(self.cars):
            # 1. accelerate
            v = min(car.v + 1, self.vmax)
            # 2. brake to the gap ahead (computed from the current config)
            v = min(v, self.gap_ahead(i))
            # 3. randomize: slow down by 1 with probability p
            if v > 0 and self.rng.random() < self.p:
                v = v - 1
            new_v[i] = v
        # 4. move (all cars at once)
        for i, car in enumerate(self.cars):
            car.v = new_v[i]
            car.x = (car.x + car.v) % self.length
        # Re-sort by position so "next index = car ahead" stays valid. Positions
        # stay distinct: a car never moves into an occupied cell (gap braking
        # guarantees v <= gap), so the sort is a pure reordering.
        self.cars.sort(key=lambda c: c.x)

        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    # -- instantaneous metrics --
    def mean_velocity(self) -> float:
        """Mean velocity over all cars at the current tick (0.0 if no cars)."""
        if not self.cars:
            return 0.0
        return sum(c.v for c in self.cars) / len(self.cars)

    def stopped_fraction(self) -> float:
        """Fraction of cars currently stopped (v == 0); 0.0 if no cars."""
        if not self.cars:
            return 0.0
        return sum(1 for c in self.cars if c.v == 0) / len(self.cars)

    @property
    def density(self) -> float:
        """Density rho = n_cars / L."""
        return self.n_cars / self.length

    # -- run --
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Advance ``transient`` then ``measure`` ticks; average the LOCKED
        metrics over the post-transient window and return the run summary."""
        for _ in range(self.transient):
            self.step()
        # Average only over the post-transient measurement window.
        mv: List[float] = []
        sf: List[float] = []
        for _ in range(self.measure):
            self.step()
            mv.append(self.mean_velocity())
            sf.append(self.stopped_fraction())
        mean_v = (sum(mv) / len(mv)) if mv else 0.0
        stopped = (sum(sf) / len(sf)) if sf else 0.0
        rho = self.density
        return {
            "length": self.length,
            "n_cars": self.n_cars,
            "rho": rho,
            "vmax": self.vmax,
            "p": self.p,
            "seed": self.seed_value,
            "transient": self.transient,
            "measure": self.measure,
            "mean_velocity": mean_v,
            "flow": rho * mean_v,
            "stopped_fraction": stopped,
        }


# -- metrics / analytic helpers -----------------------------------------------

def mean(xs: Sequence[float]) -> float:
    """Arithmetic mean of a series (0.0 if empty)."""
    return (sum(xs) / len(xs)) if xs else 0.0


def variance(xs: Sequence[float]) -> float:
    """Population variance Var(x) = E[x^2] - E[x]^2 of a series."""
    k = len(xs)
    if k == 0:
        return 0.0
    m = sum(xs) / k
    return sum((x - m) ** 2 for x in xs) / k


def std(xs: Sequence[float]) -> float:
    """Population standard deviation."""
    return variance(xs) ** 0.5


# -- run orchestration --------------------------------------------------------

def run_single(rho: float, *, length: int = 1000, vmax: int = 5, p: float = 0.3,
               seed: int = 0, transient: int = 500, measure: int = 500
               ) -> Dict[str, Any]:
    """One NaSch run at density ``rho`` and a given seed."""
    return NagelSchreckenbergModel.from_density(
        rho, length=length, vmax=vmax, p=p, seed=seed,
        transient=transient, measure=measure).run()


def run_many_seeds(rho: float, *, length: int = 1000, vmax: int = 5, p: float = 0.3,
                   n_seeds: int = 10, seed_base: int = 0, transient: int = 500,
                   measure: int = 500) -> Dict[str, Any]:
    """Run ``n_seeds`` NaSch runs (seed ``seed_base + i``) at density ``rho`` and
    summarise the LOCKED metrics (flow, mean velocity, stopped fraction) across
    seeds with their mean + spread (min/max/std)."""
    runs = [run_single(rho, length=length, vmax=vmax, p=p, seed=seed_base + i,
                       transient=transient, measure=measure)
            for i in range(n_seeds)]
    flows = [r["flow"] for r in runs]
    vels = [r["mean_velocity"] for r in runs]
    stopped = [r["stopped_fraction"] for r in runs]
    return {
        "rho": rho,
        "length": length,
        "n_cars": runs[0]["n_cars"],
        "vmax": vmax,
        "p": p,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "transient": transient,
        "measure": measure,
        "per_seed_flow": flows,
        "per_seed_mean_velocity": vels,
        "per_seed_stopped_fraction": stopped,
        "mean_flow": mean(flows),
        "std_flow": std(flows),
        "min_flow": min(flows),
        "max_flow": max(flows),
        "mean_velocity": mean(vels),
        "std_velocity": std(vels),
        "mean_stopped_fraction": mean(stopped),
        "std_stopped_fraction": std(stopped),
    }


def sweep_density(rhos: Sequence[float], *, length: int = 1000, vmax: int = 5,
                  p: float = 0.3, n_seeds: int = 10, seed_base: int = 0,
                  transient: int = 500, measure: int = 500
                  ) -> List[Dict[str, Any]]:
    """Sweep a density grid, returning one ``run_many_seeds`` summary per density
    (sorted by rho)."""
    rows = [run_many_seeds(rho, length=length, vmax=vmax, p=p, n_seeds=n_seeds,
                           seed_base=seed_base, transient=transient,
                           measure=measure)
            for rho in rhos]
    rows.sort(key=lambda r: r["rho"])
    return rows


def argmax_flow_density(rows: Sequence[Dict[str, Any]]) -> float:
    """Density rho at which the mean flow is maximal (the fundamental-diagram
    peak)."""
    return max(rows, key=lambda r: r["mean_flow"])["rho"]
