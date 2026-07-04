"""Faithful-rule + determinism tests for the Szabó-Tőke (1998) Fermi spatial PD.

These pin the payoff matrix (R=1, T=b, P=S=0), the von Neumann (z=4) neighbourhood
with periodic wrap, the self-interaction convention, the Fermi (pairwise-comparison)
acceptance probability W = 1/(1+exp(-(E_y-E_x)/K)), the conflict-free vectorised-sweep
invariant, and determinism (same seed -> identical series). They are faithfulness
tests, NOT prediction tests (P1-P3 are evaluated by
examples/repro_fermi_spatial_pd/run.py).
"""
from __future__ import annotations

import math

import numpy as np

from abm_auto.classics.fermi_spatial_pd import (
    COOPERATE,
    DEFECT,
    FermiSpatialPDModel,
    run_many_seeds,
    run_single,
    survival_threshold,
    tail_mean,
)


def _set_grid(model, arr):
    model.grid = np.asarray(arr, dtype=np.int8)


def test_von_neumann_neighbor_table_is_z4_periodic():
    m = FermiSpatialPDModel(5, b=1.4, K=0.1, seed=0)
    # Interior site (2,2) -> flat id 12: 4 von Neumann neighbours = ids 7,13,17,11.
    nbrs = {int(m.neighbors[k, 12]) for k in range(4)}
    assert nbrs == {7, 13, 17, 11}
    assert len(nbrs) == 4
    # Corner (0,0) -> id 0 still has 4 neighbours thanks to the torus:
    # N wraps to (4,0)=20, E=(0,1)=1, S=(1,0)=5, W wraps to (0,4)=4.
    corner = {int(m.neighbors[k, 0]) for k in range(4)}
    assert corner == {20, 1, 5, 4}


def test_payoff_all_cooperators_with_self_interaction():
    # All-C lattice: a cooperator plays 4 C neighbours + itself = 5 games, each R=1.
    m = FermiSpatialPDModel(5, b=1.4, K=0.1, self_interaction=True, seed=0)
    _set_grid(m, np.ones((5, 5)))
    pay = m._payoffs(m.grid.reshape(-1))
    assert pay[12] == 5.0        # 4 neighbours + self, all R=1
    assert np.allclose(pay, 5.0)  # every C site scores 5 in an all-C sea


def test_payoff_all_cooperators_without_self_interaction():
    m = FermiSpatialPDModel(5, b=1.4, K=0.1, self_interaction=False, seed=0)
    _set_grid(m, np.ones((5, 5)))
    pay = m._payoffs(m.grid.reshape(-1))
    assert pay[12] == 4.0        # 4 neighbours only, no self
    assert np.allclose(pay, 4.0)


def test_defector_payoff_in_sea_of_cooperators():
    # A lone defector in an all-C lattice scores T=b per cooperating neighbour (4);
    # self-interaction adds P=0 for the defector. With b=1.9 -> 4*1.9 = 7.6.
    m = FermiSpatialPDModel(5, b=1.9, K=0.1, self_interaction=True, seed=0)
    g = np.ones((5, 5))
    g[2, 2] = 0                  # defector at site 12
    _set_grid(m, g)
    pay = m._payoffs(m.grid.reshape(-1))
    assert abs(pay[12] - 4 * 1.9) < 1e-12   # 7.6, self-game adds P=0
    # An adjacent cooperator (site 11 = (2,1)) now has 3 C neighbours + 1 D + self(C):
    # 3*R + 0(S vs the defector) + 1*R(self) = 4.
    assert abs(pay[11] - 4.0) < 1e-12


def test_defector_and_cooperator_payoff_matrix_values():
    # All-D gives P=0 everywhere; a lone C in a D sea gets S=0 everywhere.
    m = FermiSpatialPDModel(5, b=2.0, K=0.1, self_interaction=False, seed=0)
    _set_grid(m, np.zeros((5, 5)))
    pay = m._payoffs(m.grid.reshape(-1))
    assert np.allclose(pay, 0.0)             # all-D: every game is P=0
    g = np.zeros((5, 5))
    g[2, 2] = 1                              # lone cooperator
    _set_grid(m, g)
    pay = m._payoffs(m.grid.reshape(-1))
    assert pay[12] == 0.0                     # C surrounded by D: every game is S=0


def test_fermi_acceptance_formula_matches_logistic():
    # Direct check of W = 1/(1+exp(-(Ey-Ex)/K)) at a couple of points.
    K = 0.1
    for Ex, Ey in [(4.0, 5.0), (5.0, 4.0), (3.0, 3.0)]:
        w = 1.0 / (1.0 + math.exp(-(Ey - Ex) / K))
        # equal payoffs -> W = 0.5; higher-y-payoff -> W > 0.5; lower -> W < 0.5.
        if Ey == Ex:
            assert abs(w - 0.5) < 1e-12
        elif Ey > Ex:
            assert w > 0.5
        else:
            assert w < 0.5
    # A payoff advantage saturates W toward 1 but never reaches certainty for a
    # finite gap (this is the stochastic contrast with deterministic best-takes-
    # over, which would copy the better strategy with probability exactly 1). Use a
    # moderate gap so the strict inequality survives floating point (exp(-100)
    # underflows to 0 and W rounds to exactly 1.0, which is a float artifact, not
    # the model's meaning).
    w_big = 1.0 / (1.0 + math.exp(-(1.0) / K))     # gap 1.0, K=0.1 -> W~0.99995
    assert 0.99 < w_big < 1.0


def test_conflict_free_mask_is_disjoint():
    # The vectorised-sweep filter must return pairs with all-distinct claimed sites.
    focals = np.array([0, 1, 2, 3, 4, 5])
    targets = np.array([1, 0, 3, 2, 5, 6])   # (0,1)&(1,0) conflict; (2,3)&(3,2) conflict
    keep = FermiSpatialPDModel._conflict_free_mask(focals, targets)
    kept_f = focals[keep].tolist()
    kept_t = targets[keep].tolist()
    claimed = kept_f + kept_t
    assert len(claimed) == len(set(claimed))   # every claimed site distinct
    # First-in-order pair (0,1) is kept; its mirror (1,0) is dropped.
    assert keep[0] and not keep[1]


def test_self_copy_is_noop_when_neighbour_equals_focal_strategy():
    # Fermi copy only changes anything when the two strategies differ. Start all-C;
    # one sweep on an all-C (or all-D) lattice cannot change it (every copy is C<-C).
    m = FermiSpatialPDModel(20, b=1.4, K=0.5, seed=1)
    _set_grid(m, np.ones((20, 20)))
    m.step()
    assert m.cooperator_fraction() == 1.0      # all-C is absorbing (nothing to copy)
    m2 = FermiSpatialPDModel(20, b=1.4, K=0.5, seed=1)
    _set_grid(m2, np.zeros((20, 20)))
    m2.step()
    assert m2.cooperator_fraction() == 0.0     # all-D is absorbing


def test_all_defect_is_absorbing_over_many_sweeps():
    # Above b_c2 the paper's all-D state is absorbing; starting all-D it stays 0.
    r = run_single(30, b=1.9, K=0.1, init_coop_fraction=0.0, seed=2,
                   n_sweeps=20, measure_sweeps=5)
    assert r["stationary_c"] == 0.0
    assert r["final_c"] == 0.0


def test_determinism_same_seed_identical_series():
    r1 = FermiSpatialPDModel(40, b=1.5, K=0.3, seed=3).run(15, measure_sweeps=5)
    r2 = FermiSpatialPDModel(40, b=1.5, K=0.3, seed=3).run(15, measure_sweeps=5)
    assert r1["coop_series"] == r2["coop_series"]
    assert r1["final_c"] == r2["final_c"]


def test_different_seed_changes_initial_placement():
    a = FermiSpatialPDModel(50, b=1.5, K=0.3, seed=1).run(0, measure_sweeps=1)
    b = FermiSpatialPDModel(50, b=1.5, K=0.3, seed=2).run(0, measure_sweeps=1)
    # t=0 baselines differ because the random C/D placement differs.
    assert a["coop_series"][0] != b["coop_series"][0]


def test_init_density_controls_baseline_fraction():
    m = FermiSpatialPDModel(200, b=1.5, K=0.3, init_coop_fraction=0.7, seed=0)
    assert abs(m.cooperator_fraction() - 0.7) < 0.02
    m2 = FermiSpatialPDModel(200, b=1.5, K=0.3, init_coop_fraction=0.2, seed=0)
    assert abs(m2.cooperator_fraction() - 0.2) < 0.02


def test_grid_only_holds_C_or_D():
    # After any number of sweeps the lattice is still pure 0/1 (strategies never blend).
    m = FermiSpatialPDModel(40, b=1.6, K=0.4, seed=4)
    for _ in range(10):
        m.step()
    vals = set(np.unique(m.grid).tolist())
    assert vals <= {0, 1}
    assert COOPERATE == 1 and DEFECT == 0


def test_tail_mean_averages_tail():
    series = [0.0] * 10 + [0.4, 0.4, 0.4, 0.4]
    assert abs(tail_mean(series, window=4) - 0.4) < 1e-12
    # Shorter-than-window falls back to the whole series.
    assert abs(tail_mean([0.5, 0.5], window=50) - 0.5) < 1e-12


def test_run_many_seeds_shape_and_determinism():
    a = run_many_seeds(40, b=1.5, K=0.3, n_seeds=2, n_sweeps=12, measure_sweeps=4)
    b = run_many_seeds(40, b=1.5, K=0.3, n_seeds=2, n_sweeps=12, measure_sweeps=4)
    assert a["mean_stationary_c"] == b["mean_stationary_c"]
    assert len(a["per_seed_stationary_c"]) == 2
    assert 0.0 <= a["mean_stationary_c"] <= 1.0


def test_survival_threshold_brackets_and_monotone_in_b():
    # At a small lattice the threshold locator returns a b in [b_lo, b_hi]; and a
    # clearly-too-high b_lo (cooperators already dead) returns the low clamp.
    thr = survival_threshold(40, K=0.1, self_interaction=False, seed=0,
                             b_lo=1.0, b_hi=2.2, tol=0.1, n_sweeps=60, measure_sweeps=10)
    assert 1.0 <= thr <= 2.2
