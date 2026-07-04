import numpy as np
from abm_auto.coord._network import CoordNetwork, global_efficiency, cei


def _triangle():
    # 3 fully-connected nodes, unit weights
    return CoordNetwork(nodes=["a", "b", "c"], edges={("a", "b"): 1.0, ("b", "c"): 1.0, ("a", "c"): 1.0})


def test_global_efficiency_complete_graph_is_one():
    # unit-weight complete graph: every pair distance 1 -> efficiency 1.0
    assert abs(global_efficiency(_triangle()) - 1.0) < 1e-9


def test_global_efficiency_path_lower_than_complete():
    path = CoordNetwork(nodes=["a", "b", "c"], edges={("a", "b"): 1.0, ("b", "c"): 1.0})
    assert global_efficiency(path) < global_efficiency(_triangle())


def test_higher_weight_shortens_distance():
    # edge length = 1/w, so higher weight => higher efficiency
    light = CoordNetwork(nodes=["a", "b"], edges={("a", "b"): 1.0})
    heavy = CoordNetwork(nodes=["a", "b"], edges={("a", "b"): 4.0})
    assert global_efficiency(heavy) > global_efficiency(light)


def test_cei_is_relative_efficiency_drop_on_removal():
    net = _triangle()
    val = cei(net, "a")
    assert 0.0 <= val <= 1.0  # removing a node from a complete triangle drops efficiency
    assert val > 0


import random as _random
from abm_auto.coord._network import representative_network, optimize_edges, add_random_edges


def test_representative_network_has_hubs_and_weighted_edges():
    net = representative_network(seed=1)
    assert len(net.nodes) >= 12
    assert all(w > 0 for w in net.edges.values())
    # hub departments exist
    assert "省应急管理厅" in net.nodes


def test_optimize_edges_raises_global_efficiency():
    net = representative_network(seed=2)
    e0 = global_efficiency(net)
    opt, added = optimize_edges(net, budget=3, protect="省应急管理厅")
    assert len(added) >= 1
    assert global_efficiency(opt) >= e0  # optimization never lowers static efficiency
    # protected node's CEI not weakened
    assert cei(opt, "省应急管理厅") >= cei(net, "省应急管理厅") - 1e-9


def test_random_edges_adds_budget_edges():
    net = representative_network(seed=3)
    rnd = add_random_edges(net, budget=3, rng=_random.Random(3))
    assert len(rnd.edges) == len(net.edges) + 3


# --- v2: baselines GUARANTEE every required (lead, collaborator) DAG edge ---
from abm_auto.coord._network import required_pairs


def test_required_pairs_derived_from_dag():
    # the required-pair set is built from default_tasks(), so it can't drift
    pairs = required_pairs()
    assert len(pairs) >= 12
    assert all(isinstance(p, tuple) and len(p) == 2 for p in pairs)
    # 降雨监测 (lead 省气象局) needs collaborators 省水利厅, 省应急管理厅
    assert tuple(sorted(("省气象局", "省水利厅"))) in pairs
    assert tuple(sorted(("省气象局", "省应急管理厅"))) in pairs


def test_representative_network_contains_all_required_edges():
    # v2 fix: every required DAG coordination edge must be present in EVERY baseline
    req = set(required_pairs())
    for seed in range(8):
        net = representative_network(seed=seed)
        present = {tuple(sorted(e)) for e in net.edges}
        assert req <= present, f"seed {seed} missing required edges: {req - present}"
