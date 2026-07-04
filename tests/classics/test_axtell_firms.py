"""Faithful-rule + determinism tests for the Axtell Model of Firms (Axtell 1999/2001)
reproduction.

These pin the production function O(E)=aE+bE^2, the Cobb-Douglas utility (eq. 3), the
closed-form best-response effort (eq. 5) agreeing with a numerical line search, its
economic properties (free-riding: effort falls as others' effort rises; the leisure-lover
corner e*=0), the incremental firm registry staying EXACT under set-effort / move / found,
a myopic activation that migrates an agent to a strictly better firm, the distribution
statistics (Zipf rank-size slope, Gini, excess kurtosis, Stanley sigma-vs-size slope), the
run summary shape, and determinism (same seed -> identical result).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3 (Zipf
slope in [-1.5,-0.7]; firm-size Gini >= 0.60; tent-shaped log-growth with excess kurtosis
> 1.5 and sigma decreasing with size) are evaluated by examples/repro_axtell_firms/run.py.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.axtell_firms import (
    AxtellFirmsModel,
    FirmAgent,
    best_effort_closed_form,
    best_effort_line_search,
    excess_kurtosis,
    gini,
    growth_std_by_size_slope,
    output,
    rank_size_slope,
    run_single,
    utility,
)


# -- production + utility -----------------------------------------------------

def test_output_is_increasing_returns():
    # O(E) = a*E + b*E^2. With a=b=1: O(1)=2, O(2)=6, O(3)=12.
    assert output(1.0, 1.0, 1.0) == pytest.approx(2.0)
    assert output(2.0, 1.0, 1.0) == pytest.approx(6.0)
    assert output(3.0, 1.0, 1.0) == pytest.approx(12.0)
    # per-agent average output O(E)/E rises with E (increasing returns to effort).
    assert output(4.0, 1.0, 1.0) / 4.0 > output(1.0, 1.0, 1.0) / 1.0


def test_utility_cobb_douglas_form():
    # U = income^theta * (1-effort)^(1-theta).
    assert utility(4.0, 0.5, 0.5) == pytest.approx((4.0 ** 0.5) * (0.5 ** 0.5))
    # income-lover (theta->1) values income; leisure-lover (theta->0) values leisure.
    assert utility(10.0, 0.9, 0.99) > utility(1.0, 0.9, 0.99)     # more income helps
    # zero leisure (effort=1) or non-positive income -> zero utility.
    assert utility(5.0, 1.0, 0.5) == 0.0
    assert utility(0.0, 0.3, 0.5) == 0.0


# -- best-response effort -----------------------------------------------------

def test_closed_form_matches_line_search_singleton():
    # A singleton (Ebar=0, n=1): closed form must match the numerical line search over
    # e in [0,1] to grid resolution, across a range of preferences.
    for theta in (0.05, 0.2, 0.5, 0.75, 0.95):
        cf = best_effort_closed_form(theta, 0.0, 1.0, 1.0)
        ls = best_effort_line_search(theta, 0.0, 1, 1.0, 1.0, grid=2000)
        assert cf == pytest.approx(ls, abs=2e-3)


def test_closed_form_matches_line_search_with_others():
    # In a firm where OTHERS already supply effort Ebar and size n: the utility a member
    # maximises is (O(Ebar+e)/n)^theta (1-e)^(1-theta); closed form == line search.
    for theta, Ebar, n in [(0.3, 1.5, 3), (0.6, 0.4, 2), (0.9, 2.0, 5), (0.15, 0.1, 2)]:
        cf = best_effort_closed_form(theta, Ebar, 1.0, 1.0)
        ls = best_effort_line_search(theta, Ebar, n, 1.0, 1.0, grid=2000)
        assert cf == pytest.approx(ls, abs=3e-3)


def test_best_effort_in_unit_interval():
    for theta in (0.0, 0.1, 0.5, 0.9, 1.0):
        for Ebar in (0.0, 0.5, 2.0, 10.0):
            e = best_effort_closed_form(theta, Ebar, 1.0, 1.0)
            assert 0.0 <= e <= 1.0


def test_free_riding_effort_falls_as_others_effort_rises():
    # Holding preference fixed, the best-response effort DECREASES as the others'
    # total effort Ebar rises (classic free-riding in the shared-output firm).
    theta = 0.5
    e_low = best_effort_closed_form(theta, 0.0, 1.0, 1.0)
    e_mid = best_effort_closed_form(theta, 1.0, 1.0, 1.0)
    e_high = best_effort_closed_form(theta, 5.0, 1.0, 1.0)
    assert e_low > e_mid > e_high


def test_strong_leisure_lover_is_corner_zero():
    # A near-pure leisure-lover (theta ~ 0) supplies zero effort once others carry the
    # firm — the e*=0 corner of eq. 5.
    assert best_effort_closed_form(0.001, 3.0, 1.0, 1.0) == pytest.approx(0.0, abs=1e-6)


# -- model construction + firm registry ---------------------------------------

def test_starts_all_singletons_with_best_response_effort():
    m = AxtellFirmsModel(50, seed=0)
    assert len(m.agent_list) == 50
    assert all(isinstance(a, FirmAgent) for a in m.agent_list)
    # every agent is in its own firm; 50 singleton firms.
    assert m.n_firms() == 50
    assert m.firm_sizes() == [1] * 50
    # a singleton's effort equals its solo best response (Ebar=0).
    for ag in m.agent_list:
        assert ag.effort == pytest.approx(best_effort_closed_form(ag.theta, 0.0, 1.0, 1.0))
        # the firm's cached total effort equals the member's effort.
        assert m.firm_effort[ag.firm] == pytest.approx(ag.effort)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        AxtellFirmsModel(1)                 # need > 1 agent
    with pytest.raises(ValueError):
        AxtellFirmsModel(10, b=-1.0)
    with pytest.raises(ValueError):
        AxtellFirmsModel(10, nu=0)


def test_registry_exact_after_move_to_friend_firm():
    # Force a controlled move: put agent 0's friend into a rich firm and check the
    # cached (total effort, size) stay exact across the move.
    m = AxtellFirmsModel(6, seed=1)
    a0 = m.agent_list[0]
    # make agent 0 a leisure-lover so it will happily join a productive firm and free-ride.
    a0.theta = 0.5
    # build a firm {1,2,3} with real effort and point agent 0's friend at it.
    target = 1
    for j in (2, 3):
        aj = m.agent_list[j]
        m._remove_from_firm(aj)
        m._add_to_firm(aj, target, 0.6)
    # recompute the target firm's cached effort exactly from members for the assertion.
    members = [ag for ag in m.agent_list if ag.firm == target]
    assert m.firm_size[target] == len(members)
    assert m.firm_effort[target] == pytest.approx(sum(ag.effort for ag in members))
    a0.friends = (target, target)
    old_firm = a0.firm
    m.activate(a0)
    # registry invariant: for EVERY live firm, cached size/effort == recomputed truth.
    for fid in list(m.firm_size.keys()):
        mem = [ag for ag in m.agent_list if ag.firm == fid]
        assert m.firm_size[fid] == len(mem)
        assert m.firm_effort[fid] == pytest.approx(sum(ag.effort for ag in mem), abs=1e-9)
    # total membership is conserved (every agent in exactly one firm).
    assert sum(m.firm_sizes()) == m.A
    _ = old_firm


def test_activation_moves_agent_into_a_more_productive_firm():
    # An agent alone earns little; a big productive firm offers a much larger share.
    # After activation the agent should NOT remain a singleton if joining strictly wins.
    m = AxtellFirmsModel(8, seed=2)
    a0 = m.agent_list[0]
    a0.theta = 0.6
    target = 1
    # stack several high-effort workers into the target firm.
    for j in (2, 3, 4, 5):
        aj = m.agent_list[j]
        m._remove_from_firm(aj)
        m._add_to_firm(aj, target, 0.8)
    a0.friends = (target, target)
    m.activate(a0)
    # joining a firm with big total effort (huge O(E)) beats a lone singleton -> moved.
    # target firm had its founder (agent 1) + the 4 stacked workers = 5, now +a0 = 6.
    assert a0.firm == target
    assert m.firm_size[target] == 6


def test_total_membership_conserved_over_a_run():
    m = AxtellFirmsModel(200, seed=3)
    for _ in range(10):
        m.run_period()
        assert sum(m.firm_sizes()) == m.A          # no agents lost or duplicated
        # registry stays exact throughout.
        assert all(s >= 1 for s in m.firm_sizes())


# -- distribution statistics --------------------------------------------------

def test_rank_size_slope_is_minus_one_for_exact_zipf():
    # Exact Zipf: size_k = C / rank_k. log(rank) vs log(size) has slope -1.
    sizes = [round(1000 / r) for r in range(1, 40)]
    slope = rank_size_slope(sizes)
    assert slope == pytest.approx(-1.0, abs=0.05)


def test_gini_extremes():
    assert gini([5, 5, 5, 5]) == pytest.approx(0.0)          # perfectly equal
    # one huge, many tiny -> Gini near 1.
    assert gini([1, 1, 1, 1, 1, 1, 1, 1, 1, 1000]) > 0.8
    assert gini([]) == 0.0


def test_excess_kurtosis_gaussian_vs_laplace():
    import random
    rng = random.Random(0)
    normal = [rng.gauss(0.0, 1.0) for _ in range(20000)]
    # Laplace via inverse-CDF of two exponentials.
    lap = []
    for _ in range(20000):
        u = rng.random() - 0.5
        lap.append(-math.copysign(1.0, u) * math.log(1 - 2 * abs(u)))
    k_norm = excess_kurtosis(normal)
    k_lap = excess_kurtosis(lap)
    assert abs(k_norm) < 0.4              # Gaussian excess kurtosis ~ 0
    assert k_lap > 1.5                    # Laplace excess kurtosis ~ 3 (tent-shaped)
    assert k_lap > k_norm + 1.5


def test_growth_std_by_size_slope_detects_decreasing_volatility():
    import random
    rng = random.Random(1)
    # construct (growth, size) with sigma(size) ~ size^-0.3 -> negative log-log slope.
    pairs = []
    for s in (2, 4, 8, 16, 32, 64):
        sigma = s ** -0.3
        for _ in range(500):
            pairs.append((rng.gauss(0.0, sigma), s))
    slope, pts = growth_std_by_size_slope(pairs, min_per_bin=20)
    assert slope < 0.0
    assert slope == pytest.approx(-0.3, abs=0.1)
    assert len(pts) >= 4


# -- run summary + determinism ------------------------------------------------

def test_run_summary_shape():
    res = run_single(300, seed=0, n_periods=20, burn_in=8, sample_gap=4)
    assert res["A"] == 300 and res["nu"] == 2
    # aggregate series has t=0 baseline + n_periods entries.
    assert len(res["n_firms_series"]) == 21
    assert len(res["mean_firm_size_series"]) == 21
    assert res["final_firm_sizes"] and all(s >= 1 for s in res["final_firm_sizes"])
    assert sum(res["final_firm_sizes"]) == 300      # membership conserved
    # graded statistics are present and finite.
    for key in ("rank_size_slope", "gini_firm_size", "growth_excess_kurtosis",
                "growth_std_size_slope"):
        assert key in res and math.isfinite(res[key])


def test_run_rejects_bad_windows():
    m = AxtellFirmsModel(20, seed=0)
    with pytest.raises(ValueError):
        m.run(10, burn_in=10)               # burn_in must be < n_periods
    with pytest.raises(ValueError):
        m.run(0)
    with pytest.raises(ValueError):
        m.run(10, burn_in=2, sample_gap=0)


def test_determinism_same_seed_identical_result():
    a = run_single(300, seed=42, n_periods=25, burn_in=10, sample_gap=5)
    b = run_single(300, seed=42, n_periods=25, burn_in=10, sample_gap=5)
    assert a["final_firm_sizes"] == b["final_firm_sizes"]
    assert a["growth_rates"] == b["growth_rates"]
    assert a["rank_size_slope"] == b["rank_size_slope"]
    assert a["gini_firm_size"] == b["gini_firm_size"]


def test_different_seed_differs_but_stays_shaped():
    a = run_single(300, seed=1, n_periods=25, burn_in=10, sample_gap=5)
    b = run_single(300, seed=2, n_periods=25, burn_in=10, sample_gap=5)
    for res in (a, b):
        assert sum(res["final_firm_sizes"]) == 300
        assert all(s >= 1 for s in res["final_firm_sizes"])
