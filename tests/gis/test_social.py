import networkx as nx

from abm_auto.gis._coupling import combined_neighbors
from abm_auto.gis._social import run_contagion, social_lift_gate


def grid_neighbors(side):
    def f(i):
        r, c = divmod(i, side)
        out = []
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < side and 0 <= cc < side:
                out.append(rr * side + cc)
        return out
    return f


def test_combined_neighbors_unions_spatial_and_social():
    sg = nx.Graph(); sg.add_edge(0, 55)
    nbrs = combined_neighbors(0, grid_neighbors(10), sg)
    assert 1 in nbrs and 10 in nbrs   # spatial: right + down
    assert 55 in nbrs                 # social long-range tie


def test_contagion_grows_and_is_deterministic():
    sg = nx.watts_strogatz_graph(100, 4, 0.3, seed=1)
    a = run_contagion(100, grid_neighbors(10), sg, beta=0.2, steps=8, seed=1)
    b = run_contagion(100, grid_neighbors(10), sg, beta=0.2, steps=8, seed=1)
    assert a["history"] == b["history"]            # deterministic
    assert a["final"] > a["history"][0]            # spreads


def test_social_lift_gate_passes():
    sg = nx.watts_strogatz_graph(100, 4, 0.3, seed=1)
    ok, desc = social_lift_gate(100, grid_neighbors(10), sg, beta=0.2, steps=6, seed=1)
    assert ok, desc                                # social ties extend reach


def test_social_lift_gate_fails_with_empty_social():
    sg = nx.Graph(); sg.add_nodes_from(range(100))   # no ties -> no lift
    ok, _ = social_lift_gate(100, grid_neighbors(10), sg, beta=0.2, steps=6, seed=1)
    assert not ok


def test_social_run_contagion_keeps_existing_public_result_shape():
    sg = nx.Graph()
    sg.add_nodes_from(range(4))
    sg.add_edge(0, 3)

    result = run_contagion(
        4,
        lambda i: [i + 1] if i < 3 else [],
        sg,
        beta=1.0,
        steps=1,
        seed=0,
        seeds=(0,),
    )

    assert result == {"history": [1, 2], "final": 2, "n_agents": 4}
