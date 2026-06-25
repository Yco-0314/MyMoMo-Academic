"""Dynamic flood evacuation over a time-varying raster and road network.

Built on the GIS platform layer: `FloodAgent` subclasses
`GISAgent`, `FloodModel` subclasses `GISModel` with an overridden per-tick `step`
(read the flood frame -> flooded edges -> strand on flooded edge -> plan/enter ->
move -> summary). `run_dynamic_flood_evacuation` keeps its signature and return
shape; behaviour is unchanged (the existing tests gate faithfulness). Third real
adapter on the platform.
"""
from __future__ import annotations

from math import isfinite
from numbers import Integral

import networkx as nx

from abm_auto.gis._coupling import flood_depth_per_edge
from abm_auto.gis._flood_model import _require_raster_timeline
from abm_auto.gis._platform import GISAgent, GISModel
from abm_auto.gis._routing_common import dijkstra_route


def _validate_flood_inputs(speed_m_per_tick, n_samples) -> tuple[float, int]:
    """Validate the numeric run params (mirrors _dynamic_congestion._validate_inputs).
    n_steps comes from the flood_timeline, so only speed + n_samples are validated here."""
    try:
        speed = float(speed_m_per_tick)
    except (TypeError, ValueError) as exc:
        raise ValueError("speed_m_per_tick must be positive") from exc
    if not isfinite(speed) or speed <= 0:
        raise ValueError("speed_m_per_tick must be positive")
    if isinstance(n_samples, bool) or not isinstance(n_samples, Integral) or n_samples <= 0:
        raise ValueError("n_samples must be a positive integer")
    return speed, int(n_samples)


class FloodAgent(GISAgent):
    """A node-starting moving agent under evolving flood. The model orchestrates
    the per-tick lifecycle, so the per-agent `step` is unused."""

    def __init__(self, agent_id, model, node):
        super().__init__(agent_id, model)
        self.node = node
        self.edge = None
        self.edge_progress_m = 0.0
        self.route = []
        self.arrived = False
        self.stranded = False
        self.stranded_reason = None
        self.reroutes = 0
        self.exposure_depth = 0.0
        self.arrival_t = None
        self.planned_once = False

    def step(self) -> None:
        pass


def _edge_key(u, v) -> tuple:
    return tuple(sorted((u, v)))


def _routable_graph(graph, flooded_edges: set) -> nx.Graph:
    routable = graph.copy()
    routable.remove_edges_from(flooded_edges)
    return routable


def _shortest_route(graph, start, safe_nodes: set) -> list:
    # Flood routes over the already-flood-pruned graph by raw edge length (no
    # congestion cost), so the default distance-weighted search is exactly right.
    # Flooded edges are removed from `graph` upstream (_routable_graph) before this.
    return dijkstra_route(graph, start, safe_nodes)


def _try_enter_next_edge(agent: FloodAgent, graph, flooded_edges: set) -> bool:
    if not agent.route:
        return False
    next_node = agent.route[0]
    if not graph.has_edge(agent.node, next_node):
        return False
    if _edge_key(agent.node, next_node) in flooded_edges:
        return False
    agent.edge = (agent.node, next_node)
    agent.edge_progress_m = 0.0
    return True


def _move_agent(agent: FloodAgent, graph, safe_nodes: set,
                speed_m_per_tick: float, t: int) -> None:
    u, v = agent.edge
    edge_length = float(graph.edges[u, v].get("length", 0.0))
    distance_left = edge_length - agent.edge_progress_m
    if speed_m_per_tick < distance_left:
        agent.edge_progress_m += speed_m_per_tick
        return

    agent.node = v
    agent.edge = None
    agent.edge_progress_m = 0.0
    if agent.route and agent.route[0] == v:
        agent.route.pop(0)
    if agent.node in safe_nodes:
        agent.arrived = True
        agent.arrival_t = t


def _agent_state(agent: FloodAgent) -> dict:
    return {
        "id": agent.id,
        "node": agent.node,
        "edge": agent.edge,
        "edge_progress_m": agent.edge_progress_m,
        "route": list(agent.route),
        "arrived": agent.arrived,
        "stranded": agent.stranded,
        "stranded_reason": agent.stranded_reason,
        "reroutes": agent.reroutes,
        "exposure_depth": agent.exposure_depth,
        "arrival_t": agent.arrival_t,
    }


class FloodModel(GISModel):
    """Dynamic flood evacuation on the platform. Overrides `step` with the
    per-tick lifecycle; the platform supplies GISModel/GISAgent + the AgentSet."""

    def __init__(self, geonet, flood_timeline, threshold, safe_nodes, agent_nodes,
                 speed_m_per_tick, n_samples, reroute):
        super().__init__(space=geonet, seed=0)
        self.geonet = geonet
        self.graph = geonet.graph
        self.flood_timeline = flood_timeline
        self.threshold = threshold
        self.safe_nodes = set(safe_nodes)
        self.speed = speed_m_per_tick
        self.n_samples = n_samples
        self.reroute = reroute
        self.total_reroutes = 0
        self.summaries = []
        for i, node in enumerate(agent_nodes):
            self.add_agent(FloodAgent(i, self, node))

    @property
    def agent_list(self) -> list:
        return list(self.agents)

    def step(self) -> None:
        t = self.t
        agents = self.agent_list
        graph = self.graph
        safe_nodes = self.safe_nodes
        flood = self.flood_timeline.at(t)
        depths = flood_depth_per_edge(self.geonet, flood, n_samples=self.n_samples)
        flooded_edges = {edge for edge, depth in depths.items() if depth > self.threshold}
        routable = _routable_graph(graph, flooded_edges)
        reroutes_this_step = 0

        for agent in agents:
            if agent.arrived or agent.stranded or agent.edge is None:
                continue
            depth = depths.get(_edge_key(*agent.edge), 0.0)
            if depth > self.threshold:
                agent.stranded = True
                agent.stranded_reason = "flooded_on_edge"
                agent.exposure_depth += depth

        for agent in agents:
            if agent.arrived or agent.stranded or agent.edge is not None:
                continue
            if agent.node in safe_nodes:
                agent.arrived = True
                agent.arrival_t = t
                continue

            # Reroute policy is flood-specific BY DESIGN (do not converge with the
            # congestion model's replan-every-tick): edge lengths are static here, so
            # a planned route stays optimal unless its next edge floods or vanishes.
            # Replan only "when blocked" — replanning every tick (the congestion
            # policy) would be wasted work with identical results.
            next_node = agent.route[0] if agent.route else None
            next_unavailable = (
                next_node is not None
                and (not graph.has_edge(agent.node, next_node)
                     or _edge_key(agent.node, next_node) in flooded_edges)
            )
            should_plan = False
            count_as_reroute = False

            if self.reroute:
                should_plan = not agent.route or next_unavailable
                count_as_reroute = bool(agent.route)
            elif not agent.planned_once:
                should_plan = True

            if should_plan:
                old_route = list(agent.route)
                new_route = _shortest_route(routable, agent.node, safe_nodes)
                agent.route = new_route
                agent.planned_once = True
                if count_as_reroute and new_route and new_route != old_route:
                    agent.reroutes += 1
                    reroutes_this_step += 1
                    self.total_reroutes += 1

            _try_enter_next_edge(agent, graph, flooded_edges)

        for agent in agents:
            if agent.arrived or agent.stranded or agent.edge is None:
                continue
            _move_agent(agent, graph, safe_nodes, self.speed, t)

        self.summaries.append({
            "t": t,
            "arrived": sum(1 for agent in agents if agent.arrived),
            "moving": sum(
                1 for agent in agents
                if agent.edge is not None and not agent.arrived and not agent.stranded
            ),
            "waiting": sum(
                1 for agent in agents
                if agent.edge is None and not agent.arrived and not agent.stranded
            ),
            "stranded": sum(1 for agent in agents if agent.stranded),
            "n_flooded_edges": len(flooded_edges),
            "reroutes_this_step": reroutes_this_step,
            "total_reroutes": self.total_reroutes,
        })
        self.t += 1

    def result(self) -> dict:
        agents = self.agent_list
        for agent in agents:
            if not agent.arrived and not agent.stranded:
                agent.stranded = True
                agent.stranded_reason = "not_arrived"

        arrival_times = [agent.arrival_t for agent in agents if agent.arrival_t is not None]
        moving = sum(
            1 for agent in agents
            if agent.edge is not None and not agent.arrived and not agent.stranded
        )
        return {
            "steps": self.summaries,
            "agents": [_agent_state(agent) for agent in agents],
            "n_steps": self.flood_timeline.n_steps,
            "n_agents": len(agents),
            "arrived": sum(1 for agent in agents if agent.arrived),
            "stranded": sum(1 for agent in agents if agent.stranded),
            "moving": moving,
            "total_reroutes": self.total_reroutes,
            "mean_arrival_t": (sum(arrival_times) / len(arrival_times)) if arrival_times else None,
            "max_exposure_depth": max((agent.exposure_depth for agent in agents), default=0.0),
        }


def run_dynamic_flood_evacuation(
    geonet,
    flood_timeline,
    threshold,
    safe_nodes,
    agent_nodes,
    speed_m_per_tick=100.0,
    n_samples=8,
    reroute=True,
) -> dict:
    """Move node-starting agents through a road graph as flood rasters evolve."""
    flood_timeline = _require_raster_timeline(flood_timeline)
    speed_m_per_tick, n_samples = _validate_flood_inputs(speed_m_per_tick, n_samples)

    model = FloodModel(
        geonet, flood_timeline, threshold, safe_nodes, agent_nodes,
        speed_m_per_tick, n_samples, reroute,
    )
    for _ in range(flood_timeline.n_steps):
        model.step()
    return model.result()
