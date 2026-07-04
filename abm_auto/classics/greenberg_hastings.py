"""Greenberg-Hastings excitable-media model (1978) — a faithful cellular-automaton
reproduction.

Source: Greenberg, J. M. & Hastings, S. P. (1978) "Spatial patterns for discrete models
of diffusion in excitable media", SIAM Journal on Applied Mathematics 34(3):515-523.
doi:10.1137/0134040.

IMPORTANT (honesty, binds the FINDINGS): this is a DETERMINISTIC CELLULAR AUTOMATON, NOT
an agent-stepping ABM. There are no agents that perceive, decide and act; no scheduler over
an agent roster; no per-agent step. It is a single synchronous transition rule applied to
every cell of a 2D grid at once. We disclose this exactly as the game_of_life / forest_fire
/ turing_pattern reproductions disclose they are cellular / grid-PDE models. The lock-first
+ honest-verdict + L3-bundle discipline still applies in full.

The model (the canonical 3-state Greenberg-Hastings excitable CA, verified against the
paper). Every cell is in one of ``r + 2`` states, encoded as an integer in ``0 .. r+1``:

    * 0                = QUIESCENT (rest / excitable),
    * 1                = EXCITED (firing),
    * 2, 3, ..., r+1   = the ``r`` REFRACTORY states (a deterministic countdown back to rest).

The cycle length is therefore ``T = 1 (excited) + r (refractory) = 1 + r`` steps: once a
cell fires it must march excited -> refractory_1 -> ... -> refractory_r -> quiescent before
it can fire again. ``r`` (the refractory length) is a parameter; the default is ``r = 4``
(so T = 5).

SYNCHRONOUS update (every cell's next state computed from the CURRENT grid, then the whole
grid replaced at once), von-Neumann (4-)neighbourhood:

    * QUIESCENT (0)      -> EXCITED (1)  iff >= 1 von-Neumann neighbour is EXCITED;
                            else stays QUIESCENT (0).
    * EXCITED (1)        -> first refractory state (2).
    * REFRACTORY k       -> k + 1  (counts DOWN toward rest; here the encoding counts the
                            state index UP), and the LAST refractory (r+1) -> QUIESCENT (0).

Only the EXCITED state (1) excites neighbours; refractory cells do NOT. A refractory tail
therefore acts as a one-way "wall" that a wavefront cannot back-propagate through, which is
exactly what makes a broken wavefront curl into a persistent rotating SPIRAL and what makes
two head-on wavefronts ANNIHILATE when they meet (each runs into the other's fresh
refractory tail and dies).

Boundary: TOROIDAL (periodic / wrap-around) by default, so a spiral is not killed by the
domain edge during measurement; a NON-wrapping (open) grid is also supported for the
critical-size sweep P3 (a wave that reaches an open edge simply leaves).

Determinism: the update is a pure function of the grid — there is NO randomness in the
dynamics. The only randomness anywhere is in seeding an initial condition (none of the ICs
used here actually need it, but any placement jitter is seeded), so a given initial grid
evolves bit-for-bit identically every run. NumPy is used only to make the synchronous
neighbour test fast (a wrap-around OR of the four shifted excited-masks); the result is the
canonical Greenberg-Hastings outcome.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Cell states (the refractory states are 2 .. r+1).
QUIESCENT = 0
EXCITED = 1
# The first refractory state; the last is r + 1.
FIRST_REFRACTORY = 2


# -- core CA: one synchronous step --------------------------------------------

def excited_neighbour(grid: np.ndarray, *, wrap: bool = True) -> np.ndarray:
    """Boolean (L, L): cell has >= 1 EXCITED von-Neumann (4-)neighbour.

    Implemented as the OR of the four shifted EXCITED-masks. With ``wrap=True`` the shifts
    are toroidal (``np.roll``); with ``wrap=False`` the boundary is open (cells off the grid
    are treated as non-excited, so a wave that reaches the edge simply leaves).
    """
    excited = np.asarray(grid) == EXCITED
    nb = np.zeros_like(excited)
    if wrap:
        nb |= np.roll(excited, 1, axis=0)
        nb |= np.roll(excited, -1, axis=0)
        nb |= np.roll(excited, 1, axis=1)
        nb |= np.roll(excited, -1, axis=1)
    else:
        nb[1:, :] |= excited[:-1, :]    # neighbour above is excited
        nb[:-1, :] |= excited[1:, :]    # below
        nb[:, 1:] |= excited[:, :-1]    # left
        nb[:, :-1] |= excited[:, 1:]    # right
    return nb


def step(grid: np.ndarray, *, r: int = 4, wrap: bool = True) -> np.ndarray:
    """Advance the grid one synchronous Greenberg-Hastings tick.

    States are integers in ``0 .. r+1`` (0 quiescent, 1 excited, 2..r+1 the r refractory
    states). Returns a NEW array; the input grid is not mutated.

        quiescent (0) -> excited (1)  iff a von-Neumann neighbour is excited, else 0;
        excited (1)   -> 2 (first refractory);
        refractory k (2..r+1) -> k+1, and the last refractory (r+1) -> 0 (quiescent).
    """
    if r < 1:
        raise ValueError("r (refractory length) must be >= 1")
    g = np.asarray(grid)
    last_ref = r + 1
    if int(g.max(initial=0)) > last_ref or int(g.min(initial=0)) < 0:
        raise ValueError(f"grid has states outside 0..{last_ref} for r={r}")

    nxt = np.zeros_like(g)

    quiescent = g == QUIESCENT
    excited = g == EXCITED
    refractory = g >= FIRST_REFRACTORY

    # quiescent -> excited iff an excited neighbour, else stays quiescent (0, already set).
    nb = excited_neighbour(g, wrap=wrap)
    nxt[quiescent & nb] = EXCITED

    # excited -> first refractory.
    nxt[excited] = FIRST_REFRACTORY

    # refractory k -> k+1 ; the last refractory (r+1) wraps to quiescent (0, already set).
    counting = refractory & (g < last_ref)
    nxt[counting] = g[counting] + 1
    # cells at last_ref fall to 0 (already zero in nxt).

    return nxt


def run(grid: np.ndarray, n: int, *, r: int = 4, wrap: bool = True) -> np.ndarray:
    """Evolve ``grid`` for ``n`` synchronous ticks and return the final grid."""
    if n < 0:
        raise ValueError("n must be non-negative")
    g = np.asarray(grid).copy()
    for _ in range(n):
        g = step(g, r=r, wrap=wrap)
    return g


def excited_count(grid: np.ndarray) -> int:
    """Number of EXCITED cells (the global activity observable)."""
    return int(np.sum(np.asarray(grid) == EXCITED))


def active_count(grid: np.ndarray) -> int:
    """Number of NON-quiescent cells (excited + refractory) — 'activity' for die/persist."""
    return int(np.sum(np.asarray(grid) != QUIESCENT))


def excited_series(grid: np.ndarray, n: int, *, r: int = 4,
                   wrap: bool = True) -> List[int]:
    """The excited-cell count at ticks 0..n (length n+1). Deterministic."""
    g = np.asarray(grid).copy()
    series = [excited_count(g)]
    for _ in range(n):
        g = step(g, r=r, wrap=wrap)
        series.append(excited_count(g))
    return series


# -- initial conditions -------------------------------------------------------

def blank_grid(L: int) -> np.ndarray:
    """An L x L all-quiescent grid."""
    if L <= 0:
        raise ValueError("L must be positive")
    return np.zeros((L, L), dtype=np.int64)


def broken_wavefront(L: int, *, r: int = 4,
                     row: Optional[int] = None,
                     col: Optional[int] = None) -> np.ndarray:
    """Seed a BROKEN WAVEFRONT that nucleates a single rotating spiral.

    The canonical spiral IC: a straight EXCITED wavefront with a fresh REFRACTORY tail
    behind it (so the front can only advance one way), and the whole front is CUT at a free
    end. A wavefront's exposed free end has no refractory wall wrapping around it, so it
    curls around that tip and winds up into a one-armed rotating spiral.

    Concretely, on the upper-left quadrant (row < ``row``, col < ``col``):
        * the column just left of ``col`` is EXCITED (the wavefront), and
        * the columns further left are the refractory tail 2, 3, ..., r+1 (freshest next to
          the front), so the front cannot back-propagate.
    The construction is restricted to rows above ``row`` (a half-plane), so the wavefront
    has a FREE END at ``row`` — that free end is the cut that seeds the rotation. Everything
    else is quiescent. Default ``row = L//2``, ``col = L//2`` (the cut sits near the centre
    so the spiral has room to wind on a torus).

    Deterministic (no randomness). Faithful to Greenberg & Hastings' broken-front spiral
    initiation (a half-plane of excitation adjacent to a refractory half-plane, cut at one
    end).
    """
    if L <= 0:
        raise ValueError("L must be positive")
    if r < 1:
        raise ValueError("r must be >= 1")
    g = blank_grid(L)
    row = L // 2 if row is None else row
    col = L // 2 if col is None else col
    # EXCITED wavefront: one column, only in the upper half-plane (rows [0, row)).
    ex_col = col
    if 0 <= ex_col < L:
        g[0:row, ex_col] = EXCITED
    # Refractory tail to the LEFT of the front (states 2..r+1, freshest next to the front).
    for k in range(1, r + 1):
        c = col - k
        if 0 <= c < L:
            g[0:row, c] = FIRST_REFRACTORY + (k - 1)
    return g


def planar_wave(L: int, col: int, *, r: int = 4, direction: int = +1) -> np.ndarray:
    """A single PLANAR (straight) excited wavefront spanning all rows at column ``col``,
    with its refractory tail placed so the front travels in ``direction`` (+1 = to the
    right / increasing column, -1 = to the left).

    The excited column is at ``col``; the refractory tail (states 2..r+1, freshest next to
    the front) is on the *trailing* side, so the only quiescent cells the front can excite
    next tick are on the *leading* side. This yields a clean one-way planar wave. Returned
    grid is otherwise quiescent (compose two with ``np.maximum`` / by writing into one grid
    to launch a head-on collision).
    """
    if not (0 <= col < L):
        raise ValueError("col out of range")
    g = blank_grid(L)
    g[:, col] = EXCITED
    for k in range(1, r + 1):
        c = col - direction * k                 # tail is on the trailing side
        if 0 <= c < L:
            g[:, c] = FIRST_REFRACTORY + (k - 1)
    return g


def head_on_fronts(L: int, *, r: int = 4, gap: Optional[int] = None) -> np.ndarray:
    """Two PLANAR excited wavefronts launched HEAD-ON (approaching each other).

    A right-moving front is placed in the left third and a left-moving front in the right
    third, separated by ``gap`` quiescent columns, so they travel toward the centre and
    collide there. Each front carries its own refractory tail on its trailing side (built by
    ``planar_wave``). Returned grid: the two fronts stamped onto one quiescent grid.

    The collision LINE is the centre column ``L // 2``. On collision each front runs into the
    fresh refractory tail the other front leaves behind, so both annihilate with no
    transmitted front (the Greenberg-Hastings wave-annihilation property).
    """
    if L < 6:
        raise ValueError("L too small for two separated fronts")
    gap = max(2, L // 3) if gap is None else gap
    centre = L // 2
    left_col = centre - gap // 2                 # right-moving front, left of centre
    right_col = centre + gap // 2                # left-moving front, right of centre
    left = planar_wave(L, left_col, r=r, direction=+1)
    right = planar_wave(L, right_col, r=r, direction=-1)
    # The two fronts occupy disjoint column bands; combine by taking the non-quiescent max.
    g = np.where(right != QUIESCENT, right, left)
    return g


# -- period measurement (P1) --------------------------------------------------

def dominant_period(series: List[int], *, max_period: int = 64,
                    warmup_frac: float = 0.5,
                    min_corr: float = 0.5) -> Optional[int]:
    """Estimate the dominant period of a global activity time-series by AUTOCORRELATION.

    Drops the first ``warmup_frac`` of the series (the transient during which the spiral is
    still forming and its excited count grows), LINEARLY DETRENDS the remainder (the slow
    growth ramp would otherwise swamp the periodic component and alias the autocorrelation),
    and returns the lag ``p`` in ``[2, max_period]`` that maximises the normalised
    autocorrelation AND is a local peak (higher than lag p-1 and p+1) with correlation above
    ``min_corr`` — i.e. the fundamental period of the periodic activity. Returns None if the
    series is too short or has no periodic structure (e.g. activity died to a constant).
    """
    x = np.asarray(series, dtype=np.float64)
    n0 = int(len(x) * warmup_frac)
    x = x[n0:]
    if x.size < 2 * max_period + 2:
        return None
    # linear detrend: remove the slow growth ramp so the periodic component dominates.
    t = np.arange(x.size, dtype=np.float64)
    A = np.vstack([t, np.ones_like(t)]).T
    coef, *_ = np.linalg.lstsq(A, x, rcond=None)
    x = x - A @ coef
    denom = float(np.dot(x, x))
    if denom <= 0:
        return None                              # constant series: no period
    ac = np.empty(max_period + 2)
    for lag in range(1, max_period + 2):
        ac[lag - 1] = float(np.dot(x[:-lag], x[lag:])) / denom
    # find the lag with the largest autocorrelation that is also a local peak > min_corr.
    best_p, best_v = None, min_corr
    for p in range(2, max_period + 1):
        v = ac[p - 1]
        if v > best_v and v > ac[p - 2] and v > ac[p]:
            best_v, best_p = v, p
    return best_p


def probe_period(grid0: np.ndarray, n_steps: int, *, r: int = 4, wrap: bool = True,
                 probe: Optional[Tuple[int, int]] = None,
                 warmup_frac: float = 0.5) -> Optional[int]:
    """Directly measure the spiral ROTATION period from one probe cell's excitation
    intervals.

    Evolves ``grid0`` for ``n_steps`` and records the ticks at which the probe cell is
    EXCITED (state 1). Once the spiral is established the probe fires periodically; the
    common inter-excitation gap (the mode of the differences, over the post-warmup ticks) is
    the local rotation period — the number of ticks between successive passes of the spiral
    arm over that cell. Returns None if the probe never settles into a regular rhythm.

    This is a far more robust period estimator than the global-count autocorrelation (it is
    immune to the growth ramp), and it measures exactly the quantity of interest: how often
    a fixed point in the medium is re-excited by the rotating spiral.
    """
    L = grid0.shape[0]
    if probe is None:
        probe = (L // 2 + max(4, L // 8), L // 2 + max(4, L // 8))
    pr, pc = probe[0] % L, probe[1] % L
    g = np.asarray(grid0).copy()
    exc_ticks: List[int] = []
    for t in range(n_steps + 1):
        if g[pr, pc] == EXCITED:
            exc_ticks.append(t)
        if t == n_steps:
            break
        g = step(g, r=r, wrap=wrap)
    n0 = int(len(exc_ticks) * warmup_frac)
    tail = exc_ticks[n0:]
    if len(tail) < 3:
        return None
    diffs = np.diff(tail)
    vals, counts = np.unique(diffs, return_counts=True)
    return int(vals[int(np.argmax(counts))])


def _gap_stability(grid0: np.ndarray, n_steps: int, *, r: int, wrap: bool,
                   probe: Tuple[int, int], warmup_frac: float) -> Dict[str, Any]:
    """Return the probe cell's excitation-gap statistics over the post-warmup window:
    the modal gap (rotation period), min/max gap, and how many of the last gaps equal the
    mode (used to assert the rhythm is stable to +-1 over >= n_rot rotations)."""
    L = grid0.shape[0]
    pr, pc = probe[0] % L, probe[1] % L
    g = np.asarray(grid0).copy()
    exc_ticks: List[int] = []
    for t in range(n_steps + 1):
        if g[pr, pc] == EXCITED:
            exc_ticks.append(t)
        if t == n_steps:
            break
        g = step(g, r=r, wrap=wrap)
    n0 = int(len(exc_ticks) * warmup_frac)
    tail = exc_ticks[n0:]
    if len(tail) < 3:
        return {"period": None, "n_gaps": 0, "min_gap": None, "max_gap": None,
                "n_within_1": 0}
    diffs = np.diff(tail)
    vals, counts = np.unique(diffs, return_counts=True)
    mode = int(vals[int(np.argmax(counts))])
    n_within_1 = int(np.sum(np.abs(diffs - mode) <= 1))
    return {"period": mode, "n_gaps": int(diffs.size),
            "min_gap": int(diffs.min()), "max_gap": int(diffs.max()),
            "n_within_1": n_within_1}


def measure_spiral(L: int = 220, *, r: int = 4, n_steps: int = 500,
                   warmup_frac: float = 0.5,
                   row: Optional[int] = None,
                   col: Optional[int] = None) -> Dict[str, Any]:
    """P1 experiment: seed a broken wavefront on an L x L TORUS, run ``n_steps`` ticks,
    measure the spiral's rotation period and confirm the spiral persists.

    The rotation period is measured TWO independent ways: (a) the modal excitation gap at a
    fixed probe cell away from the core (the direct rotation period; robust to the growth
    ramp), and (b) the linearly-detrended autocorrelation of the GLOBAL excited-cell count.
    Both are reported; the probe period is primary. ``matches_T`` tests the probe period
    against the cycle length ``T = 1+r`` with +-1 tolerance. Also reports whether the rhythm
    is stable to +-1 over >= 20 rotations and whether activity never died. Deterministic.
    """
    T = 1 + r
    g0 = broken_wavefront(L, r=r, row=row, col=col)
    series = excited_series(g0, n_steps, r=r, wrap=True)
    probe = (L // 2 + max(6, L // 8), L // 2 + max(6, L // 8))

    global_period = dominant_period(series, max_period=min(40, n_steps // 6),
                                    warmup_frac=warmup_frac)
    gap = _gap_stability(g0, n_steps, r=r, wrap=True, probe=probe,
                         warmup_frac=warmup_frac)
    period = gap["period"]

    # persistence: excited count in the whole measured run is always > 0 (activity alive).
    alive_whole_run = min(series[1:]) > 0 if len(series) > 1 else False
    min_excited_tail = int(min(series[int(len(series) * warmup_frac):] or [0]))

    matches_T = (period is not None) and (abs(period - T) <= 1)
    # number of rotations covered = number of stable gaps at the probe.
    n_rotations = gap["n_within_1"]
    stable_20 = (period is not None) and (n_rotations >= 20) and \
        (gap["max_gap"] is not None and abs(gap["max_gap"] - period) <= 1
         and abs(gap["min_gap"] - period) <= 1)

    return {
        "L": L, "r": r, "T": T, "n_steps": n_steps, "warmup_frac": warmup_frac,
        "series": series,
        "period": period,
        "global_count_period": global_period,
        "probe": [int(probe[0]), int(probe[1])],
        "gap_min": gap["min_gap"], "gap_max": gap["max_gap"], "gap_count": gap["n_gaps"],
        "matches_T": bool(matches_T),
        "stable_over_20_rotations": bool(stable_20),
        "alive_whole_run": bool(alive_whole_run),
        "min_excited_in_tail": min_excited_tail,
        "n_rotations": int(n_rotations),
        "final_excited": int(series[-1]),
    }


# -- collision / annihilation (P2) --------------------------------------------

def measure_collision(L: int = 80, *, r: int = 4, gap: Optional[int] = None,
                      n_steps: Optional[int] = None,
                      band: int = 3) -> Dict[str, Any]:
    """P2 experiment: launch two planar fronts HEAD-ON on an L x L OPEN (non-wrapping)
    grid, run until well after they meet, and check they ANNIHILATE with no transmitted
    front past the collision line.

    Metrics (all locked-clause quantities):
      * ``collision_col`` — the centre column L//2 (the collision line).
      * ``max_excited_in_band_after`` — the max excited-cell count in a +-``band`` column
        strip around the collision line, measured AFTER the fronts meet; annihilation
        requires this to fall back to 0 within one refractory period (T steps) of the meet.
      * ``transmitted`` — whether ANY excited cell ever appears strictly PAST the collision
        line on the far side of each front after the collision (a pass-through wave). For an
        annihilating collision this stays False.
      * ``met_step`` — the tick at which excited cells first touch the collision band.

    Open boundary is used so that, absent annihilation, a transmitted front would keep
    travelling to (and off) the far edge — making pass-through unmistakable. Deterministic.
    """
    T = 1 + r
    gap = max(2, L // 3) if gap is None else gap
    centre = L // 2
    if n_steps is None:
        # long enough for the fronts to meet (~gap/2 steps) plus a couple of cycles.
        n_steps = gap // 2 + 4 * T + 6
    g = head_on_fronts(L, r=r, gap=gap)

    lo, hi = centre - band, centre + band + 1
    met_step = None
    max_band_after = 0
    transmitted = False
    # columns strictly "past" the collision line, split by side, to detect a pass-through:
    # a wave that started on the left (moving right) transmits if excited appears at cols
    # > centre+band late; symmetric for the right front.
    band_series: List[int] = []
    for t in range(n_steps + 1):
        excited = (g == EXCITED)
        band_excited = int(excited[:, lo:hi].sum())
        band_series.append(band_excited)
        if met_step is None and band_excited > 0:
            met_step = t
        if met_step is not None and t > met_step:
            max_band_after = max(max_band_after, band_excited)
            # transmitted: excited strictly beyond the band on either far side.
            far_right = int(excited[:, hi:].sum())
            far_left = int(excited[:, :lo].sum())
            # after collision, any residual excited cells are the fronts still approaching
            # OR a genuine pass-through; a pass-through would be a coherent front that keeps
            # advancing. We flag transmission only if excited cells persist far from centre
            # AFTER the band has gone quiet (the fronts should have consumed each other).
            if band_excited == 0 and (far_right > 0 or far_left > 0) and t > (met_step + T):
                transmitted = True
        if t == n_steps:
            break
        g = step(g, r=r, wrap=False)

    # annihilation: after the meet, the band returns to 0 within one refractory period T
    # and stays 0 through the end of the run.
    annihilated_in_band = False
    zero_after_step = None
    if met_step is not None:
        # find the first step > met_step where the band is 0 and stays 0.
        for t in range(met_step + 1, len(band_series)):
            if all(v == 0 for v in band_series[t:]):
                zero_after_step = t
                break
        if zero_after_step is not None:
            annihilated_in_band = (zero_after_step - met_step) <= (T + 1)

    final_excited_total = excited_count(g)
    return {
        "L": L, "r": r, "T": T, "gap": gap, "n_steps": n_steps, "band": band,
        "collision_col": centre,
        "met_step": met_step,
        "zero_after_step": zero_after_step,
        "steps_to_quiet_after_meet": (None if zero_after_step is None or met_step is None
                                      else zero_after_step - met_step),
        "annihilated_in_band": bool(annihilated_in_band),
        "transmitted": bool(transmitted),
        "no_pass_through": bool(not transmitted),
        "final_excited_total": final_excited_total,
        "band_series": band_series,
    }


# -- critical domain size (P3) ------------------------------------------------

def survives_on_size(L: int, *, r: int, n_cycles: int = 120,
                     wrap: bool = True) -> Dict[str, Any]:
    """Seed a broken-wavefront spiral on an L x L grid and report whether activity SURVIVES.

    Runs ``n_cycles * T`` ticks. Returns whether activity was still alive at the end
    (``survived``), the tick at which activity first died (``died_at`` cycles, or None), and
    the excited-count series (subsampled). A small torus starves the spiral (the winding arm
    collides with its own refractory tail and the whole pattern extinguishes within a few
    cycles); a large-enough torus lets the spiral rotate indefinitely.
    """
    T = 1 + r
    n_steps = n_cycles * T
    g = broken_wavefront(L, r=r)
    alive_series = [excited_count(g)]
    died_at = None
    for t in range(1, n_steps + 1):
        g = step(g, r=r, wrap=wrap)
        e = excited_count(g)
        alive_series.append(e)
        if e == 0 and died_at is None:
            died_at = t
            break
    survived = alive_series[-1] > 0 and died_at is None
    died_cycles = (died_at / T) if died_at is not None else None
    return {
        "L": L, "r": r, "T": T, "n_cycles": n_cycles,
        "survived": bool(survived),
        "died_at_step": died_at,
        "died_at_cycles": died_cycles,
        "final_excited": int(alive_series[-1]),
        "n_steps_run": len(alive_series) - 1,
    }


def critical_size(r: int, *, sizes: Optional[List[int]] = None,
                  die_below_cycles: float = 5.0,
                  persist_cycles: int = 100,
                  measure_cycles: int = 120,
                  wrap: bool = True) -> Dict[str, Any]:
    """Find the critical linear domain size ``L_c`` for a refractory length ``r``.

    Sweeps grid sizes ``sizes`` (ascending). For each L, runs the broken-wavefront spiral
    ``measure_cycles`` cycles and classifies: DIES (activity gone in < ``die_below_cycles``
    cycles) vs PERSISTS (still alive at ``persist_cycles`` cycles). ``L_c`` is the smallest
    swept L that PERSISTS. Returns L_c (or None if none in range persisted), and the
    per-size outcomes.
    """
    if sizes is None:
        sizes = list(range(8, 65, 4))
    outcomes = []
    L_c = None
    for L in sizes:
        res = survives_on_size(L, r=r, n_cycles=measure_cycles, wrap=wrap)
        dies_fast = (res["died_at_cycles"] is not None
                     and res["died_at_cycles"] < die_below_cycles)
        persists = res["survived"] and res["n_steps_run"] >= persist_cycles * res["T"]
        outcomes.append({
            "L": L, "survived": res["survived"], "died_at_cycles": res["died_at_cycles"],
            "dies_fast": bool(dies_fast), "persists": bool(persists),
            "final_excited": res["final_excited"],
        })
        if L_c is None and persists:
            L_c = L
    return {
        "r": r, "T": 1 + r, "sizes": sizes,
        "die_below_cycles": die_below_cycles, "persist_cycles": persist_cycles,
        "measure_cycles": measure_cycles,
        "L_c": L_c,
        "outcomes": outcomes,
    }
