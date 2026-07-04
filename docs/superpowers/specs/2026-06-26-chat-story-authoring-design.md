# Design: chat agent story-authoring (planning-mode) flow

- **Date:** 2026-06-26
- **Status:** Approved (brainstorming) — ready for implementation plan
- **Area:** `abm_auto/chat.py` (extends the `abm-auto chat` agent loop)

> **Amendment (2026-06-27, port to public v3):** this design originally included a
> `gis` `draft_story` target and a `gis_capabilities` tool. The public `v3-substantial`
> has no `gis` CLI command, so when the chat agent was landed on current main those GIS
> paths were stripped — `draft_story` is `run`-target only, and there is no GIS tool.
> GIS references below are historical; the shipped code is GIS-free.

## Problem

The `abm-auto chat` agent can drive existing studies (list examples, run a known
`story.md`, inspect workspaces), but it does **not** help a user turn a *fuzzy ABM
idea* into a runnable `story.md`. The only existing disambiguation mechanism,
`--intent idea`, is non-interactive (it prints clarifying questions and halts).
There is no interactive "help me organize my natural language into a runnable
study" flow — which is the gap this design fills.

## Scope (light) and non-goals

**In scope:** an interactive sub-flow inside the chat agent that gathers just
enough from the user to produce a *runnable* `story.md`, lets the user review it
as a plan, and — only on approval — proposes the run.

**Non-goals (deliberately handed off / not rebuilt):**
- Producing a full ODD-structured document. The downstream `DesignAgent`
  (non-GIS, via `abm-auto run`) and the GIS extractor (`abm-auto gis extract`,
  invoked by `gis run`) already turn a `story.md` into structured artifacts. The
  authoring flow produces a *story*, not the structure.
- A separate authoring loop / mode, a slot state-machine, or a story template
  engine. None are needed (see Architecture rationale).
- Auto-running anything. The story is a reviewable plan; nothing executes without
  explicit user approval (see Planning-mode handoff).

## Design

### Two new tools (added to the existing agent loop; no new loop)

`draft_story(content, intent, target="run", observed_path=None, path=None) -> str`
— **write-only**. It never executes a study.
- Validates `intent ∈ {reproduce, originate, cross_domain, idea}` and
  `target ∈ {run, gis}`; returns an error string (fed back to the agent) on a bad value.
- Writes `content` (the full story.md text the agent composed) to `path`, defaulting
  to `stories/<slug>.md` where `<slug>` derives from a short title/timestamp; creates
  `stories/` if absent.
- If `observed_path` is given but the file does not exist, includes a warning in the
  return value but still writes.
- Returns the written path **and** the suggested command:
  - `target="run"` → `run <path> --intent <intent> [--observed <observed_path>]`
  - `target="gis"` → `gis run <path>`

`read_story(path) -> str` — **read-only**. Returns the current `story.md` content so
the agent can show it for review or re-compose during iteration.

### Agent behavior (system-prompt guidance, adaptive — not a state machine)

- **Trigger:** the user describes a modelling idea and does not point at an existing
  `story.md` / example.
- **GIS branch (infer, ask once if ambiguous):** infer whether the model is
  geographic/spatial from the idea ("flood evacuation on roads" → GIS; "opinion
  dynamics on an abstract network" → not GIS). If ambiguous, ask one question:
  "does this involve real geographic space (roads / raster / parcels)?" Set
  `target` accordingly.
- **Gather (soft checklist, one slot per turn, skip what is already clear):**
  - non-GIS: phenomenon → who the agents are + their states/behaviour → what to
    measure / the research question → reproduce (name the paper/model) vs originate
    → any `observed.csv`.
  - GIS: phenomenon → spatial structure (road network / raster grid / polygons /
    points) → spatial mechanism (flood evacuation / congestion routing /
    contagion-on-raster / …) → what to measure → data layers (raster / shapefile).
- **Compose:** when enough is gathered, the agent writes the full `story.md` text
  itself and calls `draft_story(content, intent, target)`.

### Planning-mode handoff (the core interaction)

```
gather → compose → draft_story (writes file) → ★ present the story.md AS A PLAN ★ → user reviews:
                                                     ├─ edit       → read_story + re-compose → draft_story (overwrite) → present again
                                                     ├─ approve+run → only now propose run / gis-run (via the abm_auto tool → confirm gate)
                                                     └─ save-only   → keep the story.md, do not run
```

Auto-push is **structurally impossible**, not merely discouraged:
1. `draft_story` is write-only — it cannot execute a study.
2. The only path that runs anything is the existing `abm_auto` tool, which is
   guarded by the confirm gate (y/N).
So between "story drafted" and "study runs" there are always two steps: the user
sees the story (the plan) and the user confirms the run.

The system prompt makes the review step mandatory: after `draft_story`, the agent
MUST display the full story.md and ask the user to review (edit / approve+run /
save-only) — it must not skip straight to proposing a run. The confirm gate is the
hard backstop if the LLM ever ignores this.

## Architecture rationale (mattpocock / ponytail)

- **Deep, thin tool.** `draft_story` has a small interface (content, intent,
  target, optional data/path) yet concentrates "where/how a story.md is written and
  which run command it maps to". The intelligence — gathering and composing — stays
  in the agent, reusing its existing conversational ability. **Deletion test:**
  remove `draft_story` and that write-location + command-mapping logic smears back
  into the prompt and call sites.
- **No rebuild.** No new loop, no slot state-machine, no story-template engine, no
  duplication of `DesignAgent` (light scope). GIS reuses the downstream
  `gis extract`. Net addition: 2 tools + 1 prompt section + a `target` field.

## Error handling

- Invalid `intent` / `target` → `draft_story` returns a correction string (the agent
  retries), never raises into the REPL.
- `observed_path` given but missing → warn in the return value, still write.
- Unknown `abm-auto` subcommand on the eventual run → already guarded by the existing
  `_KNOWN_SUBCOMMANDS` check + confirm gate.

## Testing (mock LLM client, no live LLM, no real study run)

- `draft_story` writes the file and returns the correct suggested command for both
  `target="run"` and `target="gis"`.
- `draft_story` rejects an invalid `intent` (and `target`) before writing.
- `draft_story` warns when `observed_path` is missing but still writes.
- `read_story` returns the written content.
- `run_turn` with a scripted client drives gather → `draft_story` → DONE (presents
  the plan), asserting no run is proposed without a subsequent explicit step.

## Where it lives

`abm_auto/chat.py` (the tools + the prompt section), on the `feat/chat-repl` branch
of the public repo, alongside the existing chat agent. Tests in `tests/test_chat.py`.
