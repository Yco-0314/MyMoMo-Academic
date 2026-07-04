from __future__ import annotations

from pathlib import Path

from abm_auto.social_platform import (
    load_social_platform_scenario,
    run_social_platform_environment,
    social_platform_exposure_gate,
    validate_social_platform_scenario,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = REPO_ROOT / "docs/reproduce/social-platform-environment/example-feed/scenario.json"


def _scenario(**overrides):
    scenario = {
        "schema": "abm-auto/social-platform-scenario/v1",
        "scenario_id": "example-feed-v1",
        "agents": [
            {"id": "alice", "interest": "evacuation"},
            {"id": "bob", "interest": "sports"},
            {"id": "city", "interest": "evacuation"},
        ],
        "posts": [
            {"id": "p_city", "author": "city", "topic": "evacuation", "action": "evacuate"},
            {"id": "p_bob", "author": "bob", "topic": "sports", "action": "ignore"},
        ],
        "follows": [
            {"follower": "alice", "followee": "bob"},
            {"follower": "bob", "followee": "city"},
        ],
        "recommendation_rules": {
            "follows_only": {},
            "boost_topic": {"topic": "evacuation"},
        },
        "target_action": "evacuate",
        "boundary_note": "Deterministic fixture only; not real social-media validity.",
    }
    scenario.update(overrides)
    return scenario


def test_valid_social_platform_scenario_passes():
    result = validate_social_platform_scenario(_scenario())

    assert result == {"ok": True, "issues": []}


def test_unknown_follow_reference_fails():
    scenario = _scenario(follows=[
        {"follower": "alice", "followee": "unknown"},
    ])

    result = validate_social_platform_scenario(scenario)

    assert result["ok"] is False
    assert "follows[0].followee references unknown agent unknown" in result["issues"]


def test_boost_topic_creates_more_exposure_and_action():
    scenario = _scenario()

    follows = run_social_platform_environment(scenario, recommendation_rule="follows_only")
    boosted = run_social_platform_environment(scenario, recommendation_rule="boost_topic")

    assert follows["exposure_count"] == 2
    assert follows["target_action_count"] == 0
    assert boosted["exposure_count"] == 4
    assert boosted["target_action_count"] == 2


def test_social_platform_exposure_gate_passes_for_seed_like_scenario():
    ok, desc = social_platform_exposure_gate(_scenario())

    assert ok is True
    assert desc.startswith("Social platform exposure gate passed")
    assert "environment-mediated exposure" in desc
    assert "not real social-media validity" in desc


def test_social_platform_exposure_gate_fails_when_boost_has_no_effect():
    scenario = _scenario(recommendation_rules={
        "follows_only": {},
        "boost_topic": {"topic": "nonexistent"},
    })

    ok, desc = social_platform_exposure_gate(scenario)

    assert ok is False
    assert desc.startswith("Social platform exposure gate failed")


def test_committed_social_platform_scenario_loads_and_passes_gate():
    scenario = load_social_platform_scenario(SCENARIO_PATH)

    assert validate_social_platform_scenario(scenario)["ok"] is True
    ok, _ = social_platform_exposure_gate(scenario)
    assert ok is True
