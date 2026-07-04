# Relative-Agreement with extremists (Deffuant-Amblard 2002) — adversarial review

**tier: deep** (trigger: 2 honest MISSes). Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (P2 y=0.506, capture 0.998; P1 capture 0.408; P3 0/20) matches bundle/results.
- fair-control: **pass** — the three regimes differ only in (U, δ); the P1/P2 capture-fraction jump (0.408→0.998) is a clean contrast.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; L3 integrity gate ok; frozen attractor verified (max-move ~5e-7, y identical at 400 vs 800 sweeps).
- mechanism-aliveness: **pass** — the relative-agreement + low-uncertainty-extremist mechanism is alive and decisive in P2 (both poles populated, 99.8% moderate capture); the failures are regime-BOUNDARY placement, not a dead mechanism.
- framing-disclosure: **pass** — genuine agent-based RA dynamics, disclosed.

## Verdict: model FAITHFUL; P1 + P3 are HONEST MISSes from MIS-PLACED regime-boundary bars.
- **P2 REPRO** — DOUBLE-EXTREME bipolarization at U=1.2: y=0.506∈[0.35,0.65], moderate-capture 0.998>0.6,
  |mean x|=0.106<0.2. The headline "extremists split the moderates to both poles" reproduces cleanly.
- **P1 MISS (honest, mis-placed bar).** At U=0.4, y=0.088<0.1 ✓ and central|x|=0.221<0.3 ✓, but
  moderate-capture=0.408 fails the <0.15 bar (robust 0.31–0.50 across 20 seeds). The faithful model gives
  PARTIAL bipolarization with a central core at U=0.4, not pure central convergence. **Even the pre-lock
  gate-check predicted <0.15 here and was wrong** — the exact "central" boundary is more sensitive to U than
  the literature suggests.
- **P3 MISS (honest, mis-placed bar).** 0/20 seeds reach single-pole at the locked δ=0.1; the single-extreme
  attractor is real but needs a far stronger asymmetry — the builder found δ=1.0 gives 60% single-pole with +
  always winning (exactly the claimed mechanism), but did NOT change the locked δ=0.1. Honest MISS.

## Discipline check: PASS. Deeper gate-design lesson.
1/3 REPRO reported honestly; no tuning (the builder even located the working δ=1.0 and left the lock intact).
Lesson beyond the earlier ones: EXACT regime boundaries (which U is "central", which δ triggers single-extreme)
are implementation/parameter-sensitive and hard to predict even WITH a pre-lock gate-check — the robust
reproducible clause is the qualitative mechanism (P2), not the precise boundary location. 19 tests.

REVIEW COMPLETE
