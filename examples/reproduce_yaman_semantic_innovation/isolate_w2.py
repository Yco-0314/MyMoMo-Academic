"""Isolated W2 test: does the updated Stage-2 extractor emit learned_operators?

Bypasses the design-phase bug (empty DESIGN.md on a re-run) by feeding
Path-1's KNOWN-GOOD mechanism_spec.md + DESIGN.md — which fully describe
the trainable semantic NN — into the W2-updated MechanismExtractor
Stage-2 (`_extract_json_spec`). Same input the OLD extractor flattened
into scalars; the question is whether the NEW prompt + schema slot make
Stage-2 populate `learned_operators`.

Reads the real Path-1 artifacts; calls the real LLM; prints the real
output. No assertion of success — prints what actually came back so P8
can be scored honestly.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from abm_auto.agents.mechanism_extractor import MechanismExtractor
from abm_auto.runner.workspace import Workspace
from abm_auto import config
from abm_auto.llm import make_client

# Path-1 workspace whose viability passed and whose DESIGN.md fully
# describes the NN (semantic_model: feedforward 16-unit ReLU + item_embeddings).
PATH1_WS = REPO / "workspace" / "20260603_005144_c0e498"


def main() -> int:
    design = (PATH1_WS / "DESIGN.md").read_text(encoding="utf-8")
    markdown_spec = (PATH1_WS / "mechanism_spec.md").read_text(encoding="utf-8")
    print(f"DESIGN.md: {len(design)} chars | mechanism_spec.md: {len(markdown_spec)} chars")
    print(f"design mentions semantic NN: "
          f"{'semantic_model' in design and ('神经网络' in design or 'feedforward' in design.lower())}")

    # Build an extractor bound to a scratch workspace (it only needs call_llm +
    # prompt loading for Stage-2; we call the private method directly).
    ws = Workspace.create(name="isolate_w2_stage2")
    client = make_client(
        provider=config.LLM_PROVIDER,
        api_key=config.get_api_key(),
        base_url=config.get_base_url(),
        timeout=120.0,
    )
    extractor = MechanismExtractor(client, ws)

    print("\nRunning updated Stage-2 _extract_json_spec (real LLM)...", flush=True)
    spec, status = extractor._extract_json_spec(markdown_spec, design)
    print(f"\nStage-2 status: {status}")
    if spec is None:
        print("Stage-2 returned None (no usable spec).")
        return 1

    los = spec.learned_operators
    print(f"\n=== P8 RESULT ===")
    print(f"learned_operators count: {len(los)}")
    for lo in los:
        print(f"  - name={lo.name!r} n_items={lo.n_items!r} "
              f"embed_dim={lo.embed_dim} hidden_dim={lo.hidden_dim} lr={lo.learning_rate}")
    print(f"\nagent_state_vars: {[(v.name, v.type) for v in spec.agent_state_vars]}")
    # save the produced json for the record
    out = PATH1_WS.parent / "isolate_w2_spec.json"
    out.write_text(spec.to_json(), encoding="utf-8")
    print(f"\nwrote {out}")
    print(f"\nP8 verdict: {'CONFIRMED (learned_operators emitted)' if los else 'FALSIFIED (still empty)'}")
    return 0 if los else 2


if __name__ == "__main__":
    sys.exit(main())
