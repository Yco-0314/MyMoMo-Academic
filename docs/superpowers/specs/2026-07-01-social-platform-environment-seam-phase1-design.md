# Social-Platform Environment Seam Phase 1 Design

**Status:** Design for minimal implementation.
**Date:** 2026-07-01
**Scope:** Add a tiny deterministic social-platform environment seam with posts,
follows, exposures, comments, and one declared recommendation rule.

## Summary

LLM-agent or synthetic society simulations are not only collections of agents.
The platform environment matters: who sees which post, which recommendation rule
creates exposure, and which environment event changes behavior.

Phase 1 adds a deterministic, non-LLM social-platform environment fixture. It
proves that changing the exposure rule can change measured outcomes. It does not
claim real social-media validity.

## Architecture

Add:

```text
abm_auto/social_platform.py
```

Scenario schema:

```text
abm-auto/social-platform-scenario/v1
```

Seed scenario:

```text
docs/reproduce/social-platform-environment/example-feed/scenario.json
```

Core API:

```python
load_social_platform_scenario(path: Path) -> dict
validate_social_platform_scenario(scenario: dict) -> dict
run_social_platform_environment(scenario: dict, *, recommendation_rule: str) -> dict
social_platform_exposure_gate(scenario: dict) -> tuple[bool, str]
```

## Minimal Semantics

Scenario contains:

- `agents`: `id`, `interest`;
- `posts`: `id`, `author`, `topic`, `action`;
- `follows`: follower/followee pairs;
- `recommendation_rules`: named rules;
- `target_action`: action counted as the behavioral outcome.

Supported rules in Phase 1:

- `follows_only`: an agent sees posts authored by accounts they follow;
- `boost_topic`: an agent sees followed posts plus posts whose topic matches
  `boost_topic`.

Outcome:

- exposure count;
- action count, where an exposed post counts if its `action` equals
  `target_action` and its `topic` equals the viewer's `interest`.

## Gate

`social_platform_exposure_gate` compares `follows_only` and `boost_topic`.

Pass condition:

- boosted rule produces more exposures or more target actions than follows-only;
- both runs validate;
- description states this proves environment-mediated exposure has behavioral
  effect in a deterministic fixture, not real social-media validity.

## Non-Goals

- No LLM agents.
- No recommendation learning.
- No social-media scale.
- No moderation.
- No feed ranking beyond the two deterministic rules.
- No real user data.
- No claim of real platform validity.

## Acceptance Criteria

- Unit tests cover scenario validation, unknown follow references, rule behavior,
  gate pass, no-effect gate fail, seed scenario loading, and boundary wording.
- Platform capability registry includes `social_platform_environment_seam`.
- Forbidden base-engine diff remains empty.
