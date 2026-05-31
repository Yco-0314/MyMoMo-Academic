# Dogfood report: codegen path on BEHAVE 2025 virus story

**Date**: 2026-05-31 08:38  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780187492`

## TL;DR

- Exit code: **0**
- Wall time: **400s** (6.7 min)
- LLM calls: **19** (est. **$0.04** at DeepSeek pricing)
- Calibration MSE: **31.9** (external-model baseline ≈ 100 ± 60)
- Halt: (none)

## Metrics

### Codegen health

| Metric | Value |
|---|---|
| Anti-pattern validator hits | **0** |
| Pipeline halted? | (none) |
| Phases logged | 12 occurrences |
| GVR retries by actor | `{'DesignerViability': 1, 'CoderVerifier': 1}` |

### Calibration health

| Parameter | Truth | Got | Rel. err |
|---|---|---|---|
| `virus_spread_chance` | 4.4 | 3.626 | 17.6% |
| `recovery_chance` | 2.5 | 2.201 | 11.9% |
| `gain_resistance_chance` | 25.0 | 23.094 | 7.6% |

**Aggregate MSE**: 31.9  
**Floor estimate** (from ADR-006): 100-200  
**External-model baseline** (commit 3c3c15c): 99 ± 59

### UX

| Metric | Value |
|---|---|
| Wall time | 400s (6.7 min) |
| LLM calls total | 19 |
| LLM calls by model | `{'deepseek-chat': 11, 'deepseek-reasoner': 8}` |
| Estimated USD cost | $0.04 |
| Report generated? | True (4,661 chars) |
| ARS package? | True |

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
