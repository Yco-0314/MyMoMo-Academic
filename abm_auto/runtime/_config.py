"""ABM Auto Runtime — ``Config``: the run's project paths.

Carries only what the Simulator path needs: project name/root, the input and
output folders, a temp folder, and the dataframe cache flag. No database,
visualizer, or port machinery — the DataCollector writes CSV directly. Public
surface used by the handcrafted models + Simulator/DataLoader: ``project_name``,
``project_root``, ``input_folder``, ``output_folder``, ``output_tables_path()``,
``temp_folder``, ``input_dataframe_cache``.
"""
from __future__ import annotations

import os


class Config:
    def __init__(
        self,
        project_name: str,
        project_root: str,
        input_folder: str,
        output_folder: str,
        input_cache: bool = False,
        data_output_type: str = "csv",
        **kwargs,
    ) -> None:
        self.project_name = project_name
        self.project_root = project_root
        # mkdir the IO folders (relative to cwd) and keep the path unchanged so
        # paths resolve identically wherever the run is launched from.
        self.output_folder = self._ensure(output_folder)
        self.input_folder = self._ensure(input_folder)
        self.temp_folder = ".abm_auto"
        # visualizer_tmpdir is where the Network optionally writes a
        # <name>_layout.gexf (visualisation path only; unused on the run path).
        self.visualizer_tmpdir = os.path.join(self.temp_folder, "visualizer")
        self.studio_port = kwargs.get("studio_port", 8089)
        self.visualizer_port = kwargs.get("visualizer_port", 8765)
        self.parallel_port = kwargs.get("parallel_port", 12233)
        self.input_dataframe_cache = input_cache
        self.data_output_type = data_output_type
        self.init_temp_folders()
        self.setup()

    def init_temp_folders(self) -> None:
        for d in (self.temp_folder, self.visualizer_tmpdir):
            if not os.path.exists(d):
                os.makedirs(d)

    @staticmethod
    def _ensure(path: str) -> str:
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def setup(self) -> None:
        """Override hook for subclasses that need extra config-time setup."""
        pass

    def output_tables_path(self) -> str:
        return self.output_folder

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


__all__ = ["Config"]
