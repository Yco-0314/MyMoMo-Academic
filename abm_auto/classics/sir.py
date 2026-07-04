"""SIR epidemic threshold — a faithful agent-based reproduction (well-mixed).

Source: Kermack, W.O. & McKendrick, A.G. (1927) "A contribution to the mathematical
theory of epidemics", Proc. R. Soc. Lond. A 115(772):700-721. Final-size relation:
Brauer, F. (2008) "Compartmental models in epidemiology", in *Mathematical
Epidemiology*, Lecture Notes in Mathematics 1945, Springer.

Rules (faithful to the discrete-time, well-mixed / mass-action SIR):
  * N agents, each a ``PersonAgent`` in one of three states S / I / R.
  * Each tick (synchronous update):
      - I_count is read at the START of the tick.
      - each S agent becomes I with probability 1 - (1 - beta/N)^I_count
        (the discrete force of infection; the per-tick hazard of meeting at least
        one of the I_count infectives, each transmitting with prob beta/N). For
        small beta*I/N this is ~ beta*I/N, the textbook mass-action term.
      - each I agent recovers (I -> R) with probability gamma.
      - S->I and I->R for a tick are both decided from the START-of-tick state and
        committed at the END of the tick (a newly-infected S does not also recover
        in the same tick; a freshly-recovered I does not infect after recovering).
  * Run until I = 0 (no more infectives). Outcome = final ATTACK RATE = 1 - S_final/N.

R0 = beta / gamma (the basic reproduction number). The classic threshold result: a
large outbreak occurs iff R0 > 1; for R0 < 1 the seed fades with negligible final
size. Conditional on take-off, the final size obeys the implicit relation
    ln(S0 / S_inf) = R0 * (1 - S_inf / N)        (S0 ~= N)
i.e. attack rate a = 1 - S_inf/N solves  a = 1 - exp(-R0 * a).

Built on the neutral platform (``abm_auto._platform``): each person is a
``PersonAgent`` whose two staged transitions are applied by the model under an
``AgentSet`` scheduler + a ``DataCollector`` (the S/I/R count series) — NOT a
hand-rolled god-loop. Given a seed the whole run is reproducible.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel, DataCollector

# State constants.
S, I, R = "S", "I", "R"


# -- Agent --------------------------------------------------------------------

class PersonAgent(Agent):
    """One person. ``state`` is S/I/R; ``_next_state`` is staged each tick and
    committed by the model after every agent has been evaluated (synchronous update,
    so the transition order is irrelevant and the run is deterministic given a seed).
    """

    def __init__(self, agent_id: int, model: "SIRModel", *, state: str = S) -> None:
        super().__init__(agent_id, model)
        self.state = state
        self._next_state = state

    def step(self) -> None:
        """Stage this agent's next state from the START-of-tick context held on the
        model (``model.p_infect`` for an S; ``model.gamma`` for an I). R is absorbing.
        """
        if self.state == S:
            # Force of infection: hazard of meeting >=1 of the I_count infectives,
            # each transmitting with per-contact prob beta/N (computed once per tick
            # on the model from the start-of-tick I_count).
            self._next_state = I if self.model.rng.random() < self.model.p_infect else S
        elif self.state == I:
            self._next_state = R if self.model.rng.random() < self.model.gamma else I
        else:  # R is absorbing
            self._next_state = R


# -- Model --------------------------------------------------------------------

class SIRModel(AgentModel):
    """Drives a well-mixed SIR epidemic to extinction of I.

    Construct with N, beta, gamma, the number of initial infecteds, and a seed.
    ``run`` iterates synchronous S->I->R updates until no infectives remain, then
    returns a summary dict (final attack rate + the S/I/R count series via the
    DataCollector).
    """

    def __init__(self, *, n: int = 10_000, beta: float, gamma: float = 0.1,
                 i0: int = 10, seed: int = 0, max_steps: Optional[int] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if not (0 < gamma <= 1):
            raise ValueError(f"gamma must be in (0, 1]; got {gamma}")
        if beta < 0:
            raise ValueError(f"beta must be >= 0; got {beta}")
        if not (0 < i0 < n):
            raise ValueError(f"i0 must be in (0, n); got i0={i0}, n={n}")
        self.n = n
        self.beta = beta
        self.gamma = gamma
        self.i0 = i0
        # generous extinction bound: well-mixed SIR ends fast, but guard anyway.
        self.max_steps = max_steps if max_steps is not None else 100_000

        # Per-tick context (recomputed each tick from start-of-tick I_count).
        self.p_infect = 0.0

        self.persons: List[PersonAgent] = []
        for k in range(n):
            person = PersonAgent(k, self, state=S)
            self.persons.append(person)
            self.add_agent(person)

        # Seed exactly i0 infecteds (the first i0 ids; the population is exchangeable
        # in a well-mixed model, so WHICH ids are seeded does not matter).
        for k in range(i0):
            self.persons[k].state = I
            self.persons[k]._next_state = I

        self.reporter = DataCollector({
            "S": lambda m: m.count(S),
            "I": lambda m: m.count(I),
            "R": lambda m: m.count(R),
        })

    # -- metrics --
    def count(self, state: str) -> int:
        return sum(1 for p in self.persons if p.state == state)

    def force_of_infection(self, i_count: int) -> float:
        """Per-S per-tick infection probability given ``i_count`` infectives:
        1 - (1 - beta/N)^i_count. beta/N is the per-contact transmission prob."""
        per_contact = self.beta / self.n
        # numerically safe for per_contact in [0, 1]
        return 1.0 - (1.0 - per_contact) ** i_count

    # -- tick --
    def step(self) -> None:
        """One synchronous SIR update: freeze the start-of-tick force of infection,
        let every agent stage its next state, then commit all states and record the
        new S/I/R counts."""
        i_count = self.count(I)
        self.p_infect = self.force_of_infection(i_count)
        self.agents.step()                       # each agent stages _next_state
        for p in self.persons:
            p.state = p._next_state
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate until no infectives remain; return the run summary."""
        self.reporter.collect(self)              # t=0 baseline (S0, I0=i0, R0=0)
        for _ in range(self.max_steps):
            if self.count(I) == 0:
                break
            self.step()
        s_final = self.count(S)
        r_final = self.count(R)
        attack_rate = 1.0 - s_final / self.n if self.n else 0.0
        return {
            "n": self.n,
            "beta": self.beta,
            "gamma": self.gamma,
            "R0": self.beta / self.gamma,
            "i0": self.i0,
            "S_final": s_final,
            "R_final": r_final,
            "attack_rate": attack_rate,
            "steps": self.t,
            "S_series": self.reporter.series("S"),
            "I_series": self.reporter.series("I"),
            "R_series": self.reporter.series("R"),
        }


# -- sweep helpers ------------------------------------------------------------

def beta_for_r0(r0: float, gamma: float) -> float:
    """beta = R0 * gamma (since R0 = beta / gamma)."""
    return r0 * gamma


def run_single(*, n: int = 10_000, r0: float, gamma: float = 0.1, i0: int = 10,
               seed: int = 0) -> Dict[str, Any]:
    """One SIR run at a target R0 (beta derived as R0*gamma)."""
    return SIRModel(n=n, beta=beta_for_r0(r0, gamma), gamma=gamma, i0=i0, seed=seed).run()


def run_many_seeds(*, n: int = 10_000, r0: float, gamma: float = 0.1, i0: int = 10,
                   n_seeds: int = 20, seed_base: int = 0,
                   takeoff_cutoff: float = 0.05) -> Dict[str, Any]:
    """Run ``n_seeds`` SIR epidemics at a target R0 and summarise.

    Each trial uses seed ``seed_base + i`` (deterministic ensemble). Returns the
    mean / min / max attack rate, the variance, the per-seed attack rates, and the
    take-off frequency + conditional-on-take-off mean (an outbreak "takes off" iff its
    attack rate >= ``takeoff_cutoff``; near R0=1 the outcome is bimodal — small
    fizzle vs large outbreak — so the conditional mean is the right comparison for
    the deterministic final-size relation).
    """
    attack_rates: List[float] = []
    for i in range(n_seeds):
        res = run_single(n=n, r0=r0, gamma=gamma, i0=i0, seed=seed_base + i)
        attack_rates.append(res["attack_rate"])
    mean = sum(attack_rates) / len(attack_rates)
    var = sum((a - mean) ** 2 for a in attack_rates) / len(attack_rates)
    took_off = [a for a in attack_rates if a >= takeoff_cutoff]
    return {
        "R0": r0,
        "n": n,
        "gamma": gamma,
        "i0": i0,
        "n_seeds": n_seeds,
        "beta": beta_for_r0(r0, gamma),
        "takeoff_cutoff": takeoff_cutoff,
        "attack_rates": attack_rates,
        "mean_attack_rate": mean,
        "var_attack_rate": var,
        "min_attack_rate": min(attack_rates),
        "max_attack_rate": max(attack_rates),
        "n_takeoff": len(took_off),
        "takeoff_frequency": len(took_off) / len(attack_rates),
        "mean_attack_rate_given_takeoff": (sum(took_off) / len(took_off)) if took_off else 0.0,
    }


def analytic_final_size(r0: float, *, tol: float = 1e-12, max_iter: int = 1000) -> float:
    """Solve the SIR final-size relation for the attack rate a (= 1 - S_inf/N), with
    S0 ~= N, by numerically solving  a = 1 - exp(-R0 * a)  via fixed-point / bisection.

    Equivalent to ln(S0/S_inf) = R0 (1 - S_inf/N) with S0 = N. For R0 <= 1 the only
    root in [0, 1] is a = 0 (no large outbreak); for R0 > 1 there is a unique positive
    root, found here by bisection on f(a) = 1 - exp(-R0*a) - a over (0, 1].
    """
    if r0 <= 1.0:
        return 0.0

    def f(a: float) -> float:
        return (1.0 - math.exp(-r0 * a)) - a

    # f(0)=0, f'(0)=R0-1>0 so f>0 just above 0; f(1)=1-exp(-R0)-1=-exp(-R0)<0.
    # The positive root is in (epsilon, 1).
    lo, hi = 1e-12, 1.0
    # ensure sign change on (lo, hi)
    if f(lo) <= 0:  # numerical underflow near 0; nudge lo up
        lo = 1e-6
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < tol:
            return mid
        # f decreasing past the root; f(lo)>0, f(hi)<0
        if fm > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
