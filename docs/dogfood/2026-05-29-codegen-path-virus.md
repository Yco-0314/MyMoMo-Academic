# Dogfood report: codegen path on BEHAVE 2025 virus story

**Date**: 2026-05-29 02:25  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Mode**: reproduce (no --external-model — full codegen path)  
**Iterations**: 2  
**Workspace**: `/home/user/Documents/Social Simulation /mymomo-academic/workspace/dogfood_codegen_1779992396`

## TL;DR

- Exit code: **0**
- Wall time: **343s** (5.7 min)
- LLM calls: **16** (est. **$0.03** at DeepSeek pricing)
- Calibration MSE: **—** (external-model baseline ≈ 100 ± 60)
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
| LLM calls total | 16 |
| LLM calls by model | `{'deepseek-chat': 9, 'deepseek-reasoner': 7}` |
| Estimated USD cost | $0.03 |
| Report generated? | True (4,047 chars) |
| ARS package? | True |

### stderr preview

```
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:243: UserWarning: Glyph 27493 (\N{CJK UNIFIED IDEOGRAPH-6B65}) missing from font(s) Arial.
  plt.tight_layout()
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:243: UserWarning: Glyph 39588 (\N{CJK UNIFIED IDEOGRAPH-9AA4}) missing from font(s) Arial.
  plt.tight_layout()
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:243: UserWarning: Glyph 26102 (\N{CJK UNIFIED IDEOGRAPH-65F6}) missing from font(s) Arial.
  plt.tight_layout()
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:243: UserWarning: Glyph 38388 (\N{CJK UNIFIED IDEOGRAPH-95F4}) missing from font(s) Arial.
  plt.tight_layout()
/home/user/Documents/Social Simulation /mymomo-academic/abm_auto/agents/visualizer.py:243: UserWarning: Glyph 24207 (\N{CJK UNIFIED IDEOGRAPH-5E8F}) missing from font(s) Arial.
  plt.tight_layout()
/home/user
```

## Verdict

**Codegen path works end-to-end** (5.7 min, exit 0, no halts, $0.03 in
LLM calls). But the run **silently degraded from calibration to
heuristic optimization** because nothing copied `observed.csv` into the
auto-named workspace — the user's empirical data went unused despite
the spec correctly identifying it. Output report is honest about this
in prose ("应使用网格搜索、贝叶斯优化或ABC进行系统校准") but the user
sees no signal at the CLI level that calibration was skipped.

## Friction inventory

_Each item: what we observed → root cause → architectural move._

### 🔴 CRITICAL: silent degradation from calibrate → optimize

**Observed**: `best_params.json` doesn't exist; `calibration_final_sim.csv`
doesn't exist; `Phase 6: Optimizing parameters...` in stdout (NOT
`Phase 6 (alt): Bayesian Calibration...`). The OptimizerAgent
hand-tuned three parameter sets across 3 iterations, with the report
LLM later writing that "应使用…ABC进行系统校准" — i.e., the AI itself
noticed calibration didn't happen.

**Root cause**: `Pipeline._should_calibrate()` (now
`iteration._should_calibrate`) checks for `workspace.path /
spec.calibration_data_path` OR `workspace.path / data/observed.csv`.
Neither exists because:
1. CLI has no flag to inject observed data into the workspace
2. The spec's `calibration_data_path = "data/observed.csv"` is
   interpreted relative to the workspace, not the story's directory
3. The workspace is auto-named at pipeline construction time, so the
   user can't pre-populate it
4. The `benchmark_external_model.py` script works around this by
   manually copying `observed.csv` into `workspace/data/` after Pipeline
   construction — that workaround is invisible to CLI users

**Architectural move**: Two options, both should be done:

- (a) **`--observed PATH` CLI flag** — copies the file into
  `workspace/data/observed.csv` before any phase runs. Lives most
  naturally as a new `InjectObservedDataPhase` after
  `ExternalModelDeclarationPhase`.
- (b) **Auto-resolve `spec.calibration_data_path` relative to story
  directory** — if the spec says "data/observed.csv" and the story
  lives at `examples/foo/story.md`, look for
  `examples/foo/data/observed.csv` and copy. Removes the need for the
  CLI flag in the common case.

Without either, every user who follows the documented "write a story
with empirical data" workflow gets the silent-degradation experience.

### 🟡 MEDIUM: OptimizerAgent fallback is dangerous when it's a fallback

**Observed**: Run 1 tried `virus_spread_chance=4.4`, Run 2 dropped it
to 0.15 (LLM treated 4.4 as a probability >1, not percent). Three
hand-tuned points across [0, 5] for one parameter is roughly useless;
the resulting "best_params" are nowhere near the ground truth and the
report acknowledges this.

**Root cause**: `OptimizerAgent` is documented as the
"heuristic alternative" but in practice produces results that look like
they came from a calibration pipeline. The CLI / report give no signal
that this fallback fired.

**Architectural move**: When `_should_calibrate()` would have returned
True if data were present, but data is missing, **fail loudly with a
helpful error** — don't silently downgrade. Either halt or emit a HIGH
audit issue. If the calibration data really is unavailable, the user
should know they're getting heuristic exploration not Bayesian fit.

### 🟡 MEDIUM: LLM treated `virus_spread_chance=4.4` as probability not percent

**Observed**: Report's Run 1 commentary: "`virus_spread_chance=4.4`
(>1，物理上不可能，但模型可能将其解释为每接触对的概率，4.4>1导致必然传播)".

**Root cause**: The unit-drift anti-pattern from
`mymomo_knowledge/05-anti-patterns.md` §4 — the LLM (Reporter, not
Coder this time) doesn't know whether the param is in percent or
probability. The Coder got it right (`virus_spread_chance / 100.0` at
point of use), but the Reporter's prose interpretation diverged.

**Architectural move**: Inject `calibration_param_specs.unit` into the
Reporter prompt the same way it's injected into the Coder prompt
(handled by `_build_calibration_contract_block`). Right now it's
visible to Coder only.

### 🟡 MEDIUM: Reporter hallucinates content

**Observed**: Report mentions "进行了三轮参数调整的迭代仿真" and discusses
"Run 3" in detail, but the pipeline was run with `--iterations 2`.

**Root cause**: Either the Reporter prompt doesn't know the iteration
count, or it confabulates filler content to meet length expectations.

**Architectural move**: Pass `len(ctx.all_insights)` into the Reporter
prompt as a hard constraint ("This study ran exactly N iterations; do
not invent additional ones").

### 🟢 MINOR: matplotlib font warnings flood stderr (CJK glyphs)

**Observed**: ~14 lines of `UserWarning: Glyph XXXX missing from
font(s) Arial` in stderr from `abm_auto/agents/visualizer.py:243`. Plot
PDFs render with placeholders for Chinese characters.

**Root cause**: matplotlib default font Arial has no CJK glyphs;
`lang="zh"` doesn't configure a CJK-capable font.

**Architectural move**: In `VisualizerAgent`, set `plt.rcParams['font.family']`
to a CJK-capable default when `lang == 'zh'` (e.g., `"PingFang SC"` on
macOS, `"Noto Sans CJK"` on Linux).

### 🟢 MINOR: anti-pattern validator was a no-op on this run

**Observed**: 0 anti-pattern hits. CoderVerifier GVR retried once but
that was for a non-anti-pattern issue.

**Root cause / interpretation**: The DeepSeek codegen on this story
was clean — no hallucinated classes / attributes / removed APIs. This
is GOOD; it means the LLM is following the current MyMoMo Knowledge Base
correctly. But it also means **we have no positive evidence that the
validator catches anything real today**. If we want to validate the
validator's user-facing value, we need to either find a story that
provokes a hallucination, or rollback prompt improvements temporarily
to artificially produce the failure pattern.

### 🟢 POSITIVE: codegen path is faster + cheaper than predicted

I predicted 8-15 min and $2-5. Actual was **5.7 min** and **$0.03**.
DeepSeek pricing is the dominant factor here vs Anthropic — running the
same flow on Claude would be ~50× more expensive.

### 🟢 POSITIVE: pipeline structure held up cleanly under codegen

The 23-phase decomposition from commit `6d195c1` ran exactly as
designed:
- All phase `should_run` predicates fired correctly
- GVR loops in Design and Coder both retried once and accepted
- The iteration loop ran twice as requested
- No phase order issues, no halt-on-misclassified-error

## Recommended next moves (priority order)

1. **(1-2h)** Fix the silent-degradation bug. Either CLI `--observed`
   flag OR auto-resolve from story-dir, ideally both. **Without this,
   no academic user can actually use this pipeline for calibration via
   the documented workflow.**

2. **(2-3h)** When data is declared but missing, halt-or-warn-loudly
   instead of silently calling OptimizerAgent. The current behavior
   is "fail open" in the worst way — produces output that looks like
   calibration result but isn't.

3. **(1h)** Pipe `calibration_param_specs.unit` into the Reporter
   prompt (eliminate the percent-vs-probability ambiguity in the
   generated report).

4. **(30min)** Fix CJK font in Visualizer for `lang="zh"` runs.

5. **(several hours, can be backgrounded)** Construct an "adversarial
   story" that intentionally provokes the LLM into producing
   anti-patterns, so we can prove the validator catches them in a
   real codegen run. Until then, the validator is theoretical.
