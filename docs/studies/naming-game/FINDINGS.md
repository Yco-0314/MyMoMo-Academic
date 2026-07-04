# Minimal Naming Game — FINDINGS

**Run 2026-06-30, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
agent is an autonomous `NamerAgent` holding its own `inventory` (a set of names) for one
shared object; the model drives random ordered pairwise interactions and records the
metrics with a `DataCollector` (not a god-loop). Code:
`abm_auto/classics/naming_game.py`; experiment: `examples/repro_naming_game/run.py`.

Model: the minimal Naming Game of Baronchelli, Felici, Loreto, Caglioti & Steels (2006),
J. Stat. Mech. P06014 (see also Steels 1995). No tuning.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| N (agents) | **1000** |
| initial inventories | **empty** (all agents) |
| interaction | random ordered pair (speaker != hearer); speaker utters a name (invents a fresh globally-unique name if its inventory is empty, else picks one uniformly at random from its inventory) |
| success rule | hearer HAS the uttered name -> BOTH speaker and hearer collapse their inventory to exactly that name |
| failure rule | hearer LACKS the uttered name -> hearer ADDS it (speaker unchanged) |
| convergence | global consensus = every agent's inventory is the SAME single name (absorbing) |
| step cap | **1,000,000** interactions (= 1000*N), chosen before the run |
| seeds | **10** (seed_base 0 -> seeds 0..9) |
| determinism | one seeded RNG chain on the model; same seed => identical run |

The cap (1e6 interactions) was chosen BEFORE running. The minimal NG is proven to
converge in O(N^1.5) successful interactions (well below ~N^2); the measured convergence
(below) is ~5x10^4 interactions, ~20x under the cap — no run was truncated, and the cap
was NOT raised post-hoc.

## Measured results (10 seeds, N=1000)

| seed | interactions to consensus | peak #distinct names | peak total words | final words | final distinct |
|---|---|---|---|---|---|
| 0 | 47,721 | 481 | 10,807 | 1000 | 1 |
| 1 | 56,082 | 530 | 10,990 | 1000 | 1 |
| 2 | 36,505 | 497 | 10,083 | 1000 | 1 |
| 3 | 54,191 | 510 | 10,286 | 1000 | 1 |
| 4 | 64,660 | 515 | 10,617 | 1000 | 1 |
| 5 | 49,964 | 482 | 10,623 | 1000 | 1 |
| 6 | 42,278 | 501 | 11,110 | 1000 | 1 |
| 7 | 60,109 | 500 | 10,896 | 1000 | 1 |
| 8 | 31,705 | 510 | 9,661 | 1000 | 1 |
| 9 | 46,369 | 494 | 10,435 | 1000 | 1 |

**Aggregates (mean over 10 seeds):**

- **Consensus fraction: 10/10 = 1.000.** Every run reached global consensus (one name
  held by all 1000 agents) within the cap; none was capped.
- **Convergence: mean 48,958 interactions, range [31,705, 64,660]** (var ~ 9.56x10^7, so
  sigma ~ 9,800). This is ~49*N ~ 1.5*N^1.5 — consistent with the published O(N^1.5) scaling.
- **Peak #distinct names: mean 502, range [481, 530]** (all >> 1).
- **Peak total words: mean 10,551, range [9,661, 11,110]** (all >> N = 1000; the peak
  vocabulary is ~10.5x the population).
- **Final #distinct names: exactly 1** in every run.
- **Final total words: exactly 1000 (= N)** in every run (each agent ends with exactly
  one name, and it is the same name for all).

## Interpretation — local -> global consensus via a vocabulary peak

The agents share NO global state: every speaker invents or picks a name from only its
own inventory, and every hearer decides only from its own inventory. Yet from these
purely local pairwise negotiations the population self-organises to a single shared
name. The trajectory shows the NG signature: in the early "invention" phase agents coin
many new names and the system fills up with synonyms — total vocabulary climbs to a peak
of ~10,500 words (~10.5*N) spread over ~500 distinct names — and then, as successful
agreements propagate and prune competitors, both the total vocabulary and the
distinct-name count COLLAPSE, ending with exactly one word per agent and exactly one name
in the whole population. This is the local-interaction -> global-lexicon-consensus result
the model claims.

## Verdicts (graded on the LOCKED metrics; falsified would be reported as MISS)

| # | Prediction | Pass clause | Measured | Verdict |
|---|---|---|---|---|
| P1 | Reaches global consensus from local interactions | 100% of runs reach one name held by all N within the cap | 10/10 (fraction 1.000), all within cap | **REPRO** |
| P2 | #distinct names peaks then collapses to 1 | max distinct > 1 AND final distinct = 1 | peak in [481, 530] (>1), final = 1 (all runs) | **REPRO** |
| P3 | Total vocabulary peaks above N then collapses to N | peak words > N AND final words = N | peak in [9,661, 11,110] (>1000), final = 1000 (all runs) | **REPRO** |

**3/3 locked clauses REPRO.**

## Caveats / scope

- This is a faithful reproduction of a published SYNTHETIC model; there is no real-world
  data. The contribution is whether the harness + the lock-before-run discipline
  reproduce the local->global consensus result (with its characteristic vocabulary peak)
  and would catch an artifact — not a claim about real human language.
- The verdicts are tier `refutation` (ADR-013): passing means "not refuted" (the run did
  not contradict the locked prediction), NOT a proof of domain truth.
- Convention: names are invented as monotonically increasing integers (a globally-unique
  fresh token per invention); using strings would be identical up to relabelling.
- Trajectories in `results.json` are sampled once per sweep of N interactions (plus a
  t=0 baseline and a final sample) to keep the file compact at N=1000 while still
  capturing the peak-then-collapse shape; convergence interaction counts are exact
  (consensus is checked after every interaction).
- Determinism: every run is reproducible given its seed (verified by
  `tests/classics/test_naming_game.py`); re-running `run.py` regenerates an identical
  `results.json` and `verdict-bundle.json`.
