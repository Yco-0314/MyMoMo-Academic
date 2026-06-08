"""ABM Auto Runtime — standalone ``AgentList`` (ADR-009 Phase 3).

A faithful, dependency-free reimplementation of ``Melodie.AgentList`` /
``MelodieInfra.core.agent_list.AgentList`` — same public API and semantics
(id assignment, ``init_agents`` scenario/model injection + ``agent.setup()``,
indexing, add/remove with reindex, ``params_df`` loading), with the three
MelodieInfra couplings dropped:

  - ``MelodieExceptions`` / ``show_prettified_warning`` → stdlib ``warnings`` +
    plain exceptions;
  - ``TableInterface`` → pandas directly (``params_df`` is a ``pd.DataFrame``);
  - the ``isinstance(agent, Melodie.Agent)`` guard → a duck-typed check (the
    object must carry an ``id``).

Verified by a byte-diff oracle: the Schelling handcrafted model produces an
identical output CSV with this AgentList swapped in for Melodie's (same seed).
"""
from __future__ import annotations

import random
import warnings
from typing import Any, Callable, Dict, List, Optional, Type


class _SeqIter:
    """Index-based iterator (mirrors Melodie's ``SeqIter``) — re-reads length
    each step so the list may be mutated mid-iteration without surprising the
    loop."""

    def __init__(self, seq: list) -> None:
        self._seq = seq
        self._i = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._i >= len(self._seq):
            raise StopIteration
        item = self._seq[self._i]
        self._i += 1
        return item


def _apply_params(agent: Any, params: Dict[str, Any]) -> None:
    """Set agent attributes from a params dict (Melodie ``Agent.set_params``
    is attribute assignment). Prefers the agent's own ``set_params`` if it
    has one, else falls back to ``setattr``."""
    setter = getattr(agent, "set_params", None)
    if callable(setter):
        setter(params)
    else:
        for k, v in params.items():
            setattr(agent, k, v)


class AgentList:
    """Typed container of agents, owned by a ``Model``. Drop-in for
    ``Melodie.AgentList``.

    The model calls ``create_agent_list(AgentClass)`` to get one, then
    ``setup_agents(n[, params_df])`` to populate it; environments iterate it
    (``for a in agents``), index it (``agents[i]``), and operators add/remove
    agents (variable-N dynamics). ``id`` values are auto-increment from 0.
    """

    def __init__(self, agent_class: "Type", model: "Any") -> None:
        self._id_offset = -1
        self.scenario = model.scenario
        self.agent_class = agent_class
        self.model = model
        self.indices: Dict[int, int] = {}
        self.agents: List[Any] = []
        self.initial_agent_num = 0

    # ── identity / containers ────────────────────────────────────────────────

    def new_id(self) -> int:
        """Auto-increment id, starting at 0."""
        self._id_offset += 1
        return self._id_offset

    def __repr__(self) -> str:
        return f"<AgentList {self.agents}>"

    def __len__(self) -> int:
        return len(self.agents)

    def __getitem__(self, item):
        return self.agents.__getitem__(item)

    def __iter__(self):
        return _SeqIter(self.agents)

    def all_agent_ids(self) -> List[int]:
        return [agent.id for agent in self]

    # ── setup / population ───────────────────────────────────────────────────

    def setup_agents(self, agents_num: int, params_df=None) -> None:
        """Create ``agents_num`` agents and (optionally) initialise their
        properties from a pandas DataFrame."""
        self.initial_agent_num = agents_num
        self.agents = self.init_agents()
        for i, agent in enumerate(self.agents):
            self._set_index(agent.id, i)
        if params_df is not None:
            self.set_properties(params_df)

    def init_agents(self) -> List[Any]:
        """Instantiate the agents, inject scenario + model, call ``setup()``."""
        agents = [self.agent_class(self.new_id()) for _ in range(self.initial_agent_num)]
        scenario = self.model.scenario
        for agent in agents:
            agent.scenario = scenario
            agent.model = self.model
            agent.setup()
        return agents

    def _set_index(self, agent_id: int, index: int) -> None:
        self.indices[agent_id] = index

    def _get_index(self, agent_id: int) -> int:
        return self.indices.get(agent_id, -1)

    def _setup(self) -> None:
        self.setup()

    def setup(self) -> None:
        """Override in a custom AgentList subclass. Default no-op."""
        pass

    # ── access ───────────────────────────────────────────────────────────────

    def get_agent(self, agent_id: int):
        """Agent with this id, or ``None``."""
        index = self._get_index(agent_id)
        return None if index == -1 else self.agents[index]

    def random_sample(self, sample_num: int) -> List[Any]:
        return random.sample(self.agents, sample_num)

    def filter(self, condition: Callable[[Any], bool]) -> List[Any]:
        return [agent for agent in self.agents if condition(agent)]

    def method_foreach(self, method_name: str, args: tuple) -> None:
        for agent in self.agents:
            getattr(agent, method_name)(*args)

    def vectorize(self, prop_name: str):
        if len(self.agents) == 0:
            return
        raise NotImplementedError

    # ── mutation (variable-N dynamics) ───────────────────────────────────────

    def add(self, agent=None, params: Optional[Dict] = None):
        return self._add(agent, params)

    def _add(self, agent, params):
        new_id = self.new_id()
        if agent is None:
            agent = self.agent_class(new_id)
        elif not hasattr(agent, "id"):
            raise TypeError(f"add() expected an agent (with .id), got {type(agent)!r}")
        agent.scenario = self.model.scenario
        agent.model = self.model
        agent.setup()
        if params is not None:
            if not isinstance(params, dict):
                raise TypeError("params must be a dict")
            if params.get("id") is not None:
                warnings.warn(
                    f"agent 'id' {agent.id} in params is overridden by auto id {new_id}"
                )
            _apply_params(agent, params)
        agent.id = new_id
        self.agents.append(agent)
        self._set_index(agent.id, len(self.agents) - 1)
        return agent

    def remove(self, agent) -> None:
        index = self._get_index(agent.id)
        self.agents.pop(index)
        for i, a in enumerate(self.agents):
            self._set_index(a.id, i)

    # ── dataframe I/O ────────────────────────────────────────────────────────

    def set_properties(self, props_df) -> None:
        """Initialise agent properties from a DataFrame (one row per agent).
        Filters by ``id_scenario`` if that column is present; matches rows to
        agents by ``id`` if present, else positionally."""
        self._set_properties(props_df)
        self.agents.sort(key=lambda agent: agent.id)

    def _set_properties(self, props_df) -> None:
        df = props_df
        if "id_scenario" in df.columns:
            df = df[df["id_scenario"] == self.scenario.id]
        param_names = [c for c in df.columns if c != "id_scenario"]
        rows = df.to_dict("records")
        if "id" in param_names:
            for row in rows:
                params = {k: row[k] for k in param_names}
                agent = self.get_agent(params["id"])
                if agent is None:
                    agent = self.add()
                _apply_params(agent, params)
        else:
            assert len(self) == len(rows), (len(self), len(rows))
            for i, row in enumerate(rows):
                _apply_params(self.agents[i], {k: row[k] for k in param_names})

    def to_list(self, column_names: List[str]) -> List[Dict]:
        if len(self.agents) == 0:
            raise RuntimeError("AgentList is empty")
        agent0 = self.agents[0]
        for column_name in column_names:
            if not hasattr(agent0, column_name):
                raise AttributeError(f"agent property {column_name!r} does not exist")
        data_list = []
        for agent in self.agents:
            d = {k: getattr(agent, k) for k in column_names}
            d["id"] = agent.id
            data_list.append(d)
        return data_list

    def to_dataframe(self, column_names: List[str] = None):
        """Dump agent properties to a DataFrame (called by data collectors)."""
        import pandas as pd

        df = pd.DataFrame(self.to_list(column_names))
        df["id"] = df["id"].astype(int)
        return df


__all__ = ["AgentList"]
