import networkx as nx

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


class FakeAgent:
    def __init__(self, node="A"):
        self.id = 7
        self.node = node
        self.edge = None
        self.edge_progress_m = 0.0
        self.route = []
        self.arrived = False
        self.stranded = False
        self.stranded_reason = None
        self.reroutes = 0
        self.arrival_t = None


class FakeModel:
    def __init__(self):
        self.reroutes_this_step = 0
        self.total_reroutes = 0


def _graph():
    graph = nx.Graph()
    graph.add_edge("A", "B", length=100.0)
    graph.add_edge("B", "C", length=100.0)
    return graph


def test_edge_key_is_symmetric_and_repr_ordered_for_mixed_node_types():
    assert edge_key("10", 2) == edge_key(2, "10")


def test_routable_graph_removes_blocked_edges_without_mutating_source():
    graph = _graph()
    blocked = {edge_key("A", "B")}

    pruned = routable_graph(graph, blocked)

    assert graph.has_edge("A", "B")
    assert not pruned.has_edge("A", "B")
    assert pruned.has_edge("B", "C")


def test_try_enter_next_edge_respects_blocked_edges():
    agent = FakeAgent()
    agent.route = ["B"]

    assert try_enter_next_edge(agent, _graph(), blocked_edges={edge_key("A", "B")}) is False
    assert agent.edge is None
    assert try_enter_next_edge(agent, _graph(), blocked_edges=set()) is True
    assert agent.edge == ("A", "B")
    assert agent.edge_progress_m == 0.0


def test_advance_on_edge_does_not_carry_speed_across_edges():
    agent = FakeAgent()
    agent.edge = ("A", "B")
    agent.route = ["B", "C"]

    advance_on_edge(agent, _graph(), safe_nodes={"C"}, distance_m=250.0, t=3)

    assert agent.node == "B"
    assert agent.edge is None
    assert agent.route == ["C"]
    assert agent.arrived is False


def test_advance_on_edge_marks_arrival_on_safe_node():
    agent = FakeAgent()
    agent.edge = ("A", "B")
    agent.route = ["B"]

    advance_on_edge(agent, _graph(), safe_nodes={"B"}, distance_m=100.0, t=4)

    assert agent.arrived is True
    assert agent.arrival_t == 4
    assert agent.route == []


def test_record_reroute_counts_only_real_nonempty_route_changes():
    agent = FakeAgent()
    model = FakeModel()

    record_reroute(agent, model, old_route=["B"], new_route=["B"], count_as_reroute=True)
    record_reroute(agent, model, old_route=["B"], new_route=[], count_as_reroute=True)
    assert agent.reroutes == 0

    record_reroute(agent, model, old_route=["B"], new_route=["C"], count_as_reroute=True)

    assert agent.reroutes == 1
    assert model.reroutes_this_step == 1
    assert model.total_reroutes == 1


def test_counts_finalization_mean_arrival_and_state_serialization():
    waiting = FakeAgent()
    moving = FakeAgent()
    moving.edge = ("A", "B")
    arrived = FakeAgent()
    arrived.arrived = True
    arrived.arrival_t = 2
    stranded = FakeAgent()
    stranded.stranded = True
    agents = [waiting, moving, arrived, stranded]

    assert movement_counts(agents) == {
        "arrived": 1,
        "moving": 1,
        "waiting": 1,
        "stranded": 1,
    }
    assert mean_arrival_t(agents) == 2

    mark_not_arrived(agents)

    assert waiting.stranded_reason == "not_arrived"
    assert moving.stranded_reason == "not_arrived"
    assert arrived.stranded is False
    assert stranded.stranded_reason is None
    assert moving_agent_state(arrived, extra={"exposure_depth": 0.5})["exposure_depth"] == 0.5
