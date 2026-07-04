"""Sugarscape (Epstein & Axtell 1996) — a faithful agent-based reproduction.

Source: Epstein, J.M. & Axtell, R. (1996) *Growing Artificial Societies: Social
Science from the Bottom Up*. Brookings Institution Press / MIT Press. Chapter II
(the "Animation I" / Sugarscape G1 + M + agent ruleset that produces an emergent
right-skewed wealth distribution).

Rules (verified against the book's "Sugarscape" specification):

  Environment (the "sugarscape"):
    * A 50x50 grid, TOROIDAL (wraps in both directions) — Epstein & Axtell's
      sugarscape wraps.
    * Each cell has a fixed sugar CAPACITY and a current sugar LEVEL <= capacity.
      The classic landscape has TWO sugar "mountains" (peaks) in opposite corners
      with capacities falling off radially in concentric terraces 0..4.
    * Regrow rule G_alpha: each occupied/empty cell regrows sugar toward its
      capacity by ``regrow`` per tick. We use the classic G1 (alpha = 1, i.e.
      +1 sugar/tick up to capacity). ``regrow=None`` gives G_infinity (instant
      regrow to capacity). The runner documents which is used.

  Agents (rule M, "agent movement"):
    Each ``SugarAgent`` carries fixed life parameters drawn once at birth:
        vision      v ~ U{1..6}    (how far it can see along the 4 axes)
        metabolism  m ~ U{1..4}    (sugar burned per tick)
        sugar       w ~ U{5..25}   (initial wealth; accumulates thereafter)
    Movement rule M (von-Neumann, the book's basic rule):
        1. Look only along the 4 cardinal directions (N/E/S/W) out to ``vision``
           cells (no diagonals); consider only UNOCCUPIED cells (plus the agent's
           own cell, which it may keep).
        2. Move to the nearest unoccupied site having the MAXIMUM sugar; ties in
           sugar are broken by NEAREST distance, then by a fixed direction order
           (a deterministic tie-break — the book breaks ties randomly, but a fixed
           order keeps a seeded run reproducible and does not change the aggregate
           outcome).
        3. Harvest ALL sugar at the destination cell (cell sugar -> 0).
        4. Subtract metabolism from the agent's sugar.
        5. If the agent's sugar < 0 it DIES and is removed from the grid.

  Outcome = the Gini coefficient of the living agents' wealth over time. From a
  near-uniform start the distribution becomes strongly right-skewed (a few rich,
  many poor) and the Gini rises to a high steady value — Epstein & Axtell's
  signature emergent-inequality result.

Built on the neutral platform (``abm_auto._platform``): each agent is a
``SugarAgent`` whose ``step`` applies rule M; the model owns the grid + regrow,
drives an ``AgentSet`` scheduler and a ``DataCollector`` (Gini + population
series) — NOT a hand-rolled god-loop. Given a seed the whole run is reproducible.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

Cell = Tuple[int, int]

# The 4 von-Neumann directions, in a FIXED order used as the final tie-break
# (N, E, S, W as (drow, dcol)). Movement looks out to ``vision`` along each.
_VN_DIRS: Tuple[Cell, ...] = ((-1, 0), (0, 1), (1, 0), (0, -1))


# -- landscape ----------------------------------------------------------------

def classic_two_peak_capacity(nrows: int = 50, ncols: int = 50,
                              peak: int = 4) -> List[List[int]]:
    """The classic Sugarscape capacity landscape: two sugar mountains in opposite
    corners, capacities in concentric terraces 0..``peak``.

    Two peaks are placed at ~(0.25, 0.25) and ~(0.75, 0.75) of the grid. A cell's
    capacity is ``peak`` minus a scaled distance to the NEAREST peak (clamped to
    [0, peak]), giving the familiar terraced double-mountain. Toroidal distance is
    used so the terraces are consistent with the wrapped movement space.
    """
    p1 = (round(0.25 * nrows), round(0.25 * ncols))
    p2 = (round(0.75 * nrows), round(0.75 * ncols))
    # radius over which capacity falls from `peak` to 0 (covers the half-grid)
    radius = max(nrows, ncols) * 0.30
    cap = [[0] * ncols for _ in range(nrows)]
    for r in range(nrows):
        for c in range(ncols):
            d = min(_toroidal_dist((r, c), p1, nrows, ncols),
                    _toroidal_dist((r, c), p2, nrows, ncols))
            level = peak - int(d / (radius / peak))
            cap[r][c] = max(0, min(peak, level))
    return cap


def _toroidal_dist(a: Cell, b: Cell, nrows: int, ncols: int) -> float:
    """Euclidean distance on a torus (shortest wrap in each axis)."""
    dr = abs(a[0] - b[0])
    dr = min(dr, nrows - dr)
    dc = abs(a[1] - b[1])
    dc = min(dc, ncols - dc)
    return (dr * dr + dc * dc) ** 0.5


# -- Gini ---------------------------------------------------------------------

def gini(values: Sequence[float]) -> float:
    """Gini coefficient of a non-negative wealth list (0 = equal, ->1 = unequal).

    Standard mean-absolute-difference form:
        G = sum_i sum_j |x_i - x_j| / (2 n^2 mean).
    Computed in O(n log n) via the sorted-cumulative identity. Empty or all-zero
    input -> 0.0 (no inequality is defined).
    """
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0:
        return 0.0
    total = sum(xs)
    if total <= 0.0:
        return 0.0
    cum = 0.0
    # G = (2 * sum_i (i+1) x_i) / (n * sum x) - (n + 1) / n   (1-indexed)
    for i, x in enumerate(xs):
        cum += (i + 1) * x
    return (2.0 * cum) / (n * total) - (n + 1.0) / n


def top_decile_share(values: Sequence[float]) -> float:
    """Share of total wealth held by the richest 10% of agents.

    Uses ceil(0.1 n) agents (at least 1 when there are agents). Empty / all-zero
    -> 0.0.
    """
    xs = sorted((float(v) for v in values), reverse=True)
    n = len(xs)
    if n == 0:
        return 0.0
    total = sum(xs)
    if total <= 0.0:
        return 0.0
    k = max(1, -(-n // 10))  # ceil(n/10)
    return sum(xs[:k]) / total


def median(values: Sequence[float]) -> float:
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2:
        return xs[mid]
    return (xs[mid - 1] + xs[mid]) / 2.0


# -- Agent --------------------------------------------------------------------

class SugarAgent(Agent):
    """One Sugarscape agent. Fixed life params (vision, metabolism) + accumulating
    ``sugar`` (wealth) + a grid ``cell`` (row, col). ``alive`` flags removal."""

    def __init__(self, agent_id: int, model: "SugarscapeModel", *, cell: Cell,
                 vision: int, metabolism: int, sugar: float) -> None:
        super().__init__(agent_id, model)
        self.cell = cell
        self.vision = vision
        self.metabolism = metabolism
        self.sugar = float(sugar)
        self.alive = True

    def visible_sites(self) -> List[Tuple[Cell, int, int, int]]:
        """All candidate destination sites = the agent's own cell plus every
        UNOCCUPIED cell within ``vision`` along the 4 cardinal directions.

        Returns (cell, sugar_there, distance, dir_index) tuples. The own cell is
        distance 0; ``dir_index`` is the index into ``_VN_DIRS`` (own cell -> -1)
        used only as the final, fixed tie-break.
        """
        model = self.model
        r, c = self.cell
        sites: List[Tuple[Cell, int, int, int]] = [
            (self.cell, model.sugar_at(self.cell), 0, -1)  # stay-put option
        ]
        for di, (dr, dc) in enumerate(_VN_DIRS):
            for dist in range(1, self.vision + 1):
                nr = (r + dr * dist) % model.nrows
                nc = (c + dc * dist) % model.ncols
                ncell = (nr, nc)
                if model.occupied(ncell):
                    continue  # cannot move onto an occupied cell
                sites.append((ncell, model.sugar_at(ncell), dist, di))
        return sites

    def best_site(self) -> Cell:
        """Rule M target: the site with the MOST sugar; ties -> nearest; further
        ties -> fixed direction order (deterministic)."""
        sites = self.visible_sites()
        # maximise sugar, then minimise distance, then minimise dir index.
        best = max(sites, key=lambda s: (s[1], -s[2], -s[3]))
        return best[0]

    def step(self) -> None:
        """Rule M then metabolism then death. The model owns the grid mutation so
        occupancy stays consistent within the tick."""
        if not self.alive:
            return
        target = self.best_site()
        self.model.move_agent(self, target)         # also harvests destination sugar
        self.sugar -= self.metabolism
        if self.sugar < 0:
            self.model.kill_agent(self)


# -- Model --------------------------------------------------------------------

class SugarscapeModel(AgentModel):
    """Drives the Sugarscape dynamics on a fixed toroidal grid.

    Construct with grid dims, the capacity landscape, a regrow rate, N agents, and
    the attribute ranges. ``run(n_steps)`` advances ``n_steps`` ticks (regrow ->
    agent moves/harvest/metabolism/death) and records the Gini + population series.
    """

    def __init__(self, *, nrows: int = 50, ncols: int = 50,
                 capacity: Optional[List[List[int]]] = None,
                 n_agents: int = 250, regrow: Optional[int] = 1,
                 vision_range: Tuple[int, int] = (1, 6),
                 metabolism_range: Tuple[int, int] = (1, 4),
                 sugar_range: Tuple[int, int] = (5, 25),
                 peak: int = 4, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="random_order")
        self.nrows = nrows
        self.ncols = ncols
        self.regrow = regrow                # None => G_infinity (instant to cap)
        self.peak = peak
        self.vision_range = vision_range
        self.metabolism_range = metabolism_range
        self.sugar_range = sugar_range

        self.capacity = (capacity if capacity is not None
                         else classic_two_peak_capacity(nrows, ncols, peak))
        # current sugar starts at full capacity (the standard initial sugarscape).
        self.sugar: List[List[int]] = [
            [self.capacity[r][c] for c in range(ncols)] for r in range(nrows)
        ]
        # grid[r][c] -> SugarAgent or None (occupancy).
        self.grid: List[List[Optional[SugarAgent]]] = [
            [None for _ in range(ncols)] for _ in range(nrows)
        ]

        # Place N agents on distinct random cells; draw attributes from the
        # locked uniform ranges (inclusive). Deterministic given the seed.
        all_cells: List[Cell] = [(r, c) for r in range(nrows) for c in range(ncols)]
        self.rng.shuffle(all_cells)
        n_agents = min(n_agents, len(all_cells))
        self.n_agents_initial = n_agents

        vlo, vhi = vision_range
        mlo, mhi = metabolism_range
        slo, shi = sugar_range
        self.agent_by_id: Dict[int, SugarAgent] = {}
        self.living: List[SugarAgent] = []
        for i in range(n_agents):
            cell = all_cells[i]
            agent = SugarAgent(
                i, self, cell=cell,
                vision=self.rng.randint(vlo, vhi),
                metabolism=self.rng.randint(mlo, mhi),
                sugar=self.rng.randint(slo, shi),
            )
            r, c = cell
            self.grid[r][c] = agent
            self.agent_by_id[i] = agent
            self.living.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "gini": lambda m: m.gini_wealth(),
            "population": lambda m: m.population(),
            "mean_wealth": lambda m: m.mean_wealth(),
            "median_wealth": lambda m: m.median_wealth(),
            "top_decile_share": lambda m: m.top_decile_share(),
        })

    # -- grid queries --
    def sugar_at(self, cell: Cell) -> int:
        return self.sugar[cell[0]][cell[1]]

    def occupied(self, cell: Cell) -> bool:
        return self.grid[cell[0]][cell[1]] is not None

    # -- metrics --
    def wealths(self) -> List[float]:
        return [a.sugar for a in self.living if a.alive]

    def population(self) -> int:
        return sum(1 for a in self.living if a.alive)

    def gini_wealth(self) -> float:
        return gini(self.wealths())

    def mean_wealth(self) -> float:
        ws = self.wealths()
        return sum(ws) / len(ws) if ws else 0.0

    def median_wealth(self) -> float:
        return median(self.wealths())

    def top_decile_share(self) -> float:
        return top_decile_share(self.wealths())

    # -- mutation --
    def move_agent(self, agent: SugarAgent, target: Cell) -> None:
        """Move ``agent`` to ``target`` (its chosen best site), harvesting all
        sugar there. A no-op move (target == current cell) still harvests."""
        old = agent.cell
        if target != old:
            self.grid[old[0]][old[1]] = None
            self.grid[target[0]][target[1]] = agent
            agent.cell = target
        # harvest: take all sugar at the (new) cell.
        agent.sugar += self.sugar[target[0]][target[1]]
        self.sugar[target[0]][target[1]] = 0

    def kill_agent(self, agent: SugarAgent) -> None:
        agent.alive = False
        r, c = agent.cell
        if self.grid[r][c] is agent:
            self.grid[r][c] = None

    def regrow_sugar(self) -> None:
        """Regrow rule G: each cell moves toward its capacity. G1 (regrow=1) adds
        +1/tick; G_infinity (regrow=None) snaps to capacity."""
        if self.regrow is None:
            for r in range(self.nrows):
                row_cap = self.capacity[r]
                self.sugar[r] = list(row_cap)
            return
        inc = self.regrow
        for r in range(self.nrows):
            srow = self.sugar[r]
            crow = self.capacity[r]
            for c in range(self.ncols):
                if srow[c] < crow[c]:
                    srow[c] = min(crow[c], srow[c] + inc)

    # -- tick --
    def step(self) -> None:
        """One Sugarscape tick: regrow the sugarscape, then every living agent
        applies rule M (move/harvest/metabolism/death) in scheduled order. Dead
        agents are pruned from the living list and the scheduler after the sweep."""
        self.regrow_sugar()
        # iterate over a snapshot of the living agents (deaths happen mid-sweep).
        for agent in self.agents.ordered():
            if agent.alive:
                agent.step()
        # prune the dead so the next tick's schedule + metrics see only the living.
        self.living = [a for a in self.living if a.alive]
        self.agents._agents = list(self.living)     # keep scheduler in sync
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_steps: int) -> Dict[str, Any]:  # type: ignore[override]
        """Advance ``n_steps`` ticks; return a summary dict (initial vs final Gini,
        distribution stats, and the per-tick series)."""
        self.reporter.collect(self)                  # t=0 baseline (uniform start)
        initial = self.reporter.records[0]
        for _ in range(n_steps):
            if self.population() == 0:
                break
            self.step()
        final = self.reporter.records[-1]
        return {
            "nrows": self.nrows,
            "ncols": self.ncols,
            "regrow": self.regrow,
            "peak": self.peak,
            "n_agents_initial": self.n_agents_initial,
            "vision_range": list(self.vision_range),
            "metabolism_range": list(self.metabolism_range),
            "sugar_range": list(self.sugar_range),
            "steps": self.t,
            "initial_gini": initial["gini"],
            "final_gini": final["gini"],
            "initial_population": initial["population"],
            "final_population": final["population"],
            "final_mean_wealth": final["mean_wealth"],
            "final_median_wealth": final["median_wealth"],
            "final_top_decile_share": final["top_decile_share"],
            "gini_series": self.reporter.series("gini"),
            "population_series": self.reporter.series("population"),
        }


# -- multi-seed helpers -------------------------------------------------------

def run_single(*, nrows: int = 50, ncols: int = 50, n_agents: int = 250,
               regrow: Optional[int] = 1, peak: int = 4,
               vision_range: Tuple[int, int] = (1, 6),
               metabolism_range: Tuple[int, int] = (1, 4),
               sugar_range: Tuple[int, int] = (5, 25),
               n_steps: int = 150, seed: int = 0) -> Dict[str, Any]:
    """One full Sugarscape run for a given seed."""
    model = SugarscapeModel(
        nrows=nrows, ncols=ncols, n_agents=n_agents, regrow=regrow, peak=peak,
        vision_range=vision_range, metabolism_range=metabolism_range,
        sugar_range=sugar_range, seed=seed,
    )
    res = model.run(n_steps)
    res["seed"] = seed
    return res


def _variance(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return sum((x - m) ** 2 for x in xs) / (n - 1)


def run_many_seeds(seeds: Sequence[int], *, nrows: int = 50, ncols: int = 50,
                   n_agents: int = 250, regrow: Optional[int] = 1, peak: int = 4,
                   vision_range: Tuple[int, int] = (1, 6),
                   metabolism_range: Tuple[int, int] = (1, 4),
                   sugar_range: Tuple[int, int] = (5, 25),
                   n_steps: int = 150) -> Dict[str, Any]:
    """Run one Sugarscape simulation per seed and summarise across seeds.

    Returns per-seed rows plus the cross-seed mean (and variance/range) of the
    initial and final Gini and the distribution stats — the headline numbers the
    locked clauses P1-P3 are evaluated against.
    """
    rows: List[Dict[str, Any]] = []
    for s in seeds:
        rows.append(run_single(
            nrows=nrows, ncols=ncols, n_agents=n_agents, regrow=regrow, peak=peak,
            vision_range=vision_range, metabolism_range=metabolism_range,
            sugar_range=sugar_range, n_steps=n_steps, seed=s,
        ))
    n = len(rows)
    init_ginis = [r["initial_gini"] for r in rows]
    final_ginis = [r["final_gini"] for r in rows]
    mean_w = [r["final_mean_wealth"] for r in rows]
    med_w = [r["final_median_wealth"] for r in rows]
    tds = [r["final_top_decile_share"] for r in rows]
    pops = [r["final_population"] for r in rows]
    return {
        "seeds": list(seeds),
        "nrows": nrows,
        "ncols": ncols,
        "n_agents": n_agents,
        "regrow": regrow,
        "peak": peak,
        "vision_range": list(vision_range),
        "metabolism_range": list(metabolism_range),
        "sugar_range": list(sugar_range),
        "n_steps": n_steps,
        "rows": rows,
        "mean_initial_gini": sum(init_ginis) / n if n else 0.0,
        "mean_final_gini": sum(final_ginis) / n if n else 0.0,
        "var_final_gini": _variance(final_ginis),
        "min_final_gini": min(final_ginis) if final_ginis else 0.0,
        "max_final_gini": max(final_ginis) if final_ginis else 0.0,
        "min_initial_gini": min(init_ginis) if init_ginis else 0.0,
        "max_initial_gini": max(init_ginis) if init_ginis else 0.0,
        "mean_final_mean_wealth": sum(mean_w) / n if n else 0.0,
        "mean_final_median_wealth": sum(med_w) / n if n else 0.0,
        "mean_final_top_decile_share": sum(tds) / n if n else 0.0,
        "mean_final_population": sum(pops) / n if n else 0.0,
    }
