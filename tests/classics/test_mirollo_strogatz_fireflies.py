"""Faithful-rule + determinism tests for the Mirollo-Strogatz pulse-coupled oscillator
reproduction.

These pin the RULES of the 1990 model, not its predictions: the concave charging curve and
its exact inverse (f(0)=0, f(1)=1, monotone, concave-down for b>0; linear for b==0), the
event-driven advance-to-next-firing, the fire/reset, the pulse-kick applied in VOLTAGE
(x_j -> min(1, x_j + eps)), ABSORPTION (a kicked oscillator driven to threshold fires in the
same instant and coalesces into one firing group that stays phase-locked forever), the
all-in-one-group sync detection, and determinism of the seeded initial-phase draw. The
locked P1-P3 (universal sync, coupling speeds sync, concavity necessary) are graded by
examples/repro_mirollo_strogatz_fireflies/run.py, NOT here.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.mirollo_strogatz_fireflies import (
    MirolloStrogatzModel,
    f_curve,
    f_inverse,
    is_concave,
    run_many_seeds,
    run_single,
)


# -- charging curve f and its exact inverse -----------------------------------

def test_curve_endpoints_and_monotone():
    # f(0)=0, f(1)=1 at both the concave and the linear settings, and strictly increasing.
    for b in (0.0, 1.0, 3.0, 5.0):
        assert f_curve(0.0, b) == pytest.approx(0.0)
        assert f_curve(1.0, b) == pytest.approx(1.0)
        prev = -1.0
        for k in range(0, 101):
            phi = k / 100.0
            val = f_curve(phi, b)
            assert val > prev - 1e-15          # non-decreasing
            prev = val


def test_curve_is_concave_down_for_positive_b():
    # Concave-down: f(phi) lies strictly ABOVE the chord, i.e. f(mid) > (f(a)+f(c))/2, and
    # f(0.5) > 0.5 (the curve bulges up). The linear control does neither (equality).
    b = 3.0
    for a, c in [(0.0, 1.0), (0.1, 0.9), (0.2, 0.6)]:
        mid = 0.5 * (a + c)
        chord = 0.5 * (f_curve(a, b) + f_curve(c, b))
        assert f_curve(mid, b) > chord + 1e-9
    assert f_curve(0.5, b) > 0.5 + 1e-6
    # linear control: exactly on the chord, f(0.5) == 0.5.
    assert f_curve(0.5, 0.0) == pytest.approx(0.5)
    assert is_concave(3.0) and not is_concave(0.0)


def test_f_inverse_round_trips():
    # f_inv must be the EXACT inverse of f at both settings (the load-bearing pairing that
    # makes the voltage kick x_j -> f(phi_j)+eps translate back to a phase).
    for b in (0.0, 2.0, 3.0, 4.0):
        for k in range(1, 100):
            phi = k / 100.0
            assert f_inverse(f_curve(phi, b), b) == pytest.approx(phi, abs=1e-9)
        # and the other direction on voltage.
        for k in range(1, 100):
            x = k / 100.0
            assert f_curve(f_inverse(x, b), b) == pytest.approx(x, abs=1e-9)


def test_curve_clamps_out_of_range():
    for b in (0.0, 3.0):
        assert f_curve(-0.3, b) == 0.0 and f_curve(1.7, b) == 1.0
        assert f_inverse(-0.3, b) == 0.0 and f_inverse(1.7, b) == 1.0


# -- event-driven advance / fire / reset --------------------------------------

def test_advance_brings_leader_to_threshold():
    m = MirolloStrogatzModel(4, eps=0.1, b=3.0, seed=0)
    # overwrite phases by hand: leader at 0.7, others below.
    for a, p in zip(m.agent_list, [0.7, 0.4, 0.2, 0.1]):
        a.phi = p
    dt = m._advance_to_next_firing()
    assert dt == pytest.approx(0.3)
    assert max(a.phi for a in m.agent_list) == pytest.approx(1.0)
    # the gaps between phases are preserved by the uniform advance.
    assert m.agent_list[1].phi == pytest.approx(0.7)


def test_fire_resets_leader_and_kicks_others_in_voltage():
    # No absorption case: a lone firer resets to 0 and pulls every other oscillator up by eps
    # in VOLTAGE, i.e. phi_j -> f_inv(f(phi_j) + eps). Verify the exact voltage bookkeeping.
    b, eps = 3.0, 0.1
    m = MirolloStrogatzModel(2, eps=eps, b=b, seed=0)
    m.agent_list[0].phi = 1.0                     # firer at threshold
    m.agent_list[1].phi = 0.2                     # follower, far from threshold
    x_before = f_curve(0.2, b)
    n_fired = m._fire_cascade()
    assert n_fired == 1                           # only the leader fires (no absorption)
    assert m.agent_list[0].phi == pytest.approx(0.0)      # firer reset
    # follower kicked UP by eps in voltage, then mapped back to phase.
    assert f_curve(m.agent_list[1].phi, b) == pytest.approx(x_before + eps, abs=1e-9)
    assert m.agent_list[1].phi > 0.2             # phase advanced


def test_kick_saturates_at_one_not_over():
    # A kick can never push voltage above 1: x_j -> min(1, x_j + eps).
    b, eps = 3.0, 0.5
    m = MirolloStrogatzModel(2, eps=eps, b=b, seed=0)
    m.agent_list[0].phi = 1.0
    m.agent_list[1].phi = 0.95                    # already high; +0.5 voltage would exceed 1
    m._fire_cascade()
    # follower absorbed -> reset to 0 (see absorption test); voltage was clamped at 1 first.
    assert 0.0 <= m.agent_list[1].phi <= 1.0


# -- ABSORPTION / coalescence -------------------------------------------------

def test_absorption_coalesces_into_one_group():
    # If a kick drives a follower to/over threshold, it fires in the SAME instant and joins
    # the firer's group; both reset to 0 and share one group label (phase-locked forever).
    b, eps = 3.0, 0.5
    m = MirolloStrogatzModel(2, eps=eps, b=b, seed=0)
    m.agent_list[0].phi = 1.0
    # choose follower so that f(phi)+eps >= 1  =>  absorbed.
    m.agent_list[1].phi = f_inverse(1.0 - eps + 0.05, b)   # voltage 0.55 -> +0.5 -> >=1
    n_fired = m._fire_cascade()
    assert n_fired == 2                           # both fired via absorption
    assert m.agent_list[0].group == m.agent_list[1].group  # one group
    assert m.agent_list[0].phi == 0.0 and m.agent_list[1].phi == 0.0
    assert m.n_groups() == 1


def test_absorbed_group_stays_locked_forever():
    # Once coalesced the group must remain a single group through further cycles: identical
    # phase, identical future kicks -> they never split.
    b, eps = 3.0, 0.5
    m = MirolloStrogatzModel(3, eps=eps, b=b, seed=0)
    m.agent_list[0].phi = 1.0
    m.agent_list[1].phi = f_inverse(0.6, b)       # will be absorbed (0.6+0.5>=1)
    m.agent_list[2].phi = 0.1                     # far away, not absorbed this event
    m._fire_cascade()
    assert m.agent_list[0].group == m.agent_list[1].group
    # run several more events; the two coalesced ones keep IDENTICAL phase and stay in one
    # shared group forever (their common label may only shrink if they later merge with a
    # lower-labelled group — it never splits them apart).
    for _ in range(20):
        m._step_event()
        assert m.agent_list[0].phi == pytest.approx(m.agent_list[1].phi)
        assert m.agent_list[0].group == m.agent_list[1].group


def test_single_pulse_not_a_domino():
    # THE faithfulness invariant: one firing event = ONE collective eps pulse. A lone leader
    # must only absorb oscillators that ITS single eps pulse pushes over threshold; it must
    # NOT drag far-below oscillators over the edge via a domino of re-firing absorbed members.
    # Construct: 1 leader at threshold, some followers within eps of threshold (absorbed),
    # and a low oscillator MORE than eps below threshold (must survive).
    b, eps = 3.0, 0.1
    m = MirolloStrogatzModel(4, eps=eps, b=b, seed=0)
    m.agent_list[0].phi = 1.0                              # leader
    m.agent_list[1].phi = f_inverse(1.0 - 0.5 * eps, b)   # within eps -> absorbed
    m.agent_list[2].phi = f_inverse(1.0 - 0.5 * eps, b)   # within eps -> absorbed
    m.agent_list[3].phi = f_inverse(0.5, b)               # voltage 0.5, 0.5+eps<1 -> survives
    n_fired = m._fire_cascade()
    assert n_fired == 3                                   # leader + the two within one pulse
    assert m.agent_list[3].phi > 0.0                      # the low one was NOT swept up
    # its voltage moved up by exactly ONE eps (one collective pulse), not many.
    assert f_curve(m.agent_list[3].phi, b) == pytest.approx(0.5 + eps, abs=1e-9)
    assert m.n_groups() == 2                              # {leader,1,2} and {3}


def test_no_absorption_when_kick_too_small():
    # A small eps that does not reach threshold must NOT coalesce anyone.
    b, eps = 3.0, 0.01
    m = MirolloStrogatzModel(2, eps=eps, b=b, seed=0)
    m.agent_list[0].phi = 1.0
    m.agent_list[1].phi = 0.2
    n_fired = m._fire_cascade()
    assert n_fired == 1
    assert m.n_groups() == 2                      # still two distinct groups


# -- sync detection -----------------------------------------------------------

def test_full_sync_is_one_group_all_fire():
    # A tiny concave system reaches full sync = one group; the summary flags it.
    res = run_single(6, eps=0.3, b=3.0, seed=1, max_cycles=2000)
    assert res["synced"] is True
    assert res["n_groups_final"] == 1
    assert res["cycles_to_sync"] is not None and res["cycles_to_sync"] >= 1
    assert res["concave"] is True


def test_single_oscillator_is_trivially_synced():
    res = run_single(1, eps=0.1, b=3.0, seed=0, max_cycles=10)
    assert res["synced"] is True
    assert res["n_groups_final"] == 1


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_single(30, eps=0.1, b=3.0, seed=7, max_cycles=3000)
    b = run_single(30, eps=0.1, b=3.0, seed=7, max_cycles=3000)
    assert a["synced"] == b["synced"]
    assert a["cycles_to_sync"] == b["cycles_to_sync"]
    assert a["n_groups_final"] == b["n_groups_final"]


def test_initial_phases_are_distinct_and_seeded():
    m = MirolloStrogatzModel(50, eps=0.1, b=3.0, seed=3)
    phases = m.phases()
    assert len(set(phases)) == 50                 # distinct draw (no exact t=0 tie)
    assert all(0.0 < p < 1.0 for p in phases)
    # same seed -> same draw.
    m2 = MirolloStrogatzModel(50, eps=0.1, b=3.0, seed=3)
    assert m2.phases() == phases
    # different seed -> different draw.
    m3 = MirolloStrogatzModel(50, eps=0.1, b=3.0, seed=4)
    assert m3.phases() != phases


# -- multi-seed aggregation shape ---------------------------------------------

def test_run_many_seeds_shape_and_median():
    out = run_many_seeds(20, eps=0.2, b=3.0, n_seeds=5, seed_base=0, max_cycles=3000)
    assert out["n_seeds"] == 5
    assert 0.0 <= out["sync_fraction"] <= 1.0
    assert len(out["per_seed_synced"]) == 5
    assert len(out["per_seed_cycles_to_sync"]) == 5
    # median is over the seeds that DID sync; consistent with the sorted synced list.
    synced_cyc = out["synced_cycles_sorted"]
    if synced_cyc:
        assert out["median_cycles_to_sync"] is not None
        assert min(synced_cyc) <= out["median_cycles_to_sync"] <= max(synced_cyc)


# -- validation ---------------------------------------------------------------

def test_invalid_params_raise():
    with pytest.raises(ValueError):
        MirolloStrogatzModel(0)
    with pytest.raises(ValueError):
        MirolloStrogatzModel(10, eps=0.0)
    with pytest.raises(ValueError):
        MirolloStrogatzModel(10, b=-1.0)
    with pytest.raises(ValueError):
        MirolloStrogatzModel(10).run_to_sync(max_cycles=0)
    with pytest.raises(ValueError):
        run_many_seeds(10, n_seeds=0)
