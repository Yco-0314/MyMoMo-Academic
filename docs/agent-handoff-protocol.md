# Agent Handoff Protocol

## Purpose

This protocol keeps long-running agent or operator work reproducible across
limit stops, context compactions, branch handoffs, and reviewer switches where
the next contributor must continue without guessing.

The protocol is evidence-based. Record what changed, what was run, what passed,
what failed, and exactly where to resume. Do not rely on memory-only context.

## Source-Of-Truth Hierarchy

1. `AGENTS.md` is the durable project source of truth for repository rules.
2. Tool-specific entrypoints, when present, must stay thin and point back to
   `AGENTS.md` and this protocol.
3. `docs/agent-handoff-protocol.md` defines cross-agent handoff behavior.
4. `docs/agent-handoff-template.md` is the copyable status note.
5. Conversation history is useful context, but it is not durable project state.

## When To Write A Handoff Note

Write a handoff note before any of these events:

- stopping because of model, tool, or time limits
- switching between implementation agents, reviewers, or operators
- pausing with uncommitted work
- finishing a branch that another agent may verify or merge
- resuming after context compaction when the next action is not obvious

If the working tree is clean and the task is fully merged, a short final status
message can serve as the handoff note. If work remains, use the template.

## Required Handoff Fields

Every handoff note must include these fields:

- Branch
- Current commit
- Working tree
- Changed files
- Commits created
- Commands actually run
- Verification status
- Forbidden base-engine diff
- Remaining task
- Next command
- Blockers or assumptions

Use exact command names and observed results. For tests, record the real pass,
fail, skip, or warning counts. For commands that were not run, say `not run` and
why.

## Safe Resume Procedure

The receiving agent should do this before editing:

1. Read `AGENTS.md`.
2. Read this protocol.
3. Read the latest handoff note or final status from the previous agent.
4. Run `git status --short --branch`.
5. Inspect recent commits with `git log --oneline -8`.
6. Inspect uncommitted changes before modifying files.
7. Verify the forbidden base-engine paths are untouched when the task touches
   the repo.

If the handoff says tests passed but the result is stale or ambiguous, rerun the
smallest relevant verification before relying on it.

Before relying on a completed handoff note, run the structural handoff gate:

```bash
.venv/bin/python -m abm_auto.agent_handoff gate <handoff-note.md>
```

This gate checks that required sections and fields are present and populated. It
does not verify that the recorded command results are true.

## Verification Expectations

For documentation-only handoff work, run:

```bash
git diff --check
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
```

For GIS runtime or codegen work, also run the targeted GIS tests, full GIS suite,
and base suite described in `AGENTS.md`.

Never claim a command passed without reading its real output.

## Evidence Foundry Challenge Handoff

When a contributor needs to hand an evidence-reading task to another contributor
without re-running or re-implementing the underlying model, use a MyMoMo Evidence
Foundry challenge pack:

1. The producer records a portable `challenge-pack.json` with repo-relative
   artifact paths and strong hashes.
2. The answering agent writes an `answer-*.json` manifest with claim verdicts and
   citations to challenge artifact keys.
3. The verifying agent runs:

```bash
.venv/bin/python -m abm_auto.repro_challenge validate <challenge-pack.json> --repo .
.venv/bin/python -m abm_auto.repro_challenge grade <challenge-pack.json> <answer.json> --repo .
.venv/bin/python -m abm_auto.repro_challenge gate <challenge-pack.json> <answer.json> --repo .
```

This checks answer/evidence alignment. It is not a reproduction rerun, not a
scientific truth certificate, and not permission to bypass the original
reproduction owner.

Dogfood example:

```bash
.venv/bin/python -m abm_auto.repro_challenge gate \
  docs/reproduce/autodata-challenges/mir-v0-half-a/challenge-pack.json \
  docs/reproduce/autodata-challenges/mir-v0-half-a/answer-codex.json \
  --repo .
```

## Forbidden Base-Engine Paths

GIS work must remain additive. Do not modify these directories unless the user
explicitly changes the project invariant:

- `abm_auto/runtime/`
- `abm_auto/codegen/`
- `abm_auto/calibration/`
- `abm_auto/agents/`
- `abm_auto/pipeline/`

The standard check is:

```bash
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

Expected output is empty.

## What Not To Record

Do not store long task transcripts in `AGENTS.md`.

Do not require or record private chain-of-thought. Agents should record concise
reasoning summaries, decisions, command outputs, file paths, commits, and
remaining work.

Do not hide uncertainty. If a check was skipped, failed, or only partially run,
record that state directly.

## Merge Handoff

When a branch is ready to merge:

1. Confirm the working tree is clean.
2. Confirm forbidden base-engine diff is empty.
3. Confirm required verification commands were run and record their results.
4. Fast-forward merge to `main` if the user requested landing.
5. Delete the merged local feature branch when it is no longer needed.
6. Report the final `main` commit and the verification results.
