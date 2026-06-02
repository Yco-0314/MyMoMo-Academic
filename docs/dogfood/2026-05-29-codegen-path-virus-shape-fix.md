# Dogfood report: codegen path on the virus-on-a-network story

**Date**: 2026-05-29 17:42  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780047292`

## TL;DR

- Exit code: **0**
- Wall time: **432s** (7.2 min)
- LLM calls: **19** (est. **$0.04** at DeepSeek pricing)
- Calibration MSE: **5295.9** (external-model baseline ≈ 100 ± 60)
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
| `virus_spread_chance` | 4.4 | 14.193 | 222.6% |
| `recovery_chance` | 2.5 | 0.270 | 89.2% |
| `gain_resistance_chance` | 25.0 | 70.485 | 181.9% |

**Aggregate MSE**: 5295.9  
**Floor estimate** (from ADR-006): 100-200  
**External-model baseline** (commit 3c3c15c): 99 ± 59

### UX

| Metric | Value |
|---|---|
| Wall time | 432s (7.2 min) |
| LLM calls total | 19 |
| LLM calls by model | `{'deepseek-chat': 11, 'deepseek-reasoner': 8}` |
| Estimated USD cost | $0.04 |
| Report generated? | True (3,442 chars) |
| ARS package? | True |

### stderr preview

```
/home/user/Documents/Social Simulation /abm-auto/.venv/lib/python3.11/site-packages/scipy/stats/_axis_nan_policy.py:592: RuntimeWarning: Precision loss occurred in moment calculation due to catastrophic cancellation. This occurs when the data are nearly identical. Results may be unreliable.
  res = hypotest_fun_out(*samples, **kwds)

```

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
