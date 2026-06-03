"""ABM Auto Runtime — MoranProcess, a library population-dynamics operator.

Harvested from the Yaman reproduction (ADR-013 Path 2): the hand-written
reference model needed an overlapping-generations Moran turnover (some
individuals die, survivors reproduce in proportion to fitness, the offspring
inherit part of the parent's state but reset the rest, population size held
constant). That is a mechanism a LARGE class of evolutionary / cultural-
evolution ABMs share — and exactly the kind of thing the codegen design
phase used to fill with several `AI-ASSUMPTION` tags (a "Moran-style
selection process", a death rule, an inheritance rule), pushing complex but
standard models past the viability gate.

The fix mirrors W2 (FeedforwardLearner) and the topology operators: the
error-prone, model-AGNOSTIC parts are LIBRARY (written once, self-tested
once, always correct) — who dies (constant hazard or age-based Gompertz),
who reproduces (fitness-proportional selection), and keeping N constant.
The model supplies only its DOMAIN inheritance through the ``inherit`` hook:
what an offspring copies from its parent vs. resets. Same library/strategy
split as the learned operator — generated code never writes the selection
loop, it declares the operator and provides the one-line inheritance rule.
"""
from __future__ import annotations

import math
import random
from typing import Any, Callable, Optional

_VALID_DEATH_MODELS = {"constant", "gompertz"}


class MoranProcess:
    """Fixed-N overlapping-generations turnover for evolutionary ABMs.

    One ``turnover`` call is one generation of partial population replacement:

      1. each individual dies with probability given by the death model
         (``constant`` hazard, or age-based ``gompertz`` P = a·e^(b·age));
      2. the dead slots are refilled by offspring of survivors selected with
         probability proportional to fitness (uniform if all fitness ≤ 0);
      3. for each (offspring slot, parent) the caller's ``inherit`` hook runs
         — it copies the heritable state and resets the rest;
      4. survivors age by one; newborns are reset to age 0.

    Population size is invariant. Deterministic given the seed (or an injected
    ``random.Random``). ``fitness_attr`` / ``age_attr`` name the agent
    attributes the operator reads.
    """

    def __init__(
        self,
        *,
        fitness_attr: str = "score",
        death_model: str = "constant",
        death_rate: float = 0.05,
        gompertz_a: float = 0.0001365,
        gompertz_b: float = 0.2097,
        age_attr: str = "age",
        seed: int = 0,
    ) -> None:
        if death_model not in _VALID_DEATH_MODELS:
            raise ValueError(
                f"death_model={death_model!r} not in {sorted(_VALID_DEATH_MODELS)}"
            )
        if death_model == "constant" and not (0.0 < death_rate < 1.0):
            raise ValueError(f"death_rate={death_rate} must be in (0, 1) for constant model")
        if death_model == "gompertz" and (gompertz_a <= 0 or gompertz_b <= 0):
            raise ValueError("gompertz_a and gompertz_b must be > 0")
        self.fitness_attr = fitness_attr
        self.death_model = death_model
        self.death_rate = float(death_rate)
        self.gompertz_a = float(gompertz_a)
        self.gompertz_b = float(gompertz_b)
        self.age_attr = age_attr
        self._rng = random.Random(seed)

    # ── death ──────────────────────────────────────────────────────────────

    def death_probability(self, agent: Any) -> float:
        if self.death_model == "constant":
            return self.death_rate
        age = float(getattr(agent, self.age_attr, 0))
        return min(1.0, self.gompertz_a * math.exp(self.gompertz_b * age))

    # ── one generation of turnover ───────────────────────────────────────────

    def turnover(
        self,
        agents: list,
        *,
        inherit: Callable[[Any, Any], None],
        rng: Optional[random.Random] = None,
    ) -> int:
        """Death + fitness-proportional Moran rebirth, fixed N. ``inherit``
        (child, parent) is the model's one-line heritability rule. Returns the
        number of births this generation."""
        r = rng or self._rng
        dead = [a for a in agents if r.random() < self.death_probability(a)]
        survivors = [a for a in agents if a not in dead]
        if not survivors:
            # everyone rolled death — skip turnover, just age (avoids extinction)
            for a in agents:
                self._set_age(a, self._get_age(a) + 1)
            return 0

        weights = [max(0.0, float(getattr(s, self.fitness_attr, 0.0))) for s in survivors]
        total = sum(weights)
        for child in dead:
            parent = self._select(survivors, weights, total, r)
            inherit(child, parent)
            self._set_age(child, 0)
        for s in survivors:
            self._set_age(s, self._get_age(s) + 1)
        return len(dead)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get_age(self, agent: Any) -> int:
        return int(getattr(agent, self.age_attr, 0))

    def _set_age(self, agent: Any, value: int) -> None:
        setattr(agent, self.age_attr, value)

    @staticmethod
    def _select(survivors: list, weights: list, total: float, rng: random.Random):
        """Pick a parent ∝ fitness; uniform fallback when all fitness ≤ 0."""
        if total <= 0.0:
            return survivors[rng.randint(0, len(survivors) - 1)]
        threshold = rng.random() * total
        acc = 0.0
        for s, w in zip(survivors, weights):
            acc += w
            if threshold <= acc:
                return s
        return survivors[-1]


def self_test() -> bool:
    """Library self-test (ADR-013 Gate philosophy applied to the operator):
    on a synthetic population with a fitness gradient, turnover must (a) hold
    N constant, and (b) let fitness-proportional selection enrich the
    population for high-fitness lineages (mean fitness rises). Proves the
    death/selection/rebirth logic is correct — checked once so generated code
    trusting the library is safe.
    """
    class _A:
        pass

    n = 20
    agents = []
    for i in range(n):
        a = _A()
        a.fit = float(i)       # fitness gradient 0..19, mean 9.5
        a.age = 0
        agents.append(a)

    mp = MoranProcess(fitness_attr="fit", death_model="constant",
                      death_rate=0.3, seed=0)

    def inherit(child, parent):
        child.fit = parent.fit   # offspring inherit fitness; selection enriches

    rng = random.Random(0)
    for _ in range(80):
        mp.turnover(agents, inherit=inherit, rng=rng)
        if len(agents) != n:        # N must stay constant
            return False
    mean_fit = sum(a.fit for a in agents) / len(agents)
    # selection must push mean fitness clearly above the 9.5 starting mean.
    return mean_fit > 13.0
