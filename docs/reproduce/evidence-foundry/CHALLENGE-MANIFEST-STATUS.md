# Evidence Foundry Challenge Manifest Status

Evidence Foundry Challenge Manifest Phase 2 adds a pre-run contract layer above
the existing challenge-pack answer grader.

Implemented public surface:

- `abm_auto.evidence_challenge_manifest`
- `validate_evidence_challenge_manifest(...)`
- `evidence_challenge_manifest_gate(...)`
- CLI commands:
  - `.venv/bin/python -m abm_auto.evidence_challenge_manifest validate <manifest> --repo .`
  - `.venv/bin/python -m abm_auto.evidence_challenge_manifest gate <manifest> --repo .`

Seed fixture:

- `docs/reproduce/evidence-foundry/challenge-manifest-example/challenge-manifest.json`
- `docs/reproduce/evidence-foundry/challenge-manifest-example/source-manifest.json`

Batch integration:

- `docs/reproduce/evidence-foundry/batch-registry.json` includes
  `kind="evidence_challenge_manifest"`.
- `docs/reproduce/evidence-foundry/BATCH-REPORT.md` includes the manifest gate.
- `docs/reproduce/platform-capabilities/registry.json` registers
  `evidence_foundry_challenge_manifest` as native Evidence Foundry capability.

Boundary:

This gate validates claim/data/gate/verdict/failure-report contract
completeness only. It does not execute declared gate commands, rerun a paper
reproduction, call an LLM, generate datasets, disclose private artifacts, or
certify scientific truth.
