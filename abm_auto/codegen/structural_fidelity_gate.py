"""StructuralFidelityGate — spec-vs-code structural checks as a Gate (ADR-013).

Extracts the pure judgement out of the `_structural_fidelity_validator`
closure in pipeline/phases/codegen.py. That closure captured `ctx` only
to fetch two things — `mechanism_spec.json` and the model's code files —
then judged purely. This Gate is that pure core, depending on nothing
but its `(spec, code_files)` input. No ctx, no workspace, no I/O.

(The existing closure is left in place for this commit — additive. A
follow-up can rewire the closure + tests/test_structural_fidelity.py's
duplicated `_scan` to delegate here, making this the single source of
truth. Logged, not done, to avoid touching Pipeline in this step.)

Tier = "verification". The checks prove a COMPLETE structural property
over the spec: every declared scenario_param appears as `self.X` in
scenario.py, every declared agent_state_var appears in agent.py, a
GridAgent never coexists with Network wiring, and every declared
INTERACTION operator (PayoffGame / RuleTable / VitalDynamics) is actually
called in the LLM-owned interaction body (`self.<name>`), never hand-rolled.
These are exhaustive over the spec's declarations (like the anti-pattern
catalogue), so the self-test can prove both directions — known-bad caught,
clean passes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class StructuralFidelityInput:
    """Input: the parsed mechanism_spec.json + the model's code files
    ({path: contents}). Both are already in hand at the call site —
    the Gate adds no I/O of its own."""

    spec: dict
    code_files: dict[str, str]


# Import Verdict lazily-safe at module top (no heavy deps).
from abm_auto.verification.gate import Verdict


def _scan(spec: dict, code_files: dict[str, str]) -> list[str]:
    """Pure structural scan. The canonical implementation of the logic
    that pipeline/phases/codegen.py:_structural_fidelity_validator and
    tests/test_structural_fidelity.py:_scan currently each hold a copy of.
    Returns human-readable issue strings (empty = structurally faithful).
    """
    issues: list[str] = []

    scenario_src = code_files.get("core/scenario.py", "")
    if scenario_src.strip():
        for p in spec.get("scenario_params", []) or []:
            name = p.get("name", "")
            if not name:
                continue
            if not re.search(rf"\bself\.{re.escape(name)}\b", scenario_src):
                issues.append(
                    f"scenario.py: missing declaration `self.{name}`. "
                    f"mechanism_spec.json declares it as a scenario_param "
                    f"(unit={p.get('unit', '?')}, default={p.get('default', '?')}); "
                    f"add `self.{name} = <default>` in Scenario.setup()."
                )

    agent_src = code_files.get("core/agent.py", "")
    if agent_src.strip():
        for v in spec.get("agent_state_vars", []) or []:
            name = v.get("name", "")
            if not name:
                continue
            if not re.search(rf"\bself\.{re.escape(name)}\b", agent_src):
                issues.append(
                    f"agent.py: missing state variable `self.{name}`. "
                    f"mechanism_spec.json declares it as an agent_state_var "
                    f"(type={v.get('type', '?')}, init={v.get('init', '?')!r}); "
                    f"initialize it in Agent.setup()."
                )

    # Grid/Network contradiction (2026-05-30 originate dogfood).
    model_src = code_files.get("core/model.py", "")
    spec_topology = spec.get("topology")
    agent_inherits_grid = bool(
        agent_src and re.search(r"class\s+\w+\(\s*GridAgent\s*\)", agent_src)
    )
    model_uses_network = bool(
        model_src and (
            "setup_agent_connections" in model_src or "create_network" in model_src
        )
    )
    if agent_inherits_grid and model_uses_network:
        spec_topo_type = (
            spec_topology.get("type") if isinstance(spec_topology, dict) else None
        )
        issues.append(
            f"Grid/Network contradiction: agent.py inherits GridAgent but "
            f"model.py wires a Network topology (`{spec_topo_type or 'unknown'}`). "
            f"Network.add_agent asserts isinstance(agent, NetworkAgent), which "
            f"crashes at Phase 4. Fix in mechanism_spec.json: set "
            f'"topology": null for Grid / spatial / no-topology models.'
        )

    # Operator USE (ADR-014 codegen fidelity — Hawk-Dove e2e E5b). An INTERACTION
    # operator (PayoffGame / RuleTable / VitalDynamics) is constructed in
    # template-owned model.py AND wired onto the environment as `self.<name>`. The
    # LLM-owned interaction body (environment.py / agent.py) MUST CALL it; a
    # declared-but-uncalled operator means the LLM hand-rolled the mechanism (the
    # constructed operator is dead code). model.py is excluded on purpose — it
    # always references the operator (it builds + wires it), so scanning it would
    # never catch the hand-roll. MoranProcess (population_dynamics) is model-driven
    # turnover and is intentionally NOT required in the interaction body.
    interaction_src = "\n".join(
        code_files.get(f, "") or "" for f in ("core/environment.py", "core/agent.py")
    )
    if interaction_src.strip():
        op_kinds = (
            ("payoff_games", "PayoffGame", "pa, pb = self.{n}.play(a.strategy, b.strategy)"),
            ("reference_assets", "RuleTable", "self.{n}.combine(items) / self.{n}.given_indices()"),
            ("vital_dynamics", "VitalDynamics", "self.{n}.step(agents, spawn=..., on_birth=...)"),
        )
        for spec_key, opname, call_hint in op_kinds:
            for op in spec.get(spec_key, []) or []:
                name = op.get("name", "")
                if not name:
                    continue
                # accept the wired env attr `self.<name>` or `self.model.<name>`
                if not re.search(rf"\bself\.(?:model\.)?{re.escape(name)}\b", interaction_src):
                    issues.append(
                        f"environment.py/agent.py: declared {opname} `self.{name}` is "
                        f"never called. model.py constructs it and wires it onto the "
                        f"environment as `self.{name}` — the interaction body must CALL "
                        f"it (`{call_hint.format(n=name)}`), not hand-roll the mechanism. "
                        f"A declared operator that is never used is a codegen-fidelity "
                        f"failure (the operator exists to replace the hand-roll)."
                    )

    return issues


class StructuralFidelityGate:
    """Gate over the 'spec + code' family: verifies the generated code's
    structural surface matches mechanism_spec.json. Verification tier."""

    name = "structural_fidelity"
    family = "spec_and_code"
    tier = "verification"

    def judge(self, x: StructuralFidelityInput) -> Verdict:
        """Deterministic: scan spec vs code, fail iff any structural drift.
        Empty spec or empty code → pass (nothing to verify against), same
        as the original closure's early-return semantics."""
        issues = _scan(x.spec, x.code_files)
        return Verdict(
            passed=not issues,
            tier="verification",
            gate_name=self.name,
            reasons=issues,
            salient_number=None,  # structural drift is categorical
            evidence={"issue_count": len(issues)},
        )

    def self_test(self) -> bool:
        """Verification-paradigm self-test on synthetic spec+code.

          (a) aligned spec+code → pass
          (b) missing scenario_param → caught
          (c) missing agent_state_var → caught
          (d) Grid/Network contradiction → caught
          (e) declared interaction operator CALLED → pass
          (f) declared interaction operator never called → caught

        Pure, no I/O. (b)-(d),(f) are the known-bad end; (a),(e) guard
        against over-firing. Exhaustive over the four check families → the
        completeness that earns verification tier.
        """
        aligned_spec = {
            "scenario_params": [{"name": "beta", "default": 0.3}],
            "agent_state_vars": [{"name": "state", "type": "int"}],
            "topology": None,
        }
        aligned_code = {
            "core/scenario.py": "class S:\n    def setup(self):\n        self.beta = 0.3\n",
            "core/agent.py": "class A:\n    def setup(self):\n        self.state = 0\n",
            "core/model.py": "class M:\n    pass\n",
        }
        if not self.judge(StructuralFidelityInput(aligned_spec, aligned_code)).passed:
            return False  # (a) clean must pass

        # (b) missing scenario_param
        bad_scn = dict(aligned_code, **{"core/scenario.py": "class S:\n    pass\n"})
        if self.judge(StructuralFidelityInput(aligned_spec, bad_scn)).passed:
            return False

        # (c) missing agent_state_var
        bad_agent = dict(aligned_code, **{"core/agent.py": "class A:\n    pass\n"})
        if self.judge(StructuralFidelityInput(aligned_spec, bad_agent)).passed:
            return False

        # (d) Grid/Network contradiction
        contra_spec = {"scenario_params": [], "agent_state_vars": [],
                       "topology": {"type": "watts_strogatz"}}
        contra_code = {
            "core/agent.py": "class A(GridAgent):\n    pass\n",
            "core/model.py": "class M:\n    def setup(self):\n        self.network = self.create_network()\n",
        }
        if self.judge(StructuralFidelityInput(contra_spec, contra_code)).passed:
            return False

        # (e) declared interaction operator CALLED in the body → pass
        op_spec = {"scenario_params": [], "agent_state_vars": [], "topology": None,
                   "payoff_games": [{"name": "game"}]}
        op_ok = {"core/environment.py":
                 "class E:\n    def step(self, agents):\n        pa, pb = self.game.play(0, 1)\n"}
        if not self.judge(StructuralFidelityInput(op_spec, op_ok)).passed:
            return False

        # (f) declared interaction operator NEVER called (hand-rolled) → caught
        op_bad = {"core/environment.py":
                  "class E:\n    def step(self, agents):\n        pa = agents[0].play_against(agents[1])\n"}
        if self.judge(StructuralFidelityInput(op_spec, op_bad)).passed:
            return False

        return True
