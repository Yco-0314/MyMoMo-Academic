"""Faithful-rule + determinism tests for the Relative-Agreement with extremists
(Deffuant, Amblard, Weisbuch & Faure 2002) reproduction.

These pin the segment overlap ``h_ij``, the relative-agreement firing gate
(``h_ij > u_i``), the asymmetric opinion + uncertainty update with the ``u_i``
(NOT ``2*u_i``) denominator, the extremist seeding (fraction, poles, delta split, low
uncertainty), the locked polarization metric ``y = p'_+^2 + p'_-^2`` over the
initially-moderate agents, the sweep micro-rule, determinism (same seed -> identical
result), and the single-pole (P3) readout helper.

They are faithfulness tests, NOT prediction tests — the locked predictions P1-P3
(docs/studies/deffuant-amblard/PREDICTIONS-locked.md) are evaluated by
examples/repro_deffuant_amblard/run.py.
"""
from __future__ import annotations

import pytest

from abm_auto.classics.deffuant_amblard import (
    RAAgent,
    RelativeAgreementModel,
    run_single,
    single_pole_capture_stats,
)


# -- construction + population --------------------------------------------------

def test_population_split_moderates_and_extremists():
    m = RelativeAgreementModel(n=200, p_e=0.2, u_e=0.1, big_u=0.4, delta=0.0, seed=0)
    assert len(m.agent_list) == 200
    assert all(isinstance(a, RAAgent) for a in m.agent_list)
    extremists = [a for a in m.agent_list if a.is_extremist]
    moderates = [a for a in m.agent_list if not a.is_extremist]
    assert len(extremists) == 40          # 0.2 * 200
    assert len(moderates) == 160
    # extremists sit exactly at +-1 with the low uncertainty; symmetric split.
    assert all(a.u == pytest.approx(0.1) for a in extremists)
    assert all(abs(a.x) == pytest.approx(1.0) for a in extremists)
    assert m.n_pos_extreme == 20 and m.n_neg_extreme == 20
    # moderates: within [-1, 1] and carry the global uncertainty U.
    for a in moderates:
        assert -1.0 <= a.x <= 1.0
        assert a.u == pytest.approx(0.4)


def test_delta_makes_more_positive_extremists():
    # delta > 0 => a + majority of extremists (P3's deterministic asymmetry).
    m = RelativeAgreementModel(n=200, p_e=0.2, delta=0.1, seed=0)
    assert m.n_extreme == 40
    assert m.n_pos_extreme == 22 and m.n_neg_extreme == 18   # round(40*1.1/2)=22
    assert m.n_pos_extreme > m.n_neg_extreme
    n_pos_at_plus1 = sum(1 for a in m.agent_list if a.is_extremist and a.x > 0)
    n_neg_at_minus1 = sum(1 for a in m.agent_list if a.is_extremist and a.x < 0)
    assert n_pos_at_plus1 == 22 and n_neg_at_minus1 == 18


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        RelativeAgreementModel(n=0)
    with pytest.raises(ValueError):
        RelativeAgreementModel(n=10, p_e=1.5)
    with pytest.raises(ValueError):
        RelativeAgreementModel(n=10, u_e=0.0)
    with pytest.raises(ValueError):
        RelativeAgreementModel(n=10, big_u=-0.1)
    with pytest.raises(ValueError):
        RelativeAgreementModel(n=10, delta=2.0)


# -- the elementary relative-agreement interaction ------------------------------

def _bare_pair(xi, ui, xj, uj, *, mu=0.5):
    """A 2-agent model whose (x, u) we set by hand for isolated interaction tests."""
    m = RelativeAgreementModel(n=2, p_e=0.0, big_u=1.0, mu=mu, seed=0)
    i, j = m.agent_list
    i.x, i.u = xi, ui
    j.x, j.u = xj, uj
    return m, i, j


def test_no_overlap_no_interaction():
    # Disjoint segments: i=[0.8,1.2] (x=1.0,u=0.2), j=[-1.2,-0.8]. h < 0 <= u_i: no fire.
    m, i, j = _bare_pair(1.0, 0.2, -1.0, 0.2)
    x0, u0 = j.x, j.u
    move = m.interact(i, j)
    assert move == 0.0
    assert j.x == x0 and j.u == u0        # influenced agent untouched


def test_overlap_below_u_i_does_not_fire():
    # Segments touch a little but h_ij <= u_i (the RA gate): still no interaction.
    # i=[0.6,1.4] (x=1.0,u=0.4), j=[-0.5,0.9] (x=0.2,u=0.7): overlap [0.6,0.9]=0.3 < u_i=0.4.
    m, i, j = _bare_pair(1.0, 0.4, 0.2, 0.7)
    hi = min(i.x + i.u, j.x + j.u) - max(i.x - i.u, j.x - j.u)
    assert hi == pytest.approx(0.3)
    assert hi <= i.u                       # gate: overlap does not exceed u_i
    x0, u0 = j.x, j.u
    assert m.interact(i, j) == 0.0
    assert j.x == x0 and j.u == u0


def test_relative_agreement_update_matches_formula():
    # i=[0.7,1.3] (x=1.0,u=0.3), j=[-0.2,0.8] (x=0.3,u=0.5), mu=0.5.
    # overlap = min(1.3,0.8) - max(0.7,-0.2) = 0.8 - 0.7 = 0.1 ... <= u_i, so widen it:
    # use j with larger reach so h_ij > u_i.
    # i=[0.6,1.4] (x=1.0,u=0.4), j=[-0.6,1.0] (x=0.2,u=0.8):
    #   overlap = min(1.4,1.0) - max(0.6,-0.6) = 1.0 - 0.6 = 0.4  -> equals u_i, not >.
    # push j.x up so overlap strictly exceeds u_i:
    # i=[0.5,1.5] (x=1.0,u=0.5), j=[-0.3,1.3] (x=0.5,u=0.8):
    #   overlap = min(1.5,1.3) - max(0.5,-0.3) = 1.3 - 0.5 = 0.8 > u_i=0.5. ra = 0.8/0.5-1 = 0.6
    m, i, j = _bare_pair(1.0, 0.5, 0.5, 0.8, mu=0.5)
    hi = min(i.x + i.u, j.x + j.u) - max(i.x - i.u, j.x - j.u)
    assert hi == pytest.approx(0.8) and hi > i.u
    ra = hi / i.u - 1.0                     # 0.6
    assert ra == pytest.approx(0.6)
    exp_dx = m.mu * ra * (i.x - j.x)        # 0.5 * 0.6 * (1.0-0.5) = 0.15
    exp_du = m.mu * ra * (i.u - j.u)        # 0.5 * 0.6 * (0.5-0.8) = -0.09
    xj0, uj0 = j.x, j.u
    xi0, ui0 = i.x, i.u
    move = m.interact(i, j)
    assert move == pytest.approx(abs(exp_dx))
    assert j.x == pytest.approx(xj0 + exp_dx)      # j moves toward i
    assert j.u == pytest.approx(uj0 + exp_du)      # j's uncertainty shrinks toward i's
    # ASYMMETRY: only j changes; the influencer i is untouched.
    assert i.x == xi0 and i.u == ui0


def test_denominator_is_u_i_not_two_u_i():
    # ra uses h/u_i, not h/(2 u_i). With h=0.8, u_i=0.5: h/u_i-1 = 0.6 (NOT h/(2u_i)-1=-0.2).
    m, i, j = _bare_pair(1.0, 0.5, 0.5, 0.8, mu=0.5)
    hi = min(i.x + i.u, j.x + j.u) - max(i.x - i.u, j.x - j.u)
    ra_correct = hi / i.u - 1.0
    ra_wrong = hi / (2.0 * i.u) - 1.0
    assert ra_correct == pytest.approx(0.6)
    assert ra_wrong == pytest.approx(-0.2)
    # the model's committed move must reflect the u_i denominator (positive pull).
    xj0 = j.x
    m.interact(i, j)
    assert j.x > xj0                        # j moved TOWARD i (a widening influence)


def test_low_uncertainty_influencer_pulls_harder():
    # The confident (small u_i) influencer yields a larger ra for the same overlap, so
    # it moves the influenced agent more — the mechanism by which extremists dominate.
    # Same j, same overlap geometry; only u_i differs.
    m1, i1, j1 = _bare_pair(0.0, 0.2, 0.5, 0.7, mu=0.5)   # confident influencer
    m2, i2, j2 = _bare_pair(0.0, 0.6, 0.5, 0.7, mu=0.5)   # unsure influencer
    h1 = min(i1.x + i1.u, j1.x + j1.u) - max(i1.x - i1.u, j1.x - j1.u)
    h2 = min(i2.x + i2.u, j2.x + j2.u) - max(i2.x - i2.u, j2.x - j2.u)
    # both fire
    assert h1 > i1.u and h2 > i2.u
    x1_0, x2_0 = j1.x, j2.x
    m1.interact(i1, j1)
    m2.interact(i2, j2)
    move1 = abs(j1.x - x1_0)
    move2 = abs(j2.x - x2_0)
    assert move1 > move2                    # the more-confident influencer pulls harder


# -- the locked metric ----------------------------------------------------------

def test_polarization_metric_central_is_zero():
    # No moderate near either extreme -> p'_+ = p'_- = 0 -> y = 0.
    m = RelativeAgreementModel(n=10, p_e=0.0, big_u=0.4, seed=0)
    for a in m.agent_list:
        a.x = 0.0                           # all central
    assert m.polarization_y() == pytest.approx(0.0)
    assert m.moderate_captured_fraction() == pytest.approx(0.0)


def test_polarization_metric_double_extreme_near_half():
    # Half the moderates at +1, half at -1 -> p'_+ = p'_- = 0.5 -> y = 0.5.
    m = RelativeAgreementModel(n=10, p_e=0.0, big_u=0.4, seed=0)
    for k, a in enumerate(m.agent_list):
        a.x = 1.0 if k < 5 else -1.0
    assert m.polarization_y() == pytest.approx(0.5)
    p_pos, p_neg = m.capture_fractions()
    assert p_pos == pytest.approx(0.5) and p_neg == pytest.approx(0.5)


def test_polarization_metric_single_extreme_is_one():
    # All moderates captured by ONE pole -> p'_+ = 1 -> y = 1.
    m = RelativeAgreementModel(n=10, p_e=0.0, big_u=0.4, seed=0)
    for a in m.agent_list:
        a.x = 0.95
    assert m.polarization_y() == pytest.approx(1.0)
    assert m.moderate_captured_fraction() == pytest.approx(1.0)


def test_metric_excludes_extremists():
    # y is graded over INITIALLY-MODERATE agents only; seeded extremists don't count.
    m = RelativeAgreementModel(n=100, p_e=0.2, big_u=0.4, delta=0.0, seed=1)
    # force every moderate to be central; extremists remain pinned at +-1.
    for a in m.agent_list:
        if not a.is_extremist:
            a.x = 0.0
    # extremists at +-1 would each give |x|>0.8, but they are excluded -> y=0.
    assert m.polarization_y() == pytest.approx(0.0)
    assert m.moderate_captured_fraction() == pytest.approx(0.0)


def test_central_mean_abs_x_over_uncaptured_only():
    m = RelativeAgreementModel(n=10, p_e=0.0, big_u=0.4, seed=0)
    xs = [0.0, 0.2, -0.4, 0.9, -0.95, 0.1, -0.1, 0.3, -0.3, 0.05]
    for a, x in zip(m.agent_list, xs):
        a.x = x
    # captured (|x|>0.8): 0.9, -0.95 -> excluded; central mean over the other 8.
    central = [x for x in xs if abs(x) <= 0.8]
    exp = sum(abs(x) for x in central) / len(central)
    assert m.central_mean_abs_x() == pytest.approx(exp)


# -- sweep mechanics + run shape ------------------------------------------------

def test_run_summary_shape():
    res = run_single(n=200, big_u=0.4, delta=0.0, seed=0, n_sweeps=50)
    assert res["n"] == 200 and res["n_sweeps"] == 50
    assert len(res["y_series"]) == 51                 # t=0 baseline + 50 sweeps
    assert len(res["max_move_series"]) == 51
    assert 0.0 <= res["y"] <= 1.0
    assert 0.0 <= res["moderate_captured_fraction"] <= 1.0
    assert res["n_moderate"] == 160 and res["n_extreme"] == 40
    assert len(res["final_moderate_opinions"]) == 160


def test_run_rejects_bad_sweep_budget():
    m = RelativeAgreementModel(n=10, seed=0)
    with pytest.raises(ValueError):
        m.run(0)


def test_opinions_stay_in_bounds_over_a_run():
    # RA is contractive toward influencers in [-1,1]; opinions must not blow past +-1.
    res = run_single(n=200, big_u=1.2, delta=0.0, seed=3, n_sweeps=200)
    for x in res["final_opinions"]:
        assert -1.0001 <= x <= 1.0001


# -- determinism ----------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(n=200, big_u=1.2, delta=0.0, seed=7, n_sweeps=100)
    b = run_single(n=200, big_u=1.2, delta=0.0, seed=7, n_sweeps=100)
    assert a["final_opinions"] == b["final_opinions"]
    assert a["y_series"] == b["y_series"]
    assert a["y"] == b["y"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=200, big_u=1.2, delta=0.0, seed=1, n_sweeps=100)
    b = run_single(n=200, big_u=1.2, delta=0.0, seed=2, n_sweeps=100)
    for res in (a, b):
        assert 0.0 <= res["y"] <= 1.0
        assert all(0.0 <= yv <= 1.0 for yv in res["y_series"])


# -- P3 single-pole readout helper ----------------------------------------------

def test_single_pole_capture_stats():
    # Hand-built runs: two + single-pole, one - single-pole, one bipolar (not single).
    runs = [
        {"p_plus": 0.97, "p_minus": 0.02},   # + single-pole
        {"p_plus": 0.95, "p_minus": 0.05},   # + single-pole
        {"p_plus": 0.03, "p_minus": 0.96},   # - single-pole
        {"p_plus": 0.50, "p_minus": 0.50},   # bipolar, not single-pole
    ]
    stats = single_pole_capture_stats(runs, dominant_bar=0.9, opposite_bar=0.1)
    assert stats["n_total"] == 4
    assert stats["n_single_pole"] == 3
    assert stats["frac_single_pole"] == pytest.approx(0.75)
    assert stats["n_plus_won"] == 2 and stats["n_minus_won"] == 1
    assert stats["frac_plus_among_single"] == pytest.approx(2 / 3)
