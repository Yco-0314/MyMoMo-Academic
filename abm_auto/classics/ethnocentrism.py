"""Hammond & Axelrod (2006) ethnocentrism — a faithful agent-based reproduction.

Source: Hammond, R.A. & Axelrod, R. (2006) "The Evolution of Ethnocentrism",
Journal of Conflict Resolution 50(6):926-936. doi:10.1177/0022002706293470
(open: https://www.rob-axelrod.com/files/Hammond-and-Axelrod-2006.pdf).

Rules (verified against the paper's canonical model):

  * An L x L grid (L=50) of sites, each EMPTY or holding one ``EthnoAgent``. At most
    one agent per site. Neighbourhood = the 4 von Neumann (N/E/S/W) neighbours.
  * Each agent has a TAG (one of 4 colours) and a STRATEGY = a pair of booleans
      (cooperate-with-SAME-tag?, cooperate-with-DIFFERENT-tag?).
    The 4 strategy/phenotypes are:
      - ethnocentric  = (C-in, D-out)  -> cooperate with own tag, defect on others
      - humanitarian  = (C-in, C-out)  -> cooperate with everyone  (a.k.a. altruist)
      - egoist/selfish= (D-in, D-out)  -> defect on everyone
      - traitorous    = (D-in, C-out)  -> defect on own tag, cooperate with others
  * The Hammond-Axelrod tick has FOUR stages, in this order:
      (1) IMMIGRATION — one new agent (random tag + random strategy) is placed on a
          uniformly-random EMPTY site (skipped if the grid is full).
      (2) INTERACTION — every agent plays a one-shot PD with EACH of its occupied
          von Neumann neighbours. The donation game: an agent that COOPERATES toward
          a neighbour pays cost c=0.01 and GIVES that neighbour benefit b=0.03; whether
          it cooperates depends on the agent's strategy and whether the neighbour shares
          its tag. Each agent starts the tick with the base PTR (potential-to-reproduce)
          0.12 and accumulates the net payoff (benefits received minus costs paid). PTR
          is clamped to [0, 1] (it is used as a probability in stage 3).
      (3) REPRODUCTION — in scheduled order, each agent reproduces with probability =
          its (clamped) PTR; if it succeeds AND it has at least one empty von Neumann
          neighbour, an offspring is placed on a uniformly-random empty neighbour. The
          offspring inherits the parent's tag and strategy, each of the THREE loci (tag,
          coop-in bit, coop-out bit) independently mutated with probability m=0.005 (a
          mutated tag becomes a uniformly-random one of the 4; a mutated bit flips).
      (4) DEATH — every agent dies with probability d=0.10, freeing its site.
  * Outcome = the population shares of the 4 strategies + the realized in-group and
    out-group cooperation rates, measured over the tail of a long (~2000-tick) run.

Built on the neutral platform (``abm_auto._platform``): every site occupant is a
state-carrying ``EthnoAgent`` on an ``AgentSet`` roster + a ``DataCollector`` (the
strategy-share series). NOTE (adversarial review 2026-06-30): the four Hammond-Axelrod
stages (immigrate/interact/reproduce/die) are orchestrated at the MODEL level (a staged
grid loop in ``step``), not driven by autonomous per-agent ``step``/``AgentSet.do`` calls —
so this is a model-orchestrated grid model, not a god-loop-free autonomous-agent scheduler.
The agents hold tag+strategy state; the per-stage logic is model-level. Given a seed the
whole run is reproducible.

Faithfulness note on the PD: Hammond & Axelrod use a one-shot donation/PD game where the
only act is the decision to help (pay c, give b) or not. There is no separate "received
defection" penalty — a defector simply withholds the gift. So an agent's net payoff for a
tick is (b * #neighbours-who-cooperated-toward-it) - (c * #neighbours-it-cooperated-with).
Cooperation is unconditional on the partner's choice (one-shot, simultaneous), exactly as
in the paper; this is what makes ethnocentrism (help own tag, exploit-by-withholding from
others) outcompete the alternatives in a viscous (spatially clustered) population.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

Cell = Tuple[int, int]

# Hammond-Axelrod canonical constants (FIXED — see PREDICTIONS-locked.md; NOT tuned).
N_TAGS = 4            # number of distinguishable tag colours
COST = 0.01          # c: cost paid to cooperate (give) toward a neighbour
BENEFIT = 0.03       # b: benefit a cooperated-with neighbour receives  (b/c = 3)
BASE_PTR = 0.12      # base potential-to-reproduce before payoff is added
MUTATION = 0.005     # per-locus mutation probability at reproduction (tag, in-bit, out-bit)
DEATH_RATE = 0.10    # per-agent death probability each tick

# Strategy = (coop_in, coop_out). Canonical phenotype names for the 4 combinations.
STRATEGIES: Tuple[Tuple[bool, bool], ...] = (
    (True, False),   # ethnocentric
    (True, True),    # humanitarian
    (False, False),  # egoist
    (False, True),   # traitorous
)


def strategy_name(coop_in: bool, coop_out: bool) -> str:
    """Map a (coop_in, coop_out) strategy to its canonical phenotype name."""
    if coop_in and not coop_out:
        return "ethnocentric"
    if coop_in and coop_out:
        return "humanitarian"
    if not coop_in and not coop_out:
        return "egoist"
    return "traitorous"


STRATEGY_NAMES = ("ethnocentric", "humanitarian", "egoist", "traitorous")


# -- Agent --------------------------------------------------------------------

class EthnoAgent(Agent):
    """One agent: a tag + a strategy + a per-tick PTR accumulator."""

    def __init__(self, agent_id: int, model: "EthnocentrismModel", *,
                 cell: Cell, tag: int, coop_in: bool, coop_out: bool) -> None:
        super().__init__(agent_id, model)
        self.cell = cell
        self.tag = tag
        self.coop_in = coop_in
        self.coop_out = coop_out
        self.ptr = BASE_PTR
        self.alive = True

    @property
    def strategy(self) -> Tuple[bool, bool]:
        return (self.coop_in, self.coop_out)

    @property
    def phenotype(self) -> str:
        return strategy_name(self.coop_in, self.coop_out)

    def cooperates_with(self, other: "EthnoAgent") -> bool:
        """Does this agent cooperate (pay c, give b) toward ``other``? Depends on its
        strategy and whether ``other`` shares its tag (same-tag -> coop_in bit)."""
        return self.coop_in if other.tag == self.tag else self.coop_out


# -- Model --------------------------------------------------------------------

class EthnocentrismModel(AgentModel):
    """Drives the Hammond-Axelrod ethnocentrism model on a fixed L x L grid.

    Per-tick order (the paper): (1) immigration, (2) interaction (accumulate PTR via the
    one-shot PD with the 4 von Neumann neighbours), (3) reproduction into an empty
    neighbour with prob = PTR (mutated inheritance), (4) death at a fixed rate. The
    ``DataCollector`` records strategy shares + cooperation rates each tick.
    """

    NEIGHBOUR_OFFSETS: Tuple[Cell, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))  # von Neumann

    def __init__(self, *, side: int = 50, n_tags: int = N_TAGS, cost: float = COST,
                 benefit: float = BENEFIT, base_ptr: float = BASE_PTR,
                 mutation: float = MUTATION, death_rate: float = DEATH_RATE,
                 seed: int = 0, max_steps: int = 2000) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.side = side
        self.n_tags = n_tags
        self.cost = cost
        self.benefit = benefit
        self.base_ptr = base_ptr
        self.mutation = mutation
        self.death_rate = death_rate
        self.max_steps = max_steps

        # grid[r][c] -> the EthnoAgent occupying that site, or None.
        self.grid: List[List[Optional[EthnoAgent]]] = [
            [None for _ in range(side)] for _ in range(side)
        ]
        self.empty_cells: set[Cell] = {(r, c) for r in range(side) for c in range(side)}
        self._next_id = 0

        # last-tick realized cooperation tallies (filled during interaction).
        self._in_coop = 0      # in-group cooperative ACTS
        self._in_total = 0     # in-group ordered (agent, same-tag neighbour) pairs
        self._out_coop = 0     # out-group cooperative ACTS
        self._out_total = 0    # out-group ordered (agent, diff-tag neighbour) pairs

        self.reporter = DataCollector({
            "population": lambda m: m.population(),
            "ethnocentric": lambda m: m.strategy_share("ethnocentric"),
            "humanitarian": lambda m: m.strategy_share("humanitarian"),
            "egoist": lambda m: m.strategy_share("egoist"),
            "traitorous": lambda m: m.strategy_share("traitorous"),
            "in_coop_rate": lambda m: m.in_coop_rate(),
            "out_coop_rate": lambda m: m.out_coop_rate(),
        })

    # -- grid helpers --
    def _new_id(self) -> int:
        i = self._next_id
        self._next_id += 1
        return i

    def _place(self, agent: EthnoAgent, cell: Cell) -> None:
        r, c = cell
        self.grid[r][c] = agent
        self.empty_cells.discard(cell)
        agent.cell = cell

    def _vacate(self, cell: Cell) -> None:
        r, c = cell
        self.grid[r][c] = None
        self.empty_cells.add(cell)

    def _neighbour_cells(self, cell: Cell) -> List[Cell]:
        r, c = cell
        out: List[Cell] = []
        for dr, dc in self.NEIGHBOUR_OFFSETS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.side and 0 <= nc < self.side:
                out.append((nr, nc))
        return out

    def _occupied_neighbours(self, agent: EthnoAgent) -> List[EthnoAgent]:
        out: List[EthnoAgent] = []
        for (nr, nc) in self._neighbour_cells(agent.cell):
            occ = self.grid[nr][nc]
            if occ is not None:
                out.append(occ)
        return out

    def _empty_neighbours(self, cell: Cell) -> List[Cell]:
        return [c for c in self._neighbour_cells(cell) if self.grid[c[0]][c[1]] is None]

    def living_agents(self) -> List[EthnoAgent]:
        """Agents currently on the grid, in row-major (deterministic) order."""
        out: List[EthnoAgent] = []
        for r in range(self.side):
            row = self.grid[r]
            for c in range(self.side):
                occ = row[c]
                if occ is not None:
                    out.append(occ)
        return out

    # -- stage 1: immigration --
    def _immigrate(self) -> None:
        if not self.empty_cells:
            return
        cell = self._choice(sorted(self.empty_cells))
        tag = self.rng.randrange(self.n_tags)
        coop_in = self.rng.random() < 0.5
        coop_out = self.rng.random() < 0.5
        agent = EthnoAgent(self._new_id(), self, cell=cell, tag=tag,
                           coop_in=coop_in, coop_out=coop_out)
        self._place(agent, cell)

    # -- stage 2: interaction (donation/PD with the 4 NN) --
    def _interact(self) -> None:
        agents = self.living_agents()
        # reset PTR to base for every agent at the start of the interaction stage
        for a in agents:
            a.ptr = self.base_ptr
        self._in_coop = self._in_total = self._out_coop = self._out_total = 0
        # one-shot simultaneous donation game over every ORDERED (agent -> neighbour) pair.
        for a in agents:
            for nb in self._occupied_neighbours(a):
                same = (nb.tag == a.tag)
                if same:
                    self._in_total += 1
                else:
                    self._out_total += 1
                if a.cooperates_with(nb):
                    # a pays cost c, nb receives benefit b
                    a.ptr -= self.cost
                    nb.ptr += self.benefit
                    if same:
                        self._in_coop += 1
                    else:
                        self._out_coop += 1
        # clamp PTR into [0,1] so it is a valid reproduction probability
        for a in agents:
            if a.ptr < 0.0:
                a.ptr = 0.0
            elif a.ptr > 1.0:
                a.ptr = 1.0

    # -- stage 3: reproduction (prob = PTR, into an empty NN, mutated inheritance) --
    def _reproduce(self) -> None:
        # snapshot parents in deterministic order; offspring placed this tick do not
        # themselves reproduce until the next tick (Hammond-Axelrod semantics).
        for parent in self.living_agents():
            if self.rng.random() >= parent.ptr:
                continue
            empties = self._empty_neighbours(parent.cell)
            if not empties:
                continue
            target = self._choice(empties)
            tag, coop_in, coop_out = self._inherit(parent)
            child = EthnoAgent(self._new_id(), self, cell=target, tag=tag,
                               coop_in=coop_in, coop_out=coop_out)
            self._place(child, target)

    def _inherit(self, parent: EthnoAgent) -> Tuple[int, bool, bool]:
        """Offspring genome: parent's (tag, coop_in, coop_out) with each locus
        independently mutated with prob ``self.mutation``."""
        tag = parent.tag
        if self.rng.random() < self.mutation:
            tag = self.rng.randrange(self.n_tags)
        coop_in = parent.coop_in
        if self.rng.random() < self.mutation:
            coop_in = not coop_in
        coop_out = parent.coop_out
        if self.rng.random() < self.mutation:
            coop_out = not coop_out
        return tag, coop_in, coop_out

    # -- stage 4: death --
    def _die(self) -> None:
        for agent in self.living_agents():
            if self.rng.random() < self.death_rate:
                self._vacate(agent.cell)

    # -- RNG helper (deterministic uniform choice from a list) --
    def _choice(self, seq: List[Any]) -> Any:
        return seq[self.rng.randrange(len(seq))]

    # -- metrics --
    def population(self) -> int:
        return self.side * self.side - len(self.empty_cells)

    def strategy_counts(self) -> Dict[str, int]:
        counts = {name: 0 for name in STRATEGY_NAMES}
        for a in self.living_agents():
            counts[a.phenotype] += 1
        return counts

    def strategy_share(self, name: str) -> float:
        pop = self.population()
        if pop == 0:
            return 0.0
        return self.strategy_counts()[name] / pop

    def in_coop_rate(self) -> float:
        """Fraction of in-group (same-tag) ordered neighbour pairs in which the agent
        cooperated, from the most recent interaction stage."""
        return self._in_coop / self._in_total if self._in_total else 0.0

    def out_coop_rate(self) -> float:
        """Fraction of out-group (different-tag) ordered neighbour pairs cooperated."""
        return self._out_coop / self._out_total if self._out_total else 0.0

    # -- tick --
    def step(self) -> None:  # type: ignore[override]
        """One Hammond-Axelrod tick: immigration -> interaction -> reproduction -> death."""
        self._immigrate()
        self._interact()
        self._reproduce()
        self._die()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``max_steps`` ticks; return a summary with the share + coop-rate series."""
        self.reporter.collect(self)  # t=0 baseline (empty grid)
        for _ in range(self.max_steps):
            self.step()
        return {
            "side": self.side,
            "n_tags": self.n_tags,
            "cost": self.cost,
            "benefit": self.benefit,
            "base_ptr": self.base_ptr,
            "mutation": self.mutation,
            "death_rate": self.death_rate,
            "steps": self.t,
            "population_series": self.reporter.series("population"),
            "ethnocentric_series": self.reporter.series("ethnocentric"),
            "humanitarian_series": self.reporter.series("humanitarian"),
            "egoist_series": self.reporter.series("egoist"),
            "traitorous_series": self.reporter.series("traitorous"),
            "in_coop_series": self.reporter.series("in_coop_rate"),
            "out_coop_series": self.reporter.series("out_coop_rate"),
        }


# -- summary statistics -------------------------------------------------------

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs: List[float]) -> float:
    import math
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


# -- multi-seed drivers -------------------------------------------------------

def run_single(*, side: int = 50, n_tags: int = N_TAGS, cost: float = COST,
               benefit: float = BENEFIT, base_ptr: float = BASE_PTR,
               mutation: float = MUTATION, death_rate: float = DEATH_RATE,
               seed: int = 0, max_steps: int = 2000, tail: int = 200) -> Dict[str, Any]:
    """One full ethnocentrism run for a given seed; tail = #ticks at the end to average
    the steady-state shares + cooperation rates over."""
    model = EthnocentrismModel(
        side=side, n_tags=n_tags, cost=cost, benefit=benefit, base_ptr=base_ptr,
        mutation=mutation, death_rate=death_rate, seed=seed, max_steps=max_steps)
    res = model.run()
    res["seed"] = seed
    res["tail"] = tail
    for key in ("ethnocentric", "humanitarian", "egoist", "traitorous"):
        res[f"{key}_tail_mean"] = _mean(res[f"{key}_series"][-tail:])
    res["in_coop_tail_mean"] = _mean(res["in_coop_series"][-tail:])
    res["out_coop_tail_mean"] = _mean(res["out_coop_series"][-tail:])
    res["population_tail_mean"] = _mean(res["population_series"][-tail:])
    return res


def run_many_seeds(seeds: List[int], *, side: int = 50, n_tags: int = N_TAGS,
                   cost: float = COST, benefit: float = BENEFIT, base_ptr: float = BASE_PTR,
                   mutation: float = MUTATION, death_rate: float = DEATH_RATE,
                   max_steps: int = 2000, tail: int = 200) -> Dict[str, Any]:
    """Run one simulation per seed at a FIXED config; average the steady-state strategy
    shares + cooperation rates over the last ``tail`` ticks, then across seeds. Returns
    per-seed rows plus cross-seed means and standard deviations."""
    rows: List[Dict[str, Any]] = []
    for s in seeds:
        rows.append(run_single(side=side, n_tags=n_tags, cost=cost, benefit=benefit,
                               base_ptr=base_ptr, mutation=mutation, death_rate=death_rate,
                               seed=s, max_steps=max_steps, tail=tail))

    def col(key: str) -> List[float]:
        return [r[key] for r in rows]

    shares = {name: col(f"{name}_tail_mean") for name in STRATEGY_NAMES}
    in_coop = col("in_coop_tail_mean")
    out_coop = col("out_coop_tail_mean")
    pop = col("population_tail_mean")
    return {
        "seeds": list(seeds),
        "config": {
            "side": side, "n_tags": n_tags, "cost": cost, "benefit": benefit,
            "base_ptr": base_ptr, "mutation": mutation, "death_rate": death_rate,
            "max_steps": max_steps, "tail": tail, "bc_ratio": benefit / cost,
        },
        "rows": rows,
        "mean_shares": {name: _mean(shares[name]) for name in STRATEGY_NAMES},
        "sd_shares": {name: _stdev(shares[name]) for name in STRATEGY_NAMES},
        "mean_in_coop_rate": _mean(in_coop),
        "sd_in_coop_rate": _stdev(in_coop),
        "mean_out_coop_rate": _mean(out_coop),
        "sd_out_coop_rate": _stdev(out_coop),
        "mean_population": _mean(pop),
    }
