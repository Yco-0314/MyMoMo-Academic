import pytest

from abm_auto.gis import _official_incident_validation as validation
from abm_auto.gis._official_incident_validation import (
    official_dynamic_incident_event_effect_gate,
    official_dynamic_incident_event_effect_report,
)


def test_default_report_runs_baseline_and_incident_models():
    report = official_dynamic_incident_event_effect_report()

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["n_matched_incidents"] == 2
    assert report["baseline_result"]["mean_arrival_t"] == 1
    assert report["incident_result"]["mean_arrival_t"] == 3
    assert report["effect"]["arrival_delay"] == 2
    assert report["effect"]["baseline_total_waiting"] == 1
    assert report["effect"]["incident_total_waiting"] == 3
    assert report["effect"]["waiting_delta"] == 2
    assert report["effect"]["incident_steps_with_closed_edges"] == [1, 2]
    assert report["effect"]["max_closed_edges"] == 1
    assert report["effect"]["changed"] is True
    assert report["params"]["reroute"] is False
    assert report["params"]["agent_nodes"] == [(0, 0)]
    assert report["params"]["safe_nodes"] == [(200, 0)]
    assert "not traffic-flow validity" in report["boundary_note"]


def test_default_gate_passes_with_boundary_text():
    ok, desc = official_dynamic_incident_event_effect_gate()

    assert ok, desc
    assert "official dynamic incident event effect smoke passed" in desc
    assert "matched_incidents=2" in desc
    assert "arrival_delay=2" in desc
    assert "waiting_delta=2" in desc
    assert "not traffic-flow validity" in desc
    assert "not production map matching" in desc
    assert "not real incident calibration" in desc


def test_report_fails_before_dynamic_model_when_intake_fails():
    geonet = validation._default_validation_geonet()
    geonet.crs = "EPSG:4326"

    report = official_dynamic_incident_event_effect_report(geonet=geonet)

    assert report["ok"] is False
    assert "official incident event intake failed" in report["reason"]
    assert report["baseline_result"] is None
    assert report["incident_result"] is None
    assert report["effect"] is None


def test_report_fails_when_no_matched_incidents(monkeypatch):
    def fake_report(manifest_path, geonet=None):
        return {
            "ok": True,
            "reason": "",
            "dataset": "fake",
            "source_agency": "fake agency",
            "geographic_scope": "fake scope",
            "matched_incidents": [],
            "boundary_note": "fake boundary",
        }

    monkeypatch.setattr(
        validation,
        "official_incident_event_edge_match_report",
        fake_report,
    )

    report = official_dynamic_incident_event_effect_report()

    assert report["ok"] is False
    assert report["reason"] == "official incident event intake produced no matched incidents"
    assert report["baseline_result"] is None
    assert report["incident_result"] is None
    assert report["effect"] is None


def test_gate_fails_when_incidents_have_no_effect(monkeypatch):
    def fake_report(manifest_path, geonet=None):
        return {
            "ok": True,
            "reason": "",
            "dataset": "fake",
            "source_agency": "fake agency",
            "geographic_scope": "fake scope",
            "matched_incidents": [
                {"t": 99, "edge": ((100, 0), (200, 0)), "closed": True},
                {"t": 100, "edge": ((100, 0), (200, 0)), "closed": False},
            ],
            "boundary_note": "fake boundary",
        }

    monkeypatch.setattr(
        validation,
        "official_incident_event_edge_match_report",
        fake_report,
    )

    ok, desc = official_dynamic_incident_event_effect_gate()

    assert ok is False
    assert desc == "official incident events did not affect dynamic incident output"


@pytest.mark.parametrize("agent_nodes", [[], [(999, 999)], "bad"])
def test_invalid_agent_nodes_fail(agent_nodes):
    with pytest.raises(ValueError, match="agent_nodes"):
        official_dynamic_incident_event_effect_report(agent_nodes=agent_nodes)


@pytest.mark.parametrize("safe_nodes", [[], [(999, 999)], "bad"])
def test_invalid_safe_nodes_fail(safe_nodes):
    with pytest.raises(ValueError, match="safe_nodes"):
        official_dynamic_incident_event_effect_report(safe_nodes=safe_nodes)


@pytest.mark.parametrize("kwargs", [{"n_steps": 0}, {"speed_m_per_tick": 0.0}])
def test_invalid_dynamic_parameters_fail(kwargs):
    with pytest.raises(ValueError):
        official_dynamic_incident_event_effect_report(**kwargs)
