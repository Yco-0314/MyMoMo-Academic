"""Faithful-rule + determinism tests for the image-scoring indirect-reciprocity
(Nowak & Sigmund 1998) reproduction.

These pin the strategy/image bounds, the donor's help rule (help iff recipient.s >=
donor.k), the donation-game payoffs (help costs c, gives b; refuse is free), the image
update with observation probability q (+1 help / -1 refuse, capped, only when observed),
the per-generation image + payoff reset, the payoff-proportional reproduction with the
min-shift and roulette parent choice, mutation (mu), the modal-strategy helper and
steady-state estimator, and determinism (same seed -> identical result).

They are FAITHFULNESS tests, NOT prediction tests — the locked predictions P1-P3
(fixation to k=0; information threshold q>c/b; group-size effect) are graded by
examples/repro_image_scoring/run.py.
"""
from __future__ import annotations

import pytest

from abm_auto.classics.image_scoring import (
    ImageScoringModel,
    K_MAX,
    K_MIN,
    K_VALUES,
    PlayerAgent,
    S_MAX,
    S_MIN,
    modal_strategy,
    run_single,
    tail_mean,
)


# -- bounds + construction ----------------------------------------------------

def test_strategy_range_and_image_bounds():
    # k spans [-5, +6] (12 strategies); image score bounds are [-5, +5].
    assert K_MIN == -5 and K_MAX == 6
    assert K_VALUES == tuple(range(-5, 7)) and len(K_VALUES) == 12
    assert S_MIN == -5 and S_MAX == 5


def test_population_is_player_agents_with_neutral_initial_image():
    m = ImageScoringModel(n=100, seed=0)
    assert len(m.agent_list) == 100
    assert all(isinstance(a, PlayerAgent) for a in m.agent_list)
    for a in m.agent_list:
        assert a.s == 0                       # everyone starts at neutral reputation
        assert a.k in K_VALUES                 # a valid strategy
        assert a.payoff == 0.0


def test_pinned_initial_strategy():
    m = ImageScoringModel(n=50, init_strategy="0", seed=1)
    assert all(a.k == 0 for a in m.agent_list)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        ImageScoringModel(n=1)                 # need n > 1
    with pytest.raises(ValueError):
        ImageScoringModel(n=10, b=0.1, c=1.0)  # need b > c
    with pytest.raises(ValueError):
        ImageScoringModel(n=10, c=0.0)         # need c > 0
    with pytest.raises(ValueError):
        ImageScoringModel(n=10, q=1.5)         # q out of [0,1]
    with pytest.raises(ValueError):
        ImageScoringModel(n=10, mu=-0.1)       # mu out of [0,1]
    with pytest.raises(ValueError):
        ImageScoringModel(n=10, interactions_per_agent=0)
    with pytest.raises(ValueError):
        ImageScoringModel(n=10, init_strategy="99")   # not a valid threshold


# -- the help rule ------------------------------------------------------------

def test_help_rule_is_recipient_image_ge_donor_threshold():
    m = ImageScoringModel(n=3, seed=0)
    donor, recipient, _ = m.agent_list
    donor.k = 0
    recipient.s = 0
    assert donor.helps(recipient)              # 0 >= 0 -> help
    recipient.s = -1
    assert not donor.helps(recipient)          # -1 >= 0 -> refuse
    recipient.s = 3
    assert donor.helps(recipient)              # 3 >= 0 -> help
    # unconditional cooperator (k=-5) helps even the worst image; defector (k=6) never.
    donor.k = -5
    recipient.s = -5
    assert donor.helps(recipient)
    donor.k = 6
    recipient.s = 5
    assert not donor.helps(recipient)          # 5 >= 6 is false -> never helps


# -- donation-game payoffs + image update ------------------------------------

def test_help_transfers_benefit_and_pays_cost_and_raises_image_when_observed():
    # q=1 so the act is always observed; a helping donor pays c, recipient gains b,
    # donor image +1.
    m = ImageScoringModel(n=2, b=1.0, c=0.1, q=1.0, seed=0)
    donor, recipient = m.agent_list
    donor.k, donor.s, donor.payoff = -5, 0, 0.0    # always helps
    recipient.s, recipient.payoff = 0, 0.0
    # force donor=index0, recipient=index1 by construction of the interaction draw:
    # run a single interaction repeatedly is random; instead call the helper on known
    # agents via a controlled model with n=2 (only i!=j pairing possible).
    m._n_help = 0
    m._n_interactions = 0
    # deterministically exercise the two roles by seeding then checking aggregate effect
    # over one interaction: with n=2 the donor/recipient are the two agents in some order.
    before = (donor.payoff, recipient.payoff, donor.s, recipient.s)
    m._donation_interaction()
    # exactly one help or refuse happened; check the invariant that a help moved payoff
    # by (-c, +b) and image +1 for whoever was the donor.
    changed_payoff = [a for a in m.agent_list if a.payoff != 0.0]
    assert m._n_interactions == 1
    # whichever agent was donor: if it helped, its payoff is -c and its image is +1.
    for a in m.agent_list:
        if a.payoff < 0.0:
            assert a.payoff == pytest.approx(-0.1)
            assert a.s == 1                     # helped -> image +1 (observed)
        if a.payoff > 0.0:
            assert a.payoff == pytest.approx(1.0)   # recipient got b
    _ = before, changed_payoff


def test_refuse_is_free_and_lowers_image_when_observed():
    # A defector (k=6) never helps; with q=1 its image drops by 1 and no payoff moves for
    # the donor (recipient gets nothing).
    m = ImageScoringModel(n=2, b=1.0, c=0.1, q=1.0, seed=3)
    for a in m.agent_list:
        a.k, a.s, a.payoff = 6, 0, 0.0          # both pure defectors
    m._n_help = 0
    m._n_interactions = 0
    m._donation_interaction()
    assert m._n_help == 0                        # a refusal, not a help
    assert m._n_interactions == 1
    donor = next(a for a in m.agent_list if a.s != 0)
    assert donor.s == -1                         # refused -> image -1 (observed)
    assert all(a.payoff == 0.0 for a in m.agent_list)   # refusal is free, no benefit


def test_image_unchanged_when_unobserved():
    # q=0: the act is never observed, so no image ever moves (even though help/refuse
    # payoffs still accrue).
    m = ImageScoringModel(n=2, b=1.0, c=0.1, q=0.0, seed=0)
    for a in m.agent_list:
        a.k, a.s, a.payoff = -5, 0, 0.0          # both always help
    for _ in range(50):
        m._donation_interaction()
    assert all(a.s == 0 for a in m.agent_list)   # images never moved (unobserved)


def test_image_score_is_capped():
    m = ImageScoringModel(n=2, q=1.0, seed=0)
    a, b = m.agent_list
    a.k = -5            # a always helps -> image rises, capped at S_MAX
    b.k = -5
    a.s = S_MAX
    b.s = S_MAX
    for _ in range(30):
        m._donation_interaction()
    for x in m.agent_list:
        assert S_MIN <= x.s <= S_MAX


# -- generation reset ---------------------------------------------------------

def test_play_generation_resets_images_and_payoffs_and_counts_acts():
    m = ImageScoringModel(n=20, q=1.0, init_strategy="-5", seed=0)   # all always-help
    # dirty the state first
    for a in m.agent_list:
        a.s, a.payoff = 3, 99.0
    m.play_generation()
    # with all unconditional cooperators every interaction is a help -> coop-act frac == 1
    assert m.last_coop_act_fraction == pytest.approx(1.0)
    assert m._n_interactions == m.m
    # image/payoff were reset to 0 at the start of the generation (then evolved by play).
    # every agent both donated and received across m=200 interactions, so payoffs moved,
    # but they started from a clean 0 (not the injected 99).
    assert all(a.payoff != 99.0 for a in m.agent_list)


def test_defectors_never_cooperate():
    m = ImageScoringModel(n=20, q=1.0, init_strategy="6", seed=0)    # all defectors
    m.play_generation()
    assert m.last_coop_act_fraction == pytest.approx(0.0)
    assert all(a.payoff == 0.0 for a in m.agent_list)   # no help ever -> no payoff moves


# -- reproduction -------------------------------------------------------------

def test_reproduction_is_payoff_proportional_favours_high_payoff():
    # One agent gets a large payoff, the rest zero -> after reproduction (mu=0) the whole
    # population should copy the winner's strategy.
    m = ImageScoringModel(n=10, mu=0.0, seed=0)
    for a in m.agent_list:
        a.k, a.payoff = 3, 0.0
    winner = m.agent_list[4]
    winner.k, winner.payoff = -2, 1000.0
    m.reproduce()
    assert all(a.k == -2 for a in m.agent_list)         # everyone copied the winner


def test_reproduction_flat_fitness_is_uniform_not_a_crash():
    # All payoffs equal -> total shifted weight 0 -> uniform parent choice; strategies are
    # resampled (a valid strategy for everyone) without error.
    m = ImageScoringModel(n=30, mu=0.0, seed=1)
    for a in m.agent_list:
        a.payoff = 5.0
    ks_before = {a.k for a in m.agent_list}
    m.reproduce()
    assert all(a.k in K_VALUES for a in m.agent_list)
    assert all(a.k in ks_before for a in m.agent_list)  # only existing strategies survive


def test_mutation_can_introduce_new_strategies():
    # With mu=1 every offspring is a fresh random strategy, independent of parents.
    m = ImageScoringModel(n=200, mu=1.0, init_strategy="0", seed=2)
    for a in m.agent_list:
        a.payoff = 1.0
    m.reproduce()
    seen = {a.k for a in m.agent_list}
    assert len(seen) > 1                                 # mutation spread strategies out
    assert seen.issubset(set(K_VALUES))


def test_no_mutation_keeps_strategies_within_parent_set():
    m = ImageScoringModel(n=50, mu=0.0, init_strategy="0", seed=0)
    for a in m.agent_list:
        a.payoff = float(a.id)                # distinct payoffs, all parents are k=0
    m.reproduce()
    assert all(a.k == 0 for a in m.agent_list)   # only k=0 parents exist -> all k=0


# -- metrics + helpers --------------------------------------------------------

def test_coop_strategy_fraction_counts_non_defector_strategies():
    m = ImageScoringModel(n=10, seed=0)
    for i, a in enumerate(m.agent_list):
        a.k = 6 if i < 4 else 0               # 4 defectors, 6 stern discriminators
    assert m.coop_strategy_fraction() == pytest.approx(0.6)
    for a in m.agent_list:
        a.k = 6
    assert m.coop_strategy_fraction() == pytest.approx(0.0)
    for a in m.agent_list:
        a.k = -5
    assert m.coop_strategy_fraction() == pytest.approx(1.0)


def test_strategy_frequency_and_mean_k():
    m = ImageScoringModel(n=4, seed=0)
    for a, k in zip(m.agent_list, [0, 0, 2, -2]):
        a.k = k
    assert m.strategy_frequency(0) == pytest.approx(0.5)
    assert m.mean_k() == pytest.approx(0.0)


def test_modal_strategy_picks_the_most_common_threshold():
    counts = {k: 0 for k in K_VALUES}
    counts[0] = 40
    counts[3] = 10
    counts[-1] = 5
    assert modal_strategy(counts) == 0
    # tie broken toward the smaller |k| then smaller k
    counts2 = {k: 0 for k in K_VALUES}
    counts2[2] = 7
    counts2[-2] = 7
    assert modal_strategy(counts2) == -2         # |2|==|-2|, smaller k wins


def test_tail_mean_is_trailing_window_mean():
    series = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert tail_mean(series, last=2) == pytest.approx(0.45)   # mean(0.4, 0.5)
    assert tail_mean(series, last=100) == pytest.approx(0.3)  # whole series
    assert tail_mean([], last=5) == 0.0


# -- run summary shape --------------------------------------------------------

def test_run_summary_shape():
    res = run_single(n=50, q=1.0, seed=0, n_generations=20)
    assert res["n"] == 50 and res["q"] == 1.0
    assert len(res["coop_act_series"]) == 21           # t=0 baseline + 20 gens
    assert len(res["coop_strategy_series"]) == 21
    assert len(res["mean_k_series"]) == 21
    assert sum(res["final_strategy_counts"].values()) == 50
    assert 0.0 <= res["final_coop_strategy_fraction"] <= 1.0


# -- determinism --------------------------------------------------------------

def test_determinism_same_seed_identical_result():
    a = run_single(n=50, q=1.0, seed=42, n_generations=40)
    b = run_single(n=50, q=1.0, seed=42, n_generations=40)
    assert a["coop_act_series"] == b["coop_act_series"]
    assert a["coop_strategy_series"] == b["coop_strategy_series"]
    assert a["final_strategy_counts"] == b["final_strategy_counts"]


def test_different_seed_can_differ_but_stays_shaped():
    a = run_single(n=50, q=1.0, seed=1, n_generations=40)
    b = run_single(n=50, q=1.0, seed=2, n_generations=40)
    for res in (a, b):
        assert all(0.0 <= x <= 1.0 for x in res["coop_act_series"])
        assert all(0.0 <= x <= 1.0 for x in res["coop_strategy_series"])


# -- qualitative sanity (the locked grade lives in run.py) --------------------

def test_full_info_no_mutation_establishes_cooperation_then_drifts():
    # Faithfulness sanity, NOT the locked grade. With q=1 and no mutation, cooperation is
    # established (coop-act fraction -> 1) and the population fixes on a COOPERATIVE
    # strategy (k <= 0), but which one is neutral drift: once everyone helps and images
    # saturate, all k <= 0 strategies are payoff-equivalent, so the population does NOT
    # reliably settle on exactly k=0 (this is the known drift of plain image scoring; P1
    # in run.py grades the paper's idealised k=0 claim honestly, expecting a MISS here).
    res = run_single(n=100, q=1.0, mu=0.0, seed=0, n_generations=500)
    assert res["coop_act_series"][-1] > 0.9              # cooperation is established
    assert res["final_coop_strategy_fraction"] > 0.9     # fixed on cooperative strategies
    assert res["final_mean_k"] <= 0.5                     # among the cooperative (k<=0) block


def test_full_info_no_mutation_fixes_on_a_single_strategy():
    # Without mutation the population fixes (a single strategy holds nearly everyone),
    # even though which cooperative strategy varies by seed.
    res = run_single(n=100, q=1.0, mu=0.0, seed=3, n_generations=500)
    counts = res["final_strategy_counts"]
    modal_count = max(counts.values())
    assert modal_count >= 95            # near-fixation on one strategy (n=100)
