"""Faithful-rule + determinism tests for the Tag-based cooperation
(Riolo-Cohen-Axelrod 2001) reproduction.

These pin the donation predicate, the vectorised donation/payoff arithmetic (against a
pure-Python reference), the tournament-selection rule, the mutation bounds (tag reflected
into [0,1], tolerance truncated at 0, mutation only with the given rate), the
dominant-cluster-share metric, the crash-and-recover event detector, the summary /
multi-seed drivers, parameter validation, and determinism (same seed -> identical run).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(donation-rate band, dominant cluster, intermittent waves) are evaluated by
examples/repro_tag_cooperation/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.tag_cooperation import (
    TagAgent,
    TagCooperationModel,
    donates,
    donation_rate_reference,
    has_crash_and_recover,
    run_many_seeds,
    run_single,
    summarize_run,
    _reflect_unit_interval,
)


# -- donation predicate -------------------------------------------------------

def test_donation_predicate_within_and_outside_tolerance():
    # recipient tag exactly at the tolerance edge -> donates (<=); just beyond -> not.
    assert donates(0.5, 0.1, 0.55) is True          # |0.55-0.5|=0.05 <= 0.1
    assert donates(0.5, 0.1, 0.60) is True           # |0.10| == tolerance -> donates
    assert donates(0.5, 0.1, 0.61) is False          # |0.11| > tolerance
    assert donates(0.5, 0.0, 0.5) is True            # zero tolerance: only exact tag
    assert donates(0.5, 0.0, 0.5001) is False


# -- vectorised donation arithmetic == pure-Python reference ------------------

def test_donation_rate_matches_reference():
    # Build a model, capture the exact partner assignment its RNG produces, and check
    # the model's realized donation rate equals the pure-Python reference on those pairs.
    m = TagCooperationModel(n=30, seed=3, generations=0)
    n, P = m.n, m.pairings
    # reproduce the model's recipient draw deterministically from a fresh generator with
    # the SAME seed AFTER the two initial U[0,1] draws (tau, tol) the ctor consumed.
    g = np.random.default_rng(3)
    _ = g.random(n)   # tau draw (already consumed by ctor)
    _ = g.random(n)   # tol draw
    offsets = g.integers(1, n, size=(n, P))
    recipients = (np.arange(n)[:, None] + offsets) % n

    # the model's donation phase (uses its own generator, now at the same offset)
    m._donate_and_score()
    model_rate = m._last_donation_rate

    ref = donation_rate_reference(m.tau.tolist(), m.tol.tolist(),
                                  [list(row) for row in recipients])
    assert model_rate == pytest.approx(ref)


def test_donors_never_pair_with_themselves():
    m = TagCooperationModel(n=20, seed=1, generations=0)
    n, P = m.n, m.pairings
    g = np.random.default_rng(1)
    _ = g.random(n); _ = g.random(n)
    offsets = g.integers(1, n, size=(n, P))
    recipients = (np.arange(n)[:, None] + offsets) % n
    for i in range(n):
        assert i not in recipients[i], "a donor must never be paired with itself"


def test_payoff_conserves_donation_accounting():
    # Each donation moves benefit to a recipient and costs the donor; total benefit
    # handed out = benefit * (#donations), total cost paid = cost * (#donations).
    m = TagCooperationModel(n=40, seed=7, generations=0, cost=0.1, benefit=1.0)
    fitness = m._donate_and_score()
    n_donations = round(m._last_donation_rate * m.n * m.pairings)
    total = float(np.sum(fitness))
    # sum of fitness = benefit*D - cost*D = (b - c) * D
    assert total == pytest.approx((m.benefit - m.cost) * n_donations, abs=1e-9)


# -- tournament selection -----------------------------------------------------

def test_tournament_copies_the_fitter():
    # Two agents with a huge fitness gap: after reproduction, every agent should be a
    # copy of the fitter one's (tau, tol) (n=2 -> each focal's only opponent is the other).
    m = TagCooperationModel(n=2, seed=0, generations=0)
    m.tau = np.array([0.2, 0.8])
    m.tol = np.array([0.05, 0.95])
    fitness = np.array([10.0, -10.0])   # agent 0 is far fitter
    # zero mutation so the copy is exact
    m.mutation_rate = 0.0
    m._reproduce(fitness)
    assert np.allclose(m.tau, 0.2)      # both slots copy agent 0's tag
    assert np.allclose(m.tol, 0.05)


def test_reproduction_preserves_population_size():
    m = TagCooperationModel(n=50, seed=2, generations=0)
    m._reproduce(m._donate_and_score())
    assert m.tau.shape == (50,)
    assert m.tol.shape == (50,)
    assert len(m.agent_list) == 50


# -- mutation bounds ----------------------------------------------------------

def test_reflect_unit_interval_keeps_tags_in_range():
    x = np.array([-0.03, 0.0, 0.5, 1.0, 1.02, -0.5, 1.4])
    y = _reflect_unit_interval(x)
    assert np.all(y >= 0.0) and np.all(y <= 1.0)
    # reflection: -0.03 -> 0.03 ; 1.02 -> 0.98
    assert y[0] == pytest.approx(0.03)
    assert y[4] == pytest.approx(0.98)
    # values already in range are unchanged
    assert y[2] == pytest.approx(0.5)
    assert y[3] == pytest.approx(1.0)


def test_tolerance_never_negative_after_reproduction():
    m = TagCooperationModel(n=60, seed=5, generations=0, mutation_rate=1.0,
                            mutation_sigma=0.5)   # heavy mutation to stress the bound
    m.tol = np.zeros(60)                          # all at the boundary
    m._reproduce(m._donate_and_score())
    assert np.all(m.tol >= 0.0)


def test_tags_stay_in_unit_interval_over_a_short_run():
    m = TagCooperationModel(n=50, seed=9, generations=200)
    m.run()
    assert np.all(m.tau >= 0.0) and np.all(m.tau <= 1.0)
    assert np.all(m.tol >= 0.0)


def test_zero_mutation_rate_makes_no_mutations():
    m = TagCooperationModel(n=30, seed=4, generations=0, mutation_rate=0.0)
    # force a lopsided fitness so tournament winners are well-defined, then check the
    # new population is exactly a re-selection of old rows (no perturbation).
    fitness = np.arange(30, dtype=float)
    before_unique = set(np.round(m.tau, 12))
    m._reproduce(fitness)
    after_unique = set(np.round(m.tau, 12))
    # with zero mutation, every new tag value must have existed in the old population
    assert after_unique.issubset(before_unique)


# -- cluster-share metric -----------------------------------------------------

def test_cluster_share_all_identical_is_one():
    m = TagCooperationModel(n=100, seed=0, generations=0)
    m.tau = np.full(100, 0.42)
    assert m.dominant_cluster_share() == pytest.approx(1.0)


def test_cluster_share_uniform_spread_is_small():
    m = TagCooperationModel(n=100, seed=0, generations=0, cluster_eps=0.01)
    m.tau = np.linspace(0.0, 1.0, 100)   # evenly spread across [0,1]
    # a 2*eps=0.02-wide band around the modal bin holds only ~2-3 of 100 agents
    assert m.dominant_cluster_share() < 0.1


# -- crash-and-recover detector -----------------------------------------------

def test_crash_and_recover_detects_a_wave():
    # a plateau at 0.7 that drops to 0.1 (below 0.5x mean) then recovers to 0.75
    series = [0.7] * 50 + [0.1] * 5 + [0.75] * 50
    assert has_crash_and_recover(series, window=50) is True


def test_no_crash_on_a_flat_plateau():
    series = [0.7 + 0.001 * (i % 3) for i in range(300)]   # tiny jitter, no crash
    assert has_crash_and_recover(series, window=100) is False


# -- summary + multi-seed drivers ---------------------------------------------

def test_summarize_run_shape():
    res = run_single(n=40, seed=0, generations=300)
    summ = summarize_run(res, burn_in=50, cv_window=100)
    assert 0.0 <= summ["mean_donation_rate"] <= 1.0
    assert 0.0 <= summ["mean_cluster_share"] <= 1.0
    assert summ["cv_donation_rate"] >= 0.0
    assert isinstance(summ["has_crash_recover"], (bool, np.bool_))


def test_run_series_length_is_one_per_generation():
    res = run_single(n=30, seed=0, generations=120)
    assert len(res["donation_rate_series"]) == 120
    assert len(res["cluster_share_series"]) == 120
    assert len(res["mean_tolerance_series"]) == 120


def test_run_many_seeds_aggregates():
    agg = run_many_seeds([0, 1, 2], n=40, generations=200, burn_in=50, cv_window=100)
    assert agg["seeds"] == [0, 1, 2]
    assert len(agg["rows"]) == 3
    assert 0.0 <= agg["mean_donation_rate"] <= 1.0
    assert 0.0 <= agg["frac_seeds_crash_recover"] <= 1.0
    assert agg["example_series"] is not None
    assert len(agg["example_series"]["donation_rate_series"]) == 200


# -- parameter validation -----------------------------------------------------

def test_invalid_params_raise():
    with pytest.raises(ValueError):
        TagCooperationModel(n=1)                       # need n > 1
    with pytest.raises(ValueError):
        TagCooperationModel(n=10, pairings=0)
    with pytest.raises(ValueError):
        TagCooperationModel(n=10, cost=-0.1)
    with pytest.raises(ValueError):
        TagCooperationModel(n=10, mutation_rate=1.5)
    with pytest.raises(ValueError):
        TagCooperationModel(n=10, mutation_sigma=-0.01)
    with pytest.raises(ValueError):
        TagCooperationModel(n=10, generations=-1)


# -- population invariants ----------------------------------------------------

def test_population_is_tag_agents_with_traits_in_range():
    m = TagCooperationModel(n=100, seed=0, generations=0)
    assert len(m.agent_list) == 100
    assert all(isinstance(a, TagAgent) for a in m.agent_list)
    for a in m.agent_list:
        assert 0.0 <= a.tau <= 1.0
        assert a.tolerance >= 0.0


def test_roster_mirrors_arrays_after_a_generation():
    m = TagCooperationModel(n=20, seed=1, generations=0)
    m.step()
    for i, a in enumerate(m.agent_list):
        assert a.tau == pytest.approx(float(m.tau[i]))
        assert a.tolerance == pytest.approx(float(m.tol[i]))


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_run():
    a = run_single(n=50, seed=42, generations=300)
    b = run_single(n=50, seed=42, generations=300)
    assert a["donation_rate_series"] == b["donation_rate_series"]
    assert a["cluster_share_series"] == b["cluster_share_series"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=50, seed=1, generations=200)
    b = run_single(n=50, seed=2, generations=200)
    for res in (a, b):
        assert all(0.0 <= x <= 1.0 for x in res["donation_rate_series"])
        assert all(0.0 <= x <= 1.0 for x in res["cluster_share_series"])
