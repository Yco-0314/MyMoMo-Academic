import os
from abm_auto.runtime import Config, Simulator
from core.model import MyMoMoGridModel
from core.scenario import MyMoMoScenario

if __name__ == "__main__":
    config = Config(
        project_name="MyMoMoGrid",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",
        output_folder="data/output",
    )
    simulator = Simulator(
        config=config,
        model_cls=MyMoMoGridModel,
        scenario_cls=MyMoMoScenario,
    )
    simulator.run()
