"""2D Ising model with Glauber single-spin dynamics — a faithful agent-based
reproduction of the Onsager ferromagnetic phase transition.

Source: Onsager, L. (1944) "Crystal Statistics. I. A Two-Dimensional Model with an
Order-Disorder Transition", Phys. Rev. 65:117-149. doi:10.1103/PhysRev.65.117.
The exact critical temperature of the 2D square-lattice Ising model is
T_c = 2 / ln(1 + sqrt(2)) ≈ 2.269 (in units where J = k_B = 1).

This IS a genuine agent-based model (disclosed honestly, unlike the BTW/forest-fire
cellular automata in this batch): each lattice site carries a ``SpinAgent`` whose
``step`` performs that site's own Glauber spin-flip decision. The agents are driven by
an ``AgentSet`` scheduler in ``random_order`` (a fresh seeded permutation each sweep =
random-sequential Glauber dynamics), and an ``IsingModel`` (an ``AgentModel`` subclass)
owns the seeded RNG + the shared spin lattice + a ``DataCollector`` for the per-sweep
magnetization series. There is no god-loop: the per-site flip decision lives on the
agent.

Rules (the canonical 2D Ising / Glauber heat-bath update, J = 1, 4 nearest neighbours
with periodic boundaries):

  * An L x L periodic lattice of spins s_i ∈ {+1, -1}. Random initial configuration
    (each spin ±1 with prob 1/2, seeded).
  * One "tick" (sweep) = one random-sequential pass: every site is visited exactly once,
    in a fresh seeded random permutation, and updated in place (the update of site i sees
    the already-updated spins of sites visited earlier this sweep).
  * Glauber single-spin update at site i: let h_i = sum of the 4 nearest-neighbour spins.
    The energy cost of FLIPPING spin i is ΔE = 2 · s_i · h_i (J = 1). Set the spin to
    +1 with the heat-bath probability p_up = 1 / (1 + exp(-2·h_i / T)); equivalently the
    flip s_i -> -s_i is accepted with probability 1 / (1 + exp(ΔE / T)). Both forms are
    identical for the two-state heat bath and are the standard Glauber rule.
  * Magnetization m = (sum_i s_i) / N; the order parameter is |m|. Below T_c the system
    spontaneously orders (|m| -> nonzero); above T_c it is disordered (|m| -> 0 up to a
    finite-size floor ~ 1/sqrt(N)).

Measurement: run a fixed number of sweeps, discard the first half (equilibration), and
average |m| over the second half. Reported per (T, seed); the runner averages over seeds.

Determinism: a single ``numpy.random.default_rng(seed)`` draws BOTH the initial spins
and every per-site accept/reject uniform, in a fixed order, so the same seed reproduces
byte-identical output. NumPy holds the lattice and computes the neighbour field; the
SpinAgent owns the decision and writes its own spin.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from abm_auto._platform import Agent, AgentModel, AgentSet, DataCollector

# Onsager (1944) exact 2D square-lattice critical temperature (J = k_B = 1).
T_C_ONSAGER = 2.0 / math.log(1.0 + math.sqrt(2.0))  # ≈ 2.269185


# -- Agent --------------------------------------------------------------------

class SpinAgent(Agent):
    """One lattice site at grid coordinate (row, col).

    The spin VALUE lives in the model's shared ``lattice`` array (so neighbour reads
    are O(1) and vectorised), but the per-site Glauber DECISION lives here: ``step``
    reads the site's 4-neighbour field from the model, computes the heat-bath
    probability, draws one uniform from the model's RNG, and writes the site's new
    spin back into the lattice. That is the agent acting on its own state — not a
    god-loop sweeping the grid.
    """

    def __init__(self, agent_id: int, model: "IsingModel", *, row: int, col: int) -> None:
        super().__init__(agent_id, model)
        self.row = row
        self.col = col

    def step(self) -> None:
        self.model.glauber_update(self.row, self.col)


# -- the Glauber heat-bath probability (pure function; hand-testable) ---------

def flip_probability(s_i: int, h_i: int, T: float) -> float:
    """Probability of ACCEPTING the flip s_i -> -s_i under the Glauber rule.

    ΔE = 2 · s_i · h_i (J = 1; h_i = sum of the 4 nearest-neighbour spins). The flip is
    accepted with probability 1 / (1 + exp(ΔE / T)). This is the energy-lowering-favoured
    Metropolis-Glauber heat-bath form: ΔE < 0 (flip lowers energy) -> prob > 1/2; ΔE > 0
    -> prob < 1/2; ΔE = 0 -> exactly 1/2. T -> 0 makes it a deterministic descent; large
    T pushes every flip toward 1/2 (disorder).
    """
    dE = 2.0 * s_i * h_i
    return 1.0 / (1.0 + math.exp(dE / T))


def heat_bath_up_probability(h_i: int, T: float) -> float:
    """Probability the spin ENDS at +1 under the heat-bath rule (independent of its
    current value): p_up = 1 / (1 + exp(-2·h_i / T)). Used by the vectorised model
    update; equivalent to ``flip_probability`` applied to whichever current spin."""
    return 1.0 / (1.0 + math.exp(-2.0 * h_i / T))


def neighbour_field(lattice: np.ndarray, row: int, col: int) -> int:
    """Sum of the 4 nearest-neighbour spins of site (row, col) on a periodic L x L
    lattice (the local field h_i). Pure helper for tests / the single-site path."""
    L = lattice.shape[0]
    return int(
        lattice[(row - 1) % L, col]
        + lattice[(row + 1) % L, col]
        + lattice[row, (col - 1) % L]
        + lattice[row, (col + 1) % L]
    )


# -- Model --------------------------------------------------------------------

class IsingModel(AgentModel):
    """2D Ising / Glauber dynamics on an L x L periodic lattice of SpinAgents.

    Construct with L, temperature T, and a seed. ``run`` performs ``n_sweeps``
    random-sequential sweeps; ``step`` (one sweep) drives every SpinAgent once in a
    fresh seeded permutation (random-sequential Glauber). The shared spin lattice is a
    NumPy (L, L) int8 array; ``glauber_update`` is the per-site decision the agent calls.

    The per-sweep |m| is collected by a ``DataCollector``. ``run`` returns the
    equilibrium |m| (mean of |m| over the back half of the sweeps) plus the full series.
    Deterministic given ``seed``.
    """

    def __init__(self, *, L: int = 32, T: float = 2.27, seed: int = 0,
                 n_sweeps: int = 2000) -> None:
        if L <= 0:
            raise ValueError("L must be positive")
        if T <= 0:
            raise ValueError("T must be positive (Glauber prob undefined at T=0)")
        super().__init__(seed=seed, schedule="random_order")
        self.L = L
        self.N = L * L
        self.T = float(T)
        self.seed = seed
        self.n_sweeps = n_sweeps

        # One seeded NumPy generator drives the initial spins AND every accept/reject
        # draw. (The platform's random.Random self.rng is left in place for the
        # AgentSet permutation; the physics RNG is this separate NumPy stream, seeded
        # from the same seed so the whole run is reproducible.)
        self._np_rng = np.random.default_rng(seed)

        # Random ±1 initial configuration.
        self.lattice = np.where(
            self._np_rng.random((L, L)) < 0.5, 1, -1
        ).astype(np.int8)

        # One SpinAgent per site, in row-major order. The AgentSet reshuffles them each
        # sweep (random_order) → random-sequential dynamics.
        self.agents = AgentSet([], schedule="random_order", rng=self.rng)
        aid = 0
        for r in range(L):
            for c in range(L):
                self.add_agent(SpinAgent(aid, self, row=r, col=c))
                aid += 1

        self.reporter = DataCollector({"abs_m": lambda m: m.abs_magnetization()})

    # -- metrics --
    def magnetization(self) -> float:
        return float(self.lattice.sum()) / self.N

    def abs_magnetization(self) -> float:
        return abs(self.magnetization())

    def energy(self) -> float:
        """Total interaction energy E = -J · sum over distinct NN bonds s_i s_j (J=1),
        with periodic boundaries. Each horizontal/vertical bond counted once."""
        lat = self.lattice.astype(np.int64)
        right = (lat * np.roll(lat, -1, axis=1)).sum()
        down = (lat * np.roll(lat, -1, axis=0)).sum()
        return float(-(right + down))

    # -- the per-site Glauber decision the SpinAgent calls --
    def glauber_update(self, row: int, col: int) -> None:
        """Heat-bath update of one site: read its 4-neighbour field, set the spin to +1
        with prob p_up = 1/(1+exp(-2h/T)), else -1. One uniform is drawn from the
        physics RNG. In-place (the next agent this sweep sees the new value)."""
        h = neighbour_field(self.lattice, row, col)
        p_up = heat_bath_up_probability(h, self.T)
        u = float(self._np_rng.random())
        self.lattice[row, col] = 1 if u < p_up else -1

    # -- one sweep = one random-sequential pass over all SpinAgents --
    def step(self) -> None:
        self.agents.step()           # AgentSet random_order → fresh permutation, each agent updates once
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_sweeps`` sweeps; return the equilibrium |m| (mean over the back half)
        and the per-sweep |m| series. Deterministic given the seed."""
        self.reporter.collect(self)          # sweep-0 baseline (initial config)
        for _ in range(self.n_sweeps):
            self.step()
        series = self.reporter.series("abs_m")
        # Discard the first half (equilibration); average |m| over the rest.
        burn = len(series) // 2
        tail = series[burn:]
        eq_abs_m = float(np.mean(tail)) if tail else float(series[-1])
        return {
            "L": self.L,
            "T": self.T,
            "seed": self.seed,
            "n_sweeps": self.n_sweeps,
            "burn_in": burn,
            "abs_m": eq_abs_m,
            "abs_m_series": series,
            "final_abs_m": series[-1] if series else 0.0,
            "final_energy_per_spin": self.energy() / self.N,
        }


# -- single / Monte-Carlo helpers ---------------------------------------------

def run_single(*, L: int = 32, T: float = 2.27, seed: int = 0,
               n_sweeps: int = 2000) -> Dict[str, Any]:
    """One Ising/Glauber run at temperature T; returns the equilibrium |m| summary."""
    return IsingModel(L=L, T=T, seed=seed, n_sweeps=n_sweeps).run()


def run_many_seeds(*, L: int = 32, T: float = 2.27, n_seeds: int = 5,
                   seed_base: int = 0, n_sweeps: int = 2000) -> Dict[str, Any]:
    """Run ``n_seeds`` independent Glauber runs at temperature T and summarise the
    equilibrium |m|.

    Each trial uses seed ``seed_base + i``. Returns the mean / std / min / max of the
    per-seed equilibrium |m|, plus the per-seed records. Deterministic given
    (L, T, seed_base, n_sweeps).
    """
    results: List[Dict[str, Any]] = []
    for i in range(n_seeds):
        results.append(run_single(L=L, T=T, seed=seed_base + i, n_sweeps=n_sweeps))

    abs_ms = [r["abs_m"] for r in results]
    arr = np.asarray(abs_ms, dtype=np.float64)
    return {
        "L": L,
        "T": T,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "n_sweeps": n_sweeps,
        "mean_abs_m": float(arr.mean()),
        "std_abs_m": float(arr.std(ddof=0)),
        "min_abs_m": float(arr.min()),
        "max_abs_m": float(arr.max()),
        "per_seed_abs_m": abs_ms,
        "per_seed": [
            {"seed": r["seed"], "abs_m": r["abs_m"], "final_abs_m": r["final_abs_m"]}
            for r in results
        ],
    }


def sweep_temperatures(temperatures: Sequence[float], *, L: int = 32, n_seeds: int = 5,
                       seed_base: int = 0, n_sweeps: int = 2000) -> List[Dict[str, Any]]:
    """Run the seed-averaged experiment at each temperature in ``temperatures``.

    Returns one ``run_many_seeds`` summary per temperature, in the given order.
    """
    return [
        run_many_seeds(L=L, T=T, n_seeds=n_seeds, seed_base=seed_base, n_sweeps=n_sweeps)
        for T in temperatures
    ]


# -- analysis -----------------------------------------------------------------

def is_monotone_non_increasing(values: Sequence[float], *, tol: float = 1e-9) -> bool:
    """True iff ``values`` is non-increasing within ``tol`` (P3: |m|(T) non-increasing
    across the temperature grid). ``tol`` absorbs finite-size / finite-sample wobble."""
    return all(values[i + 1] <= values[i] + tol for i in range(len(values) - 1))


def half_magnetization_crossing(temperatures: Sequence[float], abs_ms: Sequence[float],
                                *, level: float = 0.5) -> Optional[float]:
    """Estimate the temperature at which the seed-averaged |m| first drops through
    ``level`` (default 0.5), by linear interpolation between the bracketing grid points.

    ``temperatures`` is ascending; ``abs_ms`` is the matching seed-averaged |m|. Returns
    the interpolated crossing T, or None if |m| never crosses from >= level to < level
    on the grid. If |m| is already below ``level`` at the lowest T, returns that lowest T
    (the transition is at or below the grid floor).
    """
    ts = list(temperatures)
    ms = list(abs_ms)
    if not ts:
        return None
    if ms[0] < level:
        return ts[0]
    for i in range(len(ts) - 1):
        m0, m1 = ms[i], ms[i + 1]
        if m0 >= level > m1:
            # Linear interpolation in T for the |m| = level crossing.
            t0, t1 = ts[i], ts[i + 1]
            if m0 == m1:
                return t0
            frac = (m0 - level) / (m0 - m1)
            return t0 + frac * (t1 - t0)
    return None
