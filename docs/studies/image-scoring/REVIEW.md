# Indirect reciprocity by image scoring — adversarial review

**tier: deep** (trigger: 2 honest MISSes). Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (q-threshold collapse 0.000→0.78, k=0 freq 0.20, coop 0.887/0.999/0.999) matches bundle/results.
- fair-control: **pass** — P2 sweeps only q; P3 sweeps only n.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; L3 integrity gate ok.
- mechanism-aliveness: **pass** — the reputation-discrimination mechanism is alive (P2: cooperation collapses below q=c/b and is sustained at q=1.0); cooperation IS established in P1/P3 (it's the SELECTION of k=0 / the size-decay that miss).
- framing-disclosure: **pass** — genuine agent-based indirect reciprocity, disclosed.

## Verdict: model FAITHFUL; P1 + P3 are HONEST MISSes from GATE-DESIGN errors in the lock (not bugs).
- **P2 REPRO** — the paper's mechanistic headline: cooperation requires the information threshold q > c/b.
  Collapses (<1% acts) for q≤0.05, sustained (fraction 1.0) at q=1.0, crossover near q≈c/b=0.1. Decisive.
- **P1 MISS (honest, lock error).** Cooperation is fully established (coop-act 1.000) but the population does
  not fix on exactly k=0 (k=0 freq 0.20, |mean k|=2.40). This is the KNOWN neutral drift of plain image
  scoring: once all cooperate and images saturate, all k≤0 strategies are payoff-equivalent, so WITHOUT
  mutation there is no gradient selecting k=0. A builder literature check confirmed this is faithful
  documented behaviour (k=0 is selected only when mutation reintroduces defectors; image scoring was later
  shown not to be an ESS). **The lock's P1 (k=0 fixation with NO mutation) was mis-specified** — it demands
  a selection gradient the model does not have without mutation.
- **P3 MISS (honest, lock error).** Coop fraction 0.887/0.999/0.999 at n=20/50/100 — not the target
  0.90/0.47/0.18 decrease. Under the lock's OWN m=10n rule, per-capita information is constant in n, so
  group size does not dilute reputation; the published decrease needs a FIXED total round count, which
  m=10n does not impose. The lock's protocol contradicts the effect it asks for. Reported as a null.

## Discipline check: PASS. Recurring gate-design lesson.
1/3 REPRO reported honestly; no tuning; two falsifications reported as genuine features of the faithful
model + the mis-specified lock. This is the 4th–5th instance (q-voter ε, social-impact α, PSV/pavlov bars)
where a LOCKED protocol/bar was the defect, not the model — the anti-fabrication core holds (honest MISS
every time), but the pre-lock gate-design check (does the locked protocol actually exhibit the claim?)
should catch these before locking. 24 tests.

REVIEW COMPLETE
