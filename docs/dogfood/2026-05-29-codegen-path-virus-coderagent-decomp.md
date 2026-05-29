# Dogfood report: codegen path on BEHAVE 2025 virus story

**Date**: 2026-05-29 23:03  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780066600`

## TL;DR

- Exit code: **0**
- Wall time: **385s** (6.4 min)
- LLM calls: **19** (est. **$0.04** at DeepSeek pricing)
- Calibration MSE: **180.3** (external-model baseline ≈ 100 ± 60)
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
| `virus_spread_chance` | 4.4 | 5.579 | 26.8% |
| `recovery_chance` | 2.5 | 4.269 | 70.7% |
| `gain_resistance_chance` | 25.0 | 13.697 | 45.2% |

**Aggregate MSE**: 180.3  
**Floor estimate** (from ADR-006): 100-200  
**External-model baseline** (commit 3c3c15c): 99 ± 59

### UX

| Metric | Value |
|---|---|
| Wall time | 385s (6.4 min) |
| LLM calls total | 19 |
| LLM calls by model | `{'deepseek-chat': 12, 'deepseek-reasoner': 7}` |
| Estimated USD cost | $0.04 |
| Report generated? | True (4,507 chars) |
| ARS package? | True |

### stderr preview

```
Matplotlib is building the font cache; this may take a moment.

```

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
