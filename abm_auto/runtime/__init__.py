"""
ABM Auto Runtime — simulation engine.

All generated model code imports from here::

    from abm_auto.runtime import Agent, Model, Grid, ...

**Architecture**
    A fully self-developed engine (ADR-009 complete). Every class here is
    standalone Python — Agent/AgentList/Grid/Network/Spot/Edge, Model + the
    Simulator/Config/DataLoader orchestrator, Scenario, DataCollector, and the
    library operators. There is **no Melodie dependency** anywhere in the package
    (the engine was decommissioned in five oracle-gated steps; the original
    Melodie-delegated implementation is gone).

**Exposed surface**
    Agent, AgentList, Model, Environment, DataCollector, Scenario, Config,
    Simulator, Grid, GridAgent, Network, NetworkAgent, topologies, + operators.

**Design notes**
    - Agent._safe_attr(name, default): keeps CSV-loaded values through setup()
    - GridAgent/NetworkAgent.set_category(): default category 0 (single-type)
    - Model.create_grid()/create_network(): inject self.agents so get_neighbors()
      needs no agent_list arg; Grid.width/height are properties
    - Grid/Network.get_neighbors(agent): return Agent objects, auto-resolved
    - byte-for-byte equivalence to the former engine is pinned by
      ``engine_oracle.py`` over the handcrafted corpus.
"""

# ADR-009 complete: the runtime no longer imports Melodie anywhere.
RUNTIME_ENGINE: str = "ABM Auto Runtime"

# ── Custom classes (fix gotchas, extend API, or fully standalone) ─────────────

from abm_auto.runtime._agent import Agent, GridAgent, NetworkAgent
from abm_auto.runtime._grid import Grid
from abm_auto.runtime._network import Network
from abm_auto.runtime._model import Model
from abm_auto.runtime._environment import Environment
from abm_auto.runtime._scenario import Scenario  # standalone (ADR-009 Phase 1)
from abm_auto.runtime._data_collector import DataCollector  # standalone (ADR-009 Phase 2)
from abm_auto.runtime._agent_list import AgentList  # standalone (ADR-009 Phase 3)
from abm_auto.runtime._config import Config  # standalone (ADR-009 Phase 4, Stage A)
from abm_auto.runtime._simulator import Simulator  # standalone (ADR-009 Phase 4, Stage A)
from abm_auto.runtime._learner import FeedforwardLearner  # learned-operator (ADR-013 W2 wall fix)
from abm_auto.runtime._population import MoranProcess  # population-dynamics operator (ADR-013 W4 harvest)
from abm_auto.runtime._rule_table import RuleTable  # reference-data operator (ADR-013 W3 harvest)
from abm_auto.runtime._payoff_game import PayoffGame  # game-theory operator (ADR-014 Phase 2 harvest)
from abm_auto.runtime._vital_dynamics import VitalDynamics  # variable-N birth/death (ADR-014 Phase 2 harvest)
from abm_auto.runtime import _topologies as topologies  # noqa: F401  exposed as `runtime.topologies`

# ADR-009 complete — no Melodie import remains; every export above is standalone.

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
