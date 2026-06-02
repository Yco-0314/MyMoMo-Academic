# Dogfood report: codegen path on the virus-on-a-network story

**Date**: 2026-05-30 00:10  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780070728`

## TL;DR

- Exit code: **1**
- Wall time: **315s** (5.2 min)
- LLM calls: **11** (est. **$0.02** at DeepSeek pricing)
- Calibration MSE: **—** (external-model baseline ≈ 100 ± 60)
- Halt: (none)

## Metrics

### Codegen health

| Metric | Value |
|---|---|
| Anti-pattern validator hits | **0** |
| Pipeline halted? | (none) |
| Phases logged | 8 occurrences |
| GVR retries by actor | `{'DesignerViability': 1, 'CoderVerifier': 1}` |

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
| Wall time | 315s (5.2 min) |
| LLM calls total | 11 |
| LLM calls by model | `{'deepseek-chat': 6, 'deepseek-reasoner': 5}` |
| Estimated USD cost | $0.02 |
| Report generated? | False (0 chars) |
| ARS package? | False |

### stderr preview

```
╭───────────────────── Traceback (most recent call last) ──────────────────────╮
│ /home/user/Documents/Social Simulation /mymomo-academic/abm_auto/cli.py:87   │
│ in run                                                                       │
│                                                                              │
│    84 │   │   external_model_path=external_model,                            │
│    85 │   │   observed_path=str(observed) if observed else None,             │
│    86 │   )                                                                  │
│ ❱  87 │   workspace_path = pipeline.run()                                    │
│    88 │   console.print(f"\n[bold]Output directory:[/bold] {workspace_path}" │
│    89                                                                        │
│    90                                                                        │
│                                                                              │
│ /home/user/Documents/Socia
```

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
