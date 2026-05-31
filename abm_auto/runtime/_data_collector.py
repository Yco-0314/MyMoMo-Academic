"""ABM Auto Runtime — standalone DataCollector with pluggable streaming backends.

Phase 2 of the ADR-009 engine roadmap replaced ``Melodie.DataCollector``
with a pandas-backed CSV-only implementation. Phase 3 (this file, also
ADR-011 wedge W6 "scale-portable") adds:

  - A ``TableWriter`` Protocol — the pluggable-backend seam.
  - ``CsvTableWriter`` (default) + ``ParquetTableWriter`` — two adapters,
    so the seam is real (not hypothetical).
  - **Streaming**: when ``flush_every`` is set, ``collect()`` flushes the
    row buffer to the backend periodically and clears it, so a million-
    tick trajectory does not accumulate a million rows in memory.

Design invariants
-----------------
1. **CSV default stays byte-equal.** With ``flush_every=None`` (default)
   the collector buffers everything and does ONE write at ``save()`` —
   byte-identical to the Phase 2 implementation (header=True, mode='w',
   CRLF). The byte-equal SIR fixture (tests/e2e/...) gates this.
2. **Streaming CSV == non-streaming CSV.** Chunked append produces the
   same bytes as a single write. Tested directly.
3. **Scale is configuration, not rewrite.** A user opts into streaming /
   Parquet by setting two class attributes on their DataCollector
   subclass; model + calibration code is untouched.

Config channel
--------------
``Model.create_data_collector(cls)`` instantiates ``cls()`` with no args
(Melodie convention), so configuration travels via class attributes:

    class BigRunCollector(DataCollector):
        flush_every = 1000        # flush every 1000 ticks
        backend_type = "parquet"  # columnar output
        def setup(self):
            self.add_environment_property("count_s")

Defaults (``flush_every=None``, ``backend_type="csv"``) reproduce Phase 2
behaviour exactly.

What stays dropped from Melodie (per ADR-009 Phase 2)
----------------------------------------------------
SQLite target, add_custom_collector, calc_time, get_single_agent_data.
SQLite remains a Protocol-ready slot (TableWriter) but is NOT built —
zero use in our codebase, deferred under anti-wedge A4 until a multi-
scenario relational-query need surfaces.

Downstream note
---------------
``SimulatorWrapper`` reads the CSV output. The Parquet backend round-
trips (write→read equal) but is not yet wired to the calibration reader;
that integration lands when a model actually selects ``backend_type=
"parquet"`` for a calibration run. CSV remains the calibration default.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Protocol, Type

import pandas as pd

# Output filename for the environment-properties table. Must match
# Melodie's ``MelodieInfra.db.DBConn.ENVIRONMENT_RESULT_TABLE`` constant
# so SimulatorWrapper's CSV-reading layer keeps working unchanged.
_ENV_TABLE = "Result_Simulator_Environment"

# Melodie's writer emits CRLF line endings (Python csv module default in
# text mode on the version Melodie ships). Pandas defaults to LF, which
# would break byte-equal regression with pre-swap reference CSVs. Force
# CRLF here so the swap stays a true drop-in.
_LINE_TERMINATOR = "\r\n"


def _underline_to_camel(s: str) -> str:
    """snake_case → CamelCase. Matches Melodie's util semantics for the
    agent-properties table filename (``Result_Simulator_<ContainerCamel>``).
    """
    return "".join(part.capitalize() for part in s.split("_"))


# ─────────────────────────────────────────────────────────────────────────
# TableWriter Protocol + adapters (the pluggable-backend seam)
# ─────────────────────────────────────────────────────────────────────────


class TableWriter(Protocol):
    """Writes rows for ONE output table, supporting incremental append.

    Lifecycle: ``write_chunk`` called 1+ times (each with a batch of
    rows), then ``finalize`` once. A non-streaming collector calls
    ``write_chunk`` exactly once with all rows; a streaming collector
    calls it repeatedly with bounded-size batches.
    """

    def write_chunk(self, rows: List[Dict[str, Any]]) -> None: ...
    def finalize(self) -> None: ...


class CsvTableWriter:
    """CSV adapter. First chunk writes header (mode='w'); subsequent
    chunks append headerless (mode='a'). Concatenation is byte-identical
    to a single ``DataFrame.to_csv`` of all rows — the single-chunk case
    reduces exactly to the Phase 2 write.
    """

    def __init__(self, path: str, lineterminator: str = _LINE_TERMINATOR) -> None:
        self.path = path
        self.lineterminator = lineterminator
        self._header_written = False

    def write_chunk(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        df = pd.DataFrame(rows)
        df.to_csv(
            self.path,
            index=False,
            header=not self._header_written,
            mode="w" if not self._header_written else "a",
            lineterminator=self.lineterminator,
        )
        self._header_written = True

    def finalize(self) -> None:
        # CSV needs no close; file handle is opened/closed per chunk by
        # pandas. Nothing to flush. Method exists for Protocol conformance.
        pass


class ParquetTableWriter:
    """Parquet adapter via pyarrow incremental ParquetWriter.

    Schema is pinned from the first chunk; later chunks are coerced to
    that schema so a column that looks int in one batch and float in
    another doesn't fork the file schema (raises if genuinely
    incompatible — that's a real data bug, not silenced).
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._writer = None  # pyarrow.parquet.ParquetWriter, lazy
        self._schema = None

    def write_chunk(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as e:  # pragma: no cover - env-dependent
            raise RuntimeError(
                "ParquetTableWriter requires pyarrow. Install with "
                "`pip install pyarrow`, or use backend_type='csv'."
            ) from e

        if self._schema is None:
            table = pa.Table.from_pylist(rows)
            self._schema = table.schema
            self._writer = pq.ParquetWriter(self.path, self._schema)
        else:
            table = pa.Table.from_pylist(rows, schema=self._schema)
        self._writer.write_table(table)

    def finalize(self) -> None:
        if self._writer is not None:
            self._writer.close()
            self._writer = None


def _make_writer(backend_type: str, base_path: str, table_name: str) -> TableWriter:
    """Factory: backend_type → a TableWriter for one table."""
    if backend_type == "csv":
        return CsvTableWriter(os.path.join(base_path, table_name + ".csv"))
    if backend_type == "parquet":
        return ParquetTableWriter(os.path.join(base_path, table_name + ".parquet"))
    raise ValueError(
        f"Unknown backend_type {backend_type!r}. Supported: 'csv', 'parquet'. "
        f"(SQLite is a Protocol-ready slot but not built — see module docstring.)"
    )


# ─────────────────────────────────────────────────────────────────────────
# DataCollector
# ─────────────────────────────────────────────────────────────────────────


class DataCollector:
    """Standalone DataCollector with pluggable streaming backends.

    Subclass and override :meth:`setup` to register collected properties.
    Optionally set ``flush_every`` (ticks between flushes) and
    ``backend_type`` ("csv" | "parquet") as class attributes to opt into
    streaming / columnar output. Defaults reproduce Phase 2 behaviour.

    Framework wires ``model``/``scenario``/``config`` back-refs via
    ``Model.create_data_collector``; from then on ``collect()`` /
    ``save()`` are framework-called.
    """

    _CORE_PROPERTIES_ = ["id_scenario", "id_run", "period"]

    # ── configuration (override in subclass) ──────────────────────────
    #: Ticks between streaming flushes. None = buffer all, write once at
    #: save() (Phase 2 behaviour; byte-equal CSV default).
    flush_every: Optional[int] = None
    #: Output backend. "csv" (default) | "parquet".
    backend_type: str = "csv"

    def __init__(self, target: Optional[str] = None):
        # `target` is the legacy Melodie knob ("sqlite"/"csv"); superseded
        # by `backend_type` but kept in the signature for source-compat.
        if target not in {None, "csv"}:
            raise ValueError(
                f"DataCollector legacy target only supports 'csv', got {target!r}. "
                f"Use the `backend_type` class attribute for 'parquet'. "
                f"SQLite was dropped in ADR-009 Phase 2 (unused)."
            )

        # Back-refs assigned by Model.create_data_collector
        self.model: Any = None
        self.scenario: Any = None
        self.config: Any = None

        # Registration tables — populated by user's setup()
        self._env_property_names: List[str] = []
        self._agent_property_specs: Dict[str, List[str]] = {}

        # Per-period buffers — flushed by save() (or mid-run if streaming)
        self._env_rows: List[Dict[str, Any]] = []
        self._agent_rows: Dict[str, List[Dict[str, Any]]] = {}

        # Active writers, created lazily on first flush, keyed by table name.
        # Persist across streaming flushes (CSV tracks header state, Parquet
        # holds the open file).
        self._writers: Dict[str, TableWriter] = {}
        self._ticks_since_flush = 0

        # Observability: peak buffered rows seen (lets tests assert that
        # streaming actually bounds memory).
        self._peak_buffered_rows = 0

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
        and resets counters."""
        self.setup()
        self._time_elapsed = 0.0
        self._ticks_since_flush = 0
        self._peak_buffered_rows = 0

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
        """Record env + agent properties for this period.

        When ``flush_every`` is set, flushes buffers to the backend every
        ``flush_every`` ticks so memory stays bounded for long runs.
        """
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

        self._track_peak_buffer()

        # Streaming flush check
        self._ticks_since_flush += 1
        if self.flush_every is not None and self._ticks_since_flush >= self.flush_every:
            self._flush()
            self._ticks_since_flush = 0

        self._time_elapsed += time.time() - t0

    # ── flush + save ──────────────────────────────────────────────────

    def _track_peak_buffer(self) -> None:
        buffered = len(self._env_rows) + sum(len(r) for r in self._agent_rows.values())
        if buffered > self._peak_buffered_rows:
            self._peak_buffered_rows = buffered

    def _flush(self) -> None:
        """Write current buffers to their backend writers (append) + clear.

        Writers are created lazily on first flush per table and persist
        (CSV tracks header state, Parquet holds the open file)."""
        base_path = self.model.config.output_tables_path()
        os.makedirs(base_path, exist_ok=True)

        if self._env_rows:
            writer = self._writers.get(_ENV_TABLE)
            if writer is None:
                writer = _make_writer(self.backend_type, base_path, _ENV_TABLE)
                self._writers[_ENV_TABLE] = writer
            writer.write_chunk(self._env_rows)
            self._env_rows = []

        for container_name, rows in self._agent_rows.items():
            if not rows:
                continue
            table_name = f"Result_Simulator_{_underline_to_camel(container_name)}"
            writer = self._writers.get(table_name)
            if writer is None:
                writer = _make_writer(self.backend_type, base_path, table_name)
                self._writers[table_name] = writer
            writer.write_chunk(rows)
        self._agent_rows = {k: [] for k in self._agent_rows}

    def save(self) -> None:
        """Flush any remaining buffered data + finalize all writers.

        With ``flush_every=None`` (default) this is the ONLY flush: a
        single ``write_chunk`` per table with all rows, header=True,
        mode='w' — byte-identical to the Phase 2 single-write path.
        """
        if not self.status:
            return
        t0 = time.time()

        self._flush()
        for writer in self._writers.values():
            writer.finalize()
        self._writers = {}

        self._time_elapsed += time.time() - t0
