"""Ensemble runner: for each representative network × scenario × seed, run the
three treatments (original / optimized / random null) and collect makespan +
static-efficiency gain. Then the three analyses + counterexample detection."""
from __future__ import annotations

import random
import statistics
from typing import List

from abm_auto.coord._network import (CoordNetwork, representative_network, optimize_edges,
                                     add_random_edges, global_efficiency)
from abm_auto.coord._model import CoordModel, Task, Scenario
from abm_auto.coord._metrics import makespan
from abm_auto.coord._gate import CoordNullGate

PROTECT = "省应急管理厅"


def default_tasks() -> List[Task]:
    """The 9-task DAG (DOC B). lead/collaborators must be names in _DEPTS."""
    T = Task
    return [
        T("降雨监测", "省气象局", ["省水利厅", "省应急管理厅"], 3, "监测预警", [], 0),
        T("水情研判", "省水利厅", ["省气象局", "省应急管理厅"], 3, "监测预警", ["降雨监测"], 0),
        T("会商决策", "省应急管理厅", ["省水利厅", "省气象局", "省交通运输厅", "省公安厅"], 4, "监测预警", ["水情研判"], 0),
        T("预警发布", "省气象局", ["省通信管理局", "省公安厅"], 3, "监测预警", ["会商决策"], 0),
        T("交通管控准备", "省公安厅", ["省交通运输厅", "铁路部门"], 4, "处置救援", ["预警发布"], 0),
        T("群众转移", "省民政厅", ["省公安厅", "省交通运输厅"], 5, "处置救援", ["预警发布"], 0),
        T("抢险救援", "消防救援队伍", ["省水利厅", "省应急管理厅"], 5, "处置救援", ["预警发布"], 0),
        T("物资保障", "省粮食和物资储备局", ["省商务厅", "省交通运输厅"], 4, "处置救援", ["预警发布"], 0),
        T("事后恢复", "省民政厅", ["省商务厅", "国网电力公司", "省公安厅"], 4, "事后恢复", ["群众转移", "抢险救援"], 0),
    ]


def default_scenario() -> Scenario:
    return Scenario(triggers={0: ["降雨监测"]}, edge_cuts={})


def _run_treatment(net: CoordNetwork, seed: int) -> float:
    return makespan(CoordModel(net, default_tasks(), default_scenario(), seed=seed).run())


def run_ensemble(*, n_networks: int, seeds=(0, 1, 2), budget: int = 4) -> List[dict]:
    rows: List[dict] = []
    for ni in range(n_networks):
        base = representative_network(seed=ni)
        e0 = global_efficiency(base)
        opt, _ = optimize_edges(base, budget=budget, protect=PROTECT)
        rnd = add_random_edges(base, budget=budget, rng=random.Random(1000 + ni))
        treatments = {
            "original": (base, 0.0),
            "optimized": (opt, (global_efficiency(opt) - e0) / e0 if e0 else 0.0),
            "null": (rnd, (global_efficiency(rnd) - e0) / e0 if e0 else 0.0),
        }
        for tname, (net, sgain) in treatments.items():
            for seed in seeds:
                rows.append({"network": ni, "treatment": tname, "scenario": "default",
                             "seed": seed, "makespan": _run_treatment(net, seed),
                             "static_efficiency_gain": sgain})
    return rows


def _mean_makespan(rows, network, treatment):
    xs = [r["makespan"] for r in rows if r["network"] == network and r["treatment"] == treatment]
    return statistics.mean(xs) if xs else float("nan")


def analyze(rows: List[dict]) -> dict:
    networks = sorted({r["network"] for r in rows})
    per_net = []
    for n in networks:
        orig = _mean_makespan(rows, n, "original")
        opt = _mean_makespan(rows, n, "optimized")
        null = _mean_makespan(rows, n, "null")
        sgain = next(r["static_efficiency_gain"] for r in rows if r["network"] == n and r["treatment"] == "optimized")
        per_net.append({"network": n, "orig": orig, "opt": opt, "null": null,
                        "makespan_gain": orig - opt, "static_gain": sgain})
    n_improved = sum(1 for p in per_net if p["opt"] < p["orig"])
    # null-gate on ensemble means
    gate = CoordNullGate(margin=1.0)
    mean_orig = statistics.mean(p["orig"] for p in per_net)
    mean_opt = statistics.mean(p["opt"] for p in per_net)
    mean_null = statistics.mean(p["null"] for p in per_net)
    verdict = gate.judge(original=mean_orig, optimized=mean_opt, null=mean_null)
    # consistency: correlation static_gain <-> makespan_gain
    sg = [p["static_gain"] for p in per_net]
    mg = [p["makespan_gain"] for p in per_net]
    corr = statistics.correlation(sg, mg) if len(per_net) > 1 and len(set(sg)) > 1 and len(set(mg)) > 1 else float("nan")
    # counterexamples: static efficiency up but makespan also up (worse)
    counter = [p for p in per_net if p["static_gain"] > 0 and p["makespan_gain"] < 0]
    return {
        "process_effectiveness": {"n_networks": len(per_net), "n_improved": n_improved,
                                  "mean_orig": mean_orig, "mean_opt": mean_opt},
        "consistency": {"static_vs_makespan_corr": corr},
        "null_gate": {"passed": verdict.passed, "verdict": verdict.render()},
        "counterexamples": counter,
        "per_network": per_net,
    }
