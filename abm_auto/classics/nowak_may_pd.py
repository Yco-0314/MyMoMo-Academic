"""Nowak & May (1992) spatial prisoner's dilemma — a faithful agent-based reproduction.

Source: Nowak, M.A. & May, R.M. (1992) "Evolutionary games and spatial chaos",
Nature 359:826-829.

Rules (verified against the paper):
  * Square lattice (default 99x99) with PERIODIC (toroidal) boundaries; every site
    holds one ``PDAgent`` that is a pure cooperator (C) or pure defector (D).
  * Payoff matrix in the Nowak-May rescaling: against EACH partner,
        T = b   (I defect, partner cooperates)   1 < b < 2
        R = 1   (both cooperate)
        P = 0   (both defect)
        S = 0   (I cooperate, partner defects)
    So a cooperator scores 1 per cooperating partner and 0 per defecting partner;
    a defector scores b per cooperating partner and 0 per defecting partner.
  * SELF-INTERACTION CONVENTION (Nowak & May): each agent plays the 8 Moore
    neighbours AND ITSELF. The self-game adds R=1 to a cooperator's score (and
    P=0 to a defector's). This is the canonical convention that produces the
    paper's persistent C-clusters / dynamic-fractal patterns; without it the
    cluster boundaries score differently and the canonical figures do not appear.
    It is implemented and documented here as a deliberate, fixed modelling choice
    (``self_interaction=True`` by default). The flag exists so a test can show the
    rule's sensitivity to it, NOT so it is tuned per run.
  * UPDATE RULE: synchronous. Every agent computes its total payoff (sum over the
    8 Moore neighbours + optionally itself). Then, simultaneously, every agent
    adopts the strategy of the highest-scoring agent among {itself + its 8 Moore
    neighbours} (it keeps its own strategy on a tie / if it is the local best).
  * Deterministic given the initial configuration: the dynamics have no RNG; only
    the random initial C/D placement uses the seed.

WELL-MIXED CONTROL (structure destroyed): same payoffs, same best-response
imitation, but each agent's "neighbourhood" is 8 OTHER agents drawn at random AND
RE-DRAWN every tick. Spatial correlation cannot build up, so cooperator clusters
cannot form and cooperation collapses to ~0 — the contrast that isolates spatial
structure as the cause.

Built on the neutral platform (``abm_auto._platform``): each site is a ``PDAgent``
whose ``step`` stages its next strategy from local scores; the model owns the
lattice, the synchronous commit, and a ``DataCollector`` (cooperator-fraction
series) — not a hand-rolled god-loop.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

COOPERATE = "C"
DEFECT = "D"


# -- Agent --------------------------------------------------------------------

class PDAgent(Agent):
    """One lattice site. ``strategy`` is 'C' or 'D'; ``payoff`` is the score it
    accumulated this tick; ``_next_strategy`` is staged during a tick and committed
    by the model so the whole update is synchronous (order-independent)."""

    def __init__(self, agent_id: int, model: "NowakMayModel", *, strategy: str) -> None:
        super().__init__(agent_id, model)
        self.strategy = strategy
        self.payoff = 0.0
        self._next_strategy = strategy

    # -- payoff --
    def compute_payoff(self) -> float:
        """Sum this agent's payoff over its game partners (Moore-8, plus itself if
        the self-interaction convention is on). A C scores R=1 per C partner and
        S=0 per D partner; a D scores T=b per C partner and P=0 per D partner."""
        model = self.model
        agents = model.agent_by_id
        partners = list(model.neighbors[self.id])
        if model.self_interaction:
            partners.append(self.id)
        score = 0.0
        if self.strategy == COOPERATE:
            for j in partners:
                if agents[j].strategy == COOPERATE:
                    score += model.R  # both cooperate
                # else S = 0
        else:  # DEFECT
            for j in partners:
                if agents[j].strategy == COOPERATE:
                    score += model.b  # T: defect vs cooperator
                # else P = 0
        return score

    # -- imitation: stage the next strategy --
    def choose_next_strategy(self) -> None:
        """Adopt the strategy of the highest-scoring agent among {self + Moore-8}.
        Ties keep the incumbent strategy (self is the default best)."""
        model = self.model
        agents = model.agent_by_id
        best_strategy = self.strategy
        best_score = self.payoff  # self is the default incumbent
        for j in model.neighbors[self.id]:
            nb = agents[j]
            if nb.payoff > best_score:
                best_score = nb.payoff
                best_strategy = nb.strategy
        self._next_strategy = best_strategy

    def step(self) -> None:
        """Per-agent stage used by the scheduler: stage the next strategy from the
        payoffs the model computed this tick. The model commits all next-strategies
        at once, so payoff computation never sees a half-updated lattice."""
        self.choose_next_strategy()


# -- Model --------------------------------------------------------------------

class NowakMayModel(AgentModel):
    """Spatial PD on a periodic square lattice with synchronous best-response
    imitation. Construct with a size, b, and an initial cooperator density; ``run``
    iterates ``n_steps`` synchronous ticks and records the cooperator fraction."""

    def __init__(self, width: int = 99, height: int = 99, *, b: float = 1.85,
                 init_coop_fraction: float = 0.5, self_interaction: bool = True,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.width = width
        self.height = height
        self.b = float(b)
        self.R = 1.0
        self.S = 0.0
        self.P = 0.0
        self.init_coop_fraction = init_coop_fraction
        self.self_interaction = self_interaction
        self.n = width * height

        # Moore-8 neighbourhood with periodic boundaries, keyed by site id = y*W+x.
        self.neighbors: Dict[int, List[int]] = self._build_moore_neighbors()

        # Random initial C/D placement (the ONLY use of the RNG).
        self.agent_by_id: Dict[int, PDAgent] = {}
        for site in range(self.n):
            strat = COOPERATE if self.rng.random() < init_coop_fraction else DEFECT
            agent = PDAgent(site, self, strategy=strat)
            self.agent_by_id[site] = agent
            self.add_agent(agent)

        self.reporter = DataCollector({"coop_fraction": lambda m: m.cooperator_fraction()})

    # -- lattice --
    def _build_moore_neighbors(self) -> Dict[int, List[int]]:
        W, H = self.width, self.height
        nbrs: Dict[int, List[int]] = {}
        for y in range(H):
            for x in range(W):
                site = y * W + x
                ids = []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx = (x + dx) % W
                        ny = (y + dy) % H
                        ids.append(ny * W + nx)
                nbrs[site] = ids
        return nbrs

    # -- metrics --
    def cooperator_count(self) -> int:
        return sum(1 for a in self.agent_by_id.values() if a.strategy == COOPERATE)

    def cooperator_fraction(self) -> float:
        return self.cooperator_count() / self.n if self.n else 0.0

    # -- tick --
    def step(self) -> None:
        """One synchronous tick: (1) every agent computes its payoff against the
        CURRENT lattice; (2) every agent stages its next strategy (best neighbour);
        (3) the model commits all strategies at once; (4) record + advance t."""
        agents = self.agent_by_id
        # 1) payoffs against the frozen current lattice
        for a in agents.values():
            a.payoff = a.compute_payoff()
        # 2) stage next strategies from those payoffs
        self.agents.step()
        # 3) synchronous commit
        for a in agents.values():
            a.strategy = a._next_strategy
        # 4) record
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_steps: int = 200) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate ``n_steps`` synchronous ticks; return a run summary including the
        full cooperator-fraction series (t=0 baseline + every tick)."""
        self.reporter.collect(self)  # t=0 baseline (initial random placement)
        for _ in range(n_steps):
            self.step()
        series = self.reporter.series("coop_fraction")
        return {
            "width": self.width,
            "height": self.height,
            "b": self.b,
            "n": self.n,
            "self_interaction": self.self_interaction,
            "init_coop_fraction": self.init_coop_fraction,
            "n_steps": n_steps,
            "coop_series": series,
            "final_coop_fraction": series[-1],
        }


# -- Well-mixed control -------------------------------------------------------

class WellMixedPDModel(AgentModel):
    """Mean-field control: same payoffs + same best-response imitation, but each
    agent's 8 "neighbours" are OTHER agents drawn uniformly at random and RE-DRAWN
    every tick. Destroying the fixed spatial structure removes the correlation that
    lets cooperator clusters survive, so cooperation should collapse to ~0.

    Re-uses ``PDAgent`` unchanged: only ``model.neighbors`` changes from tick to
    tick. NOTE (adversarial review 2026-06-29): the collapse DOES depend on the
    self_interaction choice — with self_interaction=False (the original default) the
    control settles ~0, but with a FAIR self_interaction=True (matching the spatial
    arm) it settles ~0.083. The fair control is the apples-to-apples one (isolates
    structure alone); the runner grades P2/P3 on it. Do NOT claim the collapse is
    self-interaction-independent."""

    def __init__(self, n: int = 9801, *, b: float = 1.85, k: int = 8,
                 init_coop_fraction: float = 0.5, self_interaction: bool = False,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.n = n
        self.b = float(b)
        self.R = 1.0
        self.S = 0.0
        self.P = 0.0
        self.k = k
        self.init_coop_fraction = init_coop_fraction
        self.self_interaction = self_interaction

        self.agent_by_id: Dict[int, PDAgent] = {}
        for site in range(self.n):
            strat = COOPERATE if self.rng.random() < init_coop_fraction else DEFECT
            agent = PDAgent(site, self, strategy=strat)
            self.agent_by_id[site] = agent
            self.add_agent(agent)

        # neighbours are (re)assigned every tick; start with one draw so payoff is
        # defined even before the first step.
        self.neighbors: Dict[int, List[int]] = {}
        self._redraw_neighbors()

        self.reporter = DataCollector({"coop_fraction": lambda m: m.cooperator_fraction()})

    def _redraw_neighbors(self) -> None:
        """Assign each agent k distinct random partners (excluding itself), fresh
        every tick — the structure-destroying step."""
        ids = range(self.n)
        rng = self.rng
        nbrs: Dict[int, List[int]] = {}
        for site in ids:
            chosen: List[int] = []
            seen = {site}
            # sample k distinct partners != self
            while len(chosen) < self.k:
                j = rng.randrange(self.n)
                if j in seen:
                    continue
                seen.add(j)
                chosen.append(j)
            nbrs[site] = chosen
        self.neighbors = nbrs

    # -- metrics --
    def cooperator_count(self) -> int:
        return sum(1 for a in self.agent_by_id.values() if a.strategy == COOPERATE)

    def cooperator_fraction(self) -> float:
        return self.cooperator_count() / self.n if self.n else 0.0

    # -- tick --
    def step(self) -> None:
        agents = self.agent_by_id
        self._redraw_neighbors()  # structure destroyed: fresh random partners
        for a in agents.values():
            a.payoff = a.compute_payoff()
        self.agents.step()
        for a in agents.values():
            a.strategy = a._next_strategy
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_steps: int = 200) -> Dict[str, Any]:  # type: ignore[override]
        self.reporter.collect(self)  # t=0 baseline
        for _ in range(n_steps):
            self.step()
        series = self.reporter.series("coop_fraction")
        return {
            "n": self.n,
            "b": self.b,
            "k": self.k,
            "self_interaction": self.self_interaction,
            "init_coop_fraction": self.init_coop_fraction,
            "n_steps": n_steps,
            "coop_series": series,
            "final_coop_fraction": series[-1],
        }


# -- sweep / summary helpers --------------------------------------------------

def steady_state_fraction(series: List[float], *, last: int = 50) -> float:
    """Mean cooperator fraction over the last ``last`` recorded ticks (the
    statistical steady state). Falls back to the whole series if it is shorter."""
    tail = series[-last:] if len(series) >= last else series
    return sum(tail) / len(tail) if tail else 0.0


def run_spatial_seeds(width: int = 99, height: int = 99, *, b: float = 1.85,
                      init_coop_fraction: float = 0.5, self_interaction: bool = True,
                      n_steps: int = 200, seeds: Tuple[int, ...] = (0, 1, 2, 3, 4),
                      last: int = 50) -> Dict[str, Any]:
    """Run the spatial lattice over several seeds; report per-seed steady-state
    cooperator fraction + the aggregate mean/min/max."""
    per_seed = []
    for s in seeds:
        res = NowakMayModel(width, height, b=b, init_coop_fraction=init_coop_fraction,
                            self_interaction=self_interaction, seed=s).run(n_steps)
        ss = steady_state_fraction(res["coop_series"], last=last)
        per_seed.append({"seed": s, "steady_state": ss,
                         "final": res["final_coop_fraction"],
                         "coop_series": res["coop_series"]})
    ss_vals = [r["steady_state"] for r in per_seed]
    return {
        "kind": "spatial",
        "width": width, "height": height, "b": b,
        "init_coop_fraction": init_coop_fraction,
        "self_interaction": self_interaction, "n_steps": n_steps,
        "seeds": list(seeds), "last": last,
        "per_seed": per_seed,
        "mean_steady_state": sum(ss_vals) / len(ss_vals),
        "min_steady_state": min(ss_vals),
        "max_steady_state": max(ss_vals),
    }


def run_wellmixed_seeds(n: int = 9801, *, b: float = 1.85, k: int = 8,
                        init_coop_fraction: float = 0.5, self_interaction: bool = False,
                        n_steps: int = 200,
                        seeds: Tuple[int, ...] = (0, 1, 2, 3, 4),
                        last: int = 50) -> Dict[str, Any]:
    """Run the well-mixed control over several seeds; report per-seed steady-state
    cooperator fraction + the aggregate mean/min/max.

    ``self_interaction`` controls FAIRNESS of the control vs the spatial arm: the
    spatial arm uses self_interaction=True, so a FAIR (apples-to-apples) control that
    isolates the effect of *structure alone* must also set self_interaction=True. The
    default False reproduces the (unfair, two-variable) mean-field control originally
    reported; the runner now grades P2/P3 on the FAIR control."""
    per_seed = []
    for s in seeds:
        res = WellMixedPDModel(n, b=b, k=k, init_coop_fraction=init_coop_fraction,
                               self_interaction=self_interaction, seed=s).run(n_steps)
        ss = steady_state_fraction(res["coop_series"], last=last)
        per_seed.append({"seed": s, "steady_state": ss,
                         "final": res["final_coop_fraction"],
                         "coop_series": res["coop_series"]})
    ss_vals = [r["steady_state"] for r in per_seed]
    return {
        "kind": "well_mixed",
        "n": n, "b": b, "k": k,
        "init_coop_fraction": init_coop_fraction, "n_steps": n_steps,
        "seeds": list(seeds), "last": last,
        "per_seed": per_seed,
        "mean_steady_state": sum(ss_vals) / len(ss_vals),
        "min_steady_state": min(ss_vals),
        "max_steady_state": max(ss_vals),
    }
