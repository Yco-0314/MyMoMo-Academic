"""ABM Auto Runtime — VitalDynamics, a variable-population birth/death operator.

Harvested by demand (ADR-014 Phase 2): ~11 corpus models are energy/resource
ecologies (wolf-sheep, rabbits-grass, daisyworld, tragedy-of-the-commons) whose
population GROWS and SHRINKS. `MoranProcess` cannot serve them — it is fixed-N
(one death per birth). VitalDynamics is the variable-N sibling: agents below a
death condition are removed, agents meeting a reproduction condition spawn
offspring, and the population size is EMERGENT.

The error-prone parts are LIBRARY: never add/remove while iterating (rebuild the
list once), conserve energy on a split, cap at a carrying capacity. The model
supplies only its domain bits — the per-step energy dynamics (applied to agents
BEFORE step), a `spawn` factory that creates a blank child, and an optional
`on_birth(parent, child)` hook to finish initialising it.
"""
from __future__ import annotations

import random
from typing import Callable, Optional


class VitalDynamics:
    """Variable-population birth/death. One ``step`` is: remove the dead
    (energy <= ``death_at``), then let survivors reproduce — by an energy
    threshold (``reproduce_at``) or a per-step probability (``reproduce_prob``);
    on reproduction the parent's energy is split with the child (unless
    ``split_energy=False``). ``max_population`` caps growth. Returns
    (births, deaths); the ``agents`` list is rebuilt in place.
    """

    def __init__(
        self,
        *,
        energy_attr: str = "energy",
        death_at: float = 0.0,
        reproduce_at: Optional[float] = None,
        reproduce_prob: Optional[float] = None,
        split_energy: bool = True,
        max_population: Optional[int] = None,
        seed: int = 0,
    ) -> None:
        if reproduce_at is None and reproduce_prob is None:
            raise ValueError("VitalDynamics needs reproduce_at OR reproduce_prob")
        if reproduce_prob is not None and not (0.0 <= reproduce_prob <= 1.0):
            raise ValueError(f"reproduce_prob={reproduce_prob} must be in [0, 1]")
        if max_population is not None and max_population < 1:
            raise ValueError("max_population must be >= 1")
        self.energy_attr = energy_attr
        self.death_at = float(death_at)
        self.reproduce_at = reproduce_at
        self.reproduce_prob = reproduce_prob
        self.split_energy = split_energy
        self.max_population = max_population
        self._rng = random.Random(seed)

    def _energy(self, a) -> float:
        return float(getattr(a, self.energy_attr))

    def _reproduces(self, a, rng: random.Random) -> bool:
        if self.reproduce_at is not None:
            return self._energy(a) >= self.reproduce_at
        return rng.random() < self.reproduce_prob

    def step(self, agents: list, *, spawn: Callable, on_birth: Optional[Callable] = None,
             rng: Optional[random.Random] = None) -> tuple[int, int]:
        r = rng or self._rng
        survivors = [a for a in agents if self._energy(a) > self.death_at]
        deaths = len(agents) - len(survivors)

        newborns = []
        for parent in survivors:
            if self.max_population is not None and \
                    len(survivors) + len(newborns) >= self.max_population:
                break
            if not self._reproduces(parent, r):
                continue
            child = spawn()
            if self.split_energy:
                half = self._energy(parent) / 2.0
                setattr(parent, self.energy_attr, half)
                setattr(child, self.energy_attr, half)
            if on_birth is not None:
                on_birth(parent, child)
            newborns.append(child)

        agents[:] = survivors + newborns      # rebuild once — no mutate-while-iterate
        return (len(newborns), deaths)


def self_test() -> bool:
    """Library self-test: death removes low energy, reproduction splits energy
    (conserved), and the population genuinely VARIES — grows when fed, collapses
    to zero when starved (what makes this distinct from fixed-N MoranProcess).
    """
    class _A:
        pass

    def make(energies):
        out = []
        for e in energies:
            a = _A(); a.energy = float(e); out.append(a)
        return out

    def spawn():
        c = _A(); c.energy = 0.0; return c

    # threshold mode: die at <=0, reproduce at >=10, split energy
    vd = VitalDynamics(energy_attr="energy", death_at=0, reproduce_at=10)
    agents = make([12, 5, 0, -1, 20])         # 0,-1 die; 12,20 reproduce; 5 idles
    births, deaths = vd.step(agents, spawn=spawn)
    if (births, deaths) != (2, 2):
        return False
    # 3 survivors + 2 newborns; energy conserved on split (12->6+6, 20->10+10)
    if sorted(a.energy for a in agents) != [5, 6, 6, 10, 10]:
        return False

    # population GROWS when everyone is fed (births, no deaths)
    pop = make([20] * 8)
    b, d = vd.step(pop, spawn=spawn)
    if d != 0 or b != 8 or len(pop) != 16:
        return False

    # population COLLAPSES to zero when starved (all die, no births)
    dead = make([-1] * 6)
    b, d = vd.step(dead, spawn=spawn)
    if (b, d, len(dead)) != (0, 6, 0):
        return False

    # carrying capacity caps growth
    capped = VitalDynamics(death_at=0, reproduce_at=1, max_population=10)
    pop = make([100] * 8)
    capped.step(pop, spawn=spawn)
    if len(pop) > 10:
        return False
    return True
