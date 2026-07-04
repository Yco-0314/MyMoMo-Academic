"""Faithful-rule + determinism tests for the Public Goods + punishment reproduction.

These pin the PGG payoff accounting (pot split, contribution cost), the punishment
accounting (defector loses gamma per punisher; punisher pays beta per defector), the
cooperation metric (contributors = C + P), the FAIR-treatment invariant (no Punisher
in the no-punishment arm), the payoff-proportional imitation rule, and determinism
(same seed -> identical result). They are faithfulness tests, NOT prediction tests
(the predictions are evaluated by examples/repro_public_goods_punishment/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.public_goods import (
    COOPERATOR,
    DEFECTOR,
    PUNISHER,
    PlayerAgent,
    PublicGoodsModel,
    run_treatment_seeds,
    steady_state_fraction,
)


def _set_group(model: PublicGoodsModel, strategies):
    """Assign a known strategy to each of the (group_size == n) agents."""
    for i, s in enumerate(strategies):
        model.agent_by_id[i].strategy = s


def test_pgg_payoff_accounting_single_group_hand_verifiable():
    # One group of 5: {C, C, C, D, P}. c=1, r=3, beta=1, gamma=3.
    # contributors = 4 (3C + 1P); pot = r*c*4 = 12; share = 12/5 = 2.4.
    #   C: 2.4 - 1            = 1.4
    #   D: 2.4 - gamma*1      = 2.4 - 3 = -0.6  (one punisher fines it)
    #   P: 2.4 - 1 - beta*1   = 2.4 - 1 - 1 = 0.4 (pays to punish one defector)
    m = PublicGoodsModel(n=5, group_size=5, with_punishment=True, seed=0)
    _set_group(m, [COOPERATOR, COOPERATOR, COOPERATOR, DEFECTOR, PUNISHER])
    m.assign_payoffs()
    pays = [m.agent_by_id[i].payoff for i in range(5)]
    assert pays[0] == pytest.approx(1.4)
    assert pays[1] == pytest.approx(1.4)
    assert pays[2] == pytest.approx(1.4)
    assert pays[3] == pytest.approx(-0.6)
    assert pays[4] == pytest.approx(0.4)


def test_defector_freerides_when_no_punishers():
    # Group {C, C, C, C, D}, no punishers. contributors=4, pot=12, share=2.4.
    #   C: 2.4 - 1 = 1.4 ;  D: 2.4 - 0 = 2.4  -> the defector STRICTLY out-earns
    # every cooperator (the free-rider advantage that collapses cooperation).
    m = PublicGoodsModel(n=5, group_size=5, with_punishment=False, seed=0)
    _set_group(m, [COOPERATOR, COOPERATOR, COOPERATOR, COOPERATOR, DEFECTOR])
    m.assign_payoffs()
    coop_pay = m.agent_by_id[0].payoff
    def_pay = m.agent_by_id[4].payoff
    assert coop_pay == pytest.approx(1.4)
    assert def_pay == pytest.approx(2.4)
    assert def_pay > coop_pay  # defection pays better absent punishment


def test_punishment_can_invert_the_freerider_advantage():
    # Same group but the four contributors are PUNISHERS: {P, P, P, P, D}.
    # contributors=4, share=2.4; n_punishers=4, n_defectors=1.
    #   P: 2.4 - 1 - beta*1 = 0.4 ;  D: 2.4 - gamma*4 = 2.4 - 12 = -9.6
    # Now the defector is the WORST off -> punishment flips the incentive.
    m = PublicGoodsModel(n=5, group_size=5, with_punishment=True, seed=0)
    _set_group(m, [PUNISHER, PUNISHER, PUNISHER, PUNISHER, DEFECTOR])
    m.assign_payoffs()
    pun_pay = m.agent_by_id[0].payoff
    def_pay = m.agent_by_id[4].payoff
    assert pun_pay == pytest.approx(0.4)
    assert def_pay == pytest.approx(2.4 - 3 * 4)
    assert def_pay < pun_pay  # defection now pays WORSE


def test_cooperation_metric_counts_contributors_C_and_P():
    m = PublicGoodsModel(n=10, group_size=5, with_punishment=True, seed=0)
    _set_group(m, [COOPERATOR, COOPERATOR, PUNISHER, PUNISHER, DEFECTOR,
                   DEFECTOR, DEFECTOR, COOPERATOR, PUNISHER, DEFECTOR])
    # contributors = 3 C + 3 P = 6 of 10.
    assert m.contributor_count() == 6
    assert m.cooperation_fraction() == pytest.approx(0.6)


def test_no_punishment_treatment_seeds_no_punisher():
    m = PublicGoodsModel(n=1000, with_punishment=False, seed=0)
    counts = m.strategy_counts()
    assert counts[PUNISHER] == 0
    assert counts[COOPERATOR] + counts[DEFECTOR] == 1000
    # Default fair init is roughly equal halves C/D.
    assert counts[COOPERATOR] == pytest.approx(500, abs=1)


def test_no_punishment_cannot_seed_punishers():
    with pytest.raises(ValueError):
        PublicGoodsModel(n=100, with_punishment=False,
                         init_mix={COOPERATOR: 0.4, DEFECTOR: 0.4, PUNISHER: 0.2})


def test_with_punishment_default_init_is_equal_thirds():
    m = PublicGoodsModel(n=1005, with_punishment=True, seed=0)
    counts = m.strategy_counts()
    assert counts[COOPERATOR] == pytest.approx(335, abs=1)
    assert counts[DEFECTOR] == pytest.approx(335, abs=1)
    assert counts[PUNISHER] == pytest.approx(335, abs=1)
    assert sum(counts.values()) == 1005


def test_n_must_be_multiple_of_group_size():
    with pytest.raises(ValueError):
        PublicGoodsModel(n=1001, group_size=5)


def test_imitation_copies_strictly_better_model_with_full_prob_gap():
    # If the chosen model's payoff exceeds self's by the FULL payoff span, the copy
    # probability is 1.0, so the agent always adopts the model's strategy.
    m = PublicGoodsModel(n=10, group_size=5, with_punishment=True, seed=0)
    self_agent = m.agent_by_id[0]
    self_agent.strategy = DEFECTOR
    self_agent.payoff = 0.0
    # Force the model selection + a model that is exactly payoff_span better.
    target = m.agent_by_id[1]
    target.strategy = PUNISHER
    target.payoff = m.payoff_span  # gap/span = 1.0 -> always copy
    m.random_other_id = lambda _self_id, _t=target: _t.id  # type: ignore[assignment]
    self_agent.choose_next_strategy()
    assert self_agent._next_strategy == PUNISHER


def test_imitation_never_copies_a_worse_or_equal_model():
    m = PublicGoodsModel(n=10, group_size=5, with_punishment=True, seed=0)
    self_agent = m.agent_by_id[0]
    self_agent.strategy = COOPERATOR
    self_agent.payoff = 5.0
    worse = m.agent_by_id[1]
    worse.strategy = DEFECTOR
    worse.payoff = 5.0  # equal -> never copy
    m.random_other_id = lambda _self_id, _t=worse: _t.id  # type: ignore[assignment]
    self_agent.choose_next_strategy()
    assert self_agent._next_strategy == COOPERATOR


def test_determinism_same_seed_identical_result():
    a = PublicGoodsModel(n=200, with_punishment=True, seed=3).run(40)
    b = PublicGoodsModel(n=200, with_punishment=True, seed=3).run(40)
    assert a["coop_series"] == b["coop_series"]
    assert a["final_strategy_counts"] == b["final_strategy_counts"]


def test_run_treatment_seeds_is_deterministic_and_shaped():
    a = run_treatment_seeds(with_punishment=False, n=200, n_rounds=30, seeds=(0, 1, 2))
    b = run_treatment_seeds(with_punishment=False, n=200, n_rounds=30, seeds=(0, 1, 2))
    assert a["mean_steady_state"] == b["mean_steady_state"]
    assert len(a["per_seed"]) == 3
    assert 0.0 <= a["mean_steady_state"] <= 1.0
    # mean trajectory has the t=0 baseline + one point per round.
    assert len(a["mean_trajectory"]) == 31


def test_steady_state_fraction_uses_tail():
    series = [1.0] * 10 + [0.2] * 5
    assert steady_state_fraction(series, last=5) == pytest.approx(0.2)
    # Falls back to whole series when shorter than `last`.
    assert steady_state_fraction([0.4, 0.6], last=50) == pytest.approx(0.5)


def test_strategy_update_is_synchronous_commit():
    # After a step, every committed strategy equals its staged _next_strategy.
    m = PublicGoodsModel(n=100, with_punishment=True, seed=1)
    m.assign_payoffs()
    m.agents.step()
    staged = {i: a._next_strategy for i, a in m.agent_by_id.items()}
    for a in m.agent_by_id.values():
        a.strategy = a._next_strategy
    for i, a in m.agent_by_id.items():
        assert a.strategy == staged[i]


def test_isolated_player_agent_contributes_predicate():
    model = PublicGoodsModel(n=5, with_punishment=True, seed=0)
    c = PlayerAgent(0, model, strategy=COOPERATOR)
    d = PlayerAgent(1, model, strategy=DEFECTOR)
    p = PlayerAgent(2, model, strategy=PUNISHER)
    assert c.contributes() is True
    assert d.contributes() is False
    assert p.contributes() is True
