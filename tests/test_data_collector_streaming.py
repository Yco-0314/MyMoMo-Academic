"""Tests for DataCollector v2 — streaming + pluggable backends (ADR-009 Phase 3 / W6).

Core invariants under test:
  1. CSV default is byte-equal to the Phase 2 single-write path.
  2. Streaming CSV (chunked) == non-streaming CSV (single write), byte for byte.
  3. Parquet backend round-trips (write chunked → read back → same data).
  4. Streaming actually bounds memory (peak buffer << total rows).
  5. Backend factory rejects unknown backends; legacy SQLite target raises.

DataCollector needs model/scenario/config/environment back-refs. We build
minimal fakes rather than spin up a real Workspace + Simulator — the
collector's logic is pure given those back-refs.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from abm_auto.runtime._data_collector import (
    CsvTableWriter,
    DataCollector,
    ParquetTableWriter,
    _make_writer,
)

try:
    import pyarrow  # noqa: F401
    _HAS_PYARROW = True
except ImportError:
    _HAS_PYARROW = False


# ── minimal fakes ─────────────────────────────────────────────────────────


class _FakeEnv:
    def __init__(self) -> None:
        self.vals: dict = {}

    def to_dict(self, names: list[str]) -> dict:
        return {n: self.vals[n] for n in names}


class _FakeScenario:
    id = 0


class _FakeConfig:
    def __init__(self, out: Path) -> None:
        self._out = str(out)

    def output_tables_path(self) -> str:
        return self._out


class _FakeAgent:
    def __init__(self, agent_id: int, **attrs) -> None:
        self.id = agent_id
        for k, v in attrs.items():
            setattr(self, k, v)


class _FakeModel:
    def __init__(self, out: Path) -> None:
        self.scenario = _FakeScenario()
        self.run_id_in_scenario = 0
        self.environment = _FakeEnv()
        self.config = _FakeConfig(out)
        self.agents: list = []


# ── collector subclasses for tests ────────────────────────────────────────


class _EnvCollector(DataCollector):
    def setup(self) -> None:
        self.add_environment_property("count_s")
        self.add_environment_property("count_i")


class _StreamEnvCollector(_EnvCollector):
    flush_every = 10


class _ParquetEnvCollector(_EnvCollector):
    flush_every = 10
    backend_type = "parquet"


def _run_env(collector_cls, out: Path, n_ticks: int) -> DataCollector:
    """Drive a collector over n_ticks with a deterministic env series."""
    out.mkdir(parents=True, exist_ok=True)
    model = _FakeModel(out)
    dc = collector_cls()
    dc.model = model
    dc.scenario = model.scenario
    dc.config = model.config
    dc._setup()
    for t in range(n_ticks):
        model.environment.vals = {"count_s": 150 - t, "count_i": t}
        dc.collect(t)
    dc.save()
    return dc


# ── invariant 1 + 2: byte-equal default + streaming-equivalence ──────────


def test_streaming_csv_byte_equal_to_nonstreaming(tmp_path: Path) -> None:
    """The load-bearing test: chunked streaming output is byte-identical to
    the single-write output. If this passes, streaming is a pure
    memory optimisation with zero output change."""
    _run_env(_EnvCollector, tmp_path / "full", 50)
    _run_env(_StreamEnvCollector, tmp_path / "stream", 50)
    full = (tmp_path / "full" / "Result_Simulator_Environment.csv").read_bytes()
    stream = (tmp_path / "stream" / "Result_Simulator_Environment.csv").read_bytes()
    assert full == stream


def test_csv_default_uses_crlf(tmp_path: Path) -> None:
    """Phase 2 invariant: CRLF line endings (matches Melodie writer)."""
    _run_env(_EnvCollector, tmp_path / "full", 5)
    raw = (tmp_path / "full" / "Result_Simulator_Environment.csv").read_bytes()
    assert b"\r\n" in raw
    # header + 5 rows = 6 CRLF
    assert raw.count(b"\r\n") == 6


def test_csv_content_correct(tmp_path: Path) -> None:
    dc = _run_env(_EnvCollector, tmp_path / "full", 3)
    lines = (tmp_path / "full" / "Result_Simulator_Environment.csv").read_text().splitlines()
    assert lines[0] == "id_scenario,id_run,period,count_s,count_i"
    assert lines[1] == "0,0,0,150,0"
    assert lines[3] == "0,0,2,148,2"


def test_streaming_divisible_tick_count(tmp_path: Path) -> None:
    """flush_every divides n_ticks evenly (last collect triggers a flush,
    save() flush is then empty) — still byte-equal."""
    _run_env(_EnvCollector, tmp_path / "full", 30)
    _run_env(_StreamEnvCollector, tmp_path / "stream", 30)  # 30 % 10 == 0
    full = (tmp_path / "full" / "Result_Simulator_Environment.csv").read_bytes()
    stream = (tmp_path / "stream" / "Result_Simulator_Environment.csv").read_bytes()
    assert full == stream


def test_streaming_fewer_ticks_than_flush(tmp_path: Path) -> None:
    """n_ticks < flush_every: never mid-flushes, reduces to single write."""
    _run_env(_EnvCollector, tmp_path / "full", 5)
    _run_env(_StreamEnvCollector, tmp_path / "stream", 5)  # 5 < 10
    full = (tmp_path / "full" / "Result_Simulator_Environment.csv").read_bytes()
    stream = (tmp_path / "stream" / "Result_Simulator_Environment.csv").read_bytes()
    assert full == stream


# ── invariant 4: bounded memory ───────────────────────────────────────────


def test_streaming_bounds_peak_buffer(tmp_path: Path) -> None:
    full = _run_env(_EnvCollector, tmp_path / "full", 1000)
    stream = _run_env(_StreamEnvCollector, tmp_path / "stream", 1000)
    # Non-streaming buffers every row (1 env row/tick × 1000 ticks)
    assert full._peak_buffered_rows == 1000
    # Streaming caps near flush_every (peak tracked just before flush)
    assert stream._peak_buffered_rows <= 10
    assert stream._peak_buffered_rows < full._peak_buffered_rows


# ── invariant 3: Parquet round-trip ───────────────────────────────────────


@pytest.mark.skipif(not _HAS_PYARROW, reason="pyarrow not installed")
def test_parquet_round_trips(tmp_path: Path) -> None:
    import pyarrow.parquet as pq

    _run_env(_ParquetEnvCollector, tmp_path / "pq", 50)
    path = tmp_path / "pq" / "Result_Simulator_Environment.parquet"
    assert path.exists()
    df = pq.read_table(path).to_pandas()
    assert len(df) == 50
    assert list(df["count_s"]) == [150 - t for t in range(50)]
    assert list(df["period"]) == list(range(50))


@pytest.mark.skipif(not _HAS_PYARROW, reason="pyarrow not installed")
def test_parquet_matches_csv_data(tmp_path: Path) -> None:
    """Parquet and CSV backends produce the same logical data."""
    import pandas as pd
    import pyarrow.parquet as pq

    _run_env(_EnvCollector, tmp_path / "csv", 40)
    _run_env(_ParquetEnvCollector, tmp_path / "pq", 40)
    csv_df = pd.read_csv(tmp_path / "csv" / "Result_Simulator_Environment.csv")
    pq_df = pq.read_table(tmp_path / "pq" / "Result_Simulator_Environment.parquet").to_pandas()
    pd.testing.assert_frame_equal(
        csv_df.reset_index(drop=True), pq_df.reset_index(drop=True), check_dtype=False,
    )


# ── invariant 5: backend factory + legacy guard ──────────────────────────


def test_make_writer_csv(tmp_path: Path) -> None:
    w = _make_writer("csv", str(tmp_path), "T")
    assert isinstance(w, CsvTableWriter)


@pytest.mark.skipif(not _HAS_PYARROW, reason="pyarrow not installed")
def test_make_writer_parquet(tmp_path: Path) -> None:
    w = _make_writer("parquet", str(tmp_path), "T")
    assert isinstance(w, ParquetTableWriter)


def test_make_writer_unknown_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown backend_type"):
        _make_writer("mongodb", str(tmp_path), "T")


def test_legacy_sqlite_target_raises() -> None:
    with pytest.raises(ValueError, match="SQLite"):
        DataCollector(target="sqlite")


def test_default_target_and_backend() -> None:
    dc = DataCollector()
    assert dc.backend_type == "csv"
    assert dc.flush_every is None


# ── agent-table streaming (the real memory hog) ──────────────────────────


class _AgentCollector(DataCollector):
    def setup(self) -> None:
        self.add_environment_property("count_s")
        self.add_agent_property("agents", "state")


class _StreamAgentCollector(_AgentCollector):
    flush_every = 5


def _run_with_agents(collector_cls, out: Path, n_ticks: int, n_agents: int) -> DataCollector:
    out.mkdir(parents=True, exist_ok=True)
    model = _FakeModel(out)
    model.agents = [_FakeAgent(i, state=0) for i in range(n_agents)]
    dc = collector_cls()
    dc.model = model
    dc.scenario = model.scenario
    dc.config = model.config
    dc._setup()
    for t in range(n_ticks):
        model.environment.vals = {"count_s": 150 - t}
        for a in model.agents:
            a.state = t % 3
        dc.collect(t)
    dc.save()
    return dc


def test_agent_table_streaming_byte_equal(tmp_path: Path) -> None:
    _run_with_agents(_AgentCollector, tmp_path / "full", 20, 10)
    _run_with_agents(_StreamAgentCollector, tmp_path / "stream", 20, 10)
    for name in ("Result_Simulator_Environment.csv", "Result_Simulator_Agents.csv"):
        full = (tmp_path / "full" / name).read_bytes()
        stream = (tmp_path / "stream" / name).read_bytes()
        assert full == stream, f"{name} differs between streaming and non-streaming"


def test_agent_table_streaming_bounds_memory(tmp_path: Path) -> None:
    # 10 agents × 50 ticks = 500 agent rows + 50 env rows = 550 buffered if full
    full = _run_with_agents(_AgentCollector, tmp_path / "full", 50, 10)
    stream = _run_with_agents(_StreamAgentCollector, tmp_path / "stream", 50, 10)
    assert full._peak_buffered_rows == 550  # 50 env + 500 agent
    # streaming: flush every 5 ticks → peak ≈ 5 env + 50 agent = 55
    assert stream._peak_buffered_rows <= 55
    assert stream._peak_buffered_rows < full._peak_buffered_rows
