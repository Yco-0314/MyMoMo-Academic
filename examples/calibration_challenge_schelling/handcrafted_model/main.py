"""Hand-crafted Schelling segregation simulator.

Cross-domain stress test #2: Grid-based (not Network like SIR/Opinion),
different column names again (n_unhappy / segregation_index /
fraction_segregated). Exercises the Grid adapter + cross-domain
column matching.
"""
import os
from abm_auto.runtime import Config, Simulator
from core.model import SchellingModel
from core.scenario import SchellingScenario

if __name__ == "__main__":
    config = Config(
        project_name="SchellingSegregation",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",
        output_folder="data/output",
    )
    simulator = Simulator(config=config, model_cls=SchellingModel, scenario_cls=SchellingScenario)
    simulator.run()
