# Chat Story-Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an interactive, planning-mode story-authoring sub-flow to the `abm-auto chat` agent: it helps a user turn a fuzzy ABM idea into a runnable `story.md`, then hands it off for review before anything runs.

> **Amendment (2026-06-27, port to public v3):** the `gis` `draft_story` target and the
> `gis_capabilities` tool described below were stripped when this agent was landed on the
> public `v3-substantial` (which has no `gis` CLI command). `draft_story` is `run`-target
> only. GIS references below are historical; the shipped code is GIS-free.

**Architecture:** Reuse the existing tool-using agent loop in `abm_auto/chat.py`. Add two thin tools — `read_story` (read-only) and `draft_story` (write-only; never executes) — plus an authoring/planning-mode section in the system prompt. The agent gathers via its existing `DONE:` questions and composes the story itself; `draft_story` only writes the file and reports the suggested command. Running stays behind the existing confirm-gated `abm_auto` tool, so auto-push is structurally impossible.

**Tech Stack:** Python, typer/rich CLI, pytest. Tests drive the loop with a `FakeClient` (scripted LLM replies) + a fake confirm callback — no live LLM, no real study runs.

**Spec:** `docs/superpowers/specs/2026-06-26-chat-story-authoring-design.md`

**Branch:** `feat/chat-repl` (public repo `mymomo-academic`). Run tests with `.venv/bin/python -m pytest tests/test_chat.py -v`.

---

## File Structure

- **Modify `abm_auto/chat.py`** — add `_tool_read_story`, `_tool_draft_story`, a `_slug` helper, the `_VALID_INTENT` / `_VALID_TARGET` sets; register `read_story` in `_READONLY_TOOLS` and `draft_story` in `dispatch`; extend `_SYSTEM` with the authoring/planning-mode guidance. (One responsibility: the chat agent + its tools — already lives here.)
- **Modify `tests/test_chat.py`** — add tests for the two tools and a planning-mode `run_turn` test.

No new files: the feature is two tools + prompt text on the existing module (ponytail — no new loop/module).

---

## Task 1: `read_story` tool

**Files:**
- Modify: `abm_auto/chat.py`
- Test: `tests/test_chat.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_chat.py`:

```python
def test_read_story_returns_content(tmp_path):
    story = tmp_path / "s.md"
    story.write_text("# Rumor spread\nagents gossip", encoding="utf-8")
    out = chat.dispatch(f'read_story {{"path": "{story}"}}', confirm=lambda c: True)
    assert "Rumor spread" in out


def test_read_story_missing_path(tmp_path):
    out = chat.dispatch(f'read_story {{"path": "{tmp_path / "nope.md"}"}}', confirm=lambda c: True)
    assert "not found" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_chat.py::test_read_story_returns_content tests/test_chat.py::test_read_story_missing_path -v`
Expected: FAIL — `dispatch` returns `"unknown tool: 'read_story'"`, so the asserts fail.

- [ ] **Step 3: Implement `_tool_read_story` and register it**

In `abm_auto/chat.py`, add the function next to the other `_tool_*` functions:

```python
def _tool_read_story(args: dict) -> str:
    path = Path(str(args.get("path", "")))
    if not path.is_file():
        return f"story not found: {path}"
    return path.read_text(encoding="utf-8")
```

Then add it to the `_READONLY_TOOLS` dict (it is genuinely read-only):

```python
_READONLY_TOOLS: dict[str, Callable[[dict], str]] = {
    "list_examples": _tool_list_examples,
    "describe_workspace": _tool_describe_workspace,
    "gis_capabilities": _tool_gis_capabilities,
    "read_story": _tool_read_story,
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_chat.py -v`
Expected: PASS (all chat tests, including the two new ones).

- [ ] **Step 5: Commit**

```bash
git add abm_auto/chat.py tests/test_chat.py
git commit -m "feat(chat): add read_story tool"
```

---

## Task 2: `draft_story` tool — write + suggested run command + validation

**Files:**
- Modify: `abm_auto/chat.py`
- Test: `tests/test_chat.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_chat.py`:

```python
def test_draft_story_writes_and_returns_run_command(tmp_path):
    p = tmp_path / "s.md"
    call = (
        'draft_story {"content": "# SIR\\npeople infect neighbours", '
        f'"intent": "reproduce", "path": "{p}"}}'
    )
    out = chat.dispatch(call, confirm=lambda c: True)
    assert p.read_text(encoding="utf-8").startswith("# SIR")
    assert f"run {p} --intent reproduce" in out


def test_draft_story_rejects_invalid_intent(tmp_path):
    p = tmp_path / "s.md"
    call = f'draft_story {{"content": "x", "intent": "nonsense", "path": "{p}"}}'
    out = chat.dispatch(call, confirm=lambda c: True)
    assert "invalid intent" in out
    assert not p.exists()  # nothing written on a bad spec


def test_draft_story_default_path_slug(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = chat.dispatch(
        'draft_story {"content": "# Rumor model\\nbody", "intent": "originate"}',
        confirm=lambda c: True,
    )
    written = list((tmp_path / "stories").glob("*.md"))
    assert len(written) == 1
    assert "rumor" in written[0].name.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_chat.py -k draft_story -v`
Expected: FAIL — `dispatch` returns `"unknown tool: 'draft_story'"`.

- [ ] **Step 3: Implement the slug helper, validation sets, and `_tool_draft_story`**

In `abm_auto/chat.py`, add `import re` to the imports (near `import json`), then add:

```python
_VALID_INTENT = {"reproduce", "originate", "cross_domain", "idea"}
_VALID_TARGET = {"run", "gis"}


def _slug(content: str) -> str:
    first = next((ln.strip().lstrip("#").strip() for ln in content.splitlines() if ln.strip()), "")
    s = re.sub(r'[\\/:*?"<>|\s]+', "-", first).strip("-")[:40]
    return s or "story"


def _tool_draft_story(args: dict) -> str:
    content = str(args.get("content", "")).strip()
    intent = str(args.get("intent", "")).strip()
    target = str(args.get("target", "run")).strip()
    observed = args.get("observed_path")
    if not content:
        return "no story content given"
    if intent not in _VALID_INTENT:
        return f"invalid intent {intent!r}; valid: {', '.join(sorted(_VALID_INTENT))}"
    if target not in _VALID_TARGET:
        return f"invalid target {target!r}; valid: run, gis"

    path = args.get("path")
    story_path = Path(str(path)) if path else Path("stories") / f"{_slug(content)}.md"
    story_path.parent.mkdir(parents=True, exist_ok=True)
    story_path.write_text(content, encoding="utf-8")

    if target == "gis":
        cmd = f"gis run {story_path}"
    else:
        cmd = f"run {story_path} --intent {intent}"
        if observed:
            cmd += f" --observed {observed}"
    warn = ""
    if observed and not Path(str(observed)).exists():
        warn = f"\nwarning: observed file not found: {observed}"
    return f"wrote {story_path}{warn}\nsuggested command: abm-auto {cmd}"
```

Then register it in `dispatch`, before the `unknown tool` fallback:

```python
    if name == "draft_story":
        return _tool_draft_story(args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_chat.py -v`
Expected: PASS (all chat tests).

- [ ] **Step 5: Commit**

```bash
git add abm_auto/chat.py tests/test_chat.py
git commit -m "feat(chat): add draft_story tool (write-only, with run-command + intent validation)"
```

---

## Task 3: `draft_story` — `gis` target and missing-observed warning

**Files:**
- Modify: (no code change — behaviour already implemented in Task 2)
- Test: `tests/test_chat.py`

These behaviours were implemented in Task 2; lock them with explicit tests.

- [ ] **Step 1: Write the tests**

Append to `tests/test_chat.py`:

```python
def test_draft_story_gis_target_suggests_gis_run(tmp_path):
    p = tmp_path / "s.md"
    call = (
        'draft_story {"content": "# Flood evac\\nagents flee on roads", '
        f'"intent": "originate", "target": "gis", "path": "{p}"}}'
    )
    out = chat.dispatch(call, confirm=lambda c: True)
    assert f"gis run {p}" in out
    assert "--intent" not in out  # gis path has no --intent flag


def test_draft_story_warns_on_missing_observed(tmp_path):
    p = tmp_path / "s.md"
    call = (
        'draft_story {"content": "# SIR\\nx", "intent": "reproduce", '
        f'"observed_path": "{tmp_path / "nope.csv"}", "path": "{p}"}}'
    )
    out = chat.dispatch(call, confirm=lambda c: True)
    assert "observed file not found" in out
    assert p.exists()  # still writes despite the warning
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_chat.py -k "gis_target or missing_observed" -v`
Expected: PASS (Task 2 already implements both paths).

- [ ] **Step 3: (no implementation needed)**

If either test fails, re-check the `target == "gis"` branch and the `warn` block in `_tool_draft_story`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_chat.py
git commit -m "test(chat): lock draft_story gis-target + missing-observed behaviour"
```

---

## Task 4: Planning-mode system prompt + the no-auto-run guarantee

**Files:**
- Modify: `abm_auto/chat.py` (the `_SYSTEM` string)
- Test: `tests/test_chat.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chat.py`:

```python
def test_authoring_turn_does_not_auto_run(tmp_path, monkeypatch):
    # The agent drafts a story then presents it; it must NOT propose a run in the
    # same turn, so the confirm gate is never reached.
    monkeypatch.chdir(tmp_path)
    confirmed = []
    client = FakeClient([
        'TOOL: draft_story {"content": "# Rumor\\nbody", "intent": "originate"}',
        "DONE: Here is the story I drafted — review it: edit, approve & run, or just save?",
    ])
    answer = chat.run_turn(client, "m", [], "model how rumors spread",
                           confirm=lambda c: confirmed.append(c) or True)
    assert "review" in answer.lower()
    assert confirmed == []  # nothing was sent to the confirm gate → nothing ran
    assert list((tmp_path / "stories").glob("*.md"))  # but the story was drafted
```

- [ ] **Step 2: Run the test to verify it passes structurally, then strengthen the prompt**

Run: `.venv/bin/python -m pytest tests/test_chat.py::test_authoring_turn_does_not_auto_run -v`
Expected: PASS already (draft_story doesn't run; the scripted client ends on DONE). This test pins the no-auto-run guarantee. Proceed to add the prompt guidance so the *real* agent behaves this way.

- [ ] **Step 3: Extend `_SYSTEM` with the new tools + authoring guidance**

In `abm_auto/chat.py`, in the `_SYSTEM` string's TOOLS list, add the two tools:

```
- read_story(path)          → read back a story.md you drafted (to show or revise it)
- draft_story(content, intent, target, observed_path?, path?)
                            → WRITE a story.md you composed. intent ∈ {reproduce, originate,
                              cross_domain, idea}; target "run" (standard) or "gis" (spatial,
                              geo-referenced). Returns the path + suggested command. It does
                              NOT run anything.
```

And add this AUTHORING block to `_SYSTEM` (after the TOOLS list, before the reply-format lines):

```
AUTHORING (turning a fuzzy idea into a runnable study):
When the user describes a modelling idea with no existing story.md, help them author one:
1. Decide if it is GEOGRAPHIC/spatial (roads, raster, flood, parcels, points/polygons) →
   target "gis"; otherwise target "run". Ask one question only if genuinely unclear.
2. Gather, ONE question per turn, skipping anything already clear: the phenomenon; the agents
   (who acts + their states/behaviour); what to measure / the research question; reproduce
   (name a paper/model) vs originate; any observed.csv. For gis: spatial structure + spatial
   mechanism + data layers instead.
3. When you have enough, COMPOSE the full story.md text yourself and call draft_story.
4. PLAN REVIEW (required): after draft_story, SHOW the full story.md and ask the user to review
   it as a plan — to (a) edit it, (b) approve & run, or (c) just save it. Do NOT skip straight
   to running. On edit → revise and draft_story again. On approve → only then propose the
   abm_auto run/gis command (which will itself ask to confirm). On save-only → stop.
```

- [ ] **Step 4: Run the full chat test file**

Run: `.venv/bin/python -m pytest tests/test_chat.py -v`
Expected: PASS (prompt text is not asserted by existing tests; all pass).

- [ ] **Step 5: Commit**

```bash
git add abm_auto/chat.py tests/test_chat.py
git commit -m "feat(chat): planning-mode story-authoring guidance in the agent prompt"
```

---

## Task 5: Manual smoke + final verification

**Files:** none (verification only)

- [ ] **Step 1: Full chat suite**

Run: `.venv/bin/python -m pytest tests/test_chat.py -v`
Expected: PASS (all tasks' tests green).

- [ ] **Step 2: Live smoke (needs an LLM key in `.env`)**

Run:
```bash
printf '帮我建一个谣言在小镇扩散的模型\n[answer the agent's questions]\nexit\n' | .venv/bin/python -m abm_auto.cli chat
```
Expected: the agent asks a couple of gather questions, calls `draft_story` (a file appears under `stories/`), then presents the story and asks you to review (edit / approve & run / save) — it does NOT auto-run.

- [ ] **Step 3: Confirm no regression in the base CLI**

Run: `.venv/bin/python -m abm_auto.cli --help`
Expected: lists `chat` among the commands; no errors.

---

## Self-Review

**Spec coverage:**
- Light scope / no DesignAgent duplication → Tasks add only authoring; no pipeline changes. ✓
- `draft_story` write-only with intent validation + run/gis command → Task 2 + Task 3. ✓
- `read_story` read-only → Task 1. ✓
- `target` field (GIS branch) → Task 2 (field) + Task 3 (gis test) + Task 4 (prompt branch). ✓
- Planning-mode handoff / no auto-push → Task 4 (prompt + no-auto-run test); structural guarantee (draft_story never runs; only `abm_auto` runs, behind confirm). ✓
- Error handling (invalid intent/target; missing observed warns) → Task 2 + Task 3. ✓
- Tests via FakeClient + fake confirm, no live LLM → all tasks. ✓

**Placeholder scan:** none — every step has real test/impl code and exact commands.

**Type consistency:** `dispatch(call, confirm)`, `_READONLY_TOOLS: dict[str, Callable[[dict], str]]`, `_tool_*(args)->str`, `_tool_abm_auto(args, confirm)` match the existing module; new `_tool_read_story(args)`, `_tool_draft_story(args)`, `_slug(content)`, `_VALID_INTENT`, `_VALID_TARGET` are defined before use. `FakeClient` and `chat.run_turn(client, model, history, msg, confirm)` match existing `tests/test_chat.py`.
