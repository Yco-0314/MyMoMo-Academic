# Evidence Foundry Answer Template Status

**Status:** Covered by existing implementation.
**Date:** 2026-07-01

## What Is Covered

Evidence Foundry answer templates are implemented by the generic challenge
helper:

```text
abm_auto.repro_challenge.build_answer_template
```

CLI:

```bash
.venv/bin/python -m abm_auto.repro_challenge answer-template \
  docs/reproduce/autodata-challenges/mir-v0-half-a/challenge-pack.json \
  --out /tmp/answer-template.json
```

The generated answer manifest includes:

- `schema`;
- `task_id`;
- one `claims` row per expected claim id;
- default `INCONCLUSIVE` verdicts;
- empty citation lists for every claim.

## Verification Coverage

The behavior is covered by:

```text
tests/test_repro_challenge.py::test_build_answer_template_from_challenge_pack
tests/test_repro_challenge.py::test_repro_challenge_module_cli_writes_answer_template
```

## Design Boundary

No new runtime implementation is needed in `abm_auto.evidence_foundry_batch`.
The answer template belongs to challenge-pack authoring and handoff, while the
batch gate handles committed artifact health. Keeping one implementation avoids
two competing answer JSON contracts.

This helper creates a blank answer shape. It does not generate a scientific
answer, read evidence, execute a model, validate claims, or certify truth. The
filled answer must still pass `grade`, `gate`, `registry-gate`, or the top-level
Evidence Foundry doctor.
