# Findings — Hawk-Dove e2e RE-RUN #5 (the clean reproduction — 11/11)

Workspace `workspace/20260609_014715_06412a`. Predictions locked pre-run
(`faa4d37`). Under test: the interaction-completeness gate (`16aa73a`) + the bug-A
refinement (`2eeace3`), composing with every earlier fix. **11 HIT / 0 MISS. E6 is
a genuine, selection-driven reproduction of the Hawk-Dove ESS — for the first time
across five runs, and for the right reason.**

## Scorecard (predicted → actual)

| # | prediction | actual | verdict |
|---|---|---|---|
| E1 | viability passes (≤1 refine) | passed iter 2/3 (assumptions=1) | **HIT** |
| E2 | operators + μ + all-Hawk + death_rate≥0.05; strategy inherited not reset | death_rate=0.5; inherit_attrs=['strategy']; reset_attrs=['score','fitness']; μ=0.01 | **HIT** |
| E3 | Coverage Gate PASS | passed | **HIT** |
| E4 | synthesis no fire | did not fire | **HIT** |
| E5a | model.py wires self.game + drives turnover + inherit(strategy)+μ | all present | **HIT** |
| E5b | env.step() plays the game (reached from step) | gate fired → GVR rewrote env.step to take agents/scenario + call `self.game.play` | **HIT** |
| **E6** | all-Hawk → fluctuates around ESS 0.5 via selection | **1.000 → ≤0.60 by gen 11 → last-100 mean 0.515 (sd 0.042), last-30 0.530** | **HIT** ✅ |
| E7 | template faithful to spec values | V/C, death_rate=0.5, μ=0.01 emitted exactly | **HIT** |
| E8 | _moran_inherit has μ re-draw + inherits strategy | both present | **HIT** |
| E9 | env.py has no hand-rolled turnover | none | **HIT** |
| E10 | strategy heritable e2e (inherit, not reset) | inherit_attrs=['strategy'], not in reset_attrs | **HIT** |

## E6 — a real reproduction, verified mechanism (not a coincidence)

The trajectory is the textbook result, reached by selection:
- gens 0–10: all-Hawk (1.0), `mean_score = −20` (every agent plays 10 Hawk-vs-Hawk
  rounds at (V−C)/2 = −1, ×2 for symmetric scoring → −20). Real, negative fitness.
- gen 11: a mutation-seeded Dove invades and selection amplifies it hard — Doves
  earn 0 vs Hawks while Hawks earn −1, so Doves are far fitter when Hawks are
  common. `hawk_ratio` crashes to 0.495, `mean_score` jumps to +10.
- gens 12–299: fluctuates around the ESS — **last-100 mean 0.515, last-30 mean
  0.530**, sd ≈ 0.03–0.04 (finite-N noise at N=200). ESS = V/C = 0.5.

This is the RIGHT reason, unlike re-run #2's coincidental 0.66 drift. `mean_score`
swings −20 → +10 with the composition, which only happens if the game is actually
played and fitness is real — so selection, not neutral drift, is driving it. The
operator does the payoff; the model drives the Moran turnover; the inherited
strategy is what selection acts on; mutation provides the invading Dove.

## Layer 6 closed: env.step() drives the interaction

`core/environment.py:step()` now plays the game on the execution path:

```python
def step(self, agents, scenario):
    for agent in agents:
        agent.reset_score()
    for agent in agents:
        opponents = random.sample([a for a in agents if a.id != agent.id], num_opponents)
        for opponent in opponents:
            pa, pb = self.game.play(agent.strategy, opponent.strategy)   # operator, reached from step()
            agent.score += pa
            opponent.score += pb
    for agent in agents:
        agent.compute_fitness()
```

The gate fired ("declared PayoffGame self.game is never called"), the GVR loop
rewrote `environment.step()` to take `(agents, scenario)` and call
`self.game.play(...)`. The operator is now REACHED from the framework's only
per-tick entry — the run-#4 orphan (game stranded in an uncalled `agent.step()`)
is gone.

## The whole arc: 5 runs, 6 layers, all closed, composing

| run | layer found | fix | this run |
|----|-------------|-----|---------|
| #1 | payoff hand-rolled | operator-use gate | — |
| #2 | strategy not inherited / dead hand-rolled turnover | bug A / bug B gate | held |
| #3 | death_rate degenerate | bug C (story + floor) | death_rate=0.5 ✓ |
| #4 | strategy reset each gen / orphaned interaction | A refinement / interaction-completeness gate | both held ✓ |
| #5 | — | — | **11/11, clean E6** |

Every fix from the arc is present and composing on one live run: operators
constructed + wired (E5a), payoff called from env.step (E5b, layer 6), turnover
model-driven with no hand-roll (E9), strategy inherited not reset (E10), sane
death_rate (E2), mutation seeding (E8) — and the result is the ESS reached by
selection from an all-Hawk extreme (E6).

## Honest bottom line

I predicted E6 HIT five times and missed the first four — each miss a distinct
layer the locked-prediction discipline forced into the open (mutation,
inherit_attrs, death_rate, reset_attrs + orphaned interaction). The fifth is a
real HIT: I read the CSV and the env.py, and the mechanism is correct, not a
V/C=0.5 coincidence. The discipline did exactly its job across the whole arc — it
turned five "looks reproduced" into four caught false-passes and one verified
reproduction. The architecture (operators → coverage/structural gates → template
ownership → spec normalization → interaction-completeness) is proven end-to-end on
a live, untrusted-paper reproduction that converges to the textbook ESS.
