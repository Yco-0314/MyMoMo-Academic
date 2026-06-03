"""Innovator — one individual in the population.

State (per SI Algorithms 1 & 2):
  inventory          set of owned item indices (starts = the 6 base items)
  memory             set of frozenset(T) already attempted (no re-attempts)
  successful         list of frozenset(recipe) that produced an innovation
                     (feeds updateModels — "all successful recipes acquired
                     via individual AND social learning")
  age, score         int / float
  semantic_model     FeedforwardLearner (the trainable distributional model M)

Algorithm 2 lives here as ``individual_attempt``. The three branches:
  rand > P_S          -> random exploration (n items sampled from inventory)
  else, rand > P_G    -> semantic prediction (Predict chain over owned items)
  else                -> generalization (swap an item in a known recipe for
                         its embedding-nearest owned neighbour)

INTERPRETATION (documented, not silent): the SI's Predict(M, t) ranges over
all items, but you can only physically combine items you OWN, so we take the
argmax of p(y|t) restricted to the current inventory. Likewise the
generalization neighbour is the embedding-nearest OWNED item. This is the
faithful reading of "combining existing items" (SI, Task interface).
"""
from __future__ import annotations

import numpy as np

from abm_auto.runtime import Agent


class Innovator(Agent):
    def setup(self):
        # Scalars survive CSV/_safe_attr; containers + model attached by the
        # model in setup() (they need task/scenario knowledge).
        self.age: int = self._safe_attr("age", 0)
        self.score: float = self._safe_attr("score", 0.0)
        self.inventory: set = set()
        self.memory: set = set()
        self.successful: list = []
        self.semantic_model = None
        self._task = None

    # ── lifecycle ─────────────────────────────────────────────────────────

    def attach(self, task, semantic_model) -> None:
        """Give the agent the shared task graph + a fresh semantic model and
        seed its inventory with the base items."""
        self._task = task
        self.semantic_model = semantic_model
        self.inventory = set(task.given_indices())
        self.memory = set()
        self.successful = []
        self.age = 0
        self.score = 0.0

    def reborn_from(self, parent: "Innovator") -> None:
        """Offspring: inherits the parent's trained semantic model (a copy),
        but starts with only the base inventory (SI: 'Offspring inherit their
        parent's semantic model but begin with only the basic items')."""
        import copy

        self.semantic_model = copy.deepcopy(parent.semantic_model)
        self.inventory = set(self._task.given_indices())
        self.memory = set()
        self.successful = []
        self.age = 0
        self.score = 0.0

    # ── Algorithm 2: individual innovation ────────────────────────────────

    def individual_attempt(self, rng, p_semantic: float, p_generalize: float) -> None:
        n = rng.randint(1, 3)                       # 1, 2, or 3 items
        inv = list(self.inventory)

        if rng.random() > p_semantic or self.semantic_model is None:
            # random exploration: n items sampled WITH replacement, then deduped
            T = {rng.choice(inv) for _ in range(n)}
        elif rng.random() > p_generalize:
            T = self._semantic_chain(n, rng)
        else:
            T = self._generalize(rng)

        self._attempt(T)

    def _semantic_chain(self, n: int, rng) -> set:
        """t1 random from inventory; t2 = best owned partner of t1; t3 = best
        owned partner of t2. Predict restricted to owned items."""
        t1 = rng.choice(list(self.inventory))
        T = {t1}
        if n >= 2:
            t2 = self._predict_owned(t1, exclude=T, rng=rng)
            if t2 is not None:
                T.add(t2)
                if n >= 3:
                    t3 = self._predict_owned(t2, exclude=T, rng=rng)
                    if t3 is not None:
                        T.add(t3)
        return T

    def _generalize(self, rng) -> set:
        """Take a known successful recipe, swap one item for its embedding-
        nearest owned neighbour (similarity-based generalization)."""
        if not self.successful:
            # no recipe to generalize from yet -> fall back to a random pair
            inv = list(self.inventory)
            return {rng.choice(inv), rng.choice(inv)}
        base_recipe = list(rng.choice([list(s) for s in self.successful]))
        tj = rng.choice(base_recipe)
        tk = self._sample_near_owned(tj, exclude=set(base_recipe), rng=rng)
        T = set(base_recipe)
        if tk is not None:
            T.discard(tj)
            T.add(tk)
        return T

    def _predict_owned(self, t: int, exclude: set, rng):
        """Sample y ~ p(y | t) restricted to owned items (renormalised),
        excluding `exclude`. SAMPLING, not argmax: the paper's semantic model
        is a distribution that is sampled; argmax collapses to a single
        repeated partner and explores worse than random (see probe_semantic.py
        / FINDINGS-science.md run 1)."""
        proba = self.semantic_model.predict_proba(t)
        cand = [it for it in self.inventory if it != t and it not in exclude]
        if not cand:
            return None
        weights = [float(proba[it]) for it in cand]
        total = sum(weights)
        if total <= 0.0:
            return cand[rng.randint(0, len(cand) - 1)]
        r = rng.random() * total
        acc = 0.0
        for it, w in zip(cand, weights):
            acc += w
            if r <= acc:
                return it
        return cand[-1]

    def _sample_near_owned(self, t: int, exclude: set, rng):
        """Sample an owned item with probability decreasing in embedding
        distance to t (soft nearest): p ∝ exp(-dist / mean_dist).

        Stochastic counterpart of a deterministic argmin-nearest. Run 3
        showed deterministic nearest collapses generalization into a single
        repeated neighbour (the same failure mode argmax had for the
        predict-chain); sampling keeps the analogy diverse while still biased
        toward similar items. (The prior deterministic version is preserved
        in git at the run-3 commit.)"""
        E = self.semantic_model.E
        v = E[t]
        cand = [it for it in self.inventory if it != t and it not in exclude]
        if not cand:
            return None
        dists = np.array([float(np.linalg.norm(E[it] - v)) for it in cand])
        scale = float(dists.mean()) + 1e-9
        w = np.exp(-dists / scale)
        total = float(w.sum())
        if total <= 0.0:
            return cand[rng.randint(0, len(cand) - 1)]
        w = w / total
        r = rng.random()
        acc = 0.0
        for it, wi in zip(cand, w):
            acc += float(wi)
            if r <= acc:
                return it
        return cand[-1]

    def _attempt(self, T: set) -> None:
        """Execute a combination: if novel, valid, and productive, innovate."""
        if not T:
            return
        key = frozenset(T)
        if key in self.memory:
            return
        self.memory.add(key)
        product = self._task.combine(key)
        if product is not None and product not in self.inventory:
            self.inventory.add(product)
            self.score += self._task.weight_of(product)
            self.successful.append(key)

    # ── social learning (called by the environment / Algorithm 1) ─────────

    def try_social_learning(self, demonstrator: "Innovator", rng) -> bool:
        """Copy ONE recipe: an item the demonstrator has that I lack and can
        craft from my CURRENT inventory. Returns True if a recipe executed."""
        if demonstrator is self:
            return False
        candidates = []
        for item in demonstrator.inventory:
            if item in self.inventory:
                continue
            rec = self._task.recipe_for(item)
            if rec is not None and rec <= self.inventory:
                candidates.append((rec, item))
        if not candidates:
            return False
        rec, item = candidates[rng.randint(0, len(candidates) - 1)]
        self.inventory.add(item)
        self.score += self._task.weight_of(item)
        self.successful.append(rec)        # socially-acquired recipes train M too
        self.memory.add(rec)
        return True

    # ── updateModels (Algorithm 1) ────────────────────────────────────────

    def update_semantic_model(self, epochs: int) -> None:
        """Train M on co-ingredient pairs from all successful recipes."""
        if self.semantic_model is None or not self.successful:
            return
        pairs = []
        for rec in self.successful:
            items = list(rec)
            for a in items:
                for b in items:
                    if a != b:
                        pairs.append((a, b))
        if pairs:
            self.semantic_model.train(pairs, epochs=epochs)
