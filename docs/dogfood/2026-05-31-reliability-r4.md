# Dogfood report: codegen path on the virus-on-a-network story

**Date**: 2026-05-31 08:56  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780188572`

## TL;DR

- Exit code: **0**
- Wall time: **394s** (6.6 min)
- LLM calls: **19** (est. **$0.04** at DeepSeek pricing)
- Calibration MSE: **5763.2** (external-model baseline ≈ 100 ± 60)
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
| `virus_spread_chance` | 4.4 | 16.535 | 275.8% |
| `recovery_chance` | 2.5 | 2.563 | 2.5% |
| `gain_resistance_chance` | 25.0 | 77.478 | 209.9% |

**Aggregate MSE**: 5763.2  
**Floor estimate** (from ADR-006): 100-200  
**External-model baseline** (commit 3c3c15c): 99 ± 59

### UX

| Metric | Value |
|---|---|
| Wall time | 394s (6.6 min) |
| LLM calls total | 19 |
| LLM calls by model | `{'deepseek-chat': 12, 'deepseek-reasoner': 7}` |
| Estimated USD cost | $0.04 |
| Report generated? | True (3,546 chars) |
| ARS package? | True |

### stderr preview

```
/home/user/Documents/Social Simulation /abm-auto/.venv/lib/python3.11/site-packages/scipy/stats/_axis_nan_policy.py:592: RuntimeWarning: Precision loss occurred in moment calculation due to catastrophic cancellation. This occurs when the data are nearly identical. Results may be unreliable.
  res = hypotest_fun_out(*samples, **kwds)

```

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
