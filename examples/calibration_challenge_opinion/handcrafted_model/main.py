"""Hand-crafted Deffuant opinion-dynamics simulator.

Cross-domain stress test for abm-auto's calibration seams. Uses different
column names (mean_opinion / opinion_variance / n_clusters) and a
different topology (Watts-Strogatz, not netlogo_spatially_clustered) than
the SIR example, exercising COLUMN_ALIASES, topology adapters, and the
calibrator's domain-agnosticism.
"""
import os
from abm_auto.runtime import Config, Simulator
from core.model import OpinionModel
from core.scenario import OpinionScenario

if __name__ == "__main__":
    config = Config(
        project_name="OpinionDynamics",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",
        output_folder="data/output",
    )
    simulator = Simulator(config=config, model_cls=OpinionModel, scenario_cls=OpinionScenario)
    simulator.run()
