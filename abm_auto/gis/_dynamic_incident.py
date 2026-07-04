"""Dynamic incident routing over a GeoNetwork road graph.

Agents move over a road graph while per-tick incident events close or reopen
edges. Routing is node-only and uses the shared deterministic Dijkstra over a
copy of the graph with active closures removed.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from numbers import Integral

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
from abm_auto.gis._platform import DataCollector, GISAgent, RunReporter, StagedGISModel
from abm_auto.gis._routing_common import dijkstra_route


class IncidentAgent(GISAgent):
    """A node-starting moving agent under active road-edge incidents."""

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
        self.arrival_t = None
        self.planned_once = False

    def step(self) -> None:
        pass

    def strand_if_closed_on_edge(self) -> None:
        if self.arrived or self.stranded or self.edge is None:
            return
        if edge_key(*self.edge) in self.model.closed_edges:
            self.stranded = True
            self.stranded_reason = "incident_on_edge"

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
            and (
                not model.graph.has_edge(self.node, next_node)
                or edge_key(self.node, next_node) in model.closed_edges
            )
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

        try_enter_next_edge(self, model.graph, model.closed_edges)

    def move_along_edge(self) -> None:
        if self.arrived or self.stranded or self.edge is None:
            return
        advance_on_edge(
            self, self.model.graph, self.model.safe_nodes, self.model.speed, self.model.t,
        )


def _validate_inputs(n_steps, speed_m_per_tick) -> tuple[int, float]:
    if isinstance(n_steps, bool) or not isinstance(n_steps, Integral) or n_steps <= 0:
        raise ValueError("n_steps must be a positive integer")
    try:
        speed = float(speed_m_per_tick)
    except (TypeError, ValueError) as exc:
        raise ValueError("speed_m_per_tick must be positive") from exc
    if not isfinite(speed) or speed <= 0:
        raise ValueError("speed_m_per_tick must be positive")
    return int(n_steps), speed


def _normalize_events(graph, incidents) -> dict:
    if incidents is None:
        raise ValueError("incidents must be event mappings")

    events_by_t = {}
    for event in incidents:
        if not isinstance(event, Mapping):
            raise ValueError("incident events must be mappings")

        t = event.get("t")
        if isinstance(t, bool) or not isinstance(t, Integral) or t < 0:
            raise ValueError("incident event t must be a non-negative integer")

        if "edge" not in event:
            raise ValueError("incident event edge is required")
        edge = event["edge"]
        try:
            u, v = edge
        except (TypeError, ValueError) as exc:
            raise ValueError("incident event edge must contain two nodes") from exc
        if not graph.has_edge(u, v):
            raise ValueError("incident event edge must exist in geonet.graph")

        closed = event.get("closed")
        if not isinstance(closed, bool):
            raise ValueError("incident event closed must be boolean")

        events_by_t.setdefault(int(t), []).append((edge_key(u, v), closed))
    return events_by_t


def _shortest_route(graph, start, safe_nodes: set) -> list:
    return dijkstra_route(graph, start, safe_nodes)


class IncidentRoutingModel(StagedGISModel):
    """Dynamic incident routing on the staged platform lifecycle."""

    stages = ("strand_if_closed_on_edge", "plan_or_enter", "move_along_edge")

    def __init__(
        self,
        geonet,
        safe_nodes,
        agent_nodes,
        incidents,
        speed_m_per_tick,
        reroute,
    ):
        super().__init__(space=geonet, seed=0)
        self.geonet = geonet
        self.graph = geonet.graph
        self.safe_nodes = set(safe_nodes)
        self.speed = speed_m_per_tick
        self.reroute = reroute
        self.events_by_t = incidents
        self.closed_edges = set()
        self.routable = self.graph
        self.reroutes_this_step = 0
        self.total_reroutes = 0
        self.reporter = DataCollector({
            "t": lambda m: m.t,
            "arrived": lambda m: movement_counts(m.agent_list)["arrived"],
            "moving": lambda m: movement_counts(m.agent_list)["moving"],
            "waiting": lambda m: movement_counts(m.agent_list)["waiting"],
            "stranded": lambda m: movement_counts(m.agent_list)["stranded"],
            "n_closed_edges": lambda m: len(m.closed_edges),
            "closed_edges": lambda m: list(sorted(m.closed_edges, key=repr)),
            "reroutes_this_step": lambda m: m.reroutes_this_step,
            "total_reroutes": lambda m: m.total_reroutes,
        })
        for i, node in enumerate(agent_nodes):
            self.add_agent(IncidentAgent(i, self, node))

    @property
    def agent_list(self) -> list:
        return list(self.agents)

    @property
    def summaries(self) -> list:
        return self.reporter.records

    def begin_step(self) -> None:
        for edge, closed in self.events_by_t.get(self.t, []):
            if closed:
                self.closed_edges.add(edge)
            else:
                self.closed_edges.discard(edge)
        self.routable = routable_graph(self.graph, self.closed_edges)
        self.reroutes_this_step = 0

    def result(self, n_steps: int) -> dict:
        agents = self.agent_list
        mark_not_arrived(agents)
        counts = movement_counts(agents)
        return RunReporter(self.reporter).report(
            peaks={"max_closed_edges": "n_closed_edges"},
            extra={
                "agents": [moving_agent_state(agent) for agent in agents],
                "n_steps": n_steps,
                "n_agents": len(agents),
                "arrived": counts["arrived"],
                "stranded": counts["stranded"],
                "moving": counts["moving"],
                "total_reroutes": self.total_reroutes,
                "mean_arrival_t": mean_arrival_t(agents),
            },
        )


def run_dynamic_incident_routing(
    geonet,
    safe_nodes,
    agent_nodes,
    incidents,
    n_steps=6,
    speed_m_per_tick=100.0,
    reroute=True,
) -> dict:
    """Move node-starting agents through a road graph as incidents close edges."""
    n_steps, speed_m_per_tick = _validate_inputs(n_steps, speed_m_per_tick)
    incidents = _normalize_events(geonet.graph, incidents)
    model = IncidentRoutingModel(
        geonet,
        safe_nodes,
        agent_nodes,
        incidents,
        speed_m_per_tick,
        reroute,
    )
    for _ in range(n_steps):
        model.step()
    return model.result(n_steps)
