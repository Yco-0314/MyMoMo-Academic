"""Structured NetLogo Interface-tab controls ingest.

These tests pin a non-executing controls spec. They do not require NetLogo to be
installed and do not claim procedure/parser compatibility.
"""
from __future__ import annotations

from pathlib import Path

from abm_auto.ingest.netlogo import parse_nlogo, to_story_md


def _write_text_nlogo(tmp_path: Path, interface: str) -> Path:
    path = tmp_path / "controls_demo.nlogo"
    path.write_text(
        "\n".join([
            "globals [ total ]",
            "@#$#@#$#@",
            interface.strip(),
            "@#$#@#$#@",
            "## WHAT IS IT?",
            "",
            "Controls fixture.",
        ]),
        encoding="utf-8",
    )
    return path


def test_text_nlogo_parses_structured_controls_and_legacy_fields(tmp_path):
    interface = """
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
"""

    model = parse_nlogo(_write_text_nlogo(tmp_path, interface))

    assert [s.name for s in model.controls.sliders] == ["speed"]
    slider = model.controls.sliders[0]
    assert slider.label == "Speed"
    assert slider.minimum.to_dict() == {"raw": "0", "number": 0.0}
    assert slider.maximum.to_dict() == {"raw": "population - 1", "number": None}
    assert slider.default.to_dict() == {"raw": "5", "number": 5.0}
    assert slider.step.to_dict() == {"raw": "0.5", "number": 0.5}
    assert slider.units == "ticks"
    assert slider.orientation == "HORIZONTAL"

    switch = model.controls.switches[0]
    assert switch.name == "show-links?"
    assert switch.label == "Show links?"
    assert switch.default is True

    chooser = model.controls.choosers[0]
    assert chooser.name == "mode"
    assert chooser.choices == ["low", "high"]
    assert chooser.default == "high"

    input_box = model.controls.input_boxes[0]
    assert input_box.name == "seed-value"
    assert input_box.default.to_dict() == {"raw": "42", "number": 42.0}
    assert input_box.multiline is False

    monitor = model.controls.monitors[0]
    assert monitor.name == "Turtle Count"
    assert monitor.reporter == "count turtles"

    plot = model.controls.plots[0]
    assert plot.name == "Population"
    assert plot.x_axis == "time"
    assert plot.y_axis == "count"
    assert plot.pens[0].name == "count"
    assert plot.pens[0].update_command == "plot count turtles"

    assert model.sliders == [
        {"name": "speed", "min": 0.0, "max": 0.0, "default": 5.0, "step": 0.5}
    ]
    assert model.plots == ["Population"]
    assert "speed" in to_story_md(model)
    assert "Population" in to_story_md(model)


def test_nlogox_parses_structured_controls(tmp_path):
    path = tmp_path / "controls_demo.nlogox"
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<model>
  <code>globals [ total ]</code>
  <info>## WHAT IS IT?\nXML controls fixture.</info>
  <widgets>
    <slider variable="speed" display="Speed" min="0" max="population - 1" default="5" step="0.5" units="ticks" direction="HORIZONTAL" />
    <switch variable="show-links?" display="Show links?" on="true" />
    <chooser variable="mode" display="Mode" choices="&quot;low&quot; &quot;high&quot;" currentChoice="high" />
    <inputBox variable="seed-value" display="Seed" default="42" multiline="false" />
    <monitor display="Turtle Count" reporter="count turtles" />
    <plot display="Population" xAxis="time" yAxis="count">
      <pen display="count" interval="1.0" mode="0" color="-16777216" update="plot count turtles" />
    </plot>
  </widgets>
</model>
""",
        encoding="utf-8",
    )

    model = parse_nlogo(path)

    assert model.controls.sliders[0].maximum.raw == "population - 1"
    assert model.controls.switches[0].default is True
    assert model.controls.choosers[0].choices == ["low", "high"]
    assert model.controls.choosers[0].default == "high"
    assert model.controls.input_boxes[0].default.raw == "42"
    assert model.controls.monitors[0].reporter == "count turtles"
    assert model.controls.plots[0].pens[0].update_command == "plot count turtles"
    assert model.sliders[0]["name"] == "speed"
    assert model.plots == ["Population"]


def test_committed_virus_fixture_preserves_richer_plot_and_expression_controls():
    model = parse_nlogo(Path("tests/fixtures/netlogo/Virus_on_a_Network.nlogo"))

    sliders = {s.name: s for s in model.controls.sliders}
    assert len(sliders) >= 7
    assert sliders["average-node-degree"].maximum.raw == "number-of-nodes - 1"
    assert sliders["average-node-degree"].maximum.number is None
    assert sliders["virus-spread-chance"].default.number == 2.5

    network_plot = next(p for p in model.controls.plots if p.name == "Network Status")
    assert [pen.name for pen in network_plot.pens] == ["susceptible", "infected", "resistant"]
    assert network_plot.pens[0].update_command.startswith("plot (count turtles")

    assert any(s["name"] == "average-node-degree" for s in model.sliders)
    assert "Network Status" in model.plots
