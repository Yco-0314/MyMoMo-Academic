"""Faithful-rule + determinism + analytic-anchor tests for the spatial
rock-paper-scissors (cyclic dominance) reproduction.

These pin the cyclic-dominance map (R>S>P>R), the three reaction rules (predation empties
the prey; reproduction fills an empty cell; exchange swaps), the locality difference
between the spatial and well-mixed arms, determinism (same seed -> identical run), and a
qualitative coexistence-vs-extinction sanity check on small grids. They are faithfulness
tests, NOT prediction tests (the locked predictions P1-P3 are evaluated by
examples/repro_rock_paper_scissors/run.py).

This IS a genuine agent-based model: one SiteAgent per cell, driven by the AgentSet
scheduler; each step is one MC event from that site's neighbourhood.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.rock_paper_scissors import (
    EMPTY,
    P,
    PREY,
    R,
    RPSModel,
    S,
    SPECIES,
    SiteAgent,
    beats,
    run_many_seeds,
    run_single,
)


# -- cyclic dominance map -----------------------------------------------------

def test_cyclic_dominance_map():
    # R beats S, S beats P, P beats R (and nothing beats its own predator back).
    assert beats(R, S)
    assert beats(S, P)
    assert beats(P, R)
    # The reverse relations are all false (strict cyclic dominance).
    assert not beats(S, R)
    assert not beats(P, S)
    assert not beats(R, P)
    # A species never beats itself; empty is never a predator/prey.
    for sp in SPECIES:
        assert not beats(sp, sp)
        assert not beats(sp, EMPTY)
        assert not beats(EMPTY, sp)
    # PREY is a 3-cycle.
    assert PREY[R] == S and PREY[S] == P and PREY[P] == R


# -- reaction rules (predation / reproduction / exchange) ---------------------

def _model(L=5, **kw):
    """A tiny model; we overwrite the lattice by hand to test single events. Rates are
    overridden per-test so the categorical draw lands on the reaction under test."""
    m = RPSModel(L=L, seed=0, n_gen=0, **kw)
    return m


def test_predation_empties_the_prey_focal_is_predator():
    # sigma only -> the event is always PREDATION. Place predator at focal, prey to the
    # right; force the partner to be the right neighbour and the reaction draw to selection.
    m = _model(sigma=1.0, mu=0.0, epsilon=0.0)
    m.lattice[:] = EMPTY
    m.lattice[2, 2] = R   # rock (predator of scissors)
    m.lattice[2, 3] = S   # scissors (prey)
    # Force partner = right neighbour, reaction = selection (u < cum[0] = 1.0 always here).
    m._partner = lambda r, c: (2, 3)
    m._np_rng = _FixedRng(uniform=0.0)
    m.event(2, 2)
    assert m.lattice[2, 2] == R       # predator survives
    assert m.lattice[2, 3] == EMPTY   # prey consumed -> empty


def test_predation_empties_the_prey_focal_is_prey():
    # Symmetric: focal is the PREY, neighbour is the predator -> focal dies.
    m = _model(sigma=1.0, mu=0.0, epsilon=0.0)
    m.lattice[:] = EMPTY
    m.lattice[2, 2] = S   # scissors (prey of rock)
    m.lattice[2, 3] = R   # rock (predator)
    m._partner = lambda r, c: (2, 3)
    m._np_rng = _FixedRng(uniform=0.0)
    m.event(2, 2)
    assert m.lattice[2, 2] == EMPTY   # focal prey consumed
    assert m.lattice[2, 3] == R       # predator survives


def test_predation_noop_between_same_species():
    m = _model(sigma=1.0, mu=0.0, epsilon=0.0)
    m.lattice[:] = EMPTY
    m.lattice[2, 2] = R
    m.lattice[2, 3] = R   # same species: no predation
    m._partner = lambda r, c: (2, 3)
    m._np_rng = _FixedRng(uniform=0.0)
    m.event(2, 2)
    assert m.lattice[2, 2] == R and m.lattice[2, 3] == R  # unchanged


def test_reproduction_fills_empty_neighbour():
    # mu only -> the event is always REPRODUCTION. Species fills an adjacent empty cell.
    m = _model(sigma=0.0, mu=1.0, epsilon=0.0)
    m.lattice[:] = EMPTY
    m.lattice[2, 2] = P   # paper, focal
    m.lattice[2, 3] = EMPTY
    m._partner = lambda r, c: (2, 3)
    m._np_rng = _FixedRng(uniform=0.5)
    m.event(2, 2)
    assert m.lattice[2, 2] == P
    assert m.lattice[2, 3] == P   # offspring of the same species


def test_reproduction_into_empty_focal_from_neighbour():
    m = _model(sigma=0.0, mu=1.0, epsilon=0.0)
    m.lattice[:] = EMPTY
    m.lattice[2, 2] = EMPTY  # focal empty
    m.lattice[2, 3] = S      # scissors neighbour reproduces into focal
    m._partner = lambda r, c: (2, 3)
    m._np_rng = _FixedRng(uniform=0.5)
    m.event(2, 2)
    assert m.lattice[2, 2] == S
    assert m.lattice[2, 3] == S


def test_reproduction_noop_when_no_empty_cell():
    m = _model(sigma=0.0, mu=1.0, epsilon=0.0)
    m.lattice[:] = EMPTY
    m.lattice[2, 2] = R
    m.lattice[2, 3] = P   # neither empty -> reproduction does nothing
    m._partner = lambda r, c: (2, 3)
    m._np_rng = _FixedRng(uniform=0.5)
    m.event(2, 2)
    assert m.lattice[2, 2] == R and m.lattice[2, 3] == P


def test_exchange_swaps_the_two_cells():
    # epsilon only -> the event is always EXCHANGE. The two cells swap contents.
    m = _model(sigma=0.0, mu=0.0, epsilon=1.0)
    m.lattice[:] = EMPTY
    m.lattice[2, 2] = R
    m.lattice[2, 3] = EMPTY
    m._partner = lambda r, c: (2, 3)
    m._np_rng = _FixedRng(uniform=0.9)
    m.event(2, 2)
    assert m.lattice[2, 2] == EMPTY  # swapped with the empty neighbour (mobility into a hole)
    assert m.lattice[2, 3] == R


def test_exchange_swaps_two_species():
    m = _model(sigma=0.0, mu=0.0, epsilon=1.0)
    m.lattice[:] = EMPTY
    m.lattice[2, 2] = R
    m.lattice[2, 3] = P
    m._partner = lambda r, c: (2, 3)
    m._np_rng = _FixedRng(uniform=0.9)
    m.event(2, 2)
    assert m.lattice[2, 2] == P and m.lattice[2, 3] == R


# -- neighbour / partner selection (the locality difference) -------------------

def test_local_neighbour_is_von_neumann_adjacent_periodic():
    m = _model(L=5, well_mixed=False)
    seen = set()
    # Draw many neighbours of (0,0); all must be the 4 periodic von-Neumann neighbours.
    rng = np.random.default_rng(1)
    m._np_rng = rng
    for _ in range(200):
        seen.add(m._random_neighbour(0, 0))
    expected = {(4, 0), (1, 0), (0, 4), (0, 1)}  # up/down/left/right with wraparound
    assert seen == expected


def test_well_mixed_partner_can_be_far():
    m = _model(L=5, well_mixed=True)
    rng = np.random.default_rng(2)
    m._np_rng = rng
    far = False
    for _ in range(500):
        r, c = m._random_global(2, 2)
        assert (r, c) != (2, 2)                 # never the focal site itself
        if abs(r - 2) + abs(c - 2) > 1:         # a non-adjacent (global) partner appears
            far = True
    assert far


def test_agent_step_delegates_to_model_event():
    m = _model(L=5, sigma=1.0, mu=0.0, epsilon=0.0)
    agent = SiteAgent(0, m, row=1, col=1)
    calls = []
    m.event = lambda r, c: calls.append((r, c))  # type: ignore[assignment]
    agent.step()
    assert calls == [(1, 1)]


# -- determinism --------------------------------------------------------------

def test_same_seed_identical_run():
    a = run_single(L=20, epsilon=0.0, seed=7, n_gen=30)
    b = run_single(L=20, epsilon=0.0, seed=7, n_gen=30)
    assert a["final_fractions"] == b["final_fractions"]
    assert a["fR_series"] == b["fR_series"]
    assert a["n_surviving"] == b["n_surviving"]


def test_different_seeds_can_differ():
    a = run_single(L=20, epsilon=0.0, seed=1, n_gen=30)
    b = run_single(L=20, epsilon=0.0, seed=2, n_gen=30)
    assert a["fR_series"] != b["fR_series"]


def test_well_mixed_and_spatial_differ_same_seed():
    # Same seed, same rules — only locality differs — must produce different trajectories.
    sp = run_single(L=20, epsilon=0.0, well_mixed=False, seed=3, n_gen=30)
    wm = run_single(L=20, epsilon=0.0, well_mixed=True, seed=3, n_gen=30)
    assert sp["fR_series"] != wm["fR_series"]


# -- fractions / bookkeeping ---------------------------------------------------

def test_fractions_and_empty_sum_to_one():
    r = run_single(L=20, epsilon=0.0, seed=0, n_gen=20)
    ff = r["final_fractions"]
    total = ff["R"] + ff["P"] + ff["S"] + r["final_empty_fraction"]
    assert total == pytest.approx(1.0, abs=1e-9)


def test_n_surviving_counts_present_species():
    m = _model(L=10)
    m.lattice[:] = R          # only rocks present
    assert m.n_surviving() == 1
    m.lattice[0, 0] = S
    assert m.n_surviving() == 2
    m.lattice[0, 1] = P
    assert m.n_surviving() == 3


def test_rejects_bad_params():
    with pytest.raises(ValueError):
        RPSModel(L=0)
    with pytest.raises(ValueError):
        RPSModel(L=10, sigma=-1.0)
    with pytest.raises(ValueError):
        RPSModel(L=10, sigma=0.0, mu=0.0, epsilon=0.0)


# -- coexistence-vs-extinction sanity (small grid, qualitative) ----------------

def test_spatial_coexists_more_than_well_mixed_small():
    # On a modest grid over a long-ish run, the LOCAL arm preserves more species than the
    # WELL-MIXED arm averaged over a few seeds. This is the qualitative direction of the
    # locked P3 contrast (the runner does the full L=100 long-run grading).
    sp = run_many_seeds(L=30, epsilon=0.0, well_mixed=False, n_seeds=5, n_gen=300)
    wm = run_many_seeds(L=30, epsilon=0.0, well_mixed=True, n_seeds=5, n_gen=300)
    assert sp["mean_n_surviving"] > wm["mean_n_surviving"]
    # The well-mixed arm should lose biodiversity in at least one seed.
    assert wm["min_n_surviving"] < 3


# -- a tiny deterministic fixed-RNG stub for single-event reaction tests -------

class _FixedRng:
    """A minimal stand-in for numpy's Generator that returns a fixed uniform for
    ``random()`` (so we can land the categorical reaction draw deterministically in the
    single-event tests). ``integers`` is unused on these paths (partner is monkeypatched)."""

    def __init__(self, *, uniform: float) -> None:
        self._u = uniform

    def random(self, *args, **kwargs):
        return self._u

    def integers(self, *args, **kwargs):  # pragma: no cover - not exercised
        return 0
