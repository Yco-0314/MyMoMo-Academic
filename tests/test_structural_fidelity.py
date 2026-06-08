"""Test the structural fidelity scan logic in isolation.

The scan logic is now the single source of truth in
`StructuralFidelityGate._scan` (ADR-013 debt 3b); the CodegenPhase
closure delegates to it. These tests pin the invariants directly against
that canonical `_scan` with synthetic spec + code_files dicts, no
Pipeline spin-up.

Assertions check substrings (param names, "Grid/Network contradiction",
"watts_strogatz") + empty-list, all of which the canonical (richer)
messages contain — so they survived the merge from the old abbreviated
in-test reimplementation.
"""
from __future__ import annotations

import json
from pathlib import Path

from abm_auto.codegen.structural_fidelity_gate import _scan


def test_clean_code_passes() -> None:
    """Aligned code (every spec field appears in correct file) yields zero issues."""
    spec = {
        "scenario_params": [
            {"name": "agent_num", "type": "int", "default": 100},
            {"name": "periods", "type": "int", "default": 250},
        ],
        "agent_state_vars": [
            {"name": "state", "type": "int", "init": "0"},
        ],
    }
    files = {
        "core/scenario.py": (
            "class S(Scenario):\n"
            "    def setup(self):\n"
            "        self.agent_num = 100\n"
            "        self.periods = 250\n"
        ),
        "core/agent.py": (
            "class A(Agent):\n"
            "    def setup(self):\n"
            "        self.state = 0\n"
        ),
    }
    assert _scan(spec, files) == []


def test_scenario_param_missing_in_scenario_py() -> None:
    """If spec declares a scenario_param that scenario.py doesn't, flag it."""
    spec = {
        "scenario_params": [
            {"name": "missing_param", "type": "int", "default": 1, "unit": "ticks"},
            {"name": "agent_num", "type": "int", "default": 100},
        ],
        "agent_state_vars": [],
    }
    files = {
        "core/scenario.py": "self.agent_num = 100\n",
    }
    issues = _scan(spec, files)
    assert len(issues) == 1
    assert "missing_param" in issues[0]


def test_agent_state_var_missing_in_agent_py() -> None:
    """If spec declares an agent_state_var that agent.py doesn't initialize, flag it."""
    spec = {
        "scenario_params": [],
        "agent_state_vars": [
            {"name": "happiness", "type": "float", "init": "0.5"},
            {"name": "state", "type": "int", "init": "0"},
        ],
    }
    files = {
        "core/agent.py": "self.state = 0  # only this — happiness is missing\n",
    }
    issues = _scan(spec, files)
    assert len(issues) == 1
    assert "happiness" in issues[0]


def test_no_spec_no_issues() -> None:
    """Empty mechanism_spec.json fields → nothing to validate against → pass."""
    spec = {"scenario_params": [], "agent_state_vars": []}
    files = {"core/scenario.py": "...", "core/agent.py": "..."}
    assert _scan(spec, files) == []


def test_word_boundary_strict() -> None:
    """`self.agent_num_max` should NOT satisfy a spec asking for `agent_num`."""
    spec = {
        "scenario_params": [{"name": "agent_num", "type": "int", "default": 1}],
        "agent_state_vars": [],
    }
    files = {"core/scenario.py": "self.agent_num_max = 100\n"}
    issues = _scan(spec, files)
    assert len(issues) == 1
    assert "agent_num" in issues[0]


def test_missing_files_silent_pass() -> None:
    """When code_files doesn't include scenario.py or agent.py (e.g., LLM
    failed to emit them yet), the validator skips silently so it doesn't
    crowd out the dry_run validator's clearer error."""
    spec = {
        "scenario_params": [{"name": "x", "type": "int", "default": 1}],
        "agent_state_vars": [{"name": "y", "type": "int", "init": "0"}],
    }
    assert _scan(spec, {}) == []
    assert _scan(spec, {"core/model.py": "..."}) == []


def test_real_mechanism_spec_roundtrip(tmp_path: Path) -> None:
    """End-to-end: dump a realistic spec.json + matching files, scan, expect clean."""
    spec_data = {
        "project_name": "VirusOnNetwork",
        "scenario_params": [
            {"name": "periods", "type": "int", "default": 250, "unit": "ticks"},
            {"name": "agent_num", "type": "int", "default": 150, "unit": "count"},
            {"name": "virus_spread_chance", "type": "float", "default": 4.4,
             "unit": "percent", "min": 0, "max": 20},
        ],
        "agent_state_vars": [
            {"name": "state", "type": "int", "init": "0"},
            {"name": "virus_check_timer", "type": "int", "init": "0"},
        ],
    }
    (tmp_path / "mechanism_spec.json").write_text(json.dumps(spec_data))
    files = {
        "core/scenario.py": (
            "class VirusScenario(Scenario):\n"
            "    def setup(self):\n"
            "        self.periods: int = 250\n"
            "        self.agent_num: int = 150\n"
            "        self.virus_spread_chance: float = 4.4\n"
        ),
        "core/agent.py": (
            "class Person(NetworkAgent):\n"
            "    def setup(self):\n"
            "        self.state: int = 0\n"
            "        self.virus_check_timer: int = 0\n"
        ),
    }
    assert _scan(spec_data, files) == []


# ── Grid/Network contradiction (from originate dogfood) ─────────────────


def test_grid_network_contradiction_caught() -> None:
    """The originate-dogfood bug: agent.py uses GridAgent but model.py wires
    Network. The validator must surface this contradiction with a clear
    fix message pointing at mechanism_spec.json topology."""
    spec = {
        "scenario_params": [],
        "agent_state_vars": [],
        "topology": {"type": "watts_strogatz", "params": {"k": 6, "p": 0.1}},
    }
    files = {
        "core/agent.py": "class Household(GridAgent):\n    pass\n",
        "core/model.py": (
            "class M(Model):\n"
            "    def setup(self):\n"
            "        self.network.setup_agent_connections(\n"
            "            agent_lists=[self.agents],\n"
            "            topology=topologies.watts_strogatz(k=6, p=0.1),\n"
            "        )\n"
        ),
    }
    issues = _scan(spec, files)
    assert any("Grid/Network contradiction" in i for i in issues)
    assert any("watts_strogatz" in i for i in issues)


def test_pure_grid_passes_when_no_network_in_model() -> None:
    """GridAgent + model.py without Network setup → no contradiction."""
    spec = {
        "scenario_params": [],
        "agent_state_vars": [],
        "topology": None,
    }
    files = {
        "core/agent.py": "class Household(GridAgent):\n    pass\n",
        "core/model.py": "class M(Model):\n    def setup(self):\n        self.grid = self.create_grid(width=80, height=80)\n",
    }
    assert _scan(spec, files) == []


def test_pure_network_passes_no_contradiction() -> None:
    """NetworkAgent + Network setup → no contradiction."""
    spec = {
        "scenario_params": [],
        "agent_state_vars": [],
        "topology": {"type": "watts_strogatz", "params": {"k": 6, "p": 0.1}},
    }
    files = {
        "core/agent.py": "class Person(NetworkAgent):\n    pass\n",
        "core/model.py": (
            "class M(Model):\n"
            "    def setup(self):\n"
            "        self.network.setup_agent_connections(\n"
            "            agent_lists=[self.agents],\n"
            "            topology=topologies.watts_strogatz(k=6, p=0.1),\n"
            "        )\n"
        ),
    }
    assert _scan(spec, files) == []


# ── Operator USE (codegen fidelity, Hawk-Dove e2e E5b) ──────────────────────


def test_declared_payoff_game_called_passes() -> None:
    """A declared PayoffGame that the env CALLS via the wired self.<name> is clean."""
    spec = {"scenario_params": [], "agent_state_vars": [],
            "payoff_games": [{"name": "game", "game": "hawk_dove"}]}
    files = {
        "core/environment.py": (
            "class E(Environment):\n"
            "    def step(self, agents):\n"
            "        pa, pb = self.game.play(agents[0].strategy, agents[1].strategy)\n"
        ),
    }
    assert _scan(spec, files) == []


def test_declared_payoff_game_handrolled_caught() -> None:
    """The real E5b failure: the operator is declared+wired but env hand-rolls
    the matrix (self.game never called) → must be caught."""
    spec = {"scenario_params": [], "agent_state_vars": [],
            "payoff_games": [{"name": "game", "game": "hawk_dove"}]}
    files = {
        "core/environment.py": (
            "class E(Environment):\n"
            "    def step(self, agents):\n"
            "        pa = agents[0].play_against(agents[1])\n"
        ),
        "core/agent.py": (
            "class P(Agent):\n"
            "    def play_against(self, other):\n"
            "        return 2 if self.strategy else 0\n"
        ),
    }
    issues = _scan(spec, files)
    assert len(issues) == 1
    assert "self.game" in issues[0] and "never called" in issues[0]


def test_declared_operator_via_self_model_passes() -> None:
    """Reaching the operator through self.model.<name> also counts as use."""
    spec = {"scenario_params": [], "agent_state_vars": [],
            "vital_dynamics": [{"name": "vital"}]}
    files = {
        "core/environment.py": (
            "class E(Environment):\n"
            "    def step(self, agents):\n"
            "        self.model.vital.step(agents, spawn=lambda: None)\n"
        ),
    }
    assert _scan(spec, files) == []


def test_operator_check_silent_without_interaction_files() -> None:
    """No env.py/agent.py yet (early codegen) → operator check stays silent."""
    spec = {"scenario_params": [], "agent_state_vars": [],
            "payoff_games": [{"name": "game"}]}
    assert _scan(spec, {}) == []
    assert _scan(spec, {"core/model.py": "self.game = PayoffGame.hawk_dove()"}) == []


# ── Hand-rolled turnover (bug B): Moran is model-driven, env must not re-roll it ──


def test_handrolled_turnover_caught_when_pop_dynamics_declared() -> None:
    """The re-run #2 dead `moran_process` in env.py — flagged now."""
    spec = {"scenario_params": [], "agent_state_vars": [],
            "population_dynamics": {"fitness_attr": "score"}}
    files = {"core/environment.py":
             "class E(Environment):\n    def moran_process(self, agents, scenario):\n        return agents\n"}
    issues = _scan(spec, files)
    assert len(issues) == 1
    assert "moran_process" in issues[0] and "hand-rolled population turnover" in issues[0]


def test_no_handrolled_turnover_passes() -> None:
    spec = {"scenario_params": [], "agent_state_vars": [],
            "population_dynamics": {"fitness_attr": "score"}}
    files = {"core/environment.py":
             "class E(Environment):\n    def step(self, agents, scenario):\n        for a in agents:\n            a.score += 1\n"}
    assert _scan(spec, files) == []


def test_turnover_check_silent_without_pop_dynamics() -> None:
    """No population_dynamics → a method named e.g. reproduce is the model's own
    business, not flagged."""
    spec = {"scenario_params": [], "agent_state_vars": []}
    files = {"core/environment.py": "class E:\n    def reproduce(self):\n        pass\n"}
    assert _scan(spec, files) == []
