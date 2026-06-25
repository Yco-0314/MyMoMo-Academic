"""Dynamic congestion-aware routing over a GeoNetwork road graph.

Built on the GIS platform layer: `CongestionAgent` subclasses
`GISAgent`, `CongestionModel` subclasses `GISModel` with an overridden per-tick
`step` (the 6-phase order: costs -> plan/reroute -> enter -> load -> move ->
summary). `run_dynamic_congestion_routing` keeps its signature and return shape;
behaviour is unchanged (the existing tests gate faithfulness). This is the second
real adapter on the platform, alongside the contagion reference model.
"""
from __future__ import annotations

from math import isfinite
from numbers import Integral

from abm_auto.gis._platform import GISAgent, GISModel
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


def _edge_key(u, v) -> tuple:
    return tuple(sorted((u, v), key=repr))


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
        key = _edge_key(*agent.edge)
        loads[key] = loads.get(key, 0) + 1
    return loads


def _congestion_multiplier(load, congestion_alpha) -> float:
    return 1.0 + congestion_alpha * max(load - 1, 0)


def _congested_edge_costs(graph, previous_loads, congestion_alpha) -> dict:
    costs = {}
    for u, v, data in graph.edges(data=True):
        length = float(data.get("length", 1.0))
        load = previous_loads.get(_edge_key(u, v), 0)
        costs[_edge_key(u, v)] = length * _congestion_multiplier(load, congestion_alpha)
    return costs


def _shortest_route_by_cost(graph, start, safe_nodes, edge_costs) -> list:
    # Congestion routes by the *congested* edge cost (length x multiplier), falling
    # back to raw length for edges with no recorded cost. The search itself is the
    # shared deterministic Dijkstra (_routing_common); only the cost lookup differs.
    return dijkstra_route(
        graph, start, safe_nodes,
        edge_cost=lambda u, v, length: edge_costs.get(_edge_key(u, v), length),
    )


def _try_enter_next_edge(agent: CongestionAgent, graph) -> bool:
    if not agent.route:
        return False
    next_node = agent.route[0]
    if not graph.has_edge(agent.node, next_node):
        return False
    agent.edge = (agent.node, next_node)
    agent.edge_progress_m = 0.0
    return True


def _move_agent(
    agent: CongestionAgent,
    graph,
    safe_nodes: set,
    speed_m_per_tick: float,
    edge_loads: dict,
    congestion_alpha: float,
    t: int,
) -> None:
    u, v = agent.edge
    edge_length = float(graph.edges[u, v].get("length", 0.0))
    distance_left = edge_length - agent.edge_progress_m
    load = edge_loads.get(_edge_key(u, v), 1)
    speed = speed_m_per_tick / _congestion_multiplier(load, congestion_alpha)
    if speed < distance_left:
        agent.edge_progress_m += speed
        return

    agent.node = v
    agent.edge = None
    agent.edge_progress_m = 0.0
    if agent.route and agent.route[0] == v:
        agent.route.pop(0)
    if agent.node in safe_nodes:
        agent.arrived = True
        agent.arrival_t = t


def _agent_state(agent: CongestionAgent) -> dict:
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
        "arrival_t": agent.arrival_t,
    }


class CongestionModel(GISModel):
    """The dynamic congestion routing model on the platform. Overrides `step`
    with the 6-phase tick; the platform supplies the GISModel/GISAgent base and
    the AgentSet that holds the agents."""

    def __init__(self, geonet, safe_nodes, agent_nodes,
                 speed_m_per_tick, congestion_alpha, reroute):
        super().__init__(space=geonet, seed=0)
        self.graph = geonet.graph
        self.safe_nodes = set(safe_nodes)
        self.speed = speed_m_per_tick
        self.alpha = congestion_alpha
        self.reroute = reroute
        self.previous_loads = {}
        self.total_reroutes = 0
        self.max_edge_load = 0
        self.summaries = []
        for i, node in enumerate(agent_nodes):
            self.add_agent(CongestionAgent(i, self, node))

    @property
    def agent_list(self) -> list:
        return list(self.agents)

    def step(self) -> None:
        t = self.t
        agents = self.agent_list
        graph = self.graph
        safe_nodes = self.safe_nodes
        edge_costs = _congested_edge_costs(graph, self.previous_loads, self.alpha)
        mean_congested_cost = (
            sum(edge_costs.values()) / len(edge_costs) if edge_costs else 0.0
        )
        reroutes_this_step = 0

        for agent in agents:
            if agent.arrived or agent.stranded or agent.edge is not None:
                continue
            if agent.node in safe_nodes:
                agent.arrived = True
                agent.arrival_t = t
                continue

            # Reroute policy is congestion-specific BY DESIGN (do not converge with
            # the flood model's selective replan): edge costs change every tick as
            # loads shift, so a node-waiting agent must replan every tick to react to
            # congestion. Replanning only "when blocked" (the flood policy) would make
            # agents ignore congestion after their first plan — defeating the model.
            should_plan = False
            count_as_reroute = False
            if self.reroute:
                should_plan = True
                count_as_reroute = agent.planned_once
            elif not agent.planned_once:
                should_plan = True

            if should_plan:
                old_route = list(agent.route)
                agent.route = _shortest_route_by_cost(
                    graph, agent.node, safe_nodes, edge_costs,
                )
                if count_as_reroute and agent.route and agent.route != old_route:
                    agent.reroutes += 1
                    reroutes_this_step += 1
                    self.total_reroutes += 1
                agent.planned_once = True

        for agent in agents:
            if agent.arrived or agent.stranded or agent.edge is not None:
                continue
            _try_enter_next_edge(agent, graph)

        current_loads = _edge_loads(agents)
        if current_loads:
            self.max_edge_load = max(self.max_edge_load, max(current_loads.values()))

        for agent in agents:
            if agent.arrived or agent.stranded or agent.edge is None:
                continue
            _move_agent(agent, graph, safe_nodes, self.speed,
                        current_loads, self.alpha, t)

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
            "edge_loads": dict(sorted(current_loads.items(), key=lambda item: repr(item[0]))),
            "max_edge_load": max(current_loads.values(), default=0),
            "reroutes_this_step": reroutes_this_step,
            "total_reroutes": self.total_reroutes,
            "mean_congested_cost": mean_congested_cost,
        })
        self.previous_loads = current_loads
        self.t += 1

    def result(self, n_steps: int) -> dict:
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
            "n_steps": n_steps,
            "n_agents": len(agents),
            "arrived": sum(1 for agent in agents if agent.arrived),
            "stranded": sum(1 for agent in agents if agent.stranded),
            "moving": moving,
            "total_reroutes": self.total_reroutes,
            "mean_arrival_t": (
                sum(arrival_times) / len(arrival_times) if arrival_times else None
            ),
            "max_edge_load": self.max_edge_load,
        }


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
