# Chat orchestrator: plan-mode + stop + auto-trust — design

**Date:** 2026-06-27
**Status:** Approved (brainstorming) — ready for implementation plan
**Area:** `abm_auto/chat.py` (extends the `abm-auto chat` agent loop) + `tests/test_chat.py`. Public repo `MyMoMo-Academic`, branch `feat/chat-orchestrator` off `v3-substantial`.

## Problem

The `abm-auto chat` agent runs one confirm-gated command at a time. A real study is multi-step (run → check trust → optimize → re-check), and today the agent fires commands one by one with no upfront plan, no automatic trustworthiness read-out, and no clean way to stop a sequence partway. Roadmap #3 (slice b): make the agent a **bounded, plan-approved orchestrator that reports trust**.

## Decisions (locked in brainstorming)

- **Execution model:** *hybrid*. The agent proposes a multi-step plan; the user approves the whole plan once; on execution, cheap/read steps auto-run, but each expensive step (`run`/`optimize`/`sensitivity`/`batch`) still asks a per-step confirm.
- **Budget/stop:** *stop only*, no count/token cap. Declining an expensive step, or Ctrl-C, cleanly aborts the rest of the plan.
- **Trust integration:** after a `run`/`optimize` step, auto-run `trust <workspace>` and fold the CLEAN/CAVEATED/FAILED verdict (+ open-issue counts) into the conversation.

## Design

All changes are in `abm_auto/chat.py`; the existing single-command `abm_auto` tool stays for one-offs.

### 1. Reusable command runner (DRY)

Extract the subprocess call from `_tool_abm_auto` into `_run_command(cmd: str) -> tuple[int, str]` (runs `[sys.executable, "-m", "abm_auto.cli", *shlex.split(cmd)]`, returns `(returncode, output_tail)`). `_tool_abm_auto` calls it after its confirm; the plan executor calls it too. `execute_plan` takes the runner as an injectable parameter (`run_command=_run_command`) so tests can substitute a fake.

### 2. `propose_plan` tool

The agent emits `TOOL: propose_plan {"steps": ["run examples/x/story.md --intent reproduce -n 2", "optimize <ws> -n 2", "trust <ws>"]}`. Routed in `dispatch` to `_tool_propose_plan(args, confirm)`:

1. Parse `steps` (list of abm-auto command strings). Empty/malformed → return a clear error, nothing runs.
2. **Validate every step's subcommand against `_KNOWN_SUBCOMMANDS` upfront**; if any is unknown, reject the whole plan (run nothing) and name the offender.
3. Render the numbered plan and ask `confirm(rendered_plan)` (one approval for the whole plan). Declined → return "plan declined; nothing run".
4. On approval, call `execute_plan(steps, confirm)` and return its summary.

The single `confirm` callback already plumbed through `dispatch`/`run_turn`/`repl` serves both the plan-approval gate and the per-step gate (it just renders different text).

### 3. `execute_plan(steps, confirm, run_command=_run_command) -> str`

The deep module. Runs the approved steps in order:

- `_EXPENSIVE = {"run", "optimize", "sensitivity", "batch"}`.
- For each step (1-indexed):
  - **Expensive gate:** if the subcommand is expensive and `confirm(step)` is False → **stop**: record "stopped at step k (declined)" and run no further steps.
  - Run via `run_command(step)` → `(rc, output)`.
  - **Failure halts the plan:** if `rc != 0`, record the failure and stop the remaining steps (don't blindly continue).
  - **Auto-trust:** if the subcommand is `run` or `optimize`, resolve the workspace (`_workspace_for(subcommand, step, output)` — from the run's `Output directory:`/`Results:` line, else the command's first path-like argument) and, if found, `run_command(f"trust {ws}")`, capturing the verdict line; if not found, note "trust skipped (workspace not found)".
  - Record a per-step result (ran/stopped/failed, output tail, trust verdict).
- Wrap the loop in `try/except KeyboardInterrupt` → clean "stopped by user at step k".
- Return a structured multi-step summary (what ran, outcomes, trust verdicts, where/why it stopped) for the agent to discuss in natural language.

### 4. System prompt

Add a `propose_plan` tool entry and a short orchestration section: for a multi-step study, propose a plan via `propose_plan` instead of firing one command; the user approves once; cheap steps auto-run while expensive ones reconfirm; the user can stop anytime; after `run`/`optimize` the orchestrator reports trust (CLEAN/CAVEATED/FAILED) — discuss open issues rather than declaring success.

## Error handling

- Empty/malformed `steps`, or any unknown subcommand → reject the whole plan, run nothing, explain why.
- A step exits non-zero → stop the remaining plan, report which step failed (with its output tail).
- Workspace not resolvable after a run/optimize → skip auto-trust for that step with a note (don't crash).
- Ctrl-C mid-plan → caught, clean "stopped" summary; the REPL stays alive.

## Testing (no live LLM, no real subprocess)

`execute_plan` is tested with a fake `run_command` (records calls, returns scripted `(rc, output)`) and a fake `confirm`:
- All-yes plan runs every step in order.
- **Hybrid:** expensive steps invoke `confirm`; cheap steps (`trust`/`memory`/`trajectories`/`review`) do not.
- **Auto-trust:** after a `run` whose output contains `Output directory: /tmp/ws`, `run_command("trust /tmp/ws")` is called and its verdict appears in the summary.
- **Stop on decline:** declining an expensive step leaves later steps un-run; summary says stopped.
- **Stop on failure:** a step returning `rc != 0` halts the remaining plan.
- **Stop on Ctrl-C:** a `run_command` that raises `KeyboardInterrupt` yields a clean stopped summary, no exception escapes.
- `_tool_propose_plan` via `dispatch`: unknown subcommand → whole plan rejected, nothing run; declined plan-approval → nothing run.
- Workspace not found → auto-trust skipped with a note.

## Non-goals

- Token/$ budgeting or a step-count cap (explicitly out — stop-only).
- Parallel step execution (steps are sequential).
- Changing the single-command `abm_auto` tool's behavior, or `run_turn`/`step`/`repl` beyond routing `propose_plan` in `dispatch`.
- GIS (public v3 has no `gis` command).

## Where it lives

- `abm_auto/chat.py` — `_run_command`, `_EXPENSIVE`, `_workspace_for`, `execute_plan`, `_tool_propose_plan`, `dispatch` routing, `_SYSTEM` additions.
- `tests/test_chat.py` — the orchestrator tests above.
- Branch `feat/chat-orchestrator` off `v3-substantial`.
