"""Tests for multi-fidelity calibration primitives.

Covers:
  - Fidelity dataclass (factory presets, frozen semantics)
  - _narrow_priors (centered narrowing, clipping to bounds, robustness)
  - SimulatorWrapper._apply_fidelity (period scaling, no-op cases)
  - SimulatorWrapper.restore_periods_to_base (post-MF cleanup)

End-to-end fit() with MF is exercised via tests/e2e/cross_domain_lean.py.
"""
from __future__ import annotations

import pandas as pd
import pytest

from abm_auto.calibration.calibrator import _narrow_priors
from abm_auto.calibration.simulator import SimulatorWrapper
from abm_auto.calibration.types import Fidelity


# ── Fidelity dataclass ──────────────────────────────────────────────────


def test_fidelity_presets_have_expected_periods_scale() -> None:
    # Tuned conservative post-ADR-008 first cross-domain run (SIR regression
    # at 0.2 coarse). Coarse=0.4 captures most ABM dynamics; medium=0.7
    # reaches late-stage relaxation.
    assert Fidelity.coarse().periods_scale == 0.4
    assert Fidelity.medium().periods_scale == 0.7
    assert Fidelity.full().periods_scale == 1.0


def test_fidelity_presets_have_distinct_labels() -> None:
    labels = {Fidelity.coarse().label, Fidelity.medium().label, Fidelity.full().label}
    assert labels == {"coarse", "medium", "full"}


def test_fidelity_is_frozen() -> None:
    """Immutability protects MF schedule from accidental mutation mid-run."""
    f = Fidelity.coarse()
    with pytest.raises(Exception):
        f.periods_scale = 0.99  # type: ignore[misc]


# ── _narrow_priors ──────────────────────────────────────────────────────


def test_narrow_priors_centers_on_best_params() -> None:
    priors = {"x": {"min": 0.0, "max": 10.0}}
    out = _narrow_priors(priors, around={"x": 5.0}, factor=0.2)
    # half-width = 10 * 0.2 / 2 = 1.0, so [4.0, 6.0]
    assert out["x"]["min"] == pytest.approx(4.0)
    assert out["x"]["max"] == pytest.approx(6.0)


def test_narrow_priors_clips_to_original_bounds_on_left() -> None:
    """A best near the lower edge can't push the new range past the original."""
    priors = {"x": {"min": 0.0, "max": 10.0}}
    out = _narrow_priors(priors, around={"x": 0.5}, factor=0.5)
    # half = 2.5, raw range = [-2.0, 3.0], clipped → [0.0, 3.0]
    assert out["x"]["min"] == 0.0
    assert out["x"]["max"] == pytest.approx(3.0)


def test_narrow_priors_clips_to_original_bounds_on_right() -> None:
    priors = {"x": {"min": 0.0, "max": 10.0}}
    out = _narrow_priors(priors, around={"x": 9.0}, factor=0.5)
    # half = 2.5, raw [6.5, 11.5], clipped → [6.5, 10.0]
    assert out["x"]["min"] == pytest.approx(6.5)
    assert out["x"]["max"] == 10.0


def test_narrow_priors_preserves_unbounded_params() -> None:
    """If `around` is missing a key, that prior stays at its original range."""
    priors = {"x": {"min": 0.0, "max": 10.0}, "y": {"min": 1.0, "max": 2.0}}
    out = _narrow_priors(priors, around={"x": 5.0}, factor=0.2)
    assert out["x"]["min"] == pytest.approx(4.0)
    assert out["x"]["max"] == pytest.approx(6.0)
    # y was not in `around`, so it stays untouched
    assert out["y"]["min"] == 1.0
    assert out["y"]["max"] == 2.0


def test_narrow_priors_falls_back_on_degenerate_range() -> None:
    """Too-narrow factor → fall back to original range, never zero-width."""
    priors = {"x": {"min": 0.0, "max": 10.0}}
    out = _narrow_priors(priors, around={"x": 5.0}, factor=0.001)
    # half-width 0.005 produces [4.995, 5.005], width 0.01 = 0.1% of original
    # Below the 1% safety threshold → fall back to [0, 10]
    assert out["x"]["min"] == 0.0
    assert out["x"]["max"] == 10.0


def test_narrow_priors_handles_zero_width_input() -> None:
    """Degenerate input (min == max) doesn't crash — passes through."""
    priors = {"x": {"min": 5.0, "max": 5.0}}
    out = _narrow_priors(priors, around={"x": 5.0}, factor=0.25)
    assert out["x"]["min"] == 5.0
    assert out["x"]["max"] == 5.0


# ── SimulatorWrapper._apply_fidelity ────────────────────────────────────


class _FakeWorkspace:
    """Tiny fake workspace just enough to give the simulator a CSV path."""
    def __init__(self, csv_path) -> None:
        self.model_dir = csv_path.parent.parent.parent


def _make_sim(csv_path, fidelity: Fidelity | None = None) -> SimulatorWrapper:
    ws = _FakeWorkspace(csv_path)
    sim = SimulatorWrapper.__new__(SimulatorWrapper)
    # Bypass __init__ to avoid needing an executor for these pure-logic tests
    sim.workspace = ws
    sim.executor = None
    sim._run_counter = 0
    sim.summary_fn = None
    sim.expected_rows = None
    sim.fidelity = fidelity
    sim._base_periods = None
    return sim


def test_apply_fidelity_noop_when_fidelity_is_none(tmp_path) -> None:
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"periods": [250], "alpha": [0.5]}).to_csv(csv, index=False)
    sim = _make_sim(csv, fidelity=None)
    out = sim._apply_fidelity({"alpha": 0.3})
    assert out == {"alpha": 0.3}  # no periods injection


def test_apply_fidelity_noop_when_full(tmp_path) -> None:
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"periods": [250], "alpha": [0.5]}).to_csv(csv, index=False)
    sim = _make_sim(csv, fidelity=Fidelity.full())
    out = sim._apply_fidelity({"alpha": 0.3})
    assert "periods" not in out  # full → no injection (CSV already has base)


def test_apply_fidelity_scales_periods_for_coarse(tmp_path) -> None:
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"periods": [250], "alpha": [0.5]}).to_csv(csv, index=False)
    sim = _make_sim(csv, fidelity=Fidelity.coarse())
    out = sim._apply_fidelity({"alpha": 0.3})
    assert out["periods"] == 100  # 250 * 0.4
    assert out["alpha"] == 0.3


def test_apply_fidelity_scales_periods_for_medium(tmp_path) -> None:
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"periods": [250], "alpha": [0.5]}).to_csv(csv, index=False)
    sim = _make_sim(csv, fidelity=Fidelity.medium())
    out = sim._apply_fidelity({"alpha": 0.3})
    assert out["periods"] == 175  # 250 * 0.7


def test_apply_fidelity_honors_caller_override(tmp_path) -> None:
    """If params already has `periods`, fidelity scaling is bypassed."""
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"periods": [250], "alpha": [0.5]}).to_csv(csv, index=False)
    sim = _make_sim(csv, fidelity=Fidelity.coarse())
    out = sim._apply_fidelity({"alpha": 0.3, "periods": 77})
    assert out["periods"] == 77  # caller wins


def test_apply_fidelity_enforces_minimum_periods(tmp_path) -> None:
    """Scaling a tiny CSV `periods` down further must not produce 0 or negative."""
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"periods": [5], "alpha": [0.5]}).to_csv(csv, index=False)
    sim = _make_sim(csv, fidelity=Fidelity.coarse())
    out = sim._apply_fidelity({"alpha": 0.3})
    assert out["periods"] >= 2  # floor=2


def test_apply_fidelity_silent_noop_when_no_periods_column(tmp_path) -> None:
    """Models without a `periods` column (rare) shouldn't error — just skip."""
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"alpha": [0.5]}).to_csv(csv, index=False)
    sim = _make_sim(csv, fidelity=Fidelity.coarse())
    out = sim._apply_fidelity({"alpha": 0.3})
    assert "periods" not in out


# ── SimulatorWrapper.restore_periods_to_base ────────────────────────────


def test_restore_periods_to_base_overwrites_scaled_value(tmp_path) -> None:
    """Simulates MF leaving coarse periods in CSV, then restoring."""
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"periods": [250], "alpha": [0.5]}).to_csv(csv, index=False)
    sim = _make_sim(csv)
    # Snapshot base, then write a "stale" coarse value as if a coarse sim ran
    sim._ensure_base_periods()
    pd.DataFrame({"periods": [50], "alpha": [0.5]}).to_csv(csv, index=False)

    sim.restore_periods_to_base()
    df = pd.read_csv(csv)
    assert int(df["periods"].iloc[0]) == 250  # restored


def test_restore_periods_to_base_noop_when_no_snapshot(tmp_path) -> None:
    """If MF never ran (no snapshot), restore is a no-op — CSV untouched."""
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"periods": [42]}).to_csv(csv, index=False)
    sim = _make_sim(csv)
    # No _ensure_base_periods called → _base_periods stays None
    sim.restore_periods_to_base()
    df = pd.read_csv(csv)
    assert int(df["periods"].iloc[0]) == 42  # unchanged


def test_restore_periods_to_base_idempotent_when_already_at_base(tmp_path) -> None:
    """Calling restore twice doesn't error or thrash the CSV."""
    csv = tmp_path / "data" / "input" / "SimulatorScenarios.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame({"periods": [200]}).to_csv(csv, index=False)
    sim = _make_sim(csv)
    sim._ensure_base_periods()
    sim.restore_periods_to_base()
    sim.restore_periods_to_base()  # second call must be silent
    df = pd.read_csv(csv)
    assert int(df["periods"].iloc[0]) == 200
