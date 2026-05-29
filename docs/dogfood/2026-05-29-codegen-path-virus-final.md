# Dogfood report: codegen path on BEHAVE 2025 virus story

**Date**: 2026-05-29 17:01  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780045287`

## TL;DR

- Exit code: **1**
- Wall time: **2s** (0.0 min)
- LLM calls: **0** (est. **$0.00** at DeepSeek pricing)
- Calibration MSE: **—** (external-model baseline ≈ 100 ± 60)
- Halt: (none)

## Metrics

### Codegen health

| Metric | Value |
|---|---|
| Anti-pattern validator hits | **0** |
| Pipeline halted? | (none) |
| Phases logged | 0 occurrences |
| GVR retries by actor | `(none)` |

### Calibration health

| Parameter | Truth | Got | Rel. err |
|---|---|---|---|
| `virus_spread_chance` | 4.4 | — | — |
| `recovery_chance` | 2.5 | — | — |
| `gain_resistance_chance` | 25.0 | — | — |

**Aggregate MSE**: —  
**Floor estimate** (from ADR-006): 100-200  
**External-model baseline** (commit 3c3c15c): 99 ± 59

### UX

| Metric | Value |
|---|---|
| Wall time | 2s (0.0 min) |
| LLM calls total | 0 |
| LLM calls by model | `(none)` |
| Estimated USD cost | $0.00 |
| Report generated? | False (0 chars) |
| ARS package? | False |

### stderr preview

```
╭───────────────────── Traceback (most recent call last) ──────────────────────╮
│ /home/user/Documents/Social Simulation /mymomo-academic/abm_auto/cli.py:65   │
│ in run                                                                       │
│                                                                              │
│    62 │   if timeout_llm is not None:                                        │
│    63 │   │   phase_timeouts["llm"] = timeout_llm                            │
│    64 │                                                                      │
│ ❱  65 │   pipeline = Pipeline(                                               │
│    66 │   │   story_path=story,                                              │
│    67 │   │   iterations=iterations,                                         │
│    68 │   │   model=model,                                                   │
│                                                                              │
│ /home/user/Documents/Socia
```

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
