"""Faithful-rule + determinism tests for the majority-vote (de Oliveira 1992) reproduction.

These pin the LOCAL update rule (majority sign with prob 1-q, minority with prob q),
the 4-NN von-Neumann periodic neighbourhood, the 2-2 tie coin, the random-sequential
sweep, the order-parameter |m|, and determinism (same seed -> identical result). They
are faithfulness tests, NOT prediction tests (P1-P3 are evaluated by
examples/repro_majority_vote/run.py against the locked grid).
"""
from __future__ import annotations

from abm_auto.classics.majority_vote import (
    MajorityVoteModel,
    half_crossing,
    is_monotone_non_increasing,
    run_many_seeds,
    run_single,
)


def test_periodic_4nn_neighbours_wrap_on_torus():
    # 3x3 lattice. Corner site (0,0)=id 0 has NN up=(2,0)=6, down=(1,0)=3,
    # left=(0,2)=2, right=(0,1)=1 by toroidal wrap.
    m = MajorityVoteModel(L=3, q=0.0, seed=0)
    up, down, left, right = m.neighbors[0]
    assert (up, down, left, right) == (6, 3, 2, 1)
    # Every site has exactly 4 distinct neighbours (a self-neighbour would mean L<3
    # wrap collision; L=3 is the minimal clean torus for von Neumann).
    for i in range(m.N):
        assert len(set(m.neighbors[i])) == 4
        assert i not in m.neighbors[i]


def test_clear_majority_adopted_at_zero_noise():
    # q=0: a site whose 4 NN sum to +2 (3 up, 1 down) must become +1 even if it
    # started at -1 (the deterministic majority-vote limit).
    m = MajorityVoteModel(L=3, q=0.0, seed=0)
    up, down, left, right = m.neighbors[4]  # center of a 3x3 torus
    m.sites[up].spin = 1
    m.sites[down].spin = 1
    m.sites[left].spin = 1
    m.sites[right].spin = -1  # sum = +2 -> majority +1
    m.sites[4].spin = -1      # minority start
    m.update_site(4)
    assert m.sites[4].spin == 1


def test_pure_noise_takes_minority_sign():
    # q=1: the spin ALWAYS takes the minority (-majority) sign. With a +2 field the
    # majority is +1 so the site must become -1.
    m = MajorityVoteModel(L=3, q=1.0, seed=0)
    up, down, left, right = m.neighbors[4]
    for sid in (up, down, left):
        m.sites[sid].spin = 1
    m.sites[right].spin = -1  # field +2 -> majority +1
    m.sites[4].spin = 1
    m.update_site(4)
    assert m.sites[4].spin == -1


class _FixedDraws:
    def __init__(self, draws):
        self._draws = iter(draws)

    def random(self):
        return next(self._draws)


def test_two_two_tie_flips_current_spin_with_half_probability_independent_of_q():
    m = MajorityVoteModel(L=3, q=0.0, seed=11)
    up, down, left, right = m.neighbors[4]
    m.sites[up].spin = 1
    m.sites[down].spin = 1
    m.sites[left].spin = -1
    m.sites[right].spin = -1
    m.sites[4].spin = 1
    m.rng = _FixedDraws([0.49])
    m.update_site(4)
    assert m.sites[4].spin == -1

    m = MajorityVoteModel(L=3, q=1.0, seed=11)
    up, down, left, right = m.neighbors[4]
    m.sites[up].spin = 1
    m.sites[down].spin = 1
    m.sites[left].spin = -1
    m.sites[right].spin = -1
    m.sites[4].spin = 1
    m.rng = _FixedDraws([0.50])
    m.update_site(4)
    assert m.sites[4].spin == 1


def test_two_two_tie_is_unbiased_over_many_draws():
    # A 2-2 split (field sum 0) has no majority -> S(0)=0 and the current spin
    # flips with probability 1/2. Over many independent ties, the up-fraction is
    # ~0.5 (up-down symmetry).
    m = MajorityVoteModel(L=3, q=0.0, seed=11)
    up, down, left, right = m.neighbors[4]
    ups = 0
    n = 4000
    for _ in range(n):
        m.sites[up].spin = 1
        m.sites[down].spin = 1
        m.sites[left].spin = -1
        m.sites[right].spin = -1  # sum = 0 -> tie
        m.sites[4].spin = 1
        m.update_site(4)
        ups += 1 if m.sites[4].spin == 1 else 0
    frac = ups / n
    assert 0.45 < frac < 0.55


def test_magnetization_metric_definitions():
    m = MajorityVoteModel(L=4, q=0.0, seed=0)
    for a in m.sites:
        a.spin = 1
    assert m.magnetization() == 1.0
    assert m.abs_magnetization() == 1.0
    # Flip exactly half to -1 -> signed m = 0, |m| = 0.
    for a in m.sites[: m.N // 2]:
        a.spin = -1
    assert m.magnetization() == 0.0
    assert m.abs_magnetization() == 0.0


def test_determinism_same_seed_identical_series():
    a = run_single(L=20, q=0.075, seed=3, equilibration=40, measurement=40)
    b = run_single(L=20, q=0.075, seed=3, equilibration=40, measurement=40)
    assert a["abs_m_series"] == b["abs_m_series"]
    assert a["abs_m_mean"] == b["abs_m_mean"]
    assert a["final_magnetization"] == b["final_magnetization"]


def test_different_seed_changes_trajectory():
    a = run_single(L=20, q=0.10, seed=1, equilibration=40, measurement=40)
    b = run_single(L=20, q=0.10, seed=2, equilibration=40, measurement=40)
    # Distinct seeds give distinct (initial spins + dynamics) trajectories.
    assert a["abs_m_series"] != b["abs_m_series"]


def test_low_noise_orders_high_noise_disorders():
    # The qualitative signature of the order-disorder transition (small lattice,
    # short run — this is a faithfulness sanity check, not the locked P1 grade).
    lo = run_single(L=24, q=0.02, seed=0, equilibration=60, measurement=60)
    hi = run_single(L=24, q=0.15, seed=0, equilibration=60, measurement=60)
    assert lo["abs_m_mean"] > 0.7   # ordered ferromagnetic phase
    assert hi["abs_m_mean"] < 0.3   # disordered paramagnetic phase


def test_run_many_seeds_is_deterministic_and_shaped():
    a = run_many_seeds(L=20, q=0.075, n_seeds=3, seed_base=0,
                       equilibration=30, measurement=30)
    b = run_many_seeds(L=20, q=0.075, n_seeds=3, seed_base=0,
                       equilibration=30, measurement=30)
    assert a["abs_m_per_seed"] == b["abs_m_per_seed"]
    assert a["abs_m_mean"] == b["abs_m_mean"]
    assert len(a["abs_m_per_seed"]) == 3
    assert 0.0 <= a["abs_m_mean"] <= 1.0


def test_q_validation_and_L_validation():
    import pytest

    with pytest.raises(ValueError):
        MajorityVoteModel(L=1, q=0.1)
    with pytest.raises(ValueError):
        MajorityVoteModel(L=10, q=1.5)
    with pytest.raises(ValueError):
        MajorityVoteModel(L=10, q=-0.1)


def test_half_crossing_interpolation():
    # |m| descending through 0.5 between q=0.05 (|m|=0.6) and q=0.10 (|m|=0.4):
    # crossing at q = 0.05 + (0.6-0.5)/(0.6-0.4) * 0.05 = 0.075.
    q_grid = [0.02, 0.05, 0.10, 0.15]
    abs_m = [0.9, 0.6, 0.4, 0.05]
    qc = half_crossing(q_grid, abs_m, level=0.5)
    assert qc is not None
    assert abs(qc - 0.075) < 1e-9
    # A curve that never crosses returns None.
    assert half_crossing(q_grid, [0.9, 0.8, 0.7, 0.6], level=0.5) is None


def test_is_monotone_non_increasing():
    assert is_monotone_non_increasing([0.9, 0.6, 0.4, 0.05]) is True
    assert is_monotone_non_increasing([0.9, 0.6, 0.65, 0.05]) is False
    # Tiny seed-noise wiggle within tolerance still counts as non-increasing.
    assert is_monotone_non_increasing([0.9, 0.6, 0.6 + 1e-12, 0.05]) is True
