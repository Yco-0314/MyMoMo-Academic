"""ABM Auto Runtime — standalone ``Model`` (ADR-009 Phase 4, Stage B).

No longer subclasses ``Melodie.Model``. Reimplements the model lifecycle
faithfully — the same contract the Simulator drives and generated/handcrafted
models rely on:

    Model(config, scenario, run_id_in_scenario) → _setup() [create() → setup()
    → each queued component's _setup()] → run()   (loop via iterator(period))

What it owns: ``__init__``, the ``create_*`` factories (agent_list / environment
/ grid / network / data_collector), ``iterator`` + the run-loop routine, and
``_setup``. Melodie machinery dropped: the sqlite ``create_db_conn``, the legacy
``create_agent_container``, ``table_generator`` (no corpus/codegen model uses
them). ``_visualizer_step`` is kept as a no-op so generated ``iterator`` loops
are unchanged.

Stage B keeps the (Stage-A) Melodie-wrapped Grid/Network/Agent — our Model
provides the duck-typed attributes they read (``config``, ``scenario``,
``agents``). Stage C un-wraps those, after which ``import Melodie`` leaves the
runtime entirely. Gated by the byte-diff engine oracle.

Key fix retained from earlier (Candidate 3): ``create_grid`` / ``create_network``
inject ``self.agents`` so ``get_neighbors()`` needs no agent_list argument.
"""
from __future__ import annotations

import random
from typing import List, Optional, Type, Union


class _ModelRunRoutine:
    """The run-loop iterator (mirrors Melodie's ``ModelRunRoutine``): yields the
    current step 0..period_num-1, advancing the visualizer (a no-op here)."""

    def __init__(self, max_step: int, model: "Model") -> None:
        self._current_step = -1
        self._max_step = max_step
        self.model: Optional["Model"] = model

    def __iter__(self):
        return self

    def __next__(self) -> int:
        if self._current_step >= self._max_step - 1:
            raise StopIteration
        self.model._visualizer_step(self._current_step)
        self._current_step += 1
        return self._current_step

    def __del__(self):
        self.model = None


class Model:
    """ABM Auto base model. Lifecycle: ``create()`` + ``setup()`` (overridden by
    the user), then ``run()``. The Simulator calls ``_setup()`` then ``run()``."""

    def __init__(
        self,
        config,
        scenario,
        run_id_in_scenario: int = 0,
        visualizer=None,
    ) -> None:
        self.scenario = scenario
        self.config = config
        self.environment = None
        self.data_collector = None
        self.table_generator = None
        self.run_id_in_scenario = run_id_in_scenario
        self.network = None
        self.visualizer = visualizer
        self.initialization_queue: List = []

    def __del__(self):
        self.visualizer = None

    # ── user hooks ───────────────────────────────────────────────────────────

    def create(self) -> None:
        """Create model components (agent lists, environment, grid/network,
        data collector). Overridden by the model."""
        pass

    def setup(self) -> None:
        """Establish initial state (after ``create()``). Overridden by the model."""
        pass

    def run(self) -> None:
        """The main simulation loop. Overridden by the model."""
        pass

    # ── component factories ──────────────────────────────────────────────────

    def create_agent_list(self, agent_class: Type):
        """An :class:`AbmAuto.AgentList` (ADR-009 Phase 3)."""
        from abm_auto.runtime._agent_list import AgentList

        return AgentList(agent_class, model=self)

    def create_environment(self, env_class: Type):
        env = env_class()
        env.model = self
        env.scenario = self.scenario
        self.initialization_queue.append(env)
        return env

    def create_grid(self, grid_cls: Optional[Type] = None, spot_cls: Optional[Type] = None):
        """Create a Grid (defaulting to ABM Auto's Grid), inject ``self.agents``
        so ``get_neighbors()`` resolves neighbours without a caller-supplied list.
        """
        from abm_auto.runtime._grid import Grid as _Grid

        if grid_cls is None:
            grid_cls = _Grid
        if spot_cls is None:
            # Stage B: our Grid still wraps Melodie's Grid, which needs a Spot.
            # Stage C replaces this with our own Spot.
            from MelodieInfra.core import Spot as spot_cls  # type: ignore
        grid = grid_cls(spot_cls, self.scenario)
        self.initialization_queue.append(grid)
        if getattr(self, "agents", None) is not None:
            grid._agent_list_ref = self.agents
        return grid

    def create_network(self, network_cls: Optional[Type] = None, edge_cls: Optional[Type] = None):
        """Create a Network (defaulting to ABM Auto's Network), inject
        ``self.agents`` + a scenario-seeded RNG for the topology callables."""
        from abm_auto.runtime._network import Network as _Network

        if network_cls is None:
            network_cls = _Network
        network = network_cls(model=self, edge_cls=edge_cls)
        self.initialization_queue.append(network)
        if getattr(self, "agents", None) is not None:
            network._agent_list_ref = self.agents
        network._rng = random.Random(int(getattr(self.scenario, "seed", 0)))
        return network

    def create_data_collector(self, data_collector_cls: Type):
        data_collector = data_collector_cls()
        data_collector.model = self
        data_collector.scenario = self.scenario
        data_collector.config = self.config
        self.initialization_queue.append(data_collector)
        return data_collector

    # ── run loop ─────────────────────────────────────────────────────────────

    def iterator(self, period_num: int) -> _ModelRunRoutine:
        return _ModelRunRoutine(period_num, self)

    def _visualizer_step(self, current_step: int) -> None:
        if (self.visualizer is not None) and (current_step > 0):
            self.visualizer.step(current_step)

    def init_visualize(self) -> None:
        """Hook for visualizer setup; overridden when needed."""
        pass

    # ── framework setup ──────────────────────────────────────────────────────

    def _setup(self) -> None:
        """Run ``create()``, ``setup()``, then every queued component's
        ``_setup()`` in registration order."""
        self.create()
        self.setup()
        for component in self.initialization_queue:
            component._setup()
