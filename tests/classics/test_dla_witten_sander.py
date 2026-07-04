"""Faithful-rule + determinism tests for the on-lattice DLA (Witten-Sander 1981) reproduction.

These pin the seed, the nearest-neighbour sticking rule, the NO-OVERLAP invariant (guaranteed by the
lattice), the enclosed-mass fractal-dimension fit, and determinism. They are faithfulness tests, NOT
prediction tests — the locked P1-P3 (D in [1.55,1.90], fractal not compact, tip-screening) are
evaluated by examples/repro_dla_witten_sander/run.py.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.dla_witten_sander import DLAModel, run_single


def test_seed_at_origin():
    m = DLAModel(n=5, seed=0)
    assert (0, 0) in m.occupied
    assert m.xs[0] == 0 and m.ys[0] == 0
    assert m.size == 1  # only the seed before growth


def test_touches_cluster_rule():
    m = DLAModel(n=5, seed=0)
    # a von-Neumann neighbour of the seed touches; a diagonal / far cell does not.
    assert m._touches_cluster(1, 0)
    assert m._touches_cluster(0, -1)
    assert not m._touches_cluster(1, 1)     # diagonal is not a von-Neumann contact
    assert not m._touches_cluster(5, 5)


def test_grow_adds_particles_no_overlap():
    m = DLAModel(n=200, seed=1)
    m.grow()
    assert m.size == 200
    # NO OVERLAP: every stuck cell is distinct (a set can't hold duplicates, and the count matches).
    assert len(m.occupied) == 200
    assert len(set(zip(m.xs, m.ys))) == 200
    # every non-seed particle is adjacent (contact distance = one lattice step) to the cluster:
    for idx in range(1, m.size):
        i, j = m.xs[idx], m.ys[idx]
        nbrs = [(i + di, j + dj) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        assert any(nb in m.occupied for nb in nbrs)


def test_all_particles_at_least_contact_apart():
    # On the lattice, no two occupied cells coincide, so the min centre-to-centre distance is >= 1
    # (the contact distance) — the invariant the off-lattice version struggled with.
    m = DLAModel(n=150, seed=3)
    m.grow()
    cells = list(zip(m.xs, m.ys))
    for a in range(len(cells)):
        xi, yi = cells[a]
        best = min(math.hypot(xi - cells[b][0], yi - cells[b][1])
                   for b in range(len(cells)) if b != a)
        assert best >= m.contact - 1e-9   # contact == 1 lattice step


def test_mass_dimension_of_compact_disk_is_about_two():
    # A hand-built FILLED disk (compact) must read mass dimension ~2, not fractal.
    m = DLAModel(n=1, seed=0)
    R = 30
    for i in range(-R, R + 1):
        for j in range(-R, R + 1):
            if i * i + j * j <= R * R:
                m._add((i, j))
    md = m.mass_dimension()
    assert md["D"] == pytest.approx(2.0, abs=0.15)   # compact -> D ~ 2


def test_dla_cluster_is_fractal_below_two():
    r = run_single(n=3000, seed=2)
    assert 1.4 <= r["D"] <= 1.95          # fractal, clearly below the compact 2.0
    assert r["D_r2"] > 0.9                 # clean power law


def test_determinism_same_seed():
    a = run_single(n=800, seed=7)
    b = run_single(n=800, seed=7)
    assert a["D"] == b["D"]
    assert a["r_max"] == b["r_max"]
    assert a["outer_shell_fraction"] == b["outer_shell_fraction"]


def test_outer_shell_fraction_in_range():
    r = run_single(n=1500, seed=1)
    assert 0.0 <= r["outer_shell_fraction"] <= 1.0
