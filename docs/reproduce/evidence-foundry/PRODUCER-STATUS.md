# Evidence Foundry Producer Status

**Status:** Covered by existing implementation.
**Date:** 2026-07-01

## What Is Covered

Evidence Foundry challenge production is implemented by the generic challenge
helper:

```text
abm_auto.repro_challenge.validate_challenge_producer_spec
abm_auto.repro_challenge.build_challenge_pack_from_producer_spec
```

CLI:

```bash
.venv/bin/python -m abm_auto.repro_challenge produce \
  docs/reproduce/autodata-challenges/mir-v0-half-a/producer-spec.json \
  --repo . \
  --out /tmp/mir-v0-challenge-pack.json
```

The producer flow:

- validates a hash-free `producer-spec.json`;
- requires repo-relative artifact paths;
- fingerprints referenced evidence artifacts;
- writes a hash-addressed `challenge-pack.json`;
- validates the generated pack.

## Verification Coverage

The behavior is covered by:

```text
tests/test_repro_challenge.py::test_committed_producer_spec_rebuilds_mir_dogfood_pack
tests/test_repro_challenge.py::test_validate_challenge_producer_spec_rejects_bad_paths_and_claims
tests/test_repro_challenge.py::test_repro_challenge_module_cli_produces_pack_from_spec
```

## Design Boundary

No new runtime implementation is needed in `abm_auto.evidence_foundry_batch`.
The producer belongs to challenge-pack authoring, while the batch gate handles
already-committed artifact health. Keeping one implementation avoids two
competing fingerprint/render paths for the same challenge pack schema.

This helper creates challenge packs from declared artifacts and locked expected
claims. It does not infer claims, generate answers, execute models, or certify
scientific truth. Generated packs must still pass validation, answer grading,
registry gates, batch gates, or the top-level Evidence Foundry doctor.
