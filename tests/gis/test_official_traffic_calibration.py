import json
import shutil
from pathlib import Path

from abm_auto.gis._official_centerline_match import (
    SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
)
from abm_auto.gis._official_traffic_calibration import (
    official_traffic_calibration_gate,
    official_traffic_calibration_report,
    official_traffic_observed_target_from_centerline_match,
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


def test_official_traffic_observed_target_preserves_centerline_provenance():
    loaded = official_traffic_observed_target_from_centerline_match(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    observed = loaded["observed"]
    assert observed.dataset == "Seattle SDOT 2023 FLOWMAP centerline match"
    assert observed.metric == "edge_load"
    assert observed.provenance()["n_edges"] == 3
    assert "Seattle_Streets_1/FeatureServer/0" in observed.source
    assert loaded["station_streets"] == {
        "sdot-342953": "15TH AVE NE",
        "sdot-342077": "17TH AVE S",
        "sdot-342019": "MARINE VIEW DR SW",
    }


def test_official_traffic_calibration_selects_scale_one():
    report = official_traffic_calibration_report(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["best_params"] == {"demand_scale": 1.0}
    assert report["best_loss"] == 0.0
    assert report["loss_improvement"] > 0.0
    assert report["calibration"]["best_metrics"]["coverage"] == 1.0
    assert report["calibration"]["n_evaluations"] == 3
    assert report["observed_provenance"]["n_edges"] == 3
    assert "not traffic-flow validity" in report["boundary_note"]


def test_official_traffic_calibration_accepts_custom_simulator_and_grid():
    def simulator(params, observed):
        return {
            edge: value + params["offset"]
            for edge, value in observed.edge_values.items()
        }

    report = official_traffic_calibration_report(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
        param_grid={"offset": [-100.0, 0.0, 100.0]},
        simulator=simulator,
    )

    assert report["ok"] is True
    assert report["best_params"] == {"offset": 0.0}
    assert report["best_loss"] == 0.0
    assert report["calibration"]["n_evaluations"] == 3


def test_official_traffic_calibration_fails_before_calibration_when_centerline_match_fails(tmp_path):
    manifest_path = _copy_centerline_fixture(tmp_path)
    _write_manifest_override(manifest_path, expected_max_match_distance_m=0.000001)

    report = official_traffic_calibration_report(manifest_path)

    assert report["ok"] is False
    assert "centerline edge match" in report["reason"]
    assert report["calibration"] is None
    assert report["centerline_report"]["diagnostics"]["coverage"] == 1.0


def test_official_traffic_calibration_gate_passes_with_boundary_text():
    ok, desc = official_traffic_calibration_gate(
        SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST
    )

    assert ok, desc
    assert "official traffic calibration bridge passed" in desc
    assert "Seattle SDOT 2023 FLOWMAP centerline match" in desc
    assert "best_params={'demand_scale': 1.0}" in desc
    assert "not traffic-flow validity" in desc
    assert "not congestion calibration" in desc
