"""Conway's Game of Life (1970) — a faithful B3/S23 cellular-automaton reproduction.

Source: Gardner, M. (1970) "Mathematical Games: The fantastic combinations of John
Conway's new solitaire game 'life'", Scientific American 223(4):120-123. The rule and
the catalogued pattern behaviours (glider, blinker, block, beacon) are Conway/Gardner's,
locked here BEFORE the run — not tuned.

IMPORTANT (honesty, binds the FINDINGS): this is a DETERMINISTIC CELLULAR AUTOMATON, NOT
an agent-stepping ABM. There are no agents that perceive, decide and act; no scheduler
over an agent roster; no per-agent step. It is a single synchronous transition rule
applied to every cell of a grid at once. We disclose this exactly as the BTW sandpile /
forest-fire reproductions disclose they are cellular automata. The lock-first +
honest-verdict + L3-bundle discipline still fully applies.

The rule (the canonical B3/S23 "Life", verified against Conway/Gardner 1970):
  * An L x L grid of cells, each DEAD (0) or ALIVE (1). The grid is TOROIDAL (periodic /
    wrap-around) so there is no special boundary.
  * Each cell's neighbourhood is the MOORE-8 (the eight cells orthogonally and diagonally
    adjacent), counted with wrap-around.
  * SYNCHRONOUS update — every cell's next state is computed from the CURRENT grid, then
    the whole grid is replaced at once:
        - BIRTH  (B3):  a DEAD cell with exactly 3 live neighbours becomes ALIVE.
        - SURVIVAL (S23): a LIVE cell with 2 or 3 live neighbours stays ALIVE.
        - DEATH: every other cell becomes / stays DEAD (loneliness < 2, overcrowding > 3).

Determinism: there is NO randomness anywhere — given a starting grid, the entire orbit is
fixed. We therefore do NO seeding or averaging; the locked claims are EXACT pattern
periods and the glider's exact net translation, not statistical quantities. NumPy is used
only to make the synchronous neighbour-count fast (a wrap-around 8-neighbour sum); the
result is the bit-for-bit canonical Life outcome.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Cell states.
DEAD = 0
ALIVE = 1


# -- core CA: one synchronous step ------------------------------------------------

def live_neighbour_counts(grid: np.ndarray) -> np.ndarray:
    """Return the Moore-8 live-neighbour count of every cell, with toroidal wrap.

    The count for cell (i, j) is the sum of its eight neighbours on the periodic grid.
    Implemented as the sum of the eight rolled copies of the grid (np.roll wraps the
    edges, giving the toroidal neighbourhood exactly). The cell itself is never counted.
    """
    g = np.asarray(grid, dtype=np.int64)
    total = np.zeros_like(g)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue  # the cell itself is not its own neighbour
            total += np.roll(np.roll(g, di, axis=0), dj, axis=1)
    return total


def step(grid: np.ndarray) -> np.ndarray:
    """Advance the grid one generation under B3/S23 (synchronous, toroidal).

    Returns a NEW (L, L) array of 0/1 ints; the input grid is not mutated. A dead cell
    with exactly 3 live neighbours is born; a live cell with 2 or 3 live neighbours
    survives; every other cell is dead next generation.
    """
    g = np.asarray(grid, dtype=np.int64)
    n = live_neighbour_counts(g)
    alive = g == ALIVE
    # B3: dead cell with exactly 3 neighbours is born.
    born = (~alive) & (n == 3)
    # S23: live cell with 2 or 3 neighbours survives.
    survives = alive & ((n == 2) | (n == 3))
    nxt = np.zeros_like(g)
    nxt[born | survives] = ALIVE
    return nxt


def run(grid: np.ndarray, n: int) -> np.ndarray:
    """Evolve ``grid`` for ``n`` generations under B3/S23 and return the final grid.

    ``n`` must be >= 0; ``run(grid, 0)`` returns a copy of the input grid. The input grid
    is never mutated.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    g = np.asarray(grid, dtype=np.int64).copy()
    for _ in range(n):
        g = step(g)
    return g


def history(grid: np.ndarray, n: int) -> List[np.ndarray]:
    """Return the orbit [G0, G1, ..., Gn] (n+1 grids) of ``grid`` under B3/S23.

    G0 is a copy of the input; G_{k+1} = step(G_k). Used to measure periods and the
    live-cell-count series without re-running step repeatedly.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    g = np.asarray(grid, dtype=np.int64).copy()
    frames = [g.copy()]
    for _ in range(n):
        g = step(g)
        frames.append(g.copy())
    return frames


def live_count(grid: np.ndarray) -> int:
    """Number of live cells in the grid."""
    return int(np.asarray(grid).sum())


# -- canonical seed patterns ------------------------------------------------------

# Each pattern is given as a small list of (row, col) live cells relative to its own
# top-left, exactly as catalogued by Conway/Gardner. ``place_pattern`` stamps it onto a
# blank toroidal grid at a chosen offset (centred by default) so wrap interference is
# avoided on a large grid.

# Glider — a period-4 diagonal spaceship that moves (+1, +1) per period.
GLIDER: List[Tuple[int, int]] = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]

# Blinker — a period-2 oscillator (a horizontal 3-cell row <-> vertical 3-cell column).
BLINKER: List[Tuple[int, int]] = [(1, 0), (1, 1), (1, 2)]

# Block — a 2x2 still life (period 1, unchanged forever).
BLOCK: List[Tuple[int, int]] = [(0, 0), (0, 1), (1, 0), (1, 1)]

# Beacon — a period-2 oscillator (two diagonally-touching blocks).
BEACON: List[Tuple[int, int]] = [(0, 0), (0, 1), (1, 0), (1, 1),
                                 (2, 2), (2, 3), (3, 2), (3, 3)]

PATTERNS: Dict[str, List[Tuple[int, int]]] = {
    "glider": GLIDER,
    "blinker": BLINKER,
    "block": BLOCK,
    "beacon": BEACON,
}


def blank_grid(L: int) -> np.ndarray:
    """An L x L dead grid."""
    if L <= 0:
        raise ValueError("L must be positive")
    return np.zeros((L, L), dtype=np.int64)


def place_pattern(cells: List[Tuple[int, int]], L: int,
                  offset: Optional[Tuple[int, int]] = None) -> np.ndarray:
    """Stamp ``cells`` (a list of (row, col)) onto a blank L x L toroidal grid.

    ``offset`` is the (row, col) of the pattern's local origin on the grid; if None the
    pattern is roughly centred. Coordinates wrap (mod L) so the function never raises on a
    large grid, but the caller is expected to use a grid big enough that the pattern does
    not wrap into itself during the measured run.
    """
    grid = blank_grid(L)
    if offset is None:
        max_r = max(r for r, _ in cells)
        max_c = max(c for _, c in cells)
        offset = ((L - max_r) // 2, (L - max_c) // 2)
    r0, c0 = offset
    for r, c in cells:
        grid[(r0 + r) % L, (c0 + c) % L] = ALIVE
    return grid


# -- pattern analysis: period + net translation ----------------------------------

def _live_coords(grid: np.ndarray) -> np.ndarray:
    """The (k, 2) array of live-cell (row, col) coordinates, sorted."""
    coords = np.argwhere(np.asarray(grid) == ALIVE)
    if coords.size == 0:
        return coords
    order = np.lexsort((coords[:, 1], coords[:, 0]))
    return coords[order]


def _normalized_shape(grid: np.ndarray) -> Tuple[Tuple[int, int], ...]:
    """The pattern's SHAPE as a translation-invariant frozen set of cell offsets.

    Live cells are translated so the minimum row and minimum column are both 0. Two grids
    have the same normalized shape iff one is a pure translation of the other (on the
    infinite plane; on a torus this holds as long as the pattern does not wrap).
    """
    coords = _live_coords(grid)
    if coords.size == 0:
        return tuple()
    coords = coords - coords.min(axis=0)
    return tuple(map(tuple, coords.tolist()))


def _centroid(grid: np.ndarray) -> Tuple[float, float]:
    """The centroid (mean row, mean col) of the live cells (NaN-free; assumes nonempty)."""
    coords = _live_coords(grid)
    return (float(coords[:, 0].mean()), float(coords[:, 1].mean()))


def detect_period(grid: np.ndarray, max_period: int = 64) -> Optional[Dict[str, Any]]:
    """Detect the SHAPE period of ``grid`` and its net per-period translation.

    Evolves the grid and finds the smallest p in [1, max_period] such that generation p
    has the SAME normalized shape as generation 0 (i.e. it is generation 0 possibly
    translated). Returns a dict with:
        * ``period``      — the shape period p (a spaceship returns to its shape at p,
                            translated; an oscillator returns at p with zero translation;
                            a still life has p = 1 with zero translation).
        * ``translation`` — the integer (drow, dcol) net displacement over one period,
                            measured by the live-cell centroid shift (rounded; exact for a
                            rigid translation), reported on the un-wrapped plane.
        * ``live_count``  — live-cell count at generation 0 (conserved across the period
                            for a rigid spaceship / still life; may oscillate for an
                            oscillator).
    Returns None if no period <= max_period is found. Deterministic; no seeding.

    NOTE: this matches the pattern by its translation-invariant shape, so it correctly
    identifies the glider's period as 4 (it returns to a GLIDER shape, shifted) rather
    than reporting a spurious larger value. The grid must be large enough that the pattern
    does not wrap during the first ``max_period`` generations, or the centroid-based
    translation can be corrupted by wrap; the runner sizes the grid accordingly.
    """
    grid = np.asarray(grid, dtype=np.int64)
    base_shape = _normalized_shape(grid)
    if not base_shape:
        return None
    base_centroid = _centroid(grid)
    g = grid.copy()
    for p in range(1, max_period + 1):
        g = step(g)
        if _normalized_shape(g) == base_shape:
            c = _centroid(g)
            drow = int(round(c[0] - base_centroid[0]))
            dcol = int(round(c[1] - base_centroid[1]))
            return {
                "period": p,
                "translation": (drow, dcol),
                "live_count": live_count(grid),
            }
    return None


def live_count_series(grid: np.ndarray, n: int) -> List[int]:
    """The live-cell count at generations 0..n (length n+1). Deterministic."""
    return [live_count(g) for g in history(grid, n)]
