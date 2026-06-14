"""
ABM Auto Runtime — simulation engine.

All generated model code imports from here::

    from abm_auto.runtime import Agent, Model, Grid, ...

**Architecture**
    A self-developed, dependency-free engine. Every class here is standalone
    Python — Agent/AgentList/Grid/Network/Spot/Edge, Model + the
    Simulator/Config/DataLoader orchestrator, Scenario, DataCollector, and the
    library operators.

**Exposed surface**
    Agent, AgentList, Model, Environment, DataCollector, Scenario, Config,
    Simulator, Grid, GridAgent, Network, NetworkAgent, topologies, + operators.

**Design notes**
    - Agent._safe_attr(name, default): keeps CSV-loaded values through setup()
    - GridAgent/NetworkAgent.set_category(): default category 0 (single-type)
    - Model.create_grid()/create_network(): inject self.agents + a
      scenario-seeded RNG so get_neighbors() needs no agent_list arg;
      Grid.width/height are properties
    - Grid/Network.get_neighbors(agent): return live Agent objects
    - engine_oracle.py validates the handcrafted corpus two ways: --science
      (behavioural correctness) and --check (byte-level regression).
"""

RUNTIME_ENGINE: str = "ABM Auto Runtime"

# ── Custom classes (fix gotchas, extend API, or fully standalone) ─────────────

from abm_auto.runtime._agent import Agent, GridAgent, NetworkAgent
from abm_auto.runtime._grid import Grid
from abm_auto.runtime._network import Network
from abm_auto.runtime._model import Model
from abm_auto.runtime._environment import Environment
from abm_auto.runtime._scenario import Scenario
from abm_auto.runtime._data_collector import DataCollector
from abm_auto.runtime._agent_list import AgentList
from abm_auto.runtime._config import Config
from abm_auto.runtime._simulator import Simulator
from abm_auto.runtime._learner import FeedforwardLearner  # learned-operator (ADR-013 W2 wall fix)
from abm_auto.runtime._population import MoranProcess  # population-dynamics operator (ADR-013 W4 harvest)
from abm_auto.runtime._rule_table import RuleTable  # reference-data operator (ADR-013 W3 harvest)
from abm_auto.runtime._payoff_game import PayoffGame  # game-theory operator (ADR-014 Phase 2 harvest)
from abm_auto.runtime._vital_dynamics import VitalDynamics  # variable-N birth/death (ADR-014 Phase 2 harvest)
from abm_auto.runtime import _topologies as topologies  # noqa: F401  exposed as `runtime.topologies`

__all__ = [
    # Core
    "Agent",
    "AgentList",
    "Model",
    "Environment",
    "DataCollector",
    "FeedforwardLearner",
    "MoranProcess",
    "RuleTable",
    "PayoffGame",
    "VitalDynamics",
    "Scenario",
    "Config",
    "Simulator",
    # Spatial
    "Grid",
    "GridAgent",
    # Network
    "Network",
    "NetworkAgent",
    "topologies",
    # Meta
    "RUNTIME_ENGINE",
]
