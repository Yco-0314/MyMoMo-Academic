"""Cyclic cellular automaton (Fisch, Gravner & Griffeath 1991) — a faithful reproduction.

Source (verified, not from memory):
  * Fisch, R., Gravner, J. & Griffeath, D. (1991) "Threshold-range scaling of excitable
    cellular automata", Statistics and Computing 1(1):23-39. doi:10.1007/BF01890834.
    (The n-colour cyclic cellular automaton; the spiral-forming / debris-fixating
    dichotomy as the number of colours n varies on the Moore/threshold-1 lattice.)

IMPORTANT (honesty, binds the FINDINGS): this is a DETERMINISTIC (given the seed)
CELLULAR AUTOMATON, NOT an agent-stepping ABM. There are no agents that perceive, decide
and act; no scheduler over an agent roster; no per-agent step. It is a single synchronous
transition rule applied to every cell of the grid at once. We disclose this exactly as the
BTW-sandpile / Game-of-Life reproductions disclose they are cellular automata. The
lock-first + honest-verdict + L3-bundle discipline still fully applies.

The rule (the n-colour cyclic CA, verified against Fisch-Gravner-Griffeath 1991):
  * An L x L grid of cells, each holding one of n COLOURS in {0, 1, ..., n-1}. The grid is
    TOROIDAL (periodic wrap-around) so there is no special boundary.
  * Each cell's neighbourhood is the MOORE-8 (the eight cells orthogonally and diagonally
    adjacent), counted with wrap-around.
  * The colours form a CYCLIC dominance ladder 0 -> 1 -> ... -> n-1 -> 0: colour k is
    "eaten by" (advances toward) colour (k+1) mod n.
  * SYNCHRONOUS update with THRESHOLD 1 — every cell's next colour is computed from the
    CURRENT grid, then the whole grid is replaced at once:
        - A cell in colour k ADVANCES to (k+1) mod n iff at least ONE of its Moore-8
          neighbours currently holds the successor colour (k+1) mod n.
        - Otherwise the cell KEEPS colour k.
    (Threshold 1: a single successor neighbour is enough. No cell ever skips a colour or
    moves backward — advancement is strictly +1 around the cycle.)
  * Random uniform initial colours in {0, ..., n-1}, drawn from one seeded NumPy generator.

Phenomenology (what the locked P1/P2/P3 test):
  * For SMALL n (e.g. n = 8) the field self-organises out of the random soup into
    persistent ROTATING SPIRALS: a nonzero fraction of cells keeps advancing forever, and a
    persistently-active cell cycles back to its own starting colour every n steps.
  * For LARGE n (e.g. n = 16, above the critical colour count for Moore/threshold-1) the
    dynamics FIXATE into frozen "debris": the fraction of cells changing per step decays to
    ~0 as no cell can find its successor colour nearby.

Determinism: a single ``numpy.random.default_rng(seed)`` draws the initial colour field;
the transition rule itself has NO randomness, so the whole orbit is fixed by the seed.
NumPy is used only to make the synchronous 8-neighbour successor test fast (eight rolled
comparisons OR-ed together); the result is the exact cyclic-CA outcome.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

# The eight Moore-neighbour offsets (orthogonal + diagonal), never including (0, 0).
_MOORE: tuple[tuple[int, int], ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
)


def random_grid(L: int, n: int, *, seed: int = 0) -> np.ndarray:
    """An L x L grid of uniform random colours in {0, ..., n-1}, from ``seed``.

    Deterministic given ``seed``: a single ``numpy.random.default_rng(seed)`` draws the
    whole field. Raises on non-positive L or n < 2 (a cyclic CA needs >= 2 colours).
    """
    if L <= 0:
        raise ValueError(f"L must be positive (got {L})")
    if n < 2:
        raise ValueError(f"n (number of colours) must be >= 2 (got {n})")
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(L, L)).astype(np.int64)


def has_successor_neighbour(grid: np.ndarray, n: int) -> np.ndarray:
    """Boolean (L, L) mask: True where at least one Moore-8 neighbour holds the successor
    colour (grid+1) mod n of the focal cell, with toroidal wrap.

    For each of the eight neighbour offsets we roll the grid and test, per cell, whether the
    rolled neighbour equals this cell's own successor colour ``(grid + 1) % n``; the eight
    boolean tests are OR-ed. This is the threshold-1 advancement condition, computed for the
    whole grid at once. The cell itself is never one of its own neighbours.
    """
    g = np.asarray(grid, dtype=np.int64)
    successor = (g + 1) % n
    hit = np.zeros(g.shape, dtype=bool)
    for di, dj in _MOORE:
        neighbour = np.roll(np.roll(g, di, axis=0), dj, axis=1)
        hit |= (neighbour == successor)
    return hit


def step(grid: np.ndarray, n: int) -> np.ndarray:
    """Advance the grid one synchronous cyclic-CA generation (threshold 1, Moore-8, torus).

    Returns a NEW (L, L) array; the input grid is not mutated. A cell in colour k advances
    to (k+1) mod n iff at least one Moore neighbour currently holds (k+1) mod n, otherwise
    it keeps colour k.
    """
    g = np.asarray(grid, dtype=np.int64)
    advance = has_successor_neighbour(g, n)
    nxt = g.copy()
    nxt[advance] = (g[advance] + 1) % n
    return nxt


def run(grid: np.ndarray, n: int, steps: int) -> np.ndarray:
    """Evolve ``grid`` for ``steps`` generations and return the final grid.

    ``steps`` must be >= 0; ``run(grid, n, 0)`` returns a copy. Input never mutated.
    """
    if steps < 0:
        raise ValueError("steps must be non-negative")
    g = np.asarray(grid, dtype=np.int64).copy()
    for _ in range(steps):
        g = step(g, n)
    return g


def change_fraction_series(grid: np.ndarray, n: int, steps: int) -> Dict[str, Any]:
    """Evolve ``grid`` for ``steps`` generations, recording the fraction of cells that
    CHANGE colour at each step (the classic activity order parameter).

    Returns a dict with:
      * ``change_fraction`` — list of length ``steps``; entry t is
        (number of cells whose colour differs between generation t and t+1) / (L*L).
      * ``final_grid``      — the grid after ``steps`` generations.
    The change fraction settles to a nonzero plateau in the spiral phase and decays to ~0 on
    fixation. Deterministic given the input grid.
    """
    if steps < 0:
        raise ValueError("steps must be non-negative")
    g = np.asarray(grid, dtype=np.int64).copy()
    total = g.size
    changes: List[float] = []
    for _ in range(steps):
        nxt = step(g, n)
        changed = int(np.count_nonzero(nxt != g))
        changes.append(changed / total)
        g = nxt
    return {"change_fraction": changes, "final_grid": g}


def colour_history(grid: np.ndarray, n: int, steps: int) -> np.ndarray:
    """Return the full colour orbit as an (steps+1, L, L) int array [G0, G1, ..., G_steps].

    Used by the period analysis (P3): the colour time series of every cell is a column
    through this stack. Deterministic. Memory is (steps+1)*L*L int64 — the runner keeps
    ``steps`` modest for the period window.
    """
    if steps < 0:
        raise ValueError("steps must be non-negative")
    g = np.asarray(grid, dtype=np.int64).copy()
    frames = np.empty((steps + 1,) + g.shape, dtype=np.int64)
    frames[0] = g
    for t in range(1, steps + 1):
        g = step(g, n)
        frames[t] = g
    return frames


def _advances_per_cell(frames: np.ndarray, n: int) -> np.ndarray:
    """Per-cell count of colour ADVANCEMENTS across the window ``frames`` ((T+1, L, L)).

    A cell "advances" at step t iff its colour goes from k to (k+1) mod n between frame t and
    t+1. Since the rule only ever advances +1 (never skips or reverses), the number of
    advances over the window is exactly how many colours the cell moved through — and a cell
    that returns to its start every n steps advances at a steady rate of one colour per step
    on average through a spiral. Returns an (L, L) int array.
    """
    diff = (frames[1:] - frames[:-1]) % n           # (T, L, L): 0 if unchanged, 1 if advanced
    # A genuine advance is exactly a +1 step mod n (the rule guarantees this); count them.
    return np.count_nonzero(diff == 1, axis=0)


def dominant_active_period(grid: np.ndarray, n: int, *, window: int,
                           active_frac: float = 0.75) -> Dict[str, Any]:
    """Measure the dominant colour-return PERIOD at persistently-active cells over ``window``
    generations, for the P3 test (spiral phase: the period should equal n).

    Method (no hand-picked core; a population statistic over all steadily-cycling cells):
      1. Build the colour orbit over ``window`` generations.
      2. A cell is PERSISTENTLY ACTIVE if it advanced on at least ``active_frac * window``
         of the steps (it keeps cycling, not frozen debris).
      3. For each such cell, the colour-return period = (number of steps) / (number of
         colour advances over the window), i.e. how many steps it takes to move forward one
         colour on average. A cell cycling steadily one colour per step has period ~ 1 step
         per colour and returns to its start colour every n such advances — so the RETURN
         period (steps to come back to the same colour) is n * (steps per advance). In the
         clean spiral phase a persistently-active cell advances ~ once per step, giving a
         return period ~ n.

    Returns a dict with the median return period over active cells, the fraction of cells
    that are persistently active, and the active-cell count. NaN period if there are no
    active cells (fixation). Deterministic given the input grid.
    """
    if window <= 0:
        raise ValueError("window must be positive")
    frames = colour_history(grid, n, window)
    advances = _advances_per_cell(frames, n)         # (L, L) advances over the window
    active_mask = advances >= (active_frac * window)
    n_active = int(np.count_nonzero(active_mask))
    total = frames.shape[1] * frames.shape[2]
    active_fraction = n_active / total
    if n_active == 0:
        return {"median_return_period": float("nan"),
                "active_fraction": active_fraction, "n_active": 0,
                "window": window, "active_frac_threshold": active_frac}
    adv = advances[active_mask].astype(np.float64)
    # steps-per-advance for each active cell; the colour-return period is n * that.
    steps_per_advance = window / adv
    return_period = n * steps_per_advance
    return {
        "median_return_period": float(np.median(return_period)),
        "mean_return_period": float(np.mean(return_period)),
        "median_steps_per_advance": float(np.median(steps_per_advance)),
        "active_fraction": active_fraction, "n_active": n_active,
        "window": window, "active_frac_threshold": active_frac,
    }


# =============================================================================
# run summaries (used by tests + the runner)
# =============================================================================

def run_single(*, L: int = 256, n: int = 8, steps: int = 400, seed: int = 0,
               tail_frac: float = 0.25, period_window: int = 40,
               period_active_frac: float = 0.75) -> Dict[str, Any]:
    """One cyclic-CA run at (L, n, seed): evolve ``steps`` generations, then measure the
    change-fraction plateau (tail-mean activity) and, in a following window, the dominant
    colour-return period at persistently-active cells.

    Returns:
      * ``change_fraction`` — the full per-step change-fraction series (length ``steps``).
      * ``tail_mean_change`` — mean change fraction over the last ``tail_frac`` of the run
        (the plateau estimate; nonzero in the spiral phase, ~0 on fixation).
      * ``final_change`` — the change fraction on the very last step.
      * ``tail_is_nonzero_stable`` — True iff the tail-mean is not decaying to 0
        (last-quarter mean >= 0.5 * first-tail mean AND both above a small floor).
      * period metrics from ``dominant_active_period`` over ``period_window`` further steps
        starting from the final grid.
    Deterministic given the seed.
    """
    grid0 = random_grid(L, n, seed=seed)
    series = change_fraction_series(grid0, n, steps)
    changes = series["change_fraction"]
    final_grid = series["final_grid"]

    tail_len = max(1, int(round(tail_frac * steps)))
    tail = changes[-tail_len:]
    tail_mean = float(np.mean(tail)) if tail else float("nan")
    # split the run in halves to check the activity is NOT still decaying at the end.
    half = max(1, len(changes) // 2)
    first_half_mean = float(np.mean(changes[:half])) if changes else float("nan")
    second_half_mean = float(np.mean(changes[half:])) if changes else float("nan")

    period = dominant_active_period(final_grid, n, window=period_window,
                                    active_frac=period_active_frac)

    return {
        "L": L, "n": n, "steps": steps, "seed": seed, "tail_frac": tail_frac,
        "change_fraction": changes,
        "tail_mean_change": tail_mean,
        "final_change": float(changes[-1]) if changes else float("nan"),
        "first_half_mean_change": first_half_mean,
        "second_half_mean_change": second_half_mean,
        "median_return_period": period["median_return_period"],
        "mean_return_period": period.get("mean_return_period", float("nan")),
        "median_steps_per_advance": period.get("median_steps_per_advance", float("nan")),
        "active_fraction": period["active_fraction"],
        "n_active": period["n_active"],
        "period_window": period_window,
        "period_active_frac": period_active_frac,
    }


def run_many_seeds(*, L: int = 256, n: int = 8, steps: int = 400, n_seeds: int = 2,
                   seed_base: int = 0, tail_frac: float = 0.25, period_window: int = 40,
                   period_active_frac: float = 0.75) -> Dict[str, Any]:
    """Run ``n_seeds`` independent cyclic-CA runs at fixed (L, n) and aggregate the plateau
    activity + colour-return period across seeds. Each trial uses ``seed_base + i``.

    Aggregates: per-seed tail-mean change fraction (plateau), the mean/min over seeds; the
    per-seed final-step change; and the per-seed median colour-return period + its mean over
    seeds (period metrics are only meaningful where cells stay active). Deterministic.
    """
    if n_seeds <= 0:
        raise ValueError(f"need n_seeds > 0 (got {n_seeds})")
    runs = [run_single(L=L, n=n, steps=steps, seed=seed_base + i, tail_frac=tail_frac,
                       period_window=period_window, period_active_frac=period_active_frac)
            for i in range(n_seeds)]
    tail_means = [r["tail_mean_change"] for r in runs]
    finals = [r["final_change"] for r in runs]
    periods = [r["median_return_period"] for r in runs]
    active_fracs = [r["active_fraction"] for r in runs]
    valid_periods = [p for p in periods if p == p]        # drop NaN (fixated) periods

    return {
        "L": L, "n": n, "steps": steps, "n_seeds": n_seeds, "seed_base": seed_base,
        "tail_frac": tail_frac, "period_window": period_window,
        "period_active_frac": period_active_frac,
        "per_seed_tail_mean_change": tail_means,
        "per_seed_final_change": finals,
        "per_seed_median_return_period": periods,
        "per_seed_active_fraction": active_fracs,
        "mean_tail_change": float(np.mean(tail_means)),
        "min_tail_change": float(np.min(tail_means)),
        "max_tail_change": float(np.max(tail_means)),
        "mean_final_change": float(np.mean(finals)),
        "max_final_change": float(np.max(finals)),
        "mean_active_fraction": float(np.mean(active_fracs)),
        "median_return_period_over_seeds": (
            float(np.median(valid_periods)) if valid_periods else float("nan")),
        "mean_return_period_over_seeds": (
            float(np.mean(valid_periods)) if valid_periods else float("nan")),
        "n_seeds_with_active_cells": len(valid_periods),
        "per_seed": [
            {"seed": r["seed"], "tail_mean_change": r["tail_mean_change"],
             "final_change": r["final_change"],
             "first_half_mean_change": r["first_half_mean_change"],
             "second_half_mean_change": r["second_half_mean_change"],
             "median_return_period": r["median_return_period"],
             "median_steps_per_advance": r["median_steps_per_advance"],
             "active_fraction": r["active_fraction"], "n_active": r["n_active"]}
            for r in runs
        ],
        "per_seed_change_series": [
            {"seed": r["seed"], "change_fraction": r["change_fraction"]} for r in runs
        ],
    }
