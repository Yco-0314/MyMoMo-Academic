"""Faithful-rule + determinism tests for the ant-trail flow CA reproduction.

These pin the MECHANISM of the Chowdhury-Guttal-Nishinari-Schadschneider 2002
ant-trail CA — hard-core exclusion (at most one ant per site, ant-count
conservation), the pheromone-dependent hop probability (Q with pheromone ahead,
q without, q < Q), the deposit-then-evaporate pheromone dynamics (marks under
ants never evaporate; unused marks evaporate with prob f; f=1 wipes every unused
mark; f=0 keeps all marks), the fundamental-diagram observables, and
determinism. They are faithfulness tests of the RULES, NOT prediction tests —
the locked P1/P2/P3 (velocity plateau, right-shifted flow peak, evaporation
recovers NaSch) are graded by examples/repro_ant_trail_bidirectional/run.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.classics.ant_trail_bidirectional import (
    AntTrailModel,
    fundamental_diagram,
    run_density,
    velocity_band_variation,
)


# -- construction / invalid params --------------------------------------------

def test_invalid_params_raise():
    with pytest.raises(ValueError):
        AntTrailModel(L=0, rho=0.3)
    with pytest.raises(ValueError):
        AntTrailModel(L=500, rho=0.0)          # rho must be in (0,1)
    with pytest.raises(ValueError):
        AntTrailModel(L=500, rho=1.0)
    with pytest.raises(ValueError):
        AntTrailModel(L=500, rho=0.3, Q=0.2, q=0.8)   # require q <= Q
    with pytest.raises(ValueError):
        AntTrailModel(L=500, rho=0.3, f=1.5)


def test_initial_placement_count_and_exclusion():
    m = AntTrailModel(L=500, rho=0.3, seed=0)
    assert int(m.occ.sum()) == m.n_ants == round(0.3 * 500)
    assert m.occ.max() <= 1                      # exclusion at t=0
    # pheromone starts exactly on the ants (a consistent initial trail).
    assert np.array_equal(m.pher, m.occ)


# -- exclusion + conservation (the hard-core exclusion process) ---------------

def test_exclusion_never_double_occupies():
    m = AntTrailModel(L=500, rho=0.4, f=0.01, seed=1)
    for _ in range(400):
        m.step()
        assert int(m.occ.max()) <= 1             # never two ants on a site


def test_ant_count_conserved():
    m = AntTrailModel(L=500, rho=0.35, f=0.02, seed=2)
    n0 = int(m.occ.sum())
    for _ in range(400):
        m.step()
    assert int(m.occ.sum()) == n0                # ants are neither created nor destroyed


def test_step_returns_number_of_movers_and_only_forward():
    # On a hand-built ring, count hops and verify each hop is exactly +1 (mod L).
    m = AntTrailModel(L=10, rho=0.3, Q=1.0, q=1.0, f=0.0, seed=0)
    m.occ[:] = 0
    m.occ[0] = 1
    m.occ[5] = 1
    m.pher[:] = 1                                 # pheromone everywhere -> Q=1 hop guaranteed
    before = m.occ.copy()
    moved = m.step()
    assert moved == 2                             # both isolated ants have an empty site ahead
    # each ant advanced exactly one site.
    assert m.occ[1] == 1 and m.occ[0] == 0
    assert m.occ[6] == 1 and m.occ[5] == 0
    assert int(m.occ.sum()) == int(before.sum())


def test_blocked_ant_cannot_move():
    # Two adjacent ants: the front one is blocked by nothing (moves), the back one is
    # blocked by the front one AT THE FROZEN current state (cannot move this tick).
    m = AntTrailModel(L=10, rho=0.3, Q=1.0, q=1.0, f=0.0, seed=0)
    m.occ[:] = 0
    m.occ[3] = 1
    m.occ[4] = 1                                  # ant at 3 is blocked by ant at 4
    m.pher[:] = 1
    moved = m.step()
    # ant at 4 -> 5 (front, empty ahead). ant at 3 was blocked (4 occupied at frozen state).
    assert m.occ[5] == 1 and m.occ[4] == 0
    assert m.occ[3] == 1                          # blocked ant stayed
    assert moved == 1


# -- the pheromone-dependent hop probability (Q vs q) -------------------------

def test_hop_probability_uses_pheromone_ahead():
    # Deterministic edges: Q=1 with pheromone ahead => the ant ALWAYS hops;
    # q=0 without pheromone ahead => the ant NEVER hops. Isolate one ant each.
    # (a) pheromone on the target ahead -> hop.
    m = AntTrailModel(L=10, rho=0.3, Q=1.0, q=0.0, f=0.0, seed=0)
    m.occ[:] = 0; m.occ[2] = 1
    m.pher[:] = 0; m.pher[3] = 1                  # mark on the site AHEAD (target)
    assert m.step() == 1 and m.occ[3] == 1

    # (b) no pheromone on the target ahead -> with q=0, never hops.
    m2 = AntTrailModel(L=10, rho=0.3, Q=1.0, q=0.0, f=0.0, seed=0)
    m2.occ[:] = 0; m2.occ[2] = 1
    m2.pher[:] = 0                                # no mark ahead
    assert m2.step() == 0 and m2.occ[2] == 1


def test_pheromone_behind_does_not_enhance_hop():
    # The hop rate depends on the mark AHEAD (target i+1), not behind. A mark only
    # at the current site (behind the move) must NOT grant the Q rate: with q=0 the
    # ant cannot move even though its own site is marked.
    m = AntTrailModel(L=10, rho=0.3, Q=1.0, q=0.0, f=0.0, seed=0)
    m.occ[:] = 0; m.occ[2] = 1
    m.pher[:] = 0; m.pher[2] = 1                  # mark under the ant, NOT ahead
    assert m.step() == 0 and m.occ[2] == 1


# -- pheromone deposit + evaporation ------------------------------------------

def test_pheromone_deposited_on_occupied_sites():
    # After a step every occupied site carries a mark (ants deposit/refresh).
    m = AntTrailModel(L=500, rho=0.3, f=0.5, seed=3)
    m.step()
    occ = m.occ == 1
    assert np.all(m.pher[occ] == 1)              # every ant sits on a marked site


def test_mark_under_ant_never_evaporates():
    # f=1 would wipe every UNUSED mark, but a mark under an ant is refreshed and
    # must survive. Build a single stuck ant (blocked ahead) on a fully-marked ring.
    m = AntTrailModel(L=10, rho=0.3, Q=1.0, q=1.0, f=1.0, seed=0)
    m.occ[:] = 0
    m.occ[3] = 1
    m.occ[4] = 1                                  # ant at 3 is blocked and stays
    m.pher[:] = 1
    m.step()
    # ant at 3 stayed (blocked) -> its site is still occupied -> its mark refreshed.
    assert m.occ[3] == 1 and m.pher[3] == 1


def test_full_evaporation_wipes_all_unused_marks():
    # f=1: every marked site with NO ant loses its mark in one step.
    m = AntTrailModel(L=20, rho=0.3, f=1.0, seed=4)
    m.occ[:] = 0
    m.occ[10] = 1                                 # one ant
    m.pher[:] = 1                                 # everything marked
    m.step()
    # after the step: only sites currently occupied keep a mark; all else evaporates.
    unoccupied = m.occ == 0
    assert np.all(m.pher[unoccupied] == 0)
    assert m.pher[m.occ == 1].min() == 1


def test_zero_evaporation_keeps_all_marks():
    # f=0: no unused mark ever evaporates; the marked set only GROWS (deposit only).
    m = AntTrailModel(L=500, rho=0.3, f=0.0, seed=5)
    marked0 = int(m.pher.sum())
    for _ in range(50):
        m.step()
    assert int(m.pher.sum()) >= marked0          # marks are never removed at f=0


# -- observables + band metric ------------------------------------------------

def test_velocity_bounds_and_flow_identity():
    r = run_density(500, 0.3, f=0.01, seed=0, transient=200, measure=200)
    assert 0.0 <= r["mean_velocity"] <= 1.0      # <v> is a hop fraction in [0,1]
    assert r["flow"] == pytest.approx(r["rho"] * r["mean_velocity"])
    assert r["n_ants"] == round(0.3 * 500)


def test_low_hop_rate_gives_low_velocity():
    # With q=Q=0.1 (uniform tiny hop prob), the tail-averaged velocity must be small
    # (bounded by the hop prob) — a sanity check that <v> tracks the hop probability.
    r = run_density(500, 0.2, Q=0.1, q=0.1, f=0.5, seed=0, transient=300, measure=300)
    assert r["mean_velocity"] <= 0.15


def test_band_variation_flat_vs_declining():
    dens = [0.2, 0.3, 0.4, 0.5]
    flat = [0.30, 0.30, 0.30, 0.30]
    assert velocity_band_variation(dens, flat, 0.2, 0.5)["variation"] == pytest.approx(0.0)
    declining = [0.40, 0.30, 0.20, 0.10]         # (0.40-0.10)/0.40 = 0.75
    v = velocity_band_variation(dens, declining, 0.2, 0.5)
    assert v["variation"] == pytest.approx(0.75)
    assert v["n_band"] == 4


def test_fundamental_diagram_shape_and_argmax():
    dens = [0.1, 0.3, 0.5, 0.7, 0.9]
    fd = fundamental_diagram(500, dens, f=0.01, seeds=(0, 1), transient=200, measure=200)
    assert len(fd["flow"]) == len(fd["mean_velocity"]) == len(dens)
    assert fd["rho_star"] in dens
    assert fd["peak_index"] == int(np.argmax(fd["flow"]))
    assert fd["peak_flow"] == pytest.approx(max(fd["flow"]))
    # flow at the extremes must be lower than at the interior peak (a peaked diagram).
    assert fd["flow"][0] < fd["peak_flow"]
    assert fd["flow"][-1] < fd["peak_flow"]


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed():
    a = run_density(500, 0.3, f=0.005, seed=7, transient=300, measure=300)
    b = run_density(500, 0.3, f=0.005, seed=7, transient=300, measure=300)
    assert a["mean_velocity"] == b["mean_velocity"]
    assert a["flow"] == b["flow"]
    assert a["mean_pheromone_fraction"] == b["mean_pheromone_fraction"]


def test_different_seed_differs():
    a = run_density(500, 0.45, f=0.005, seed=1, transient=300, measure=300)
    b = run_density(500, 0.45, f=0.005, seed=2, transient=300, measure=300)
    # different seeded placement/draws -> the tail-averaged velocity differs
    assert a["mean_velocity"] != b["mean_velocity"]
