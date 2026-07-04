"""Axelrod (1997) dissemination of culture — a faithful agent-based reproduction.

Source: Axelrod, R. (1997) "The Dissemination of Culture: A Model with Local
Convergence and Global Polarization", J. Conflict Resolution 41(2):203-226.

Rules (verified against the paper):
  * An L x L grid of sites. Each site holds a ``CultureAgent`` whose culture is a
    list of F *features*, each holding one of q integer *traits* in [0, q).
  * Neighbourhood: von-Neumann-4 (N/S/E/W) with NO wrap (bounded grid), matching
    Axelrod's original square lattice. Edge/corner sites simply have fewer
    neighbours. (Documented choice; see module note below.)
  * Activation event (one "step"): pick a random site (the active agent) and one of
    its random neighbours. With probability equal to their *cultural similarity*
    (the fraction of the F features on which they share the same trait) they
    interact; on interaction, pick at random one feature on which they DIFFER and
    the active agent copies the neighbour's trait at that feature.
  * Absorbing state: no adjacent pair has overlap strictly between 0 and 1 — i.e.
    every neighbouring pair is either culturally identical (similarity 1, nothing to
    copy) or completely distinct (similarity 0, can never interact). At that point no
    activation event can ever change anything, so the run halts.
  * Outcome: the number of distinct stable cultural *regions* — connected components
    (over the von-Neumann adjacency) of sites that share an identical culture.

Built on the neutral platform (``abm_auto._platform``): each site is an autonomous
``CultureAgent`` whose ``step`` enacts the activation rule; the model drives an
``AgentSet`` + ``DataCollector`` rather than a hand-rolled god-loop. The schedule is
*one random activation per model step* (Axelrod's event-driven update), so the model's
``step`` activates a single random agent. Given a seed the whole run is reproducible.

Neighbourhood note: Axelrod (1997) used a bounded (non-toroidal) square lattice with
the four orthogonal neighbours. We follow that exactly (von-Neumann-4, no wrap). The
qualitative claims (more traits q -> more regions; more features F -> fewer regions;
small q -> monoculture) are robust to this choice.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class CultureAgent(Agent):
    """One lattice site. ``culture`` is a list of F integer traits in [0, q).

    The agent knows its (row, col) on the grid and queries the model for its
    von-Neumann neighbours. ``step`` performs one Axelrod activation with this agent
    as the active site.
    """

    def __init__(self, agent_id: int, model: "CultureModel", *, row: int, col: int,
                 culture: List[int]) -> None:
        super().__init__(agent_id, model)
        self.row = row
        self.col = col
        self.culture = list(culture)

    def neighbors(self) -> List["CultureAgent"]:
        return self.model.neighbors_of(self.row, self.col)

    def step(self) -> None:
        """One Axelrod activation with this agent active: pick a random neighbour,
        interact with probability = cultural similarity, and on interaction copy one
        random differing feature's trait from the neighbour."""
        nbrs = self.neighbors()
        if not nbrs:
            return
        other = self.model.rng.choice(nbrs)
        self.interact_with(other)

    def interact_with(self, other: "CultureAgent") -> bool:
        """Attempt an interaction with ``other``. Returns True iff a trait was copied.

        With probability = similarity(self, other) the pair interacts; on interaction
        a random feature on which they DIFFER is chosen and ``self`` adopts ``other``'s
        trait there. Pairs that are identical (sim=1) or fully distinct (sim=0) never
        copy.
        """
        F = self.model.n_features
        diff = [i for i in range(F) if self.culture[i] != other.culture[i]]
        n_diff = len(diff)
        if n_diff == 0:
            return False  # identical: nothing to copy
        similarity = (F - n_diff) / F
        if similarity == 0.0:
            return False  # fully distinct: never interact
        # Interact with probability = similarity.
        if self.model.rng.random() < similarity:
            feature = self.model.rng.choice(diff)
            self.culture[feature] = other.culture[feature]
            return True
        return False


# -- Model --------------------------------------------------------------------

class CultureModel(AgentModel):
    """Drives Axelrod culture dynamics on an L x L bounded grid to an absorbing state.

    One model ``step`` = one random activation event (event-driven update). ``run``
    iterates activations until the configuration is absorbing (no adjacent pair has
    0 < similarity < 1) or a step cap is hit, then reports the number of stable
    cultural regions.
    """

    def __init__(self, *, L: int = 10, n_features: int = 5, n_traits: int = 5,
                 seed: int = 0, max_steps: Optional[int] = None,
                 absorb_check_every: Optional[int] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        self.L = L
        self.n_features = n_features
        self.n_traits = n_traits
        self.n = L * L
        # A generous cap; for L=10 the dynamics reach absorption well within this.
        self.max_steps = max_steps if max_steps is not None else 2_000_000
        # Checking absorption every step is O(n) and dominates runtime; amortise it.
        self.absorb_check_every = (
            absorb_check_every if absorb_check_every is not None else self.n
        )

        # Build the grid of agents with random initial cultures (seeded RNG).
        self.grid: List[List[CultureAgent]] = []
        aid = 0
        for r in range(L):
            row_agents: List[CultureAgent] = []
            for c in range(L):
                culture = [self.rng.randrange(n_traits) for _ in range(n_features)]
                agent = CultureAgent(aid, self, row=r, col=c, culture=culture)
                row_agents.append(agent)
                self.add_agent(agent)
                aid += 1
            self.grid.append(row_agents)

        self.reporter = DataCollector({"active_edges": lambda m: m.active_edge_count()})

    # -- topology --
    def neighbors_of(self, row: int, col: int) -> List[CultureAgent]:
        """von-Neumann-4 neighbours (N/S/E/W), bounded grid (no wrap)."""
        out: List[CultureAgent] = []
        if row > 0:
            out.append(self.grid[row - 1][col])
        if row < self.L - 1:
            out.append(self.grid[row + 1][col])
        if col > 0:
            out.append(self.grid[row][col - 1])
        if col < self.L - 1:
            out.append(self.grid[row][col + 1])
        return out

    def _adjacent_pairs(self):
        """Yield each adjacent (von-Neumann) ordered-once pair (right + down edges)."""
        for r in range(self.L):
            for c in range(self.L):
                a = self.grid[r][c]
                if c < self.L - 1:
                    yield a, self.grid[r][c + 1]
                if r < self.L - 1:
                    yield a, self.grid[r + 1][c]

    def similarity(self, a: CultureAgent, b: CultureAgent) -> float:
        same = sum(1 for i in range(self.n_features) if a.culture[i] == b.culture[i])
        return same / self.n_features

    # -- metrics --
    def active_edge_count(self) -> int:
        """Number of adjacent pairs that can still interact (0 < similarity < 1)."""
        n = 0
        F = self.n_features
        for a, b in self._adjacent_pairs():
            same = sum(1 for i in range(F) if a.culture[i] == b.culture[i])
            if 0 < same < F:
                n += 1
        return n

    def is_absorbing(self) -> bool:
        """True iff NO adjacent pair has 0 < similarity < 1 (no event can fire)."""
        F = self.n_features
        for a, b in self._adjacent_pairs():
            same = sum(1 for i in range(F) if a.culture[i] == b.culture[i])
            if 0 < same < F:
                return False
        return True

    def count_regions(self) -> int:
        """Number of connected components of identical-culture neighbours
        (von-Neumann adjacency). This is the count of distinct stable regions."""
        seen = [[False] * self.L for _ in range(self.L)]
        regions = 0
        for r0 in range(self.L):
            for c0 in range(self.L):
                if seen[r0][c0]:
                    continue
                regions += 1
                culture = self.grid[r0][c0].culture
                # Flood fill the connected same-culture component.
                stack = [(r0, c0)]
                seen[r0][c0] = True
                while stack:
                    r, c = stack.pop()
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < self.L and 0 <= cc < self.L and not seen[rr][cc]:
                            if self.grid[rr][cc].culture == culture:
                                seen[rr][cc] = True
                                stack.append((rr, cc))
        return regions

    def distinct_cultures(self) -> int:
        """Number of distinct culture vectors present (NOT spatially connected).
        Reported as a diagnostic alongside ``count_regions``."""
        return len({tuple(a.culture) for a in self.agents})

    # -- tick --
    def step(self) -> None:
        """One activation event: a single uniformly-random agent is activated."""
        agent = self.rng.choice(list(self.agents))
        agent.step()
        self.t += 1

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate activation events until absorbing (or the step cap). Returns the
        run summary including the number of stable cultural regions."""
        if self.reporter is not None:
            self.reporter.collect(self)  # t=0 baseline
        absorbed = False
        for _ in range(self.max_steps):
            if self.t % self.absorb_check_every == 0 and self.is_absorbing():
                absorbed = True
                break
            self.step()
        else:
            absorbed = self.is_absorbing()
        # Final exact check (the cap may have landed mid-cycle).
        if not absorbed:
            absorbed = self.is_absorbing()
        if self.reporter is not None:
            self.reporter.collect(self)
        regions = self.count_regions()
        return {
            "L": self.L,
            "n_features": self.n_features,
            "n_traits": self.n_traits,
            "seed": self.rng_seed if hasattr(self, "rng_seed") else None,
            "steps": self.t,
            "absorbed": absorbed,
            "regions": regions,
            "distinct_cultures": self.distinct_cultures(),
            "largest_region_fraction": self._largest_region_fraction(),
        }

    def _largest_region_fraction(self) -> float:
        """Fraction of the grid occupied by the single largest region (1.0 => one
        culture fills the whole grid = monoculture)."""
        sizes = self._region_sizes()
        return (max(sizes) / self.n) if sizes else 0.0

    def _region_sizes(self) -> List[int]:
        seen = [[False] * self.L for _ in range(self.L)]
        sizes: List[int] = []
        for r0 in range(self.L):
            for c0 in range(self.L):
                if seen[r0][c0]:
                    continue
                culture = self.grid[r0][c0].culture
                size = 0
                stack = [(r0, c0)]
                seen[r0][c0] = True
                while stack:
                    r, c = stack.pop()
                    size += 1
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < self.L and 0 <= cc < self.L and not seen[rr][cc]:
                            if self.grid[rr][cc].culture == culture:
                                seen[rr][cc] = True
                                stack.append((rr, cc))
                sizes.append(size)
        return sizes


# -- run + sweep helpers ------------------------------------------------------

def run_single(*, L: int = 10, n_features: int = 5, n_traits: int = 5,
               seed: int = 0, max_steps: Optional[int] = None) -> Dict[str, Any]:
    """One Axelrod run to an absorbing state; returns the summary dict."""
    model = CultureModel(L=L, n_features=n_features, n_traits=n_traits, seed=seed,
                         max_steps=max_steps)
    model.rng_seed = seed  # for the summary
    return model.run()


def run_many_seeds(*, L: int = 10, n_features: int = 5, n_traits: int = 5,
                   n_seeds: int = 10, seed_base: int = 0,
                   max_steps: Optional[int] = None) -> Dict[str, Any]:
    """Run ``n_seeds`` independent Axelrod runs (seeds ``seed_base..seed_base+n-1``)
    at fixed (L, F, q) and summarise the number-of-regions distribution.

    Deterministic: run ``i`` uses seed ``seed_base + i``. Returns mean/min/max
    regions, the per-seed region counts, and per-seed full summaries.
    """
    per_seed: List[Dict[str, Any]] = []
    regions: List[int] = []
    for i in range(n_seeds):
        s = seed_base + i
        res = run_single(L=L, n_features=n_features, n_traits=n_traits, seed=s,
                         max_steps=max_steps)
        per_seed.append(res)
        regions.append(res["regions"])
    mean_regions = sum(regions) / len(regions) if regions else 0.0
    all_absorbed = all(r["absorbed"] for r in per_seed)
    mean_largest = (
        sum(r["largest_region_fraction"] for r in per_seed) / len(per_seed)
        if per_seed else 0.0
    )
    return {
        "L": L,
        "n_features": n_features,
        "n_traits": n_traits,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "regions": regions,
        "mean_regions": mean_regions,
        "min_regions": min(regions) if regions else 0,
        "max_regions": max(regions) if regions else 0,
        "all_absorbed": all_absorbed,
        "mean_largest_region_fraction": mean_largest,
        "per_seed": per_seed,
    }


def regions_vs_q(*, qs: List[int], L: int = 10, n_features: int = 5,
                 n_seeds: int = 10, seed_base: int = 0,
                 max_steps: Optional[int] = None) -> List[Dict[str, Any]]:
    """Sweep number of traits q at fixed F; one summary per q (mean over seeds)."""
    return [
        run_many_seeds(L=L, n_features=n_features, n_traits=q, n_seeds=n_seeds,
                       seed_base=seed_base, max_steps=max_steps)
        for q in qs
    ]


def regions_vs_F(*, Fs: List[int], L: int = 10, n_traits: int = 10,
                 n_seeds: int = 10, seed_base: int = 0,
                 max_steps: Optional[int] = None) -> List[Dict[str, Any]]:
    """Sweep number of features F at fixed q; one summary per F (mean over seeds)."""
    return [
        run_many_seeds(L=L, n_features=f, n_traits=n_traits, n_seeds=n_seeds,
                       seed_base=seed_base, max_steps=max_steps)
        for f in Fs
    ]
