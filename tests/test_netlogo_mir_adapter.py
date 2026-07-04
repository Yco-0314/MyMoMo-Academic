"""NetLogo controls -> MIR adapter tests.

The adapter is semantic packaging only: no NetLogo execution, no codegen, and
no expression evaluation.
"""
from __future__ import annotations

from pathlib import Path

from abm_auto.ingest.netlogo import parse_nlogo
from abm_auto.mir import MIR
from abm_auto.mir._netlogo_adapter import netlogo_controls_to_mir, netlogo_model_to_mir


def _write_text_nlogo(tmp_path: Path) -> Path:
    path = tmp_path / "controls_demo.nlogo"
    path.write_text(
        """globals [ total ]
@#$#@#$#@
SLIDER
0
0
120
30
speed
Speed
0
population - 1
5
0.5
1
ticks
HORIZONTAL

SWITCH
0
40
120
70
show-links?
Show links?
1
1
-1000

CHOOSER
0
80
120
110
mode
Mode
"low" "high"
1

INPUTBOX
0
120
120
160
seed-value
42
1
0
Number

MONITOR
0
170
120
200
Turtle Count
count turtles
17
1
11

PLOT
0
210
200
340
Population
time
count
0.0
10.0
0.0
100.0
true
false
"" ""
PENS
"count" 1.0 0 -16777216 true "" "plot count turtles"
@#$#@#$#@
## WHAT IS IT?

Controls fixture.
""",
        encoding="utf-8",
    )
    return path


def test_netlogo_controls_map_to_mir_run_params_and_metrics(tmp_path):
    model = parse_nlogo(_write_text_nlogo(tmp_path))
    mir = netlogo_model_to_mir(model)

    assert mir.metadata.name == "controls_demo"
    assert mir.metadata.domain == "netlogo"
    assert mir.metadata.provenance["source"] == "netlogo_controls_to_mir"

    speed = mir.run.params["speed"]
    assert speed["kind"] == "slider"
    assert speed["label"] == "Speed"
    assert speed["maximum"] == {"raw": "population - 1", "number": None}
    assert speed["default"] == {"raw": "5", "number": 5.0}
    assert speed["units"] == "ticks"

    assert mir.run.params["show-links?"] == {
        "kind": "switch",
        "label": "Show links?",
        "default": True,
    }
    assert mir.run.params["mode"] == {
        "kind": "chooser",
        "label": "Mode",
        "choices": ["low", "high"],
        "default": "high",
    }
    assert mir.run.params["seed-value"]["default"] == {"raw": "42", "number": 42.0}

    monitor_metric = next(m for m in mir.metrics if m["kind"] == "monitor")
    assert monitor_metric == {
        "kind": "monitor",
        "name": "Turtle Count",
        "reporter": "count turtles",
    }
    plot_metric = next(m for m in mir.metrics if m["kind"] == "plot")
    assert plot_metric["name"] == "Population"
    assert plot_metric["pens"][0]["update_command"] == "plot count turtles"

    assert mir.trace["source_format"] == "netlogo"
    assert mir.trace["controls"]["sliders"][0]["maximum"]["raw"] == "population - 1"
    assert mir.extensions == {}
    assert mir.entities == []
    assert mir.state == []
    assert mir.relations == []
    assert mir.layers == []


def test_netlogo_controls_mir_survives_json_roundtrip(tmp_path):
    mir = netlogo_controls_to_mir(parse_nlogo(_write_text_nlogo(tmp_path)))
    restored = MIR.from_json(mir.to_json())

    assert restored.run.params["speed"]["maximum"]["raw"] == "population - 1"
    assert restored.run.params["speed"]["maximum"]["number"] is None
    assert restored.metrics == mir.metrics
    assert restored.trace["controls"] == mir.trace["controls"]
    assert restored.extensions == {}


def test_committed_virus_fixture_maps_controls_to_mir():
    model = parse_nlogo(Path("tests/fixtures/netlogo/Virus_on_a_Network.nlogo"))
    mir = netlogo_model_to_mir(model)

    avg_degree = mir.run.params["average-node-degree"]
    assert avg_degree["kind"] == "slider"
    assert avg_degree["maximum"]["raw"] == "number-of-nodes - 1"
    assert avg_degree["maximum"]["number"] is None

    network_plot = next(m for m in mir.metrics if m["kind"] == "plot" and m["name"] == "Network Status")
    assert [pen["name"] for pen in network_plot["pens"]] == [
        "susceptible",
        "infected",
        "resistant",
    ]
    assert network_plot["pens"][0]["update_command"].startswith("plot (count turtles")
