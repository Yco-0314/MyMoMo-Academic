# Dogfood report: codegen path on BEHAVE 2025 virus story

**Date**: 2026-05-31 08:49  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780188244`

## TL;DR

- Exit code: **0**
- Wall time: **328s** (5.5 min)
- LLM calls: **15** (est. **$0.03** at DeepSeek pricing)
- Calibration MSE: **—** (external-model baseline ≈ 100 ± 60)
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
| `virus_spread_chance` | 4.4 | 2.900 | 34.1% |
| `recovery_chance` | 2.5 | 4.236 | 69.5% |
| `gain_resistance_chance` | 25.0 | 3.492 | 86.0% |

**Aggregate MSE**: —  
**Floor estimate** (from ADR-006): 100-200  
**External-model baseline** (commit 3c3c15c): 99 ± 59

### UX

| Metric | Value |
|---|---|
| Wall time | 328s (5.5 min) |
| LLM calls total | 15 |
| LLM calls by model | `{'deepseek-chat': 11, 'deepseek-reasoner': 4}` |
| Estimated USD cost | $0.03 |
| Report generated? | True (4,001 chars) |
| ARS package? | True |

### stderr preview

```
/home/user/Documents/Social Simulation /abm-auto/.venv/lib/python3.11/site-packages/scipy/stats/_axis_nan_policy.py:592: RuntimeWarning: Precision loss occurred in moment calculation due to catastrophic cancellation. This occurs when the data are nearly identical. Results may be unreliable.
  res = hypotest_fun_out(*samples, **kwds)

```

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
