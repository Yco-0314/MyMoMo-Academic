"""ABM Auto Runtime — graph-coupled ``Network`` + ``Edge``.

A network couples agents by an explicit adjacency graph. Agents are the nodes
themselves (live ``NetworkAgent`` objects), so neighbour queries return objects
with no id-to-object lookup.

Design notes:

* **Nodes are agent objects.** Adjacency is ``dict[agent -> list[agent]]``;
  neighbour order is the order edges were added. (Identity-hashable agents make
  this safe as dict keys.)
* **Edges may carry properties.** An ``Edge`` records its endpoints plus an
  optional property bag; edges are indexed by the ordered ``(source, target)``
  pair so ``get_edge`` / ``get_node_edges`` stay O(1) / O(deg).
* **Graph construction is a seam.** ``setup_agent_connections`` takes a
  ``Topology`` callable ``(n, rng) -> nx.Graph`` and an injected, seedable
  ``_rng``, so the wiring (Erdős–Rényi, small-world, scale-free, clustered, …)
  is chosen by the caller and is reproducible.
* Visualisation layout helpers are kept (lazy ``networkx``); they project the
  object graph onto ``(category, id)`` keys for GEXF and are unused on the
  non-visual run path.
"""
from __future__ import annotations

import os
import random
from typing import Any, Dict, List, Optional, Tuple, Type

from abm_auto.runtime._agent import NetworkAgent


class Edge:
    """A link between two agents, optionally carrying named properties."""

    def __init__(self, source, target, **properties) -> None:
        self.source = source
        self.target = target
        self.properties: Dict[str, Any] = dict(properties)
        self.setup()
        self.post_setup()

    def setup(self) -> None:
        pass

    def post_setup(self) -> None:
        for prop_name, prop_value in self.properties.items():
            setattr(self, prop_name, prop_value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.source!r} --> {self.target!r}>"


class Network:
    """Graph linking agents. Nodes are agent objects; adjacency and edge records
    are kept in parallel so neighbour and edge queries are both cheap."""

    def __init__(self, model=None, edge_cls: Optional[Type[Edge]] = None,
                 directed: bool = False, name: str = "network") -> None:
        self.model = model
        self.directed = directed
        self.edge_cls: Type[Edge] = edge_cls if edge_cls is not None else Edge
        self._neighbors: Dict[Any, List[Any]] = {}        # agent → neighbour agents (ordered)
        self._edges: Dict[Tuple[Any, Any], Edge] = {}     # (source, target) → Edge
        self.agent_categories: Dict[int, Any] = {}        # category → agent_list (registry)
        self._rng: Optional[random.Random] = None
        # Back-compat hook: Model.create_network may assign this; the redesigned
        # network stores agent objects directly, so it is never read here.
        self._agent_list_ref: Optional[Any] = None
        # Visualisation only (unused on the non-visual path):
        self.layout_file = os.path.join(model.config.visualizer_tmpdir, name + "_layout.gexf")
        self.layout: dict = {}
        self._layout_creator = lambda G: __import__("networkx").spring_layout(G)
        self.setup()

    def _setup(self) -> None:
        self.setup()

    def setup(self) -> None:
        pass

    # ── nodes ─────────────────────────────────────────────────────────────────

    def add_agent(self, agent) -> None:
        assert isinstance(agent, NetworkAgent)
        agent.set_category()
        agent._set_network(self)
        self._neighbors.setdefault(agent, [])

    def remove_agent(self, agent) -> None:
        assert hasattr(agent, "category")
        for neighbor in self._neighbors.pop(agent, []):
            others = self._neighbors.get(neighbor)
            if others and agent in others:
                others.remove(agent)
            self._edges.pop((agent, neighbor), None)
            self._edges.pop((neighbor, agent), None)

    def all_agents(self):
        return list(self._neighbors.keys())

    # ── edges ─────────────────────────────────────────────────────────────────

    def add_edge(self, source, target, edge: Edge) -> None:
        self._neighbors.setdefault(source, []).append(target)
        self._edges[(source, target)] = edge
        if not self.directed:
            self._neighbors.setdefault(target, []).append(source)
            self._edges[(target, source)] = edge

    def create_edge(self, source, target, **edge_properties) -> None:
        assert source in self._neighbors, "source agent is not a node of this network"
        assert target in self._neighbors, "target agent is not a node of this network"
        self.add_edge(source, target, self.edge_cls(source, target, **edge_properties))

    def get_edge(self, source, target) -> Edge:
        return self._edges[(source, target)]

    def remove_edge(self, source, target) -> None:
        self._edges.pop((source, target), None)
        if target in self._neighbors.get(source, []):
            self._neighbors[source].remove(target)
        if not self.directed:
            self._edges.pop((target, source), None)
            if source in self._neighbors.get(target, []):
                self._neighbors[target].remove(source)

    def get_node_edges(self, agent) -> List[Edge]:
        assert isinstance(agent, NetworkAgent)
        return [self._edges[(agent, n)] for n in self._neighbors.get(agent, [])
                if (agent, n) in self._edges]

    # ── graph construction seam ───────────────────────────────────────────────

    def setup_agent_connections(self, agent_lists: List[Any], topology) -> None:
        """Build the network from a Topology callable ``(n, rng) -> nx.Graph``.

        Integer graph nodes ``0..n-1`` map to agents in the order they appear
        across ``agent_lists``; every graph edge becomes an undirected link.
        """
        assert isinstance(agent_lists, list)
        node_id_to_agent: Dict[int, Any] = {}
        node_id = 0
        for agent_list in agent_lists:
            if len(agent_list) > 0:
                agent_list[0].set_category()
                self.agent_categories[agent_list[0].category] = agent_list
            for agent in agent_list:
                self.add_agent(agent)
                node_id_to_agent[node_id] = agent
                node_id += 1

        rng = self._rng if self._rng is not None else random.Random()
        g = topology(len(self._neighbors), rng)
        for src_idx, dst_idx in g.edges:
            source = node_id_to_agent[src_idx]
            target = node_id_to_agent[dst_idx]
            self.add_edge(source, target, self.edge_cls(source, target))
        self._nx_edges = list(g.edges)

    # ── neighbours (returns live agent objects) ───────────────────────────────

    def get_neighbors(self, agent, agent_list: Any = None, return_agents: bool = True):
        """Agents adjacent to *agent*.

        Returns live ``NetworkAgent`` objects (nodes are objects, so there is no
        lookup step). ``return_agents=False`` yields raw ``(category, id)`` tuples
        instead. ``agent_list`` is accepted for backward compatibility and ignored.
        """
        assert hasattr(agent, "category")
        neighbors = self._neighbors.get(agent, [])
        if return_agents:
            return list(neighbors)
        return [(n.category, n.id) for n in neighbors]

    def _get_neighbor_positions(self, agent_id: int, category: int):
        """Back-compat: raw ``(category, id)`` tuples of a node's neighbours."""
        for agent, neighbors in self._neighbors.items():
            if agent.id == agent_id and agent.category == category:
                return [(n.category, n.id) for n in neighbors]
        return []

    # ── layout (visualization only; unused on the non-visual path) ────────────

    def setup_layout_creator(self, layout_creator) -> None:
        self._layout_creator = layout_creator

    def update_layout(self) -> None:
        import ast

        import networkx as nx
        import numpy as np

        if os.path.exists(self.layout_file):
            try:
                G = nx.read_gexf(self.layout_file, node_type=ast.literal_eval)
                self.layout = {n: np.array([G.nodes[n]["viz"]["position"]["x"],
                                            G.nodes[n]["viz"]["position"]["y"]]) for n in G.nodes}
                return
            except Exception:
                pass
        g = nx.DiGraph()
        for agent, neighbors in self._neighbors.items():
            for neighbor in neighbors:
                g.add_edge((agent.category, agent.id), (neighbor.category, neighbor.id))
        layout = self._layout_creator(g)
        for node, pos in layout.items():
            g.nodes[node]["viz"] = {"position": {"x": pos[0], "y": pos[1], "z": 0}}
        nx.write_gexf(g, self.layout_file)
        self.layout = layout

    def get_position(self, agent_category: int, agent_id: int):
        if (agent_category, agent_id) not in self.layout:
            self.update_layout()
        return self.layout[(agent_category, agent_id)] * 1000


__all__ = ["Network", "Edge"]
