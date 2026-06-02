# Dogfood report — α + β + ε on the virus-on-a-network calibration

**Date**: 2026-05-30 17:05  
**Story**: `examples/calibration_challenge_virus/story.md`  
**Observed**: multi-seed (commit 00ad49b)  
**Ground truth**: virus=4.4 / recov=2.5 / resist=25.0

## TL;DR

- **α** (2 runs): MSE = 103.7 ± 40.7 (baseline 44.5) — **WORSE — 2.33× baseline (summary may lose too much signal)**
- **β** profile: 0 flat params, Fisher: 0 flat directions
- **ε** verify_execution: PASS (zero mismatches on known-correct sim)

## α: trajectory_features SummaryStats adapter

| Run | MSE | Wall (s) | virus | recov | resist |
|---|---|---|---|---|---|
| 1 | 63.0 | 93 | 4.989 | 4.639 | 15.871 |
| 2 | 144.4 | 94 | 4.620 | 3.257 | 23.558 |

**Aggregate MSE**: 103.7 ± 40.7  
**vs full_trajectory baseline** (44.5): ratio = 2.33×

## β: profile_likelihood + fisher_info_eigen

**MAP used**: `{'virus_spread_chance': 4.989327531968789, 'recovery_chance': 4.6386409065505525, 'gain_resistance_chance': 15.870641114051473}`

## Profile likelihood (per-parameter identifiability)

| Parameter | MAP value | MAP objective | Min profile | Max profile | Curvature | Verdict |
|---|---|---|---|---|---|---|
| `virus_spread_chance` | 4.9893 | 13.61 | 34.94 | 353.30 | 23.385 | identified |
| `recovery_chance` | 4.6386 | 13.61 | 33.72 | 336.64 | 22.251 | identified |
| `gain_resistance_chance` | 15.8706 | 13.61 | 40.37 | 332.36 | 21.448 | identified |


## Fisher information eigendecomposition (local identifiability)

Hessian of ||sim−obs||² at MAP, eigendecomposed. Small eigenvalues correspond to flat directions in joint param-space — these are parameter combinations that don't affect fit quality.

| Rank | Eigenvalue | Direction (param: coefficient) |
|---|---|---|
| 1 | 250769.6279 | virus_spread_chance=-0.011, recovery_chance=+1.000, gain_resistance_chance=+0.003 |
| 2 | 9096.5369 | virus_spread_chance=+1.000, recovery_chance=+0.011, gain_resistance_chance=+0.003 |
| 3 | 576.1255 | virus_spread_chance=-0.003, recovery_chance=-0.003, gain_resistance_chance=+1.000 |


## ε: verify_execution

**Verdict**: PASS (zero mismatches on known-correct sim)

### LLM-extracted claims

| Target | Direction | Rationale |
|---|---|---|
| `susceptible` | `monotonic_decrease` | Susceptible individuals are converted to infected or resistant, with only a small possibility of reversion from recovered to susceptible, so the net trend is downward. |
| `infected` | `peak_then_decay` | Infected count rises initially from the outbreak, then declines as recovery outpaces new infections, eventually reaching zero. |
| `resistant` | `monotonic_increase` | Resistant individuals accumulate over time as recovered agents gain resistance, and they never leave the resistant state. |

### Actual sim trajectory classifications

| Target | Direction | Peak ratio | Monotonicity |
|---|---|---|---|
| `susceptible` | `unclear` | 5.25 | 0.27 |
| `infected` | `unclear` | 3.45 | 0.43 |
| `resistant` | `unclear` | 1.00 | 0.35 |
