"""Faithful-rule + determinism tests for the minimal Naming Game reproduction.

These pin the NG interaction rule (random ordered pair; speaker utters a name —
invent-if-empty / uniform pick otherwise; success collapses BOTH to the uttered name,
failure adds it to the hearer), the empty-start inventories, unique invention, the
total-words / distinct-names metrics, the absorbing global-consensus state, determinism
(same seed -> identical run), and the run-summary shape. They are faithfulness tests,
NOT prediction tests (the locked predictions P1-P3 are evaluated by
examples/repro_naming_game/run.py).
"""
from __future__ import annotations

import pytest

from abm_auto.classics.naming_game import (
    NamerAgent,
    NamingGameModel,
    run_many_seeds,
    run_single,
)


def test_initial_inventories_empty():
    m = NamingGameModel(n=100, seed=0)
    assert m.n == 100
    assert all(len(a.inventory) == 0 for a in m.namers)
    assert m.total_words() == 0
    assert m.distinct_names() == 0
    assert not m.at_consensus()


def test_utter_invents_unique_name_when_empty():
    m = NamingGameModel(n=10, seed=0)
    a, b = m.namers[0], m.namers[1]
    name_a = a.utter()              # empty -> invent + add to own inventory
    name_b = b.utter()
    assert a.inventory == {name_a}
    assert b.inventory == {name_b}
    assert name_a != name_b         # invented names are globally unique


def test_utter_picks_from_own_inventory_when_nonempty():
    m = NamingGameModel(n=10, seed=0)
    a = m.namers[0]
    a.inventory = {7, 8, 9}
    for _ in range(50):
        name = a.utter()
        assert name in {7, 8, 9}    # only ever an existing own name
    assert a.inventory == {7, 8, 9}  # uttering an existing name does not change inventory


def test_success_collapses_both_to_uttered_name():
    m = NamingGameModel(n=4, seed=0)
    speaker, hearer = m.namers[0], m.namers[1]
    speaker.inventory = {1, 2, 3}
    hearer.inventory = {3, 4, 5}    # hearer HAS name 3 -> success path
    speaker.adopt_success(3)
    hearer.adopt_success(3)
    assert speaker.inventory == {3}
    assert hearer.inventory == {3}


def test_failure_adds_name_to_hearer_only():
    m = NamingGameModel(n=4, seed=0)
    speaker, hearer = m.namers[0], m.namers[1]
    speaker.inventory = {1, 2}
    hearer.inventory = {9}
    hearer.hear_failure(1)          # hearer lacks name 1 -> failure
    assert hearer.inventory == {1, 9}
    assert speaker.inventory == {1, 2}   # speaker unchanged on failure


def test_interact_success_and_failure_paths():
    # Force a known success: both agents share exactly one name.
    m = NamingGameModel(n=2, seed=0)
    m.namers[0].inventory = {42}
    m.namers[1].inventory = {42}
    # pair must be (speaker, hearer) distinct; with n=2 both orderings succeed.
    assert m.interact() is True
    assert m.namers[0].inventory == {42}
    assert m.namers[1].inventory == {42}


def test_total_words_and_distinct_names_metrics():
    m = NamingGameModel(n=3, seed=0)
    m.namers[0].inventory = {1, 2}
    m.namers[1].inventory = {2, 3}
    m.namers[2].inventory = {3}
    assert m.total_words() == 5           # 2 + 2 + 1
    assert m.distinct_names() == 3        # {1, 2, 3}


def test_invent_name_is_monotonic_and_unique():
    m = NamingGameModel(n=5, seed=0)
    names = [m.invent_name() for _ in range(5)]
    assert names == [0, 1, 2, 3, 4]
    assert len(set(names)) == 5


def test_consensus_detection_requires_identical_single_name():
    m = NamingGameModel(n=3, seed=0)
    m.namers[0].inventory = {7}
    m.namers[1].inventory = {7}
    m.namers[2].inventory = {7}
    assert m.at_consensus()
    assert m.consensus_name() == 7
    # disagreement on the single name -> NOT consensus
    m.namers[2].inventory = {8}
    assert not m.at_consensus()
    assert m.consensus_name() is None
    # an agent holding two names -> NOT consensus even if one matches
    m.namers[2].inventory = {7, 8}
    assert not m.at_consensus()


def test_consensus_is_absorbing():
    # Once every inventory is the same single name, no interaction changes anything.
    m = NamingGameModel(n=10, seed=0)
    for a in m.namers:
        a.inventory = {99}
    assert m.at_consensus()
    for _ in range(200):
        assert m.interact() is True       # every utterance is 99 -> always a success
        assert m.at_consensus()
        assert m.total_words() == 10
        assert m.distinct_names() == 1


def test_run_reaches_consensus_small():
    res = run_single(n=50, seed=1)
    assert res["reached_consensus"] is True
    assert res["capped"] is False
    assert res["final_total_words"] == res["n"]      # each agent ends with exactly 1
    assert res["final_distinct_names"] == 1          # one shared name
    assert res["consensus_name"] is not None
    assert res["interactions_to_consensus"] == res["total_interactions"]
    # NG signature: vocabulary peaks above N, distinct names peak above 1
    assert res["peak_total_words"] > res["n"]
    assert res["peak_distinct_names"] > 1


def test_each_agent_ends_with_exactly_one_name():
    m = NamingGameModel(n=40, seed=2)
    m.run()
    assert all(len(a.inventory) == 1 for a in m.namers)
    only = {next(iter(a.inventory)) for a in m.namers}
    assert len(only) == 1                            # all share the SAME single name


def test_determinism_same_seed_identical_run():
    a = run_single(n=100, seed=7)
    b = run_single(n=100, seed=7)
    assert a["total_interactions"] == b["total_interactions"]
    assert a["consensus_name"] == b["consensus_name"]
    assert a["total_words_series"] == b["total_words_series"]
    assert a["distinct_names_series"] == b["distinct_names_series"]


def test_different_seeds_can_differ():
    times = {run_single(n=100, seed=s)["total_interactions"] for s in range(8)}
    assert len(times) > 1


def test_run_many_seeds_shape_and_determinism():
    a = run_many_seeds(n=60, n_runs=10, seed_base=0)
    b = run_many_seeds(n=60, n_runs=10, seed_base=0)
    assert a["consensus_fraction"] == b["consensus_fraction"]
    assert a["per_run"] == b["per_run"]
    assert a["n_runs"] == 10
    # every run reaches consensus at this small N
    assert a["consensus_fraction"] == 1.0
    # NG signature aggregated: distinct names peak >1 and final =1; words peak >N, final =N
    assert a["peak_distinct_names"]["min"] > 1
    assert a["final_distinct_names"]["max"] == 1
    assert a["peak_total_words"]["min"] > a["n"]
    assert a["final_total_words"]["min"] == a["n"]
    assert a["final_total_words"]["max"] == a["n"]
    ct = a["convergence_interactions"]
    assert ct["min"] <= ct["mean"] <= ct["max"]
    assert ct["n"] == 10


def test_invalid_n_rejected():
    with pytest.raises(ValueError):
        NamingGameModel(n=1)


def test_step_is_noop_scheduler_not_driver():
    # The platform scheduler must not drive the async NG (agent.step is a no-op).
    m = NamingGameModel(n=10, seed=0)
    before = m.total_words()
    for a in m.namers:
        a.step()
    assert m.total_words() == before == 0
