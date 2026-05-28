"""Anti-pattern scanner regression tests — codegen-failure fixtures.

Each fixture is a (synthetic code snippet, expected anti-pattern name) pair.
The test asserts that `scan()` reports that anti-pattern. Coverage gate at
the end forces every entry in ANTI_PATTERNS to have a fixture.

When you add a new anti-pattern to `abm_auto/codegen/anti_patterns.py`:
  1. Append the AntiPattern entry there.
  2. Append a fixture tuple to FIXTURES below.
  3. Update mymomo_knowledge/05-anti-patterns.md if it's a new section.

The coverage gate (`test_every_anti_pattern_has_a_fixture`) will fail
otherwise, forcing the discipline.
"""
from __future__ import annotations

import pytest

from abm_auto.codegen.anti_patterns import ANTI_PATTERNS, scan


# Each tuple: (anti_pattern.name, synthetic code snippet that should trigger it)
FIXTURES: list[tuple[str, str]] = [
    # § 1 — Hallucinated class names
    (
        "hallucinated_NetworkGrid",
        "from abm_auto.runtime import NetworkGrid\nclass M: pass\n",
    ),
    (
        "hallucinated_GridNetwork",
        "from abm_auto.runtime import GridNetwork\n",
    ),
    (
        "hallucinated_NetworkModel",
        "class MyModel(NetworkModel):\n    pass\n",
    ),
    (
        "hallucinated_WattsStrogatzNetwork",
        "self.network = WattsStrogatzNetwork(k=6, p=0.1)\n",
    ),
    (
        "hallucinated_BarabasiAlbertGraph",
        "self.network = BarabasiAlbertGraph(m=3)\n",
    ),
    (
        "hallucinated_GridModel",
        "class MyModel(GridModel):\n    pass\n",
    ),
    (
        "hallucinated_NetworkAgentModel",
        "class MyModel(NetworkAgentModel):\n    pass\n",
    ),
    (
        "hallucinated_AgentScheduler",
        "scheduler = AgentScheduler(self.agents)\n",
    ),
    (
        "hallucinated_EventLoop",
        "loop = EventLoop()\n",
    ),
    # § 2 — Hallucinated attributes / methods
    (
        "hallucinated_attr_gen_num",
        "if agent.gen_num > 0:\n    pass\n",
    ),
    (
        "hallucinated_attr_generation_num",
        "print(agent.generation_num)\n",
    ),
    (
        "hallucinated_method_shuffle",
        "self.agents.shuffle()\n",
    ),
    (
        "hallucinated_hook_after_setup",
        "class M(Model):\n    def after_setup(self):\n        pass\n",
    ),
    (
        "hallucinated_add_property",
        "self.data_collector.add_property('count')\n",
    ),
    # § 3 — Removed string-based network API
    (
        "removed_api_network_type",
        "self.network.setup_agent_connections(network_type='watts_strogatz_graph')\n",
    ),
    (
        "removed_api_network_params",
        "self.network.setup_agent_connections(network_params={'k': 6})\n",
    ),
    (
        "bad_networkx_name_watts_strogatz",
        "g = getattr(nx, 'watts_strogatz_graph')(150, k=6, p=0.1)\n",
    ),
    (
        "bad_networkx_name_barabasi_albert",
        "g = getattr(nx, 'barabasi_albert_graph')(150, m=3)\n",
    ),
    (
        "bad_networkx_name_erdos_renyi",
        "g = nx.erdos_renyi_graph(150, p=0.05)\n",
    ),
]


@pytest.mark.parametrize("expected_name,code", FIXTURES, ids=[name for name, _ in FIXTURES])
def test_anti_pattern_match(expected_name: str, code: str) -> None:
    """Each fixture's synthetic code must trigger its expected anti-pattern."""
    issues = scan({"core/model.py": code})
    matched = [i for i in issues if expected_name in i]
    assert matched, (
        f"Expected pattern {expected_name!r} to match. "
        f"Code: {code!r}. Got issues: {issues}"
    )


def test_clean_code_passes() -> None:
    """Current-style code (no anti-patterns) should produce zero issues."""
    code = """
from abm_auto.runtime import Model, NetworkAgent, topologies

class Person(NetworkAgent):
    def setup(self):
        self.state: int = self._safe_attr("state", 0)

class MyModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Person)
        self.network = self.create_network()

    def setup(self):
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        self.network.setup_agent_connections(
            agent_lists=[self.agents],
            topology=topologies.watts_strogatz(k=6, p=0.1),
        )

    def run(self):
        for t in self.iterator(self.scenario.periods):
            for agent in self.agents:
                for nb in self.network.get_neighbors(agent):
                    pass
"""
    assert scan({"core/model.py": code}) == []


def test_non_py_files_skipped() -> None:
    """Non-.py files must not be scanned (CSVs / markdown may legitimately mention the strings)."""
    csv_content = (
        "id,run_num,periods,network_type\n"   # `network_type` appears in CSV header
        "0,1,250,watts_strogatz_graph\n"
    )
    md_content = "Documentation may freely mention `WattsStrogatzNetwork` as a forbidden example."
    issues = scan({
        "data/input/SimulatorScenarios.csv": csv_content,
        "docs/README.md": md_content,
    })
    assert issues == []


def test_every_anti_pattern_has_a_fixture() -> None:
    """Coverage gate: any new AntiPattern entry must also have a fixture in FIXTURES.

    Forces the discipline that adding a pattern + adding a test happen together.
    """
    catalog_names = {ap.name for ap in ANTI_PATTERNS}
    fixture_names = {name for name, _ in FIXTURES}
    missing = catalog_names - fixture_names
    assert not missing, (
        f"Anti-patterns without fixtures: {sorted(missing)}. "
        f"Add (name, synthetic_code) entries to FIXTURES in this file."
    )
