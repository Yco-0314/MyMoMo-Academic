"""Faithful-rule + determinism tests for the Pastor-Satorras-Vespignani (2001) SIS-on-
scale-free-networks reproduction.

These pin: the network generators (BA degree/count invariants, ER/regular <k>, degree
moments), the HMF threshold formula lambda_c = <k>/<k^2>, the synchronous SIS update rule
(recovery, force of infection, absorbing state), quasi-stationary restart, agreement
between the faithful platform path and the fast numpy path, and the stretched-exponential
fit method on a hand-built input. They are FAITHFULNESS tests, NOT prediction tests — the
locked P1/P2/P3 are graded by examples/repro_pastor_satorras_vespignani/run.py.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from abm_auto.classics.pastor_satorras_vespignani import (
    Network,
    NetworkSISModel,
    build_ba,
    build_er,
    build_regular,
    estimate_threshold,
    fit_stretched_exponential,
    sis_prevalence_ensemble,
    sis_qs_run,
)


# -- network generation -------------------------------------------------------

def test_ba_node_and_edge_counts():
    m = 3
    n = 500
    net = build_ba(n, m, seed=0)
    assert net.n == n
    # min degree is m (every node born with m edges); mean degree -> 2m
    assert int(net.degree.min()) == m
    assert abs(net.mean_degree() - 2 * m) < 0.5
    # simple graph: symmetric, no self-loops
    for i in range(0, n, 37):
        assert i not in net.adjacency[i]
        for j in net.adjacency[i]:
            assert i in net.adjacency[j]


def test_ba_second_moment_grows_with_n():
    # <k^2> should grow with N on BA (heavy tail); this is what drives lambda_c -> 0.
    small = build_ba(1000, 3, seed=1)
    big = build_ba(20000, 3, seed=1)
    assert big.second_moment() > small.second_moment()
    # HMF threshold shrinks with N on BA.
    assert big.hmf_threshold() < small.hmf_threshold()


def test_er_mean_degree_and_finite_second_moment():
    net = build_er(5000, 6.0, seed=2)
    assert abs(net.mean_degree() - 6.0) < 0.4
    # ER (Poisson): <k^2> ~= <k>^2 + <k> = 42; finite, ~ homogeneous.
    assert abs(net.second_moment() - (36.0 + 6.0)) < 6.0
    # HMF threshold ~ 1/<k> ~ 0.14-0.17.
    assert 0.10 < net.hmf_threshold() < 0.21


def test_regular_graph_exact_degree_and_threshold():
    net = build_regular(2000, 6, seed=3)
    assert int(net.degree.min()) == 6
    assert int(net.degree.max()) == 6
    # <k^2> = 36 exactly, lambda_c = 6/36 = 1/6.
    assert net.second_moment() == pytest.approx(36.0)
    assert net.hmf_threshold() == pytest.approx(1.0 / 6.0)


def test_hmf_threshold_formula():
    # Hand-built tiny graph: a path 0-1-2 has degrees [1,2,1]; <k>=4/3, <k^2>=6/3=2.
    adj = [set() for _ in range(3)]
    adj[0].add(1); adj[1].add(0)
    adj[1].add(2); adj[2].add(1)
    net = Network(3, adj)
    assert net.mean_degree() == pytest.approx(4.0 / 3.0)
    assert net.second_moment() == pytest.approx(2.0)
    assert net.hmf_threshold() == pytest.approx((4.0 / 3.0) / 2.0)


def test_csr_neighbours_match_adjacency():
    net = build_ba(300, 3, seed=5)
    for i in range(0, 300, 11):
        csr = set(int(x) for x in net.indices[net.indptr[i]:net.indptr[i + 1]])
        assert csr == net.adjacency[i]


# -- SIS update rule (faithful platform path) ---------------------------------

def test_recovery_dt_one_recovers_every_step_with_no_infection():
    # lam=0: no infection. With dt=1 (mu=1) all infecteds recover in one step -> extinct
    # (qs off so it truly absorbs).
    net = build_regular(200, 6, seed=0)
    res = NetworkSISModel(net, lam=0.0, dt=1.0, rho0=0.2, ticks=5, tail=1,
                          seed=0, qs=False).run()
    assert res["I_series"][0] > 0            # seeded
    assert res["I_series"][1] == 0           # all recovered after one step
    assert res["prevalence"] == 0.0


def test_force_of_infection_saturates_high_lambda():
    # With lam=1 every S with >=1 infected neighbour becomes I with high prob.
    # On a connected regular graph seeded densely this stays highly prevalent.
    net = build_regular(300, 6, seed=1)
    res = sis_qs_run(net, lam=1.0, dt=0.5, rho0=0.5, ticks=30, tail=10, seed=1)
    assert res["prevalence"] > 0.2


def test_below_threshold_dies_out_on_homogeneous():
    # On a regular <k>=6 graph, lambda well below 1/6 should die out (prevalence ~ 0).
    net = build_regular(2000, 6, seed=2)
    res = sis_qs_run(net, lam=0.05, dt=0.5, rho0=0.1, ticks=200, tail=100, seed=2,
                     qs=False)
    assert res["prevalence"] < 0.02


def test_ba_sustains_infection_below_homogeneous_threshold():
    # The PSV signature (sanity, not the graded gate): on BA, lambda=0.05 sits BELOW the
    # homogeneous threshold 1/<k>=0.167 yet still sustains a small but clearly non-zero
    # endemic prevalence (the vanishing-threshold effect). On a homogeneous graph at the
    # same lambda the infection dies out (~0), so any finite BA prevalence is the signature.
    net = build_ba(20000, 3, seed=3)
    res = sis_qs_run(net, lam=0.05, dt=0.5, rho0=0.05, ticks=400, tail=200, seed=3)
    assert res["prevalence"] > 0.0005      # small but finite (BA), vs ~0 for homogeneous


# -- faithful path vs fast numpy path agree -----------------------------------

def test_platform_and_numpy_paths_agree_on_small_net():
    # The two paths implement the identical rule; on the same network + same lambda they
    # should give the same order-of-magnitude metastable prevalence (both are stochastic
    # with independent RNG streams, so we compare means over seeds within a tolerance).
    net = build_regular(400, 6, seed=7)
    plat = [
        NetworkSISModel(net, lam=0.30, dt=0.5, rho0=0.2, ticks=150, tail=80,
                        seed=s, qs=True).run()["prevalence"]
        for s in range(4)
    ]
    fast = [
        sis_qs_run(net, lam=0.30, dt=0.5, rho0=0.2, ticks=150, tail=80, seed=s)["prevalence"]
        for s in range(4)
    ]
    mp = sum(plat) / len(plat)
    mf = sum(fast) / len(fast)
    assert mp > 0.05 and mf > 0.05                 # both sustain above threshold
    assert abs(mp - mf) < 0.12                     # same regime


# -- determinism --------------------------------------------------------------

def test_numpy_path_deterministic_same_seed():
    net = build_ba(2000, 3, seed=9)
    a = sis_qs_run(net, lam=0.1, dt=0.5, rho0=0.05, ticks=100, tail=50, seed=11)
    b = sis_qs_run(net, lam=0.1, dt=0.5, rho0=0.05, ticks=100, tail=50, seed=11)
    assert a["prevalence"] == b["prevalence"]


def test_build_ba_deterministic_same_seed():
    a = build_ba(3000, 3, seed=4)
    b = build_ba(3000, 3, seed=4)
    assert list(a.degree) == list(b.degree)


# -- empty-node handling in the numpy reduceat --------------------------------

def test_isolated_node_counts_zero_infected_neighbours():
    # A graph with an isolated node must never get infected (no neighbours).
    adj = [set() for _ in range(4)]
    adj[0].add(1); adj[1].add(0)
    adj[1].add(2); adj[2].add(1)
    # node 3 is isolated
    net = Network(4, adj)
    # seed only node 3 -> it recovers, no one else ever infected (isolated, no neighbours).
    res = sis_qs_run(net, lam=0.9, dt=1.0, rho0=0.25, ticks=5, tail=1, seed=0, qs=False)
    assert res["I_final"] == 0


# -- estimate_threshold -------------------------------------------------------

def test_estimate_threshold_interpolates_crossing():
    lambdas = [0.02, 0.04, 0.06, 0.08, 0.10]
    prev = [0.0, 0.0, 0.02, 0.05, 0.1]   # crosses rho_star=0.01 between 0.04 and 0.06
    thr = estimate_threshold(lambdas, prev, rho_star=0.01)
    assert 0.04 < thr < 0.06


def test_estimate_threshold_infinite_when_never_crosses():
    lambdas = [0.02, 0.04, 0.06]
    prev = [0.0, 0.0, 0.0]
    assert math.isinf(estimate_threshold(lambdas, prev, rho_star=0.01))


# -- stretched-exponential fit ------------------------------------------------

def test_stretched_exponential_recovers_known_C_and_A():
    # Build rho = A exp(-C/lambda) exactly, then check the fit recovers C, A, R^2=1.
    A, C = 0.8, 0.3
    lambdas = [0.04, 0.05, 0.06, 0.08, 0.10, 0.12]
    prev = [A * math.exp(-C / lam) for lam in lambdas]
    fit = fit_stretched_exponential(lambdas, prev)
    assert fit["C"] == pytest.approx(C, rel=1e-9)
    assert fit["A"] == pytest.approx(A, rel=1e-9)
    assert fit["r_squared"] == pytest.approx(1.0, abs=1e-12)
    assert fit["n_points"] == len(lambdas)


def test_stretched_exponential_ignores_zero_prevalence_points():
    lambdas = [0.02, 0.04, 0.06, 0.08]
    prev = [0.0, 0.01, 0.03, 0.06]      # first point rho=0 is skipped
    fit = fit_stretched_exponential(lambdas, prev)
    assert fit["n_points"] == 3


# -- ensemble helper ----------------------------------------------------------

def test_ensemble_regenerates_network_per_realization():
    res = sis_prevalence_ensemble(
        lambda s: build_ba(2000, 3, seed=s),
        lam=0.1, dt=0.5, rho0=0.05, ticks=100, tail=50,
        n_realizations=3, seed_base=0,
    )
    assert len(res["prevalences"]) == 3
    assert res["mean_prevalence"] >= 0.0
    assert res["second_moment"] > res["mean_degree"]   # heavy tail -> <k^2> >> <k>
