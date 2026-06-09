"""ABM Auto Runtime — standalone ``Simulator`` (ADR-009 Phase 4, Stage A).

The batch / multi-scenario orchestrator. Drop-in for ``Melodie.Simulator`` on
the ``run()`` path:

    setup() → pre_run() [clear output · DataLoader → scenarios · attach the
    standard tables onto each scenario] → for scenario, for id_run in
    range(scenario.run_num): run_model() [construct Model, _setup(), run()]

The sequential multi-scenario / multi-run batch is preserved in full. What is
dropped vs Melodie: the sqlite DB (our DataCollector writes CSV), the visualizer
(``run_visual``), and the multiprocessing ``run_parallel`` (a parallel-execution
optimisation, not a capability — sequential ``run()`` already covers
multi-scenario/batch; parallel can return as a Phase-4 follow-up).

Stage A keeps Melodie's ``Model`` (this Simulator drives it via the same
``Model(config, scenario, run_id) → _setup() → run()`` lifecycle); Stage B
un-subclasses Model. Gated by the byte-diff engine oracle.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from typing import List, Optional, Type

from abm_auto.runtime._data_loader import DataLoader

logger = logging.getLogger(__name__)

# scenario-table name → the attribute name it is attached under on each scenario
_STANDARD_TABLE_MAP = {
    "SimulatorScenarios": "simulator_scenarios",
    "TrainerScenarios": "trainer_scenarios",
    "CalibratorScenarios": "calibrator_scenarios",
    "CalibratorParamsScenarios": "calibrator_params_scenarios",
    "TrainerParamsScenarios": "trainer_params_scenarios",
}


class Simulator:
    def __init__(
        self,
        config,
        scenario_cls: Type,
        model_cls: Type,
        data_loader_cls: Optional[Type] = None,
        visualizer_cls: Optional[Type] = None,
    ) -> None:
        self.config = config
        self.scenario_cls = scenario_cls
        self.model_cls = model_cls
        self.df_loader_cls = data_loader_cls or DataLoader
        self.data_loader = None
        self.scenarios: Optional[List] = None
        # visualizer_cls accepted for API parity; the standalone path is non-visual
        self.visualizer_cls = visualizer_cls

    # ── hooks / helpers ──────────────────────────────────────────────────────

    def setup(self) -> None:
        """A hook for custom simulator setup, called before ``pre_run``."""
        pass

    def get_dataframe(self, table_name: str):
        return self.data_loader.get_dataframe(table_name)

    def clear_output_tables(self) -> None:
        out = self.config.output_tables_path()
        if os.path.exists(out):
            shutil.rmtree(out)
        os.makedirs(out)

    # ── pre-run: scenarios + output ──────────────────────────────────────────

    def pre_run(self, clear_output_data: bool = True) -> None:
        if clear_output_data:
            self.clear_output_tables()
        self.data_loader = self.df_loader_cls(self, self.config, self.scenario_cls)
        self.scenarios = self.generate_scenarios()
        for table_name, attr_name in _STANDARD_TABLE_MAP.items():
            if table_name in self.data_loader.registered_dataframes:
                df = self.data_loader.registered_dataframes[table_name]
                for scenario in self.scenarios:
                    setattr(scenario, attr_name, df)
        if not self.scenarios:
            raise ValueError("no valid scenario generated")

    def generate_scenarios(self) -> List:
        return self.data_loader.generate_scenarios("Simulator")

    # ── run a single (scenario, run) ─────────────────────────────────────────

    def run_model(self, config, scenario, id_run: int, model_class: Type) -> None:
        scenario.id_run = id_run
        model = model_class(config, scenario, run_id_in_scenario=id_run)
        model._setup()
        model.run()

    # ── batch entry point ────────────────────────────────────────────────────

    def run(self) -> None:
        """Run every scenario for its ``run_num`` runs, sequentially."""
        t0 = time.time()
        self.setup()
        self.pre_run()
        assert self.scenarios is not None
        for scenario in self.scenarios:
            for id_run in range(scenario.run_num):
                self.run_model(self.config, scenario, id_run, self.model_cls)
        logger.info(f"Simulator completed, time elapsed {time.time() - t0:.3f}s.")


__all__ = ["Simulator"]
