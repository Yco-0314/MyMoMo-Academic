# Dogfood report: codegen path on the virus-on-a-network story

**Date**: 2026-05-31 09:01  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780188967`

## TL;DR

- Exit code: **0**
- Wall time: **331s** (5.5 min)
- LLM calls: **16** (est. **$0.03** at DeepSeek pricing)
- Calibration MSE: **148.1** (external-model baseline ≈ 100 ± 60)
- Halt: (none)

## Metrics

### Codegen health

| Metric | Value |
|---|---|
| Anti-pattern validator hits | **0** |
| Pipeline halted? | (none) |
| Phases logged | 10 occurrences |
| GVR retries by actor | `{'DesignerViability': 1, 'CoderVerifier': 1}` |

### Calibration health

| Parameter | Truth | Got | Rel. err |
|---|---|---|---|
| `virus_spread_chance` | 4.4 | 2.127 | 51.7% |
| `recovery_chance` | 2.5 | 1.070 | 57.2% |
| `gain_resistance_chance` | 25.0 | 57.978 | 131.9% |

**Aggregate MSE**: 148.1  
**Floor estimate** (from ADR-006): 100-200  
**External-model baseline** (commit 3c3c15c): 99 ± 59

### UX

| Metric | Value |
|---|---|
| Wall time | 331s (5.5 min) |
| LLM calls total | 16 |
| LLM calls by model | `{'deepseek-chat': 12, 'deepseek-reasoner': 4}` |
| Estimated USD cost | $0.03 |
| Report generated? | True (3,143 chars) |
| ARS package? | True |

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
