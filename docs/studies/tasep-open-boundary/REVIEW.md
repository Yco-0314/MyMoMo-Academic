# TASEP with open boundaries (DEHP 1993) — review

**tier: minimal+ (adversarially verified)** — 3/3 REPRO. CA (disclosed).

## Cheap checks + adversarial verification
- numeric-provenance: **pass** — bundle (J=0.251, low-density match, coexistence jump 0.355) matches results.
- fair-control: **pass** — P1/P2/P3 sweep alpha,beta on one open-chain rule; graded vs mean-field exact values.
- no-post-lock-drift: **pass** — graded vs lock committed e6f4f29 BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness / adversarial: **pass** — independent re-run: J(alpha=0.7,beta=0.7)=0.2507 AND J(0.8,0.9)=0.2507 — the maximal current is EXACTLY 0.25 and INDEPENDENT of alpha,beta (the DEHP plateau, non-degenerate). Low-density J(0.3,0.8)=0.2093 = mean-field alpha(1-alpha)=0.21 and bulk rho=0.307 = alpha=0.3.
- framing-disclosure: **pass** — exclusion-process CA, disclosed.

## Verdict: SOUND. 3/3 REPRO (adversarially verified).
P1 maximal-current plateau J=1/4 independent of boundary rates; P2 low-density phase J=alpha(1-alpha), rho=alpha;
P3 coexistence-line density jump. The exactly-known boundary-induced three-phase diagram reproduces. 18 tests. No tuning.
REVIEW COMPLETE (minimal+, adversarially verified)
