"""Faithful-rule + determinism tests for the Burridge-Knopoff (Carlson-Langer
1989) spring-block reproduction.

These pin the RULES of the mechanical model, not the locked predictions: the
velocity-weakening friction law (onset kinetic drop to F0*(1-sigma), odd in v,
monotone weakening), the coil/leaf spring elastic force with pinned boundaries,
the energy-stable velocity-Verlet stability guard, the stick-slip burst bookkeeping
(a block breaks free only at/above the static threshold and re-sticks when its
velocity reverses), the loading-to-threshold jump, and the power-law / heavy-tail
metrics. Determinism is pinned too. The locked P1-P3 clauses (GR exponent in
[1.5,2.5], >=2 decades + max>=100x median, mean moment decreasing with stiffness)
are graded by examples/repro_burridge_knopoff/run.py, NOT here.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.burridge_knopoff import (
    BurridgeKnopoffModel,
    decades_spanned,
    friction_force,
    max_over_median,
    mle_power_law_exponent,
    positive_moments,
    run_single,
    small_event_window,
)


# -- velocity-weakening friction law ------------------------------------------

def test_friction_onset_is_reduced_kinetic_value():
    # At slip onset (|v| -> 0+) the KINETIC branch starts at F0*(1-sigma), a
    # discontinuous drop of sigma*F0 below the static maximum F0. This onset drop
    # is the instability that drives the slip burst.
    F0, sigma, alpha = 1.0, 0.1, 3.0
    phi = friction_force(np.array([1e-9]), F0, sigma, alpha)[0]
    assert phi == pytest.approx(F0 * (1.0 - sigma), rel=1e-4)


def test_friction_is_zero_at_rest():
    # Exactly at v = 0 the odd law returns 0 (a stuck block's friction is the
    # static reaction, not this kinetic force).
    assert friction_force(np.array([0.0]), 1.0, 0.05, 3.0)[0] == 0.0


def test_friction_is_odd_in_velocity():
    v = np.array([0.3, 1.0, 4.0])
    pos = friction_force(v, 1.0, 0.02, 3.0)
    neg = friction_force(-v, 1.0, 0.02, 3.0)
    assert np.allclose(pos, -neg)


def test_friction_weakens_with_speed():
    # Velocity WEAKENING: the kinetic friction magnitude strictly decreases as the
    # slip speed grows (this is what makes a slipping block accelerate).
    speeds = np.array([0.01, 0.1, 1.0, 10.0, 100.0])
    mags = friction_force(speeds, 1.0, 0.05, 3.0)
    assert np.all(np.diff(mags) < 0.0)


def test_sigma_sets_onset_drop_size():
    # Larger sigma -> larger static->kinetic drop -> smaller kinetic onset force.
    small = friction_force(np.array([1e-9]), 1.0, 0.01, 3.0)[0]
    big = friction_force(np.array([1e-9]), 1.0, 0.30, 3.0)[0]
    assert big < small


# -- elastic force: coil spring + leaf-spring coupling + pinned ends ----------

def test_coil_spring_pulls_toward_plate():
    # With all blocks at u=0 and the plate at L, the only elastic force is the
    # coil spring -(u - L) = +L on every block (leaf coupling of a flat chain=0).
    m = BurridgeKnopoffModel(n=5, ell=2.0, seed=0, init_noise=0.0)
    u = np.zeros(5)
    F = m.elastic_force(u, plate=0.7)
    assert np.allclose(F, 0.7)


def test_leaf_coupling_is_discrete_laplacian_with_pins():
    # A single unit bump: ell^2 * (u_{i+1} - 2u_i + u_{i-1}) with u=0 pins outside.
    m = BurridgeKnopoffModel(n=4, ell=2.0, seed=0, init_noise=0.0)  # ell^2 = 4
    u = np.array([0.0, 1.0, 0.0, 0.0])
    lap = m._coupling(u)
    # block1 bump: neighbours are block0(0) and block2(0): 4*(0 - 2*1 + 0) = -8
    # block0: left pin(0), right block1(1): 4*(1 - 2*0 + 0) = 4
    # block2: left block1(1), right block3(0): 4*(0 - 2*0 + 1) = 4
    assert lap[0] == pytest.approx(4.0)
    assert lap[1] == pytest.approx(-8.0)
    assert lap[2] == pytest.approx(4.0)
    assert lap[3] == pytest.approx(0.0)


def test_flat_chain_has_no_interior_coupling_force():
    # A flat chain has zero leaf-spring force in its INTERIOR (a discrete Laplacian
    # of a constant is 0). The two END blocks are pinned to u=0 outside, so a flat
    # chain lifted to u=c feels a restoring pull at the boundaries -> nonzero there.
    m = BurridgeKnopoffModel(n=6, ell=3.0, seed=0, init_noise=0.0)  # ell^2 = 9
    u = np.full(6, 2.5)
    lap = m._coupling(u)
    assert np.allclose(lap[1:-1], 0.0)               # interior: constant -> 0
    assert lap[0] == pytest.approx(9.0 * (2.5 - 2.0 * 2.5))   # left pin at 0
    assert lap[-1] == pytest.approx(9.0 * (2.5 - 2.0 * 2.5))  # right pin at 0


# -- stability guard (energy-stable timestep) ---------------------------------

def test_stability_guard_rejects_too_large_dt():
    # velocity-Verlet needs dt*omega_max well under 2; the guard rejects a dt that
    # is too large for the (ell-dependent) stiffest mode.
    with pytest.raises(ValueError):
        BurridgeKnopoffModel(n=32, ell=5.0, dt=0.5)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        BurridgeKnopoffModel(n=0)
    with pytest.raises(ValueError):
        BurridgeKnopoffModel(n=8, ell=0.0)
    with pytest.raises(ValueError):
        BurridgeKnopoffModel(n=8, sigma=0.0)     # need 0 < sigma < 1
    with pytest.raises(ValueError):
        BurridgeKnopoffModel(n=8, sigma=1.0)
    with pytest.raises(ValueError):
        BurridgeKnopoffModel(n=8, nu=0.0)


# -- stick-slip burst bookkeeping ---------------------------------------------

def test_below_threshold_chain_does_not_slip():
    # A chain whose maximum elastic load is below F0 has no burst: moment 0, no
    # participating blocks (nothing breaks free).
    m = BurridgeKnopoffModel(n=8, ell=2.0, seed=0, init_noise=0.0)
    m.plate = 0.5                    # coil load 0.5 < F0 = 1.0 everywhere
    moment, size = m._run_burst()
    assert size == 0
    assert moment == pytest.approx(0.0)


def test_loading_brings_a_block_exactly_to_threshold_then_it_slips():
    # _load_to_next_threshold advances the plate until the first block reaches F0.
    # That block must then actually break free (moment > 0, >=1 participant) — the
    # onset kinetic friction F0*(1-sigma) is below the F0 load, so there is a net
    # unbalanced force that accelerates it.
    m = BurridgeKnopoffModel(n=16, ell=2.0, sigma=0.05, seed=0)
    assert m._load_to_next_threshold() is True
    elastic = m.elastic_force(m.u, m.plate)
    assert np.max(np.abs(elastic)) >= m.F0 - 1e-9     # a block is at threshold
    moment, size = m._run_burst()
    assert size >= 1
    assert moment > 0.0


def test_friction_law_controls_event_statistics():
    # The velocity-weakening friction is the physical driver: changing sigma (the
    # onset stress drop) MUST change the event statistics. If sigma had no effect
    # the burst dynamics would be a friction-free geometric artifact.
    small = run_single(n=48, ell=3.0, sigma=0.01, seed=0, n_events=500, transient=100)
    big = run_single(n=48, ell=3.0, sigma=0.30, seed=0, n_events=500, transient=100)
    assert small["mean_moment"] != big["mean_moment"]


def test_burst_terminates_and_state_stays_finite():
    m = BurridgeKnopoffModel(n=64, ell=3.0, sigma=0.01, seed=1)
    for _ in range(200):
        if not m._load_to_next_threshold():
            break
        moment, _ = m._run_burst()
        assert np.isfinite(moment)
    assert np.all(np.isfinite(m.u)) and np.all(np.isfinite(m.v))


def test_events_span_multiple_block_sizes():
    # A genuine spring-block chain produces a RANGE of event sizes (single-block
    # slips up to multi-block cascades), not one characteristic size.
    res = run_single(n=64, ell=3.0, sigma=0.01, seed=0, n_events=1000, transient=200)
    sizes = np.asarray(res["sizes"])
    assert sizes.max() > 5                    # multi-block cascades occur
    assert sizes.min() <= 2                   # small single/few-block slips occur
    assert len(np.unique(sizes)) >= 5         # a spread of sizes, not one scale


# -- power-law / heavy-tail metrics -------------------------------------------

def test_positive_moments_drops_nonpositive():
    m = [0.0, -1.0, 2.0, 3.0, 0.0]
    assert np.allclose(positive_moments(m), [2.0, 3.0])


def test_mle_exponent_recovers_known_power_law():
    # Draw a continuous power law p(x) ~ x^-alpha for x>=xmin via inverse-CDF and
    # check the Clauset-Shalizi-Newman MLE recovers alpha within a few stderr.
    rng = np.random.default_rng(0)
    alpha_true, xmin = 2.5, 1.0
    u = rng.random(20000)
    x = xmin * (1.0 - u) ** (-1.0 / (alpha_true - 1.0))
    fit = mle_power_law_exponent(x, xmin=xmin, xmax=np.max(x))
    assert fit["alpha"] == pytest.approx(alpha_true, abs=5 * fit["stderr"])


def test_decades_and_max_over_median():
    m = [1.0, 2.0, 4.0, 8.0, 16.0, 100.0]
    assert decades_spanned(m) == pytest.approx(2.0)          # log10(100/1)
    assert max_over_median(m) == pytest.approx(100.0 / 6.0)  # median of 6 vals


def test_small_event_window_is_ordered_subrange():
    x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 100.0]
    lo, hi = small_event_window(x, lo_pct=50.0, hi_pct=97.5)
    assert lo < hi
    assert lo >= np.min(x) and hi <= np.max(x)


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_single(n=48, ell=3.0, sigma=0.01, seed=7, n_events=300, transient=50)
    b = run_single(n=48, ell=3.0, sigma=0.01, seed=7, n_events=300, transient=50)
    assert a["moments"] == b["moments"]
    assert a["mean_moment"] == b["mean_moment"]


def test_different_seed_differs():
    a = run_single(n=48, ell=3.0, sigma=0.01, seed=1, n_events=300, transient=50)
    b = run_single(n=48, ell=3.0, sigma=0.01, seed=2, n_events=300, transient=50)
    assert a["mean_moment"] != b["mean_moment"]
