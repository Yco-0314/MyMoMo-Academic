"""Tests that the TemplateGenerator EMITS declared operators (ADR-014 codegen
fidelity — the Hawk-Dove e2e fix).

The e2e showed the CoderAgent hand-rolls a declared operator instead of calling
it. model.py is template-owned, so the template now constructs each operator +
drives the turnover deterministically from the spec. These pin that.
"""
from __future__ import annotations

from abm_auto.codegen.mechanism_spec import (
    AgentStateVar,
    MechanismSpec,
    PayoffGameSpec,
    PopulationDynamicsSpec,
    ReferenceAsset,
    ScenarioParam,
    TopologySpec,
    VitalDynamicsSpec,
)
from abm_auto.codegen.template_generator import generate_model_py


def _base(**overrides) -> MechanismSpec:
    kw = dict(
        topology=None,
        scenario_params=[
            ScenarioParam(name="agent_num", type="int", default=200),
            ScenarioParam(name="periods", type="int", default=300),
            ScenarioParam(name="V", type="float", default=2.0),
            ScenarioParam(name="C", type="float", default=4.0),
        ],
        n_agents_param="agent_num",
        periods_param="periods",
        env_step_pseudocode="play + accumulate",
        targets=["hawk_fraction"],
        agent_state_vars=[
            AgentStateVar(name="strategy", type="int", init="0"),
            AgentStateVar(name="score", type="float", init="0.0"),
            AgentStateVar(name="fitness", type="float", init="1.0"),
        ],
    )
    kw.update(overrides)
    return MechanismSpec(**kw)


def test_no_operators_no_emission() -> None:
    code = generate_model_py(_base())
    assert "PayoffGame" not in code and "MoranProcess" not in code
    compile(code, "model.py", "exec")


def test_payoff_and_moran_are_constructed_and_driven() -> None:
    spec = _base(
        payoff_games=[PayoffGameSpec(name="game", game="hawk_dove",
                                     params={"V": "scenario.V", "C": "scenario.C"},
                                     strategy_var="strategy")],
        population_dynamics=PopulationDynamicsSpec(
            fitness_attr="fitness", death_model="constant", death_rate=0.5,
            inherit_attrs=["strategy"], reset_attrs=["score", "fitness"]),
    )
    code = generate_model_py(spec)
    assert "from abm_auto.runtime import Model, PayoffGame, MoranProcess" in code
    assert "self.game = PayoffGame.hawk_dove(V=self.scenario.V, C=self.scenario.C)" in code
    assert "self._moran = MoranProcess(fitness_attr='fitness'" in code
    assert "self._moran.turnover(self.agents, inherit=self._moran_inherit)" in code
    # #1a: the PayoffGame is WIRED onto the environment (interaction operator),
    # so env.step() can call self.game.play(...). Moran is model-driven — NOT wired.
    assert "self.environment.game = self.game" in code
    assert "self.environment._moran" not in code
    # inherit hook from inherit_attrs / reset_attrs (reset -> the agent_state_var init)
    assert "child.strategy = copy.deepcopy(parent.strategy)" in code
    assert "child.score = 0.0" in code
    assert "child.fitness = 1.0" in code
    compile(code, "model.py", "exec")


def test_matrix_game_emitted() -> None:
    code = generate_model_py(_base(payoff_games=[
        PayoffGameSpec(name="g", game="matrix", matrix=[[3, 0], [5, 1]])]))
    assert "self.g = PayoffGame.from_matrix([[3, 0], [5, 1]])" in code
    compile(code, "model.py", "exec")


def test_vital_dynamics_constructed() -> None:
    code = generate_model_py(_base(vital_dynamics=[
        VitalDynamicsSpec(name="vital", energy_attr="score", reproduce_prob=0.04,
                          max_population=3000)]))
    assert "from abm_auto.runtime import Model, VitalDynamics" in code
    assert "self.vital = VitalDynamics(energy_attr='score'" in code
    assert "reproduce_prob=0.04" in code and "max_population=3000" in code
    assert "self.environment.vital = self.vital" in code   # #1a wired onto env
    compile(code, "model.py", "exec")


def test_reference_asset_loaded() -> None:
    code = generate_model_py(_base(reference_assets=[
        ReferenceAsset(name="rules", filename="rules.csv", output_col="item",
                       input_cols=["c1", "c2"], given_col="given")]))
    assert "RuleTable" in code
    assert "self.rules = RuleTable.from_csv(" in code and "'rules.csv'" in code
    assert "self.environment.rules = self.rules" in code   # #1a wired onto env
    compile(code, "model.py", "exec")


def test_network_variant_also_emits_operators() -> None:
    spec = _base(
        topology=TopologySpec(type="watts_strogatz", params={"k": 4, "p": 0.1}),
        payoff_games=[PayoffGameSpec(name="game", game="hawk_dove",
                                     params={"V": 2, "C": 4})],
        population_dynamics=PopulationDynamicsSpec(
            fitness_attr="fitness", inherit_attrs=["strategy"], reset_attrs=["score"]),
    )
    code = generate_model_py(spec)
    assert "MoranProcess" in code
    assert "self._moran.turnover(self.agents, inherit=self._moran_inherit)" in code
    # #1a: wiring present in the network variant too, and BEFORE initialize()
    # (so the env owns the operator when its initialize hook runs).
    assert "self.environment.game = self.game" in code
    assert code.index("self.environment.game = self.game") < code.index("initialize(")
    compile(code, "model.py", "exec")
