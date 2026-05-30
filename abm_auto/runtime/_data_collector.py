"""ABM Auto Runtime — standalone DataCollector.

Phase 2 of the ADR-009 engine replacement roadmap. Replaces
``Melodie.DataCollector`` (459 LoC + Melodie.Table abstraction +
SQLite/CSV dual backend) with a pandas-backed CSV-only implementation.

What this class does
--------------------
Subclassed by the user (every example has its own ``FooDataCollector``).
``setup()`` registers which environment + agent properties to collect.
Then the framework calls ``collect(period)`` once per tick and
``save()`` at end of run; the result lands as
``Result_Simulator_Environment.csv`` (and per-container agent CSVs)
in the model's output directory.

Output CSV format (byte-equal to Melodie's):

    id_scenario,id_run,period,<env_prop_1>,<env_prop_2>,...
    0,0,0,147,3,0
    0,0,1,147,3,0
    ...

What this drops vs Melodie
--------------------------
- **SQLite target**: not used in our codebase. ``target="sqlite"`` raises.
- **Custom collectors** (``add_custom_collector``): unused.
- **``calc_time`` decorator + ``get_single_agent_data``**: unused.
- **``time_elapsed`` accounting**: kept but trivial.
- **Status check (``isinstance(operator, Simulator)``)**: hard-coded True;
  we never run under Calibrator/Trainer (we have our own calibration
  pipeline via ``abm_auto.calibration``).

Surface kept identical so user/generated code observes no change:
``setup()``, ``_setup()``, ``add_environment_property``,
``add_agent_property``, ``collect``, ``save``, ``model``/``scenario``/
``config`` back-refs.

See `docs/decisions/ADR-009-engine-replacement-roadmap.md` Phase 2.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Type

import pandas as pd

# Output filename for the environment-properties table. Must match
# Melodie's ``MelodieInfra.db.DBConn.ENVIRONMENT_RESULT_TABLE`` constant
# so SimulatorWrapper's CSV-reading layer keeps working unchanged.
_ENV_TABLE = "Result_Simulator_Environment"

# Melodie's writer emits CRLF line endings (Python csv module default in
# text mode on the version Melodie ships). Pandas defaults to LF, which
# would break byte-equal regression with pre-swap reference CSVs. Force
# CRLF here so Phase 2 swap is a true drop-in.
_LINE_TERMINATOR = "\r\n"


def _underline_to_camel(s: str) -> str:
    """snake_case → CamelCase. Matches Melodie's util semantics for the
    agent-properties table filename (``Result_Simulator_<ContainerCamel>``).
    """
    return "".join(part.capitalize() for part in s.split("_"))


class DataCollector:
    """Standalone DataCollector. Pandas-backed, CSV-only.

    Subclass and override :meth:`setup` to register collected properties.
    Framework wires ``model``/``scenario``/``config`` back-refs via
    ``Model.create_data_collector``; from then on ``collect()`` /
    ``save()`` are framework-called.
    """

    _CORE_PROPERTIES_ = ["id_scenario", "id_run", "period"]

    def __init__(self, target: str = "csv"):
        if target not in {"csv", None}:
            raise ValueError(
                f"DataCollector only supports target='csv', got {target!r}. "
                f"SQLite target was dropped in ADR-009 Phase 2 (unused)."
            )
        self.target = target

        # Back-refs assigned by Model.create_data_collector
        self.model: Any = None
        self.scenario: Any = None
        self.config: Any = None

        # Registration tables — populated by user's setup()
        self._env_property_names: List[str] = []
        self._agent_property_specs: Dict[str, List[str]] = {}

        # Per-period buffers — flushed by save()
        self._env_rows: List[Dict[str, Any]] = []
        self._agent_rows: Dict[str, List[Dict[str, Any]]] = {}

        self._time_elapsed = 0.0

    # ── status (always-on; no Calibrator/Trainer special case) ────────

    @property
    def status(self) -> bool:
        """Always True. Melodie skipped collection under Calibrator/Trainer
        to speed those up; we don't use either (own calibration pipeline)."""
        return True

    # ── user-overridable hook ─────────────────────────────────────────

    def setup(self) -> None:
        """Override to register properties via ``add_environment_property``
        and/or ``add_agent_property``."""

    # ── framework-called lifecycle ────────────────────────────────────

    def _setup(self) -> None:
        """Called once after Model wires the back-refs. Drives user setup
        and resets the elapsed-time counter."""
        self.setup()
        self._time_elapsed = 0.0

    def time_elapsed(self) -> float:
        return self._time_elapsed

    # ── registration ──────────────────────────────────────────────────

    def add_environment_property(self, property_name: str, as_type: Optional[Type] = None) -> None:
        """Register an attribute on ``model.environment`` to record per tick.
        ``as_type`` is accepted for source-compat but ignored (pandas infers)."""
        self._env_property_names.append(property_name)

    def add_agent_property(
        self,
        container_name: str,
        property_name: str,
        as_type: Optional[Type] = None,
    ) -> None:
        """Register an attribute on every agent in ``model.<container_name>``
        to record per tick."""
        if self.model is not None and not hasattr(self.model, container_name):
            raise AttributeError(
                f"Model has no agent container '{container_name}' "
                f"(registered via add_agent_property)"
            )
        self._agent_property_specs.setdefault(container_name, []).append(property_name)

    # ── per-tick collection ───────────────────────────────────────────

    def collect(self, period: int) -> None:
        """Record env + agent properties for this period. Idempotent for a
        given period only by convention — callers don't call twice."""
        if not self.status:
            return
        t0 = time.time()

        # Environment row — id_scenario, id_run, period + env props
        env_row: Dict[str, Any] = {
            "id_scenario": self.model.scenario.id,
            "id_run": self.model.run_id_in_scenario,
            "period": period,
        }
        env_row.update(self.model.environment.to_dict(self._env_property_names))
        self._env_rows.append(env_row)

        # Agent rows — one per (container, agent) pair
        for container_name, prop_names in self._agent_property_specs.items():
            container = getattr(self.model, container_name)
            rows_for_container = self._agent_rows.setdefault(container_name, [])
            for agent in container:
                row: Dict[str, Any] = {
                    "id_scenario": self.model.scenario.id,
                    "id_run": self.model.run_id_in_scenario,
                    "period": period,
                    "id": agent.id,
                }
                for prop in prop_names:
                    row[prop] = getattr(agent, prop)
                rows_for_container.append(row)

        self._time_elapsed += time.time() - t0

    # ── save ──────────────────────────────────────────────────────────

    def save(self) -> None:
        """Write buffered env + agent data to CSV files under
        ``model.config.output_tables_path()``. Idempotent: a second call
        without further ``collect()`` writes nothing."""
        if not self.status:
            return
        t0 = time.time()

        base_path = self.model.config.output_tables_path()
        os.makedirs(base_path, exist_ok=True)

        # Environment table
        if self._env_rows:
            df = pd.DataFrame(self._env_rows)
            df.to_csv(
                os.path.join(base_path, _ENV_TABLE + ".csv"),
                index=False, lineterminator=_LINE_TERMINATOR,
            )
            self._env_rows = []

        # Agent tables (one per container) — name matches Melodie's
        # "Result_Simulator_<CamelContainer>"
        for container_name, rows in self._agent_rows.items():
            if not rows:
                continue
            df = pd.DataFrame(rows)
            table_name = f"Result_Simulator_{_underline_to_camel(container_name)}"
            df.to_csv(
                os.path.join(base_path, table_name + ".csv"),
                index=False, lineterminator=_LINE_TERMINATOR,
            )
        self._agent_rows = {}

        self._time_elapsed += time.time() - t0
