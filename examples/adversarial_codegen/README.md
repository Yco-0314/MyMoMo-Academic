# Adversarial codegen fixture

This story is engineered to provoke the LLM into producing
**every category of hallucination** cataloged in
`abm_auto/mymomo_knowledge/05-anti-patterns.md`:

| Phrasing in story.md | Targets anti-pattern |
|---|---|
| "Use a **WattsStrogatzNetwork** class" | `hallucinated_WattsStrogatzNetwork` (§1) |
| "Has a `generation_num` attribute" | `hallucinated_attr_generation_num` (§2) |
| "Track `agent.gen_num`" | `hallucinated_attr_gen_num` (§2) |
| "**Shuffle agents** at the start of each tick" | `hallucinated_method_shuffle` (§2) |
| "In an **after_setup hook**" | `hallucinated_hook_after_setup` (§2) |

## How to run

```bash
python -m abm_auto.cli run examples/adversarial_codegen/story.md \
  --iterations 1 --mode originate --no-lit-review
```

## Expected behavior (the gate this fixture exists for)

The anti-pattern validator in `abm_auto/codegen/anti_patterns.py` should
fire on at least 3 of the 5 targets during CoderVerifier GVR. GVR then
feeds the validator's descriptive feedback (which references the
`05-anti-patterns.md` sections) back to CoderAgent, which produces
corrected code on retry.

If the validator misses any targets that the story explicitly contains,
that's a real catalog gap — open an issue and add the missing pattern.

## Validation procedure

1. Run the command above; capture stdout + workspace.
2. Read `workspace/<id>/audit_ledger.jsonl`; search for `anti_pattern`
   issues raised by CoderVerifier GVR.
3. Assert at least the WattsStrogatzNetwork and method_shuffle catches
   appear in the GVR feedback trail.
4. Verify that the FINAL generated code in `workspace/<id>/model/core/`
   does NOT contain the targeted strings (i.e., the LLM corrected them
   after seeing validator feedback).

The dogfood report at `docs/dogfood/2026-05-29-codegen-path-virus.md`
documents the broader e2e methodology. This fixture is the
"adversarial-input variant" — proves the validator earns its keep when
the LLM actually does hallucinate.
