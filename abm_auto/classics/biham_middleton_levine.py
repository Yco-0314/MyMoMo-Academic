"""Biham-Middleton-Levine 2D traffic (1992) — a faithful two-species traffic
cellular-automaton reproduction.

Source: Biham, O., Middleton, A. A., Levine, D. (1992) "Self-organization and a
dynamical transition in traffic-flow models", Phys. Rev. A 46:R6124-R6127.
doi:10.1103/PhysRevA.46.R6124. The rule and the LOCKED claims (a density-driven
free-flow -> gridlock phase transition with a sharp velocity 1->0 step) are the
paper's, pre-registered here BEFORE the run — not tuned.

IMPORTANT (honesty, binds the FINDINGS): this is a DETERMINISTIC-RULE CELLULAR
AUTOMATON, NOT an agent-stepping ABM. There are no agents that perceive, decide
and act; no scheduler over an agent roster; no per-agent step. It is a single
synchronous transition rule applied to a whole grid at once (the only randomness
is the initial placement of cars, driven by one seeded RNG). We disclose this
exactly as the Game of Life / BTW sandpile / forest-fire reproductions disclose
they are cellular automata. The lock-first + honest-verdict + L3-bundle
discipline still fully applies.

The rule (verified against Biham-Middleton-Levine 1992):
  * An L x L grid of cells, each EMPTY (0), a RED car (1) that moves EAST, or a
    BLUE car (2) that moves NORTH. The grid is TOROIDAL (periodic / wrap-around),
    so there is no boundary.
  * Cars alternate colours by tick PARITY. On EVEN ticks every RED car
    simultaneously attempts to move one cell EAST — to ``(x+1) mod L`` in the
    column direction (axis 1). On ODD ticks every BLUE car simultaneously
    attempts to move one cell NORTH — to ``(y-1) mod L`` in the row direction
    (axis 0; "north" = decreasing row index, the convention fixed here).
  * SIMULTANEOUS movement within a colour (classic BML): a car moves iff its
    target cell is EMPTY in the CURRENT configuration, and it stays otherwise.
    Because within one colour on one tick the two colours never share a target
    and same-colour cars all move along the same axis by the same amount, the
    "target empty now" test is collision-free and order-independent — the
    move is a single synchronous permutation of that colour's cars.
  * Density rho = fraction of occupied cells. Equal numbers of red and blue are
    placed uniformly at random (one seeded RNG) to reach rho.

Outcome (the LOCKED observable):
  * mean velocity v = fraction of the ACTIVE colour's cars that actually moved on
    a tick. We average this over BOTH colours (red on even ticks, blue on odd
    ticks) over a measurement window AFTER a warm-up, giving the steady-state
    mean velocity v(rho). At low rho v -> ~1 (free flow); above a critical rho_c
    v -> ~0 (global gridlock); the drop is a sharp near-step phase transition.

Determinism: the only randomness is the seeded initial placement; the update is
a deterministic synchronous rule. Same seed => identical grid evolution
(bit-for-bit). We use several seeds and report seed-averaged v(rho). NumPy is
used only to make the synchronous colour-move fast (a masked wrap-around shift);
the result is the exact BML outcome.

WATCH finite-size metastability: on small grids the transition is smeared by
metastable states, so we use L >= 128, a long warm-up, and average over the
tail. If a transition is genuinely smeared, that is an honest finding — report
it, do not hide it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# Cell states.
EMPTY = 0
RED = 1   # moves EAST (+1 along axis 1, columns), on EVEN ticks
BLUE = 2  # moves NORTH (-1 along axis 0, rows), on ODD ticks


# -- initial placement --------------------------------------------------------

def place_cars(L: int, rho: float, seed: int) -> np.ndarray:
    """Return an ``L x L`` grid with equal red/blue cars placed to density ``rho``.

    ``round(rho * L * L)`` cells are occupied; the occupied cells are split as
    evenly as possible into RED and BLUE (if the count is odd, red gets the extra
    one). Placement is uniform-at-random over the grid, driven by one seeded
    numpy RNG, so the same seed reproduces the same starting grid bit-for-bit.
    """
    if L <= 0:
        raise ValueError(f"L must be positive (got {L})")
    if not (0.0 <= rho <= 1.0):
        raise ValueError(f"rho must be in [0, 1] (got {rho})")
    rng = np.random.default_rng(seed)
    n_cells = L * L
    n_occ = int(round(rho * n_cells))
    n_occ = min(n_occ, n_cells)
    n_red = (n_occ + 1) // 2   # red gets the extra car when n_occ is odd
    n_blue = n_occ - n_red
    grid = np.zeros(n_cells, dtype=np.int8)
    if n_occ > 0:
        cells = rng.choice(n_cells, size=n_occ, replace=False)
        grid[cells[:n_red]] = RED
        grid[cells[n_red:n_red + n_blue]] = BLUE
    return grid.reshape(L, L)


# -- core CA: one colour's synchronous move -----------------------------------

def _move_colour(grid: np.ndarray, colour: int) -> Tuple[np.ndarray, int, int]:
    """Advance every car of ``colour`` one step, returning (new_grid, n_moved, n_cars).

    RED moves EAST — target is the neighbour at ``(x+1) mod L`` along axis 1.
    BLUE moves NORTH — target is the neighbour at ``(y-1) mod L`` along axis 0.
    A car of ``colour`` moves iff its target cell is EMPTY in the CURRENT grid.
    All movers advance simultaneously (a single synchronous permutation): the
    car vacates its old cell and fills the target cell. ``n_moved`` is how many
    of the ``n_cars`` cars actually advanced (the numerator/denominator of the
    active-colour velocity for this tick).
    """
    g = np.asarray(grid)
    is_car = g == colour
    n_cars = int(is_car.sum())
    if colour == RED:
        axis, shift = 1, -1   # roll by -1 brings the +1 neighbour's content back
    elif colour == BLUE:
        axis, shift = 0, +1   # roll by +1 brings the -1 (north) neighbour's content back
    else:
        raise ValueError(f"colour must be RED({RED}) or BLUE({BLUE}), got {colour}")
    # The cell AHEAD of each car (its move target) is empty iff the rolled
    # occupancy is EMPTY at the car's location.
    target_empty = np.roll(g, shift, axis=axis) == EMPTY
    movers = is_car & target_empty          # cars that will advance this tick
    n_moved = int(movers.sum())
    if n_moved == 0:
        return g.copy(), n_moved, n_cars
    # Synchronous update: clear the vacated cells, then fill each target cell.
    # arrivals[t] is True where a mover lands (the target of a mover): roll the
    # movers mask FORWARD by one in the direction of travel.
    arrivals = np.roll(movers, -shift, axis=axis)
    new_g = g.copy()
    new_g[movers] = EMPTY                    # movers leave their old cell
    new_g[arrivals] = colour                 # ... and occupy the cell ahead
    return new_g, n_moved, n_cars


def step(grid: np.ndarray, tick: int) -> Tuple[np.ndarray, int, int, int]:
    """One BML tick: RED moves on EVEN ``tick``, BLUE on ODD ``tick``.

    Returns ``(new_grid, active_colour, n_moved, n_cars)`` where ``active_colour``
    is the colour that moved this tick, ``n_moved`` the number that advanced and
    ``n_cars`` the number of that colour present. The instantaneous active-colour
    velocity is ``n_moved / n_cars`` (1.0 when there are no cars of that colour).
    """
    colour = RED if (tick % 2 == 0) else BLUE
    new_g, n_moved, n_cars = _move_colour(grid, colour)
    return new_g, colour, n_moved, n_cars


# -- model --------------------------------------------------------------------

class BMLModel:
    """The Biham-Middleton-Levine traffic CA on a periodic ``L x L`` grid.

    Construct with grid size ``L``, density ``rho`` and a ``seed`` (the seed drives
    the random initial placement only; the update is deterministic). ``run``
    warms up ``warmup`` ticks, then averages the active-colour velocity over the
    next ``measure`` ticks to get the steady-state mean velocity ``v(rho)``.
    """

    def __init__(self, L: int = 128, rho: float = 0.3, seed: int = 0) -> None:
        if L <= 0:
            raise ValueError(f"L must be positive (got {L})")
        if not (0.0 <= rho <= 1.0):
            raise ValueError(f"rho must be in [0, 1] (got {rho})")
        self.L = L
        self.rho = rho
        self.seed = seed
        self.grid = place_cars(L, rho, seed)
        self.tick = 0

    # -- one tick --
    def step(self) -> float:
        """Advance one tick; return the active colour's velocity (moved/cars).

        Velocity is ``1.0`` when the active colour has no cars this tick (nothing
        can be blocked), so an all-one-colour or empty grid reads as free flow.
        """
        new_g, _colour, n_moved, n_cars = step(self.grid, self.tick)
        self.grid = new_g
        self.tick += 1
        return 1.0 if n_cars == 0 else n_moved / n_cars

    # -- instantaneous state --
    def counts(self) -> Tuple[int, int, int]:
        """(#empty, #red, #blue) on the current grid."""
        g = self.grid
        n_red = int((g == RED).sum())
        n_blue = int((g == BLUE).sum())
        n_empty = g.size - n_red - n_blue
        return n_empty, n_red, n_blue

    @property
    def n_cars(self) -> int:
        """Total number of cars (red + blue) on the grid."""
        _e, r, b = self.counts()
        return r + b

    # -- run --
    def run(self, warmup: int = 4000, measure: int = 2000) -> Dict[str, Any]:
        """Warm up then measure; return the steady-state mean velocity summary.

        The steady-state ``mean_velocity`` is the active-colour velocity averaged
        over the ``measure`` post-warm-up ticks (both colours are sampled because
        the active colour alternates each tick). ``velocity_series`` is the tail
        window's per-tick velocity (for diagnostics). A separate red/blue tail
        mean is reported so a colour asymmetry (should be ~symmetric) is visible.
        """
        if warmup < 0 or measure <= 0:
            raise ValueError("warmup must be >= 0 and measure > 0")
        for _ in range(warmup):
            self.step()
        vels: List[float] = []
        red_vels: List[float] = []
        blue_vels: List[float] = []
        for _ in range(measure):
            active_is_red = (self.tick % 2 == 0)
            v = self.step()
            vels.append(v)
            (red_vels if active_is_red else blue_vels).append(v)
        mean_v = float(np.mean(vels)) if vels else 0.0
        return {
            "L": self.L,
            "rho": self.rho,
            "seed": self.seed,
            "warmup": warmup,
            "measure": measure,
            "mean_velocity": mean_v,
            "red_mean_velocity": float(np.mean(red_vels)) if red_vels else 1.0,
            "blue_mean_velocity": float(np.mean(blue_vels)) if blue_vels else 1.0,
            "velocity_series": [round(float(x), 6) for x in vels[-64:]],
            "n_cars": self.n_cars,
        }


# -- run orchestration --------------------------------------------------------

def run_single(rho: float, *, L: int = 128, seed: int = 0,
               warmup: int = 4000, measure: int = 2000) -> Dict[str, Any]:
    """One BML run at density ``rho`` and a given seed."""
    return BMLModel(L=L, rho=rho, seed=seed).run(warmup=warmup, measure=measure)


def _mean(xs: Sequence[float]) -> float:
    return float(np.mean(xs)) if len(xs) else 0.0


def _std(xs: Sequence[float]) -> float:
    return float(np.std(xs)) if len(xs) else 0.0


def run_many_seeds(rho: float, *, L: int = 128, n_seeds: int = 4, seed_base: int = 0,
                   warmup: int = 4000, measure: int = 2000) -> Dict[str, Any]:
    """Run ``n_seeds`` BML runs (seed ``seed_base + i``) at density ``rho`` and
    summarise the steady-state mean velocity across seeds (mean + spread)."""
    runs = [run_single(rho, L=L, seed=seed_base + i, warmup=warmup, measure=measure)
            for i in range(n_seeds)]
    vels = [r["mean_velocity"] for r in runs]
    return {
        "rho": rho,
        "L": L,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "warmup": warmup,
        "measure": measure,
        "per_seed_velocity": vels,
        "mean_velocity": _mean(vels),
        "std_velocity": _std(vels),
        "min_velocity": min(vels) if vels else 0.0,
        "max_velocity": max(vels) if vels else 0.0,
        "per_seed_red_velocity": [r["red_mean_velocity"] for r in runs],
        "per_seed_blue_velocity": [r["blue_mean_velocity"] for r in runs],
        "example_velocity_series": runs[0]["velocity_series"],
    }


def sweep_density(rhos: Sequence[float], *, L: int = 128, n_seeds: int = 4,
                  seed_base: int = 0, warmup: int = 4000, measure: int = 2000
                  ) -> List[Dict[str, Any]]:
    """Sweep a density grid, returning one ``run_many_seeds`` summary per density
    (sorted by rho)."""
    rows = [run_many_seeds(rho, L=L, n_seeds=n_seeds, seed_base=seed_base,
                           warmup=warmup, measure=measure)
            for rho in rhos]
    rows.sort(key=lambda r: r["rho"])
    return rows


# -- transition analysis ------------------------------------------------------

def _interp_crossing(rows: Sequence[Dict[str, Any]], level: float) -> Optional[float]:
    """Density at which the seed-mean velocity curve crosses ``level`` going DOWN.

    Scans the (rho, mean_velocity) curve in increasing rho and returns the first
    density where velocity drops from >= ``level`` to < ``level``, linearly
    interpolated between the bracketing points. Returns None if the curve never
    crosses (e.g. it stays above or below ``level`` over the whole sweep).
    """
    pts = sorted(((r["rho"], r["mean_velocity"]) for r in rows), key=lambda p: p[0])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if y0 >= level > y1:
            if y0 == y1:
                return x0
            frac = (y0 - level) / (y0 - y1)
            return x0 + frac * (x1 - x0)
    return None


def critical_density(rows: Sequence[Dict[str, Any]]) -> Optional[float]:
    """The transition density rho_c where the mean-velocity curve crosses 0.5."""
    return _interp_crossing(rows, 0.5)


def transition_width(rows: Sequence[Dict[str, Any]], high: float = 0.9,
                     low: float = 0.1) -> Optional[float]:
    """Width of the density interval over which v drops from >= ``high`` to <= ``low``.

    Returns ``rho(v=low) - rho(v=high)`` using the linear crossings of the
    seed-mean curve. A near-step transition gives a small width; a gradual
    (e.g. linear v = 1 - rho) decline gives a large one. Returns None if either
    crossing is absent from the swept range.
    """
    x_high = _interp_crossing(rows, high)
    x_low = _interp_crossing(rows, low)
    if x_high is None or x_low is None:
        return None
    return x_low - x_high
