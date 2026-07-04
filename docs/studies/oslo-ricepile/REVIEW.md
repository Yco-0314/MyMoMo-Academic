# Oslo rice-pile model (1996) — review

**tier: minimal+ (adversarially verified)** — 3/3 REPRO. CA (disclosed).

## Cheap checks
- numeric-provenance: **pass** — bundle (L=256 tau=1.444, heavy tail 5.36 decades, <s> ratio 1.997) matches results.
- fair-control: **pass** — single 1D stochastic-slope rule swept over L in {32,64,128,256}.
- no-post-lock-drift: **pass** — graded vs lock d7599ab BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness: **pass** — genuinely critical in 1D (heavy tail spanning 5.4 decades) where a deterministic 1D BTW pile is trivial; cutoff scales with L (mean avalanche size grows monotonically L=32->256). 18 tests pass.
- framing-disclosure: **pass** — 1D stochastic-threshold SOC CA, disclosed.

## Verdict: SOUND. 3/3 REPRO.
P1 Oslo exponent tau=1.444 in [1.4,1.7]; P2 genuinely critical (heavy-tailed, 5.4 decades); P3 finite-size cutoff
scaling (<s> grows with L). The stochastic per-site critical slope makes 1D non-trivially critical, distinct
from btw_sandpile. 18 tests. No tuning.
REVIEW COMPLETE (minimal+)
