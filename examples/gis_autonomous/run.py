"""Autonomous GIS: one sentence -> GIS model, end to end.

story --(intent)--> GIS? --(LLM: DeepSeek)--> GISModelSpec --(template)--> code
      --(fidelity gate)--> --(run)--> science gate.

Reads the LLM key from env DEEPSEEK_API_KEY. External call; nothing committed.
Compares the LLM extraction against the locked expectations.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from abm_auto.llm import make_client
from abm_auto.gis._intent import detect_gis_intent
from abm_auto.gis._extractor import extract_gis_spec
from abm_auto.gis._templates import render
from abm_auto.gis._codegen_gate import gis_codegen_gate

REPO = str(Path(__file__).resolve().parent.parent.parent)

STORIES = [
    ("S1", "Simulate an epidemic spreading over the population density raster of a city.",
     {"spatial_type": "raster", "mechanism": "sir"}),
    ("S2", "Model commuters routing on a city road network loaded from /tmp/roads.shp.",
     {"spatial_type": "network", "mechanism": "routing_load", "data_path": "/tmp/roads.shp"}),
    ("S3", "An opinion-dynamics model on a random small-world network of agents.",
     {"is_gis": False}),
]


def main():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("set DEEPSEEK_API_KEY"); return
    client = make_client(provider="deepseek", api_key=key, timeout=60)

    for tag, story, expect in STORIES:
        print(f"\n=== {tag}: {story}")
        intent = detect_gis_intent(story)
        print(f"  intent: is_gis={intent.is_gis} type={intent.spatial_type}")
        if not intent.is_gis:
            ok = expect.get("is_gis") is False
            print(f"  {'MATCH' if ok else 'MISS'}: non-GIS -> stays on the normal path")
            continue

        spec = extract_gis_spec(story, client)
        match = (spec.spatial_type == expect["spatial_type"]
                 and spec.mechanism == expect["mechanism"]
                 and (("data_path" not in expect) or spec.data_path == expect["data_path"]))
        print(f"  extracted: type={spec.spatial_type} mech={spec.mechanism} data={spec.data_path!r}")
        print(f"  {'MATCH' if match else 'MISS'} vs locked expectation")

        files = render(spec)
        fok, reasons = gis_codegen_gate(files, spec)
        print(f"  fidelity gate: {'PASS' if fok else 'FAIL ' + str(reasons)}")

        if spec.spatial_type == "raster":   # fully runnable (synthetic)
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "main.py"; p.write_text(files["main.py"])
                out = subprocess.run([sys.executable, str(p)], capture_output=True,
                                     text=True, timeout=120,
                                     env={**os.environ, "PYTHONPATH": REPO})
                verdict = out.stdout.strip() or out.stderr[-200:]
                print(f"  FULL LOOP run -> {verdict}")


if __name__ == "__main__":
    main()
