"""Confirm-or-refute: did run-2 silently use lr=0.001 (CSV override of the
scenario default), leaving M undertrained? Run semantic-solo and sem+soc at
both regimes; if lr=0.2 lifts them clearly above the lr=0.001 numbers, run-2
was undertrained and its 'synergy' was a sampling artifact, not semantic
guidance."""
from __future__ import annotations

import csv
import statistics as st

from abm_auto.runtime import Config, Simulator

from core.model import YamanModel
from core.scenario import YamanScenario
from run_experiment import HERE, OUTPUT, _write_scenario


def run(lr, ep, seed, p_s, p_sl, p_g=0.0):
    _write_scenario(id=0, run_num=1, periods=150, agent_num=50, n_attempts=10,
                    seed=seed, p_semantic=p_s, p_social=p_sl, p_generalize=p_g,
                    embed_dim=16, hidden_dim=16, learning_rate=lr, train_epochs=ep)
    cfg = Config(project_name="YamanSemanticInnovation", project_root=HERE,
                 input_folder="data/input", output_folder="data/output")
    Simulator(config=cfg, model_cls=YamanModel, scenario_cls=YamanScenario).run()
    return int(list(csv.DictReader(open(OUTPUT)))[-1]["repertoire_size"])


for lr, ep in [(0.001, 5), (0.2, 20)]:
    solo = [run(lr, ep, s, 0.9, 0.0) for s in range(4)]
    both = [run(lr, ep, s, 0.9, 0.9) for s in range(4)]
    print(f"lr={lr:<5} ep={ep:<3} | semantic-solo {st.mean(solo):4.1f} {solo} | "
          f"sem+soc {st.mean(both):4.1f} {both}")
