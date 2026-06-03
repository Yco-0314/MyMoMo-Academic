"""Algorithm 1 — one generation of cumulative cultural evolution.

Per SI pseudocode (Algorithm 1):
  1. Attempts phase: repeat N x n_attempts times, each time a RANDOM
     individual (with budget left) makes one attempt — w.p. P_SL a social-
     learning attempt (copy a craftable recipe off the highest-scoring
     individual), else an individual attempt (Algorithm 2). Random
     interleaving lets a same-generation discovery be copied within the
     same generation.
  2. updateModels: every individual trains its semantic model on all
     recipes it has acquired (individual + social).
  3. Death: each individual dies w.p. P_D = a * exp(b * age)  (Gompertz;
     a=0.0001365, b=0.2097 — SI lines 270-272).
  4. Moran turnover: dead slots are refilled by offspring of survivors
     selected with probability proportional to score; offspring inherit the
     parent's trained semantic model but reset to the base inventory.

HARVEST NOTE (Path-2 → architecture): steps 3-4 are a self-contained
"Moran/Wright-Fisher population-dynamics" operator (W4 candidate) — fixed
N, fitness-proportional selection, inheritance hook. A research model
should declare "turnover: moran, fitness: score" and get this, not write
selection loops the viability gate then flags as assumptions.
"""
from __future__ import annotations

from abm_auto.runtime import Environment


class YamanEnvironment(Environment):
    def setup(self):
        # Metrics recomputed each generation by the model; declared here so
        # the DataCollector can read them as environment properties.
        self.repertoire_size = 0      # distinct non-base items the population holds
        self.max_level = 0            # deepest innovation level reached
        self.mean_score = 0.0
        self.max_score = 0.0
        self.mean_inventory = 0.0

    # ── one generation ────────────────────────────────────────────────────

    def step(self, agents, scenario, task, moran, rng) -> None:
        self._attempts_phase(agents, scenario, rng)
        for a in agents:
            a.update_semantic_model(int(scenario.train_epochs))
        # W4 MoranProcess operator owns death + fitness-proportional rebirth +
        # fixed N + ageing. The inherit hook is the one model-specific line:
        # offspring inherits the trained model, resets to the base inventory.
        moran.turnover(agents, inherit=lambda c, p: c.reborn_from(p), rng=rng)

    def _attempts_phase(self, agents, scenario, rng) -> None:
        p_social = float(scenario.p_social)
        p_semantic = float(scenario.p_semantic)
        p_generalize = float(scenario.p_generalize)
        budget = {a.id: int(scenario.n_attempts) for a in agents}
        remaining = [a for a in agents if budget[a.id] > 0]

        while remaining:
            agent = rng.choice(remaining)
            if rng.random() < p_social:
                demo = max(agents, key=lambda x: x.score)
                agent.try_social_learning(demo, rng)   # attempt spent either way
            else:
                agent.individual_attempt(rng, p_semantic, p_generalize)
            budget[agent.id] -= 1
            if budget[agent.id] <= 0:
                remaining = [a for a in remaining if a.id != agent.id]
