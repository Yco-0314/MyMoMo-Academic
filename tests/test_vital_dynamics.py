"""Tests for VitalDynamics (ADR-014 Phase 2) + its two cross-domain adapters.

Library: death removes low energy, reproduction splits energy (conserved), the
population genuinely VARIES (grows/collapses/caps) — what distinguishes it from
fixed-N MoranProcess. Then "two adapters = real seam" via two ecological regimes
that use the operator differently: density-regulated growth → carrying capacity,
and a finite resource → boom-bust collapse.
"""
from __future__ import annotations

import random

from abm_auto.runtime import VitalDynamics
from abm_auto.runtime._vital_dynamics import self_test


class _Critter:
    __slots__ = ("energy",)


def _pop(n, energy):
    out = []
    for _ in range(n):
        c = _Critter(); c.energy = float(energy); out.append(c)
    return out


def _spawn():
    c = _Critter(); c.energy = 0.0; return c


# ── library ────────────────────────────────────────────────────────────────


def test_self_test_passes() -> None:
    assert self_test() is True


def test_death_removes_low_energy() -> None:
    vd = VitalDynamics(death_at=0, reproduce_at=999)        # nothing reproduces
    pop = _pop(3, 5) + _pop(2, -1) + _pop(1, 0)
    births, deaths = vd.step(pop, spawn=_spawn)
    assert (births, deaths) == (0, 3) and len(pop) == 3


def test_reproduction_splits_energy() -> None:
    vd = VitalDynamics(death_at=0, reproduce_at=10)
    pop = _pop(1, 20)
    vd.step(pop, spawn=_spawn)
    assert len(pop) == 2 and sorted(a.energy for a in pop) == [10.0, 10.0]


def test_requires_a_reproduction_rule() -> None:
    import pytest
    with pytest.raises(ValueError):
        VitalDynamics(death_at=0)                           # neither reproduce_at nor _prob


def test_carrying_capacity_caps_growth() -> None:
    vd = VitalDynamics(death_at=0, reproduce_at=1, max_population=10)
    pop = _pop(8, 100)
    vd.step(pop, spawn=_spawn)
    assert len(pop) <= 10


# ── adapters: VitalDynamics in two ecological regimes ────────────────────────


def _run_capped_growth(seed, steps=80, cap=40):
    """Abundant food (net energy gain → no starvation) + a carrying-capacity
    cap: the population grows from a few and PLATEAUS at the cap, holding there
    (logistic-style) — it does not crash."""
    rng = random.Random(seed)
    vd = VitalDynamics(death_at=0, reproduce_prob=0.3, max_population=cap, seed=seed)
    pop = _pop(4, 12)
    hist = []
    for _ in range(steps):
        for a in pop:
            a.energy += 4.0 - 1.0          # net gain → energy stays positive, no deaths
        vd.step(pop, spawn=_spawn, rng=rng)
        hist.append(len(pop))
    return hist


def _run_boom_bust(seed, steps=120):
    """A FINITE, non-renewing resource: the population blooms while food lasts,
    then collapses to extinction once it is exhausted."""
    rng = random.Random(seed)
    vd = VitalDynamics(death_at=0, reproduce_at=8, seed=seed)
    pop = _pop(5, 6)
    resource = 600.0
    hist = []
    for _ in range(steps):
        if pop:
            if resource > 0:
                per_capita = min(resource / len(pop), 5.0)
                resource -= per_capita * len(pop)
                for a in pop:
                    a.energy += per_capita - 2.0
            else:
                for a in pop:
                    a.energy -= 2.0           # starve
        vd.step(pop, spawn=_spawn, rng=rng)
        hist.append(len(pop))
    return hist


def test_capped_growth_reaches_and_holds_cap() -> None:
    """Population grows from a few and PLATEAUS at the carrying-capacity cap (40),
    holding there — variable-N growth + regulation, no crash."""
    hist = _run_capped_growth(seed=0, cap=40)
    assert hist[0] < 40                # started below cap
    assert max(hist) >= 38             # grew to (near) the cap
    assert sum(hist[-20:]) / 20 >= 35  # held at the cap, did not crash


def test_boom_bust_collapses_to_extinction() -> None:
    """On a finite resource the population BLOOMS above its start then CRASHES to
    extinction — the variable-N down-swing fixed-N turnover cannot show."""
    hist = _run_boom_bust(seed=1)
    assert max(hist) > 10              # bloomed
    assert hist[-1] == 0              # crashed to extinction
