"""Tests for the stub extraction + the wired CoverageGatePhase (ADR-014 1a).

Proves the gate now has a real caller: a well-specified-but-unbuildable spec
(a GAN in the design prose) HALTS the pipeline; a covered spec passes.
"""
from __future__ import annotations

import types

from abm_auto.codegen.coverage_gate import (
    CoverageGate,
    extract_mechanisms_heuristic,
)
from abm_auto.codegen.mechanism_spec import (
    LearnedOperator,
    MechanismSpec,
    PopulationDynamicsSpec,
    ScenarioParam,
)
from abm_auto.pipeline.phases.coverage import CoverageGatePhase
from abm_auto.runner.workspace import Workspace


def _spec(**overrides) -> MechanismSpec:
    kw = dict(
        scenario_params=[
            ScenarioParam(name="agent_num", type="int", default=50),
            ScenarioParam(name="periods", type="int", default=100),
        ],
        n_agents_param="agent_num",
        periods_param="periods",
        env_step_pseudocode="step",
        targets=["metric"],
    )
    kw.update(overrides)
    return MechanismSpec(**kw)


# ── stub extraction ────────────────────────────────────────────────────────


def test_extract_flags_gan_prose_uncovered() -> None:
    mechs = extract_mechanisms_heuristic(
        None, "The generator and discriminator are trained by adversarial training (a GAN).")
    assert not CoverageGate().check(mechs).passed


def test_extract_typed_operator_slots_are_covered() -> None:
    spec = _spec(
        learned_operators=[LearnedOperator(name="m", n_items=96)],
        population_dynamics=PopulationDynamicsSpec(),
    )
    mechs = extract_mechanisms_heuristic(spec, "agents combine items by simple rules")
    assert CoverageGate().check(mechs).passed


def test_extract_plain_prose_is_ordinary() -> None:
    mechs = extract_mechanisms_heuristic(None, "each unhappy agent moves to a random empty cell")
    assert CoverageGate().check(mechs).passed


def test_extract_reinforcement_learning_uncovered_but_tabular_q_ok() -> None:
    assert not CoverageGate().check(
        extract_mechanisms_heuristic(None, "agents use deep reinforcement learning")).passed
    assert CoverageGate().check(
        extract_mechanisms_heuristic(None, "agents use tabular q-learning")).passed


# ── the wired phase (integration: the gate now has a caller) ────────────────


def _ctx(spec: MechanismSpec, design: str):
    ws = Workspace.create(name="test_coverage_phase")
    (ws.path / "mechanism_spec.json").write_text(spec.to_json(), encoding="utf-8")
    ws.write_design(design)
    ws.write_mechanism_spec("")
    return types.SimpleNamespace(workspace=ws, using_external_model=False,
                                 pipeline_halted=False, halt_reason="")


def test_phase_halts_on_unbuildable_gan() -> None:
    ctx = _ctx(_spec(), "A conditional GAN: generator vs discriminator, adversarial training.")
    phase = CoverageGatePhase()
    assert phase.should_run(ctx)
    phase.run(ctx)
    assert ctx.pipeline_halted
    assert "Coverage Gate" in ctx.halt_reason


def test_phase_passes_on_covered_spec() -> None:
    spec = _spec(learned_operators=[LearnedOperator(name="m", n_items=96)],
                 population_dynamics=PopulationDynamicsSpec())
    ctx = _ctx(spec, "Agents carry a trained model; population undergoes turnover by simple rules.")
    phase = CoverageGatePhase()
    phase.run(ctx)
    assert not ctx.pipeline_halted


def test_phase_skipped_for_external_model() -> None:
    ctx = _ctx(_spec(), "anything")
    ctx.using_external_model = True
    assert not CoverageGatePhase().should_run(ctx)
