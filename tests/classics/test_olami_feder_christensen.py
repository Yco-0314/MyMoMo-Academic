"""Faithful-rule + determinism tests for the Olami-Feder-Christensen earthquake CA
(Olami, Feder & Christensen 1992) reproduction.

These pin the OFC micro-rules: the uniform drive (after a drive max(force) == f_th),
the threshold topple/redistribution (a topple sends exactly alpha*F_old to each present
neighbour, the site resets to 0, an INTERIOR topple conserves a 4*alpha fraction, an
edge/corner topple LOSES the off-lattice share), the open-boundary geometry (4/3/2
neighbours interior/edge/corner), the avalanche cascade on a hand-built tiny lattice,
the event-size accounting (one event = number of topplings per drive), and determinism
(same seed -> identical event series).

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(heavy-tailed sizes, alpha=0.2 mean > alpha=0.1 mean, stationary + init-independent) are
evaluated by examples/repro_ofc_earthquake/run.py.
"""
from __future__ import annotations

import pytest

from abm_auto.classics.olami_feder_christensen import (
    OFCModel,
    SiteAgent,
    log_histogram,
    run_single,
    _median,
    _summarise_sizes,
)


# -- construction + invariants ------------------------------------------------

def test_population_is_site_agents_on_lattice_within_initial_band():
    m = OFCModel(L=5, alpha=0.2, seed=0)
    assert len(m.agent_list) == 25
    assert all(isinstance(a, SiteAgent) for a in m.agent_list)
    for a in m.agent_list:
        assert 0 <= a.row < 5 and 0 <= a.col < 5
        assert a.id == m.idx(a.row, a.col)
        assert 0.0 <= a.f < m.f_th          # initial forces ~ U[0, f_th)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        OFCModel(L=1)                       # need L > 1
    with pytest.raises(ValueError):
        OFCModel(L=5, alpha=0.0)            # alpha must be > 0
    with pytest.raises(ValueError):
        OFCModel(L=5, alpha=0.3)            # alpha must be <= 0.25
    with pytest.raises(ValueError):
        OFCModel(L=5, f_th=0.0)             # f_th must be > 0


# -- open-boundary geometry: neighbour counts ---------------------------------

def test_neighbour_counts_interior_edge_corner():
    m = OFCModel(L=5, alpha=0.2, seed=0)
    # interior site (2,2) has 4 neighbours
    assert len(m._neighbours[m.idx(2, 2)]) == 4
    # edge site (0,2) has 3 neighbours (one off the top edge is lost)
    assert len(m._neighbours[m.idx(0, 2)]) == 3
    # corner site (0,0) has 2 neighbours (two off-lattice are lost)
    assert len(m._neighbours[m.idx(0, 0)]) == 2
    assert len(m._neighbours[m.idx(4, 4)]) == 2
    assert len(m._neighbours[m.idx(4, 0)]) == 2


def test_neighbours_are_the_von_neumann_set():
    m = OFCModel(L=5, alpha=0.2, seed=0)
    got = set(m._neighbours[m.idx(2, 2)])
    want = {m.idx(1, 2), m.idx(3, 2), m.idx(2, 1), m.idx(2, 3)}
    assert got == want


# -- the DRIVE rule -----------------------------------------------------------

def test_drive_brings_max_exactly_to_threshold():
    m = OFCModel(L=6, alpha=0.2, seed=3)
    delta = m.drive_to_threshold()
    assert delta >= 0.0
    assert max(m.force) == pytest.approx(m.f_th)


def test_drive_adds_the_same_increment_to_every_site():
    m = OFCModel(L=4, alpha=0.2, seed=1)
    before = list(m.force)
    expected_delta = m.f_th - max(before)
    delta = m.drive_to_threshold()
    assert delta == pytest.approx(expected_delta)
    for b, a in zip(before, m.force):
        assert a - b == pytest.approx(delta)


# -- a SINGLE topple: exact bookkeeping ---------------------------------------

def test_single_interior_topple_moves_4_alpha_to_each_neighbour_and_conserves_4alpha():
    # One over-threshold interior site, all others well below: exactly one topple.
    m = OFCModel(L=5, alpha=0.2, seed=0)
    for i in range(m.n_sites):
        m.force[i] = 0.0
    centre = m.idx(2, 2)
    m.force[centre] = 1.0                    # exactly at threshold, interior
    total_before = sum(m.force)
    topples = m.relax()
    assert topples == 1
    # site reset to 0
    assert m.force[centre] == pytest.approx(0.0)
    # each of the 4 neighbours gained alpha * F_old = 0.2 * 1.0 = 0.2
    for j in m._neighbours[centre]:
        assert m.force[j] == pytest.approx(0.2)
    # interior conservation: a 4*alpha = 0.8 fraction of the released 1.0 is retained
    # on the lattice (0.2 to each of 4 neighbours); nothing else changed.
    assert sum(m.force) == pytest.approx(0.8)
    assert sum(m.force) == pytest.approx(4 * m.alpha * 1.0)
    # dissipated share (interior, alpha<0.25) = 1 - 4*alpha of the released force
    assert total_before - sum(m.force) == pytest.approx((1.0 - 4 * m.alpha) * 1.0)


def test_conservative_alpha_quarter_interior_topple_loses_nothing():
    # alpha = 0.25 is the conservative case: an interior topple gives away 4*0.25 = 1.0
    # of the released force, so the lattice total is unchanged.
    m = OFCModel(L=5, alpha=0.25, seed=0)
    for i in range(m.n_sites):
        m.force[i] = 0.0
    centre = m.idx(2, 2)
    m.force[centre] = 1.0
    total_before = sum(m.force)
    m.relax()
    assert sum(m.force) == pytest.approx(total_before)   # conserved
    for j in m._neighbours[centre]:
        assert m.force[j] == pytest.approx(0.25)


def test_corner_topple_loses_the_off_lattice_share():
    # A corner site has only 2 neighbours; the other 2*alpha share is lost (open bdy).
    m = OFCModel(L=5, alpha=0.2, seed=0)
    for i in range(m.n_sites):
        m.force[i] = 0.0
    corner = m.idx(0, 0)
    m.force[corner] = 1.0
    m.relax()
    assert m.force[corner] == pytest.approx(0.0)
    nbrs = m._neighbours[corner]
    assert len(nbrs) == 2
    for j in nbrs:
        assert m.force[j] == pytest.approx(0.2)
    # only 2*alpha = 0.4 retained; the other 0.6 (0.2 dissipated + 0.4 off-lattice) gone.
    assert sum(m.force) == pytest.approx(2 * m.alpha * 1.0)


# -- a CASCADE on a hand-built tiny lattice -----------------------------------

def test_cascade_propagates_across_a_hand_built_lattice():
    # Build a 3x3 lattice where toppling the centre pushes a neighbour over threshold,
    # which then topples too: an event of size >= 2 from a single relax.
    m = OFCModel(L=3, alpha=0.25, seed=0)   # conservative so transfer is largest
    for i in range(m.n_sites):
        m.force[i] = 0.0
    centre = m.idx(1, 1)
    east = m.idx(1, 2)
    # centre at threshold; east pre-loaded just under threshold so the centre's
    # 0.25 share tips it over.
    m.force[centre] = 1.0
    m.force[east] = 0.8
    topples = m.relax()
    # centre topples (size>=1); east receives 0.25 -> 1.05 >= 1 -> topples too.
    assert topples >= 2
    # after the cascade, no site is at/over threshold
    assert max(m.force) < m.f_th


def test_relax_terminates_with_no_site_over_threshold():
    m = OFCModel(L=8, alpha=0.2, seed=5)
    m.drive_to_threshold()
    m.relax()
    assert max(m.force) < m.f_th


def test_a_site_can_topple_more_than_once_in_one_avalanche():
    # Re-loading a site that already toppled, then driving it back over threshold within
    # the SAME avalanche, must count as a second topple. Construct a small chain.
    m = OFCModel(L=3, alpha=0.25, seed=0)
    for i in range(m.n_sites):
        m.force[i] = 0.0
    c = m.idx(1, 1)
    n = m.idx(0, 1)
    s = m.idx(2, 1)
    w = m.idx(1, 0)
    e = m.idx(1, 2)
    # centre over threshold; all four arms pre-loaded so that after the centre topples
    # (0.25 to each), several arms cross threshold and topple, each sending 0.25 back to
    # the centre — enough to push the (now-0) centre back over 1.0 and topple again.
    m.force[c] = 1.0
    for arm in (n, s, w, e):
        m.force[arm] = 0.8        # +0.25 from centre -> 1.05 -> each topples, 0.25 -> c
    topples = m.relax()
    # centre + 4 arms = at least 5 topples; centre receives 4*0.25 = 1.0 back -> topples
    # a second time -> >= 6 topples total.
    assert topples >= 6
    assert max(m.force) < m.f_th


# -- event-size accounting (one drive -> one event) ---------------------------

def test_drive_step_returns_at_least_one_topple():
    # Every drive brings exactly one site to threshold, so every event has size >= 1.
    m = OFCModel(L=10, alpha=0.2, seed=2)
    for _ in range(50):
        s = m.drive_step()
        assert s >= 1
        assert s == m.last_event_size


def test_run_series_length_and_summary_shape():
    res = run_single(L=10, alpha=0.2, seed=0, n_events=200, transient=100)
    assert len(res["event_sizes"]) == 200       # transient NOT recorded
    assert res["n_events"] == 200
    assert res["transient"] == 100
    assert res["max_event_size"] >= res["median_nonzero_event_size"]
    assert all(s >= 1 for s in res["event_sizes"])      # OFC: every event >= 1 topple
    assert res["mean_event_size"] == pytest.approx(
        sum(res["event_sizes"]) / 200)
    assert res["decades_spanned"] >= 0.0


def test_run_rejects_bad_arguments():
    m = OFCModel(L=8, alpha=0.2, seed=0)
    with pytest.raises(ValueError):
        m.run(0, transient=10)
    with pytest.raises(ValueError):
        m.run(10, transient=-1)


# -- summary helpers ----------------------------------------------------------

def test_median_of_odd_and_even():
    assert _median([3, 1, 2]) == pytest.approx(2.0)
    assert _median([1, 2, 3, 4]) == pytest.approx(2.5)
    assert _median([]) == 0.0


def test_summarise_sizes_decades_and_ratio():
    sizes = [1, 1, 2, 10, 1000]
    summ = _summarise_sizes(sizes)
    # min nonzero = 1, max = 1000 -> log10(1000) - log10(1) = 3 decades
    assert summ["decades_spanned"] == pytest.approx(3.0)
    assert summ["max_event_size"] == 1000
    assert summ["min_nonzero_event_size"] == 1
    # median of [1,1,2,10,1000] = 2 ; max/median = 500
    assert summ["median_nonzero_event_size"] == pytest.approx(2.0)
    assert summ["max_over_median_nonzero"] == pytest.approx(500.0)


def test_log_histogram_bins_are_log_spaced_and_count_all():
    sizes = [1, 1, 5, 50, 500]
    h = log_histogram(sizes, bins_per_decade=2)
    assert sum(h["counts"]) == len(sizes)       # every event lands in a bin
    assert len(h["bin_left_edges"]) == len(h["counts"])
    assert h["bin_left_edges"][0] == pytest.approx(1.0)   # first edge at size 1


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_event_series():
    a = run_single(L=20, alpha=0.2, seed=42, n_events=300, transient=200)
    b = run_single(L=20, alpha=0.2, seed=42, n_events=300, transient=200)
    assert a["event_sizes"] == b["event_sizes"]
    assert a["mean_event_size"] == b["mean_event_size"]
    assert a["max_event_size"] == b["max_event_size"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(L=20, alpha=0.2, seed=1, n_events=300, transient=200)
    b = run_single(L=20, alpha=0.2, seed=2, n_events=300, transient=200)
    for res in (a, b):
        assert all(s >= 1 for s in res["event_sizes"])
        assert res["mean_event_size"] > 0.0


def test_initial_forces_are_seed_dependent():
    m1 = OFCModel(L=10, alpha=0.2, seed=1)
    m2 = OFCModel(L=10, alpha=0.2, seed=2)
    assert m1.force != m2.force                 # different seed -> different init draw
