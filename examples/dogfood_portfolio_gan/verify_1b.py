"""Verify 1b end-to-end: does the LLM CoverageExtractor catch the GAN (so the
gate HALTs), and pass Yaman? Real LLM. The deterministic core is already tested;
this confirms the PROMPT gives good recall (the evidence half actually works)."""
from __future__ import annotations

from abm_auto import config
from abm_auto.agents.coverage_extractor import CoverageExtractor
from abm_auto.codegen.coverage_gate import CoverageGate, merge_mechanisms, recall_floor
from abm_auto.llm import make_client
from abm_auto.runner.workspace import Workspace

client = make_client(provider=config.LLM_PROVIDER, api_key=config.get_api_key(),
                     base_url=config.get_base_url(), timeout=120.0)
ws = Workspace.create(name="verify_1b")
ext = CoverageExtractor(client, ws)

cases = {
    "GAN":   "examples/dogfood_portfolio_gan/dogfood_DESIGN.md",
    "Yaman": "examples/reproduce_yaman_semantic_innovation/dogfood_w4_DESIGN.md",
}
for label, path in cases.items():
    prose = open(path).read()
    llm = ext.extract(prose)                         # the LLM evidence
    mechs = merge_mechanisms(llm, recall_floor(prose))
    v = CoverageGate().check(mechs)
    print(f"\n=== {label} ===")
    print("LLM extracted:", [(m.capability, sorted(m.markers), m.std_algorithm) for m in llm])
    print("verdict:", "PASS" if v.passed else "HALT", "| uncovered caps:",
          sorted({m.capability for m in mechs if m.name in v.uncovered}))
