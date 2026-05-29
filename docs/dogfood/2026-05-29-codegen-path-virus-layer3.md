# Dogfood report: codegen path on BEHAVE 2025 virus story

**Date**: 2026-05-29 15:15  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780038650`

## TL;DR

- Exit code: **0**
- Wall time: **305s** (5.1 min)
- LLM calls: **13** (est. **$0.03** at DeepSeek pricing)
- Calibration MSE: **—** (external-model baseline ≈ 100 ± 60)
- Halt: (none)

## Metrics

### Codegen health

| Metric | Value |
|---|---|
| Anti-pattern validator hits | **0** |
| Pipeline halted? | (none) |
| Phases logged | 13 occurrences |
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
| Wall time | 305s (5.1 min) |
| LLM calls total | 13 |
| LLM calls by model | `{'deepseek-chat': 6, 'deepseek-reasoner': 7}` |
| Estimated USD cost | $0.03 |
| Report generated? | True (4,128 chars) |
| ARS package? | True |

### stderr preview

```
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:266: UserWarning: Glyph 27493 (\N{CJK UNIFIED IDEOGRAPH-6B65}) missing from font(s) Arial.
  plt.tight_layout()
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:266: UserWarning: Glyph 39588 (\N{CJK UNIFIED IDEOGRAPH-9AA4}) missing from font(s) Arial.
  plt.tight_layout()
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:266: UserWarning: Glyph 26102 (\N{CJK UNIFIED IDEOGRAPH-65F6}) missing from font(s) Arial.
  plt.tight_layout()
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:266: UserWarning: Glyph 38388 (\N{CJK UNIFIED IDEOGRAPH-95F4}) missing from font(s) Arial.
  plt.tight_layout()
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:266: UserWarning: Glyph 24207 (\N{CJK UNIFIED IDEOGRAPH-5E8F}) missing from font(s) Arial.
  plt.tight_layout()
/home/user
```

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
