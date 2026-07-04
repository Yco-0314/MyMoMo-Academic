"""Faithful-rule + determinism tests for the Win-Stay-Lose-Shift (Pavlov) noisy-IPD
reproduction of Nowak & Sigmund (1993).

These pin the memory-one policy semantics (the 4-vector indexed by last-round outcome),
the implementation-noise flip, the exact joint-state Markov transition matrix + its unique
stationary distribution, the exact-vs-agent-based-simulation agreement, the evolutionary
generation (fitness-proportional selection + mutation over a finite population), the
invasion asymmetry primitive, and determinism (same seed -> identical result).

They are FAITHFULNESS tests, NOT prediction tests — the locked predictions P1-P3
(docs/studies/pavlov-wsls/PREDICTIONS-locked.md: WSLS restores cooperation under noise,
WSLS exploits ALLC, WSLS dominates the co-evolving noisy population) are graded by
examples/repro_pavlov_wsls/run.py.
"""
from __future__ import annotations

import random

import pytest

from abm_auto.classics.pavlov_wsls import (
    COOPERATE,
    DEFECT,
    JOINT_STATES,
    PAYOFF,
    STRATEGIES,
    T, R, P, S,
    EvolvingPopulation,
    MemoryOneAgent,
    PopMember,
    coop_prob,
    exact_payoff,
    exact_payoffs,
    invasion_test,
    run_evolution,
    simulate_payoffs,
    stationary_distribution,
    tail_mean,
    transition_matrix,
)


# -- payoff matrix + outcome indexing -----------------------------------------

def test_payoff_matrix_is_canonical_pd():
    assert (T, R, P, S) == (5.0, 3.0, 1.0, 0.0)
    assert T > R > P > S                    # PD ordering
    assert 2 * R > T + S                    # cooperation beats alternating exploitation
    assert PAYOFF[(COOPERATE, COOPERATE)] == R
    assert PAYOFF[(DEFECT, COOPERATE)] == T
    assert PAYOFF[(COOPERATE, DEFECT)] == S
    assert PAYOFF[(DEFECT, DEFECT)] == P


def test_coop_prob_indexes_by_own_outcome():
    # WSLS = (p_R,p_S,p_T,p_P) = (1,0,0,1): C after R (I C, opp C) and after P (I D, opp D).
    wsls = STRATEGIES["WSLS"]
    assert coop_prob(wsls, COOPERATE, COOPERATE) == 1.0   # outcome R
    assert coop_prob(wsls, COOPERATE, DEFECT) == 0.0      # outcome S
    assert coop_prob(wsls, DEFECT, COOPERATE) == 0.0      # outcome T
    assert coop_prob(wsls, DEFECT, DEFECT) == 1.0         # outcome P
    # TFT = (1,0,1,0) copies the OPPONENT: C after R/T (opp played C), D after S/P (opp D).
    tft = STRATEGIES["TFT"]
    assert coop_prob(tft, COOPERATE, COOPERATE) == 1.0    # opp C -> C
    assert coop_prob(tft, DEFECT, COOPERATE) == 1.0       # opp C -> C
    assert coop_prob(tft, COOPERATE, DEFECT) == 0.0       # opp D -> D
    assert coop_prob(tft, DEFECT, DEFECT) == 0.0          # opp D -> D


def test_strategy_library_vectors_are_the_canonical_four():
    assert STRATEGIES["WSLS"] == (1.0, 0.0, 0.0, 1.0)
    assert STRATEGIES["TFT"] == (1.0, 0.0, 1.0, 0.0)
    assert STRATEGIES["ALLC"] == (1.0, 1.0, 1.0, 1.0)
    assert STRATEGIES["ALLD"] == (0.0, 0.0, 0.0, 0.0)


# -- MemoryOneAgent: intended move + implementation noise ---------------------

def test_intended_move_opens_with_open_move():
    a = MemoryOneAgent(0, None, policy=STRATEGIES["WSLS"], eps=0.0)
    assert a.intended_move(None, None) == COOPERATE       # first round: opening
    b = MemoryOneAgent(1, None, policy=STRATEGIES["ALLD"], eps=0.0, open_move=DEFECT)
    assert b.intended_move(None, None) == DEFECT


def test_intended_move_follows_policy_deterministically_for_pure_strategies():
    # ALLD (all zeros) always intends D; ALLC (all ones) always intends C, whatever the state.
    alld = MemoryOneAgent(0, None, policy=STRATEGIES["ALLD"], eps=0.0)
    allc = MemoryOneAgent(1, None, policy=STRATEGIES["ALLC"], eps=0.0)
    for my, opp in [(COOPERATE, COOPERATE), (COOPERATE, DEFECT),
                    (DEFECT, COOPERATE), (DEFECT, DEFECT)]:
        assert alld.intended_move(my, opp) == DEFECT
        assert allc.intended_move(my, opp) == COOPERATE


def test_wsls_intended_move_is_win_stay_lose_shift():
    # WSLS with eps=0: after R (won, C) stay C; after T (won, D) stay D; after S (lost) shift;
    # after P (lost) shift to C.
    a = MemoryOneAgent(0, None, policy=STRATEGIES["WSLS"], eps=0.0)
    assert a.intended_move(COOPERATE, COOPERATE) == COOPERATE   # R -> stay C
    assert a.intended_move(DEFECT, COOPERATE) == DEFECT         # T -> stay D
    assert a.intended_move(COOPERATE, DEFECT) == DEFECT         # S (lost while C) -> shift to D
    assert a.intended_move(DEFECT, DEFECT) == COOPERATE         # P (lost while D) -> shift to C


def test_zero_noise_never_flips():
    a = MemoryOneAgent(0, None, policy=STRATEGIES["ALLC"], eps=0.0,
                       rng=random.Random(0))
    for _ in range(1000):
        assert a.noisy_move(COOPERATE, COOPERATE) == COOPERATE   # eps=0 -> never flips


def test_full_noise_always_flips():
    a = MemoryOneAgent(0, None, policy=STRATEGIES["ALLC"], eps=1.0,
                       rng=random.Random(0))
    for _ in range(1000):
        assert a.noisy_move(COOPERATE, COOPERATE) == DEFECT      # eps=1 -> always flips


def test_noise_flips_at_roughly_epsilon_rate():
    eps = 0.1
    a = MemoryOneAgent(0, None, policy=STRATEGIES["ALLC"], eps=eps, rng=random.Random(1))
    n = 20000
    flips = sum(1 for _ in range(n) if a.noisy_move(COOPERATE, COOPERATE) == DEFECT)
    assert flips / n == pytest.approx(eps, abs=0.02)             # ~eps fraction flipped


def test_bad_policy_or_eps_raises():
    with pytest.raises(ValueError):
        MemoryOneAgent(0, None, policy=(1.0, 0.0, 0.0))          # not a 4-vector
    with pytest.raises(ValueError):
        MemoryOneAgent(0, None, policy=STRATEGIES["WSLS"], eps=1.5)


# -- exact Markov transition matrix + stationary distribution -----------------

def test_transition_rows_are_stochastic():
    for a in STRATEGIES:
        for b in STRATEGIES:
            mat = transition_matrix(STRATEGIES[a], STRATEGIES[b], 0.01)
            assert len(mat) == 4 and all(len(row) == 4 for row in mat)
            for row in mat:
                assert sum(row) == pytest.approx(1.0, abs=1e-12)
                assert all(0.0 <= x <= 1.0 for x in row)


def test_stationary_distribution_is_a_fixed_point():
    mat = transition_matrix(STRATEGIES["WSLS"], STRATEGIES["WSLS"], 0.01)
    pi = stationary_distribution(mat)
    assert sum(pi) == pytest.approx(1.0, abs=1e-12)
    # pi P == pi
    piP = [sum(pi[i] * mat[i][j] for i in range(4)) for j in range(4)]
    for j in range(4):
        assert piP[j] == pytest.approx(pi[j], abs=1e-9)


def test_wsls_self_play_is_mostly_mutual_cooperation_under_noise():
    # The P1 mechanism: two WSLS players spend the vast majority of time in CC (cooperation
    # restored after any accidental defection). CC is JOINT_STATES[0].
    mat = transition_matrix(STRATEGIES["WSLS"], STRATEGIES["WSLS"], 0.01)
    pi = stationary_distribution(mat)
    cc_index = JOINT_STATES.index((COOPERATE, COOPERATE))
    assert pi[cc_index] > 0.9                     # >90% of rounds are mutual cooperation


def test_exact_payoffs_mirror_symmetry():
    # a's payoff vs b equals b's payoff when the roles are swapped.
    pa, pb = exact_payoffs(STRATEGIES["WSLS"], STRATEGIES["ALLC"], 0.01)
    pa2, pb2 = exact_payoffs(STRATEGIES["ALLC"], STRATEGIES["WSLS"], 0.01)
    assert pa == pytest.approx(pb2, abs=1e-9)
    assert pb == pytest.approx(pa2, abs=1e-9)


def test_exact_payoffs_rejects_degenerate_noise():
    with pytest.raises(ValueError):
        exact_payoffs(STRATEGIES["WSLS"], STRATEGIES["WSLS"], 0.0)   # not ergodic
    with pytest.raises(ValueError):
        exact_payoffs(STRATEGIES["WSLS"], STRATEGIES["WSLS"], 1.0)


def test_wsls_vs_allc_splits_between_cooperate_and_exploit():
    # Faithful mechanism (not the graded P2 bar): memory-one WSLS vs ALLC locks into EITHER
    # CC (R) or DC (T); noise moves it symmetrically between them, so the stationary weight
    # sits ~half on CC and ~half on DC and WSLS's mean payoff is ~ (R+T)/2 = 4, strictly
    # between R=3 (pure cooperation) and T=5 (pure exploitation).
    mat = transition_matrix(STRATEGIES["WSLS"], STRATEGIES["ALLC"], 0.01)
    pi = stationary_distribution(mat)
    cc = pi[JOINT_STATES.index((COOPERATE, COOPERATE))]
    dc = pi[JOINT_STATES.index((DEFECT, COOPERATE))]
    assert cc > 0.4 and dc > 0.4                  # weight split between cooperate + exploit
    pa, _ = exact_payoffs(STRATEGIES["WSLS"], STRATEGIES["ALLC"], 0.01)
    assert R < pa < T                             # strictly between pure-C and pure-exploit


# -- exact chain == agent-based noisy simulation ------------------------------

@pytest.mark.parametrize("pair", [("WSLS", "WSLS"), ("TFT", "TFT"),
                                  ("WSLS", "ALLC"), ("WSLS", "TFT"), ("TFT", "ALLD")])
def test_exact_payoff_matches_noisy_simulation(pair):
    # The exact Markov payoff is the rounds->infinity limit of the genuine agent-based
    # noisy match; a long simulation must agree within Monte-Carlo error.
    a, b = pair
    ex_a, ex_b = exact_payoff(a, b, 0.01)
    si_a, si_b = simulate_payoffs(a, b, 0.01, rounds=300_000, seed=3)
    assert si_a == pytest.approx(ex_a, abs=0.03)
    assert si_b == pytest.approx(ex_b, abs=0.03)


# -- evolutionary population --------------------------------------------------

def test_population_is_pop_members_summing_to_n():
    pop = EvolvingPopulation(strategies=("WSLS", "TFT", "ALLC"), n=100, eps=0.01,
                             mu=0.01, seed=0)
    assert len(pop.members) == 100
    assert all(isinstance(m, PopMember) for m in pop.members)
    assert sum(pop.counts().values()) == 100
    # frequencies are a probability vector
    freqs = pop.frequencies()
    assert sum(freqs.values()) == pytest.approx(1.0)
    assert all(0.0 <= f <= 1.0 for f in freqs.values())


def test_population_respects_init_counts():
    pop = EvolvingPopulation(strategies=("WSLS", "TFT", "ALLC"), n=100,
                             init_counts={"WSLS": 50, "TFT": 30, "ALLC": 20}, seed=0)
    c = pop.counts()
    assert c == {"WSLS": 50, "TFT": 30, "ALLC": 20}


def test_bad_population_params_raise():
    with pytest.raises(ValueError):
        EvolvingPopulation(n=0)
    with pytest.raises(ValueError):
        EvolvingPopulation(mu=1.5)
    with pytest.raises(ValueError):
        EvolvingPopulation(strategies=("WSLS", "TFT"), n=100,
                           init_counts={"WSLS": 10, "TFT": 10})   # sums to 20, not 100


def test_generation_preserves_population_size():
    pop = EvolvingPopulation(strategies=("WSLS", "TFT", "ALLC"), n=100, seed=1)
    for _ in range(20):
        pop.step()
        assert len(pop.members) == 100
        assert sum(pop.counts().values()) == 100


def test_monomorphic_population_stays_put_without_mutation():
    # A pure population with mu=0 has no other type to select or mutate into -> stays pure.
    pop = EvolvingPopulation(strategies=("WSLS", "TFT", "ALLC"), n=100, mu=0.0,
                             init_counts={"WSLS": 100, "TFT": 0, "ALLC": 0}, seed=2)
    for _ in range(30):
        pop.step()
    assert pop.counts()["WSLS"] == 100


def test_run_summary_shape():
    res = run_evolution(n=100, eps=0.01, mu=0.01, strategies=("WSLS", "TFT", "ALLC"),
                        seed=0, generations=40, measure_last=10)
    assert set(res["strategies"]) == {"WSLS", "TFT", "ALLC"}
    for s in res["strategies"]:
        assert len(res["freq_series"][s]) == 41         # gen 0 baseline + 40 generations
        assert 0.0 <= res["late_freq"][s] <= 1.0
    # frequencies sum to 1 each generation
    for g in range(41):
        tot = sum(res["freq_series"][s][g] for s in res["strategies"])
        assert tot == pytest.approx(1.0)


def test_run_rejects_bad_measure_window():
    pop = EvolvingPopulation(strategies=("WSLS", "TFT", "ALLC"), n=100, seed=0)
    with pytest.raises(ValueError):
        pop.run(20, measure_last=0)
    with pytest.raises(ValueError):
        pop.run(20, measure_last=50)


# -- invasion asymmetry primitive ---------------------------------------------

def test_invasion_wsls_resists_allc_tft_admits_allc():
    # The P3 mechanism (faithful, decisive): a small ALLC minority DIES OUT under a WSLS
    # resident (WSLS exploits/resists ALLC) but TAKES OVER under a TFT resident (TFT is
    # neutral toward ALLC, so drift/selection lets ALLC accumulate). mu=0 isolates selection.
    wsls_res = invasion_test(resident="WSLS", invader="ALLC", invader_count=5, n=100,
                             eps=0.01, mu=0.0, n_seeds=5, generations=200, measure_last=50)
    tft_res = invasion_test(resident="TFT", invader="ALLC", invader_count=5, n=100,
                            eps=0.01, mu=0.0, n_seeds=5, generations=200, measure_last=50)
    # WSLS resists: ALLC stays below its seed level (0.05) — here it is driven out entirely.
    assert wsls_res["mean_late_invader_freq"] < 0.05
    # TFT admits: ALLC rises well above its seed level.
    assert tft_res["mean_late_invader_freq"] > 0.5
    # and the asymmetry is large.
    assert tft_res["mean_late_invader_freq"] - wsls_res["mean_late_invader_freq"] > 0.5


# -- steady-state estimator ---------------------------------------------------

def test_tail_mean_is_trailing_window_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert tail_mean(series, window=2) == pytest.approx(0.45)    # mean(0.4, 0.5)
    assert tail_mean(series, window=100) == pytest.approx(0.3)   # whole series
    assert tail_mean([], window=5) == 0.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_evolution():
    a = run_evolution(n=100, eps=0.01, mu=0.01, strategies=("WSLS", "TFT", "ALLC"),
                      seed=42, generations=60, measure_last=20)
    b = run_evolution(n=100, eps=0.01, mu=0.01, strategies=("WSLS", "TFT", "ALLC"),
                      seed=42, generations=60, measure_last=20)
    assert a["freq_series"] == b["freq_series"]
    assert a["late_freq"] == b["late_freq"]


def test_simulate_payoffs_deterministic_for_a_seed():
    a = simulate_payoffs("WSLS", "TFT", 0.01, rounds=5000, seed=9)
    b = simulate_payoffs("WSLS", "TFT", 0.01, rounds=5000, seed=9)
    assert a == b
