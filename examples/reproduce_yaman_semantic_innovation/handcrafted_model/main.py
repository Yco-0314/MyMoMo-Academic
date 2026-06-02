"""Hand-crafted Yaman et al. (2026) semantic-innovation reference model.

Reproduce mode (ADR Path 2): the model is hand-written from the paper's SI
Algorithms 1 & 2 over the REAL OSF recipe tree; abm-auto provides the
runtime (Model/Agent/Environment/DataCollector), the FeedforwardLearner
operator (W2), and the analysis layer. We do not codegen this model — it
is the reference the codegen path is measured against.
"""
import os

from abm_auto.runtime import Config, Simulator

from core.model import YamanModel
from core.scenario import YamanScenario

if __name__ == "__main__":
    config = Config(
        project_name="YamanSemanticInnovation",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",
        output_folder="data/output",
    )
    simulator = Simulator(config=config, model_cls=YamanModel, scenario_cls=YamanScenario)
    simulator.run()
