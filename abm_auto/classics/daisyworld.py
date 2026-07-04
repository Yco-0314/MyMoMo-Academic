"""Watson-Lovelock Daisyworld (1983) — a genuine agent-based, spatial reproduction.

Source: Watson, A.J. & Lovelock, J.E. (1983) "Biological homeostasis of the global
environment: the parable of Daisyworld", Tellus B 35(4):284-289.
doi:10.1111/j.1600-0889.1983.tb00031.x.

Watson & Lovelock's parable: a planet seeded with two daisy species — BLACK (low albedo,
absorbs sunlight, locally WARM) and WHITE (high albedo, reflects sunlight, locally COOL) —
keeps its global temperature nearly constant across a wide range of solar luminosity. As
the sun brightens, white daisies (which thrive by cooling their own patches) take over and
raise the planetary albedo, cancelling the warming; as it dims, black daisies dominate and
warm the planet. The regulation is an emergent consequence of *local* selection on growth,
with NO global control law — exactly the kind of self-organisation an ABM should show.

THIS IS A GENUINE AGENT-BASED MODEL (not a cellular automaton, not the original two-ODE
mean-field box model). Each grid CELL is a `Patch` agent that, on its turn, perceives its
own local temperature and its neighbourhood, then ACTS: an occupied daisy patch may die
(age-out at a fixed rate) and a daisy patch may colonise an empty von-Neumann neighbour
with a probability set by a parabolic growth response to that neighbour's local temperature.
The model rides ``abm_auto._platform`` (Agent / AgentModel / DataCollector). The only
difference between the two experimental arms is the PRESENCE OF DAISIES (a bare control vs a
daisy-seeded world) — same grid, same albedos, same luminosity grid, same seeds (FAIR).

Temperature rule (documented, the load-bearing physical assumption)
-------------------------------------------------------------------
We use a two-part rule: a planetary energy balance for the mean, plus a LOCAL albedo
correction so a cell's own colour shifts its temperature (this is what couples life to
climate at the patch level), then a diffusion smoothing toward the local mean.

  1. Mean planetary albedo  A_bar = mean over cells of the cell albedo (bare / black /
     white). With white > bare > black albedo, more white daisies raise A_bar.

  2. Planetary effective temperature from a Stefan-Boltzmann-like balance
        S * L_sol * (1 - A_bar) = sigma * (T_planet_K)^4
     (S = solar constant, L_sol = solar-luminosity multiplier, sigma = Stefan-Boltzmann).
     We pick S so that at L_sol = 1.0 and the BARE albedo a planet of all-bare ground sits
     near the daisy growth optimum (~22.5 C). T_planet is then in kelvin; convert to C.

  3. Local temperature of a cell = T_planet + LOCAL_GAIN * (A_bar - albedo_cell). A cell
     darker than the planetary mean (black daisy, low albedo) is locally WARMER; a brighter
     cell (white daisy) is locally COOLER. This is the Watson-Lovelock local-heating term
     (their q*(A_bar - A_i)), and it is what lets a daisy modify the temperature that
     governs its own and its neighbours' growth.

  4. Diffusion: blend each cell's local temperature DIFFUSE-fraction toward the mean of its
     Moore-8 neighbourhood (a one-pass smoothing, as in the NetLogo Daisyworld), so heat
     spreads between patches rather than each patch being thermally isolated.

Growth response (the parabolic selection on temperature)
--------------------------------------------------------
A daisy seeds an empty neighbour with probability beta(T_local) = max(0, 1 - k*(T_opt -
T_local)^2), a downward parabola peaking at T_opt = 22.5 C and reaching 0 at +/- sqrt(1/k)
degrees from the optimum. Black and white daisies share the SAME beta curve; they differ
only in albedo, so the SELECTION between them is purely via the local temperature each
creates. Daisies die at a fixed per-tick rate gamma (age-out), independent of temperature.

Determinism: one ``numpy.random.default_rng(seed)`` drives the initial seeding, the
death draws and the colonisation draws; identical seed -> identical trajectory.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from abm_auto._platform import Agent, AgentModel, DataCollector

# Cell states.
BARE = 0
BLACK = 1
WHITE = 2

# Default albedos (fraction of sunlight reflected): bare ~0.5, black ~0.25 (absorbs ->
# warm), white ~0.75 (reflects -> cool). Locked before the run; NOT tuned.
ALBEDO_BARE = 0.5
ALBEDO_BLACK = 0.25
ALBEDO_WHITE = 0.75

# Stefan-Boltzmann constant (W m^-2 K^-4).
SIGMA = 5.670374419e-8


def solar_constant_for_optimum(t_opt_c: float = 22.5, albedo_bare: float = ALBEDO_BARE) -> float:
    """Return the solar constant S such that an ALL-BARE planet at L_sol=1.0 has mean
    temperature exactly ``t_opt_c`` (so the world starts near the daisy optimum at unit
    luminosity). From S*(1-A_bare) = sigma*T_K^4 with T_K = t_opt_c + 273.15."""
    t_k = t_opt_c + 273.15
    return SIGMA * t_k ** 4 / (1.0 - albedo_bare)


class Patch(Agent):
    """One grid cell as an agent. Holds its (row, col), its state (bare/black/white) and
    its current local temperature (set by the model each tick before agents act). On its
    step it MAY die (occupied patches age out at rate gamma) and MAY colonise an empty
    von-Neumann neighbour with the parabolic growth probability evaluated at that
    neighbour's local temperature."""

    def __init__(self, agent_id: int, model: "Daisyworld", r: int, c: int, state: int) -> None:
        super().__init__(agent_id, model)
        self.r = r
        self.c = c
        self.state = state
        self.temp = 0.0  # local temperature (C); refreshed by the model each tick

    def step(self) -> None:  # pragma: no cover - exercised via model.step
        m = self.model
        # 1. Death (age-out) — occupied patches die at a fixed rate gamma.
        if self.state != BARE and m.rng.random() < m.gamma:
            self.state = BARE
            return
        # 2. Reproduction — an occupied patch tries to colonise ONE empty von-Neumann
        #    neighbour, chosen at random, with probability beta(neighbour's local temp).
        if self.state == BARE:
            return
        empties = m.empty_neighbours(self.r, self.c)
        if not empties:
            return
        nr, nc = empties[int(m.rng.integers(0, len(empties)))]
        beta = m.growth_prob(m.temp_grid[nr, nc])
        if m.rng.random() < beta:
            m.patch_at(nr, nc).state = self.state


class Daisyworld(AgentModel):
    """A spatial, agent-based Daisyworld on an L x L grid (toroidal Moore-8 diffusion,
    von-Neumann colonisation). Each tick: recompute every cell's local temperature from
    the current daisy layout and L_sol, then let the Patch agents act (death + spread).

    The ``with_daisies`` flag is the ONLY arm difference: with it False the world is all
    bare ground forever (the bare control — temperature is just the energy balance at the
    bare albedo, no biota), exercising the same temperature rule and L_sol.
    """

    def __init__(
        self,
        *,
        L: int = 50,
        L_sol: float = 1.0,
        t_opt: float = 22.5,
        k: float = 0.003265,
        gamma: float = 0.1,
        albedo_bare: float = ALBEDO_BARE,
        albedo_black: float = ALBEDO_BLACK,
        albedo_white: float = ALBEDO_WHITE,
        local_gain: float = 30.0,
        diffuse: float = 0.5,
        solar_constant: Optional[float] = None,
        init_black_frac: float = 0.1,
        init_white_frac: float = 0.1,
        with_daisies: bool = True,
        seed: int = 0,
        collect: bool = True,
    ) -> None:
        super().__init__(seed=seed)
        if L <= 0:
            raise ValueError("L must be positive")
        if not (0.0 <= albedo_black < albedo_bare < albedo_white <= 1.0):
            raise ValueError("require 0 <= albedo_black < albedo_bare < albedo_white <= 1")
        self.L = L
        self.L_sol = float(L_sol)
        self.t_opt = float(t_opt)
        self.k = float(k)
        self.gamma = float(gamma)
        self.albedo = {BARE: albedo_bare, BLACK: albedo_black, WHITE: albedo_white}
        self.local_gain = float(local_gain)
        self.diffuse = float(diffuse)
        self.with_daisies = with_daisies
        self.S = solar_constant if solar_constant is not None else solar_constant_for_optimum(
            t_opt, albedo_bare)
        # numpy RNG drives all stochastic choices (seeding + death + spread).
        self.rng = np.random.default_rng(seed)

        # State grid + temperature grid.
        self.grid = np.full((L, L), BARE, dtype=np.int8)
        self.temp_grid = np.zeros((L, L), dtype=np.float64)

        if with_daisies:
            self._seed_daisies(init_black_frac, init_white_frac)

        # Build the Patch agent for every cell (row-major order = sequential schedule).
        self._patches: List[List[Patch]] = [[None] * L for _ in range(L)]  # type: ignore
        aid = 0
        for r in range(L):
            for c in range(L):
                p = Patch(aid, self, r, c, int(self.grid[r, c]))
                self._patches[r][c] = p
                self.add_agent(p)
                aid += 1

        self._compute_temperatures()  # so temps are valid before the first agent step

        if collect:
            self.reporter = DataCollector({
                "mean_temp": lambda mm: mm.mean_temp(),
                "black_frac": lambda mm: mm.state_fraction(BLACK),
                "white_frac": lambda mm: mm.state_fraction(WHITE),
                "bare_frac": lambda mm: mm.state_fraction(BARE),
            })

    # -- setup helpers ----------------------------------------------------------

    def _seed_daisies(self, black_frac: float, white_frac: float) -> None:
        """Randomly seed black and white daisies on the bare grid (without overlap)."""
        n = self.L * self.L
        idx = self.rng.permutation(n)
        n_black = int(round(black_frac * n))
        n_white = int(round(white_frac * n))
        flat = self.grid.ravel()
        flat[idx[:n_black]] = BLACK
        flat[idx[n_black:n_black + n_white]] = WHITE

    def patch_at(self, r: int, c: int) -> Patch:
        return self._patches[r][c]

    # -- temperature rule -------------------------------------------------------

    def _albedo_grid(self) -> np.ndarray:
        """(L,L) float array of each cell's albedo from its current state."""
        a = np.empty(self.grid.shape, dtype=np.float64)
        a[self.grid == BARE] = self.albedo[BARE]
        a[self.grid == BLACK] = self.albedo[BLACK]
        a[self.grid == WHITE] = self.albedo[WHITE]
        return a

    def _planet_temp_c(self, mean_albedo: float) -> float:
        """Planetary effective temperature (deg C) from S*L_sol*(1-A_bar)=sigma*T_K^4."""
        flux = self.S * self.L_sol * (1.0 - mean_albedo)
        t_k = (flux / SIGMA) ** 0.25
        return t_k - 273.15

    def _moore_neighbour_mean(self, field: np.ndarray) -> np.ndarray:
        """Toroidal Moore-8 neighbour mean of ``field`` (for the diffusion smoothing)."""
        total = np.zeros_like(field)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                total += np.roll(np.roll(field, di, axis=0), dj, axis=1)
        return total / 8.0

    def _compute_temperatures(self) -> None:
        """Refresh ``temp_grid`` from the CURRENT daisy layout and L_sol.

        T_local = T_planet + local_gain*(A_bar - albedo_cell), then diffused
        DIFFUSE-fraction toward the Moore-8 neighbour mean.
        """
        alb = self._albedo_grid()
        a_bar = float(alb.mean())
        t_planet = self._planet_temp_c(a_bar)
        local = t_planet + self.local_gain * (a_bar - alb)
        if self.diffuse > 0.0:
            nbr = self._moore_neighbour_mean(local)
            local = (1.0 - self.diffuse) * local + self.diffuse * nbr
        self.temp_grid = local

    def growth_prob(self, t_local: float) -> float:
        """Parabolic growth response beta(T) = max(0, 1 - k*(T_opt - T)^2)."""
        return max(0.0, 1.0 - self.k * (self.t_opt - t_local) ** 2)

    def empty_neighbours(self, r: int, c: int) -> List[Tuple[int, int]]:
        """The von-Neumann (4) neighbours of (r,c) that are currently BARE (toroidal)."""
        L = self.L
        out = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr = (r + dr) % L
            cc = (c + dc) % L
            if self._patches[rr][cc].state == BARE:
                out.append((rr, cc))
        return out

    # -- metrics ----------------------------------------------------------------

    def _sync_grid_from_patches(self) -> None:
        """Mirror the patch agents' states back into the int grid (for fast metrics)."""
        for r in range(self.L):
            row = self._patches[r]
            for c in range(self.L):
                self.grid[r, c] = row[c].state

    def mean_temp(self) -> float:
        return float(self.temp_grid.mean())

    def state_fraction(self, state: int) -> float:
        return float(np.mean(self.grid == state))

    def counts(self) -> Dict[str, int]:
        return {
            "bare": int(np.sum(self.grid == BARE)),
            "black": int(np.sum(self.grid == BLACK)),
            "white": int(np.sum(self.grid == WHITE)),
        }

    # -- tick -------------------------------------------------------------------

    def step(self) -> None:
        """One Daisyworld tick: refresh temps from the current layout, then let every
        Patch agent act (death + colonisation), then sync the grid + collect metrics."""
        self._compute_temperatures()
        self.agents.step()          # sequential per-patch death + spread
        self._sync_grid_from_patches()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_steps: int) -> List[Dict[str, Any]]:
        if self.reporter is not None:
            self.reporter.collect(self)   # t=0 baseline
        for _ in range(n_steps):
            self.step()
        return self.reporter.records if self.reporter is not None else []


# -- experiment helpers -----------------------------------------------------------

def equilibrate(
    *,
    L_sol: float,
    with_daisies: bool,
    seed: int,
    steps: int = 200,
    avg_last: int = 50,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Run one Daisyworld to (quasi-)equilibrium at a given L_sol and return the
    time-averaged mean temperature and daisy fractions over the last ``avg_last`` ticks.

    ``with_daisies=False`` is the bare control (no biota; same temperature rule + L_sol).
    Deterministic given ``seed``. Extra kwargs pass through to ``Daisyworld``.
    """
    m = Daisyworld(L_sol=L_sol, with_daisies=with_daisies, seed=seed, **kwargs)
    records = m.run(steps)
    tail = records[-avg_last:] if avg_last > 0 else records
    mean_temp = float(np.mean([r["mean_temp"] for r in tail]))
    black = float(np.mean([r["black_frac"] for r in tail]))
    white = float(np.mean([r["white_frac"] for r in tail]))
    bare = float(np.mean([r["bare_frac"] for r in tail]))
    return {
        "L_sol": L_sol, "with_daisies": with_daisies, "seed": seed,
        "mean_temp": mean_temp, "black_frac": black, "white_frac": white,
        "bare_frac": bare,
        "final_temp": records[-1]["mean_temp"],
        "final_black": records[-1]["black_frac"],
        "final_white": records[-1]["white_frac"],
    }


def sweep_luminosity(
    *,
    L_sol_grid: List[float],
    seeds: List[int],
    with_daisies: bool,
    steps: int = 200,
    avg_last: int = 50,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """For each L_sol in the grid, equilibrate across all ``seeds`` and return the
    seed-averaged mean temperature + daisy fractions (one row per L_sol)."""
    rows = []
    for L_sol in L_sol_grid:
        per_seed = [
            equilibrate(L_sol=L_sol, with_daisies=with_daisies, seed=s,
                        steps=steps, avg_last=avg_last, **kwargs)
            for s in seeds
        ]
        rows.append({
            "L_sol": L_sol,
            "mean_temp": float(np.mean([r["mean_temp"] for r in per_seed])),
            "temp_std": float(np.std([r["mean_temp"] for r in per_seed])),
            "black_frac": float(np.mean([r["black_frac"] for r in per_seed])),
            "white_frac": float(np.mean([r["white_frac"] for r in per_seed])),
            "bare_frac": float(np.mean([r["bare_frac"] for r in per_seed])),
            "per_seed_temp": [r["mean_temp"] for r in per_seed],
        })
    return rows


def temp_range(rows: List[Dict[str, Any]]) -> float:
    """max - min seed-averaged mean temperature across a luminosity sweep (deg C)."""
    temps = [r["mean_temp"] for r in rows]
    return float(max(temps) - min(temps)) if temps else 0.0
