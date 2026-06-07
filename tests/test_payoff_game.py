"""Tests for PayoffGame (ADR-014 Phase 2) + its two cross-domain adapters.

Library: the ordered/dual payoff (what RuleTable cannot represent), best-response,
named games. Then "two adapters = a real seam" via the COMPOSITION that justified
building it — PayoffGame x MoranProcess = evolutionary game theory — on two games
with different equilibrium structure: Prisoner's Dilemma (defectors fixate) and
Hawk-Dove (polymorphic mixed ESS). One operator, two game classes.
"""
from __future__ import annotations

import random

from abm_auto.runtime import MoranProcess, PayoffGame
from abm_auto.runtime._payoff_game import self_test


# ── library ────────────────────────────────────────────────────────────────


def test_self_test_passes() -> None:
    assert self_test() is True


def test_ordered_dual_payoff_rule_table_cannot() -> None:
    pd = PayoffGame.prisoners_dilemma()           # 0=C 1=D
    assert pd.play(0, 1) == (0.0, 5.0)            # cooperator S=0, defector T=5
    assert pd.play(1, 0) == (5.0, 0.0)            # order matters
    assert pd.payoff(0, 1) != pd.payoff(1, 0)     # NOT order-free


def test_best_response_dominant_and_cyclic() -> None:
    pd = PayoffGame.prisoners_dilemma()
    assert pd.best_response(0) == 1 and pd.best_response(1) == 1   # defect dominates
    rps = PayoffGame.rock_paper_scissors()
    assert (rps.best_response(0), rps.best_response(1), rps.best_response(2)) == (1, 2, 0)


def test_non_square_rejected() -> None:
    import pytest
    with pytest.raises(ValueError):
        PayoffGame([[1, 2, 3], [4, 5, 6]])


def test_from_matrix_roundtrip() -> None:
    g = PayoffGame.from_matrix([[2, 0], [3, 1]])
    assert g.n_strategies == 2 and g.payoff(1, 0) == 3.0


# ── adapters: PayoffGame x MoranProcess = evolutionary game theory ───────────


def _evolve(game: PayoffGame, *, start_p: float, seed: int,
            N: int = 200, gens: int = 250, mu: float = 0.02, baseline: float = 1.0):
    """Well-mixed replicator-ish dynamics via the operators: mean-field payoff
    (PayoffGame) → fitness → Moran turnover (MoranProcess). Returns the
    strategy-1 fraction history."""
    rng = random.Random(seed)

    class _A:
        __slots__ = ("strategy", "score", "age")

    pop = []
    for _ in range(N):
        a = _A()
        a.strategy = 1 if rng.random() < start_p else 0
        a.score = baseline
        a.age = 0
        pop.append(a)

    moran = MoranProcess(fitness_attr="score", death_model="constant",
                         death_rate=0.25, seed=seed)

    def inherit(child, parent):
        s = parent.strategy
        if rng.random() < mu:
            s = 1 - s
        child.strategy = s
        child.score = baseline

    hist = []
    for _ in range(gens):
        p = sum(a.strategy for a in pop) / len(pop)            # strategy-1 fraction
        # mean-field expected payoff of each strategy at mix p
        pay0 = (1 - p) * game.payoff(0, 0) + p * game.payoff(0, 1)
        pay1 = (1 - p) * game.payoff(1, 0) + p * game.payoff(1, 1)
        for a in pop:
            a.score = baseline + (pay1 if a.strategy == 1 else pay0)
        moran.turnover(pop, inherit=inherit, rng=rng)
        assert len(pop) == N
        hist.append(p)
    return hist


def test_prisoners_dilemma_defectors_fixate() -> None:
    """PD: defect is dominant → from a cooperator-majority start, the SAME
    operator pair drives defectors (strategy 1) to fixation."""
    hist = _evolve(PayoffGame.prisoners_dilemma(), start_p=0.1, seed=0)
    assert sum(hist[-50:]) / 50 > 0.85           # defectors took over


def test_hawk_dove_reaches_mixed_ess() -> None:
    """Hawk-Dove (V=2,C=4 → ESS hawks = 0.5): the SAME operator pair converges to
    a POLYMORPHIC equilibrium, not fixation — a different game class, same seam."""
    hist = _evolve(PayoffGame.hawk_dove(V=2, C=4), start_p=0.1, seed=1)
    assert 0.40 <= sum(hist[-50:]) / 50 <= 0.60
