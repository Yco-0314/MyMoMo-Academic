"""Dynamic congestion-aware routing over a GeoNetwork road graph.

Migrated onto the GIS platform layer (ADR-020): `CongestionAgent` subclasses
`GISAgent`, `CongestionModel` subclasses `StagedGISModel`, and the platform owns
the staged lifecycle (costs -> plan/reroute -> enter -> load -> move -> summary).
`run_dynamic_congestion_routing` keeps its signature and return shape; behaviour
is unchanged (the existing tests gate faithfulness). This is the second real
adapter on the platform, alongside the contagion reference model.
"""
from __future__ import annotations

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
    try_enter_next_edge,
)
from abm_auto.gis._platform import DataCollector, GISAgent, RunReporter, StagedGISModel
from abm_auto.gis._routing_common import dijkstra_route


class CongestionAgent(GISAgent):
    """A node-starting moving agent. The model orchestrates the 6-phase tick, so
    the per-agent `step` is unused (non-default tick order lives on the model)."""

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

    def plan_or_arrive(self) -> None:
        model = self.model
        if self.arrived or self.stranded or self.edge is not None:
            return
        if self.node in model.safe_nodes:
            self.arrived = True
            self.arrival_t = model.t
            return

        should_plan = False
        count_as_reroute = False
        if model.reroute:
            should_plan = True
            count_as_reroute = self.planned_once
        elif not self.planned_once:
            should_plan = True

        if should_plan:
            old_route = list(self.route)
            self.route = _shortest_route_by_cost(
                model.graph, self.node, model.safe_nodes, model.edge_costs,
            )
            record_reroute(self, model, old_route, self.route, count_as_reroute)
            self.planned_once = True

    def enter_next_edge(self) -> None:
        if self.arrived or self.stranded or self.edge is not None:
            return
        try_enter_next_edge(self, self.model.graph)

    def move_along_edge(self) -> None:
        if self.arrived or self.stranded or self.edge is None:
            return
        model = self.model
        load = model.current_loads.get(edge_key(*self.edge), 1)
        distance = model.speed / _congestion_multiplier(load, model.alpha)
        advance_on_edge(self, model.graph, model.safe_nodes, distance, model.t)


def _edge_key(u, v) -> tuple:
    return edge_key(u, v)


def _validate_inputs(n_steps, speed_m_per_tick, congestion_alpha) -> tuple[int, float, float]:
    if isinstance(n_steps, bool) or not isinstance(n_steps, Integral) or n_steps <= 0:
        raise ValueError("n_steps must be a positive integer")
    try:
        speed = float(speed_m_per_tick)
    except (TypeError, ValueError) as exc:
        raise ValueError("speed_m_per_tick must be positive") from exc
    if not isfinite(speed) or speed <= 0:
        raise ValueError("speed_m_per_tick must be positive")
    try:
        alpha = float(congestion_alpha)
    except (TypeError, ValueError) as exc:
        raise ValueError("congestion_alpha must be non-negative") from exc
    if not isfinite(alpha) or alpha < 0:
        raise ValueError("congestion_alpha must be non-negative")
    return int(n_steps), speed, alpha


def _edge_loads(agents) -> dict:
    loads = {}
    for agent in agents:
        if agent.arrived or agent.stranded or agent.edge is None:
            continue
        key = edge_key(*agent.edge)
        loads[key] = loads.get(key, 0) + 1
    return loads


def _congestion_multiplier(load, congestion_alpha) -> float:
    return 1.0 + congestion_alpha * max(load - 1, 0)


def _congested_edge_costs(graph, previous_loads, congestion_alpha) -> dict:
    costs = {}
    for u, v, data in graph.edges(data=True):
        length = float(data.get("length", 1.0))
        load = previous_loads.get(edge_key(u, v), 0)
        costs[edge_key(u, v)] = length * _congestion_multiplier(load, congestion_alpha)
    return costs


def _shortest_route_by_cost(graph, start, safe_nodes, edge_costs) -> list:
    # Congestion routes by the *congested* edge cost (length x multiplier), falling
    # back to raw length for edges with no recorded cost. The search itself is the
    # shared deterministic Dijkstra (_routing_common); only the cost lookup differs.
    return dijkstra_route(
        graph, start, safe_nodes,
        edge_cost=lambda u, v, length: edge_costs.get(edge_key(u, v), length),
    )


class CongestionModel(StagedGISModel):
    """The dynamic congestion routing model on the staged platform lifecycle."""

    stages = ("plan_or_arrive", "enter_next_edge", "move_along_edge")

    def __init__(self, geonet, safe_nodes, agent_nodes,
                 speed_m_per_tick, congestion_alpha, reroute):
        super().__init__(space=geonet, seed=0)
        self.graph = geonet.graph
        self.safe_nodes = set(safe_nodes)
        self.speed = speed_m_per_tick
        self.alpha = congestion_alpha
        self.reroute = reroute
        self.previous_loads = {}
        self.edge_costs = {}
        self.current_loads = {}
        self.reroutes_this_step = 0
        self.mean_congested_cost = 0.0
        self.total_reroutes = 0
        self.reporter = DataCollector({
            "t": lambda m: m.t,
            "arrived": lambda m: movement_counts(m.agent_list)["arrived"],
            "moving": lambda m: movement_counts(m.agent_list)["moving"],
            "waiting": lambda m: movement_counts(m.agent_list)["waiting"],
            "stranded": lambda m: movement_counts(m.agent_list)["stranded"],
            "edge_loads": lambda m: dict(
                sorted(m.current_loads.items(), key=lambda item: repr(item[0]))
            ),
            "max_edge_load": lambda m: max(m.current_loads.values(), default=0),
            "reroutes_this_step": lambda m: m.reroutes_this_step,
            "total_reroutes": lambda m: m.total_reroutes,
            "mean_congested_cost": lambda m: m.mean_congested_cost,
        })
        for i, node in enumerate(agent_nodes):
            self.add_agent(CongestionAgent(i, self, node))

    @property
    def agent_list(self) -> list:
        return list(self.agents)

    @property
    def summaries(self) -> list:
        return self.reporter.records

    def begin_step(self) -> None:
        self.edge_costs = _congested_edge_costs(
            self.graph, self.previous_loads, self.alpha,
        )
        self.mean_congested_cost = (
            sum(self.edge_costs.values()) / len(self.edge_costs)
            if self.edge_costs else 0.0
        )
        self.reroutes_this_step = 0

    def after_stage(self, stage: str) -> None:
        if stage != "enter_next_edge":
            return
        self.current_loads = _edge_loads(self.agent_list)

    def end_step(self) -> None:
        self.previous_loads = self.current_loads

    def result(self, n_steps: int) -> dict:
        agents = self.agent_list
        mark_not_arrived(agents)
        counts = movement_counts(agents)
        # The run summary flows through the platform RunReporter: the per-tick
        # `steps` block and the peak `max_edge_load` come from the collected
        # series; run-level rosters/counters pass through as `extra`.
        return RunReporter(self.reporter).report(
            peaks={"max_edge_load": "max_edge_load"},
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


def run_dynamic_congestion_routing(
    geonet,
    safe_nodes,
    agent_nodes,
    n_steps=6,
    speed_m_per_tick=100.0,
    congestion_alpha=2.0,
    reroute=True,
) -> dict:
    """Move node-starting agents through a road graph with dynamic congestion costs."""
    n_steps, speed_m_per_tick, congestion_alpha = _validate_inputs(
        n_steps, speed_m_per_tick, congestion_alpha,
    )
    model = CongestionModel(
        geonet, safe_nodes, agent_nodes,
        speed_m_per_tick, congestion_alpha, reroute,
    )
    for _ in range(n_steps):
        model.step()
    return model.result(n_steps)
