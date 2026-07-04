from abm_auto.coord._experiment import run_ensemble, analyze


def test_small_ensemble_runs_and_analyzes():
    rows = run_ensemble(n_networks=4, seeds=(0, 1), budget=3)
    # one row per (network, treatment, scenario, seed)
    assert rows and {"network", "treatment", "scenario", "seed", "makespan",
                     "static_efficiency_gain"} <= set(rows[0])
    treatments = {r["treatment"] for r in rows}
    assert {"original", "optimized", "null"} <= treatments

    rep = analyze(rows)
    assert "process_effectiveness" in rep      # optimized vs original makespan
    assert "consistency" in rep                # static gain <-> makespan gain
    assert "null_gate" in rep                  # optimized vs null verdict
    assert "counterexamples" in rep            # list (possibly empty) of static↑/makespan↑ instances
    assert isinstance(rep["counterexamples"], list)
