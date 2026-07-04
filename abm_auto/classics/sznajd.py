"""Sznajd 2000 opinion dynamics ("united we stand") — a faithful agent-based reproduction.

Source: Sznajd-Weron, K. & Sznajd, J. (2000) "Opinion evolution in closed community",
Int. J. Mod. Phys. C 11(6):1157-1165.

This is the **2D** Sznajd model (the standard 2D "united we stand, divided we fall"
generalisation of the original 1D chain). Rules (verified against the model family):

  * L x L lattice with PERIODIC boundaries; each cell hosts an ``OpinionAgent`` holding
    an opinion s in {-1, +1}. The opinion lives ON the agent (agents persist; the rule
    reads/writes the opinions of agents at local lattice cells).
  * Initial up-density d: each cell independently set to +1 with probability d, else -1
    (random placement, seeded).
  * Update step ("united we stand"): pick a UNIFORMLY RANDOM 2x2 plaquette (its
    top-left anchor cell is drawn at random; the plaquette is anchor + right + down +
    down-right, all with wraparound). If ALL FOUR agents in the plaquette share the same
    opinion, set the EIGHT outer neighbours that share an edge with the 2x2 block (two
    above, two below, two left, two right — the canonical Stauffer 2000 "convince the 8
    nearest neighbours" rule; the 4 diagonal corners of the surrounding frame are NOT
    persuaded) to that opinion. Otherwise nothing changes. The pick is purely local +
    random — there is NO global oracle reading the whole lattice to choose where to act.
  * One "tick" (sweep) = L*L plaquette picks. Run until a FROZEN state (a full sweep
    produced zero opinion changes) or a step cap is hit.
  * Outcome = final magnetization m = mean opinion over all cells, plus which consensus
    was reached (all-up m=+1, all-down m=-1, or a non-consensus frozen state).

Deterministic given a seed: a single seeded RNG chain on the model drives both the
initial placement and every plaquette pick, so the same seed reproduces byte-identical
output.

Built on the neutral platform (``abm_auto._platform``): each cell is an autonomous
``OpinionAgent`` carrying its opinion; the ``SznajdModel`` owns the seeded RNG, the
lattice index, the plaquette rule, and a ``DataCollector`` for the per-sweep
magnetization series — NOT a hand-rolled god-loop.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class OpinionAgent(Agent):
    """One lattice site. ``opinion`` in {-1, +1}; ``row``/``col`` are its fixed cell.

    The agent is a passive opinion-holder: the Sznajd plaquette rule (owned by the
    model) reads four agents' opinions and, when they agree, writes the consensus
    opinion onto the eight perimeter agents. There is no per-agent ``step`` in the
    classic Sznajd dynamics (the unit of action is a plaquette pick, not an agent
    activation), so ``step`` is a no-op kept only to satisfy the platform contract.
    """

    def __init__(self, agent_id: int, model: "SznajdModel", *, row: int, col: int,
                 opinion: int) -> None:
        super().__init__(agent_id, model)
        self.row = row
        self.col = col
        self.opinion = opinion

    def step(self) -> None:  # pragma: no cover - Sznajd acts per-plaquette, not per-agent
        pass


# -- Model --------------------------------------------------------------------

class SznajdModel(AgentModel):
    """2D Sznajd "united we stand" dynamics on an L x L periodic lattice.

    Construct with the lattice size L, the initial up-density d, and a seed. ``run``
    drives plaquette picks one sweep (L*L picks) at a time until a frozen state (a full
    sweep with no changes) or ``max_sweeps`` is reached, then returns a summary dict
    (final magnetization + consensus label + the per-sweep magnetization series).
    """

    def __init__(self, *, L: int = 40, d: float = 0.5, seed: int = 0,
                 max_sweeps: int = 1000) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.seed = seed
        self.L = L
        self.d = d
        self.max_sweeps = max_sweeps
        self.n = L * L

        # Random initial placement (seeded): each cell +1 with prob d, else -1.
        self.grid: List[List[OpinionAgent]] = []
        agent_id = 0
        for r in range(L):
            row_agents: List[OpinionAgent] = []
            for c in range(L):
                opinion = 1 if self.rng.random() < d else -1
                agent = OpinionAgent(agent_id, self, row=r, col=c, opinion=opinion)
                row_agents.append(agent)
                self.add_agent(agent)
                agent_id += 1
            self.grid.append(row_agents)

        self.reporter = DataCollector({"magnetization": lambda m: m.magnetization()})

    # -- metrics --
    def magnetization(self) -> float:
        """Mean opinion over all cells, in [-1, +1]."""
        total = sum(self.grid[r][c].opinion for r in range(self.L) for c in range(self.L))
        return total / self.n if self.n else 0.0

    def up_fraction(self) -> float:
        """Fraction of cells currently +1."""
        ups = sum(1 for r in range(self.L) for c in range(self.L)
                  if self.grid[r][c].opinion == 1)
        return ups / self.n if self.n else 0.0

    def consensus(self) -> Optional[int]:
        """+1 if the whole lattice is +1, -1 if all -1, else None (no consensus)."""
        m = self.magnetization()
        if m == 1.0:
            return 1
        if m == -1.0:
            return -1
        return None

    # -- the plaquette rule --
    def _plaquette_cells(self, r: int, c: int) -> Tuple[Tuple[int, int], ...]:
        """The four cells of the 2x2 plaquette anchored (top-left) at (r, c), with
        wraparound."""
        L = self.L
        rd, cd = (r + 1) % L, (c + 1) % L
        return ((r, c), (r, cd), (rd, c), (rd, cd))

    def _perimeter_cells(self, r: int, c: int) -> Tuple[Tuple[int, int], ...]:
        """The EIGHT outer neighbours of the 2x2 plaquette anchored at (r, c): the cells
        that share an EDGE with the 2x2 block — two above it, two below it, two left, two
        right (the four diagonal corners of the surrounding 4x4 frame are EXCLUDED, which
        is the canonical 2D Sznajd "convince the 8 nearest neighbours" rule, Stauffer 2000).
        Computed with wraparound; the plaquette spans rows r..r+1, cols c..c+1."""
        L = self.L
        rm1, r0, r1, r2 = (r - 1) % L, r % L, (r + 1) % L, (r + 2) % L
        cm1, c0, c1, c2 = (c - 1) % L, c % L, (c + 1) % L, (c + 2) % L
        return (
            (rm1, c0), (rm1, c1),     # two cells directly ABOVE the plaquette
            (r2, c0), (r2, c1),       # two cells directly BELOW the plaquette
            (r0, cm1), (r1, cm1),     # two cells directly LEFT of the plaquette
            (r0, c2), (r1, c2),       # two cells directly RIGHT of the plaquette
        )

    def apply_plaquette(self, r: int, c: int) -> int:
        """Apply the 'united we stand' rule at the plaquette anchored at (r, c).

        Returns the number of opinion changes made (0 if the four did not all agree, or
        if every perimeter cell already held the consensus opinion)."""
        cells = self._plaquette_cells(r, c)
        s0 = self.grid[cells[0][0]][cells[0][1]].opinion
        # All four must share the same opinion.
        for (rr, cc) in cells[1:]:
            if self.grid[rr][cc].opinion != s0:
                return 0
        changes = 0
        # The 8 perimeter cells are distinct for L >= 4 (the only sizes we run). On a
        # tiny lattice (L < 4) wraparound could alias two of them, but the convince
        # writes the SAME value, so a de-dup keeps the change count honest.
        seen: set = set()
        for (rr, cc) in self._perimeter_cells(r, c):
            if (rr, cc) in seen:
                continue
            seen.add((rr, cc))
            agent = self.grid[rr][cc]
            if agent.opinion != s0:
                agent.opinion = s0
                changes += 1
        return changes

    # -- tick (one sweep = L*L plaquette picks) --
    def step(self) -> None:
        """One sweep: L*L uniformly-random plaquette picks, each applying the rule.

        Records the post-sweep magnetization and stores the sweep's total change count
        on ``self._sweep_changes`` so ``run`` can detect a frozen state."""
        L = self.L
        changes = 0
        for _ in range(self.n):
            r = self.rng.randrange(L)
            c = self.rng.randrange(L)
            changes += self.apply_plaquette(r, c)
        self._sweep_changes = changes
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Run sweeps until a frozen state (a full sweep with zero changes) or the sweep
        cap; return the run summary."""
        self.reporter.collect(self)              # t=0 baseline (initial placement)
        self._sweep_changes = 0
        frozen = False
        for _ in range(self.max_sweeps):
            self.step()
            if self._sweep_changes == 0:
                frozen = True
                break
        m = self.magnetization()
        return {
            "L": self.L,
            "d": self.d,
            "n": self.n,
            "seed": self.seed,
            "sweeps": self.t,
            "frozen": frozen,
            "magnetization": m,
            "abs_magnetization": abs(m),
            "up_fraction": self.up_fraction(),
            "consensus": self.consensus(),          # +1, -1, or None
            "all_up": self.consensus() == 1,
            "magnetization_series": self.reporter.series("magnetization"),
        }


# -- sweep / Monte-Carlo helpers ----------------------------------------------

def run_single(*, L: int = 40, d: float = 0.5, seed: int = 0,
               max_sweeps: int = 1000) -> Dict[str, Any]:
    """One Sznajd run to a frozen state (or the sweep cap)."""
    return SznajdModel(L=L, d=d, seed=seed, max_sweeps=max_sweeps).run()


def run_many_seeds(*, L: int = 40, d: float = 0.5, n_seeds: int = 20,
                   seed_base: int = 0, max_sweeps: int = 1000,
                   consensus_tol: float = 0.95) -> Dict[str, Any]:
    """Run ``n_seeds`` independent Sznajd runs at density d and summarise.

    Each trial uses seed ``seed_base + i`` (drives both the initial placement and the
    plaquette picks). Returns per-seed results plus the locked-metric aggregates:
    the fraction of runs reaching |magnetization| >= ``consensus_tol`` (near-complete
    consensus), P(all-UP) (fraction ending in the all-+1 consensus), and magnetization
    mean/variance across seeds. Deterministic given (L, d, seed_base, max_sweeps).
    """
    results: List[Dict[str, Any]] = []
    for i in range(n_seeds):
        results.append(run_single(L=L, d=d, seed=seed_base + i, max_sweeps=max_sweeps))

    mags = [r["magnetization"] for r in results]
    abs_mags = [r["abs_magnetization"] for r in results]
    n = len(results)
    mean_mag = sum(mags) / n if n else 0.0
    mean_abs = sum(abs_mags) / n if n else 0.0
    var_mag = sum((x - mean_mag) ** 2 for x in mags) / n if n else 0.0
    var_abs = sum((x - mean_abs) ** 2 for x in abs_mags) / n if n else 0.0

    n_consensus = sum(1 for r in results if r["abs_magnetization"] >= consensus_tol)
    n_all_up = sum(1 for r in results if r["all_up"])
    n_all_down = sum(1 for r in results if r["consensus"] == -1)
    n_full = sum(1 for r in results if r["consensus"] is not None)
    n_frozen = sum(1 for r in results if r["frozen"])

    return {
        "L": L,
        "d": d,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "max_sweeps": max_sweeps,
        "consensus_tol": consensus_tol,
        "consensus_fraction": n_consensus / n if n else 0.0,   # |m| >= tol
        "p_all_up": n_all_up / n if n else 0.0,
        "p_all_down": n_all_down / n if n else 0.0,
        "p_full_consensus": n_full / n if n else 0.0,           # exact m = +/-1
        "frozen_fraction": n_frozen / n if n else 0.0,
        "mean_magnetization": mean_mag,
        "var_magnetization": var_mag,
        "mean_abs_magnetization": mean_abs,
        "var_abs_magnetization": var_abs,
        "n_consensus": n_consensus,
        "n_all_up": n_all_up,
        "n_all_down": n_all_down,
        "n_full_consensus": n_full,
        "per_seed": [
            {"seed": r["seed"], "magnetization": r["magnetization"],
             "abs_magnetization": r["abs_magnetization"], "up_fraction": r["up_fraction"],
             "consensus": r["consensus"], "all_up": r["all_up"],
             "frozen": r["frozen"], "sweeps": r["sweeps"]}
            for r in results
        ],
    }
