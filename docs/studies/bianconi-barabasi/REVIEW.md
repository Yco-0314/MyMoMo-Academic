# Bianconi-Barabási fitness model — adversarial review

**tier: deep** (trigger: 1 honest MISS). Reviewed vs the verified claim + lock. **This replaces an
earlier committed stub that used a NON-CANONICAL η=50 condensing hack** with the paper's canonical
condensation law ρ(η) = (θ+1)(1−η)^θ (θ=10), web-verified to actually condense before locking.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (Spearman 0.532, f_max 0.145, γ 2.587) matches bundle/results; incremental fitness weights match brute-force to rel-err 8e-14.
- fair-control: **pass** — P1's no-fitness BA control (|Spearman|=0.004, 0/4 bins) is the single-variable gate; P2's uniform-vs-condensing contrast varies only ρ(η).
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; L3 gate ok; FINDINGS fingerprinted.
- mechanism-aliveness: **pass** — fitness-driven attachment is alive: aged-cohort Spearman(η,k)=0.532; the condensing law produces a non-vanishing max-degree fraction (0.142→0.145) while uniform shrinks (0.024).
- framing-disclosure: **pass** — network-generation, disclosed; the condensing ρ(η)=(θ+1)(1−η)^θ θ=10 is stated.

## Verdict: FAITHFUL (canonical law); P2 is an HONEST near-threshold MISS by 0.005.
- **P1 REPRO** — fit-get-richer: aged-cohort Spearman(η,k)=0.532 ≥ 0.5, ≥2× median-degree ratio in 3/4 birth-time bins all seeds; the BA control fails (the distinctness gate). (Whole-population Spearman 0.365 disclosed — diluted by late arrivals stuck at k=m.)
- **P2 MISS (honest, marginal)** — condensing f_max at N=5e4 = 0.145 vs the 0.15 bar. The other three sub-clauses pass (non-vanishing 0.142→0.145; uniform 0.024≤0.05 shrinking; gap 0.121≥0.10). One low seed (0.059) drags the 4-seed mean under; over 10 seeds mean 0.165, median 0.164 — the signature is robust. Not a bug (weights match brute-force). Not tuned.
- **P3 REPRO** — soft exponent γ=2.587 ∈ [1.9,2.7], < 2.9 (distinguishable from BA's 3).

## Discipline check: PASS. Canonical-law upgrade over the stub.
2/3 REPRO honestly; the condensation signature is present and robust (10-seed mean 0.165) — the locked
4-seed mean just misses by 0.005 on one low seed. Replacing the η=50 stub with (θ+1)(1−η)^θ is a
faithfulness UPGRADE, not tuning. 19 tests.

REVIEW COMPLETE
