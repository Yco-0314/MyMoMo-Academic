# MIR v0 Half A Evidence Foundry Challenge

This is a dogfood pack for the MyMoMo Evidence Foundry challenge harness.
It does not rerun MIR, GIS codegen, or any model reproduction. It checks whether
an agent answer matches locked, hash-addressed evidence.

The directory name remains `autodata-challenges` for compatibility with existing
packs and tests; user-facing naming is now MyMoMo Evidence Foundry.

## Files

- `challenge-pack.json`: portable challenge manifest with strong hashes for the
  locked MIR v0 evidence artifacts.
- `producer-spec.json`: hash-free source spec that regenerates
  `challenge-pack.json` from committed evidence files.
- `answer-codex.json`: reference answer manifest used to dogfood the grader.

## Reviewer Command

Run:

`.venv/bin/python -m pytest tests/test_repro_challenge.py::test_committed_mir_v0_dogfood_pack_validates_and_grades -q`

Regenerate the pack from the producer spec:

`.venv/bin/python -m abm_auto.repro_challenge produce docs/reproduce/autodata-challenges/mir-v0-half-a/producer-spec.json --repo . --out /tmp/mir-v0-challenge-pack.json`

Audit registry discovery:

`.venv/bin/python -m abm_auto.repro_challenge registry-audit docs/reproduce/autodata-challenges/registry.json docs/reproduce/autodata-challenges --repo .`

Gate all registered challenge answers:

`.venv/bin/python -m abm_auto.repro_challenge registry-gate docs/reproduce/autodata-challenges/registry.json --repo .`

Create a blank answer manifest:

`.venv/bin/python -m abm_auto.repro_challenge answer-template docs/reproduce/autodata-challenges/mir-v0-half-a/challenge-pack.json --out /tmp/mir-v0-answer-template.json`

Write a Markdown registry report:

`.venv/bin/python -m abm_auto.repro_challenge registry-report docs/reproduce/autodata-challenges/registry.json --repo . --out /tmp/autodata-registry-report.md`

Run all Evidence Foundry challenge health checks:

`.venv/bin/python -m abm_auto.repro_challenge doctor docs/reproduce/autodata-challenges/registry.json docs/reproduce/autodata-challenges --repo .`

Passing this test means the pack validates and the answer aligns with the
evidence. It is not a MIR rerun and not a scientific truth certificate.
