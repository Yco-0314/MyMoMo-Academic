# Dogfood report: codegen path on BEHAVE 2025 virus story

**Date**: 2026-05-30 00:11  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780070734`

## TL;DR

- Exit code: **0**
- Wall time: **343s** (5.7 min)
- LLM calls: **18** (est. **$0.04** at DeepSeek pricing)
- Calibration MSE: **—** (external-model baseline ≈ 100 ± 60)
- Halt: could not produce working code (fatal errors remain after 

## Metrics

### Codegen health

| Metric | Value |
|---|---|
| Anti-pattern validator hits | **1** |
| Pipeline halted? | could not produce working code (fatal errors remain after  |
| Phases logged | 7 occurrences |
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
| Wall time | 343s (5.7 min) |
| LLM calls total | 18 |
| LLM calls by model | `{'deepseek-chat': 8, 'deepseek-reasoner': 10}` |
| Estimated USD cost | $0.04 |
| Report generated? | False (0 chars) |
| ARS package? | False |

### Anti-pattern hits (first 10)

- `Fix: The error is `hallucinated_attr_generation_num` — `agent.generation_num``

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
