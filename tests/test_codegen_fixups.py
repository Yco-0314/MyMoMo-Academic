"""Unit tests for abm_auto.codegen.fixups — post-LLM fixup pipeline."""
from __future__ import annotations

from abm_auto.codegen.fixups import (
    ConfigPathsFixup,
    CsvLocationFixup,
    GridCategoryInjectionFixup,
    SyntaxValidationFixup,
    DEFAULT_FIXUPS,
    apply_fixup_pipeline,
)


# ── ConfigPathsFixup ─────────────────────────────────────────────────────


def test_config_paths_fixup_rewrites_nonstandard_input() -> None:
    files = {
        "main.py": (
            'from abm_auto.runtime import Config\n'
            'config = Config(input_folder="input", output_folder="output")\n'
        ),
    }
    out = ConfigPathsFixup().run(files)
    assert 'input_folder="data/input"' in out["main.py"]
    assert 'output_folder="data/output"' in out["main.py"]


def test_config_paths_fixup_preserves_correct_paths() -> None:
    files = {
        "main.py": 'config = Config(input_folder="data/input", output_folder="data/output")\n',
    }
    out = ConfigPathsFixup().run(files)
    # Idempotent — unchanged
    assert out == files


def test_config_paths_fixup_should_run_only_with_main_py() -> None:
    assert not ConfigPathsFixup().should_run({"core/agent.py": "x"})
    assert ConfigPathsFixup().should_run({"main.py": "x"})


# ── CsvLocationFixup ─────────────────────────────────────────────────────


def test_csv_location_fixup_moves_to_canonical_dir() -> None:
    files = {
        "SimulatorScenarios.csv": "id,run_num\n0,1\n",
        "core/agent.py": "x",
    }
    out = CsvLocationFixup().run(files)
    assert "data/input/SimulatorScenarios.csv" in out
    assert "SimulatorScenarios.csv" not in [k for k in out if k != "data/input/SimulatorScenarios.csv"]
    assert out["data/input/SimulatorScenarios.csv"] == "id,run_num\n0,1\n"


def test_csv_location_fixup_should_run_only_if_misplaced() -> None:
    fixup = CsvLocationFixup()
    assert not fixup.should_run({"data/input/SimulatorScenarios.csv": "x"})
    assert fixup.should_run({"SimulatorScenarios.csv": "x"})
    assert fixup.should_run({"scenarios/SimulatorScenarios.csv": "x"})
    assert not fixup.should_run({"core/agent.py": "x"})


# ── GridCategoryInjectionFixup ───────────────────────────────────────────


def test_grid_category_injection_adds_method_when_missing() -> None:
    files = {
        "core/agent.py": (
            "from abm_auto.runtime import GridAgent\n\n"
            "class Person(GridAgent):\n"
            "    def setup(self):\n"
            "        self.x = 0\n"
        ),
    }
    out = GridCategoryInjectionFixup().run(files)
    assert "def set_category(self):" in out["core/agent.py"]
    assert "self.category = 0" in out["core/agent.py"]


def test_grid_category_injection_skips_if_present() -> None:
    files = {
        "core/agent.py": (
            "from abm_auto.runtime import GridAgent\n\n"
            "class Person(GridAgent):\n"
            "    def set_category(self):\n"
            "        self.category = 1\n"
            "    def setup(self):\n"
            "        pass\n"
        ),
    }
    fixup = GridCategoryInjectionFixup()
    assert not fixup.should_run(files)


def test_grid_category_injection_skips_non_grid_agents() -> None:
    files = {
        "core/agent.py": (
            "from abm_auto.runtime import NetworkAgent\n\n"
            "class Person(NetworkAgent):\n"
            "    def setup(self):\n"
            "        pass\n"
        ),
    }
    fixup = GridCategoryInjectionFixup()
    assert not fixup.should_run(files)


# ── SyntaxValidationFixup ────────────────────────────────────────────────


def test_syntax_validation_is_pure_log_no_mutation() -> None:
    files = {
        "core/model.py": "def broken(:\n",   # SyntaxError
        "core/scenario.py": "x = 1\n",
    }
    out = SyntaxValidationFixup().run(files)
    # Returns files unchanged; only logs errors
    assert out == files


# ── apply_fixup_pipeline ─────────────────────────────────────────────────


def test_pipeline_runs_all_default_fixups_in_order() -> None:
    files = {
        "main.py": 'Config(input_folder="input")\n',
        "scenarios.csv": "x",  # NOT a SimulatorScenarios.csv — should be ignored by CsvLocationFixup
        "core/agent.py": "class A(GridAgent):\n    def setup(self):\n        pass\n",
    }
    out = apply_fixup_pipeline(files)
    # ConfigPathsFixup ran
    assert 'input_folder="data/input"' in out["main.py"]
    # GridCategoryInjectionFixup ran
    assert "def set_category" in out["core/agent.py"]
    # CsvLocationFixup did NOT touch unrelated CSVs
    assert "scenarios.csv" in out


def test_pipeline_skips_fixups_when_should_run_false() -> None:
    # No main.py, no GridAgent → only SyntaxValidationFixup runs (and is a no-op)
    files = {"core/scenario.py": "x = 1\n"}
    out = apply_fixup_pipeline(files)
    assert out == files


def test_default_fixups_protocol_compliance() -> None:
    """Every entry must have a name + should_run + run callable."""
    for fixup in DEFAULT_FIXUPS:
        assert isinstance(fixup.name, str) and fixup.name
        assert callable(fixup.should_run)
        assert callable(fixup.run)
