"""Second adapter for MoranProcess — "two adapters = a real seam" (ADR-013 W4).

The first adapter is the Yaman cultural-evolution model (learned per-agent
model, Gompertz death, deepcopy-inherit, complex multi-part state). This is a
deliberately DIFFERENT use: a Hawk-Dove evolutionary game with a fixed strategy
(not a learned model), mean-field frequency-dependent payoffs, the CONSTANT
death model (exercising the path Yaman did not), and a mutate-on-inherit hook.

The SAME MoranProcess operator must drive selection to the analytical ESS —
the hawk fraction p* = V/C. If it does, the operator is a reusable seam, not
Yaman-specific.
"""
from __future__ import annotations

import random

from abm_auto.runtime import MoranProcess


class _Player:
    __slots__ = ("strategy", "payoff", "age", "id")


def _run_hawk_dove(*, start_strategy: int, seed: int):
    """Well-mixed Hawk-Dove under a Moran process. V=2, C=4 → ESS hawks = 0.5.

    Returns the hawk-fraction history. fitness = 1 (baseline) + expected
    mean-field payoff at the current hawk fraction p:
        hawk: p·(V−C)/2 + (1−p)·V
        dove:               (1−p)·V/2
    """
    V, C = 2.0, 4.0
    N, GENS, MU = 200, 300, 0.02
    rng = random.Random(seed)

    pop = []
    for i in range(N):
        a = _Player()
        a.id = i
        a.strategy = start_strategy
        a.payoff = 1.0
        a.age = 0
        pop.append(a)

    moran = MoranProcess(fitness_attr="payoff", death_model="constant",
                         death_rate=0.25, seed=seed)

    def inherit(child, parent):
        s = parent.strategy
        if rng.random() < MU:           # mutation: flip strategy
            s = 1 - s
        child.strategy = s
        child.payoff = 1.0

    history = []
    for _ in range(GENS):
        p = sum(a.strategy for a in pop) / len(pop)      # hawk fraction
        hawk_fit = 1.0 + p * (V - C) / 2 + (1 - p) * V
        dove_fit = 1.0 + (1 - p) * V / 2
        for a in pop:
            a.payoff = hawk_fit if a.strategy == 1 else dove_fit
        moran.turnover(pop, inherit=inherit, rng=rng)
        assert len(pop) == N                              # fixed N invariant
        history.append(p)
    return history


def test_moran_drives_hawk_dove_to_ess_from_doves() -> None:
    """Starting from an all-dove population, mutation introduces hawks and the
    SAME operator drives the hawk fraction up to the ESS (0.5)."""
    hist = _run_hawk_dove(start_strategy=0, seed=0)
    avg = sum(hist[-100:]) / 100
    assert 0.40 <= avg <= 0.60, f"hawk fraction {avg:.3f} not near ESS 0.5"


def test_moran_drives_hawk_dove_to_ess_from_hawks() -> None:
    """Starting from an all-hawk population, selection drives the hawk fraction
    DOWN to the same ESS — convergence from both sides (frequency-dependence)."""
    hist = _run_hawk_dove(start_strategy=1, seed=1)
    avg = sum(hist[-100:]) / 100
    assert 0.40 <= avg <= 0.60, f"hawk fraction {avg:.3f} not near ESS 0.5"


def test_constant_death_path_holds_population() -> None:
    """The constant death model (not exercised by Yaman's Gompertz) holds N."""
    hist = _run_hawk_dove(start_strategy=0, seed=2)
    assert len(hist) == 300
