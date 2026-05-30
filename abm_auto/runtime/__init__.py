"""
ABM Auto Runtime — simulation engine.

All generated model code imports from here::

    from abm_auto.runtime import Agent, Model, Grid, ...

**Architecture**
    Custom wrapper and standalone classes in ``abm_auto/runtime/`` fix known
    MyMoMo Runtime gotchas and provide a cleaner research-oriented API.  MyMoMo Runtime
    handles the underlying simulation mechanics (CSV loading, iteration, output
    collection) where we have not yet replaced it.

**Engine replacement contract**
    To swap the underlying simulation engine, update ONLY this file.
    Everything else (templates, prompts, generated model code) remains unchanged.

**Exposed surface**
    Agent, AgentList, Model, Environment, DataCollector, Scenario, Config,
    Simulator, Grid, GridAgent, Network, NetworkAgent, Calibrator, Trainer

**Key improvements over raw MyMoMo Runtime**
    - Agent._safe_attr(name, default): prevents setup() from overwriting CSV values
    - GridAgent.set_category(): default implementation (category=0), no more NotImplementedError
    - NetworkAgent.set_category(): same default
    - Model.create_grid(): injects self.agents → get_neighbors() needs no agent_list arg
    - Model.create_network(): same injection for networks
    - Grid.get_neighbors(agent): returns Agent objects, agent_list auto-resolved
    - Grid.width / Grid.height: public properties
    - Network.get_neighbors(agent): returns Agent objects, agent_list auto-resolved
    - Environment: standalone (no Melodie import)

**Route C progress**
    Standalone (no Melodie import): Agent wrappers, Grid, Network, Model, Environment
    Still delegated to MyMoMo Runtime: AgentList, DataCollector, Scenario, Config, Simulator,
                                Calibrator, Trainer
"""

try:
    import Melodie as _melodie_pkg
    _melodie_version = getattr(_melodie_pkg, "__version__", "unknown")
    RUNTIME_ENGINE: str = f"ABM Auto Runtime (MyMoMo Runtime {_melodie_version})"
except Exception:
    RUNTIME_ENGINE = "ABM Auto Runtime"

# ── Custom classes (fix gotchas, extend API, or fully standalone) ─────────────

from abm_auto.runtime._agent import Agent, GridAgent, NetworkAgent
from abm_auto.runtime._grid import Grid
from abm_auto.runtime._network import Network
from abm_auto.runtime._model import Model
from abm_auto.runtime._environment import Environment
from abm_auto.runtime._scenario import Scenario  # standalone (ADR-009 Phase 1)
from abm_auto.runtime._data_collector import DataCollector  # standalone (ADR-009 Phase 2)
from abm_auto.runtime import _topologies as topologies  # noqa: F401  exposed as `runtime.topologies`

# ── Still delegated to MyMoMo Runtime (complex CSV/DB machinery) ────────────────────

from Melodie import (
    AgentList,
    Config,
    Simulator,
    Calibrator,
    Trainer,
)

__all__ = [
    # Core
    "Agent",
    "AgentList",
    "Model",
    "Environment",
    "DataCollector",
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
    # Optimization
    "Calibrator",
    "Trainer",
    # Meta
    "RUNTIME_ENGINE",
]
