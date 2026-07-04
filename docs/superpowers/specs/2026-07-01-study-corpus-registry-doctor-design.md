# Study Corpus Registry / Doctor Phase 1

## Scope

Phase 1 adds a deterministic registry and doctor for `docs/studies`.
It is an artifact-health layer over the committed reproduction corpus:

- completed studies have `verdict-bundle.json`;
- prediction-locked studies without a bundle are reported as `pending_bundle`;
- bundle integrity is checked with the existing repro-bundle validator;
- generated registry and index files are deterministic and reviewable.

This does not run any model, alter any scientific verdict, or certify that a
finding is true. It checks that the corpus is structurally visible and that
committed bundle fingerprints still match committed documents.

## Why This Is Separate From Model Reproduction

Model reproduction remains the job of the reproduction worker. The registry
doctor is the corpus librarian:

- it can say which studies exist;
- it can say which studies are complete or pending;
- it can catch stale bundle fingerprints;
- it can report how many verdict clauses passed or failed.

It cannot decide whether a model should be considered reproduced beyond the
verdicts already locked into each bundle.

## Cross-Agent Working Tree Boundary

In a git checkout, discovery is intentionally committed-corpus-first: tracked
`verdict-bundle.json` files count as complete, tracked prediction locks without
tracked bundles count as `pending_bundle`, and untracked in-progress study
artifacts are ignored. This keeps the registry doctor stable while Claude Code
or another agent is still producing a model reproduction in the same working
tree.

Non-git temporary directories keep the simpler filesystem behavior so tests and
portable artifact packs do not need a repository.

## Behavior

`abm_auto.study_corpus` exposes:

- `discover_study_corpus(...)` for direct filesystem discovery;
- `build_study_registry(...)` for the deterministic JSON registry;
- `validate_study_registry(...)` for registry shape and path checks;
- `diagnose_study_corpus(...)` for bundle integrity plus committed registry
  and index comparison;
- `render_study_index_markdown(...)` for the human-facing index.

The command line interface supports:

```bash
python -m abm_auto.study_corpus build docs/studies \
  --repo . \
  --registry docs/studies/REGISTRY.json \
  --index docs/studies/INDEX.md

python -m abm_auto.study_corpus doctor docs/studies \
  --repo . \
  --registry docs/studies/REGISTRY.json \
  --index docs/studies/INDEX.md
```

## Current Corpus Snapshot

At introduction, after merging the concurrent Axtell reproduction commit:

- complete bundles: 79;
- pending prediction locks: 1 (`bouchaud-mezard`);
- verdict clauses: 240;
- failed verdict clauses: 36.

Failed verdict clauses are scientific outcomes recorded by the bundle, not
doctor failures. Doctor failure is reserved for registry shape errors, missing
paths, stale document fingerprints, committed registry drift, or committed
index drift.

## Packaging Fix Found By The Doctor

The first doctor run found one stale package fingerprint:
`docs/studies/coord-response/verdict-bundle.json` still pointed at the original
`FINDINGS.md` hash from the bundle-creation commit, while a later documentation
commit updated the findings text. Phase 1 updates only that fingerprint; it does
not change the findings text, model output, or verdicts.

## Non-Goals

- no model reruns;
- no new reproduction target;
- no changes to Claude-owned current reproduction WIP;
- no base-engine changes;
- no truth ranking across studies;
- no replacement for per-study locked predictions and findings.
