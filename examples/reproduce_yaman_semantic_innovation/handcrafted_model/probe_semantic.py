"""Diagnostic probe 2 (upper-bound): CAN the FeedforwardLearner learn the
recipe co-occurrence structure at all? Sweep lr x epochs, trained on ALL
real co-occurrence pairs, and measure:
  - final cross-entropy loss (uniform baseline = ln(n_items) ~ 5.21)
  - sampled valid-partner rate vs base rate (did mass concentrate on the
    valid partner SET?)
  - argmax-diversity (does argmax collapse to one item?)

If a high-lr / many-epoch regime lifts the SAMPLED rate well above chance,
the operator is sound and run-1's failure is the in-sim training regime
(lr=0.001, few recipes) + argmax. If even the upper bound stays ~uniform,
the representation/loss is too weak for a 184-way one-to-many map.
"""
from __future__ import annotations

import math
import random

from abm_auto.runtime import FeedforwardLearner
from core.task import load_totem_task

task = load_totem_task()
partners: dict[int, set] = {}
pairs = []
for ings, prod in task.recipe_lookup.items():
    items = list(ings)
    for a in items:
        for b in items:
            if a != b:
                partners.setdefault(a, set()).add(b)
                pairs.append((a, b))
ingredient_items = [x for x in partners if partners[x]]
n = len(ingredient_items)
base = sum(len(partners[x]) / (task.n_items - 1) for x in ingredient_items) / n
print(f"vocab={task.n_items} ingredient-items={n} pairs={len(pairs)} "
      f"uniform-loss={math.log(task.n_items):.2f} base-rate={base:.3f}\n")

rng = random.Random(0)


def evaluate(M):
    samp_hits = trials = 0
    am_set = set()
    for x in ingredient_items:
        am_set.add(M.predict(x, argmax=True))
        for _ in range(20):
            y = M.predict(x, argmax=False, seed=rng.randint(0, 1 << 30))
            samp_hits += (y in partners[x])
            trials += 1
    return samp_hits / trials, len(am_set)


print(f"{'lr':>6} {'epochs':>7} {'loss':>7} {'sampled_valid':>14} {'argmax_distinct':>16}")
for lr in (0.05, 0.2, 0.5):
    for epochs in (500, 2000):
        M = FeedforwardLearner(n_items=task.n_items, embed_dim=16, hidden_dim=16,
                               learning_rate=lr, seed=0)
        for _ in range(epochs):
            loss = M.train(pairs, epochs=1)
        sr, amd = evaluate(M)
        print(f"{lr:>6} {epochs:>7} {loss:>7.3f} {sr:>14.3f} {amd:>16}")
