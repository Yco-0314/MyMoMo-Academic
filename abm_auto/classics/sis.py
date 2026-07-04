"""SIS endemic threshold — a faithful agent-based reproduction (well-mixed).

Source: Kermack, W.O. & McKendrick, A.G. (1927) "A contribution to the mathematical
theory of epidemics", Proc. R. Soc. Lond. A 115(772):700-721 (the mass-action
contact process). The SIS variant (no immunity — recovery returns to Susceptible)
and its endemic equilibrium are the standard textbook result, e.g. Anderson & May
(1991) "Infectious Diseases of Humans" and Hethcote (2000) "The Mathematics of
Infectious Diseases", SIAM Review 42(4):599-653.

Rules (faithful to the discrete-time, well-mixed / mass-action SIS):
  * N agents, each a ``PersonAgent`` in one of TWO states S / I (no R — there is no
    immunity; recovery returns an infective straight back to Susceptible).
  * Each tick (synchronous update):
      - I_count is read at the START of the tick.
      - each S agent becomes I with probability 1 - (1 - beta/N)^I_count
        (the discrete force of infection; the per-tick hazard of meeting at least one
        of the I_count infectives, each transmitting with prob beta/N). For small
        beta*I/N this is ~ beta*I/N, the textbook mass-action term.
      - each I agent recovers (I -> S) with probability gamma.
      - S->I and I->S for a tick are both decided from the START-of-tick state and
        committed at the END of the tick (a newly-infected S does not also recover in
        the same tick; a freshly-recovered I does not infect after recovering).
  * Run for a FIXED number of ticks (long enough to reach steady state). Outcome =
    ENDEMIC PREVALENCE = mean I/N over the last ``tail`` ticks.

R0 = beta / gamma (the basic reproduction number). The classic SIS threshold: the
disease persists at an endemic equilibrium iff R0 > 1; for R0 <= 1 it dies out. The
endemic prevalence is
    i* = 1 - 1/R0      (for R0 > 1; i* = 0 for R0 <= 1)
the unique stable fixed point of the SIS mean-field map.

Built on the neutral platform (``abm_auto._platform``): each person is a
``PersonAgent`` whose staged transition is applied by the model under an ``AgentSet``
scheduler + a ``DataCollector`` (the S/I count series) — NOT a hand-rolled god-loop.
Given a seed the whole run is reproducible.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel, DataCollector

# State constants (no R — SIS).
S, I = "S", "I"


# -- Agent --------------------------------------------------------------------

class PersonAgent(Agent):
    """One person. ``state`` is S/I; ``_next_state`` is staged each tick and committed
    by the model after every agent has been evaluated (synchronous update, so the
    transition order is irrelevant and the run is deterministic given a seed).
    """

    def __init__(self, agent_id: int, model: "SISModel", *, state: str = S) -> None:
        super().__init__(agent_id, model)
        self.state = state
        self._next_state = state

    def step(self) -> None:
        """Stage this agent's next state from the START-of-tick context held on the
        model (``model.p_infect`` for an S; ``model.gamma`` for an I). Recovery returns
        an infective to S (no immunity)."""
        if self.state == S:
            # Force of infection: hazard of meeting >=1 of the I_count infectives, each
            # transmitting with per-contact prob beta/N (computed once per tick on the
            # model from the start-of-tick I_count).
            self._next_state = I if self.model.rng.random() < self.model.p_infect else S
        else:  # I -> S with prob gamma (recovery; no immunity)
            self._next_state = S if self.model.rng.random() < self.model.gamma else I


# -- Model --------------------------------------------------------------------

class SISModel(AgentModel):
    """Drives a well-mixed SIS contact process for a fixed number of ticks.

    Construct with N, beta, gamma, the number of initial infecteds, the number of
    ticks, the late-window length used to measure prevalence, and a seed. ``run``
    iterates synchronous S<->I updates for ``ticks`` steps, then returns a summary
    dict (endemic prevalence = mean I/N over the last ``tail`` ticks, plus the S/I
    count series via the DataCollector).
    """

    def __init__(self, *, n: int = 10_000, beta: float, gamma: float = 0.1,
                 i0: int = 10, ticks: int = 500, tail: int = 50, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if not (0 < gamma <= 1):
            raise ValueError(f"gamma must be in (0, 1]; got {gamma}")
        if beta < 0:
            raise ValueError(f"beta must be >= 0; got {beta}")
        if not (0 < i0 < n):
            raise ValueError(f"i0 must be in (0, n); got i0={i0}, n={n}")
        if not (0 < tail <= ticks):
            raise ValueError(f"tail must be in (0, ticks]; got tail={tail}, ticks={ticks}")
        self.n = n
        self.beta = beta
        self.gamma = gamma
        self.i0 = i0
        self.ticks = ticks
        self.tail = tail

        # Per-tick context (recomputed each tick from start-of-tick I_count).
        self.p_infect = 0.0

        self.persons: List[PersonAgent] = []
        for k in range(n):
            person = PersonAgent(k, self, state=S)
            self.persons.append(person)
            self.add_agent(person)

        # Seed exactly i0 infecteds (the first i0 ids; the population is exchangeable in
        # a well-mixed model, so WHICH ids are seeded does not matter).
        for k in range(i0):
            self.persons[k].state = I
            self.persons[k]._next_state = I

        self.reporter = DataCollector({
            "S": lambda m: m.count(S),
            "I": lambda m: m.count(I),
        })

    # -- metrics --
    def count(self, state: str) -> int:
        return sum(1 for p in self.persons if p.state == state)

    def force_of_infection(self, i_count: int) -> float:
        """Per-S per-tick infection probability given ``i_count`` infectives:
        1 - (1 - beta/N)^i_count. beta/N is the per-contact transmission prob."""
        per_contact = self.beta / self.n
        return 1.0 - (1.0 - per_contact) ** i_count

    # -- tick --
    def step(self) -> None:
        """One synchronous SIS update: freeze the start-of-tick force of infection, let
        every agent stage its next state, then commit all states and record the new S/I
        counts."""
        i_count = self.count(I)
        self.p_infect = self.force_of_infection(i_count)
        self.agents.step()                       # each agent stages _next_state
        for p in self.persons:
            p.state = p._next_state
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate ``ticks`` synchronous updates; return the run summary with endemic
        prevalence = mean I/N over the last ``tail`` ticks. If I hits 0 it is absorbing
        (no reintroduction), so the run continues with prevalence pinned at 0 — the
        honest near-threshold stochastic die-out."""
        self.reporter.collect(self)              # t=0 baseline (S0, I0=i0)
        for _ in range(self.ticks):
            self.step()
        i_series = self.reporter.series("I")
        # Endemic prevalence = mean I/N over the last `tail` recorded ticks.
        tail_I = i_series[-self.tail:]
        prevalence = (sum(tail_I) / len(tail_I)) / self.n if tail_I else 0.0
        i_final = i_series[-1]
        return {
            "n": self.n,
            "beta": self.beta,
            "gamma": self.gamma,
            "R0": self.beta / self.gamma,
            "i0": self.i0,
            "ticks": self.ticks,
            "tail": self.tail,
            "prevalence": prevalence,
            "I_final": i_final,
            "extinct": i_final == 0,
            "S_series": self.reporter.series("S"),
            "I_series": i_series,
        }


# -- sweep helpers ------------------------------------------------------------

def beta_for_r0(r0: float, gamma: float) -> float:
    """beta = R0 * gamma (since R0 = beta / gamma)."""
    return r0 * gamma


def endemic_prevalence(r0: float) -> float:
    """The analytic SIS endemic equilibrium prevalence i* = 1 - 1/R0 (for R0 > 1;
    0 otherwise). This is the LOCKED formula evaluated at the LOCKED R0 (not fit)."""
    return 1.0 - 1.0 / r0 if r0 > 1.0 else 0.0


def run_single(*, n: int = 10_000, r0: float, gamma: float = 0.1, i0: int = 10,
               ticks: int = 500, tail: int = 50, seed: int = 0) -> Dict[str, Any]:
    """One SIS run at a target R0 (beta derived as R0*gamma)."""
    return SISModel(n=n, beta=beta_for_r0(r0, gamma), gamma=gamma, i0=i0,
                    ticks=ticks, tail=tail, seed=seed).run()


def run_many_seeds(*, n: int = 10_000, r0: float, gamma: float = 0.1, i0: int = 10,
                   ticks: int = 500, tail: int = 50, n_seeds: int = 20,
                   seed_base: int = 0) -> Dict[str, Any]:
    """Run ``n_seeds`` SIS processes at a target R0 and summarise the endemic prevalence.

    Each trial uses seed ``seed_base + i`` (deterministic ensemble). Returns the mean /
    min / max prevalence, the variance, the per-seed prevalences, and the extinction
    frequency (fraction of seeds whose infection died out before the late window) —
    near R0=1 the process is bimodal (stochastic die-out vs persistence), so the
    extinction frequency is reported honestly alongside the mean.
    """
    prevalences: List[float] = []
    extinct: List[bool] = []
    for i in range(n_seeds):
        res = run_single(n=n, r0=r0, gamma=gamma, i0=i0, ticks=ticks, tail=tail,
                         seed=seed_base + i)
        prevalences.append(res["prevalence"])
        extinct.append(res["extinct"])
    mean = sum(prevalences) / len(prevalences)
    var = sum((p - mean) ** 2 for p in prevalences) / len(prevalences)
    n_extinct = sum(1 for e in extinct if e)
    # Mean prevalence conditional on persistence (the comparison for i* when some seeds
    # stochastically die out near threshold).
    persisted = [p for p, e in zip(prevalences, extinct) if not e]
    return {
        "R0": r0,
        "n": n,
        "gamma": gamma,
        "i0": i0,
        "ticks": ticks,
        "tail": tail,
        "n_seeds": n_seeds,
        "beta": beta_for_r0(r0, gamma),
        "prevalences": prevalences,
        "mean_prevalence": mean,
        "var_prevalence": var,
        "std_prevalence": var ** 0.5,
        "min_prevalence": min(prevalences),
        "max_prevalence": max(prevalences),
        "n_extinct": n_extinct,
        "extinction_frequency": n_extinct / len(prevalences),
        "mean_prevalence_given_persist": (sum(persisted) / len(persisted)) if persisted else 0.0,
        "i_star": endemic_prevalence(r0),
    }
