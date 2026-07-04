"""Shared private mechanics for dynamic moving-agent routing adapters."""
from __future__ import annotations


def edge_key(u, v) -> tuple:
    return tuple(sorted((u, v), key=repr))


def routable_graph(graph, blocked_edges: set):
    routable = graph.copy()
    routable.remove_edges_from(blocked_edges)
    return routable


def try_enter_next_edge(agent, graph, blocked_edges=()) -> bool:
    blocked = set(blocked_edges)
    if not agent.route:
        return False
    next_node = agent.route[0]
    if not graph.has_edge(agent.node, next_node):
        return False
    if edge_key(agent.node, next_node) in blocked:
        return False
    agent.edge = (agent.node, next_node)
    agent.edge_progress_m = 0.0
    return True


def advance_on_edge(agent, graph, safe_nodes: set, distance_m: float, t: int) -> None:
    u, v = agent.edge
    edge_length = float(graph.edges[u, v].get("length", 0.0))
    distance_left = edge_length - agent.edge_progress_m
    if distance_m < distance_left:
        agent.edge_progress_m += distance_m
        return

    agent.node = v
    agent.edge = None
    agent.edge_progress_m = 0.0
    if agent.route and agent.route[0] == v:
        agent.route.pop(0)
    if agent.node in safe_nodes:
        agent.arrived = True
        agent.arrival_t = t


def record_reroute(agent, model, old_route: list, new_route: list, count_as_reroute: bool) -> None:
    if count_as_reroute and new_route and new_route != old_route:
        agent.reroutes += 1
        model.reroutes_this_step += 1
        model.total_reroutes += 1


def mark_not_arrived(agents) -> None:
    for agent in agents:
        if not agent.arrived and not agent.stranded:
            agent.stranded = True
            agent.stranded_reason = "not_arrived"


def movement_counts(agents) -> dict:
    return {
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
    }


def mean_arrival_t(agents):
    arrival_times = [agent.arrival_t for agent in agents if agent.arrival_t is not None]
    return (sum(arrival_times) / len(arrival_times)) if arrival_times else None


def moving_agent_state(agent, extra=None) -> dict:
    out = {
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
    if extra:
        out.update(extra)
    return out
