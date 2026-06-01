"""Static anti-pattern scanner for LLM-generated MyMoMo code.

Why this exists
---------------
CoderAgent's GVR loop validates code with three checks:
  - dry_run     (import the modules — catches NameError / ImportError)
  - contract    (calibration_params present in SimulatorScenarios.csv)
  - fidelity    (LLM-judge against mechanism_spec.md)

These work but have gaps. dry_run only catches names referenced at IMPORT
time — if `WattsStrogatzNetwork()` is in a method that runs at simulate()
time, the import succeeds and the failure appears mid-Phase 4. Fidelity
catches semantic deviations but is an LLM call (slow, noisy, costs $$).

This module adds a fast, cheap, deterministic PRE-execution layer: a regex
scan for the catalog of anti-patterns the LLM keeps producing. Catalog
sourced from `abm_auto/mymomo_knowledge/05-anti-patterns.md`. New entries:
add to ANTI_PATTERNS below + add a corresponding fixture in
tests/fixtures/codegen_failures/.

When a pattern matches, the scanner returns a descriptive `reason` string
that GVR feeds back to CoderAgent's next attempt. The reason references
the anti-pattern doc by section so the LLM has a fix path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class AntiPattern:
    """One static pattern + the human-readable feedback to return on match.

    `pattern` is compiled at import time. `reason` is the GVR feedback
    string — should be specific enough for the LLM to fix on retry.
    `where` optionally narrows the scan to specific filenames (e.g.,
    "model.py" only) — None means scan all .py files.
    """
    name: str
    pattern: re.Pattern
    reason: str
    where: Optional[Callable[[str], bool]] = None


def _word(s: str) -> re.Pattern:
    """Compile a whole-word regex (word-boundary anchored on both sides)."""
    return re.compile(rf"\b{re.escape(s)}\b")


def _attr(s: str) -> re.Pattern:
    """Compile `.attr` matcher (period prefix anchored, word boundary after)."""
    return re.compile(rf"\.{re.escape(s)}\b")


# ── Catalog: every entry traces back to a §-numbered failure mode in
#    mymomo_knowledge/05-anti-patterns.md. Order does not matter — all
#    patterns are scanned every time.
ANTI_PATTERNS: list[AntiPattern] = [
    # § 1 — Hallucinated class names
    AntiPattern(
        name="hallucinated_NetworkGrid",
        pattern=_word("NetworkGrid"),
        reason=(
            "Hallucinated class `NetworkGrid` — not in abm_auto.runtime. "
            "Grid and Network are separate top-level classes (05-anti-patterns.md §1)."
        ),
    ),
    AntiPattern(
        name="hallucinated_GridNetwork",
        pattern=_word("GridNetwork"),
        reason=(
            "Hallucinated class `GridNetwork` — not in abm_auto.runtime. "
            "Grid and Network are separate top-level classes (05-anti-patterns.md §1)."
        ),
    ),
    AntiPattern(
        name="hallucinated_NetworkModel",
        pattern=_word("NetworkModel"),
        reason=(
            "Hallucinated class `NetworkModel` — not in abm_auto.runtime. "
            "Use `Model` (single base class) (05-anti-patterns.md §1)."
        ),
    ),
    AntiPattern(
        name="hallucinated_WattsStrogatzNetwork",
        pattern=_word("WattsStrogatzNetwork"),
        reason=(
            "Hallucinated class `WattsStrogatzNetwork` — not in abm_auto.runtime. "
            "Use `Network` + `topology=topologies.watts_strogatz(k=..., p=...)` "
            "(05-anti-patterns.md §1; 01-runtime-api.md §Network)."
        ),
    ),
    AntiPattern(
        name="hallucinated_BarabasiAlbertGraph",
        pattern=_word("BarabasiAlbertGraph"),
        reason=(
            "Hallucinated class `BarabasiAlbertGraph` — not in abm_auto.runtime. "
            "Use `Network` + `topology=topologies.barabasi_albert(m=...)` "
            "(05-anti-patterns.md §1)."
        ),
    ),
    AntiPattern(
        name="hallucinated_GridModel",
        pattern=_word("GridModel"),
        reason=(
            "Hallucinated class `GridModel` — not in abm_auto.runtime. "
            "Use `Model` (single base class) (05-anti-patterns.md §1)."
        ),
    ),
    AntiPattern(
        name="hallucinated_NetworkAgentModel",
        pattern=_word("NetworkAgentModel"),
        reason=(
            "Hallucinated class `NetworkAgentModel` — not in abm_auto.runtime. "
            "Use `Model` (single base class) (05-anti-patterns.md §1)."
        ),
    ),
    AntiPattern(
        name="hallucinated_AgentScheduler",
        pattern=_word("AgentScheduler"),
        reason=(
            "Hallucinated class `AgentScheduler` — no such thing. "
            "Use `for t in self.iterator(periods):` in Model.run() "
            "(05-anti-patterns.md §1)."
        ),
    ),
    AntiPattern(
        name="hallucinated_EventLoop",
        pattern=_word("EventLoop"),
        reason=(
            "Hallucinated class `EventLoop` — no such thing. "
            "Use `for t in self.iterator(periods):` in Model.run() "
            "(05-anti-patterns.md §1)."
        ),
    ),
    # § 2 — Hallucinated attributes / methods
    AntiPattern(
        name="hallucinated_attr_gen_num",
        pattern=_attr("gen_num"),
        reason=(
            "`agent.gen_num` does not exist — the LLM invented this from `Calibrator`. "
            "Drop the reference entirely (05-anti-patterns.md §2)."
        ),
    ),
    AntiPattern(
        name="hallucinated_attr_generation_num",
        pattern=_attr("generation_num"),
        reason=(
            "`agent.generation_num` does not exist — drop the reference entirely "
            "(05-anti-patterns.md §2)."
        ),
    ),
    AntiPattern(
        name="hallucinated_method_shuffle",
        pattern=re.compile(r"\.shuffle\s*\(\s*\)"),
        reason=(
            "`AgentList` has no `.shuffle()` method. Iterate `self.agents` directly — "
            "MyMoMo Runtime handles activation order (05-anti-patterns.md §2)."
        ),
    ),
    AntiPattern(
        name="hallucinated_hook_after_setup",
        pattern=re.compile(r"\bdef\s+after_setup\b"),
        reason=(
            "There is no `after_setup()` hook on `Model`. All initialisation "
            "must go inside `setup()` (05-anti-patterns.md §2)."
        ),
    ),
    AntiPattern(
        name="hallucinated_add_property",
        pattern=re.compile(r"\.add_property\s*\("),
        reason=(
            "`DataCollector.add_property(...)` does not exist. Use "
            "`add_agent_property(container, attr)` or `add_environment_property(attr)` "
            "(05-anti-patterns.md §2)."
        ),
    ),
    # § 3 — Removed string-based network API
    AntiPattern(
        name="removed_api_network_type",
        pattern=re.compile(r"\bnetwork_type\s*="),
        reason=(
            "Removed API: the `network_type=...` kwarg was deleted. "
            "Use `topology=topologies.<name>(...)` callable. Examples: "
            "`topologies.watts_strogatz(k=6, p=0.1)`, "
            "`topologies.netlogo_spatially_clustered(avg_degree=6)`. "
            "(01-runtime-api.md §Network; 05-anti-patterns.md §3.)"
        ),
    ),
    AntiPattern(
        name="removed_api_network_params",
        pattern=re.compile(r"\bnetwork_params\s*="),
        reason=(
            "Removed API: the `network_params=...` kwarg was deleted. "
            "Bind params at topology construction: "
            "`topology=topologies.watts_strogatz(k=6, p=0.1)` "
            "(01-runtime-api.md §Network; 05-anti-patterns.md §3)."
        ),
    ),
    AntiPattern(
        name="bad_networkx_name_watts_strogatz",
        pattern=_word("watts_strogatz_graph"),
        reason=(
            "Direct networkx graph names are no longer accepted as `network_type` "
            "strings (that API is removed). Use the callable form: "
            "`topology=topologies.watts_strogatz(k=..., p=...)` "
            "(01-runtime-api.md §Network)."
        ),
    ),
    AntiPattern(
        name="bad_networkx_name_barabasi_albert",
        pattern=_word("barabasi_albert_graph"),
        reason=(
            "Direct networkx graph names are no longer accepted as `network_type`. "
            "Use the callable form: `topology=topologies.barabasi_albert(m=...)` "
            "(01-runtime-api.md §Network)."
        ),
    ),
    AntiPattern(
        name="bad_networkx_name_erdos_renyi",
        pattern=_word("erdos_renyi_graph"),
        reason=(
            "Direct networkx graph names are no longer accepted as `network_type`. "
            "Use the callable form: `topology=topologies.erdos_renyi(p=...)` "
            "(01-runtime-api.md §Network)."
        ),
    ),
]


# ── Trigger snippets: one minimal code sample per anti-pattern that MUST
#    match its pattern. Single source of truth shared by:
#      - tests/test_codegen_anti_patterns.py (regression fixtures)
#      - AntiPatternGate.self_test (the verification-tier audit surface)
#    The coverage gate test asserts every ANTI_PATTERNS entry has a
#    trigger here; the parametrized fixture test asserts every trigger
#    actually fires its pattern. So this dict cannot silently drift.
TRIGGERS: dict[str, str] = {
    # § 1 — Hallucinated class names
    "hallucinated_NetworkGrid": "from abm_auto.runtime import NetworkGrid\nclass M: pass\n",
    "hallucinated_GridNetwork": "from abm_auto.runtime import GridNetwork\n",
    "hallucinated_NetworkModel": "class MyModel(NetworkModel):\n    pass\n",
    "hallucinated_WattsStrogatzNetwork": "self.network = WattsStrogatzNetwork(k=6, p=0.1)\n",
    "hallucinated_BarabasiAlbertGraph": "self.network = BarabasiAlbertGraph(m=3)\n",
    "hallucinated_GridModel": "class MyModel(GridModel):\n    pass\n",
    "hallucinated_NetworkAgentModel": "class MyModel(NetworkAgentModel):\n    pass\n",
    "hallucinated_AgentScheduler": "scheduler = AgentScheduler(self.agents)\n",
    "hallucinated_EventLoop": "loop = EventLoop()\n",
    # § 2 — Hallucinated attributes / methods
    "hallucinated_attr_gen_num": "if agent.gen_num > 0:\n    pass\n",
    "hallucinated_attr_generation_num": "print(agent.generation_num)\n",
    "hallucinated_method_shuffle": "self.agents.shuffle()\n",
    "hallucinated_hook_after_setup": "class M(Model):\n    def after_setup(self):\n        pass\n",
    "hallucinated_add_property": "self.data_collector.add_property('count')\n",
    # § 3 — Removed string-based network API
    "removed_api_network_type": "self.network.setup_agent_connections(network_type='watts_strogatz_graph')\n",
    "removed_api_network_params": "self.network.setup_agent_connections(network_params={'k': 6})\n",
    "bad_networkx_name_watts_strogatz": "g = getattr(nx, 'watts_strogatz_graph')(150, k=6, p=0.1)\n",
    "bad_networkx_name_barabasi_albert": "g = getattr(nx, 'barabasi_albert_graph')(150, m=3)\n",
    "bad_networkx_name_erdos_renyi": "g = nx.erdos_renyi_graph(150, p=0.05)\n",
}


def scan(code_files: dict[str, str]) -> list[str]:
    """Scan `code_files` for known anti-patterns.

    Args:
        code_files: {relative_path: file_contents} — typically from
            `Workspace.read_model_files()`.

    Returns a list of human-readable failure reasons (empty if clean).
    Each reason is prefixed with `[<filename>:<anti_pattern_name>]` so the
    LLM can identify both where the issue lives and which catalog entry
    matched.
    """
    issues: list[str] = []
    for filename, content in code_files.items():
        if not filename.endswith(".py"):
            continue
        for ap in ANTI_PATTERNS:
            if ap.where is not None and not ap.where(filename):
                continue
            if ap.pattern.search(content):
                issues.append(f"[{filename}:{ap.name}] {ap.reason}")
    return issues
