"""Boundary dogfood: what does abm-auto's design phase do with a conditional GAN?

PRE-REGISTERED expectation (before running):
- The model is a 4-component conditional GAN (VAE market model + Carhart
  factors, attention strategy encoder -> 8-dim latent, portfolio decoder,
  discriminator) trained on proprietary fund data — far beyond the runtime's
  only learned operator (FeedforwardLearner, a single-hidden-layer item->item
  predictor).
- Hypothesis: the design phase hits the LEARNED-OPERATOR CEILING. Most likely
  one of: (a) it FLATTENS the GAN onto FeedforwardLearner / a vague "neural
  network" (W2-wall redux at a higher level); (b) it piles up AI-ASSUMPTION
  tags (deep architecture + proprietary data = many gaps); (c) the viability
  gate REJECTS it (under-specified / not reproducible from a story).
- A clear boundary finding either way: the conditional GAN is beyond the
  operator vocabulary. n=1 (LLM stochastic).
"""
from __future__ import annotations

import json
import re

from abm_auto import config
from abm_auto.agents.designer import DesignAgent
from abm_auto.agents.viability_checker import count_assumptions
from abm_auto.llm import make_client
from abm_auto.runner.workspace import Workspace

HERE = "examples/dogfood_portfolio_gan"
story = open(f"{HERE}/story.md").read()

ws = Workspace.create(name="dogfood_portfolio_gan")
ws.write_story(story)
(ws.path / "research_spec.json").write_text(json.dumps({"mode": "reproduce"}))

client = make_client(provider=config.LLM_PROVIDER, api_key=config.get_api_key(),
                     base_url=config.get_base_url(), timeout=180.0)
design = DesignAgent(client, ws).run()

raw = len(re.findall(r"AI[-_]ASSUMPTION", design, re.IGNORECASE))
hardened = count_assumptions(design)
print("\n=== BOUNDARY DOGFOOD RESULT (portfolio GAN) ===")
print(f"raw AI-ASSUMPTION: {raw}   hardened: {hardened}   gate: {'PASS' if hardened <= 5 else 'FAIL'} (limit 5)")
print("how the GAN was handled (mentions):")
for term in ("FeedforwardLearner", "learned_operator", "GAN", "discriminator",
             "generator", "adversarial", "VAE", "attention", "neural"):
    print(f"  {term!r}: {len(re.findall(re.escape(term), design, re.IGNORECASE))}")
# is the GAN flattened onto the simple learned operator?
flat = re.findall(r"FeedforwardLearner", design, re.IGNORECASE)
print(f"flattened onto FeedforwardLearner? {'YES' if flat else 'no'}")

with open(f"{HERE}/dogfood_DESIGN.md", "w") as f:
    f.write(design)
print(f"saved dogfood_DESIGN.md ({len(design)} chars)")
