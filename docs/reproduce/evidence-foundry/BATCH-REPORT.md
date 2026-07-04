# MyMoMo Evidence Foundry Batch Report

- Registry: MyMoMo Evidence Foundry Seed Batch
- Overall gate: PASS
- Entries: 13
- Failed: 0

| Entry | Kind | Gate |
|---|---|---|
| challenge-registry | repro_challenge_registry | PASS |
| failure-pack | failure_pack | PASS |
| counterfactual | counterfactual_challenge | PASS |
| mechanism | mechanism_challenge | PASS |
| synthetic-population | synthetic_population_manifest | PASS |
| llm-replay | llm_agent_replay | PASS |
| synthetic-survey | synthetic_survey_gate | PASS |
| social-platform | social_platform_environment | PASS |
| transport-bridge | transport_bridge_manifest | PASS |
| platform-capability-registry | platform_capability_registry | PASS |
| unified-abm-bridge | unified_abm_bridge_contract | PASS |
| terrain-bridge | terrain_bridge_manifest | PASS |
| agent-handoff-note | agent_handoff_note | PASS |

## Capability Classifications

| Domain | Disposition | Evidence Level | Count |
|---|---|---|---:|
| closed_extension | bridge | E0 | 1 |
| evidence | native | E0 | 12 |
| gama | native | E0 | 1 |
| gama | native | E2 | 1 |
| gama | out_of_scope | E0 | 1 |
| llm_society | native | E0 | 4 |
| platform | audit_baseline | E0 | 1 |
| platform | bridge | E0 | 2 |
| transport | bridge | E1 | 1 |

## Notes

- `challenge-registry`: repro challenge registry gate passed (entries=2, failed=0); checks answer/evidence alignment only
- `failure-pack`: failure_pack validation passed
- `counterfactual`: Counterfactual challenge gate passed (verdict=PASS, primary_error=0.06, alternative_error=0.65); compares recorded candidate metrics, not causal proof
- `mechanism`: Mechanism challenge gate passed (verdict=PASS, matched=3/3); signature presence is mechanism evidence only, not scientific truth
- `synthetic-population`: synthetic_population_manifest validation passed
- `llm-replay`: llm_agent_replay validation passed
- `synthetic-survey`: synthetic survey gate passed (verdict=PASS, compared_rows=4); does not validate synthetic people as human substitutes
- `social-platform`: Social platform exposure gate passed (exposure_lift=2, action_lift=2); proves environment-mediated exposure affects this deterministic fixture, not real social-media validity
- `transport-bridge`: transport_bridge_manifest validation passed
- `platform-capability-registry`: platform capability registry validation passed (entries=24); classification health only, not runtime bridge execution
- `unified-abm-bridge`: Unified ABM bridge contract gate passed (participants=6, artifacts=6); not a unified runtime; not a scientific truth certificate
- `terrain-bridge`: Terrain bridge manifest gate passed (consumers=4); not a 3D renderer; not a physical simulation certificate
- `agent-handoff-note`: Agent handoff gate passed (headings=11/11, fields=28/28, issues=0); checks handoff completeness, not factual truth

This report checks committed artifact health only; it is not a scientific truth certificate.
