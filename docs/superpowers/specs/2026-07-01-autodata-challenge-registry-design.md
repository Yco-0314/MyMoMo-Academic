# AutoData Challenge Registry Design

## Summary

The challenge registry is a small curriculum table for AutoData-inspired
evidence-answering packs. It lets Codex and Claude discover which challenge packs
exist, filter them by domain/difficulty/tag, and verify each registered pack
without re-running the underlying reproduction or model.

## Scope

In scope:

- Register committed challenge packs with repo-relative paths.
- Validate registry schema, unique ids, difficulty labels, tags, pack paths, and
  optional answer manifests.
- Recursively validate each registered challenge pack.
- Optionally grade registered answers.
- Provide CLI commands for registry validation and listing.

Out of scope:

- No generation of new reproductions.
- No hidden benchmark service.
- No LLM calls.
- No edits to base-engine directories.

## Schema

Registry schema: `abm-auto/repro-challenge-registry/v1`.

Each entry includes:

- `id`: must match the challenge pack's `challenge_id`.
- `pack`: repo-relative `challenge-pack.json`.
- `answer`: optional repo-relative answer manifest.
- `domain`: broad grouping, for example `architecture`.
- `difficulty`: one of `intro`, `intermediate`, `advanced`, `regression`.
- `tags`: searchable string labels.

## CLI

- `python -m abm_auto.repro_challenge registry-validate <registry> --repo .`
- `python -m abm_auto.repro_challenge registry-validate <registry> --repo . --grade-answers`
- `python -m abm_auto.repro_challenge registry-list <registry> --domain architecture --tag mir`

The registry is a discovery and quality-control layer. It is not a scientific
truth certificate and does not authorize Codex to take over Claude's model
reproduction work.
