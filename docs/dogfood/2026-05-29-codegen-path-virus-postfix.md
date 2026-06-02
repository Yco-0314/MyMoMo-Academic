# Dogfood report: codegen path on the virus-on-a-network story

**Date**: 2026-05-29 03:00  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1779994511`

## TL;DR

- Exit code: **0**
- Wall time: **300s** (5.0 min)
- LLM calls: **18** (est. **$0.04** at DeepSeek pricing)
- Calibration MSE: **—** (external-model baseline ≈ 100 ± 60)
- Halt: (none)

## Metrics

### Codegen health

| Metric | Value |
|---|---|
| Anti-pattern validator hits | **0** |
| Pipeline halted? | (none) |
| Phases logged | 11 occurrences |
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
| Wall time | 300s (5.0 min) |
| LLM calls total | 18 |
| LLM calls by model | `{'deepseek-chat': 11, 'deepseek-reasoner': 7}` |
| Estimated USD cost | $0.04 |
| Report generated? | True (3,051 chars) |
| ARS package? | True |

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
