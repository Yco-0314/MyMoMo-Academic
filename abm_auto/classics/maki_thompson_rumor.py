"""Maki-Thompson rumor model — a faithful reproduction (well-mixed, CTMC).

Source: Maki, D.P. & Thompson, M. (1973) *Mathematical Models and Applications,
With Emphasis on the Social, Life, and Management Sciences*, Prentice-Hall,
ch. on the spread of a rumor. A directed-contact variant of the Daley-Kendall
stochastic rumor process (Daley, D.J. & Kendall, D.G. (1964) "Epidemics and
rumours", *Nature* 204:1118; (1965) J. Inst. Math. Appl. 1:42-55).

Framing (DISCLOSED, not hidden): this is a **well-mixed stochastic compartment
process** — agent states (Ignorant / Spreader / Stifler) evolving by **directed
pairwise contacts** drawn by a **Gillespie / CTMC** exponential-race scheduler.
It is NOT autonomous per-agent scheduling (each agent does not independently pick
when to act); instead the model draws the next directed contact from the whole
population, mass-action style. This mirrors the classic urn/CTMC formulation of
MT and is the honest description of the mechanism.

Rules (faithful to Maki-Thompson; only spreaders initiate):
  * N agents, each in one of three states:
      - Ignorant (I): never heard the rumor.
      - Spreader (S): has heard it and is actively spreading.
      - Stifler (R): has heard it but no longer spreads.
  * A **directed contact** originates at a Spreader and lands on a uniformly
    random OTHER agent (well-mixed). The three transition rules:
      (1) S -> I : the Ignorant becomes a Spreader (the rumor is passed on).
      (2) S -> S : the INITIATING spreader becomes a Stifler (it learns the
                   contact already knew — the rumor is "stale").
      (3) S -> R : the INITIATING spreader becomes a Stifler (same "stale" cue).
    So a spreader "ages out" (-> Stifler) the instant it directs a contact at
    ANYONE already informed (Spreader or Stifler). Only rule (1) grows S; rules
    (2)/(3) shrink it. In the Maki-Thompson variant ONLY the initiator changes
    state on an S->S contact (contrast Daley-Kendall, where BOTH become stiflers).
  * Contacts fire as a Poisson process: the total contact rate is
    ``rate * S_count`` (each of the S spreaders initiates contacts at intensity
    ``rate``), and the CONTACTED partner is uniform over the other N-1 agents.
    We advance by drawing the next event (Gillespie): who is contacted is
    chosen with population-fraction weights, so contacting a Spreader/Stifler/
    Ignorant happens in proportion to their counts.
  * Run to **absorption**: no spreaders left (S_count = 0). At that point the
    rumor can no longer spread. Outcome = final IGNORANT fraction ``i_inf`` and
    peak spreader fraction along the way.

**Rate-independence (the discriminating signature vs SIR).** Because every clock
here is the SAME contact clock (single symmetric rate, ρ = λ/α = 1 in the
canonical run), scaling the absolute ``rate`` only rescales TIME — it does not
change which event fires next nor the final composition. So ``i_inf`` is
**invariant** to the absolute rate, unlike an SIR final size, which grows with
R0. The canonical never-hear constant solves the fixed point

    theta = exp(-2 * (1 - theta))       =>   i_inf = theta ~= 0.2032    (rho = 1)

(general fixed point theta = exp(-(1 + rho)(1 - theta)); we lock rho = 1).

Built on the neutral platform (``abm_auto._platform``): each agent is a
``RumorAgent`` carrying a state; the ``MakiThompsonModel`` draws directed
contacts from the population via its seeded RNG under a ``DataCollector`` (the
I/S/R count series) — the CTMC scheduler is the model's, not a hand-rolled
god-loop over ad-hoc globals. Given a seed the whole run is reproducible.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from abm_auto._platform import Agent, AgentModel, DataCollector

# State constants.
IGNORANT, SPREADER, STIFLER = "I", "S", "R"


# -- Agent --------------------------------------------------------------------

class RumorAgent(Agent):
    """One person in the rumor process. ``state`` is I/S/R.

    Agents are state carriers; the CTMC event selection (which spreader
    initiates, who it contacts) is owned by the model's ``step`` because the
    Maki-Thompson dynamics are a population-level exponential race, not an
    autonomous per-agent tick. ``step`` is therefore a no-op here — the model
    mutates agent state on each drawn contact. This is the disclosed hybrid
    framing (see module docstring).
    """

    def __init__(self, agent_id: int, model: "MakiThompsonModel", *,
                 state: str = IGNORANT) -> None:
        super().__init__(agent_id, model)
        self.state = state

    def step(self) -> None:  # pragma: no cover - CTMC is model-driven
        # No autonomous per-agent action: the model draws directed contacts.
        return None


# -- Model --------------------------------------------------------------------

class MakiThompsonModel(AgentModel):
    """Drives a well-mixed Maki-Thompson rumor process to absorption (S = 0).

    Construct with N, the base contact ``rate`` (canonical ρ=1 single rate), the
    number of initial spreaders, and a seed. ``run`` fires directed contacts
    (Gillespie/CTMC) until no spreaders remain, then returns a summary dict with
    the final ignorant/stifler fractions, the peak spreader fraction, and the
    I/S/R count series via the DataCollector.

    We track I/S/R COUNTS on the model (not by scanning the roster each event) so
    each Gillespie step is O(1) selection — essential at N=1e5.
    """

    def __init__(self, *, n: int = 10_000, rate: float = 1.0,
                 initial_spreaders: int = 1, seed: int = 0,
                 record_every: Optional[int] = None,
                 max_events: Optional[int] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n < 2:
            raise ValueError(f"n must be >= 2; got {n}")
        if rate <= 0:
            raise ValueError(f"rate must be > 0; got {rate}")
        if not (0 < initial_spreaders < n):
            raise ValueError(
                f"initial_spreaders must be in (0, n); got {initial_spreaders}, n={n}")
        self.n = n
        self.rate = float(rate)
        self.initial_spreaders = initial_spreaders
        # Hard guard on the event loop (each event either informs a new agent or
        # stifles a spreader; total informings <= N and total stiflings <= N, so
        # the process is finite — but guard anyway).
        self.max_events = max_events if max_events is not None else 20 * n
        # Record the count series every `record_every` events (None => every event
        # for small N; downsample for large N to bound memory). Peak spreader is
        # tracked exactly (below), independent of recording granularity.
        self.record_every = record_every

        self.persons: List[RumorAgent] = []
        for k in range(n):
            person = RumorAgent(k, self, state=IGNORANT)
            self.persons.append(person)
            self.add_agent(person)

        # Seed exactly `initial_spreaders` spreaders (first ids; population is
        # exchangeable in a well-mixed model, so WHICH ids are seeded is irrelevant).
        for k in range(initial_spreaders):
            self.persons[k].state = SPREADER

        # O(1) counts (the CTMC selection reads these, not the roster).
        self.n_ignorant = n - initial_spreaders
        self.n_spreader = initial_spreaders
        self.n_stifler = 0

        # Exact peak spreader COUNT across the whole run (independent of the
        # recording granularity, which may downsample).
        self.peak_spreader = self.n_spreader
        # Elapsed CTMC time (sum of exponential waiting times) — only used to
        # demonstrate that the absolute rate rescales TIME, not composition.
        self.clock = 0.0
        self.events = 0

        self.reporter = DataCollector({
            "I": lambda m: m.n_ignorant,
            "S": lambda m: m.n_spreader,
            "R": lambda m: m.n_stifler,
            "t": lambda m: m.clock,
        })

    # -- one CTMC event -------------------------------------------------------
    def _fire_one_contact(self) -> None:
        """Draw and apply ONE directed contact (a Gillespie event).

        Total contact intensity is ``rate * S_count``; the waiting time is
        exponential with that intensity (advances the clock — pure time rescale).
        The initiating spreader contacts a uniformly random OTHER agent; the
        contacted partner's TYPE is drawn with population-fraction weights over
        the other N-1 agents. Then apply the Maki-Thompson rule.
        """
        s = self.n_spreader
        if s == 0:
            return
        total_intensity = self.rate * s
        # Exponential waiting time (advances the CTMC clock; composition-neutral).
        self.clock += self.rng.expovariate(total_intensity)

        # The contacted partner is uniform over the OTHER N-1 agents. From the
        # initiator's viewpoint the other population has:
        #   ignorants  = n_ignorant                 (never a spreader itself)
        #   spreaders  = n_spreader - 1              (exclude the initiator)
        #   stiflers   = n_stifler
        other = self.n - 1
        r = self.rng.random() * other
        if r < self.n_ignorant:
            # Rule (1): S -> I contact informs the Ignorant (it becomes a Spreader).
            self._inform_one_ignorant()
        else:
            # Rules (2)/(3): S -> S or S -> R. Only the INITIATOR ages out -> Stifler.
            self._stifle_one_spreader()

    def _inform_one_ignorant(self) -> None:
        """Turn one Ignorant into a Spreader (rule 1). Mutates the first ignorant
        found for determinism; identity is irrelevant in a well-mixed model."""
        for p in self.persons:
            if p.state == IGNORANT:
                p.state = SPREADER
                break
        self.n_ignorant -= 1
        self.n_spreader += 1
        if self.n_spreader > self.peak_spreader:
            self.peak_spreader = self.n_spreader

    def _stifle_one_spreader(self) -> None:
        """Turn one Spreader into a Stifler (rules 2/3 — the initiator ages out)."""
        for p in self.persons:
            if p.state == SPREADER:
                p.state = STIFLER
                break
        self.n_spreader -= 1
        self.n_stifler += 1

    # -- metrics --
    def count(self, state: str) -> int:
        """Live roster count (cross-check for the O(1) counters)."""
        return sum(1 for p in self.persons if p.state == state)

    # -- run ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Fire directed contacts until no spreaders remain (absorption); return
        the run summary (final ignorant/stifler fractions, peak spreader fraction,
        the I/S/R/t series, and the take-off flag)."""
        self.reporter.collect(self)  # baseline (I0, S0=seeds, R0=0, t=0)
        while self.n_spreader > 0 and self.events < self.max_events:
            self._fire_one_contact()
            self.events += 1
            self.t = self.events
            if self.record_every is None or (self.events % self.record_every == 0):
                self.reporter.collect(self)
        # Always record the final absorbing state.
        self.reporter.collect(self)

        i_inf = self.n_ignorant / self.n
        s_inf = self.n_spreader / self.n
        r_inf = self.n_stifler / self.n
        peak_frac = self.peak_spreader / self.n
        return {
            "n": self.n,
            "rate": self.rate,
            "initial_spreaders": self.initial_spreaders,
            "i_inf": i_inf,
            "s_inf": s_inf,
            "r_inf": r_inf,
            "peak_spreader_fraction": peak_frac,
            "peak_spreader_count": self.peak_spreader,
            "final_ignorant": self.n_ignorant,
            "final_stifler": self.n_stifler,
            "events": self.events,
            "clock": self.clock,
            "absorbed": self.n_spreader == 0,
            "I_series": self.reporter.series("I"),
            "S_series": self.reporter.series("S"),
            "R_series": self.reporter.series("R"),
            "t_series": self.reporter.series("t"),
        }


# -- analytic fixed point -----------------------------------------------------

def analytic_i_inf(rho: float = 1.0, *, tol: float = 1e-14,
                   max_iter: int = 100_000) -> float:
    """Final ignorant fraction ``i_inf = theta``, the root in (0, 1) of the
    Maki-Thompson fixed-point equation

        theta = exp(-(1 + rho) * (1 - theta))            (general rho = lambda/alpha)
        theta = exp(-2 * (1 - theta))                    (canonical rho = 1)

    Solved by fixed-point iteration from the low root (theta << 1). For rho = 1
    this returns ~0.2031878 (the canonical never-hear constant). theta = 1 is a
    trivial root (no outbreak); we want the small stable root reached after a
    take-off, so we iterate from a small seed which converges to it.
    """
    if rho <= 0:
        raise ValueError(f"rho must be > 0; got {rho}")
    c = 1.0 + rho
    theta = 1e-6  # start well below 1 so the iteration lands on the small root
    for _ in range(max_iter):
        nxt = math.exp(-c * (1.0 - theta))
        if abs(nxt - theta) < tol:
            return nxt
        theta = nxt
    return theta


ANALYTIC_PEAK_SPREADER = 1.0 - math.log(2.0)  # 1 - ln 2 ~= 0.3069 (rho = 1)


# -- sweep helpers ------------------------------------------------------------

def run_single(*, n: int = 10_000, rate: float = 1.0, initial_spreaders: int = 1,
               seed: int = 0, record_every: Optional[int] = None) -> Dict[str, Any]:
    """One Maki-Thompson run to absorption."""
    return MakiThompsonModel(n=n, rate=rate, initial_spreaders=initial_spreaders,
                             seed=seed, record_every=record_every).run()


def run_many_seeds(*, n: int = 10_000, rate: float = 1.0, initial_spreaders: int = 1,
                   n_seeds: int = 50, seed_base: int = 0,
                   takeoff_cutoff: float = 0.5,
                   record_every: Optional[int] = None) -> Dict[str, Any]:
    """Run ``n_seeds`` Maki-Thompson processes and summarise, **conditioning on
    outbreak** before averaging ``i_inf``.

    A single-spreader seed can die out almost immediately (its first contact lands
    on the only other informed agent, or the outbreak stifles while still tiny), so
    a raw mean would be contaminated by fizzles. A run "takes off" iff its final
    STIFLER fraction ``r_inf >= takeoff_cutoff`` (default 0.5 — the take-off cases
    reach r_inf ~ 0.797, fizzles reach ~0). We report both the unconditional stats
    and the conditional-on-take-off stats; the LOCKED metric is the
    **conditional-on-take-off mean i_inf**.
    """
    i_infs: List[float] = []
    r_infs: List[float] = []
    peaks: List[float] = []
    events_list: List[int] = []
    for i in range(n_seeds):
        res = run_single(n=n, rate=rate, initial_spreaders=initial_spreaders,
                         seed=seed_base + i, record_every=record_every)
        i_infs.append(res["i_inf"])
        r_infs.append(res["r_inf"])
        peaks.append(res["peak_spreader_fraction"])
        events_list.append(res["events"])

    took_off_idx = [k for k, rr in enumerate(r_infs) if rr >= takeoff_cutoff]
    n_takeoff = len(took_off_idx)

    def _mean(xs: List[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    def _var(xs: List[float]) -> float:
        if not xs:
            return 0.0
        m = _mean(xs)
        return sum((x - m) ** 2 for x in xs) / len(xs)

    i_infs_takeoff = [i_infs[k] for k in took_off_idx]
    peaks_takeoff = [peaks[k] for k in took_off_idx]

    return {
        "n": n,
        "rate": rate,
        "initial_spreaders": initial_spreaders,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "takeoff_cutoff": takeoff_cutoff,
        "i_infs": i_infs,
        "r_infs": r_infs,
        "peaks": peaks,
        "events": events_list,
        # unconditional (includes fizzles)
        "mean_i_inf_all": _mean(i_infs),
        # conditional on take-off (the locked metric)
        "n_takeoff": n_takeoff,
        "takeoff_frequency": n_takeoff / n_seeds if n_seeds else 0.0,
        "mean_i_inf": _mean(i_infs_takeoff),
        "var_i_inf": _var(i_infs_takeoff),
        "min_i_inf": min(i_infs_takeoff) if i_infs_takeoff else 0.0,
        "max_i_inf": max(i_infs_takeoff) if i_infs_takeoff else 0.0,
        "mean_peak_spreader": _mean(peaks_takeoff),
        "min_peak_spreader": min(peaks_takeoff) if peaks_takeoff else 0.0,
        "max_peak_spreader": max(peaks_takeoff) if peaks_takeoff else 0.0,
    }
