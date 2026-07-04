"""Schelling (1971) segregation — a faithful agent-based reproduction.

Source: Schelling, T.C. (1971) "Dynamic Models of Segregation",
J. Math. Sociol. 1:143-186.

Rules (verified against the paper's "spatial proximity" model):
  * A square grid (e.g. 50x50). Some cells are EMPTY; the rest each hold one
    ``ResidentAgent`` of one of two equal-size types (0 / 1).
  * Each agent inspects its Moore-8 neighbourhood (the up-to-8 cells around it).
    It is UNHAPPY iff the fraction of its OCCUPIED neighbours that share its type
    is strictly below the tolerance ``f`` (default 1/3).
  * Documented convention: an agent with NO occupied neighbours counts as HAPPY
    (0 like-neighbours out of 0 is vacuously satisfied; it has no grievance and
    does not move). This matches Schelling's "content if isolated" handling.
  * Each step, every currently-unhappy agent relocates to a uniformly-random
    EMPTY cell. The grid runs to a (near-)stable state: a tick with no unhappy
    agents (or a max-step cap).
  * Outcome = the mean, over all agents, of each agent's same-type fraction
    among its occupied neighbours (the segregation index). An isolated agent
    contributes 0 to this index (it has no like-neighbours), so the index is a
    conservative lower bound on clustering.

Built on the neutral platform (``abm_auto._platform``): each resident is a
``ResidentAgent`` whose ``step`` decides happiness and (if unhappy) requests a
move; the model holds the grid, drives an ``AgentSet`` scheduler and a
``DataCollector`` (the mean same-type fraction + unhappy-count series) -- NOT a
hand-rolled god-loop. Given a seed the whole run is reproducible.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

Cell = Tuple[int, int]

# The 8 Moore-neighbourhood offsets (no wrap-around; the grid has hard edges,
# so corner/edge cells simply have fewer neighbours).
_MOORE_OFFSETS: Tuple[Cell, ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)


# -- Agent --------------------------------------------------------------------

class ResidentAgent(Agent):
    """One resident. Knows its ``cell`` (row, col) and its ``type`` (0 or 1)."""

    def __init__(self, agent_id: int, model: "SchellingModel", *,
                 cell: Cell, type_: int) -> None:
        super().__init__(agent_id, model)
        self.cell = cell
        self.type = type_

    def occupied_neighbors(self) -> List["ResidentAgent"]:
        """The agents occupying this agent's Moore-8 neighbour cells."""
        grid = self.model.grid
        r, c = self.cell
        out: List["ResidentAgent"] = []
        nrows, ncols = self.model.nrows, self.model.ncols
        for dr, dc in _MOORE_OFFSETS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < nrows and 0 <= nc < ncols:
                occ = grid[nr][nc]
                if occ is not None:
                    out.append(occ)
        return out

    def same_type_fraction(self) -> float:
        """Fraction of OCCUPIED neighbours that share this agent's type.

        An agent with no occupied neighbours returns 0.0 here (it has no
        like-neighbours), but is reported HAPPY by ``is_happy`` -- see the
        documented isolated-agent convention."""
        nbrs = self.occupied_neighbors()
        if not nbrs:
            return 0.0
        same = sum(1 for a in nbrs if a.type == self.type)
        return same / len(nbrs)

    def is_happy(self) -> bool:
        """Unhappy iff same_type_fraction < f among OCCUPIED neighbours.

        Convention: an agent with no occupied neighbours is HAPPY (vacuously
        satisfied; it has no grievance and will not move)."""
        nbrs = self.occupied_neighbors()
        if not nbrs:
            return True
        return self.same_type_fraction() >= self.model.f

    def step(self) -> None:
        """If unhappy, request a relocation to a random empty cell (the model
        performs the move so the grid stays consistent within the tick)."""
        if not self.is_happy():
            self.model.relocate(self)


# -- Model --------------------------------------------------------------------

class SchellingModel(AgentModel):
    """Drives the Schelling segregation dynamics on a fixed grid.

    Construct with grid dimensions, a vacancy fraction, and a tolerance ``f``.
    ``run`` iterates until no agent is unhappy (or ``max_steps``), then returns a
    summary dict (initial vs final segregation index + the per-tick series).
    """

    def __init__(self, *, nrows: int = 50, ncols: int = 50, vacancy: float = 0.28,
                 f: float = 1.0 / 3.0, seed: int = 0, max_steps: int = 200) -> None:
        super().__init__(seed=seed, schedule="random_order")
        self.nrows = nrows
        self.ncols = ncols
        self.f = f
        self.max_steps = max_steps

        n_cells = nrows * ncols
        n_empty = int(round(vacancy * n_cells))
        n_occupied = n_cells - n_empty
        # Two equal-size types; if odd, type 0 gets the extra agent.
        n_type1 = n_occupied // 2
        n_type0 = n_occupied - n_type1

        # Grid: grid[r][c] is a ResidentAgent or None (empty).
        self.grid: List[List[Optional[ResidentAgent]]] = [
            [None for _ in range(ncols)] for _ in range(nrows)
        ]
        # Empty-cell set for O(1)-ish random relocation target sampling.
        self.empty_cells: set[Cell] = set()

        all_cells: List[Cell] = [(r, c) for r in range(nrows) for c in range(ncols)]
        self.rng.shuffle(all_cells)

        types = [0] * n_type0 + [1] * n_type1
        # Place occupied cells first (already shuffled), assign type labels in a
        # fixed order over the shuffled cells -> deterministic given the seed.
        occupied_cells = all_cells[:n_occupied]
        empty = all_cells[n_occupied:]
        for cell in empty:
            self.empty_cells.add(cell)

        self.agent_by_id: Dict[int, ResidentAgent] = {}
        for i, (cell, t) in enumerate(zip(occupied_cells, types)):
            agent = ResidentAgent(i, self, cell=cell, type_=t)
            r, c = cell
            self.grid[r][c] = agent
            self.agent_by_id[i] = agent
            self.add_agent(agent)

        self.n_occupied = n_occupied
        self.n_empty = n_empty
        self.n_type0 = n_type0
        self.n_type1 = n_type1

        self._unhappy_this_tick = 0
        self.reporter = DataCollector({
            "mean_same_fraction": lambda m: m.mean_same_fraction(),
            "unhappy": lambda m: m.unhappy_count(),
        })

    # -- metrics --
    def mean_same_fraction(self) -> float:
        """Mean over all agents of each agent's same-type fraction among its
        occupied neighbours (the segregation index). Isolated agents contribute
        0 (no like-neighbours), making this a conservative clustering measure."""
        if not self.agent_by_id:
            return 0.0
        total = sum(a.same_type_fraction() for a in self.agent_by_id.values())
        return total / len(self.agent_by_id)

    def unhappy_count(self) -> int:
        return sum(1 for a in self.agent_by_id.values() if not a.is_happy())

    # -- moves --
    def relocate(self, agent: ResidentAgent) -> None:
        """Move ``agent`` to a uniformly-random empty cell (no-op if the grid is
        full). Keeps ``grid`` and ``empty_cells`` consistent."""
        if not self.empty_cells:
            return
        # Deterministic random choice over a sorted snapshot (set order is not
        # reproducible across runs; sorting + seeded RNG makes it so).
        targets = sorted(self.empty_cells)
        target = targets[self.rng.randrange(len(targets))]
        old = agent.cell
        r, c = old
        self.grid[r][c] = None
        self.empty_cells.add(old)
        nr, nc = target
        self.grid[nr][nc] = agent
        self.empty_cells.discard(target)
        agent.cell = target

    # -- tick --
    def step(self) -> None:
        """One sweep: each unhappy agent relocates (in scheduled order). Moves
        are applied immediately, so later agents in the same tick see the updated
        grid (sequential relocation -- the standard Schelling sweep)."""
        before = self.unhappy_count()
        self.agents.step()
        self._unhappy_this_tick = before
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate until no agent is unhappy (or ``max_steps``); return summary."""
        self.reporter.collect(self)              # t=0 baseline (random placement)
        initial = self.reporter.records[0]["mean_same_fraction"]
        for _ in range(self.max_steps):
            if self.unhappy_count() == 0:
                break
            self.step()
        final = self.mean_same_fraction()
        return {
            "nrows": self.nrows,
            "ncols": self.ncols,
            "f": self.f,
            "n_occupied": self.n_occupied,
            "n_empty": self.n_empty,
            "n_type0": self.n_type0,
            "n_type1": self.n_type1,
            "steps": self.t,
            "initial_segregation": initial,
            "final_segregation": final,
            "final_unhappy": self.unhappy_count(),
            "same_fraction_series": self.reporter.series("mean_same_fraction"),
            "unhappy_series": self.reporter.series("unhappy"),
        }


# -- multi-seed helpers -------------------------------------------------------

def run_single(*, nrows: int = 50, ncols: int = 50, vacancy: float = 0.28,
               f: float = 1.0 / 3.0, seed: int = 0, max_steps: int = 200) -> Dict[str, Any]:
    """One full Schelling run to (near-)stability for a given seed."""
    model = SchellingModel(nrows=nrows, ncols=ncols, vacancy=vacancy, f=f,
                           seed=seed, max_steps=max_steps)
    res = model.run()
    res["seed"] = seed
    return res


def run_many_seeds(seeds: List[int], *, nrows: int = 50, ncols: int = 50,
                   vacancy: float = 0.28, f: float = 1.0 / 3.0,
                   max_steps: int = 200) -> Dict[str, Any]:
    """Run one Schelling simulation per seed and summarise across seeds.

    Returns per-seed rows plus the cross-seed mean initial / final segregation
    index (the headline numbers the locked clauses are evaluated against).
    """
    rows: List[Dict[str, Any]] = []
    for s in seeds:
        rows.append(run_single(nrows=nrows, ncols=ncols, vacancy=vacancy, f=f,
                               seed=s, max_steps=max_steps))
    n = len(rows)
    mean_initial = sum(r["initial_segregation"] for r in rows) / n if n else 0.0
    mean_final = sum(r["final_segregation"] for r in rows) / n if n else 0.0
    return {
        "seeds": list(seeds),
        "nrows": nrows,
        "ncols": ncols,
        "vacancy": vacancy,
        "f": f,
        "max_steps": max_steps,
        "rows": rows,
        "mean_initial_segregation": mean_initial,
        "mean_final_segregation": mean_final,
    }
