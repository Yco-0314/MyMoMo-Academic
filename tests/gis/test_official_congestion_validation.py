import json
import shutil
from pathlib import Path

import pytest

from abm_auto.gis._official_centerline_match import (
    SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
)
from abm_auto.gis._official_congestion_validation import (
    official_dynamic_congestion_validation_gate,
    official_dynamic_congestion_validation_report,
)


def _copy_centerline_fixture(tmp_path: Path) -> Path:
    source_dir = SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST.parent
    dest_parent = tmp_path / source_dir.parent.name
    shutil.copytree(source_dir.parent, dest_parent)
    return dest_parent / source_dir.name / "manifest.json"


def _write_manifest_override(path: Path, **overrides) -> Path:
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.update(overrides)
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return path


def test_official_dynamic_congestion_report_covers_observed_edges():
    report = official_dynamic_congestion_validation_report(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["observed_provenance"]["n_edges"] == 3
    assert report["metrics"]["coverage"] == 1.0
    assert report["metrics"]["matched_edges"] == 3
    assert report["metrics"]["missing_edges"] == []
    assert report["simulated_total"] == 3.0
    assert report["dynamic_result"]["arrived"] == 3
    assert report["dynamic_result"]["stranded"] == 0
    assert "not traffic-flow validity" in report["boundary_note"]


def test_official_dynamic_congestion_parameters_change_loss():
    low = official_dynamic_congestion_validation_report(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
        agents_per_edge=1,
    )
    high = official_dynamic_congestion_validation_report(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
        agents_per_edge=2,
    )

    assert low["ok"] is True
    assert high["ok"] is True
    assert high["simulated_total"] > low["simulated_total"]
    assert high["loss"] != low["loss"]


def test_official_dynamic_congestion_report_includes_edge_diagnostics():
    report = official_dynamic_congestion_validation_report(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    rows = report["edge_diagnostics"]
    assert len(rows) == 3
    json.dumps(rows)
    assert {row["street"] for row in rows} == {
        "15TH AVE NE",
        "17TH AVE S",
        "MARINE VIEW DR SW",
    }
    assert {row["objectid"] for row in rows} == {9659868, 9638977, 9645707}
    for row in rows:
        assert isinstance(row["edge"], list)
        assert len(row["edge"]) == 2
        assert isinstance(row["edge"][0], list)
        assert "edge_key" in row
        assert row["absolute_error"] == abs(row["residual"])
        assert row["relative_error"] >= 0.0


def test_official_dynamic_congestion_report_marks_worst_edge():
    report = official_dynamic_congestion_validation_report(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    rows = report["edge_diagnostics"]
    worst = max(rows, key=lambda row: row["absolute_error"])
    assert report["worst_edge"] == worst
    assert report["worst_edge"]["street"] == "15TH AVE NE"
    assert report["worst_edge"]["observed_value"] == 5497.0


def test_official_dynamic_congestion_gate_passes_with_boundary_text():
    ok, desc = official_dynamic_congestion_validation_gate(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    assert ok, desc
    assert "official dynamic congestion validation smoke passed" in desc
    assert "worst_edge_street=15TH AVE NE" in desc
    assert "max_absolute_error=" in desc
    assert "not traffic-flow validity" in desc
    assert "not congestion calibration" in desc


def test_official_dynamic_congestion_report_fails_before_model_when_centerline_match_fails(
    tmp_path,
):
    manifest_path = _copy_centerline_fixture(tmp_path)
    _write_manifest_override(manifest_path, expected_max_match_distance_m=0.000001)

    report = official_dynamic_congestion_validation_report(manifest_path)

    assert report["ok"] is False
    assert "centerline edge match" in report["reason"]
    assert report["dynamic_result"] is None
    assert report["metrics"] is None
    assert report["edge_diagnostics"] is None
    assert report["worst_edge"] is None
    assert report["centerline_report"]["diagnostics"]["coverage"] == 1.0


@pytest.mark.parametrize("agents_per_edge", [0, -1, True, 1.5, "2"])
def test_official_dynamic_congestion_rejects_invalid_agents_per_edge(
    agents_per_edge,
):
    with pytest.raises(
        ValueError,
        match="agents_per_edge must be a positive integer",
    ):
        official_dynamic_congestion_validation_report(
            SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
            agents_per_edge=agents_per_edge,
        )
