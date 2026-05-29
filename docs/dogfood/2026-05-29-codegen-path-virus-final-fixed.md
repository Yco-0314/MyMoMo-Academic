# Dogfood report: codegen path on BEHAVE 2025 virus story

**Date**: 2026-05-29 17:07  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1780045384`

## TL;DR

- Exit code: **1**
- Wall time: **255s** (4.3 min)
- LLM calls: **15** (est. **$0.03** at DeepSeek pricing)
- Calibration MSE: **—** (external-model baseline ≈ 100 ± 60)
- Halt: (none)

## Metrics

### Codegen health

| Metric | Value |
|---|---|
| Anti-pattern validator hits | **0** |
| Pipeline halted? | (none) |
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
| Wall time | 255s (4.3 min) |
| LLM calls total | 15 |
| LLM calls by model | `{'deepseek-chat': 9, 'deepseek-reasoner': 6}` |
| Estimated USD cost | $0.03 |
| Report generated? | False (0 chars) |
| ARS package? | False |

### stderr preview

```
╭───────────────────── Traceback (most recent call last) ──────────────────────╮
│ /home/user/.local/share/uv/python/cpython-3.11.14-macos-aarch64-none/lib/pyt │
│ hon3.11/pathlib.py:1116 in mkdir                                             │
│                                                                              │
│   1113 │   │   Create a new directory at this given path.                    │
│   1114 │   │   """                                                           │
│   1115 │   │   try:                                                          │
│ ❱ 1116 │   │   │   os.mkdir(self, mode)                                      │
│   1117 │   │   except FileNotFoundError:                                     │
│   1118 │   │   │   if not parents or self.parent == self:                    │
│   1119 │   │   │   │   raise                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
OSError: [Errno 63] File nam
```

## Friction inventory

_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._

TODO: fill in after observing run.
