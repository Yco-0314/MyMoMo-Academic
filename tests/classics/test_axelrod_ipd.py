"""Faithful-rule + determinism tests for the Axelrod (1984) IPD tournament.

These pin each strategy's per-round decision rule against a hand-fed local
history, the payoff matrix (T=5,R=3,P=1,S=0), the Match scoring, round-robin
self-play, and determinism (same seed -> identical scores). They are faithfulness
tests, NOT prediction tests (P1-P3 are evaluated by
examples/repro_axelrod_ipd_tournament/run.py).
"""
from __future__ import annotations

from abm_auto.classics.axelrod_ipd import (
    COOPERATE,
    DEFECT,
    PAYOFF,
    P,
    R,
    S,
    T,
    AllC,
    AllD,
    Grudger,
    Match,
    NICE_STRATEGIES,
    Pavlov,
    RandomStrategy,
    STRATEGY_FACTORIES,
    SuspiciousTFT,
    TitForTat,
    TitForTwoTats,
    TournamentModel,
    run_many_seeds,
    run_tournament,
)
import random


def _feed(agent, my_moves, opp_moves):
    """Set an agent's local match history directly (round-by-round equivalent)."""
    agent.reset_match()
    agent.my_moves = list(my_moves)
    agent.opp_moves = list(opp_moves)


# -- payoff matrix -------------------------------------------------------------

def test_payoff_matrix_axelrod_values():
    assert (T, R, P, S) == (5, 3, 1, 0)
    assert PAYOFF[(DEFECT, COOPERATE)] == 5      # T temptation
    assert PAYOFF[(COOPERATE, COOPERATE)] == 3   # R reward
    assert PAYOFF[(DEFECT, DEFECT)] == 1         # P punishment
    assert PAYOFF[(COOPERATE, DEFECT)] == 0      # S sucker
    # standard PD ordering + 2R > T+S
    assert T > R > P > S and 2 * R > T + S


# -- per-strategy decision rules ----------------------------------------------

def test_titfortat_cooperates_first_then_copies():
    a = TitForTat(0)
    a.reset_match()
    assert a.decide() == COOPERATE          # nice opening
    _feed(a, [COOPERATE], [DEFECT])
    assert a.decide() == DEFECT             # copies opp last (D)
    _feed(a, [DEFECT], [COOPERATE])
    assert a.decide() == COOPERATE          # copies opp last (C)


def test_alld_always_defects_alllc_always_cooperates():
    d = AllD(0); d.reset_match()
    c = AllC(1); c.reset_match()
    assert d.decide() == DEFECT
    assert c.decide() == COOPERATE
    _feed(d, [DEFECT] * 3, [COOPERATE] * 3)
    _feed(c, [COOPERATE] * 3, [DEFECT] * 3)
    assert d.decide() == DEFECT             # never swayed
    assert c.decide() == COOPERATE


def test_grudger_cooperates_until_first_defection_then_forever_defects():
    g = Grudger(0)
    g.reset_match()
    assert g.decide() == COOPERATE
    _feed(g, [COOPERATE, COOPERATE], [COOPERATE, COOPERATE])
    assert g.decide() == COOPERATE          # opp clean so far
    _feed(g, [COOPERATE, COOPERATE, COOPERATE], [COOPERATE, DEFECT, COOPERATE])
    assert g.decide() == DEFECT             # opp defected once -> grim, even though
    #                                          opp's LAST move was C
    _feed(g, [DEFECT] * 5, [DEFECT, COOPERATE, COOPERATE, COOPERATE, COOPERATE])
    assert g.decide() == DEFECT             # still grudging


def test_titfortwotats_needs_two_consecutive_defections():
    t = TitForTwoTats(0)
    t.reset_match()
    assert t.decide() == COOPERATE
    _feed(t, [COOPERATE], [DEFECT])
    assert t.decide() == COOPERATE          # only one defection -> forgive
    _feed(t, [COOPERATE, COOPERATE], [DEFECT, COOPERATE])
    assert t.decide() == COOPERATE          # last two are D,C -> not consecutive
    _feed(t, [COOPERATE, COOPERATE], [DEFECT, DEFECT])
    assert t.decide() == DEFECT             # two consecutive D -> retaliate


def test_suspicious_tft_defects_first_then_copies():
    s = SuspiciousTFT(0)
    s.reset_match()
    assert s.decide() == DEFECT             # suspicious opening
    _feed(s, [DEFECT], [COOPERATE])
    assert s.decide() == COOPERATE          # copies opp last (C)
    _feed(s, [COOPERATE], [DEFECT])
    assert s.decide() == DEFECT             # copies opp last (D)


def test_pavlov_win_stay_lose_shift():
    pv = Pavlov(0)
    pv.reset_match()
    assert pv.decide() == COOPERATE         # nice opening
    # last round R=3 (CC) -> win -> stay C
    _feed(pv, [COOPERATE], [COOPERATE])
    assert pv.decide() == COOPERATE
    # last round T=5 (DC) -> win -> stay D
    _feed(pv, [DEFECT], [COOPERATE])
    assert pv.decide() == DEFECT
    # last round S=0 (CD) -> lose -> shift from C to D
    _feed(pv, [COOPERATE], [DEFECT])
    assert pv.decide() == DEFECT
    # last round P=1 (DD) -> lose -> shift from D to C
    _feed(pv, [DEFECT], [DEFECT])
    assert pv.decide() == COOPERATE


def test_random_is_seeded_and_respects_p():
    r1 = RandomStrategy(0, p=0.5, rng=random.Random(42))
    r1.reset_match()
    seq1 = [r1.decide() for _ in range(50)]
    r2 = RandomStrategy(0, p=0.5, rng=random.Random(42))
    r2.reset_match()
    seq2 = [r2.decide() for _ in range(50)]
    assert seq1 == seq2                      # same seed -> identical
    # p=1.0 always cooperates, p=0.0 always defects
    rc = RandomStrategy(0, p=1.0, rng=random.Random(1)); rc.reset_match()
    rd = RandomStrategy(0, p=0.0, rng=random.Random(1)); rd.reset_match()
    assert all(rc.decide() == COOPERATE for _ in range(20))
    assert all(rd.decide() == DEFECT for _ in range(20))


# -- Match scoring -------------------------------------------------------------

def test_match_two_cooperators_score_reward_each_round():
    a, b = AllC(0), AllC(1)
    sa, sb = Match(a, b, rounds=200).play()
    assert sa == sb == 200 * R              # 200 * 3 = 600


def test_match_two_defectors_score_punishment_each_round():
    a, b = AllD(0), AllD(1)
    sa, sb = Match(a, b, rounds=200).play()
    assert sa == sb == 200 * P              # 200 * 1 = 200


def test_match_alld_exploits_allc():
    d, c = AllD(0), AllC(1)
    sd, sc = Match(d, c, rounds=200).play()
    assert sd == 200 * T                    # defector temptation each round = 1000
    assert sc == 200 * S                    # cooperator sucker each round = 0


def test_match_tft_vs_alld_locks_into_mutual_defection():
    # TFT cooperates round 1 (sucker S=0), opponent defects (T=5); thereafter TFT
    # retaliates and both defect (P=1) for the remaining 199 rounds.
    tft, d = TitForTat(0), AllD(1)
    s_tft, s_d = Match(tft, d, rounds=200).play()
    assert s_tft == S + 199 * P             # 0 + 199 = 199
    assert s_d == T + 199 * P               # 5 + 199 = 204


def test_match_tft_vs_tft_full_cooperation():
    a, b = TitForTat(0), TitForTat(1)
    sa, sb = Match(a, b, rounds=200).play()
    assert sa == sb == 200 * R              # both nice -> mutual C throughout


def test_match_resets_history_between_plays():
    # The same agent instances replay; the second match must not see the first's
    # history (TFT must cooperate on the fresh first move again).
    tft, c = TitForTat(0), AllC(1)
    Match(tft, AllD(2), rounds=10).play()   # poison tft's prior history with a D foe
    sa, sb = Match(tft, c, rounds=200).play()
    assert sa == 200 * R                     # fresh match: TFT vs AllC -> all C


# -- Tournament: round-robin incl. self-play + determinism --------------------

def test_pool_has_at_least_eight_named_strategies():
    names = [cls.name for cls, _ in STRATEGY_FACTORIES]
    assert len(names) >= 8
    assert len(set(names)) == len(names)     # all distinct
    assert "TitForTat" in names and "AllD" in names and "Pavlov" in names


def test_nice_set_is_the_documented_five():
    assert NICE_STRATEGIES == {
        "TitForTat", "AllC", "Grudger", "TitForTwoTats", "Pavlov"}


def test_tournament_runs_round_robin_including_self_play():
    m = TournamentModel(rounds=200, seed=0)
    res = m.run()
    n = len(STRATEGY_FACTORIES)
    # number of unordered pairings incl. self = n(n+1)/2
    assert len(res["pair_scores"]) == n * (n + 1) // 2
    # self-play pairings are present
    assert "TitForTat_vs_TitForTat" in res["pair_scores"]
    # every strategy has a total score
    assert set(res["scores"]) == {cls.name for cls, _ in STRATEGY_FACTORIES}
    # ranking is sorted descending by score
    scores = [row["score"] for row in res["ranking"]]
    assert scores == sorted(scores, reverse=True)


def test_tournament_determinism_same_seed_identical():
    a = run_tournament(rounds=200, seed=0)
    b = run_tournament(rounds=200, seed=0)
    assert a["scores"] == b["scores"]
    assert a["ranking"] == b["ranking"]


def test_tournament_seed_changes_only_random_dependent_totals():
    a = run_tournament(rounds=200, seed=0)
    b = run_tournament(rounds=200, seed=1)
    # The Random strategy's own total must differ across seeds (it is stochastic).
    assert a["scores"]["Random"] != b["scores"]["Random"]
    # AllC vs AllD self/cross matches are deterministic regardless of seed, but
    # AllC's TOTAL includes its match vs Random, so allow it to differ; instead
    # check a fully deterministic pairing is identical. (pair key follows pool
    # order: AllD precedes AllC, so the key is "AllD_vs_AllC".)
    assert a["pair_scores"]["AllD_vs_AllC"] == b["pair_scores"]["AllD_vs_AllC"]


def test_run_many_seeds_shape_and_determinism():
    a = run_many_seeds(rounds=200, seeds=(0, 1, 2))
    b = run_many_seeds(rounds=200, seeds=(0, 1, 2))
    assert a["mean_scores"] == b["mean_scores"]
    assert len(a["per_seed"]) == 3
    # ranking carries mean_score, variance, rank, nice flag
    row = a["ranking"][0]
    assert set(row) >= {"rank", "name", "mean_score", "min_score", "max_score",
                        "stdev", "nice"}
    # ranks are 1-based and the top row is rank 1
    assert a["ranking"][0]["rank"] == 1
