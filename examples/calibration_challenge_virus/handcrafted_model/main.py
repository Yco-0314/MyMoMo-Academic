"""Hand-crafted SIR-on-network simulator for the Milan calibration benchmark.

Sidesteps abm-auto's codegen entirely. Used by benchmark_calibration_validated.py
to test BayesianCalibrator + MSE scoring on a KNOWN-GOOD simulator. This lets
us decouple "is calibration broken?" from "is codegen broken?".
"""
import os
from abm_auto.runtime import Config, Simulator
from core.model import VirusModel
from core.scenario import VirusScenario

if __name__ == "__main__":
    config = Config(
        project_name="VirusOnNetwork",
        project_root=os.path.dirname(__file__),
        input_folder="data/input",
        output_folder="data/output",
    )
    simulator = Simulator(config=config, model_cls=VirusModel, scenario_cls=VirusScenario)
    simulator.run()
