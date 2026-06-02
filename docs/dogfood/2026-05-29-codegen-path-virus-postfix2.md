# Dogfood report: codegen path on the virus-on-a-network story

**Date**: 2026-05-29 14:09  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780034744`

## TL;DR

- Exit code: **0**
- Wall time: **230s** (3.8 min)
- LLM calls: **16** (est. **$0.03** at DeepSeek pricing)
- Calibration MSE: **—** (external-model baseline ≈ 100 ± 60)
- Halt: (none)

## Metrics

### Codegen health

| Metric | Value |
|---|---|
| Anti-pattern validator hits | **0** |
| Pipeline halted? | (none) |
| Phases logged | 6 occurrences |
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
| Wall time | 230s (3.8 min) |
| LLM calls total | 16 |
| LLM calls by model | `{'deepseek-chat': 13, 'deepseek-reasoner': 3}` |
| Estimated USD cost | $0.03 |
| Report generated? | False (0 chars) |
| ARS package? | True |

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
