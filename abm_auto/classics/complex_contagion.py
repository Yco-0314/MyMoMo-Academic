"""Faithful agent-based reproduction of Centola & Macy (2007) complex contagion.

Source: Centola, D. & Macy, M. (2007) "Complex Contagions and the Weakness of Long
Ties", AJS 113(3):702-734; model corroborated via Centola, Eguiluz & Macy (2007),
Physica A 374:449-456.

Model (faithful to the paper's stated rules)
--------------------------------------------
- Substrate: a Watts-Strogatz ring lattice on ``n`` nodes, degree ``z=8`` (each node
  wired to its 4 nearest neighbors on each side), with rewiring fraction ``p in [0,1]``.
  ``p=0`` is the clustered regular ring; ``p=1`` is (near-)randomized. We use networkx
  ``watts_strogatz_graph(n, k=8, p, seed)``. NOTE: WS rewiring is only APPROXIMATELY
  degree-preserving (rewired endpoints change individual degrees while the EDGE COUNT,
  hence the mean degree z=8, is exactly preserved). This is the standard, documented
  WS construction and is acceptable per the design spec.

- Local rule (NUMBER threshold, not fraction): a node adopts iff the NUMBER of its
  active neighbors is >= R. R=1 is a simple contagion; R=2 (or higher) is a complex
  contagion. Adoption is monotone (irreversible), as in the paper.

- Update: SYNCHRONOUS. Every agent reads the neighbor-activation snapshot taken at the
  start of the tick, so the result is independent of agent visiting order (the platform
  scheduler order does not affect the fixed point). Deterministic given a seed.

- Seeding (critical): a complex contagion (R>=2) cannot ignite from a single node, so we
  seed a small CONTIGUOUS neighborhood -- a seed node plus its immediate ring-lattice
  neighbors on the underlying (pre-rewiring) ring. The SAME seed set is used for R=1 and
  R=2. The seed is minimal (one node + its ``seed_radius`` nearest ring-neighbors on
  each side); it is NOT enlarged to force spread.

- Outcome: iterate to a fixed point (no new adoptions in a full tick); outcome = final
  adoption fraction = activated / n.

This is a genuine agent-based model on ``abm_auto._platform`` (autonomous ``Agent`` with
a local ``step``, an ``AgentSet`` scheduler, a ``DataCollector``), NOT a god-loop.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import networkx as nx

from abm_auto._platform import Agent, AgentModel, DataCollector

# Faithful fixed parameters (Centola & Macy 2007 / design spec).
DEGREE_Z = 8          # ring lattice degree (k in networkx watts_strogatz_graph)
SEED_RADIUS = 2       # seed node + this many ring-neighbors on EACH side


class ContagionAgent(Agent):
    """One node. Holds local activation state and a NUMBER-threshold adopt rule.

    The agent acts only on a snapshot of its neighbors' activation taken at the start
    of the tick (``model.snapshot``), so adoption is synchronous and order-independent.
    Adoption is irreversible.
    """

    def __init__(self, agent_id: int, model: "ContagionModel") -> None:
        super().__init__(agent_id, model)
        self.active: bool = False
        self.neighbors: List[int] = []  # filled by the model after graph build

    def step(self) -> None:
        if self.active:
            return  # monotone: once active, stays active
        model: "ContagionModel" = self.model  # type: ignore[assignment]
        snap = model.snapshot
        active_neighbors = sum(1 for nb in self.neighbors if snap[nb])
        if active_neighbors >= model.R:
            self._pending = True  # commit deferred to model.step (synchronous update)
        else:
            self._pending = False


class ContagionModel(AgentModel):
    """Centola-Macy complex-contagion model on a WS ring lattice.

    Builds the graph, wires one ``ContagionAgent`` per node, seeds a contiguous
    neighborhood, and iterates a SYNCHRONOUS number-threshold update to a fixed point.
    ``run()`` returns a dict with the final adoption fraction and trajectory.
    """

    def __init__(
        self,
        *,
        n: int,
        R: int,
        p: float,
        seed: int = 0,
        z: int = DEGREE_Z,
        seed_radius: int = SEED_RADIUS,
        graph: Optional[nx.Graph] = None,
        max_steps: int = 10_000,
    ) -> None:
        super().__init__(space=None, seed=seed)
        self._seed = seed
        self.n = n
        self.R = R
        self.p = p
        self.z = z
        self.seed_radius = seed_radius
        self.max_steps = max_steps

        # ---- substrate: WS ring lattice (approx. degree-preserving rewiring) ----
        if graph is None:
            graph = nx.watts_strogatz_graph(n, z, p, seed=seed)
        self.graph = graph

        # ---- agents: one per node ----
        self._agents_by_id: Dict[int, ContagionAgent] = {}
        for node in range(n):
            a = ContagionAgent(node, self)
            self._agents_by_id[node] = a
            self.add_agent(a)
        for node in range(n):
            self._agents_by_id[node].neighbors = sorted(self.graph.neighbors(node))

        # snapshot of activation read by agents during a tick (synchronous update)
        self.snapshot: List[bool] = [False] * n

        # ---- seeding: a contiguous neighborhood on the UNDERLYING ring ----
        # The underlying ring order is just node index order (networkx builds the WS
        # graph from a ring 0..n-1); seed node 0 +/- seed_radius wraps around the ring.
        self.seed_nodes = self._contiguous_seed()
        for node in self.seed_nodes:
            self._agents_by_id[node].active = True

        # ---- collector ----
        self.reporter = DataCollector({"adopted": lambda m: m.adopted_count()})

    def _contiguous_seed(self) -> List[int]:
        center = 0
        nodes = {center}
        for d in range(1, self.seed_radius + 1):
            nodes.add((center - d) % self.n)
            nodes.add((center + d) % self.n)
        return sorted(nodes)

    def adopted_count(self) -> int:
        return sum(1 for a in self._agents_by_id.values() if a.active)

    def adoption_fraction(self) -> float:
        return self.adopted_count() / self.n

    def step(self) -> None:
        # 1. snapshot activation at tick start (synchronous read)
        self.snapshot = [self._agents_by_id[i].active for i in range(self.n)]
        # 2. each agent decides locally against the snapshot
        self.agents.step()
        # 3. commit pending adoptions simultaneously
        newly = 0
        for a in self._agents_by_id.values():
            if not a.active and getattr(a, "_pending", False):
                a.active = True
                newly += 1
        self._newly_adopted = newly
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> dict:  # type: ignore[override]
        """Iterate the synchronous update to a fixed point. Returns a result dict."""
        if self.reporter is not None:
            self.reporter.collect(self)  # t=0 baseline (seed only)
        steps = 0
        for _ in range(self.max_steps):
            self.step()
            steps += 1
            if self._newly_adopted == 0:
                break
        return {
            "n": self.n,
            "R": self.R,
            "p": self.p,
            "z": self.z,
            "seed": self.rng_seed,
            "seed_nodes": list(self.seed_nodes),
            "n_seed": len(self.seed_nodes),
            "steps": steps,
            "adopted": self.adopted_count(),
            "adoption_fraction": self.adoption_fraction(),
            "trajectory": self.reporter.series("adopted") if self.reporter else [],
        }

    # AgentModel seeds self.rng = random.Random(seed); keep the int seed for reporting.
    @property
    def rng_seed(self) -> int:
        return self._seed


# ── Helper: build + run one configuration, average over graphs/seeds ──────────────

def run_contagion(
    *,
    n: int,
    R: int,
    p: float,
    seed: int = 0,
    z: int = DEGREE_Z,
    seed_radius: int = SEED_RADIUS,
) -> dict:
    """Build a WS graph for ``seed`` and run one complex-contagion fixed-point.

    Single-run convenience around :class:`ContagionModel`. Deterministic in ``seed``.
    """
    model = ContagionModel(n=n, R=R, p=p, seed=seed, z=z, seed_radius=seed_radius)
    return model.run()


def mean_adoption(
    *,
    n: int,
    R: int,
    p: float,
    n_seeds: int,
    z: int = DEGREE_Z,
    seed_radius: int = SEED_RADIUS,
) -> dict:
    """Average final adoption fraction over ``n_seeds`` independent WS graphs/seeds.

    Each seed both builds a fresh WS graph AND fixes the (deterministic) run; the same
    seed sequence (0..n_seeds-1) is used for every (R, p) so comparisons are paired.
    Returns the mean fraction plus the per-seed fractions and a spread.
    """
    fracs = []
    runs = []
    for s in range(n_seeds):
        res = run_contagion(n=n, R=R, p=p, seed=s, z=z, seed_radius=seed_radius)
        fracs.append(res["adoption_fraction"])
        runs.append(res)
    mean = sum(fracs) / len(fracs)
    return {
        "n": n,
        "R": R,
        "p": p,
        "n_seeds": n_seeds,
        "mean_adoption": mean,
        "min_adoption": min(fracs),
        "max_adoption": max(fracs),
        "per_seed_adoption": fracs,
        "mean_steps": sum(r["steps"] for r in runs) / len(runs),
    }
