"""Faithful-rule + determinism tests for the Oslo rice-pile (Christensen et al. 1996)
reproduction.

These pin the slope definition (open right boundary), the drive (grain at site 0), the
stochastic toppling rule (topple when z > z_c, move one grain downslope, RE-DRAW z_c in
{1,2}), thresholds staying in {1,2}, grain conservation / loss at the open boundary, the
avalanche-size count, the discrete-MLE tau, the heavy-tail stats, and determinism. They are
faithfulness tests of the RULES, NOT prediction tests — the locked P1-P3 (tau in [1.4,1.7],
heavy-tailed at large L, <s> grows with L) are evaluated by examples/repro_oslo_ricepile/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.oslo_ricepile import (
    OsloPile,
    ZC_HIGH,
    ZC_LOW,
    drive,
    fit_tau,
    heavy_tail_stats,
    run_single,
)


def _pile(L, seed=0):
    return OsloPile(L, np.random.default_rng(seed))


# -- construction / thresholds ------------------------------------------------

def test_initial_pile_is_empty_and_stable():
    p = _pile(16, seed=0)
    assert p.L == 16
    assert p.total_grains() == 0
    assert np.all(p.h == 0)
    assert p.is_stable()  # an empty pile has all slopes 0 <= z_c


def test_thresholds_are_in_allowed_set():
    p = _pile(64, seed=3)
    assert set(np.unique(p.zc)).issubset({ZC_LOW, ZC_HIGH})
    # and both values actually occur across 64 sites (uniform draw over {1,2}).
    assert set(np.unique(p.zc)) == {1, 2}


def test_invalid_L_raises():
    with pytest.raises(ValueError):
        OsloPile(0, np.random.default_rng(0))
    with pytest.raises(ValueError):
        OsloPile(-4, np.random.default_rng(0))


# -- slope definition (open right boundary) -----------------------------------

def test_slopes_open_right_boundary():
    p = _pile(4, seed=0)
    p.h[:] = np.array([5, 3, 2, 1])
    z = p.slopes()
    # interior slopes are h[i]-h[i+1]; the last site's slope is h[L-1] (ground = 0).
    assert list(z) == [5 - 3, 3 - 2, 2 - 1, 1]


def test_slope_of_flat_interior_is_zero_except_last():
    p = _pile(5, seed=0)
    p.h[:] = np.array([2, 2, 2, 2, 0])
    z = p.slopes()
    assert list(z[:-2]) == [0, 0, 0]      # flat interior
    assert z[3] == 2                        # step down to the last site
    assert z[4] == 0                        # last site is at ground level


# -- drive rule (grain added at site 0) ---------------------------------------

def test_drive_adds_grain_at_site_zero_when_stable():
    # A pile that stays stable after a drop: the grain simply lands on site 0.
    p = _pile(8, seed=1)
    p.h[:] = 0
    p.zc[:] = 2                              # high threshold -> first drop cannot topple
    s = p.drive_one()
    assert s == 0                            # no topplings
    assert p.h[0] == 1                       # grain sits on site 0
    assert p.total_grains() == 1


# -- toppling rule: move one grain downslope, count topplings -----------------

def test_single_toppling_moves_one_grain_right():
    # Construct a pile where exactly site 0 is over threshold and toppling it makes the pile
    # stable in one step. Heights [2,0,...]: z[0]=2. Set z_c[0]=1 so z[0]>z_c[0]; toppling
    # gives h=[1,1,0,...] with z[0]=0. Force all other z_c high so nothing else moves.
    p = _pile(5, seed=0)
    p.h[:] = np.array([2, 0, 0, 0, 0])
    p.zc[:] = 2
    p.zc[0] = 1
    s = p.relax()
    assert s == 1                            # exactly one toppling
    assert list(p.h) == [1, 1, 0, 0, 0]      # one grain moved from site 0 to site 1
    assert p.total_grains() == 2             # no grains lost (toppling was interior)


def test_grain_leaves_at_open_right_boundary():
    # A toppling at the LAST site sends its grain off the open boundary: total grains drop.
    p = _pile(3, seed=0)
    p.h[:] = np.array([0, 0, 2])             # z[2] = 2 (open boundary), z_c[2] = 1 -> topple
    p.zc[:] = 2
    p.zc[2] = 1
    before = p.total_grains()
    s = p.relax()
    assert s == 1
    assert p.h[2] == 1                        # last site lost one grain
    assert p.total_grains() == before - 1    # the grain LEFT the system (open boundary)


def test_relax_only_topples_over_threshold():
    # z[i] == z_c[i] is stable (topple is strict > ). Height step equal to threshold: no move.
    p = _pile(4, seed=0)
    p.h[:] = np.array([2, 0, 0, 0])          # z[0] = 2
    p.zc[0] = 2                                # z[0] == z_c[0] -> NOT over threshold
    p.zc[1:] = 2
    s = p.relax()
    assert s == 0
    assert list(p.h) == [2, 0, 0, 0]


def test_avalanche_size_counts_all_topplings():
    # A grain added to a critically-poised pile can trigger several topplings; the count is
    # the number of individual site-topplings, which conserves/loses grains consistently.
    p = _pile(6, seed=2)
    # Build a steep staircase h = [3,2,1,0,...] with all z_c = 1 so several sites are poised.
    p.h[:] = np.array([3, 2, 1, 0, 0, 0])
    p.zc[:] = 1
    grains_before = p.total_grains()
    s = p.drive_one()
    # after adding at site 0 and relaxing, the pile must be stable and s must be > 0.
    assert s > 0
    assert p.is_stable()
    # grain accounting: grains_before + 1 added - (grains that left off the right) == total now
    grains_lost = grains_before + 1 - p.total_grains()
    assert grains_lost >= 0                   # only the open right boundary can lose grains


# -- threshold re-draw on toppling --------------------------------------------

def test_threshold_redrawn_stays_in_set_after_many_avalanches():
    # After driving many grains (lots of topplings, hence lots of re-draws), every z_c is
    # still in {1,2}. This guards the stochastic-threshold re-draw rule.
    p = _pile(32, seed=5)
    drive(p, 4000, record=False)
    assert set(np.unique(p.zc)).issubset({ZC_LOW, ZC_HIGH})


def test_threshold_actually_gets_redrawn():
    # Force a deterministic re-draw: after a toppling, the toppled site's z_c is re-drawn.
    # With a controlled RNG we can't predict the value, but we CAN check it is in {1,2} and
    # that toppling occurred (so the re-draw code path ran).
    p = _pile(4, seed=7)
    p.h[:] = np.array([2, 0, 0, 0])
    p.zc[:] = 2
    p.zc[0] = 1
    s = p.relax()
    assert s == 1
    assert p.zc[0] in (1, 2)                  # re-drawn, still in the allowed set


# -- stationarity sanity (a driven pile reaches a nonzero steady state) --------

def test_driven_pile_reaches_nonzero_steady_state():
    # After enough grains, a small pile is non-empty and produces avalanches. This is a
    # RULE sanity check (the drive/relax loop does something), not a prediction grade.
    res = run_single(32, transient=2000, n_avalanches=2000, seed=0)
    assert res["final_top_height"] > 0        # the pile built up
    assert res["n_nonzero"] > 0               # some avalanches happened
    assert res["max_size"] >= 1


# -- discrete-MLE tau ---------------------------------------------------------

def test_fit_tau_recovers_known_exponent():
    # Synthetic samples from the EXACT discrete power law P(s) = s^{-tau}/zeta(tau, kmin),
    # s = kmin, kmin+1, ...  (the distribution fit_tau's MLE assumes). The MLE should recover
    # tau_true. This validates the estimator itself (not a prediction). We build the discrete
    # CDF over a large truncated support and inverse-transform sample from it — flooring a
    # continuous Pareto would NOT give this distribution and biases the estimate low.
    from scipy.special import zeta as _zeta

    rng = np.random.default_rng(0)
    tau_true = 1.55
    kmin = 1
    s_vals = np.arange(kmin, 500_000)
    pmf = s_vals.astype(np.float64) ** (-tau_true) / _zeta(tau_true, kmin)
    pmf = pmf / pmf.sum()                       # renormalize over the truncated support
    cdf = np.cumsum(pmf)
    u = rng.random(300_000)
    sizes = s_vals[np.searchsorted(cdf, u)]
    out = fit_tau(sizes, kmin=kmin)
    assert abs(out["tau"] - tau_true) < 0.03
    assert out["n_tail"] == int(sizes.size)


def test_fit_tau_excludes_zero_avalanches():
    # Zero-size avalanches are NOT part of the tail; fit_tau(kmin=1) must ignore them.
    sizes = [0, 0, 0, 1, 2, 3, 5, 8, 13, 21]
    out = fit_tau(sizes, kmin=1)
    assert out["n_tail"] == 7                  # only the seven s>=1 entries


# -- heavy-tail stats ---------------------------------------------------------

def test_heavy_tail_stats_on_hand_sizes():
    sizes = [0, 1, 1, 2, 10, 1000]
    ht = heavy_tail_stats(sizes)
    assert ht["n_nonzero"] == 5
    assert ht["max"] == 1000.0
    assert ht["min_nonzero"] == 1.0
    assert ht["median_nonzero"] == 2.0
    assert ht["decades"] == pytest.approx(3.0)             # log10(1000) - log10(1)
    assert ht["max_over_median"] == pytest.approx(500.0)   # 1000 / 2


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_single(64, transient=3000, n_avalanches=3000, seed=11)
    b = run_single(64, transient=3000, n_avalanches=3000, seed=11)
    assert a["sizes"] == b["sizes"]
    assert a["mean_size"] == b["mean_size"]
    assert a["max_size"] == b["max_size"]


def test_different_seed_differs():
    a = run_single(64, transient=3000, n_avalanches=3000, seed=1)
    b = run_single(64, transient=3000, n_avalanches=3000, seed=2)
    # Different seeded thresholds/re-draws -> the avalanche stream differs.
    assert a["sizes"] != b["sizes"]
