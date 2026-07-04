# AGENTS.md — MyMoMo Academic Public Branch

This file is the public repository source of truth for agent-assisted work.

## Project Boundary

MyMoMo Academic is an open agent-based modeling toolkit and reproduction
workbench. Public release branches are curated projections of the development
repository. Do not assume that every private development branch, private dataset,
or experimental backend is part of this public branch.

## Public Handoff Rule

Use `docs/agent-handoff-protocol.md` and `docs/agent-handoff-template.md` when a
task is paused, handed to another contributor, or resumed after context loss.
Handoff notes are evidence records: include branch, commit, changed files,
commands actually run, verification status, remaining task, next command, and
risks or assumptions.

Do not record private chain-of-thought. Record concise reasoning summaries,
decisions, command outputs, file paths, commits, and remaining work.

## Release Hygiene

Before publishing a release branch, run the relevant tests and scan for private
datasets, local absolute paths, credentials, and backend-only artifacts.
