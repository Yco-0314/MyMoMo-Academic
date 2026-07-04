"""Faithful-rule + determinism tests for the Eden growth (KPZ interface) reproduction.

These pin the perimeter-growth rule, the compact radial bulk (D~2), the strip interface width,
the OLS exponent fits (linfit / fit_beta / fit_alpha), and determinism. They are faithfulness tests,
NOT prediction tests — the locked P1-P3 (compact bulk, KPZ beta, KPZ alpha) are evaluated by
examples/repro_eden_growth/run.py.
"""
from __future__ import annotations

import math

import pytest

from abm_auto.classics.eden_growth import (
    RadialEden,
    StripEden,
    fit_alpha,
    fit_beta,
    linfit,
    run_radial,
    saturation_width,
)


# -- OLS exponent fit ---------------------------------------------------------

def test_linfit_recovers_a_line():
    xs = [0.0, 1.0, 2.0, 3.0, 4.0]
    ys = [1.0 + 2.0 * x for x in xs]
    slope, intercept, r2 = linfit(xs, ys)
    assert slope == pytest.approx(2.0)
    assert intercept == pytest.approx(1.0)
    assert r2 == pytest.approx(1.0)


def test_fit_beta_on_synthetic_power_law():
    # W = t^0.33 -> log W = 0.33 log t ; sample below saturation.
    times = [2.0 ** k for k in range(1, 12)]
    widths = [t ** 0.33 for t in times]
    out = fit_beta(times, widths, t_lo=2.0, t_hi=2048.0)
    assert out["beta"] == pytest.approx(0.33, abs=0.03)
    assert out["r2"] > 0.99


def test_fit_alpha_on_synthetic_power_law():
    Ls = [64, 128, 256, 512]
    w_sats = [L ** 0.5 for L in Ls]     # W_sat ~ L^0.5
    out = fit_alpha(Ls, w_sats)
    assert out["alpha"] == pytest.approx(0.5, abs=0.03)


# -- radial (compact bulk, P1) ------------------------------------------------

def test_radial_bulk_is_compact_dimension_two():
    r = run_radial(n=4000, seed=0)
    assert r["D"] >= 1.85          # Eden fills space -> D ~ 2 (compact), unlike DLA
    assert r["density_non_decaying"]


def test_radial_grows_requested_count():
    m = RadialEden(500, seed=1)
    m.grow()
    assert m.size >= 500


# -- strip interface (KPZ, P2/P3) ---------------------------------------------

def test_strip_width_grows_from_flat_seed():
    m = StripEden(64, seed=0)
    w0 = m.width()
    m.run_growth(n_layers=8.0, n_samples=10)
    assert m.width() > w0          # a flat seed roughens as it grows


def test_saturation_width_larger_L_is_rougher():
    w_small = saturation_width(64, seed=0)["w_sat"]
    w_large = saturation_width(256, seed=0)["w_sat"]
    assert w_large > w_small       # W_sat ~ L^alpha increases with L


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_radial(n=800, seed=5)
    b = run_radial(n=800, seed=5)
    assert a["D"] == b["D"]
