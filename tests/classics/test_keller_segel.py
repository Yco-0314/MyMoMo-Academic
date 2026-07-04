"""Faithful-rule + determinism tests for the Keller-Segel chemotaxis reproduction.

These pin the periodic 5-point Laplacian, the CONSERVATIVE UPWIND chemotactic flux (mass
conservation + up-gradient drift direction), the reaction terms (attractant production
a*rho minus decay b*c), the density/CV/low-q metrics, the S->chi derivation, the stability
guard, and determinism. They are faithfulness tests, NOT prediction tests — the locked
P1-P3 (aggregation above threshold, uniform below, long-wavelength dispersion sign check)
are evaluated by examples/repro_keller_segel/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.keller_segel import (
    KellerSegelModel,
    chemotaxis_divergence,
    laplacian,
    low_q_amplitude,
    run_single,
)


# -- laplacian ----------------------------------------------------------------

def test_laplacian_of_constant_is_zero():
    field = np.full((8, 8), 2.3)
    lap = laplacian(field, dx=0.1)
    assert np.allclose(lap, 0.0)


def test_laplacian_periodic_single_bump():
    n = 5
    field = np.zeros((n, n))
    field[2, 2] = 1.0
    dx = 0.5
    lap = laplacian(field, dx=dx)
    # center: (0+0+0+0 - 4*1)/dx^2 ; the 4 edge-neighbours: (1 - 0)/dx^2 each.
    assert lap[2, 2] == pytest.approx(-4.0 / (dx * dx))
    for r, c in [(1, 2), (3, 2), (2, 1), (2, 3)]:
        assert lap[r, c] == pytest.approx(1.0 / (dx * dx))
    # a diagonal neighbour is untouched by the 5-point stencil.
    assert lap[1, 1] == pytest.approx(0.0)


def test_laplacian_wraps_at_boundary():
    n = 4
    field = np.zeros((n, n))
    field[0, 0] = 1.0
    lap = laplacian(field, dx=1.0)
    assert lap[n - 1, 0] == pytest.approx(1.0)
    assert lap[0, n - 1] == pytest.approx(1.0)


# -- the conservative upwind chemotactic flux ---------------------------------

def test_chemotaxis_divergence_conserves_mass():
    # The divergence of a flux built on the cell faces sums to exactly zero on a periodic
    # grid (every face flux enters one cell and leaves its neighbour): mass is conserved.
    rng = np.random.default_rng(0)
    rho = 1.0 + 0.3 * rng.standard_normal((16, 16))
    c = rng.standard_normal((16, 16))
    div = chemotaxis_divergence(rho, c, chi=0.7, dx=0.25)
    assert abs(float(np.sum(div))) < 1e-10


def test_chemotaxis_pulls_density_up_the_gradient():
    # A single density bump in a MONOTONE attractant ramp must be advected toward higher c.
    # Put rho on one cell and a c that increases along +axis0; the chemotactic term should
    # DECREASE rho at that cell (it flows out toward the higher-c neighbour) and increase the
    # up-gradient neighbour. The returned 'div' is the amount ADDED to d rho.
    n = 8
    rho = np.zeros((n, n))
    rho[3, 4] = 1.0
    # c increases with row index (grad c points in +axis0); use a linear ramp.
    c = np.tile(np.arange(n, dtype=float).reshape(n, 1), (1, n))
    div = chemotaxis_divergence(rho, c, chi=1.0, dx=1.0)
    # the occupied cell loses density (flux leaves toward higher c), the +axis0 neighbour gains.
    assert div[3, 4] < 0.0
    assert div[4, 4] > 0.0


def test_chemotaxis_zero_when_attractant_flat():
    rho = np.random.default_rng(1).random((10, 10)) + 0.5
    c = np.full((10, 10), 4.2)          # flat attractant -> no gradient -> no drift
    div = chemotaxis_divergence(rho, c, chi=2.0, dx=0.3)
    assert np.allclose(div, 0.0)


def test_step_conserves_total_mass_no_diffusion_leak():
    # Diffusion (periodic) and the conservative chemotactic flux both conserve total rho.
    m = KellerSegelModel(S=3.0, n=32, side=10.0, dt=1e-3, noise=0.05, seed=2)
    mass0 = float(np.sum(m.rho))
    for _ in range(50):
        m.step()
    mass1 = float(np.sum(m.rho))
    assert mass1 == pytest.approx(mass0, rel=1e-9)


def test_density_stays_non_negative():
    m = KellerSegelModel(S=6.0, n=48, side=15.0, dt=5e-4, noise=0.05, seed=3)
    for _ in range(400):
        m.step()
    assert float(np.min(m.rho)) >= 0.0


# -- reaction terms (attractant production / decay) ---------------------------

def test_attractant_production_and_decay():
    # On a UNIFORM field the Laplacian and the chemotactic flux are exactly 0, so one step
    # is pure local reaction of c: dc = a*rho - b*c. rho only diffuses (flat -> unchanged).
    m = KellerSegelModel(S=2.0, n=6, side=6.0, a=1.5, b=0.5, rho0=1.0, dt=0.01,
                         noise=0.0, seed=0)
    m.rho[:] = 2.0
    m.c[:] = 3.0
    rho0_val, c0_val = 2.0, 3.0
    exp_c = c0_val + m.dt * (m.a * rho0_val - m.b * c0_val)
    m.step()
    assert m.c[0, 0] == pytest.approx(exp_c)
    assert m.rho[0, 0] == pytest.approx(rho0_val)     # flat rho: no diffusion, no chemotaxis


# -- S -> chi derivation ------------------------------------------------------

def test_sensitivity_maps_to_chi():
    # S = chi * a * rho0 / (D_rho * b)  =>  chi = S * D_rho * b / (a * rho0).
    m = KellerSegelModel(S=4.0, n=16, side=8.0, D_rho=2.0, D_c=1.0, a=1.5, b=0.5,
                         rho0=3.0, dt=1e-3)
    assert m.chi == pytest.approx(4.0 * 2.0 * 0.5 / (1.5 * 3.0))
    # S = 0 kills chemotaxis entirely (chi = 0).
    m0 = KellerSegelModel(S=0.0, n=16, side=8.0, dt=1e-3)
    assert m0.chi == 0.0


def test_zero_sensitivity_is_pure_diffusion_decay():
    # With S=0 (chi=0) and a=b=0, the density field just diffuses toward flat; any bump
    # decays in amplitude (max shrinks, min grows) and the mean is preserved.
    m = KellerSegelModel(S=0.0, n=24, side=12.0, a=1e-12, b=1e-12, dt=1e-3, noise=0.0, seed=0)
    m.rho[:] = 1.0
    m.rho[12, 12] = 2.0
    peak0 = float(np.max(m.rho))
    mean0 = float(np.mean(m.rho))
    for _ in range(30):
        m.step()
    assert float(np.max(m.rho)) < peak0            # bump diffuses away
    assert float(np.mean(m.rho)) == pytest.approx(mean0, rel=1e-9)


# -- metrics ------------------------------------------------------------------

def test_peak_ratio_and_cv_on_hand_field():
    m = KellerSegelModel(S=1.0, n=10, side=5.0, rho0=1.0, dt=1e-3, noise=0.0, seed=0)
    m.rho[:] = 1.0
    assert m.peak_ratio() == pytest.approx(1.0)
    assert m.coefficient_of_variation() == pytest.approx(0.0)
    m.rho[5, 5] = 4.0                              # one tall peak
    assert m.peak_ratio() == pytest.approx(4.0)
    assert m.coefficient_of_variation() > 0.0


def test_low_q_amplitude_detects_long_wavelength_mode():
    # A single full cosine wave across the box (the longest-wavelength / |k|=1 mode) must
    # give a non-zero low-q amplitude; a flat field gives zero.
    n = 32
    flat = np.full((n, n), 1.0)
    assert low_q_amplitude(flat) == pytest.approx(0.0, abs=1e-12)
    x = np.arange(n)
    wave = 1.0 + 0.5 * np.cos(2 * np.pi * x / n).reshape(n, 1) * np.ones((1, n))
    assert low_q_amplitude(wave) > 0.0
    # a higher-frequency wave (|k|=4) should NOT register in the |k|=1 shell.
    wave4 = 1.0 + 0.5 * np.cos(2 * np.pi * 4 * x / n).reshape(n, 1) * np.ones((1, n))
    assert low_q_amplitude(wave4) == pytest.approx(0.0, abs=1e-9)


# -- stability guard ----------------------------------------------------------

def test_stability_guard_rejects_too_large_dt():
    with pytest.raises(ValueError):
        KellerSegelModel(S=3.0, n=64, side=20.0, D_rho=1.0, D_c=1.0, dt=1e9)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        KellerSegelModel(S=3.0, n=0)
    with pytest.raises(ValueError):
        KellerSegelModel(S=-1.0, n=16)
    with pytest.raises(ValueError):
        KellerSegelModel(S=3.0, n=16, D_rho=0.0)
    with pytest.raises(ValueError):
        KellerSegelModel(S=3.0, n=16, rho0=0.0)


# -- run summary shape --------------------------------------------------------

def test_run_summary_shape():
    res = run_single(3.0, n=32, side=10.0, dt=1e-3, n_steps=200, record_every=50, seed=0)
    assert res["S"] == 3.0
    assert len(res["step_series"]) == len(res["peak_series"]) == len(res["cv_series"])
    assert len(res["low_q_series"]) == len(res["step_series"])
    assert res["step_series"][0] == 0 and res["step_series"][-1] == 200
    assert res["mass_rel_drift"] < 1e-9           # conservative scheme
    assert res["final_peak_ratio"] >= 1.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_single(4.0, n=32, side=10.0, dt=1e-3, n_steps=300, record_every=100, seed=7)
    b = run_single(4.0, n=32, side=10.0, dt=1e-3, n_steps=300, record_every=100, seed=7)
    assert a["peak_series"] == b["peak_series"]
    assert a["cv_series"] == b["cv_series"]
    assert a["final_peak_ratio"] == b["final_peak_ratio"]


def test_different_seed_differs():
    a = run_single(4.0, n=32, side=10.0, dt=1e-3, n_steps=300, record_every=100, seed=1)
    b = run_single(4.0, n=32, side=10.0, dt=1e-3, n_steps=300, record_every=100, seed=2)
    # different seeded noise -> the fine density field differs
    assert a["final_cv"] != b["final_cv"] or a["final_peak_ratio"] != b["final_peak_ratio"]
