import os
from abm_auto.runtime import Config, Simulator
from core.model import TemplateModel
from core.scenario import TemplateScenario

if __name__ == "__main__":
    config = Config(
        project_name="{{project_name}}",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",
        output_folder="data/output",
    )
    simulator = Simulator(config=config, model_cls=TemplateModel, scenario_cls=TemplateScenario)
    simulator.run()
