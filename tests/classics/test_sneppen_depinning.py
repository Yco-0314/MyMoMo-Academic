"""Faithful-rule + determinism tests for the Sneppen interface-depinning reproduction.

These pin the RULES (extremal minimum-pinning selection, the +1 advance + pinning redraw,
the bounded-slope |dh| <= 1 constraint enforcement, periodicity, the fresh-quenched-pinning
draw range, the record-run avalanche definition, the chi log-log fit, the adjacent-slope
correlation, and determinism). They are faithfulness tests of the RULES, NOT prediction
tests — the locked P1-P3 (roughness exponent chi, heavy-tailed avalanches, adjacent-slope
correlation sign) are evaluated by examples/repro_sneppen_depinning/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.sneppen_depinning import (
    SneppenInterface,
    adjacent_slope_correlation,
    fit_chi,
    heavy_tail_stats,
    mean_adjacent_slope_correlation,
    random_deposition_slope_correlation,
    record_run_avalanches,
    run_interface,
    run_sweep,
)


# -- construction / validation ------------------------------------------------

def test_interface_starts_flat():
    m = SneppenInterface(16, np.random.default_rng(0))
    assert m.L == 16
    assert np.all(m.h == 0)
    assert m.eta.shape == (16,)
    assert np.all((m.eta >= 0.0) & (m.eta < 1.0))
    assert m.width() == pytest.approx(0.0)


def test_too_small_L_raises():
    with pytest.raises(ValueError):
        SneppenInterface(2, np.random.default_rng(0))


def test_run_interface_rejects_bad_args():
    with pytest.raises(ValueError):
        run_interface(16, n_advance=0, seed=0)
    with pytest.raises(ValueError):
        run_interface(16, n_advance=100, seed=0, transient_frac=1.0)


# -- the extremal rule --------------------------------------------------------

def test_advance_raises_the_minimum_pinning_column():
    # Hand-set a clear global-minimum column; one advance must raise EXACTLY that column
    # (its neighbours are not yet lagging by 2, so no forced pull), and redraw its pinning.
    m = SneppenInterface(8, np.random.default_rng(0))
    m.h[:] = 5
    m.eta[:] = 0.9
    m.eta[3] = 0.01                       # unique global minimum
    old_eta3 = m.eta[3]
    acted = m.advance()
    assert acted == pytest.approx(old_eta3)   # returns the acted-on minimum (pre-redraw)
    assert m.h[3] == 6                          # that column advanced by one
    assert np.all(m.h[[0, 1, 2, 4, 5, 6, 7]] == 5)   # neighbours unchanged (no lag-by-2 yet)
    assert m.eta[3] != old_eta3                 # its pinning was redrawn


def test_advance_returns_the_global_minimum():
    m = SneppenInterface(10, np.random.default_rng(1))
    m.eta[:] = np.linspace(0.2, 0.9, 10)
    m.eta[7] = 0.05
    acted = m.advance()
    assert acted == pytest.approx(0.05)


def test_slope_constraint_pulls_up_lagging_neighbour():
    # Put a column one below its neighbours so that after IT is advanced twice it would be
    # 2 above them -> a single advance of a already-high column must drag a neighbour up.
    m = SneppenInterface(6, np.random.default_rng(2))
    # heights: neighbour of the target sits 1 low; advancing the target makes dh = 2 -> pull.
    m.h[:] = np.array([1, 1, 1, 0, 1, 1])       # column 3 lags its right neighbour... set target
    m.eta[:] = 0.9
    m.eta[2] = 0.01                              # global min at column 2 (h=1)
    m.advance()                                  # h[2] -> 2, now h[2]-h[3] = 2 - 0 = 2 : violates
    # After enforcement, no periodic bond may exceed |dh| = 1.
    h = m.h
    L = m.L
    diffs = np.abs(np.roll(h, -1) - h)
    assert np.all(diffs <= 1), f"slope constraint violated: {h.tolist()}"
    # column 3 (the lagging neighbour) must have been pulled up to satisfy the bond.
    assert h[3] >= 1


def test_slope_constraint_propagates_along_a_staircase():
    # A descending staircase: advancing the top by 1 forces a cascade of pull-ups so that
    # EVERY periodic bond ends within |dh| <= 1.
    m = SneppenInterface(8, np.random.default_rng(3))
    m.h[:] = np.array([4, 3, 2, 1, 0, 1, 2, 3])   # a valid (|dh|<=1) staircase, dips at idx 4
    m.eta[:] = 0.9
    m.eta[0] = 0.001                               # advance the top column repeatedly
    for _ in range(6):
        m.eta[int(np.argmin(m.eta))] = 0.001       # keep forcing near-column-0 style advances
        m.advance()
    diffs = np.abs(np.roll(m.h, -1) - m.h)
    assert np.all(diffs <= 1)


def test_slope_constraint_holds_through_a_long_run():
    # Invariant: after ANY number of advances, every periodic nearest-neighbour bond obeys
    # |h[x] - h[x+1]| <= 1. This is the defining constraint of Sneppen model A.
    res = run_interface(24, n_advance=6000, seed=5, transient_frac=0.5)
    h = res["final_heights"]
    diffs = np.abs(np.roll(h, -1) - h)
    assert np.all(diffs <= 1), f"max |dh| = {int(diffs.max())}"


def test_pinning_values_stay_in_unit_interval():
    m = SneppenInterface(20, np.random.default_rng(7))
    for _ in range(2000):
        m.advance()
    assert np.all((m.eta >= 0.0) & (m.eta < 1.0))


def test_width_grows_from_flat():
    # From a flat start (W=0) the interface roughens: the saturated width is strictly > 0.
    res = run_interface(64, n_advance=64 * 300, seed=0)
    assert res["w_sat"] > 0.5
    assert res["final_width"] > 0.0


# -- P2 helper: record-run avalanches -----------------------------------------

def test_record_run_avalanches_on_hand_signal():
    # signal: 0.1 (first record, start) then a run below it, then 0.5 (new record), etc.
    # records at indices 0 (0.1), 3 (0.5), 6 (0.9). Advances between: 2 (idx1,2), 2 (idx4,5),
    # then trailing 0 after the last record.
    signal = [0.1, 0.05, 0.08, 0.5, 0.2, 0.3, 0.9]
    sizes = record_run_avalanches(signal)
    # avalanche 1: between record@0 and record@3 -> 2 advances (idx 1,2)
    # avalanche 2: between record@3 and record@6 -> 2 advances (idx 4,5)
    # avalanche 3 (trailing): 0 advances after record@6
    assert sizes.tolist() == [2, 2, 0]


def test_record_run_avalanches_monotone_signal_all_zero():
    # A strictly increasing signal sets a new record every step -> every avalanche is size 0.
    signal = [0.1, 0.2, 0.3, 0.4]
    sizes = record_run_avalanches(signal)
    assert sizes.tolist() == [0, 0, 0, 0]


def test_heavy_tail_stats_hand_values():
    sizes = [0, 1, 1, 2, 10, 100]        # nonzero: 1,1,2,10,100 -> median 2, max 100
    stats = heavy_tail_stats(sizes)
    assert stats["n_nonzero"] == 5
    assert stats["max"] == 100.0
    assert stats["min_nonzero"] == 1.0
    assert stats["median_nonzero"] == 2.0
    assert stats["decades"] == pytest.approx(2.0)          # log10(100) - log10(1)
    assert stats["max_over_median"] == pytest.approx(50.0)


# -- P1 helper: chi log-log fit -----------------------------------------------

def test_fit_chi_recovers_exact_power_law():
    # W = 0.7 * L^0.63 exactly -> the log-log slope must be 0.63 and r2 == 1, monotone True.
    Ls = [32, 64, 128, 256]
    chi_true = 0.63
    w = [0.7 * (L ** chi_true) for L in Ls]
    fit = fit_chi(Ls, w)
    assert fit["chi"] == pytest.approx(chi_true, abs=1e-9)
    assert fit["r2"] == pytest.approx(1.0, abs=1e-9)
    assert fit["monotone_increasing"] is True


def test_fit_chi_flags_non_monotone():
    Ls = [32, 64, 128]
    w = [2.0, 1.0, 3.0]                    # not monotone increasing
    fit = fit_chi(Ls, w)
    assert fit["monotone_increasing"] is False


# -- P3 helper: adjacent-slope correlation ------------------------------------

def test_adjacent_slope_correlation_flat_is_zero():
    assert adjacent_slope_correlation(np.zeros(16)) == pytest.approx(0.0)


def test_adjacent_slope_correlation_alternating_is_negative():
    # A perfectly alternating slope field (+1,-1,+1,-1,...) is maximally anticorrelated: each
    # slope is the negative of its neighbour -> correlation exactly -1.
    dh = np.array([1.0, -1.0] * 8)
    assert adjacent_slope_correlation(dh) == pytest.approx(-1.0)


def test_adjacent_slope_correlation_constant_ramp_is_positive():
    # A constant nonzero slope has zero variance -> degenerate -> returns 0 (guard).
    assert adjacent_slope_correlation(np.full(16, 2.0)) == pytest.approx(0.0)
    # A block pattern (long +1 run then long -1 run) has adjacent slopes mostly equal ->
    # strongly POSITIVE correlation.
    dh = np.array([1.0] * 8 + [-1.0] * 8)
    assert adjacent_slope_correlation(dh) > 0.5


def test_mean_adjacent_slope_correlation_averages_snapshots():
    s1 = np.array([1.0, -1.0] * 8)         # corr -1
    s2 = np.array([1.0] * 8 + [-1.0] * 8)  # corr positive
    m = mean_adjacent_slope_correlation([s1, s2])
    assert m == pytest.approx(0.5 * (adjacent_slope_correlation(s1)
                                     + adjacent_slope_correlation(s2)))


def test_random_deposition_baseline_runs():
    b = random_deposition_slope_correlation(64, n_advance=64 * 200, seed=0)
    assert b["n_snapshots"] > 0
    assert -1.0 <= b["mean_adjacent_slope_correlation"] <= 1.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_interface(32, n_advance=32 * 200, seed=11)
    b = run_interface(32, n_advance=32 * 200, seed=11)
    assert a["w_sat"] == b["w_sat"]
    assert np.array_equal(a["final_heights"], b["final_heights"])
    assert np.array_equal(a["signal"], b["signal"])


def test_different_seed_differs():
    a = run_interface(32, n_advance=32 * 200, seed=1)
    b = run_interface(32, n_advance=32 * 200, seed=2)
    assert not np.array_equal(a["final_heights"], b["final_heights"])


# -- sweep summary shape ------------------------------------------------------

def test_run_sweep_shape_and_monotone_flag():
    out = run_sweep([16, 32, 64], advances_per_L=200, n_seeds=2, seed_base=0)
    assert out["Ls"] == [16, 32, 64]
    assert set(out["w_sat"].keys()) == {16, 32, 64}
    # widths should increase with L for the Sneppen interface.
    ws = out["w_sat_list"]
    assert ws[0] < ws[1] < ws[2]
    assert out["w_sat_monotone_increasing"] is True
    assert np.isfinite(out["chi"])
    assert out["n_avalanches_pooled"] > 0
    assert -1.0 <= out["mean_adjacent_slope_correlation"] <= 1.0
