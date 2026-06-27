# Chat Orchestrator (plan-mode + stop + auto-trust) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the `abm-auto chat` agent into a bounded, plan-approved orchestrator: it proposes a multi-step plan (approved once), runs cheap/read steps automatically while reconfirming each expensive step, auto-reports trust after runs, and stops cleanly on decline/failure/Ctrl-C.

**Architecture:** All changes live in `abm_auto/chat.py`. Extract the subprocess call into a reusable `_run_command`; add a deep `execute_plan` module (injectable runner) doing hybrid-confirm + auto-trust + stop; add a `propose_plan` tool that validates + gets one plan approval then calls `execute_plan`; route it in `dispatch`; extend `_SYSTEM`. The single `confirm` callback already plumbed through `dispatch`/`run_turn`/`repl` serves both the plan-approval gate and the per-step gate.

**Tech Stack:** Python, the existing `abm_auto/chat.py` tool-loop, pytest with a FakeClient + injected fake command-runner (no live LLM, no real subprocess).

**Spec:** `docs/superpowers/specs/2026-06-27-chat-orchestrator-design.md`
**Branch:** `feat/chat-orchestrator` (off `v3-substantial`). Tests: `.venv/bin/python -m pytest tests/test_chat.py -v`.

Verified current `chat.py` facts:
- `_tool_abm_auto(args, confirm)` runs `subprocess.run([sys.executable, "-m", "abm_auto.cli", *shlex.split(cmd)], capture_output=True, text=True)` and returns `f"exit {rc}\n{tail}"` where `tail = (stdout or stderr or "")[-1500:]`.
- `_KNOWN_SUBCOMMANDS = {"run","experiment","optimize","sensitivity","trajectories","memory","trust","review","ingest-netlogo","ingest-comses","batch","quickstart"}`.
- `dispatch(call, confirm)` parses `"<name> <json>"`; routes `_READONLY_TOOLS`, `abm_auto`, `draft_story`; else `unknown tool`.
- `import json, re, shlex, subprocess, sys`; `from typing import Callable`; `console = Console()` already present.

---

## Task 1: Extract `_run_command` (DRY) + `_EXPENSIVE`

**Files:**
- Modify: `abm_auto/chat.py`
- Test: `tests/test_chat.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chat.py`:

```python
def test_run_command_shape(monkeypatch):
    import abm_auto.chat as chat

    class _Proc:
        returncode = 0
        stdout = "hello world"
        stderr = ""

    monkeypatch.setattr(chat.subprocess, "run", lambda *a, **k: _Proc())
    rc, out = chat._run_command("memory ws")
    assert rc == 0
    assert "hello world" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_chat.py::test_run_command_shape -v`
Expected: FAIL — `AttributeError: module 'abm_auto.chat' has no attribute '_run_command'`.

- [ ] **Step 3: Add `_run_command` + `_EXPENSIVE`; refactor `_tool_abm_auto` to reuse it**

In `abm_auto/chat.py`, add (near `_KNOWN_SUBCOMMANDS`):

```python
# Subcommands that cost real LLM tokens / compute — they reconfirm per step even
# inside an approved plan.
_EXPENSIVE = {"run", "optimize", "sensitivity", "batch"}


def _run_command(cmd: str) -> tuple[int, str]:
    """Run ``abm-auto <cmd>`` in a subprocess; return (returncode, output_tail)."""
    proc = subprocess.run(
        [sys.executable, "-m", "abm_auto.cli", *shlex.split(cmd)],
        capture_output=True, text=True,
    )
    tail = (proc.stdout or proc.stderr or "")[-1500:]
    return proc.returncode, tail
```

Then change `_tool_abm_auto` to reuse it (replace its inline `subprocess.run(...)` + tail block):

```python
    if not confirm(cmd):
        return "user declined to run this command"
    console.print(f"[dim]$ abm-auto {cmd}[/dim]")
    rc, tail = _run_command(cmd)
    return f"exit {rc}\n{tail}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_chat.py -v`
Expected: PASS (the new test + all existing chat tests — `_tool_abm_auto` behavior unchanged).

- [ ] **Step 5: Commit**

```bash
git add abm_auto/chat.py tests/test_chat.py
git commit -m "refactor(chat): extract _run_command + _EXPENSIVE (DRY for the orchestrator)"
```

---

## Task 2: `_workspace_for` + `execute_plan` (the orchestrator core)

**Files:**
- Modify: `abm_auto/chat.py`
- Test: `tests/test_chat.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_chat.py`:

```python
def _fake_runner(script=None):
    """A fake run_command: records calls; returns script[cmd] or (0, 'ok')."""
    calls = []

    def run(cmd):
        calls.append(cmd)
        return (script or {}).get(cmd, (0, "ok"))

    return run, calls


def test_execute_plan_runs_all_steps_in_order():
    from abm_auto.chat import execute_plan
    run, calls = _fake_runner()
    summary = execute_plan(["memory ws", "trust ws"], confirm=lambda s: True, run_command=run)
    assert calls == ["memory ws", "trust ws"]
    assert "step 1/2" in summary and "step 2/2" in summary


def test_execute_plan_confirms_only_expensive_steps():
    from abm_auto.chat import execute_plan
    confirmed = []
    run, calls = _fake_runner()
    execute_plan(
        ["trust ws", "optimize ws -n 2"],
        confirm=lambda s: confirmed.append(s) or True,
        run_command=run,
    )
    assert confirmed == ["optimize ws -n 2"]  # cheap 'trust' auto-ran; only expensive asked


def test_execute_plan_auto_trusts_after_run():
    from abm_auto.chat import execute_plan
    script = {
        "run s.md -n 2": (0, "Output directory: /tmp/ws\n"),
        "trust /tmp/ws": (0, "Trust: CAVEATED\n"),
    }
    run, calls = _fake_runner(script)
    summary = execute_plan(["run s.md -n 2"], confirm=lambda s: True, run_command=run)
    assert "trust /tmp/ws" in calls
    assert "CAVEATED" in summary


def test_execute_plan_stops_when_expensive_step_declined():
    from abm_auto.chat import execute_plan
    run, calls = _fake_runner()
    summary = execute_plan(["run s.md -n 2", "trust ws"], confirm=lambda s: False, run_command=run)
    assert calls == []  # declined before running anything
    assert "STOPPED" in summary


def test_execute_plan_stops_on_step_failure():
    from abm_auto.chat import execute_plan
    run, calls = _fake_runner({"memory ws": (1, "boom")})
    summary = execute_plan(["memory ws", "trust ws"], confirm=lambda s: True, run_command=run)
    assert calls == ["memory ws"]  # second step not reached
    assert "FAILED" in summary


def test_execute_plan_stops_on_keyboard_interrupt():
    from abm_auto.chat import execute_plan

    def run(cmd):
        raise KeyboardInterrupt

    summary = execute_plan(["memory ws"], confirm=lambda s: True, run_command=run)
    assert "STOPPED" in summary  # caught; no exception escapes


def test_execute_plan_skips_trust_when_workspace_not_found():
    from abm_auto.chat import execute_plan
    run, calls = _fake_runner({"run s.md": (0, "finished, no path printed")})
    summary = execute_plan(["run s.md"], confirm=lambda s: True, run_command=run)
    assert calls == ["run s.md"]  # no auto-trust call (workspace unknown; story arg is NOT a workspace)
    assert "skipped" in summary.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_chat.py -k execute_plan -v`
Expected: FAIL — `ImportError: cannot import name 'execute_plan'`.

- [ ] **Step 3: Implement `_workspace_for` + `execute_plan`**

Add to `abm_auto/chat.py` (after `_run_command`):

```python
def _workspace_for(sub: str, cmd: str, output: str) -> str | None:
    """Resolve the workspace a run/optimize step produced or targeted.

    ``run`` prints ``Output directory: <path>`` (or ``Results: <path>``); for
    ``optimize``/``sensitivity``/``batch`` the workspace is the first positional
    argument. A ``run`` step's positional arg is the STORY, not a workspace, so we
    never fall back to it for ``run``."""
    for marker in ("Output directory:", "Results:"):
        for line in output.splitlines():
            if marker in line:
                path = line.split(marker, 1)[1].strip()
                if path:
                    return path
    if sub in ("optimize", "sensitivity", "batch"):
        for tok in shlex.split(cmd)[1:]:
            if not tok.startswith("-"):
                return tok
    return None


def execute_plan(steps, confirm: Callable[[str], bool], run_command=_run_command) -> str:
    """Run an approved multi-step plan: hybrid confirm (expensive steps reconfirm),
    auto-trust after run/optimize, and a clean stop on decline/failure/Ctrl-C."""
    results: list[str] = []
    n = len(steps)
    try:
        for i, step in enumerate(steps, 1):
            sub = step.split(maxsplit=1)[0]
            if sub in _EXPENSIVE and not confirm(step):
                results.append(f"step {i}/{n} `{step}`: STOPPED (you declined). Remaining steps not run.")
                break
            rc, output = run_command(step)
            last = output.strip().splitlines()[-1] if output.strip() else ""
            if rc != 0:
                results.append(f"step {i}/{n} `{step}`: FAILED (exit {rc}). {last}\nRemaining steps not run.")
                break
            line = f"step {i}/{n} `{step}`: ok. {last}"
            if sub in ("run", "optimize"):
                ws = _workspace_for(sub, step, output)
                if ws:
                    _, tout = run_command(f"trust {ws}")
                    verdict = next(
                        (ln.strip() for ln in tout.splitlines() if "Trust" in ln or "Cleanliness" in ln),
                        (tout.strip().splitlines()[0] if tout.strip() else "(no trust output)"),
                    )
                    line += f"\n   trust({ws}): {verdict}"
                else:
                    line += "\n   trust skipped (workspace not found in output)"
            results.append(line)
    except KeyboardInterrupt:
        results.append("STOPPED by user (Ctrl-C). Remaining steps not run.")
    return "\n".join(results)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_chat.py -k execute_plan -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add abm_auto/chat.py tests/test_chat.py
git commit -m "feat(chat): execute_plan — hybrid-confirm orchestrator with auto-trust + stop"
```

---

## Task 3: `propose_plan` tool + dispatch routing

**Files:**
- Modify: `abm_auto/chat.py`
- Test: `tests/test_chat.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_chat.py`:

```python
def test_propose_plan_rejects_unknown_subcommand():
    from abm_auto.chat import dispatch
    result = dispatch('propose_plan {"steps": ["run s.md", "frobnicate x"]}', confirm=lambda s: True)
    assert "rejected" in result.lower()
    assert "frobnicate" in result


def test_propose_plan_declined_runs_nothing():
    from abm_auto.chat import dispatch
    result = dispatch('propose_plan {"steps": ["memory ws"]}', confirm=lambda s: False)
    assert "declined" in result.lower()


def test_propose_plan_requires_nonempty_step_list():
    from abm_auto.chat import dispatch
    result = dispatch('propose_plan {"steps": []}', confirm=lambda s: True)
    assert "steps" in result.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_chat.py -k propose_plan -v`
Expected: FAIL — `dispatch` returns `unknown tool: 'propose_plan'`.

- [ ] **Step 3: Add `_tool_propose_plan` + route it in `dispatch`**

Add to `abm_auto/chat.py` (after `execute_plan`):

```python
def _tool_propose_plan(args: dict, confirm: Callable[[str], bool]) -> str:
    """Validate a multi-step plan, get one approval, then execute it."""
    steps = args.get("steps")
    if not isinstance(steps, list) or not steps or not all(isinstance(s, str) and s.strip() for s in steps):
        return "propose_plan needs a non-empty list of abm-auto command strings in 'steps'."
    steps = [s.strip() for s in steps]
    for s in steps:
        sub = s.split(maxsplit=1)[0]
        if sub not in _KNOWN_SUBCOMMANDS:
            return (
                f"plan rejected: '{sub}' is not an abm-auto command "
                f"(valid: {', '.join(sorted(_KNOWN_SUBCOMMANDS))}). Nothing run."
            )
    rendered = "proposed plan:\n" + "\n".join(f"  {i}. abm-auto {s}" for i, s in enumerate(steps, 1))
    if not confirm(rendered):
        return "plan declined; nothing run."
    return execute_plan(steps, confirm)
```

In `dispatch`, add a route (next to the `abm_auto` / `draft_story` routes):

```python
    if name == "propose_plan":
        return _tool_propose_plan(args, confirm)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_chat.py -k propose_plan -v`
Expected: PASS (3 tests). (The reject/decline/empty paths never reach `execute_plan`, so no subprocess runs.)

- [ ] **Step 5: Commit**

```bash
git add abm_auto/chat.py tests/test_chat.py
git commit -m "feat(chat): propose_plan tool — validate + one-time plan approval, then execute"
```

---

## Task 4: System prompt — orchestration guidance

**Files:**
- Modify: `abm_auto/chat.py` (the `_SYSTEM` string)
- Test: `tests/test_chat.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chat.py`:

```python
def test_system_prompt_documents_orchestration():
    from abm_auto.chat import _SYSTEM
    assert "propose_plan" in _SYSTEM
    assert "trust" in _SYSTEM.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_chat.py -k orchestration -v`
Expected: FAIL — `_SYSTEM` does not mention `propose_plan`.

- [ ] **Step 3: Add a `propose_plan` tool line + orchestration paragraph to `_SYSTEM`**

In `abm_auto/chat.py`, in the `_SYSTEM` string's tool list, add a line alongside the other tools:

```
- propose_plan(steps)      → propose a multi-step study as an ordered list of
                              abm-auto commands, e.g.
                              {"steps": ["run examples/x/story.md --intent reproduce -n 2", "optimize <workspace> -n 2"]}.
                              The user approves the whole plan ONCE; cheap/read steps
                              (trust, memory, trajectories, review) run automatically,
                              while each expensive step (run/optimize/sensitivity/batch)
                              reconfirms before it runs. The user can stop anytime.
                              After a run/optimize, the orchestrator auto-reports the
                              trust verdict (CLEAN/CAVEATED/FAILED) — discuss open
                              issues honestly rather than declaring success.
```

And add a short orchestration note in the working-style section (wherever the prompt explains how to act):

```
For a multi-step study, prefer propose_plan over firing one command at a time:
lay out the whole sequence so the user approves it once, then let cheap steps run
and reconfirm the expensive ones. Use the single abm_auto tool for genuine one-offs.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_chat.py -k orchestration -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add abm_auto/chat.py tests/test_chat.py
git commit -m "feat(chat): system prompt — orchestration guidance (propose_plan + auto-trust)"
```

---

## Task 5: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Full chat suite**

Run: `.venv/bin/python -m pytest tests/test_chat.py -v`
Expected: all PASS (existing chat tests + the new orchestrator tests).

- [ ] **Step 2: No regression in the broader suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS / skipped only.

- [ ] **Step 3: Import + CLI smoke**

Run: `.venv/bin/python -c "import abm_auto.chat; print('ok')"` and `.venv/bin/python -m abm_auto.cli chat --help`
Expected: `ok`; chat help renders without error.

---

## Self-Review

**Spec coverage:**
- Hybrid execution (plan approved once; expensive reconfirm; cheap auto) → Task 2 (`execute_plan` + `_EXPENSIVE`) + Task 3 (one approval). ✓
- Stop-only (decline / failure / Ctrl-C; no count/token cap) → Task 2 (three stop paths). ✓
- Auto-trust after run/optimize with workspace resolution → Task 2 (`_workspace_for` + trust call). ✓
- `propose_plan` tool: validate, reject unknown subcommand, one approval → Task 3. ✓
- DRY `_run_command` reused by the single-command tool → Task 1. ✓
- System-prompt orchestration guidance → Task 4. ✓
- Tests with fake runner/confirm, no live LLM/subprocess → all tasks. ✓
- Error handling (empty/malformed steps, failure halts, ws-not-found note) → Tasks 2–3. ✓

**Placeholder scan:** none — every step has real code + exact commands.

**Type/name consistency:** `_run_command(cmd)->(int,str)`, `_EXPENSIVE`, `_workspace_for(sub,cmd,output)->str|None`, `execute_plan(steps,confirm,run_command=_run_command)->str`, `_tool_propose_plan(args,confirm)->str`, dispatch route `propose_plan`. All defined before use; `_KNOWN_SUBCOMMANDS` reused as-is.

**Note:** the approved-plan path through `dispatch` uses the real `_run_command` (real subprocess); it is intentionally exercised only via `execute_plan`'s injected fake in tests, while `dispatch` tests cover routing + reject + decline (no subprocess). This keeps the unit suite free of live runs.
