# Failure Pack Evidence Foundry Challenge

This is a non-MIR seed pack for the MyMoMo Evidence Foundry challenge harness.
It does not rerun a simulation or repair a failed claim. It checks whether an
agent answer matches the committed failure-pack evidence.

The directory name remains `autodata-challenges` for compatibility with existing
commands and tests; user-facing naming is MyMoMo Evidence Foundry.

## Files

- `producer-spec.json`: hash-free source spec that regenerates
  `challenge-pack.json` from committed Evidence Foundry artifacts.
- `challenge-pack.json`: portable challenge manifest with strong hashes for the
  failure-pack evidence.
- `answer-codex.json`: reference answer manifest used to dogfood the grader.

## Reviewer Commands

Regenerate the pack from the producer spec:

`.venv/bin/python -m abm_auto.repro_challenge produce docs/reproduce/autodata-challenges/failure-pack-example/producer-spec.json --repo . --out /tmp/failure-pack-challenge-pack.json`

Gate the reference answer:

`.venv/bin/python -m abm_auto.repro_challenge gate docs/reproduce/autodata-challenges/failure-pack-example/challenge-pack.json docs/reproduce/autodata-challenges/failure-pack-example/answer-codex.json --repo .`

Gate all registered challenge answers:

`.venv/bin/python -m abm_auto.repro_challenge registry-gate docs/reproduce/autodata-challenges/registry.json --repo .`

Run all Evidence Foundry health checks:

`.venv/bin/python -m abm_auto.evidence_foundry_batch doctor docs/reproduce/evidence-foundry/batch-registry.json --challenge-registry docs/reproduce/autodata-challenges/registry.json --challenge-root docs/reproduce/autodata-challenges --repo .`

Passing this challenge means the answer aligns with committed failure-pack
evidence. It is not a reproduction rerun and not a scientific truth certificate.
