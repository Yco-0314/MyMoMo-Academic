# Findings — W4 operator dogfood (Yaman design phase)

Pre-registered in `dogfood_w4_design.py` before running. Real DesignAgent run
(deepseek-chat, reproduce mode, the W2+W4 operator vocabulary in
`phase1_design_reproduce.md`). n=1 (LLM is stochastic; baseline was 3 attempts).
Output saved to `dogfood_w4_DESIGN.md`.

## Result: the operator vocabulary WORKS; the gate metric is the bottleneck

- **AI-ASSUMPTION tags: 13** (baseline 8-11). Gate verdict: still FAIL (>5).
  The raw count did NOT drop.
- **But the operators did exactly what W4 intended.** The semantic NN is
  referenced as `FeedforwardLearner` (4×), the turnover as `Moran` (7×), and
  **zero** operator lines are tagged `AI-ASSUMPTION`. The two mechanisms that
  used to be assumption tags are now declared, provided operators.

## So why didn't the count drop? Reading the 13 tags

| # | tag | category |
|---|-----|----------|
| 1 | `id: int` | template-owned BOILERPLATE (the generator creates `id`) |
| 2 | parallel cores = 1 | template BOILERPLATE |
| 3 | `scenario_id: int` | template BOILERPLATE |
| 4 | knowledge-diversity metric (optional) | minor output choice |
| 5,8 | `generations = 200` | real param — **counted twice** (inline + §6) |
| 6,9 | `attempts_per_generation = 50` | real param — **counted twice** |
| 7,10 | `repetitions = 20` | statistical boilerplate — **counted twice** |
| 11 | death formula `age/(age+10)` | operator-defaultable param |
| 12 | recipe-tree item IDs / base items | the real **W3 gap** |
| 13 | "§6 假设 (仅AI-ASSUMPTION …)" heading | **false positive** — the regex matched the rule-explanation HEADING |

The real, irreducible research assumptions are ~4 (3 params + the recipe
tree). The other ~9 are **counting artifacts**: template boilerplate the LLM
shouldn't tag, the same param double-counted inline + in the assumptions
section, and the gate's own regex matching the section heading that explains
the rule.

## What this reveals (the next levers, evidence-based)

W4 (operator vocabulary) is necessary but not sufficient. Two NEW levers,
both surfaced by this dogfood, neither of which is "lower the gate":

1. **Harden the gate's count** (cheap, high-value): the
   `len(re.findall("AI-ASSUMPTION", design))` in `viability_checker.py` is
   polluted. It should (a) not match the rule-explanation heading, (b)
   de-duplicate the same assumption appearing inline + in §Assumptions, and
   (c) not count template-owned boilerplate (`id`, `scenario_id`, parallel
   cores) — the design prompt should also tell the LLM not to tag those.
   On THIS design that alone removes ~8 of 13, landing at ~4-5 (a PASS).

2. **W3 task-graph + reference-asset** removes the last structural research
   assumption (the recipe tree) — the model declares an external rule table
   instead of assuming its encoding.

## Honest status

The operator vocabulary is confirmed working at the mechanism level (NN +
turnover no longer cost assumptions). The headline metric didn't move because
it is dominated by boilerplate over-tagging + duplication + a regex false
positive — a gate-counting problem distinct from operator expressiveness, and
now the cheapest next fix. n=1; the qualitative finding (operators declared,
count polluted by artifacts) is robust regardless of the exact number.

## Counter hardening — outcome (honest, and it caught me twice)

`viability_checker.count_assumptions()` now: requires a real tag form
(bracketed `[AI-ASSUMPTION…]` or colon `**AI-ASSUMPTION**:`), skips the
rule-explanation heading, de-duplicates the same SUBJECT restated inline +
in §Assumptions, and skips template-owned boilerplate (`id`, `scenario_id`,
…). Unit-tested.

Two under-count bugs surfaced by reading real output (not assuming the fix
worked):
1. The first cut required a colon directly after the token, so it MISSED the
   §Assumptions bold form `**AI-ASSUMPTION**:` — dropping the real recipe-tree
   and death assumptions, giving a false "13→5 PASS". Reading the kept list
   showed the recipe tree was missing → fixed (allow emphasis before colon).
2. After that it still missed the BARE `[AI-ASSUMPTION]` marker (no colon),
   under-counting `max_generations`. Fixed (count the bracket form too).

Honest result, corrected:
- On the original 13-tag design: raw 13 → hardened **7** (removed the heading
  false-positive, the inline+§6 identifier duplicates, and `id`/`scenario_id`
  boilerplate; recipe-tree and death correctly RETAINED).
- After also adding the prompt's boilerplate-discipline, a fresh design run:
  raw 7 → hardened **6** (n=1).
- Genuine DISTINCT assumptions are ~4 (params + death + recipe tree). The
  residual over-count is **prose-vs-identifier duplication** the LLM produced
  (the same assumption tagged once as prose and once as a named param) — regex
  cannot semantically dedup these, and the prompt's "tag each assumption once"
  is the source-level fix as that discipline takes hold.

**What is NOT claimed:** a clean deterministic gate PASS for Yaman. The
hardening removes the COUNTING ARTIFACTS (tested) and the operator vocabulary
removes the operator assumptions (confirmed), which together move Yaman from a
hard reject (raw 8-13, all counted) to the gate boundary (hardened ~6, n=1).
Forcing it under 5 by further counter tweaks would be manufacturing the result
— refused. The last genuine structural assumption is the recipe tree, which
is what W3 (task-graph + reference-asset) removes.
