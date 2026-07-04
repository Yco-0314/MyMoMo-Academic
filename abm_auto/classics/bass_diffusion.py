"""Bass (1969) new-product diffusion — a faithful agent-based reproduction.

Source: Bass, F.M. (1969) "A New Product Growth for Model Consumer Durables",
Management Science 15(5):215-227.

Rules (verified against the paper's hazard, recast at the agent level):
  * N agents, every one a NON-adopter at t=0. Adoption is irreversible.
  * Each tick, the adopter FRACTION ``F`` is computed ONCE, from the state at the
    START of the tick. Then every non-adopter independently adopts with probability
    ``p + q * F`` (clamped to [0, 1]).  ``p`` = coefficient of innovation (external /
    advertising influence, acts even at F=0), ``q`` = coefficient of imitation
    (word-of-mouth, scales with how many have already adopted).
  * The update is SYNCHRONOUS: F is frozen for the whole tick, so the order in which
    agents decide does not matter (decisions within a tick do not see each other's new
    adoptions). This is the discrete-tick analogue of Bass' continuous-time hazard
    f(t)/(1-F(t)) = p + q*F(t); we note the discrete-vs-continuous subtlety in FINDINGS.

This is the agent-level dual of Bass' aggregate ODE. Bass' continuous model gives the
adoption-rate peak at the analytic t* = ln(q/p)/(p+q); the discrete agent model is
compared against that anchor (it is NOT fit to the run).

Built on the neutral platform (``abm_auto._platform``): each consumer is an
``AdopterAgent`` whose ``step`` stages its (irreversible) adoption against the frozen
tick fraction; ``BassModel`` freezes F, drives the ``AgentSet`` scheduler, commits all
adoptions at once, and records (via a ``DataCollector``) the cumulative adopters and the
per-tick new adoptions. Given a seed the whole run is reproducible.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class AdopterAgent(Agent):
    """One consumer. ``adopted`` is its binary, irreversible state.

    The adoption hazard is evaluated against ``model.tick_fraction`` — the adopter
    fraction frozen at the START of the tick — so all agents in a tick decide against
    the same F (synchronous update). The decision is staged in ``_adopting_now`` and
    committed by the model after every agent has stepped.
    """

    def __init__(self, agent_id: int, model: "BassModel") -> None:
        super().__init__(agent_id, model)
        self.adopted = False
        self._adopting_now = False

    def step(self) -> None:
        """Stage this tick's decision. An adopter stays adopted (irreversible). A
        non-adopter adopts with probability p + q*F, where F is the model's frozen
        tick fraction; each agent draws from the model's seeded RNG."""
        if self.adopted:
            self._adopting_now = False  # already counted; no NEW adoption this tick
            return
        prob = self.model.adoption_probability(self.model.tick_fraction)
        self._adopting_now = self.model.rng.random() < prob


# -- Model --------------------------------------------------------------------

class BassModel(AgentModel):
    """Drives the Bass diffusion over N agents until (near-)full adoption.

    Construct with N, p, q, a seed, and a stop fraction. ``run`` iterates synchronous
    ticks — freeze F, every agent stages its decision, commit all adoptions, record —
    until the cumulative adopter fraction reaches ``stop_fraction`` (or ``max_steps``),
    then returns a summary dict (cumulative series + per-tick new-adoption series).
    """

    def __init__(self, n: int = 10_000, *, p: float = 0.03, q: float = 0.38,
                 seed: int = 0, stop_fraction: float = 0.99,
                 max_steps: int = 1000) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.seed_value = seed
        self.n = n
        self.p = p
        self.q = q
        self.stop_fraction = stop_fraction
        self.max_steps = max_steps

        #: Adopter fraction frozen at the start of the current tick (set in ``step``).
        self.tick_fraction = 0.0
        #: New adoptions in the tick just committed (for the per-tick rate series).
        self._new_adoptions = 0

        self.agent_list: List[AdopterAgent] = []
        for i in range(n):
            agent = AdopterAgent(i, self)
            self.agent_list.append(agent)
            self.add_agent(agent)

        # cumulative = total adopters; new = adopters added in the last committed tick.
        self.reporter = DataCollector({
            "cumulative": lambda m: m.adopter_count(),
            "new": lambda m: m._new_adoptions,
        })

    # -- the Bass hazard --
    def adoption_probability(self, fraction: float) -> float:
        """Per-tick adoption probability for a non-adopter: clamp(p + q*F, 0, 1)."""
        prob = self.p + self.q * fraction
        if prob < 0.0:
            return 0.0
        if prob > 1.0:
            return 1.0
        return prob

    # -- metrics --
    def adopter_count(self) -> int:
        return sum(1 for a in self.agent_list if a.adopted)

    def adopter_fraction(self) -> float:
        return self.adopter_count() / self.n if self.n else 0.0

    # -- tick --
    def step(self) -> None:
        """One synchronous Bass tick: freeze F, every non-adopter stages its decision
        against that frozen F, then the model commits all adoptions at once and records
        the new cumulative count and the per-tick new-adoption count."""
        self.tick_fraction = self.adopter_fraction()   # F frozen for the whole tick
        self.agents.step()                              # each agent stages _adopting_now
        new_adoptions = 0
        for a in self.agent_list:
            if a._adopting_now and not a.adopted:
                a.adopted = True
                new_adoptions += 1
        self._new_adoptions = new_adoptions
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate ticks until the stop fraction (or max_steps); return the summary.

        The t=0 baseline record (0 adopters, 0 new) is collected before any tick, so
        ``new[k]`` is the count of adoptions during tick k (k>=1) and ``new[0]==0``.
        """
        self.reporter.collect(self)                     # t=0 baseline (no adopters)
        for _ in range(self.max_steps):
            self.step()
            if self.adopter_fraction() >= self.stop_fraction:
                break
        cumulative = self.reporter.series("cumulative")
        new = self.reporter.series("new")
        return {
            "n": self.n,
            "p": self.p,
            "q": self.q,
            "seed": self.seed_value,
            "steps": self.t,
            "final_adopter_count": self.adopter_count(),
            "final_adopter_fraction": self.adopter_fraction(),
            "cumulative_series": cumulative,
            "cumulative_fraction_series": [c / self.n for c in cumulative],
            "new_series": new,
            "new_fraction_series": [c / self.n for c in new],
        }


# -- analytics + multi-seed helpers -------------------------------------------

def analytic_peak_time(p: float, q: float) -> float:
    """Bass' continuous-time adoption-rate peak t* = ln(q/p)/(p+q).

    Defined only for q>p (an interior peak); for q<=p the continuous rate is
    monotonically decreasing and there is no interior peak (t* <= 0)."""
    return math.log(q / p) / (p + q)


def run_single(n: int = 10_000, *, p: float = 0.03, q: float = 0.38, seed: int = 0,
               stop_fraction: float = 0.99, max_steps: int = 1000) -> Dict[str, Any]:
    """One Bass diffusion run at a given seed."""
    return BassModel(n, p=p, q=q, seed=seed, stop_fraction=stop_fraction,
                     max_steps=max_steps).run()


def _pad(series: List[float], length: int, fill: float = None) -> List[float]:
    """Right-pad a series to ``length``. For cumulative curves, fill with the LAST
    value (adoption is irreversible, the curve plateaus); for rate curves, fill 0."""
    if len(series) >= length:
        return list(series[:length])
    pad_value = series[-1] if (fill is None and series) else (fill or 0.0)
    return list(series) + [pad_value] * (length - len(series))


def run_many_seeds(n: int = 10_000, *, p: float = 0.03, q: float = 0.38,
                   n_seeds: int = 20, seed_base: int = 0,
                   stop_fraction: float = 0.99, max_steps: int = 1000) -> Dict[str, Any]:
    """Run ``n_seeds`` Bass diffusions and average the curves over seeds.

    Each seed uses ``seed_base + i``. Runs may have different lengths (they stop at the
    first tick crossing ``stop_fraction``); the cumulative curves are right-padded with
    their final (plateau) value and the per-tick new-adoption curves with 0 before
    averaging, so the mean curves are defined over the longest run. Returns the mean
    cumulative-fraction curve, the mean per-tick new-fraction curve, and the per-seed
    argmax (peak tick) of the new-adoption curve.
    """
    runs = [run_single(n, p=p, q=q, seed=seed_base + i, stop_fraction=stop_fraction,
                        max_steps=max_steps) for i in range(n_seeds)]
    max_len = max(len(r["cumulative_fraction_series"]) for r in runs)

    cum_padded = [_pad(r["cumulative_fraction_series"], max_len) for r in runs]
    new_padded = [_pad(r["new_fraction_series"], max_len, fill=0.0) for r in runs]

    mean_cumulative = [sum(col) / n_seeds for col in zip(*cum_padded)]
    mean_new = [sum(col) / n_seeds for col in zip(*new_padded)]

    # per-seed peak tick of the (per-tick) new-adoption curve.
    per_seed_peak = [_argmax(r["new_series"]) for r in runs]
    mean_peak_tick = sum(per_seed_peak) / n_seeds

    return {
        "n": n, "p": p, "q": q, "n_seeds": n_seeds, "seed_base": seed_base,
        "stop_fraction": stop_fraction,
        "mean_cumulative_fraction": mean_cumulative,
        "mean_new_fraction": mean_new,
        "mean_peak_tick_of_mean_curve": _argmax(mean_new),
        "per_seed_peak_tick": per_seed_peak,
        "mean_per_seed_peak_tick": mean_peak_tick,
        "final_cumulative_fraction": mean_cumulative[-1],
        "max_len": max_len,
        "per_seed_final_fraction": [r["final_adopter_fraction"] for r in runs],
        "per_seed_steps": [r["steps"] for r in runs],
    }


def _argmax(series: List[float]) -> int:
    """Index of the max element (first occurrence)."""
    best_i, best_v = 0, series[0] if series else 0
    for i, v in enumerate(series):
        if v > best_v:
            best_i, best_v = i, v
    return best_i


def is_sigmoid(cumulative: List[float]) -> Dict[str, Any]:
    """Check that a cumulative curve is sigmoid: non-decreasing (monotone) with an
    INTERIOR inflection (the per-tick increments rise then fall, so the argmax of the
    first difference is strictly interior — not at the first or last step).

    Returns a dict with ``monotone``, ``inflection_tick`` (argmax of increments), and
    ``inflection_interior`` (0 < inflection < len-1)."""
    monotone = all(cumulative[i + 1] >= cumulative[i] - 1e-12
                   for i in range(len(cumulative) - 1))
    increments = [cumulative[i + 1] - cumulative[i] for i in range(len(cumulative) - 1)]
    inflection = _argmax(increments) if increments else 0
    interior = 0 < inflection < len(increments) - 1
    return {
        "monotone": monotone,
        "inflection_tick": inflection,
        "inflection_interior": interior,
    }
