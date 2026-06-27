"""Tests for the `abm-auto chat` agent loop (abm_auto.chat).

The planning/dispatch logic is driven by a fake LLM client and a fake confirm
callback, so the agent loop is verified without any live LLM or real subprocess.
"""
from __future__ import annotations

from abm_auto import chat
from abm_auto.chat import Turn


class FakeClient:
    """Returns scripted replies in order; records the prompts it was given."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def create(self, model, max_tokens, system, user):
        self.prompts.append(user)
        return self.replies.pop(0)


def test_step_tool_only():
    prose, tool_call = chat.step(FakeClient(["TOOL: list_examples {}"]), "m", [Turn("user", "x")], "")
    assert tool_call == "list_examples {}"
    assert prose == ""


def test_step_prose_then_tool():
    # The agent talks first, then calls a tool on the final line.
    prose, tool_call = chat.step(
        FakeClient(["Sure — let me see what's available.\nTOOL: list_examples {}"]), "m", [], ""
    )
    assert prose == "Sure — let me see what's available."
    assert tool_call == "list_examples {}"


def test_step_plain_reply_is_the_answer():
    prose, tool_call = chat.step(FakeClient(["Here's what I think, in plain words."]), "m", [], "")
    assert tool_call is None
    assert prose == "Here's what I think, in plain words."


def test_dispatch_unknown_tool():
    assert "unknown tool" in chat.dispatch("nope {}", confirm=lambda c: True)


def test_abm_auto_tool_respects_decline():
    # confirm=False → the command is NOT run; nothing executes.
    out = chat.dispatch('abm_auto {"args": "run examples/x/story.md"}', confirm=lambda c: False)
    assert "declined" in out


def test_run_turn_tool_then_answer():
    client = FakeClient(["Let me look.\nTOOL: list_examples {}", "Here are the examples I found."])
    history: list[Turn] = []
    answer = chat.run_turn(client, "m", history, "what examples are there?", confirm=lambda c: True)
    assert answer == "Here are the examples I found."
    assert history[0].role == "user"
    assert history[-1].content == "Here are the examples I found."


def test_run_turn_forces_answer_on_step_limit():
    # Never emits DONE: MAX_STEPS tool steps, then a forced final-answer call.
    client = FakeClient(["TOOL: list_examples {}"] * chat.MAX_STEPS + ["best-effort answer"])
    answer = chat.run_turn(client, "m", [], "loop forever", confirm=lambda c: True)
    assert answer == "best-effort answer"


def test_describe_workspace_refuses_example_dir():
    out = chat.dispatch('describe_workspace {"path": "examples/sir_epidemic"}', confirm=lambda c: True)
    assert "example scenario" in out


def test_abm_auto_tool_rejects_unknown_subcommand_before_confirm():
    called = []
    out = chat.dispatch('abm_auto {"args": "list"}', confirm=lambda c: called.append(c) or True)
    assert "not an abm-auto command" in out
    assert not called  # guard rejects bogus subcommands before asking to confirm


def test_abm_auto_tool_rejects_spatial_subcommand():
    # Public v3 has no spatial command — the guard must reject it before confirming.
    called = []
    out = chat.dispatch('abm_auto {"args": "spatial run spec.json"}',
                        confirm=lambda c: called.append(c) or True)
    assert "not an abm-auto command" in out
    assert not called


def test_known_subcommands_allowlist():
    # The allowlist mirrors the current public CLI: trust/experiment/quickstart
    # are valid; the spatial subcommand is absent from public v3.
    assert "spatial" not in chat._KNOWN_SUBCOMMANDS
    assert {"trust", "experiment", "quickstart"} <= chat._KNOWN_SUBCOMMANDS
    assert "chat" not in chat._KNOWN_SUBCOMMANDS  # excludes itself to avoid recursion


def test_read_story_returns_content(tmp_path):
    story = tmp_path / "s.md"
    story.write_text("# Rumor spread\nagents gossip", encoding="utf-8")
    out = chat.dispatch(f'read_story {{"path": "{story}"}}', confirm=lambda c: True)
    assert "Rumor spread" in out


def test_read_story_missing_path(tmp_path):
    out = chat.dispatch(f'read_story {{"path": "{tmp_path / "nope.md"}"}}', confirm=lambda c: True)
    assert "not found" in out


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


def test_draft_story_rejects_non_run_target(tmp_path):
    # Public v3 accepts only the "run" target — any other target is rejected and
    # nothing is written (the spatial target was dropped for public v3).
    p = tmp_path / "s.md"
    call = (
        'draft_story {"content": "# Flood evac\\nagents flee on roads", '
        f'"intent": "originate", "target": "spatial", "path": "{p}"}}'
    )
    out = chat.dispatch(call, confirm=lambda c: True)
    assert "invalid target" in out
    assert not p.exists()  # nothing written on a bad target


def test_draft_story_warns_on_missing_observed(tmp_path):
    p = tmp_path / "s.md"
    call = (
        'draft_story {"content": "# SIR\\nx", "intent": "reproduce", '
        f'"observed_path": "{tmp_path / "nope.csv"}", "path": "{p}"}}'
    )
    out = chat.dispatch(call, confirm=lambda c: True)
    assert "observed file not found" in out
    assert p.exists()  # still writes despite the warning


def test_authoring_turn_does_not_auto_run(tmp_path, monkeypatch):
    # The agent drafts a story then presents it; it must NOT propose a run in the
    # same turn, so the confirm gate is never reached.
    monkeypatch.chdir(tmp_path)
    confirmed = []
    client = FakeClient([
        'Let me draft that for you.\nTOOL: draft_story {"content": "# Rumor\\nbody", "intent": "originate"}',
        "Here's the story I drafted — want to edit it, run it, or just save it?",
    ])
    answer = chat.run_turn(client, "m", [], "model how rumors spread",
                           confirm=lambda c: confirmed.append(c) or True)
    assert "save" in answer.lower()  # it presented the plan for review, did not auto-run
    assert confirmed == []  # nothing was sent to the confirm gate → nothing ran
    assert list((tmp_path / "stories").glob("*.md"))  # but the story was drafted


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
