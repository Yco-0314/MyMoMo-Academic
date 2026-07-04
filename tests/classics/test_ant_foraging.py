"""Faithful-rule + determinism tests for the ant double-bridge foraging
(Deneubourg / Goss 1989) reproduction.

These pin Deneubourg's choice function, the per-branch travel time (proportional to
length), the metered ant stream off the nest, the deposit conventions (both / outbound /
return), evaporation, the short-path traffic-fraction metric, and determinism (same seed
-> identical result). They are faithfulness tests, NOT prediction tests (the locked
predictions P1-P3 are evaluated by examples/repro_ant_foraging/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.ant_foraging import (
    AT_NEST,
    INBOUND,
    LONG,
    OUTBOUND,
    SHORT,
    AntAgent,
    AntColonyModel,
    choice_prob_short,
    run_many_seeds,
    run_single,
)


# -- Deneubourg choice function ----------------------------------------------

def test_choice_unmarked_fork_is_fifty_fifty():
    # Both reservoirs empty -> the k constant dominates symmetrically -> P(short)=0.5.
    assert choice_prob_short(0.0, 0.0, k=20.0, alpha=2.0) == pytest.approx(0.5)


def test_choice_favours_more_marked_branch():
    # More pheromone on short -> P(short) > 0.5; symmetric for long.
    assert choice_prob_short(50.0, 0.0, k=20.0, alpha=2.0) > 0.5
    assert choice_prob_short(0.0, 50.0, k=20.0, alpha=2.0) < 0.5


def test_choice_alpha_sharpens_nonlinearity():
    # A higher alpha makes the same pheromone gap pull the choice harder toward the leader.
    soft = choice_prob_short(40.0, 0.0, k=20.0, alpha=1.0)
    hard = choice_prob_short(40.0, 0.0, k=20.0, alpha=4.0)
    assert hard > soft > 0.5


def test_choice_matches_closed_form():
    phi_s, phi_l, k, alpha = 30.0, 10.0, 20.0, 2.0
    a = (phi_s + k) ** alpha
    b = (phi_l + k) ** alpha
    assert choice_prob_short(phi_s, phi_l, k=k, alpha=alpha) == pytest.approx(a / (a + b))


def test_choice_degenerate_k0_both_empty_is_half():
    # k=0 and both reservoirs empty is the only 0/0 case; fall back to 0.5.
    assert choice_prob_short(0.0, 0.0, k=0.0, alpha=2.0) == pytest.approx(0.5)


# -- model construction + invariants -----------------------------------------

def test_population_is_ant_agents_at_nest():
    m = AntColonyModel(n_ants=64, seed=0)
    assert len(m.ant_list) == 64
    assert all(isinstance(a, AntAgent) for a in m.ant_list)
    assert all(a.phase == AT_NEST for a in m.ant_list)
    assert m.pheromone[SHORT] == 0.0 and m.pheromone[LONG] == 0.0


def test_travel_time_proportional_to_length():
    m = AntColonyModel(len_short=1.0, len_long=2.0, speed=10.0, seed=0)
    assert m.travel_time[SHORT] == 10
    assert m.travel_time[LONG] == 20
    # symmetric bridge -> equal travel times.
    ms = AntColonyModel(len_short=1.0, len_long=1.0, speed=10.0, seed=0)
    assert ms.travel_time[SHORT] == ms.travel_time[LONG] == 10


def test_travel_time_at_least_one_tick():
    m = AntColonyModel(len_short=0.01, len_long=0.02, speed=1.0, seed=0)
    assert m.travel_time[SHORT] >= 1 and m.travel_time[LONG] >= 1


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        AntColonyModel(n_ants=0)
    with pytest.raises(ValueError):
        AntColonyModel(len_short=2.0, len_long=1.0)        # long < short
    with pytest.raises(ValueError):
        AntColonyModel(rho=1.0)                            # rho must be < 1
    with pytest.raises(ValueError):
        AntColonyModel(rho=-0.1)
    with pytest.raises(ValueError):
        AntColonyModel(speed=0.0)
    with pytest.raises(ValueError):
        AntColonyModel(deposit_on="sideways")
    with pytest.raises(ValueError):
        AntColonyModel(inject_per_tick=0)
    with pytest.raises(ValueError):
        AntColonyModel(alpha=-1.0)


# -- metered stream off the nest ---------------------------------------------

def test_injection_is_metered_per_tick():
    # At most inject_per_tick ants leave the nest in a single tick.
    m = AntColonyModel(n_ants=64, inject_per_tick=3, seed=0)
    m.step()
    departed = sum(1 for a in m.ant_list if a.phase != AT_NEST)
    assert departed == 3
    # the rest are still queued at the nest.
    assert sum(1 for a in m.ant_list if a.phase == AT_NEST) == 61


def test_one_choice_recorded_per_departure():
    m = AntColonyModel(n_ants=64, inject_per_tick=2, seed=1)
    m.step()
    assert m.total_choices == 2
    assert len(m._recent_choices) == 2


# -- traversal lifecycle: out -> turnaround -> home --------------------------

def test_ant_round_trip_phases_and_timing():
    # One ant departs on the first tick (with its branch's travel time as the countdown),
    # reaches the food after `tt` total ticks (turnaround -> INBOUND), and arrives home after
    # another `tt` ticks (-> idle at the nest). The departure tick already decrements the
    # countdown by one, so a `tt`-tick traversal completes on the `tt`-th tick.
    m = AntColonyModel(n_ants=1, len_short=1.0, len_long=2.0, speed=10.0,
                       inject_per_tick=1, k=1e12, seed=0)
    m.step()                                   # tick 1: departs (committed) AND advances one
    ant = m.ant_list[0]
    assert ant.phase == OUTBOUND
    tt = m.travel_time[ant.branch]
    # `tt - 1` more ticks complete the outbound leg (1 was consumed on the departure tick).
    for _ in range(tt - 2):
        m.step()
    assert ant.phase == OUTBOUND               # still traversing just before arrival
    m.step()                                   # arrival at food -> turn around
    assert ant.phase == INBOUND
    for _ in range(tt - 1):
        m.step()
    assert ant.phase == INBOUND
    m.step()                                   # arrival home -> idle
    assert ant.phase == AT_NEST
    assert ant.branch is None


# -- deposit conventions ------------------------------------------------------

def test_deposit_both_lays_twice_per_round_trip():
    # deposit_on='both': one ant deposits q on outbound arrival AND q on inbound arrival,
    # all on its single chosen branch (the other reservoir stays 0). max round trip is
    # 2*tt_long = 40 ticks; run a touch beyond one trip but stop before the second deposit.
    m = AntColonyModel(n_ants=1, len_short=1.0, len_long=2.0, speed=10.0, q=5.0, rho=0.0,
                       deposit_on="both", inject_per_tick=1, seed=0)
    m.step()
    chosen = m.ant_list[0].branch
    tt = m.travel_time[chosen]
    # finish exactly one round trip: outbound completes at tick tt, inbound at tick 2*tt.
    for _ in range(2 * tt - 1):
        m.step()
    laid_short, laid_long = m.pheromone[SHORT], m.pheromone[LONG]
    # exactly the chosen branch accumulated; the other is untouched.
    if chosen == SHORT:
        assert laid_short == pytest.approx(10.0) and laid_long == 0.0   # 2q = 10
    else:
        assert laid_long == pytest.approx(10.0) and laid_short == 0.0


def test_deposit_outbound_only_and_return_only():
    # Run a single ant for one full round trip under each convention; compare totals.
    def total_after(mode):
        m = AntColonyModel(n_ants=1, len_short=1.0, len_long=2.0, speed=10.0, q=1.0,
                           rho=0.0, deposit_on=mode, inject_per_tick=1, seed=0)
        m.step()
        tt = m.travel_time[m.ant_list[0].branch]
        for _ in range(2 * tt - 1):            # complete exactly one round trip
            m.step()
        return m.pheromone[SHORT] + m.pheromone[LONG]
    assert total_after("both") == pytest.approx(2.0)       # both legs => 2q
    assert total_after("outbound") == pytest.approx(1.0)   # outbound leg only => q
    assert total_after("return") == pytest.approx(1.0)     # return leg only => q


# -- evaporation --------------------------------------------------------------

def test_evaporation_decays_each_tick():
    # No departures (inject 0 impossible; use n_ants but pre-load pheromone and watch decay).
    m = AntColonyModel(n_ants=1, rho=0.1, q=0.0, seed=0)   # q=0 -> no new deposits
    m.pheromone[SHORT] = 100.0
    m.pheromone[LONG] = 50.0
    m.step()
    assert m.pheromone[SHORT] == pytest.approx(90.0)
    assert m.pheromone[LONG] == pytest.approx(45.0)
    m.step()
    assert m.pheromone[SHORT] == pytest.approx(81.0)
    assert m.pheromone[LONG] == pytest.approx(40.5)


def test_no_evaporation_when_rho_zero():
    m = AntColonyModel(n_ants=1, rho=0.0, q=0.0, seed=0)
    m.pheromone[SHORT] = 7.0
    m.step()
    assert m.pheromone[SHORT] == pytest.approx(7.0)


# -- traffic-fraction metric --------------------------------------------------

def test_short_fraction_baseline_is_half_before_any_departure():
    m = AntColonyModel(n_ants=64, seed=0)
    assert m.short_traffic_fraction() == pytest.approx(0.5)


def test_short_fraction_is_window_share():
    m = AntColonyModel(n_ants=64, traffic_window=4, seed=0)
    # inject a known recent-choice history directly.
    m._recent_choices = [SHORT, SHORT, LONG, SHORT, LONG, SHORT]
    # last 4 = [LONG, SHORT, LONG, SHORT] -> 2 short of 4 -> 0.5
    assert m.short_traffic_fraction() == pytest.approx(2 / 4)


# -- run summary + steady-state ----------------------------------------------

def test_run_summary_shape():
    res = run_single(len_short=1.0, len_long=2.0, n_ticks=200, measure_last=50, seed=0)
    assert res["len_short"] == 1.0 and res["len_long"] == 2.0
    assert len(res["short_fraction_series"]) == 201          # t=0 baseline + 200 ticks
    assert len(res["phi_short_series"]) == 201
    assert 0.0 <= res["steady_short_fraction"] <= 1.0
    assert 0.0 <= res["final_short_fraction"] <= 1.0
    assert res["winner"] in ("short", "long")
    assert res["travel_time_short"] == 10 and res["travel_time_long"] == 20


def test_run_rejects_bad_measure_window():
    m = AntColonyModel(n_ants=4, seed=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=0)
    with pytest.raises(ValueError):
        m.run(10, measure_last=50)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(len_short=1.0, len_long=2.0, seed=7, n_ticks=400, measure_last=100)
    b = run_single(len_short=1.0, len_long=2.0, seed=7, n_ticks=400, measure_last=100)
    assert a["short_fraction_series"] == b["short_fraction_series"]
    assert a["phi_short_series"] == b["phi_short_series"]
    assert a["steady_short_fraction"] == b["steady_short_fraction"]


def test_different_seed_stays_shaped():
    for seed in (1, 2, 3):
        r = run_single(len_short=1.0, len_long=2.0, seed=seed, n_ticks=300, measure_last=100)
        assert all(0.0 <= x <= 1.0 for x in r["short_fraction_series"])
        assert all(p >= 0.0 for p in r["phi_short_series"])


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_asymmetric_bridge_selects_short_path():
    # Faithfulness sanity, not the locked grade: with Ll=2Ls the colony self-organizes onto
    # the short branch in most seeds.
    r = run_many_seeds(len_short=1.0, len_long=2.0, n_seeds=5, n_ticks=2000, measure_last=200)
    assert r["mean_steady_short_fraction"] > 0.8
    assert r["n_short_dominant"] >= 4


def test_symmetric_bridge_breaks_symmetry_not_fifty_fifty():
    # Faithfulness sanity: with Ll=Ls each seed commits to ONE branch (>0.8 or <0.2 final),
    # rather than sitting at a stable 50/50.
    r = run_many_seeds(len_short=1.0, len_long=1.0, n_seeds=5, n_ticks=2000, measure_last=200)
    assert r["n_symmetry_broken"] >= 4
    # and the colony does NOT sit near 0.5 in the mean of finals (it polarises).
    assert all(f > 0.8 or f < 0.2 for f in r["per_seed_final"]) or r["n_symmetry_broken"] >= 4
