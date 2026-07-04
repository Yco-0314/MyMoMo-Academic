# BHW Informational Cascade — PREDICTIONS (locked)

**Locked 2026-07-01 (revised before any run; the first draft used a non-standard coin-flip
tie convention with a wrong correct-cascade formula — corrected here to the canonical
follow-own-signal model BEFORE building, no run has occurred).** Claim is Bikhchandani,
Hirshleifer & Welch 1992 (J. Polit. Econ. 100:992), not tuned. Genuine agent-based (sequential
rational Bayesian agents). Verified against the paper + standard treatments.

**Model:** binary world state θ ∈ {H,L}, prior 1/2. N agents act ONCE each in fixed order. Each
draws a conditionally-independent symmetric private signal of precision p = P(s=h|H) > 1/2, then
observes ALL predecessors' ACTIONS (not signals) and Bayes-updates; **ties (equal posterior) are
broken by following one's own signal** (the canonical convention). A cascade BEGINS as soon as one
action leads the other by 2 (equivalently two consecutive identical actions from a balanced
history); thereafter every agent rationally ignores its own signal and herds. From a balanced
history each fresh pair starts a cascade w.p. p²+(1−p)² and stays balanced w.p. 2p(1−p). Canonical
p=0.7; also sweep p ∈ {0.6,0.8,0.9}. Monte-Carlo ≥200k queues per p, N=30.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | A cascade forms almost surely. | P(no cascade by agent 20) < 0.001 at p≥0.6 (analytic (2p(1−p))¹⁰ = 1.71×10⁻⁴ at p=0.7); MC formation-by-agent-20 fraction ≥ 0.999. |
| P2 | Cascades can be WRONG (rational herd ≠ correct). | conditional on a cascade, P(incorrect) = (1−p)²/(p²+(1−p)²) = **0.1552 at p=0.7** (and 0.3077 / 0.0588 at p=0.6 / 0.8); MC match within ±0.005. |
| P3 | Early onset + impaired social learning. | E[agents acting on private info before a cascade] = 2/(p²+(1−p)²) = **3.45 at p=0.7** (< 4 for all p, ±0.05); and the social-accuracy gain p²/(p²+(1−p)²) − p ≤ 0.16 at p=0.7 (late agents barely beat a lone agent). |

**Discipline:** prior, signal precision grid, queue length, MC count, the Bayes barrier rule, and
the follow-own-signal tie-break FIXED + closed-form metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** nearest built are voter / watts-cascade / granovetter-threshold — none has
a hidden ground-truth state, a private signal precision p, or Bayesian updating, so
(1−p)²/(p²+(1−p)²) is undefined for them and they cannot produce these clauses.
