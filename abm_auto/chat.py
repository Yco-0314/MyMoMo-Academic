"""``abm-auto chat`` — a conversational agent REPL that drives mymomo.

You state a research goal in natural language; an LLM agent plans and calls TOOLS
one at a time — inspecting examples and finished workspaces, and (on your confirm)
running any ``abm-auto`` command — reading each result before deciding the next
step, until it answers you. Read-only tools run freely; anything that launches a
study or mutates state asks you to confirm first.

The loop is structured so its planning/dispatch logic (`step`, `dispatch`,
`run_turn`) is unit-testable with a fake client and a fake confirm callback; the
REPL wrapper is thin I/O around it.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()

MAX_STEPS = 6  # tool calls per user turn before the agent must answer

_SYSTEM = """You are MyMoMo's research assistant — a friendly, capable guide for building and running
agent-based-modelling (ABM) studies with the abm-auto CLI. Talk like a knowledgeable colleague:
reply in natural language, briefly say what you're doing and why, ask follow-ups conversationally,
keep it concrete, and always match the user's language. You can act by calling TOOLS (below),
reading each result before continuing — but you are a collaborator, not a form.

TOOLS:
- list_examples()           → runnable example scenarios (each dir has a story.md you can `run`
                              DIRECTLY). Listing these is usually enough to answer "what can I run";
                              do NOT call describe_workspace on an examples/ directory.
- describe_workspace(path)  → summary of a FINISHED run's OUTPUT directory (created by `abm-auto run`,
                              e.g. a workspace/<timestamp> dir with REPORT.md / results/) — NOT an example.
- read_story(path)          → read back a story.md you drafted (to show or revise it)
- draft_story(content, intent, observed_path?, path?)
                            → WRITE a story.md you composed. intent ∈ {reproduce, originate,
                              cross_domain, idea}. Returns the path + suggested command. It does
                              NOT run anything.
- abm_auto(args)            → run `abm-auto <args>`, e.g.
                              {"args": "run examples/x/story.md --intent reproduce -n 2"},
                              {"args": "optimize <workspace> -n 2"}, {"args": "trust <workspace>"}.
                              Valid subcommands ONLY: run, experiment, optimize, sensitivity,
                              trajectories, memory, trust, review, ingest-netlogo, ingest-comses,
                              batch, quickstart. There is NO 'list' command — use the list_examples
                              tool to show examples. This EXECUTES (the user confirms first); it can
                              be long-running and may cost LLM tokens.
                              You can run `trust <workspace>` to report how trustworthy a finished
                              run is (CLEAN / CAVEATED / FAILED).
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

AUTHORING (turning a fuzzy idea into a runnable study):
When the user describes a modelling idea with no existing story.md, help them author one:
1. Gather, ONE question per turn, skipping anything already clear: the phenomenon; the agents
   (who acts + their states/behaviour); what to measure / the research question; reproduce
   (name a paper/model) vs originate; any observed.csv.
2. When you have enough, COMPOSE the full story.md text yourself and call draft_story.
3. PLAN REVIEW (required): after draft_story, SHOW the full story.md and ask the user to review
   it as a plan — to (a) edit it, (b) approve & run, or (c) just save it. Do NOT skip straight
   to running. On edit → revise and draft_story again. On approve → only then propose the
   abm_auto run command (which will itself ask to confirm). On save-only → stop.

For a multi-step study, prefer propose_plan over firing one command at a time:
lay out the whole sequence so the user approves it once, then let cheap steps run
and reconfirm the expensive ones. Use the single abm_auto tool for genuine one-offs.

HOW TO REPLY: write your natural-language message to the user. If you need a tool, put the call on
its OWN FINAL LINE, exactly:
  TOOL: <name> <json-args-object>
At most one TOOL line per reply. If you don't need a tool, just reply normally with NO TOOL line —
that ends your turn and is your answer to the user. After a tool runs you'll see its result and can
keep going. Don't over-call tools (after list_examples you can usually just answer); if a required
path is unknown, ask the user for it instead of guessing."""


@dataclass
class Turn:
    role: str  # "user" | "assistant"
    content: str


# ── tools ─────────────────────────────────────────────────────────────────────
def _tool_list_examples(_args: dict) -> str:
    root = Path("examples")
    if not root.is_dir():
        return "no examples/ directory in the current working directory"
    stories = sorted(str(p.parent) for p in root.glob("*/story.md"))
    return "examples with a story.md:\n" + ("\n".join(stories) if stories else "(none found)")


def _tool_describe_workspace(args: dict) -> str:
    raw = str(args.get("path", ""))
    path = Path(raw)
    if "examples" in path.parts:
        return (
            f"{raw!r} is an example scenario (an input story.md), not a finished run's output "
            f"directory. To RUN it, use the abm_auto tool with args 'run {raw}/story.md'. "
            "To list what's runnable, the list_examples result already has them — answer directly."
        )
    if not path.is_dir():
        return f"not a directory: {raw}"
    lines = [f"workspace: {path}"]
    for name in ("REPORT.md", "DESIGN.md"):
        lines.append(f"- {name}: {'present' if (path / name).exists() else 'absent'}")
    results = path / "results"
    runs = sorted(results.glob("run_*")) if results.is_dir() else []
    lines.append(f"- result runs: {len(runs)}")
    return "\n".join(lines)


def _tool_read_story(args: dict) -> str:
    path = Path(str(args.get("path", "")))
    if not path.is_file():
        return f"story not found: {path}"
    return path.read_text(encoding="utf-8")


_VALID_INTENT = {"reproduce", "originate", "cross_domain", "idea"}
_VALID_TARGET = {"run"}


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
        return f"invalid target {target!r}; valid: run"

    path = args.get("path")
    story_path = Path(str(path)) if path else Path("stories") / f"{_slug(content)}.md"
    story_path.parent.mkdir(parents=True, exist_ok=True)
    story_path.write_text(content, encoding="utf-8")

    cmd = f"run {story_path} --intent {intent}"
    if observed:
        cmd += f" --observed {observed}"
    warn = ""
    if observed and not Path(str(observed)).exists():
        warn = f"\nwarning: observed file not found: {observed}"
    return f"wrote {story_path}{warn}\nsuggested command: abm-auto {cmd}"


# abm-auto subcommands the agent may invoke (mirrors cli.py; excludes 'chat' to
# avoid recursion). Guards against the agent proposing a non-existent command.
_KNOWN_SUBCOMMANDS = {
    "run", "experiment", "optimize", "sensitivity", "trajectories", "memory",
    "trust", "review", "ingest-netlogo", "ingest-comses", "batch", "quickstart",
}

# Subcommands that cost real LLM tokens / compute — they reconfirm per step even
# inside an approved plan.
_EXPENSIVE = {"run", "optimize", "sensitivity", "batch"}


def _run_command(cmd: str) -> tuple[int, str]:
    """Run ``abm-auto <cmd>`` in a subprocess; return (returncode, output_tail).

    Forces a wide ``COLUMNS`` so the child's Rich console (which falls back to an
    80-col width when its stdout is a captured pipe) does not hard-wrap long lines —
    otherwise the ``Output directory: <path>`` line we parse for auto-trust gets
    split mid-path."""
    env = {**os.environ, "COLUMNS": "1000"}
    proc = subprocess.run(
        [sys.executable, "-m", "abm_auto.cli", *shlex.split(cmd)],
        capture_output=True, text=True, env=env,
    )
    tail = (proc.stdout or proc.stderr or "")[-1500:]
    return proc.returncode, tail


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
        # First positional argument — but skip option VALUES: a bare token right
        # after a value-taking flag (e.g. `-n 2`, `--method sobol`) is that flag's
        # value, not the workspace. `--flag=value` is self-contained.
        prev_consumes_value = False
        for tok in shlex.split(cmd)[1:]:
            if tok.startswith("-"):
                prev_consumes_value = "=" not in tok
                continue
            if prev_consumes_value:
                prev_consumes_value = False
                continue
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
                # Only auto-trust a path that actually resolves to a directory — a
                # mis-parsed/truncated path must NOT yield a verdict for the wrong
                # workspace. shlex.quote keeps a path with spaces a single argument.
                if ws and Path(ws).is_dir():
                    _, tout = run_command(f"trust {shlex.quote(ws)}")
                    verdict = next(
                        (ln.strip() for ln in tout.splitlines() if "Trust" in ln or "Cleanliness" in ln),
                        (tout.strip().splitlines()[0] if tout.strip() else "(no trust output)"),
                    )
                    line += f"\n   trust({ws}): {verdict}"
                else:
                    line += "\n   trust skipped (workspace not resolved to a directory)"
            results.append(line)
    except KeyboardInterrupt:
        results.append("STOPPED by user (Ctrl-C). Remaining steps not run.")
    return "\n".join(results)


def _tool_abm_auto(args: dict, confirm: Callable[[str], bool]) -> str:
    cmd = str(args.get("args", "")).strip()
    if not cmd:
        return "no command given"
    sub = cmd.split(maxsplit=1)[0]
    if sub not in _KNOWN_SUBCOMMANDS:
        return (
            f"'{sub}' is not an abm-auto command. Valid: {', '.join(sorted(_KNOWN_SUBCOMMANDS))}. "
            "(To show example scenarios, use the list_examples tool — not a command.)"
        )
    if not confirm(cmd):
        return "user declined to run this command"
    console.print(f"[dim]$ abm-auto {cmd}[/dim]")
    rc, tail = _run_command(cmd)
    return f"exit {rc}\n{tail}"


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


_READONLY_TOOLS: dict[str, Callable[[dict], str]] = {
    "list_examples": _tool_list_examples,
    "describe_workspace": _tool_describe_workspace,
    "read_story": _tool_read_story,
}


def dispatch(call: str, confirm: Callable[[str], bool]) -> str:
    """Execute a ``"<name> <json-args>"`` tool call; return its result text."""
    name, _, rest = call.strip().partition(" ")
    try:
        args = json.loads(rest) if rest.strip() else {}
        if not isinstance(args, dict):
            args = {"args": args}
    except json.JSONDecodeError:
        args = {"args": rest.strip().strip('"')}
    if name in _READONLY_TOOLS:
        return _READONLY_TOOLS[name](args)
    if name == "abm_auto":
        return _tool_abm_auto(args, confirm)
    if name == "propose_plan":
        return _tool_propose_plan(args, confirm)
    if name == "draft_story":
        return _tool_draft_story(args)
    return f"unknown tool: {name!r}"


def step(client, model: str, history: list[Turn], scratch: str) -> tuple[str, str | None]:
    """One agent step. Returns ``(prose, tool_call)`` where ``tool_call`` is the
    ``"<name> <json>"`` taken from a trailing ``TOOL:`` line, or ``None`` for a
    plain reply (which is the agent's answer to the user and ends the turn)."""
    convo = "\n".join(f"{t.role}: {t.content}" for t in history[-8:])
    user = convo + (f"\n\n(working notes from this turn:{scratch})" if scratch else "")
    raw = client.create(model=model, max_tokens=800, system=_SYSTEM, user=user).strip()
    lines = raw.splitlines()
    idx = next((i for i, ln in enumerate(lines) if ln.strip().startswith("TOOL:")), None)
    if idx is None:
        return raw, None
    prose = "\n".join(lines[:idx]).strip()
    tool_call = lines[idx].strip()[len("TOOL:"):].strip()
    return prose, tool_call


def _final_answer(client, model: str, history: list[Turn], scratch: str) -> str:
    """Force a direct answer from the gathered results when the step budget runs out."""
    convo = "\n".join(f"{t.role}: {t.content}" for t in history[-8:])
    raw = client.create(
        model=model, max_tokens=500,
        system="Answer the user's last request directly and concisely from the TOOL RESULTS. "
               "Do NOT request tools; just answer.",
        user=convo + "\n\nTOOL RESULTS:" + scratch + "\n\nAnswer now.",
    ).strip()
    return raw or "(couldn't complete the request — try narrowing it)"


def run_turn(client, model: str, history: list[Turn], user_msg: str,
             confirm: Callable[[str], bool]) -> str:
    """Drive one user message through the agent loop; return the final answer."""
    history.append(Turn("user", user_msg))
    scratch = ""
    seen: set[str] = set()
    for _ in range(MAX_STEPS):
        prose, tool_call = step(client, model, history, scratch)
        if prose:
            console.print(prose)
            history.append(Turn("assistant", prose))
        if tool_call is None:
            return prose
        if tool_call in seen:
            result = ("(you already ran this exact call — use the earlier result, or just "
                      "reply to the user without a TOOL line)")
        else:
            seen.add(tool_call)
            result = dispatch(tool_call, confirm)
        head = result.splitlines()[0][:80] if result else ""
        console.print(f"[dim]  · {tool_call.split(' ', 1)[0]} → {head}[/dim]")
        scratch += f"\nyou ran {tool_call} → {result}\n"
    # Step budget exhausted — force a useful answer instead of looping.
    answer = _final_answer(client, model, history, scratch)
    console.print(answer)
    history.append(Turn("assistant", answer))
    return answer


def repl(client, model: str) -> None:
    """Interactive loop: read a goal → agent plans/acts (confirm-gated) → answer."""
    console.print(
        "[bold cyan]abm-auto chat[/bold cyan] — tell me your research goal; I'll inspect, "
        "plan, and (on your confirm) run abm-auto. 'exit' or Ctrl-D to quit."
    )
    history: list[Turn] = []

    def _confirm(cmd: str) -> bool:
        console.print(f"[yellow]about to run:[/yellow] [bold]abm-auto {cmd}[/bold]")
        return Confirm.ask("run it?", default=False)

    while True:
        try:
            msg = Prompt.ask("[bold]you[/bold]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/dim]")
            return
        if msg.strip().lower() in {"exit", "quit", ":q"}:
            return
        if not msg.strip():
            continue
        run_turn(client, model, history, msg, _confirm)
