from abm_auto.coord._network import CoordNetwork
from abm_auto.coord._model import Department, Task, Scenario, CoordModel


def _tiny():
    net = CoordNetwork(nodes=["L", "C"], edges={("L", "C"): 2.0})
    tasks = [Task(name="t1", lead="L", collaborators=["C"], work=3.0, phase="p", needs=[], trigger_tick=0)]
    scenario = Scenario(triggers={0: ["t1"]}, edge_cuts={})
    return net, tasks, scenario


def test_deterministic_same_seed_same_result():
    net, tasks, scenario = _tiny()
    a = CoordModel(net, tasks, scenario, seed=7).run()
    b = CoordModel(net, tasks, scenario, seed=7).run()
    assert a == b


def test_task_completes_and_records_tick():
    net, tasks, scenario = _tiny()
    res = CoordModel(net, tasks, scenario, seed=1).run()
    assert res["t1"]["status"] == "done"
    assert res["t1"]["done_tick"] >= 0


def test_unreachable_collaborator_fails_task():
    # collaborator C has no edge to lead L -> task cannot coordinate -> fails
    net = CoordNetwork(nodes=["L", "C", "X"], edges={("L", "X"): 1.0})
    tasks = [Task(name="t1", lead="L", collaborators=["C"], work=2.0, phase="p", needs=[], trigger_tick=0)]
    res = CoordModel(net, tasks, Scenario(triggers={0: ["t1"]}, edge_cuts={}), seed=1).run()
    assert res["t1"]["status"] == "failed"


def test_higher_edge_weight_starts_task_sooner():
    # info delay ∝ 1/w: heavier lead<->collab edge => earlier start
    def first_start(w):
        net = CoordNetwork(nodes=["L", "C"], edges={("L", "C"): w})
        tasks = [Task(name="t", lead="L", collaborators=["C"], work=1.0, phase="p", needs=[], trigger_tick=0)]
        return CoordModel(net, tasks, Scenario(triggers={0: ["t"]}, edge_cuts={}), seed=1).run()["t"]["start_tick"]
    assert first_start(8.0) <= first_start(1.0)


# --- v2: functional baseline (0 failed) + biting overload (peak_overload > 1.0) ---
from abm_auto.coord._network import representative_network
from abm_auto.coord._experiment import default_tasks, default_scenario
from abm_auto.coord._metrics import peak_overload


def test_original_baseline_completes_all_tasks():
    # v2 fix (a): the ORIGINAL representative network must complete all 9 tasks
    # (0 failed / 0 pending) across networks and seeds — failures must come from
    # overload dynamics, not missing coordination links.
    for ni in range(6):
        base = representative_network(seed=ni)
        for s in range(5):
            res = CoordModel(base, default_tasks(), default_scenario(), seed=s).run()
            statuses = [v["status"] for k, v in res.items() if not k.startswith("_")]
            assert all(st == "done" for st in statuses), \
                f"net {ni} seed {s}: non-done tasks {statuses}"


def test_load_is_edge_responsive():
    # v3 (flips the v2 KNOWN_LIMITATION): peak_overload is now EMERGENT and
    # TREATMENT-VARYING — adding/selecting edges shifts a shared hub's peak concurrency.
    #
    # Mechanism: the phase-2 tasks share predecessor 预警发布 but their leads sit at
    # different network distances from 预警发布's lead, so each is NOTIFIED (activation
    # origin) at a topology-dependent tick; a collaborator (e.g. 省交通运输厅, shared by
    # 3 phase-2 tasks) bears load only during a short COORD_WINDOW after activation
    # arrives. Whether several of those windows OVERLAP at the hub depends on the
    # arrival-tick spread, which edges change — so peak load varies by treatment.
    from abm_auto.coord._network import optimize_edges, add_random_edges
    from abm_auto.coord._experiment import PROTECT
    from abm_auto.coord._metrics import makespan
    from abm_auto.coord._model import Department
    import random

    ov = lambda net: peak_overload(CoordModel(net, default_tasks(), default_scenario(), seed=0).run())

    # (a) peak_overload is NOT constant across {original, optimized, random}.
    # Checked over a small ensemble (it is a mechanism property, not an outcome
    # threshold): on at least one network the three treatments do not all coincide.
    varied = []
    for ni in range(6):
        base = representative_network(seed=ni)
        opt, _ = optimize_edges(base, budget=4, protect=PROTECT)
        rnd = add_random_edges(base, budget=4, rng=random.Random(1000 + ni))
        o, p, r = ov(base), ov(opt), ov(rnd)
        assert o > 1.0  # overload genuinely occurs (not capped at 1.0)
        if not (o == p == r):
            varied.append((ni, o, p, r))
    assert varied, "peak_overload was treatment-invariant on every network — the v3 " \
                   "edge-responsive channel did NOT activate (regression to v2 limitation)"

    # (b) infinite-capacity ablation: with capacity removed, overload cannot feed back
    # into progress, so the optimized-vs-original makespan GAIN must change on at least
    # one network — proving load actually drives the outcome, not just the metric.
    def ms(net, *, infinite):
        depts = {n: Department(n, capacity=1e6) for n in net.nodes} if infinite else None
        return makespan(CoordModel(net, default_tasks(), default_scenario(), seed=0,
                                   depts=depts).run())
    gain_changed = False
    for ni in range(6):
        base = representative_network(seed=ni)
        opt, _ = optimize_edges(base, budget=4, protect=PROTECT)
        finite_gain = ms(base, infinite=False) - ms(opt, infinite=False)
        infinite_gain = ms(base, infinite=True) - ms(opt, infinite=True)
        if finite_gain != infinite_gain:
            gain_changed = True
            break
    assert gain_changed, "removing capacity did not change the opt-vs-orig makespan " \
                         "gain on any network — load is not feeding back into the outcome"
