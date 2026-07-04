"""Scoped reproduction of Anshuka et al. 2026 (IJDRS 17:439-455).

Bathtub flood inundation on a synthetic grid + BDI human agents + a forecaster
agent. Honest scope (see PREDICTIONS-locked.md): faithful to the *mechanism*
and *direction* of all five levers (belief, alarm time, onset rate, mobility,
collaboration) and the second-order sensitivity ordering — NOT to the real Ba
catchment GIS layers.

The five `run_*` entry points each take parameters that vary one lever holding
the others at the base scenario, returning evacuated / incapacitated counts.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


# ── World layout ─────────────────────────────────────────────────────────────

# A small 20x20 grid following the paper's symbolic scheme:
#   R = river / source       (flooded at t=0)
#   B = building (agent home; agents start here)
#   W = water (river width buffer, also flooded at t=0)
#   P = path / road  (agents move only on R/B/_/P/S free of water)
#   _ = empty land
#   S = shelter (evacuation target)
#
# Elevation increases away from the river (rough left-to-right gradient with
# noise) so the bathtub flood propagates as adjacency + elevation <= water level.

_GRID_SIZE = 20

# Reproducible base layout: river on column 1, road runs along column 10,
# 4 shelters at the corners-ish, buildings in two clusters near the river.
_RIVER_COLS = (0, 1)
_ROAD_COL = 10
_SHELTERS = [(2, 18), (10, 18), (15, 18), (5, 18)]   # eastern edge (high ground)
_BUILDINGS = [
    (r, c) for r in range(3, 17) for c in (4, 5, 6, 7, 8, 9)
]


@dataclass
class AgentState:
    row: int
    col: int
    aware: bool          # has agent received and BELIEVED a warning?
    evacuated: bool
    incapacitated: bool
    mobility: float      # cells per tick (1.0 good, 0.5 reduced)
    vision: int          # Moore radius for self-warning
    prior_experience: Optional[bool] = None
    target: Optional[Tuple[int, int]] = None


# ── Bathtub flood ────────────────────────────────────────────────────────────

def _build_elevation(rng: random.Random) -> np.ndarray:
    """Gentle east-rising elevation so the floodplain (buildings, col 4-9) sits
    only slightly above the river. The shelter ridge (col 18) is the highest
    ground. Mirrors a peri-urban Ba-like floodplain qualitatively."""
    elev = np.zeros((_GRID_SIZE, _GRID_SIZE), dtype=float)
    for r in range(_GRID_SIZE):
        for c in range(_GRID_SIZE):
            # gentle quadratic so the buildings are low; shelter ridge is high
            base = 0.15 * c + 0.012 * c * c
            jitter = rng.uniform(-0.05, 0.05)
            elev[r, c] = base + jitter
    for r in range(_GRID_SIZE):
        for rc in _RIVER_COLS:
            elev[r, rc] = -1.0                      # river bed lowest
    return elev


_MOORE3 = np.ones((3, 3), dtype=bool)


def _bathtub_step(water: np.ndarray, elev: np.ndarray,
                  level: float) -> np.ndarray:
    """One bathtub spread step (vectorised; identical rule to the original loop).

    A cell becomes wet if (a) it is adjacent to an existing wet cell (Moore-1),
    and (b) its elevation <= `level` (the current water surface). Synchronous —
    neighbour wetness is read from the INPUT `water`, not the in-progress output.
    Matches the paper's Fig 3 illustration. Vectorised with a 3x3 binary dilation
    so a real ~100x100 Ba grid runs in C, not a Python triple loop (candidate #10).
    """
    from scipy.ndimage import binary_dilation

    wet = water > 0
    # dilation marks every cell that is itself wet OR has a wet Moore-1 neighbour;
    # a DRY cell flagged here therefore has >=1 wet neighbour (out-of-bounds = dry).
    neighbour_wet = binary_dilation(wet, structure=_MOORE3)
    new_wet = (~wet) & neighbour_wet & (elev <= level)
    return (wet | new_wet).astype(water.dtype)


# ── Agent step ────────────────────────────────────────────────────────────────

def _move_one_step(agent: AgentState, water: np.ndarray,
                   shelters: List[Tuple[int, int]],
                   rng: random.Random,
                   grid_size: int = _GRID_SIZE) -> None:
    """Move one Manhattan-step toward the agent's target shelter, skipping wet
    cells. If `mobility < 1.0`, agent only moves on a fraction of ticks.

    `grid_size` is a parameter (default = the synthetic 20) so the real-DEM
    reproduction can run the SAME mechanism on a ~100x100 Ba grid."""
    if agent.incapacitated or agent.evacuated:
        return

    if rng.random() > agent.mobility:
        return                                      # this tick: no move

    if agent.target is None:
        agent.target = min(
            shelters,
            key=lambda s: abs(s[0] - agent.row) + abs(s[1] - agent.col),
        )

    tr, tc = agent.target
    dr = (tr > agent.row) - (tr < agent.row)
    dc = (tc > agent.col) - (tc < agent.col)

    # try row then col; skip wet cells
    candidates = []
    if dr != 0:
        candidates.append((agent.row + dr, agent.col))
    if dc != 0:
        candidates.append((agent.row, agent.col + dc))
    for nr, nc in candidates:
        if 0 <= nr < grid_size and 0 <= nc < grid_size and water[nr, nc] == 0:
            agent.row, agent.col = nr, nc
            break

    if (agent.row, agent.col) == agent.target:
        agent.evacuated = True


def _vision_detects_flood(agent: AgentState, water: np.ndarray,
                          grid_size: int = _GRID_SIZE) -> bool:
    r0, c0 = agent.row, agent.col
    v = agent.vision
    rs = slice(max(0, r0 - v), min(grid_size, r0 + v + 1))
    cs = slice(max(0, c0 - v), min(grid_size, c0 + v + 1))
    return bool((water[rs, cs] > 0).any())


def _validate_prior_experience_frac(prior_experience_frac: Optional[float]) -> Optional[float]:
    if prior_experience_frac is None:
        return None
    if isinstance(prior_experience_frac, bool):
        raise ValueError("prior_experience_frac must be a float in [0, 1] or None")
    p = float(prior_experience_frac)
    if not np.isfinite(p) or p < 0.0 or p > 1.0:
        raise ValueError("prior_experience_frac must be a float in [0, 1] or None")
    return p


# ── Scenario runner ──────────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    evacuated: int
    incapacitated: int
    still_moving: int


def _simulate(
    rng: random.Random,
    grid_size: int,
    elev: np.ndarray,
    water: np.ndarray,
    homes: List[Tuple[int, int]],
    shelters: List[Tuple[int, int]],
    *,
    belief: float,
    alarm_t: int,
    onset_steps: int,
    mobility_good_frac: float,
    collaboration: bool,
    prior_experience_frac: Optional[float] = None,
    n_agents: int,
    max_steps: int,
) -> ScenarioResult:
    """The shared BDI-evacuation mechanism. Both ``run_scenario`` (the synthetic
    20x20 control) and ``_anshuka_real.run_scenario_real`` (the real Ba SRTM/OSM
    world, candidate #10) call this with an injected world — so the mechanism is
    byte-identical across them and ONLY the world geometry differs. The rng is
    passed in already-seeded so each entry point controls its own world-build draws."""
    prior_experience_frac = _validate_prior_experience_frac(prior_experience_frac)
    # initialise agents at random buildings
    agents: List[AgentState] = []
    for i in range(n_agents):
        r0, c0 = rng.choice(homes)
        mobility = 1.0 if rng.random() < mobility_good_frac else 0.5
        # vision range follows a normal distribution (paper §2.3.7); clip to [1, 3]
        vision = max(1, min(3, int(round(rng.gauss(1.0, 0.8)))))
        prior_experience = (
            None if prior_experience_frac is None else rng.random() < prior_experience_frac
        )
        agents.append(AgentState(
            row=r0, col=c0, aware=False, evacuated=False, incapacitated=False,
            mobility=mobility, vision=vision, prior_experience=prior_experience,
        ))

    flood_level = 0.0
    for t in range(max_steps):
        # forecaster issues the alarm at alarm_t
        if t == alarm_t:
            for a in agents:
                if a.evacuated or a.incapacitated:
                    continue
                if rng.random() < belief:
                    a.aware = True

        # bathtub: water level rises every `onset_steps` ticks
        if t > 0 and t % max(1, onset_steps) == 0:
            flood_level += 0.4
        water = _bathtub_step(water, elev, flood_level)

        # vision-based self-warning: detection is automatic, but ACTING on it
        # still requires the agent to "believe" the cue. Low-belief agents see
        # the flood but distrust the cue (paper §2.3.7: "they may also choose to
        # evacuate"). We gate uptake on the same belief probability.
        for a in agents:
            if a.evacuated or a.incapacitated or a.aware:
                continue
            if _vision_detects_flood(a, water, grid_size):
                if rng.random() < belief:
                    a.aware = True

        if collaboration:
            aware_positions = {(a.row, a.col) for a in agents if a.aware}
            for a in agents:
                if a.evacuated or a.incapacitated or a.aware:
                    continue
                # told by a neighbour standing on the same cell
                if (a.row, a.col) in aware_positions:
                    if prior_experience_frac is not None and not a.prior_experience:
                        continue
                    if rng.random() < belief:        # belief gates the uptake
                        a.aware = True

        # incapacitation: an agent standing in water at step end is incapacitated
        for a in agents:
            if a.evacuated or a.incapacitated:
                continue
            if water[a.row, a.col] > 0:
                a.incapacitated = True

        # movement: aware agents head for shelter
        for a in agents:
            if a.aware:
                _move_one_step(a, water, shelters, rng, grid_size)

        if all(a.evacuated or a.incapacitated for a in agents):
            break

    return ScenarioResult(
        evacuated=sum(1 for a in agents if a.evacuated),
        incapacitated=sum(1 for a in agents if a.incapacitated),
        still_moving=sum(1 for a in agents if not (a.evacuated or a.incapacitated)),
    )


def run_scenario(
    *,
    belief: float,          # probability an agent BELIEVES the alarm (P1)
    alarm_t: int,           # tick at which the forecaster issues the alarm (P2)
    onset_steps: int,       # ticks between water-level rises (P3:
                            #   small=rapid, large=slow)
    mobility_good_frac: float,    # fraction of agents with mobility=1.0 (P4)
    collaboration: bool,    # aware agents tell neighbours each tick (P5)
    prior_experience_frac: Optional[float] = None,
    n_agents: int = 100,
    seed: int = 0,
    max_steps: int = 150,
) -> ScenarioResult:
    """Synthetic 20x20-grid scenario (the control). Builds the synthetic world,
    then runs the shared ``_simulate`` mechanism. Candidate #10
    (``abm_auto/gis/_anshuka_real.py``) injects a REAL Ba world into the same
    ``_simulate`` — only the geometry changes."""
    rng = random.Random(seed)
    elev = _build_elevation(rng)
    water = np.zeros((_GRID_SIZE, _GRID_SIZE), dtype=int)
    # initial river/water cells
    for r in range(_GRID_SIZE):
        for rc in _RIVER_COLS:
            water[r, rc] = 1
    return _simulate(
        rng, _GRID_SIZE, elev, water, list(_BUILDINGS), _SHELTERS,
        belief=belief, alarm_t=alarm_t, onset_steps=onset_steps,
        mobility_good_frac=mobility_good_frac, collaboration=collaboration,
        prior_experience_frac=prior_experience_frac,
        n_agents=n_agents, max_steps=max_steps,
    )


# ── Convenience: run multi-seed mean ─────────────────────────────────────────

def mean_outcome(*, n_iter: int = 5, base_seed: int = 0, **kwargs) -> dict:
    """Run `n_iter` seeded simulations and return the mean evac / incap."""
    e, i = [], []
    for k in range(n_iter):
        r = run_scenario(seed=base_seed + k, **kwargs)
        e.append(r.evacuated)
        i.append(r.incapacitated)
    return {"evac": float(np.mean(e)), "incap": float(np.mean(i)),
            "evac_std": float(np.std(e)), "incap_std": float(np.std(i)),
            "n_iter": n_iter}


def prior_experience_collaboration_gate(
    *,
    belief: float = 0.1,
    n_iter: int = 10,
    base_seed: int = 0,
    min_legacy_lift: float = 4.0,
    max_gated_lift: float = 1.0,
) -> tuple[bool, str]:
    """Prove the optional prior-experience gate can suppress collaboration lift.

    This is P5 mechanism evidence on synthetic truth. It does not update the locked
    Anshuka verdict bundle or prove that the real Ba P5 residual is solved.
    """
    base = dict(
        belief=belief,
        alarm_t=0,
        onset_steps=20,
        mobility_good_frac=0.7,
        n_agents=100,
        max_steps=150,
    )
    legacy_off = mean_outcome(
        n_iter=n_iter, base_seed=base_seed, collaboration=False,
        prior_experience_frac=None, **base,
    )
    legacy_on = mean_outcome(
        n_iter=n_iter, base_seed=base_seed, collaboration=True,
        prior_experience_frac=None, **base,
    )
    gated_off = mean_outcome(
        n_iter=n_iter, base_seed=base_seed, collaboration=False,
        prior_experience_frac=0.0, **base,
    )
    gated_on = mean_outcome(
        n_iter=n_iter, base_seed=base_seed, collaboration=True,
        prior_experience_frac=0.0, **base,
    )
    legacy_lift = float(legacy_on["evac"] - legacy_off["evac"])
    gated_lift = float(gated_on["evac"] - gated_off["evac"])
    if legacy_lift < min_legacy_lift:
        return False, (
            f"legacy collaboration lift too small for gate: {legacy_lift:.3f} "
            f"< {min_legacy_lift}; not a real Anshuka reproduction fix"
        )
    if gated_lift > max_gated_lift or gated_lift >= legacy_lift:
        return False, (
            f"prior-experience gate did not reduce collaboration lift enough: "
            f"legacy={legacy_lift:.3f}, gated={gated_lift:.3f}, "
            f"max_gated={max_gated_lift}; not a real Anshuka reproduction fix"
        )
    return True, (
        f"prior-experience gate reduces collaboration lift: legacy={legacy_lift:.3f}, "
        f"gated={gated_lift:.3f}; P5 mechanism evidence only, "
        "not a real Anshuka reproduction fix or traffic-flow validity proof"
    )
