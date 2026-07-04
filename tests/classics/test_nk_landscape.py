"""Faithful-rule + determinism tests for the Kauffman NK landscape (Kauffman & Levin
1987) reproduction.

These pin the NK construction (N binary loci, each contribution depending on its locus +
K others, a seed-keyed U[0,1] contribution table, fitness = mean of the N contributions),
the local-optimum definition (fitness >= all N 1-flip neighbours), the greedy
steepest-ascent adaptive walk (move to the fittest STRICTLY-fitter neighbour, halt at an
optimum), and determinism (same landscape seed -> identical landscape, counts, and walks).
They are faithfulness tests, NOT prediction tests (the locked predictions P1-P3 are
evaluated by examples/repro_nk_landscape/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.nk_landscape import (
    AdaptiveWalkModel,
    NKLandscape,
    WalkerAgent,
    _code_to_genotype,
    _genotype_to_code,
    mean_walk_length,
    measure_k,
    run_walk,
)


# -- encoding helpers ---------------------------------------------------------

def test_code_genotype_roundtrip():
    for code in [0, 1, 2, 100, 12345, 32767]:
        g = _code_to_genotype(code, 15)
        assert len(g) == 15
        assert all(b in (0, 1) for b in g)
        assert _genotype_to_code(g) == code


def test_bit_i_maps_to_locus_i():
    # code 1 -> only locus 0 set; code 2 -> only locus 1 set.
    assert _code_to_genotype(1, 15)[0] == 1
    assert sum(_code_to_genotype(1, 15)) == 1
    assert _code_to_genotype(2, 15)[1] == 1
    assert sum(_code_to_genotype(2, 15)) == 1


# -- landscape construction + epistasis wiring --------------------------------

def test_each_locus_depends_on_K_other_loci():
    n, k = 15, 4
    land = NKLandscape(n, k, seed=0)
    assert len(land.deps) == n
    for i in range(n):
        assert len(land.deps[i]) == k          # K *other* dependencies
        assert i not in land.deps[i]           # locus itself is implicit, not in deps
        assert len(set(land.deps[i])) == k      # distinct
        assert all(0 <= j < n for j in land.deps[i])


def test_K0_has_no_epistasis():
    land = NKLandscape(15, 0, seed=0)
    assert all(deps == () for deps in land.deps)


def test_rejects_bad_N_and_K():
    with pytest.raises(ValueError):
        NKLandscape(0, 0, seed=0)              # N must be positive
    with pytest.raises(ValueError):
        NKLandscape(15, 15, seed=0)            # K must be <= N-1
    with pytest.raises(ValueError):
        NKLandscape(15, -1, seed=0)            # K must be >= 0


# -- contributions: seed-keyed, deterministic, in [0,1] -----------------------

def test_contribution_in_unit_interval():
    land = NKLandscape(15, 4, seed=0)
    g = tuple([0, 1] * 7 + [0])
    for i in range(15):
        f = land.locus_fitness(g, i)
        assert 0.0 <= f < 1.0


def test_fitness_is_mean_of_locus_contributions():
    land = NKLandscape(15, 4, seed=0)
    g = tuple([1, 0] * 7 + [1])
    expected = sum(land.locus_fitness(g, i) for i in range(15)) / 15
    assert land.fitness(g) == pytest.approx(expected)
    assert 0.0 <= land.fitness(g) <= 1.0


def test_fitness_rejects_wrong_length_genotype():
    land = NKLandscape(15, 4, seed=0)
    with pytest.raises(ValueError):
        land.fitness((0, 1, 0))


def test_contribution_depends_only_on_relevant_bits():
    # Flipping a locus that is NEITHER locus i NOR one of i's K dependencies must NOT
    # change f_i. Flipping locus i (or a dependency) generally changes it.
    land = NKLandscape(15, 2, seed=1)
    g = [0] * 15
    i = 0
    relevant = {i} | set(land.deps[i])
    irrelevant = next(j for j in range(15) if j not in relevant)
    f_before = land.locus_fitness(tuple(g), i)
    g2 = list(g)
    g2[irrelevant] ^= 1
    assert land.locus_fitness(tuple(g2), i) == f_before   # irrelevant flip -> unchanged
    g3 = list(g)
    g3[i] ^= 1
    # own-locus flip changes the relevant substring -> a different (independent) draw
    assert land.locus_fitness(tuple(g3), i) != f_before


# -- determinism of the landscape ---------------------------------------------

def test_same_seed_identical_landscape():
    a = NKLandscape(15, 4, seed=7)
    b = NKLandscape(15, 4, seed=7)
    assert a.deps == b.deps
    g = tuple([0, 1, 1, 0] * 3 + [1, 0, 1])
    assert a.fitness(g) == b.fitness(g)


def test_different_seed_differs():
    a = NKLandscape(15, 4, seed=1)
    b = NKLandscape(15, 4, seed=2)
    # wiring or contributions almost surely differ; at least one must.
    g = tuple([0, 1] * 7 + [0])
    assert (a.deps != b.deps) or (a.fitness(g) != b.fitness(g))


# -- local optima -------------------------------------------------------------

def test_neighbours_are_the_N_single_flips():
    land = NKLandscape(15, 4, seed=0)
    g = tuple([0] * 15)
    nbs = land.neighbours(g)
    assert len(nbs) == 15
    # each neighbour differs from g in exactly one bit
    for nb in nbs:
        assert sum(1 for a, b in zip(g, nb) if a != b) == 1
    assert len(set(nbs)) == 15


def test_local_optimum_definition():
    land = NKLandscape(15, 4, seed=0)
    g = tuple([0, 1] * 7 + [0])
    f = land.fitness(g)
    expected = all(f >= land.fitness(nb) for nb in land.neighbours(g))
    assert land.is_local_optimum(g) == expected


def test_K0_has_exactly_one_global_optimum():
    # The additive (K=0) landscape is single-peaked: enumerating finds exactly 1 optimum.
    land = NKLandscape(15, 0, seed=3)
    res = land.count_local_optima()
    assert res["n_optima"] == 1


def test_count_local_optima_reports_random_expectation():
    land = NKLandscape(15, 4, seed=0)
    res = land.count_local_optima()
    assert res["random_expectation"] == pytest.approx((1 << 15) / 16)  # 2048
    assert 1 <= res["n_optima"] <= (1 << 15)
    # every reported optimum is genuinely a local optimum
    for code in res["optima_codes"][:5]:
        assert land.is_local_optimum(_code_to_genotype(code, 15))


# -- the greedy adaptive walk -------------------------------------------------

def test_walk_ends_at_a_local_optimum():
    land = NKLandscape(15, 4, seed=0)
    res = run_walk(land, seed=11)
    assert res["at_optimum"] is True
    assert res["end_is_local_optimum"] is True
    assert res["walk_length"] >= 0


def test_walk_fitness_strictly_increases_along_the_walk():
    # A greedy steepest-ascent walk only moves to a STRICTLY-fitter neighbour, so the end
    # fitness must be >= the start fitness (and > when at least one move was taken).
    land = NKLandscape(15, 4, seed=2)
    res = run_walk(land, seed=5)
    assert res["end_fitness"] >= res["start_fitness"]
    if res["walk_length"] > 0:
        assert res["end_fitness"] > res["start_fitness"]


def test_walk_from_an_optimum_has_length_zero():
    land = NKLandscape(15, 4, seed=0)
    opt = land.count_local_optima()["optima_codes"][0]
    start = _code_to_genotype(opt, 15)
    model = AdaptiveWalkModel(land, start=start)
    res = model.run()
    assert res["walk_length"] == 0
    assert res["end_code"] == opt


def test_walker_moves_to_fittest_strictly_fitter_neighbour():
    land = NKLandscape(15, 2, seed=0)
    model = AdaptiveWalkModel(land, start=tuple([0] * 15))
    walker = model.walker
    assert isinstance(walker, WalkerAgent)
    nxt = walker.best_fitter_neighbour()
    if nxt is not None:
        f0 = land.fitness(walker.genotype)
        fn = land.fitness(nxt)
        assert fn > f0
        # it is the fittest among all strictly-fitter neighbours
        fitter = [nb for nb in land.neighbours(walker.genotype)
                  if land.fitness(nb) > f0]
        assert fn == max(land.fitness(nb) for nb in fitter)


def test_walk_respects_explicit_start_length():
    land = NKLandscape(15, 4, seed=0)
    with pytest.raises(ValueError):
        AdaptiveWalkModel(land, start=(0, 1, 0))


# -- determinism of walks -----------------------------------------------------

def test_walk_determinism_same_seed_same_landscape():
    land = NKLandscape(15, 4, seed=0)
    a = run_walk(land, seed=42)
    b = run_walk(land, seed=42)
    assert a["start_code"] == b["start_code"]
    assert a["end_code"] == b["end_code"]
    assert a["walk_length"] == b["walk_length"]


def test_mean_walk_length_repeatable():
    land = NKLandscape(15, 4, seed=0)
    a = mean_walk_length(land, n_walks=50, seed_base=0)
    b = mean_walk_length(land, n_walks=50, seed_base=0)
    assert a["mean_walk_length"] == b["mean_walk_length"]
    assert a["lengths"] == b["lengths"]


def test_measure_k_determinism():
    a = measure_k(15, 2, n_landscapes=3, n_walks=20)
    b = measure_k(15, 2, n_landscapes=3, n_walks=20)
    assert a["mean_n_optima"] == b["mean_n_optima"]
    assert a["mean_walk_length"] == b["mean_walk_length"]


# -- loose Monte-Carlo / structural sanity (locked grade lives in run.py) -----

def test_more_K_gives_more_optima_small_sanity():
    # K=8 has many more optima than K=0 (=1) on the same seed family. Loose sanity; the
    # locked monotonicity grade over the full grid is in run.py.
    low = measure_k(15, 0, n_landscapes=3, n_walks=10)
    high = measure_k(15, 8, n_landscapes=3, n_walks=10)
    assert low["mean_n_optima"] == 1.0
    assert high["mean_n_optima"] > low["mean_n_optima"]


def test_more_K_gives_shorter_walks_small_sanity():
    low = measure_k(15, 0, n_landscapes=3, n_walks=30)
    high = measure_k(15, 8, n_landscapes=3, n_walks=30)
    assert high["mean_walk_length"] < low["mean_walk_length"]


def test_K_equals_N_minus_1_near_random_expectation():
    # At K=N-1 the landscape is effectively random: #optima ~ 2^N/(N+1) = 2048. Allow a
    # generous +-25% band (loose sanity; this is a known analytic anchor).
    m = measure_k(15, 14, n_landscapes=5, n_walks=10)
    exp = (1 << 15) / 16
    assert 0.75 * exp <= m["mean_n_optima"] <= 1.25 * exp
