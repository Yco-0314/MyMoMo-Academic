# Coverage extraction — list the model's computational MECHANISMS

You read an ABM design + mechanism spec and output a JSON list of the model's
distinct **mechanisms** (the computational pieces a code generator must build).
You are EVIDENCE for a deterministic Coverage Gate — your job is accurate
recall + honest markers, NOT a verdict. Do not decide buildability; just
describe each mechanism with the closed labels below.

## Inputs

### DESIGN + mechanism spec

{{ design }}

## What to emit

A single fenced ```json``` block: a JSON list, one object per mechanism.
**List EVERY mechanism that LEARNS, TRAINS, GENERATES, OPTIMIZES, MATCHES a
market, or UPDATES A BELIEF.** Missing one is the worst error (it lets an
unbuildable model slip through). Plain rules / arithmetic / sampling / movement
are ONE catch-all `ordinary_logic` mechanism — don't enumerate those.

Each object:

```json
{
  "name": "semantic_model",
  "capability": "learned_predictor",
  "training_signal": "supervised_pairs",
  "markers": ["..."],
  "std_algorithm": null,
  "faithfulness": "full"
}
```

### `capability` — pick exactly one (closed set)

- `learned_predictor` — a supervised net/embedding trained on (input,target) pairs
- `lookup_table` — a static ORDER-FREE combination / reaction table (a set of
  inputs → one output; e.g. a crafting recipe)
- `payoff_game` — a 2-player game payoff matrix: ORDERED (a player's payoff vs an
  opponent), dual-output (each gets a payoff). Use this for any game-theoretic
  payoff (prisoner's dilemma, hawk-dove, public goods) — NOT `lookup_table`,
  whose order-free single-output shape cannot represent a payoff matrix.
- `population_process` — FIXED-size birth-death turnover (one death per birth)
- `variable_population` — energy/resource birth & death where the population SIZE
  grows and shrinks (wolf-sheep, rabbits-grass, daisyworld) — NOT
  `population_process`, which holds N constant
- `reinforcement_learning` — a policy/value learned from REWARD
- `generative_model` — GAN / VAE / diffusion-net (deep generative / adversarial)
- `bayesian_filter` — a belief update (Kalman, particle filter)
- `optimization` — solves an objective each step (LP / MILP / utility max)
- `market_mechanism` — auction / order-book / market clearing
- `pde_diffusion` — a continuous spatial field / reaction-diffusion solver
- `ordinary_logic` — everything else (rules, thresholds, sampling, movement)

### `training_signal` — for learned mechanisms only (else `null`)

`supervised_pairs` | `reward_td` | `adversarial` | `reconstruction` | `none`

### `markers` — honest structural flags (this is the anti-flatten signal)

Any of: `adversarial`, `multi_network`, `generative`, `encoder_decoder`,
`deep_attention`, `reward`. **If the mechanism learns from reward, include
`reward` even if it looks like a feed-forward net — do NOT flatten an RL agent
into a supervised predictor.** If it is adversarial / multi-network, say so.

### `std_algorithm` — if it is a NAMED standard algorithm, else `null`

`kalman_filter` | `tabular_q_learning` | `linear_program` |
`finite_difference_diffusion`. Use ONLY for the genuine standard algorithm
(e.g. tabular Q-learning, not deep Q-networks).

### `faithfulness`

`full` if a single provided operator could faithfully realise the WHOLE
mechanism; `partial` if only approximately; `none` if not.

## Rules

- Closed labels only — never invent a capability or marker.
- Recall over precision: list every learned/generative/optimizing/market/belief
  mechanism. The deterministic gate decides covered-or-not; you supply evidence.
- Honest markers: reward → `reward`; adversarial → `adversarial`. Flattening
  here defeats the gate.

## Output

ONE fenced ```json``` block, a JSON list. Nothing else.
