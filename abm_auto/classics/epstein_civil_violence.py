"""Epstein (2002) civil violence — a faithful agent-based reproduction (Model I).

Source: Epstein, J.M. (2002) "Modeling civil violence: An agent-based computational
approach", PNAS 99(suppl 3):7243-7250. doi:10.1073/pnas.092080199
(open: https://www.pnas.org/doi/10.1073/pnas.092080199).

Rules (verified against the paper's Model I — the "central authority" model):

  * A grid of cells (here 40x40). Two agent kinds live on it: ``CitizenAgent`` (the
    populace) and ``CopAgent``. At most one agent per cell.
  * Each citizen has a FIXED perceived hardship H ~ U[0,1] and a FIXED risk-aversion
    R ~ U[0,1]. Government legitimacy L is a GLOBAL scalar in [0,1].
      - Grievance:  G = H * (1 - L).
      - It surveys its VISION neighbourhood (a square of Moore/Chebyshev radius `vision`,
        the cell + everything within `vision` steps incl. diagonals), counting cops C
        and ACTIVE citizens A *including itself* in that neighbourhood.
      - Estimated arrest probability:  P = 1 - exp(-k * floor(C / A)),  k = 2.3 so that
        one cop in view of one active gives P = 1 - exp(-2.3) ≈ 0.90 (Epstein's value).
      - Net risk = R * P. The citizen goes ACTIVE iff  G - R * P > T  (threshold T=0.1),
        else QUIESCENT.
      - A JAILED citizen is removed from the grid for its remaining sentence (it neither
        rebels nor is counted as active/present); when the sentence expires it returns
        to an empty cell.
  * Each cop surveys its VISION neighbourhood; if any ACTIVE citizen is in view it
    ARRESTS one (uniformly at random): that citizen is jailed for J ~ U{1..Jmax} ticks.
  * MOVEMENT rule M: every (non-jailed) agent moves to a uniformly-random EMPTY cell
    within its vision each tick (a cop's vision and a citizen's vision may differ; here
    they share one `vision`). Epstein's tick order is: movement (M), then citizen state
    update, then cop enforcement; we follow that order.
  * Outcome = the fraction of citizens that are ACTIVE over time. Epstein's central
    finding is PUNCTUATED equilibrium: long calm spells broken by sudden rebellion
    bursts, with the regime governed by legitimacy L and cop density.

Built on the neutral platform (``abm_auto._platform``): each citizen/cop is an autonomous
``Agent`` and the model drives an ``AgentSet`` scheduler + ``DataCollector`` (the active
series) — NOT a hand-rolled god-loop. Given a seed, the whole run is reproducible.

Convention note (faithful to the paper): the local cop/active ratio uses C/A with A the
active count INCLUDING the deciding agent itself, so a lone would-be rebel with no cop in
view sees floor(0/1)=0 → P=0; with one cop in view it sees floor(1/1)=1 → P≈0.90. floor()
is Epstein's "(C/A) ratio" rounded down, which makes a single cop deter exactly one active.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

Cell = Tuple[int, int]

# Epstein's constants (FIXED — see PREDICTIONS-locked.md; not tuned).
K = 2.3          # arrest-probability steepness: one cop / one active -> P≈0.90
THRESHOLD = 0.1  # net-risk threshold T above which grievance tips into rebellion


def _vision_offsets(vision: int) -> Tuple[Cell, ...]:
    """All (dr, dc) offsets within Chebyshev (Moore) radius ``vision``, EXCLUDING the
    centre (0,0). Epstein's vision is a square neighbourhood of this radius."""
    out: List[Cell] = []
    for dr in range(-vision, vision + 1):
        for dc in range(-vision, vision + 1):
            if dr == 0 and dc == 0:
                continue
            out.append((dr, dc))
    return tuple(out)


# -- Agents -------------------------------------------------------------------

class CitizenAgent(Agent):
    """One member of the populace. Fixed (H, R); state is active/quiescent + jail term."""

    kind = "citizen"

    def __init__(self, agent_id: int, model: "CivilViolenceModel", *,
                 cell: Cell, hardship: float, risk_aversion: float) -> None:
        super().__init__(agent_id, model)
        self.cell = cell
        self.hardship = hardship
        self.risk_aversion = risk_aversion
        self.active = False
        self.jail_term = 0           # ticks remaining; >0 means jailed (off-grid)

    @property
    def jailed(self) -> bool:
        return self.jail_term > 0

    def grievance(self) -> float:
        """G = H * (1 - L) with L the model's global legitimacy."""
        return self.hardship * (1.0 - self.model.legitimacy)

    def arrest_probability(self) -> float:
        """P = 1 - exp(-k * floor(C / A)) over the vision neighbourhood, with C cops and
        A active citizens. The deciding citizen presumes ITSELF active (A counts self once),
        so A = 1 + (other active citizens in vision)."""
        cops, actives = self.model.count_cops_and_actives(self.cell, presumed_active=self)
        ratio = math.floor(cops / actives) if actives > 0 else 0
        return 1.0 - math.exp(-K * ratio)

    def net_risk(self) -> float:
        return self.risk_aversion * self.arrest_probability()

    def decide_activation(self) -> None:
        """Citizen state rule: ACTIVE iff (G - R*P) > T, else QUIESCENT. Jailed citizens
        do not decide (they are off-grid serving a sentence)."""
        if self.jailed:
            return
        self.active = (self.grievance() - self.net_risk()) > THRESHOLD


class CopAgent(Agent):
    """One enforcer. Stateless beyond its cell: each tick it arrests one visible active."""

    kind = "cop"

    def __init__(self, agent_id: int, model: "CivilViolenceModel", *, cell: Cell) -> None:
        super().__init__(agent_id, model)
        self.cell = cell

    def enforce(self) -> None:
        """Arrest a uniformly-random ACTIVE citizen within vision (if any), jailing it
        for J ~ U{1..Jmax}. The arrested citizen leaves the grid for its sentence."""
        self.model.cop_arrest(self)


# -- Model --------------------------------------------------------------------

class CivilViolenceModel(AgentModel):
    """Drives Epstein's Model I on a fixed grid.

    Per-tick order (Epstein): (1) every agent MOVES to a random empty cell in vision,
    (2) every citizen updates its active/quiescent state, (3) every cop arrests a visible
    active, (4) jail terms tick down (releasing finished prisoners to empty cells). The
    ``DataCollector`` records the active fraction each tick.
    """

    def __init__(self, *, nrows: int = 40, ncols: int = 40, vision: int = 7,
                 legitimacy: float = 0.5, cop_density: float = 0.04,
                 citizen_density: float = 0.70, max_jail_term: int = 30,
                 seed: int = 0, max_steps: int = 200) -> None:
        super().__init__(seed=seed, schedule="random_order")
        self.nrows = nrows
        self.ncols = ncols
        self.vision = vision
        self.legitimacy = legitimacy
        self.cop_density = cop_density
        self.citizen_density = citizen_density
        self.max_jail_term = max_jail_term
        self.max_steps = max_steps
        self._offsets = _vision_offsets(vision)

        n_cells = nrows * ncols
        n_cops = int(round(cop_density * n_cells))
        n_citizens = int(round(citizen_density * n_cells))
        if n_cops + n_citizens > n_cells:
            raise ValueError("cop_density + citizen_density exceeds grid capacity")

        # grid[r][c] -> the Agent occupying that cell, or None.
        self.grid: List[List[Optional[Agent]]] = [
            [None for _ in range(ncols)] for _ in range(nrows)
        ]
        self.empty_cells: set[Cell] = set()

        all_cells: List[Cell] = [(r, c) for r in range(nrows) for c in range(ncols)]
        self.rng.shuffle(all_cells)
        cop_cells = all_cells[:n_cops]
        citizen_cells = all_cells[n_cops:n_cops + n_citizens]
        for cell in all_cells[n_cops + n_citizens:]:
            self.empty_cells.add(cell)

        self.cops: List[CopAgent] = []
        self.citizens: List[CitizenAgent] = []
        aid = 0
        for cell in cop_cells:
            cop = CopAgent(aid, self, cell=cell)
            self._place(cop, cell)
            self.cops.append(cop)
            self.add_agent(cop)
            aid += 1
        for cell in citizen_cells:
            cit = CitizenAgent(aid, self, cell=cell,
                               hardship=self.rng.random(),
                               risk_aversion=self.rng.random())
            self._place(cit, cell)
            self.citizens.append(cit)
            self.add_agent(cit)
            aid += 1

        self.n_cops = n_cops
        self.n_citizens = n_citizens
        self.reporter = DataCollector({
            "active": lambda m: m.active_count(),
            "active_fraction": lambda m: m.active_fraction(),
            "jailed": lambda m: m.jailed_count(),
        })

    # -- grid helpers --
    def _place(self, agent: Agent, cell: Cell) -> None:
        r, c = cell
        self.grid[r][c] = agent
        self.empty_cells.discard(cell)
        agent.cell = cell

    def _vacate(self, cell: Cell) -> None:
        r, c = cell
        self.grid[r][c] = None
        self.empty_cells.add(cell)

    def _vision_cells(self, cell: Cell) -> List[Cell]:
        r, c = cell
        out: List[Cell] = []
        for dr, dc in self._offsets:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.nrows and 0 <= nc < self.ncols:
                out.append((nr, nc))
        return out

    # -- the C/A count a citizen needs --
    def count_cops_and_actives(self, cell: Cell, *,
                               presumed_active: Optional["CitizenAgent"] = None) -> Tuple[int, int]:
        """Count cops C and ACTIVE (non-jailed) citizens A in the vision of ``cell`` (the
        centre cell itself is part of the neighbourhood, plus the surrounding ring).

        If ``presumed_active`` is given (the deciding citizen), that agent is presumed
        active and counted EXACTLY once toward A regardless of its current ``active`` flag
        — and is not double-counted when its own cell is scanned. Epstein's rule: a
        would-be rebel includes itself in the local active tally when estimating risk."""
        cops = 0
        actives = 0
        # centre cell + ring
        for (nr, nc) in [cell] + self._vision_cells(cell):
            occ = self.grid[nr][nc]
            if occ is None:
                continue
            if occ is presumed_active:
                continue  # counted once below; never double-count the deciding agent
            if getattr(occ, "kind", None) == "cop":
                cops += 1
            elif getattr(occ, "kind", None) == "citizen" and occ.active and not occ.jailed:
                actives += 1
        if presumed_active is not None:
            actives += 1
        return cops, actives

    # -- movement (rule M) --
    def move_agent(self, agent: Agent) -> None:
        """Move ``agent`` to a uniformly-random EMPTY cell within its vision; stay put if
        no empty vision cell exists. Deterministic given the seeded RNG."""
        choices = [c for c in self._vision_cells(agent.cell) if self.grid[c[0]][c[1]] is None]
        if not choices:
            return
        target = choices[self.rng.randrange(len(choices))]
        self._vacate(agent.cell)
        self._place(agent, target)

    # -- enforcement --
    def cop_arrest(self, cop: CopAgent) -> None:
        """Cop arrests one uniformly-random ACTIVE citizen in vision (incl. centre)."""
        targets: List[CitizenAgent] = []
        for (nr, nc) in [cop.cell] + self._vision_cells(cop.cell):
            occ = self.grid[nr][nc]
            if getattr(occ, "kind", None) == "citizen" and occ.active and not occ.jailed:
                targets.append(occ)
        if not targets:
            return
        victim = targets[self.rng.randrange(len(targets))]
        victim.active = False
        victim.jail_term = self.rng.randint(1, self.max_jail_term)
        self._vacate(victim.cell)  # jailed citizen leaves the grid for its sentence

    # -- metrics --
    def present_citizens(self) -> List[CitizenAgent]:
        return [c for c in self.citizens if not c.jailed]

    def active_count(self) -> int:
        return sum(1 for c in self.citizens if c.active and not c.jailed)

    def active_fraction(self) -> float:
        """Active fraction over the WHOLE citizen population (active / total citizens),
        Epstein's reporting convention (jailed citizens count in the denominator as part
        of the populace)."""
        return self.active_count() / self.n_citizens if self.n_citizens else 0.0

    def jailed_count(self) -> int:
        return sum(1 for c in self.citizens if c.jailed)

    # -- tick --
    def step(self) -> None:  # type: ignore[override]
        """One Epstein tick: move all -> citizens decide -> cops enforce -> jail decrement."""
        # (1) movement (rule M) for every non-jailed agent, in scheduled order
        for agent in self.agents.ordered():
            if getattr(agent, "kind", None) == "citizen" and agent.jailed:
                continue
            self.move_agent(agent)
        # (2) citizen state update
        for c in self.citizens:
            c.decide_activation()
        # (3) cop enforcement
        for cop in self.cops:
            cop.enforce()
        # (4) jail terms tick down; release finished prisoners to an empty cell
        for c in self.citizens:
            if c.jailed:
                c.jail_term -= 1
                if c.jail_term == 0:
                    self._return_from_jail(c)
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def _return_from_jail(self, citizen: CitizenAgent) -> None:
        """Place a just-released citizen on a uniformly-random empty cell (quiescent)."""
        citizen.active = False
        if not self.empty_cells:
            return
        targets = sorted(self.empty_cells)
        target = targets[self.rng.randrange(len(targets))]
        self._place(citizen, target)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``max_steps`` ticks; return a summary with the active-fraction series."""
        self.reporter.collect(self)  # t=0 baseline (all quiescent at construction)
        for _ in range(self.max_steps):
            self.step()
        series = self.reporter.series("active_fraction")
        return {
            "nrows": self.nrows,
            "ncols": self.ncols,
            "vision": self.vision,
            "legitimacy": self.legitimacy,
            "cop_density": self.cop_density,
            "citizen_density": self.citizen_density,
            "max_jail_term": self.max_jail_term,
            "n_cops": self.n_cops,
            "n_citizens": self.n_citizens,
            "steps": self.t,
            "active_fraction_series": series,
            "active_count_series": self.reporter.series("active"),
            "jailed_series": self.reporter.series("jailed"),
            "mean_active_fraction": (sum(series) / len(series)) if series else 0.0,
            "peak_active_fraction": max(series) if series else 0.0,
        }


# -- summary statistics -------------------------------------------------------

def burstiness(series: List[float], *, eps: float = 1e-9) -> float:
    """Burstiness = peak active fraction / mean active fraction over a series.

    A flat (calm or saturated) series has burstiness ≈ 1; a punctuated series with rare
    large bursts has burstiness ≫ 1. Returns 0.0 if the mean is (near) zero (no activity
    at all -> burstiness is undefined; we report it as 0 rather than +inf so a totally
    calm regime cannot spuriously satisfy a high-burstiness clause)."""
    if not series:
        return 0.0
    mean = sum(series) / len(series)
    if mean <= eps:
        return 0.0
    return max(series) / mean


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


# -- multi-seed drivers -------------------------------------------------------

def run_single(*, nrows: int = 40, ncols: int = 40, vision: int = 7,
               legitimacy: float = 0.5, cop_density: float = 0.04,
               citizen_density: float = 0.70, max_jail_term: int = 30,
               seed: int = 0, max_steps: int = 200) -> Dict[str, Any]:
    """One full civil-violence run for a given seed."""
    model = CivilViolenceModel(
        nrows=nrows, ncols=ncols, vision=vision, legitimacy=legitimacy,
        cop_density=cop_density, citizen_density=citizen_density,
        max_jail_term=max_jail_term, seed=seed, max_steps=max_steps)
    res = model.run()
    res["seed"] = seed
    res["burstiness"] = burstiness(res["active_fraction_series"])
    return res


def run_many_seeds(seeds: List[int], *, nrows: int = 40, ncols: int = 40, vision: int = 7,
                   legitimacy: float = 0.5, cop_density: float = 0.04,
                   citizen_density: float = 0.70, max_jail_term: int = 30,
                   max_steps: int = 200, burn_in: int = 0) -> Dict[str, Any]:
    """Run one simulation per seed at a FIXED config and summarise across seeds.

    Per-seed scalars (mean / peak active fraction, burstiness) are computed over the
    post-``burn_in`` tail of each series (drop the first ``burn_in`` ticks so an initial
    transient does not bias the steady-state statistics — ``burn_in`` is FIXED, not tuned).
    Returns the per-seed rows plus cross-seed means and standard deviations.
    """
    rows: List[Dict[str, Any]] = []
    for s in seeds:
        r = run_single(nrows=nrows, ncols=ncols, vision=vision, legitimacy=legitimacy,
                       cop_density=cop_density, citizen_density=citizen_density,
                       max_jail_term=max_jail_term, seed=s, max_steps=max_steps)
        tail = r["active_fraction_series"][burn_in:]
        r["mean_active_tail"] = _mean(tail)
        r["peak_active_tail"] = max(tail) if tail else 0.0
        r["burstiness_tail"] = burstiness(tail)
        rows.append(r)

    means = [r["mean_active_tail"] for r in rows]
    peaks = [r["peak_active_tail"] for r in rows]
    bursts = [r["burstiness_tail"] for r in rows]
    return {
        "seeds": list(seeds),
        "config": {
            "nrows": nrows, "ncols": ncols, "vision": vision, "legitimacy": legitimacy,
            "cop_density": cop_density, "citizen_density": citizen_density,
            "max_jail_term": max_jail_term, "max_steps": max_steps, "burn_in": burn_in,
            "k": K, "threshold": THRESHOLD,
        },
        "rows": rows,
        "mean_active_fraction": _mean(means),
        "mean_active_fraction_sd": _stdev(means),
        "mean_peak_active_fraction": _mean(peaks),
        "mean_burstiness": _mean(bursts),
        "burstiness_sd": _stdev(bursts),
    }
