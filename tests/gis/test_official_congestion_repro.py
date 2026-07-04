import json
import shutil
from pathlib import Path

import pytest

from abm_auto.gis._official_congestion_repro import (
    OFFICIAL_DYNAMIC_CONGESTION_REPRO_SCHEMA,
    SEATTLE_SDOT_2023_DYNAMIC_CONGESTION_REPRO_MANIFEST,
    load_official_dynamic_congestion_repro_manifest,
    official_dynamic_congestion_repro_gate,
    official_dynamic_congestion_repro_report,
)


def _copy_repro_fixture(tmp_path: Path) -> Path:
    source_dir = SEATTLE_SDOT_2023_DYNAMIC_CONGESTION_REPRO_MANIFEST.parent
    dest_parent = tmp_path / source_dir.parent.name
    shutil.copytree(source_dir.parent, dest_parent)
    return dest_parent / source_dir.name / "manifest.json"


def _write_manifest_override(path: Path, **overrides) -> Path:
    raw = json.loads(path.read_text(encoding="utf-8"))
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(raw.get(key), dict):
            raw[key].update(value)
        else:
            raw[key] = value
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return path


def test_official_dynamic_congestion_repro_manifest_loads():
    manifest = load_official_dynamic_congestion_repro_manifest(
        SEATTLE_SDOT_2023_DYNAMIC_CONGESTION_REPRO_MANIFEST
    )

    assert manifest["schema"] == OFFICIAL_DYNAMIC_CONGESTION_REPRO_SCHEMA
    assert (
        manifest["dataset"]
        == "Seattle SDOT 2023 FLOWMAP dynamic congestion validation smoke"
    )
    assert Path(manifest["centerline_match_manifest_path"]).exists()
    assert manifest["run"]["agents_per_edge"] == 1
    assert manifest["run"]["comparison_agents_per_edge"] == 2
    assert manifest["expected"]["expected_n_edges"] == 3
    assert manifest["expected"]["expected_worst_edge_objectid"] == 9659868


def test_official_dynamic_congestion_repro_report_passes_with_diagnostics():
    report = official_dynamic_congestion_repro_report(
        SEATTLE_SDOT_2023_DYNAMIC_CONGESTION_REPRO_MANIFEST
    )

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["summary"]["n_edges"] == 3
    assert report["summary"]["low_simulated_total"] == 3.0
    assert report["summary"]["high_simulated_total"] == 6.0
    assert report["summary"]["loss_delta"] >= 0.0001
    assert report["summary"]["worst_edge_street"] == "15TH AVE NE"
    assert report["summary"]["worst_edge_objectid"] == 9659868
    assert len(report["low_report"]["edge_diagnostics"]) == 3
    assert len(report["high_report"]["edge_diagnostics"]) == 3
    json.dumps(report["summary"])


def test_official_dynamic_congestion_repro_gate_passes_with_boundary_text():
    ok, desc = official_dynamic_congestion_repro_gate(
        SEATTLE_SDOT_2023_DYNAMIC_CONGESTION_REPRO_MANIFEST
    )

    assert ok, desc
    assert "official dynamic congestion repro pack passed" in desc
    assert "worst_edge=15TH AVE NE/9659868" in desc
    assert "not traffic-flow validity" in desc
    assert "not congestion calibration" in desc


def test_official_dynamic_congestion_repro_report_fails_when_expected_loss_delta_is_too_strict(
    tmp_path,
):
    manifest_path = _copy_repro_fixture(tmp_path)
    _write_manifest_override(
        manifest_path,
        expected={"expected_min_loss_delta": 999.0},
    )

    report = official_dynamic_congestion_repro_report(manifest_path)

    assert report["ok"] is False
    assert "loss delta below expected_min_loss_delta" in report["reason"]


def test_official_dynamic_congestion_repro_manifest_rejects_invalid_agents_per_edge(
    tmp_path,
):
    manifest_path = _copy_repro_fixture(tmp_path)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["run"]["agents_per_edge"] = True
    manifest_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="agents_per_edge must be a positive integer",
    ):
        load_official_dynamic_congestion_repro_manifest(manifest_path)
