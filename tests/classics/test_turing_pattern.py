"""Faithful-rule + determinism tests for the Turing diffusion-driven instability
(Gierer-Meinhardt) grid-PDE reproduction.

These pin the periodic 5-point Laplacian, the Gierer-Meinhardt reaction (homogeneous
steady state a*=h*=1 is a reaction fixed point), the explicit-Euler synchronous update, the
linear dispersion analysis (critical ratio d_c = 3+2sqrt(2), the fastest-growing mode q*,
the unstable band), the radially-averaged power-spectrum wavenumber estimator (recovers a
planted single-mode field), the spatial-CoV metric, the P3 stationarity helper, and
determinism (same seed -> identical field).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(docs/studies/turing-pattern/PREDICTIONS-locked.md) are evaluated by
examples/repro_turing_pattern/run.py. This is a grid-PDE / cellular reproduction (disclosed
honestly, like gray_scott / game_of_life), not an agent-stepping ABM.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from abm_auto.classics.turing_pattern import (
    D_C,
    DU,
    TuringModel,
    amplitude_is_stationary,
    critical_ratio,
    dispersion_qstar,
    dominant_wavenumber,
    laplacian,
    run_regime,
    unstable_band,
)


# -- periodic Laplacian --------------------------------------------------------

def test_laplacian_of_constant_is_zero():
    f = np.full((16, 16), 3.7)
    lap = laplacian(f, dx=1.0)
    assert np.allclose(lap, 0.0)


def test_laplacian_is_periodic_and_matches_stencil():
    # A single bump on a periodic grid: lap at the bump = (0+0+0+0 - 4*1)/dx^2 = -4;
    # each of its 4 neighbours sees (1 - 0)/dx^2 = +1. Wrap is exercised by putting the
    # bump at a corner.
    n = 8
    f = np.zeros((n, n))
    f[0, 0] = 1.0
    lap = laplacian(f, dx=1.0)
    assert lap[0, 0] == pytest.approx(-4.0)
    assert lap[1, 0] == pytest.approx(1.0)
    assert lap[n - 1, 0] == pytest.approx(1.0)   # wrap up
    assert lap[0, 1] == pytest.approx(1.0)
    assert lap[0, n - 1] == pytest.approx(1.0)   # wrap left


def test_laplacian_scales_with_dx():
    n = 8
    f = np.zeros((n, n))
    f[0, 0] = 1.0
    lap1 = laplacian(f, dx=1.0)
    lap2 = laplacian(f, dx=2.0)
    assert lap2[0, 0] == pytest.approx(lap1[0, 0] / 4.0)   # 1/dx^2 factor


# -- Gierer-Meinhardt reaction fixed point ------------------------------------

def test_homogeneous_state_is_a_reaction_fixed_point():
    # a = h = 1 everywhere with EQUAL diffusion (d=1): the reaction vanishes and the
    # Laplacians vanish, so one Euler step leaves the field exactly put.
    m = TuringModel(Du=0.5, Dv=0.5, noise=0.0, n=16, seed=0)
    assert np.allclose(m.a, 1.0) and np.allclose(m.h, 1.0)
    m.step()
    assert np.allclose(m.a, 1.0, atol=1e-12)
    assert np.allclose(m.h, 1.0, atol=1e-12)


def test_reaction_signs_off_the_fixed_point():
    # Bump the activator above steady state with h held at 1: da/dt = rho(a^2/h - a) =
    # rho*a(a-1) > 0 for a>1 (autocatalysis), and the inhibitor source a^2 - h > 0 grows h.
    m = TuringModel(Du=0.5, Dv=0.5, noise=0.0, n=8, seed=0)
    m.a[:] = 1.2
    m.h[:] = 1.0
    a0 = m.a.copy()
    h0 = m.h.copy()
    m.step()
    assert np.all(m.a > a0)          # activator self-enhances
    assert np.all(m.h > h0)          # inhibitor is produced by the activator


# -- linear dispersion analysis (the P2 reference) ----------------------------

def test_critical_ratio_is_classic_gierer_meinhardt_value():
    assert critical_ratio() == pytest.approx(3.0 + 2.0 * math.sqrt(2.0))
    assert D_C == pytest.approx(5.82842712474619)


def test_equal_diffusion_has_no_turing_instability():
    # d = Dv/Du = 1: no unstable band, and no fastest-growing mode (qstar = 0).
    assert unstable_band(1.0, DU, DU) is None
    assert dispersion_qstar(1.0, DU, DU) == 0.0


def test_below_critical_ratio_is_stable_above_is_unstable():
    Du = 0.5
    # just below d_c: still stable (no band); comfortably above: unstable band exists.
    assert unstable_band(1.0, Du, Du * (D_C * 0.99)) is None
    band = unstable_band(1.0, Du, Du * (D_C * 1.5))
    assert band is not None and band[0] < band[1]


def test_qstar_lies_inside_the_unstable_band():
    Du = 0.5
    Dv = 1.5 * D_C * Du
    q = dispersion_qstar(1.0, Du, Dv)
    band = unstable_band(1.0, Du, Dv)
    assert band is not None
    assert band[0] <= q <= band[1]
    assert q == pytest.approx(0.8289, abs=1e-3)   # the locked linear-theory value


# -- power-spectrum wavenumber estimator --------------------------------------

def test_dominant_wavenumber_recovers_a_planted_single_mode():
    # A pure cosine field at radial mode m must be recovered as mode_peak = m, with the
    # angular wavenumber 2*pi*m/(N*dx).
    n = 128
    m_planted = 8
    x = np.arange(n)
    X, _Y = np.meshgrid(x, x, indexing="ij")
    field = 1.0 + 0.3 * np.cos(2.0 * math.pi * m_planted * X / n)
    wn = dominant_wavenumber(field, dx=1.0)
    assert wn["mode_peak"] == m_planted
    assert wn["k_angular"] == pytest.approx(2.0 * math.pi * m_planted / n)


def test_dominant_wavenumber_excludes_dc_offset():
    # The DC (mean) bin is always zeroed, so a large constant offset added to a genuine
    # single-mode field cannot masquerade as the dominant wavenumber: mode 8 still wins.
    n = 64
    m_planted = 8
    x = np.arange(n)
    X, _Y = np.meshgrid(x, x, indexing="ij")
    field = 100.0 + 0.3 * np.cos(2.0 * math.pi * m_planted * X / n)   # huge DC offset
    wn = dominant_wavenumber(field, dx=1.0)
    assert wn["radial_power"][0] == 0.0        # DC bin excluded
    assert wn["mode_peak"] == m_planted        # the real mode still dominates


def test_dominant_wavenumber_flat_field_has_no_power():
    # A perfectly constant field has zero radial power everywhere (nothing to detect).
    field = np.full((64, 64), 5.0)
    wn = dominant_wavenumber(field, dx=1.0)
    assert all(p == 0.0 for p in wn["radial_power"])


# -- CoV metric ---------------------------------------------------------------

def test_cov_zero_for_homogeneous_field():
    m = TuringModel(Du=0.5, Dv=0.5, noise=0.0, n=16, seed=0)
    assert m.spatial_cov() == pytest.approx(0.0, abs=1e-12)


def test_cov_positive_for_patterned_field():
    m = TuringModel(Du=0.5, Dv=0.5, noise=0.0, n=16, seed=0)
    m.a[::2, :] = 2.0        # stripe the activator -> nonzero spatial variation
    assert m.spatial_cov() > 0.05


# -- model construction + guards ----------------------------------------------

def test_ic_is_perturbed_homogeneous_state():
    m = TuringModel(Du=0.5, Dv=1.5 * D_C * 0.5, noise=0.01, n=32, seed=0)
    assert m.a.shape == (32, 32) and m.h.shape == (32, 32)
    assert m.a.mean() == pytest.approx(1.0, abs=0.02)
    assert m.h.mean() == pytest.approx(1.0, abs=0.02)
    assert 0.0 < m.a.std() < 0.05          # small perturbation, not a big kick


def test_diffusion_ratio_property():
    m = TuringModel(Du=0.5, Dv=2.0, noise=0.0, n=8, seed=0)
    assert m.diffusion_ratio == pytest.approx(4.0)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        TuringModel(n=0)
    with pytest.raises(ValueError):
        TuringModel(Du=0.0)
    with pytest.raises(ValueError):
        TuringModel(Dv=-1.0)
    with pytest.raises(ValueError):
        TuringModel(rho=0.0)
    with pytest.raises(ValueError):
        TuringModel(dt=0.0)
    with pytest.raises(ValueError):
        TuringModel(noise=-0.1)


def test_dt_stability_guard_rejects_too_large_dt():
    # dt >= dx^2/(4 max(Du,Dv)) must be rejected (explicit-Euler diffusion blow-up).
    with pytest.raises(ValueError):
        TuringModel(Du=0.5, Dv=4.0, dx=1.0, dt=1.0, n=8, seed=0)


# -- P3 stationarity helper ---------------------------------------------------

def test_stationarity_helper_flags_flat_and_moving_series():
    steps = [0, 1000, 2000, 3000, 4000, 5000]
    flat = [0.10, 0.50, 0.60, 0.601, 0.6012, 0.6013]     # tail (last 20%) nearly flat
    res_flat = amplitude_is_stationary(steps, flat, tail_frac=0.2,
                                       max_rel_change_per_1e3=0.05)
    assert res_flat["stationary"] is True
    moving = [0.10, 0.20, 0.30, 0.40, 0.50, 0.70]        # tail still climbing fast
    res_moving = amplitude_is_stationary(steps, moving, tail_frac=0.4,
                                         max_rel_change_per_1e3=0.05)
    assert res_moving["stationary"] is False


# -- short dynamics smoke: control stays flat, Turing grows -------------------

def test_control_stays_homogeneous_short_run():
    # d = 1 (Dv = Du): the perturbed field decays back / stays flat (CoV tiny).
    res = run_regime(Du=0.5, Dv=0.5, n=64, dt=0.005, seed=0, n_steps=2000,
                     record_every=1000)
    assert res["final_cov"] < 0.05
    assert res["qstar"] == 0.0 and res["unstable_band"] is None


def test_turing_arm_develops_variation_short_run():
    # d = 1.5 d_c: the unstable band amplifies the perturbation; even a short run shows the
    # CoV climbing well above the homogeneous control, and the linear-theory band exists.
    res = run_regime(Du=0.5, Dv=1.5 * D_C * 0.5, n=64, dt=0.005, seed=0, n_steps=4000,
                     record_every=1000)
    assert res["unstable_band"] is not None
    assert res["qstar"] > 0.0
    assert res["cov_series"][-1] > res["cov_series"][0]     # variation is growing


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_field():
    a = run_regime(Du=0.5, Dv=1.5 * D_C * 0.5, n=48, dt=0.005, seed=7, n_steps=1500,
                   record_every=500)
    b = run_regime(Du=0.5, Dv=1.5 * D_C * 0.5, n=48, dt=0.005, seed=7, n_steps=1500,
                   record_every=500)
    assert a["amplitude_series"] == b["amplitude_series"]
    assert a["final_cov"] == b["final_cov"]
    assert a["k_meas_angular"] == b["k_meas_angular"]


def test_different_seed_differs_but_stays_shaped():
    a = run_regime(Du=0.5, Dv=1.5 * D_C * 0.5, n=48, dt=0.005, seed=1, n_steps=1500,
                   record_every=500)
    b = run_regime(Du=0.5, Dv=1.5 * D_C * 0.5, n=48, dt=0.005, seed=2, n_steps=1500,
                   record_every=500)
    for res in (a, b):
        assert all(x >= 0.0 for x in res["amplitude_series"])
        assert res["k_meas_mode"] >= 0
