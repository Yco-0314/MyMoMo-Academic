"""Dynamic flood evacuation over a time-varying raster and road network.

Migrated onto the GIS platform layer (ADR-020): `FloodAgent` subclasses
`GISAgent`, `FloodModel` subclasses `StagedGISModel`, and the platform owns the
staged lifecycle (read flood frame -> flooded edges -> strand on flooded edge ->
plan/enter -> move -> summary). `run_dynamic_flood_evacuation` keeps its
signature and return shape; behaviour is unchanged (the existing tests gate
faithfulness). Third real adapter on the platform.
"""
from __future__ import annotations

from math import isfinite
from numbers import Integral

from abm_auto.gis._coupling import flood_depth_per_edge
from abm_auto.gis._dynamic_routing_lifecycle import (
    advance_on_edge,
    edge_key,
    mark_not_arrived,
    mean_arrival_t,
    movement_counts,
    moving_agent_state,
    record_reroute,
    routable_graph,
    try_enter_next_edge,
)
from abm_auto.gis._flood_model import _require_raster_timeline
from abm_auto.gis._platform import DataCollector, GISAgent, StagedGISModel
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

    def strand_if_flooded_on_edge(self) -> None:
        if self.arrived or self.stranded or self.edge is None:
            return
        model = self.model
        depth = model.depths.get(edge_key(*self.edge), 0.0)
        if depth > model.threshold:
            self.stranded = True
            self.stranded_reason = "flooded_on_edge"
            self.exposure_depth += depth

    def plan_or_enter(self) -> None:
        model = self.model
        if self.arrived or self.stranded or self.edge is not None:
            return
        if self.node in model.safe_nodes:
            self.arrived = True
            self.arrival_t = model.t
            return

        next_node = self.route[0] if self.route else None
        next_unavailable = (
            next_node is not None
            and (not model.graph.has_edge(self.node, next_node)
                 or edge_key(self.node, next_node) in model.flooded_edges)
        )
        should_plan = False
        count_as_reroute = False

        if model.reroute:
            should_plan = not self.route or next_unavailable
            count_as_reroute = bool(self.route)
        elif not self.planned_once:
            should_plan = True

        if should_plan:
            old_route = list(self.route)
            new_route = _shortest_route(model.routable, self.node, model.safe_nodes)
            self.route = new_route
            self.planned_once = True
            record_reroute(self, model, old_route, new_route, count_as_reroute)

        try_enter_next_edge(self, model.graph, model.flooded_edges)

    def move_along_edge(self) -> None:
        if self.arrived or self.stranded or self.edge is None:
            return
        model = self.model
        advance_on_edge(self, model.graph, model.safe_nodes, model.speed, model.t)


def _shortest_route(graph, start, safe_nodes: set) -> list:
    # Flood routes over the already-flood-pruned graph by raw edge length (no
    # congestion cost), so the default distance-weighted search is exactly right.
    # Flooded edges are removed from `graph` upstream by `routable_graph`.
    return dijkstra_route(graph, start, safe_nodes)


class FloodModel(StagedGISModel):
    """Dynamic flood evacuation on the staged platform lifecycle."""

    stages = (
        "strand_if_flooded_on_edge",
        "plan_or_enter",
        "move_along_edge",
    )

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
        self.reroutes_this_step = 0
        self.depths = {}
        self.flooded_edges = set()
        self.routable = self.graph
        self.reporter = DataCollector({
            "t": lambda m: m.t,
            "arrived": lambda m: movement_counts(m.agent_list)["arrived"],
            "moving": lambda m: movement_counts(m.agent_list)["moving"],
            "waiting": lambda m: movement_counts(m.agent_list)["waiting"],
            "stranded": lambda m: movement_counts(m.agent_list)["stranded"],
            "n_flooded_edges": lambda m: len(m.flooded_edges),
            "reroutes_this_step": lambda m: m.reroutes_this_step,
            "total_reroutes": lambda m: m.total_reroutes,
        })
        for i, node in enumerate(agent_nodes):
            self.add_agent(FloodAgent(i, self, node))

    @property
    def agent_list(self) -> list:
        return list(self.agents)

    @property
    def summaries(self) -> list:
        return self.reporter.records

    def begin_step(self) -> None:
        t = self.t
        flood = self.flood_timeline.at(t)
        raw_depths = flood_depth_per_edge(self.geonet, flood, n_samples=self.n_samples)
        self.depths = {edge_key(*edge): depth for edge, depth in raw_depths.items()}
        self.flooded_edges = {
            edge for edge, depth in self.depths.items() if depth > self.threshold
        }
        self.routable = routable_graph(self.graph, self.flooded_edges)
        self.reroutes_this_step = 0

    def result(self) -> dict:
        agents = self.agent_list
        mark_not_arrived(agents)
        counts = movement_counts(agents)
        return {
            "steps": self.summaries,
            "agents": [
                moving_agent_state(agent, extra={"exposure_depth": agent.exposure_depth})
                for agent in agents
            ],
            "n_steps": self.flood_timeline.n_steps,
            "n_agents": len(agents),
            "arrived": counts["arrived"],
            "stranded": counts["stranded"],
            "moving": counts["moving"],
            "total_reroutes": self.total_reroutes,
            "mean_arrival_t": mean_arrival_t(agents),
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
