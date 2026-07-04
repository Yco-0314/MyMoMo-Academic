# Stag Hunt coordination game — review

**tier: minimal** (all-REPRO 3/3, comfortable margins; no MISS). Genuine agent-based.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (x*=0.675, Hare-basin 0.692, P3 worst-err 0.025) matches bundle/results.
- fair-control: **pass** — P2 basin measured over x0~U(0,1) (500 replicates); P3 varies only the payoff set.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; bundle fingerprints FINDINGS+lock+spec. The builder replaced the lock's illustrative (4,2,2,0) [which violated strict R>T>P>S with T=P] by (5,3,2,0) giving the SAME analytic x*=0.500 under strict ordering — a disclosed faithfulness correction of a spec typo, not a verdict tune.
- mechanism-aliveness: **pass** — bistable fixation EMERGES from the agents (x* only compared against, never fed in); all 500 replicates fixate on a pure state.
- framing-disclosure: **pass** — genuine 2×2 imitation-dynamics agents, disclosed; distinct from hawk_dove's stable mixed ESS.

## Verdict: SOUND. 3/3 REPRO. Bistable basin selection + risk-dominance confirmed.
x*_emp=0.675 (canonical 0.667), Hare (risk-dominant) basin 0.692 > Stag 0.308, threshold tracks the
payoff formula across 3 sets (worst |err| 0.025). Distinctness: unstable interior + pure-ESS fixation,
the opposite of hawk_dove's stable coexistence. 18 tests, ~5s. No tuning.

REVIEW COMPLETE
