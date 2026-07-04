from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from abm_auto.ingest.netlogo import NetLogoControlsSpec, parse_nlogo
from abm_auto.netlogo_gap_audit import audit_netlogo_model


def test_virus_fixture_gap_audit_reports_supported_semantic_families():
    model = parse_nlogo(Path("tests/fixtures/netlogo/Virus_on_a_Network.nlogo"))

    audit = audit_netlogo_model(model)

    assert audit.model_name == "Virus_on_a_Network"
    assert audit.can_run_natively is False
    assert {
        "agentset_ask",
        "controls_sliders",
        "link_agents",
        "link_neighbors",
        "metric_count_turtles_with",
        "network_generation_minimal",
        "random_selection",
        "ticks",
        "turtle_state",
    }.issubset(set(audit.supported))


def test_virus_fixture_gap_audit_reports_next_execution_gaps():
    model = parse_nlogo(Path("tests/fixtures/netlogo/Virus_on_a_Network.nlogo"))

    audit = audit_netlogo_model(model)

    assert {
        "agentset_expression_parser",
        "code_tab_procedure_execution",
        "network_generation",
        "random_number_semantics",
        "visual_layout",
    }.issubset(set(audit.gaps))
    assert "layout-spring" in audit.evidence["visual_layout"]
    assert "min-one-of" in audit.evidence["network_generation"]
    assert "n-of" in audit.evidence["random_selection"]
    assert "create-link-with" in audit.evidence["network_generation_minimal"]


def test_gap_audit_is_serializable_and_sorted():
    model = parse_nlogo(Path("tests/fixtures/netlogo/Virus_on_a_Network.nlogo"))

    data = audit_netlogo_model(model).to_dict()

    assert data["supported"] == sorted(data["supported"])
    assert data["gaps"] == sorted(data["gaps"])
    assert data["can_run_natively"] is False
    assert data["unclassified"]
    assert data["evidence"]["metric_count_turtles_with"] == ["count turtles with"]


def test_gap_audit_is_conservative_for_unclassified_code():
    model = SimpleNamespace(
        name="UnknownConstructs",
        code_text="ask turtles [ unknown-primitive ]\n",
        controls=NetLogoControlsSpec(),
    )

    audit = audit_netlogo_model(model)

    assert audit.can_run_natively is False
    assert audit.unclassified == ("code_tab_text",)


def test_gap_audit_ignores_comments_and_quoted_strings():
    model = SimpleNamespace(
        name="CommentsOnly",
        code_text='; layout-spring n-of min-one-of\nshow "random layout-spring"',
        controls=NetLogoControlsSpec(),
    )

    audit = audit_netlogo_model(model)

    assert "visual_layout" not in audit.gaps
    assert "random_selection" not in audit.gaps
    assert "network_generation" not in audit.gaps


def test_gap_audit_treats_to_report_as_code_tab_execution_gap():
    model = SimpleNamespace(
        name="ReporterOnly",
        code_text="to-report infected-count\n  report count turtles\nend",
        controls=NetLogoControlsSpec(),
    )

    audit = audit_netlogo_model(model)

    assert "code_tab_procedure_execution" in audit.gaps
    assert "to-report infected-count" in audit.evidence["code_tab_procedure_execution"]


def test_controls_slider_support_is_slider_specific():
    model = SimpleNamespace(
        name="MonitorOnly",
        code_text="",
        controls=SimpleNamespace(
            sliders=[],
            switches=[],
            choosers=[],
            input_boxes=[],
            monitors=[SimpleNamespace(name="infected", reporter="count turtles with [ infected? ]")],
            plots=[],
        ),
    )

    audit = audit_netlogo_model(model)

    assert "metric_count_turtles_with" in audit.supported
    assert "controls_sliders" not in audit.supported
