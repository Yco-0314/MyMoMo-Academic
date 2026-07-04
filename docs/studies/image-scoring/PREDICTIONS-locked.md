# Indirect Reciprocity by Image Scoring (Nowak-Sigmund 1998) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Nowak & Sigmund 1998 (Nature 393:573), not tuned.
Genuine agent-based. Verified.

**Model:** n agents; each has an image score s (bounded, e.g. [−5,5]) and a strategy = threshold k;
in a donation game a random donor helps a random recipient iff recipient's s ≥ k (help: cost c to
donor, benefit b to recipient, c<b; canonical b=1, c=0.1). Helping raises the donor's image (+1),
refusing lowers it (−1); a fraction q of the population observes each interaction (image known w.p.
q). Payoffs accumulate; reproduce ∝ payoff (Moran/replicator) with optional mutation. m≈10n
interactions/generation; ≥20 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Fixation to the stern discriminator k=0 (no mutation, full info). | with q=1: k=0 frequency > 0.95 and \|mean k\| < 0.5 by t≤500; k=0 is the modal strategy in ≥90% of ≥20 seeds. |
| P2 | Information threshold q > c/b sustains cooperation. | cooperation collapses (<1% cooperative acts) for q ≤ 0.05; sustained (cooperative-strategy fraction > 0.6) at q=1.0; the crossover is near q ≈ c/b. |
| P3 | Group-size effect (with mutation). | time-avg cooperative-strategy fraction decreases monotonically with n: ≈0.90±0.10 (n=20), 0.47±0.12 (n=50), 0.18±0.10 (n=100). |

**Discipline:** n, b, c, q grid, image range, interactions, mutation, seeds FIXED + metrics locked;
no tuning. Falsified → MISS. **Distinctness (keep):** axelrod_ipd is DIRECT reciprocity (repeated
pairings, TFT); image scoring is INDIRECT (help those who helped OTHERS, via reputation, no repeat
pairing) — a discriminator conditions on the recipient's third-party image, which direct-reciprocity
and public_goods peer-punishment models have no representation of.
