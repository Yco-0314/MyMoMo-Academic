"""Dogfood W4: does the runtime operator vocabulary cut the Yaman design's
AI-ASSUMPTION count below the viability gate?

PRE-REGISTERED expectation (before running):
- Baseline: the Yaman reproduce design produced 8-11 AI-ASSUMPTION tags across
  3 earlier refine attempts; the gate (limit 5) REJECTED it.
- Hypothesis: with the W2+W4 operator vocabulary now in
  phase1_design_reproduce.md, the semantic NN and the Moran turnover are
  declared as [paper-canonical] operators, NOT AI-ASSUMPTION → the count
  drops. Success = (a) count < baseline (ideally <=5, a gate pass), and
  (b) the operator lines are NOT tagged AI-ASSUMPTION.
- Honest caveat: the recipe tree is W3 (not built yet), so it may still be
  assumed; a residual count >5 driven by non-operator gaps would MOTIVATE W3,
  not refute W4. n=1 run (LLM is stochastic); baseline was 3 attempts.
"""
from __future__ import annotations

import json
import re

from abm_auto import config
from abm_auto.agents.designer import DesignAgent
from abm_auto.agents.viability_checker import count_assumptions
from abm_auto.llm import make_client
from abm_auto.runner.workspace import Workspace

HERE = "examples/reproduce_yaman_semantic_innovation"
story = open(f"{HERE}/story.md").read()

ws = Workspace.create(name="dogfood_w4_design")
ws.write_story(story)
(ws.path / "research_spec.json").write_text(json.dumps({"mode": "reproduce"}))

client = make_client(provider=config.LLM_PROVIDER, api_key=config.get_api_key(),
                     base_url=config.get_base_url(), timeout=180.0)
design = DesignAgent(client, ws).run()

raw = len(re.findall(r"AI[-_]ASSUMPTION", design, re.IGNORECASE))
hardened = count_assumptions(design)   # what the gate now actually counts
print("\n=== DOGFOOD W4 RESULT ===")
print(f"raw findall tags: {raw}   (old gate metric; baseline 8-11)")
print(f"HARDENED count:   {hardened}   (gate limit 5; n=1 run)")
print(f"gate verdict: {'PASS' if hardened <= 5 else 'FAIL'} (limit 5)")
n = hardened

print("operator mentions:")
for term in ("Moran", "FeedforwardLearner", "MoranProcess", "semantic model",
             "operator", "turnover"):
    print(f"  {term!r}: {len(re.findall(re.escape(term), design, re.IGNORECASE))}")

bad = [l for l in design.splitlines()
       if re.search(r"semantic model|moran|turnover|neural network", l, re.I)
       and re.search(r"AI[-_]ASSUMPTION", l, re.I)]
print(f"operator lines wrongly tagged AI-ASSUMPTION (want ~0): {len(bad)}")
for l in bad[:6]:
    print("  X", l.strip()[:110])

with open(f"{HERE}/dogfood_w4_DESIGN.md", "w") as f:
    f.write(design)
print(f"saved dogfood_w4_DESIGN.md ({len(design)} chars)")
