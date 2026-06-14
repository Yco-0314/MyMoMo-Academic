"""ABM Auto Runtime — ``DataLoader``: scenario discovery and construction.

The multi-scenario heart: scans ``config.input_folder`` for the standard
``SimulatorScenarios`` table, loads it, and turns each row into a ``Scenario``
(``scenario_cls()._setup(row)``). ``load_matrix`` / ``register_dataframe`` are
thin stubs for models that register extra input tables; the corpus and codegen
paths don't use them.
"""
from __future__ import annotations

import os
from typing import List

# the five standard scenario tables auto-discovered in the input folder
_STANDARD_TABLES = {
    "SimulatorScenarios",
    "TrainerScenarios",
    "CalibratorScenarios",
    "CalibratorParamsScenarios",
    "TrainerParamsScenarios",
}


def _first_char_upper(word: str) -> str:
    return word[:1].upper() + word[1:]


def _underline_to_camel(s: str) -> str:
    """``simulator_scenarios`` → ``SimulatorScenarios``; leaves an
    already-camel name untouched."""
    return "".join(_first_char_upper(w) for w in s.split("_"))


def _read_table(path: str):
    import pandas as pd

    ext = os.path.splitext(path)[1].lower()
    if ext in {".xls", ".xlsx"}:
        return pd.read_excel(path)
    if ext == ".csv":
        return pd.read_csv(path)
    raise NotImplementedError(f"cannot read table file: {path}")


class DataLoader:
    def __init__(self, manager, config, scenario_cls, as_sub_worker: bool = False) -> None:
        assert scenario_cls is not None, "scenario_cls must not be None"
        self.config = config
        self.scenario_cls = scenario_cls
        self.registered_dataframes: dict = {}
        self.registered_matrices: dict = {}
        self.manager = manager
        self.manager.data_loader = self
        self.load_scenarios()
        self.setup()

    def setup(self) -> None:
        """Override hook for subclasses that need extra load-time setup."""
        pass

    def load_scenarios(self) -> None:
        for file_name in os.listdir(self.config.input_folder):
            camel = _underline_to_camel(os.path.splitext(file_name)[0])
            if camel in _STANDARD_TABLES:
                self.load_dataframe(file_name, camel)

    def load_dataframe(self, df_info: str, df_name: str = ""):
        name = df_name or os.path.splitext(os.path.basename(df_info))[0]
        if name in self.registered_dataframes:
            return self.registered_dataframes[name]
        df = _read_table(os.path.join(self.config.input_folder, df_info))
        self.registered_dataframes[name] = df
        return df

    def register_dataframe(self, table_name: str, data_frame, data_types=None) -> None:
        self.registered_dataframes[table_name] = data_frame

    def get_dataframe(self, table_name: str):
        return self.registered_dataframes[table_name]

    def load_matrix(self, file_name: str, mat_name: str = ""):
        import pandas as pd

        name = mat_name or os.path.basename(file_name)
        if name in self.registered_matrices:
            return self.registered_matrices[name]
        path = os.path.join(self.config.input_folder, file_name)
        ext = os.path.splitext(path)[1].lower()
        reader = pd.read_excel if ext in {".xls", ".xlsx"} else pd.read_csv
        arr = reader(path, header=None).to_numpy()
        self.registered_matrices[name] = arr
        return arr

    def generate_scenarios(self, manager_type: str) -> List:
        df_name = f"{manager_type}Scenarios"
        if df_name not in self.registered_dataframes:
            alt = _underline_to_camel(df_name)
            if alt in self.registered_dataframes:
                df_name = alt
            else:
                raise NotImplementedError(
                    f"{df_name} not loaded; registered: {list(self.registered_dataframes)}"
                )
        return self.generate_scenarios_from_dataframe(df_name)

    def generate_scenarios_from_dataframe(self, df_name: str) -> List:
        df = self.registered_dataframes[df_name]
        scenarios: list = []
        for row in df.to_dict("records"):
            scenario = self.scenario_cls()
            scenario.manager = self.manager
            scenario._setup(row)
            scenarios.append(scenario)
        if not scenarios:
            raise ValueError("no valid scenario generated from the scenario table")
        return scenarios


__all__ = ["DataLoader"]
