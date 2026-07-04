"""Deterministic social-platform environment seam."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/social-platform-scenario/v1"
SUPPORTED_RULES = frozenset({"boost_topic", "follows_only"})


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _ids(items: list[dict]) -> set[str]:
    return {item["id"] for item in items if isinstance(item, dict) and _is_nonempty_string(item.get("id"))}


def validate_social_platform_scenario(scenario: dict) -> dict:
    """Validate a tiny social-platform environment scenario."""
    if not isinstance(scenario, dict):
        return {"ok": False, "issues": ["scenario must be a JSON object"]}

    issues: list[str] = []
    if scenario.get("schema") != SCHEMA:
        issues.append(f"schema must be {SCHEMA}")
    if not _is_nonempty_string(scenario.get("scenario_id")):
        issues.append("scenario_id must be a non-empty string")
    if not _is_nonempty_string(scenario.get("target_action")):
        issues.append("target_action must be a non-empty string")

    agents = scenario.get("agents")
    if not isinstance(agents, list) or not agents:
        issues.append("agents must be a non-empty list")
        agents = []
    for idx, agent in enumerate(agents):
        if not isinstance(agent, dict):
            issues.append(f"agents[{idx}] must be an object")
            continue
        for field in ("id", "interest"):
            if not _is_nonempty_string(agent.get(field)):
                issues.append(f"agents[{idx}].{field} must be a non-empty string")

    agent_ids = _ids(agents)
    posts = scenario.get("posts")
    if not isinstance(posts, list) or not posts:
        issues.append("posts must be a non-empty list")
        posts = []
    for idx, post in enumerate(posts):
        if not isinstance(post, dict):
            issues.append(f"posts[{idx}] must be an object")
            continue
        for field in ("id", "author", "topic", "action"):
            if not _is_nonempty_string(post.get(field)):
                issues.append(f"posts[{idx}].{field} must be a non-empty string")
        if _is_nonempty_string(post.get("author")) and post["author"] not in agent_ids:
            issues.append(f"posts[{idx}].author references unknown agent {post['author']}")

    follows = scenario.get("follows")
    if not isinstance(follows, list):
        issues.append("follows must be a list")
        follows = []
    for idx, follow in enumerate(follows):
        if not isinstance(follow, dict):
            issues.append(f"follows[{idx}] must be an object")
            continue
        for field in ("follower", "followee"):
            if not _is_nonempty_string(follow.get(field)):
                issues.append(f"follows[{idx}].{field} must be a non-empty string")
        if _is_nonempty_string(follow.get("follower")) and follow["follower"] not in agent_ids:
            issues.append(f"follows[{idx}].follower references unknown agent {follow['follower']}")
        if _is_nonempty_string(follow.get("followee")) and follow["followee"] not in agent_ids:
            issues.append(f"follows[{idx}].followee references unknown agent {follow['followee']}")

    rules = scenario.get("recommendation_rules")
    if not isinstance(rules, dict):
        issues.append("recommendation_rules must be an object")
        rules = {}
    for rule_name in rules:
        if rule_name not in SUPPORTED_RULES:
            issues.append(f"unsupported recommendation rule {rule_name}")
    if "follows_only" not in rules:
        issues.append("recommendation_rules must include follows_only")
    if "boost_topic" not in rules:
        issues.append("recommendation_rules must include boost_topic")
    boost = rules.get("boost_topic", {})
    if isinstance(boost, dict) and "boost_topic" in rules and not _is_nonempty_string(boost.get("topic")):
        issues.append("recommendation_rules.boost_topic.topic must be a non-empty string")

    return {"ok": not issues, "issues": issues}


def load_social_platform_scenario(path: Path) -> dict:
    """Load a social-platform scenario JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _followees_by_follower(follows: list[dict]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for follow in follows:
        result.setdefault(follow["follower"], set()).add(follow["followee"])
    return result


def run_social_platform_environment(
    scenario: dict,
    *,
    recommendation_rule: str,
) -> dict:
    """Run one deterministic exposure pass for a recommendation rule."""
    validation = validate_social_platform_scenario(scenario)
    if not validation["ok"]:
        return {"ok": False, "issues": validation["issues"]}
    if recommendation_rule not in SUPPORTED_RULES:
        return {"ok": False, "issues": [f"unsupported recommendation rule {recommendation_rule}"]}

    followees = _followees_by_follower(scenario["follows"])
    boost_topic = scenario["recommendation_rules"].get("boost_topic", {}).get("topic")
    exposures: list[dict] = []
    target_action_count = 0

    for agent in scenario["agents"]:
        seen_post_ids: set[str] = set()
        for post in scenario["posts"]:
            follows_author = post["author"] in followees.get(agent["id"], set())
            boosted = recommendation_rule == "boost_topic" and post["topic"] == boost_topic
            if recommendation_rule == "follows_only" and not follows_author:
                continue
            if recommendation_rule == "boost_topic" and not (follows_author or boosted):
                continue
            if post["id"] in seen_post_ids:
                continue
            seen_post_ids.add(post["id"])
            exposures.append({"agent_id": agent["id"], "post_id": post["id"]})
            if post["action"] == scenario["target_action"] and post["topic"] == agent["interest"]:
                target_action_count += 1

    return {
        "ok": True,
        "rule": recommendation_rule,
        "exposures": exposures,
        "exposure_count": len(exposures),
        "target_action_count": target_action_count,
    }


def social_platform_exposure_gate(scenario: dict) -> tuple[bool, str]:
    """Gate that recommendation-mediated exposure affects a deterministic fixture."""
    follows = run_social_platform_environment(scenario, recommendation_rule="follows_only")
    boosted = run_social_platform_environment(scenario, recommendation_rule="boost_topic")
    if not follows.get("ok"):
        return False, f"Social platform exposure gate failed follows_only run: {follows['issues'][:3]}"
    if not boosted.get("ok"):
        return False, f"Social platform exposure gate failed boost_topic run: {boosted['issues'][:3]}"

    exposure_lift = boosted["exposure_count"] - follows["exposure_count"]
    action_lift = boosted["target_action_count"] - follows["target_action_count"]
    ok = exposure_lift > 0 or action_lift > 0
    status = "passed" if ok else "failed"
    return (
        ok,
        "Social platform exposure gate "
        f"{status} (exposure_lift={exposure_lift}, action_lift={action_lift}); "
        "proves environment-mediated exposure affects this deterministic fixture, "
        "not real social-media validity",
    )


__all__ = [
    "SCHEMA",
    "SUPPORTED_RULES",
    "load_social_platform_scenario",
    "run_social_platform_environment",
    "social_platform_exposure_gate",
    "validate_social_platform_scenario",
]
