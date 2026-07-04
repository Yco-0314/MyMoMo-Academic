"""Random Geometric Graph — Gilbert disk model (2D) — a faithful network-GENERATION
reproduction.

Source: Dall, J. & Christensen, M. (2002). "Random geometric graphs." Phys. Rev. E
66:016121. doi:10.1103/PhysRevE.66.016121. (The disk model traces to Gilbert 1961; its
rigorous large-N theory to Penrose 2003.)

IMPORTANT (honesty, binds the FINDINGS): this is a network-GENERATION model, NOT an
agent-stepping ABM. There are no agents, no scheduler, no ticks. We drop N points
uniformly at random in the 2D unit square and connect any two that are geometrically
close, then measure static structural properties (clustering, giant component, mean
degree). It is reproduced faithfully as a network-science result; the lock-first +
honest-verdict + L3-bundle discipline still fully applies.

Rules (the Gilbert disk ensemble):
  * N points placed uniformly at random in the 2D unit square [0, 1)^2. The boundary is
    HARD (no wrap / no torus): a point near an edge simply has fewer neighbours on that
    side. This is the distinguishing feature vs the torus variant and the source of the
    boundary correction in P1/P3.
  * Connect two points i, j iff their Euclidean distance d(i, j) <= r (the "disk" /
    unit-disk rule). r is the single control.
  * Mean degree relation <k> = N * pi * r^2 (each point's expected neighbour count is the
    density N times the disk area pi*r^2), so to target a mean degree we set
    r = sqrt(<k> / (N * pi)). Boundary loss pulls the realised mean degree modestly below
    this ideal (points near the edge lose part of their disk).

Distinct from Erdos-Renyi G(n, p) at the same <k>: ER has NO spatial embedding — its
clustering is C ~ <k>/N ~ 0.01 (edges are independent, so a neighbour of a neighbour is
no more likely to be a neighbour), and its giant component appears at <k> = 1. The RGG's
geometric overlap makes two neighbours of a node very likely to be within r of each other
too, giving a high, N-independent clustering (bulk constant 0.5865), and its giant
component appears only at a much higher critical mean degree (<k>_c ~ 4.51 for the 2D disk
model). The ER graph at matched <k> is the fair control for the clustering ratio.

Structural metrics (the locked grading quantities):
  * Clustering C = the average local clustering coefficient (mean over nodes with degree
    >= 2 of the fraction of that node's neighbour-pairs that are themselves connected).
  * Giant-component fraction S = largest connected component size / N.
  * Measured mean degree <k>_meas = 2 * (#edges) / N.

Efficiency: neighbour finding uses a uniform CELL / BUCKET grid of cell side >= r over
the unit square, so each point's r-neighbours all lie in its own cell or the 8 adjacent
ones. This is O(N) rather than O(N^2). The boundary is HARD, so cells are NOT wrapped:
edge cells simply have fewer neighbour cells. The cell-grid edge set is verified equal to
the brute-force all-pairs edge set in the tests.

The graph is handed to networkx (an ``nx.Graph``) for the structural measurements
(clustering, connected components), matching the erdos_renyi control module; only the
edge construction is spatial.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Tuple

import networkx as nx


# -- geometry / mean-degree helpers -------------------------------------------

def radius_for_mean_degree(n: int, k: float) -> float:
    """Radius r giving target mean degree <k> = N*pi*r^2, i.e. r = sqrt(<k>/(N*pi)).

    This is the IDEAL (infinite-plane) relation; the hard boundary makes the realised
    mean degree modestly lower (edge points lose part of their disk)."""
    if n <= 0:
        raise ValueError(f"need n > 0 (got {n})")
    if k < 0:
        raise ValueError(f"need k >= 0 (got {k})")
    return math.sqrt(k / (n * math.pi))


def ideal_mean_degree(n: int, r: float) -> float:
    """The ideal (no-boundary) mean degree <k> = N*pi*r^2 for a given radius."""
    return n * math.pi * r * r


def euclid_dist2(x1: float, y1: float, x2: float, y2: float) -> float:
    """Squared Euclidean distance (HARD boundary — no minimum-image / no wrap)."""
    dx = x1 - x2
    dy = y1 - y2
    return dx * dx + dy * dy


# -- the model ----------------------------------------------------------------

class RandomGeometricGraph:
    """Gilbert disk model: N points uniform in [0,1)^2, connect iff distance <= r.

    Construct with N, the connection radius ``r`` (or use ``from_mean_degree`` to target a
    mean degree), and a seed. The points are drawn once from the seeded RNG (the only
    randomness); the edge set is then deterministic. ``build()`` returns the ``nx.Graph``.

    Neighbour finding uses a NON-wrapped uniform cell grid of side >= r (O(N)); the
    boundary is HARD so edge cells simply scan fewer neighbour cells.
    """

    def __init__(self, n: int, r: float, *, seed: int = 0) -> None:
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if r <= 0:
            raise ValueError(f"need r > 0 (got {r})")
        if r > 1.0:
            # r > 1 in a unit square would connect nearly everything; the disk model is
            # only interesting for r << 1. Guard against a nonsensical radius.
            raise ValueError(f"need r <= 1 in the unit square (got {r})")
        self.n = int(n)
        self.r = float(r)
        self.r2 = self.r * self.r
        self.seed_value = int(seed)
        self.rng = random.Random(seed)

        # Points uniform in the unit square [0, 1)^2 (hard boundary).
        self.xs: List[float] = [self.rng.random() for _ in range(self.n)]
        self.ys: List[float] = [self.rng.random() for _ in range(self.n)]

        # Non-wrapped cell grid: square cells of side >= r so a point's r-neighbours lie in
        # its own cell or the 8 adjacent ones. n_cells >= 1 (a tiny r that would give more
        # cells than makes sense still works; a huge r that would give <1 cell falls back
        # to one cell == brute force, still correct).
        self.n_cells = max(1, int(math.floor(1.0 / self.r)))
        self.cell_size = 1.0 / self.n_cells

    @classmethod
    def from_mean_degree(cls, n: int, k: float, *, seed: int = 0) -> "RandomGeometricGraph":
        """Construct targeting mean degree <k>: r = sqrt(<k>/(N*pi))."""
        return cls(n, radius_for_mean_degree(n, k), seed=seed)

    # -- cell grid (non-wrapped) --
    def _cell_of(self, x: float, y: float) -> Tuple[int, int]:
        cx = min(int(x / self.cell_size), self.n_cells - 1)
        cy = min(int(y / self.cell_size), self.n_cells - 1)
        return cx, cy

    def _build_cells(self) -> Dict[Tuple[int, int], List[int]]:
        cells: Dict[Tuple[int, int], List[int]] = {}
        for i in range(self.n):
            key = self._cell_of(self.xs[i], self.ys[i])
            cells.setdefault(key, []).append(i)
        return cells

    def _neighbours(self, i: int, cells: Dict[Tuple[int, int], List[int]]) -> List[int]:
        """Indices j != i within radius r of point i, found via the non-wrapped cell grid
        (scan i's cell and its up-to-8 in-bounds neighbours). Cell side >= r guarantees no
        in-range neighbour is missed."""
        cx, cy = self._cell_of(self.xs[i], self.ys[i])
        nc = self.n_cells
        out: List[int] = []
        xi, yi = self.xs[i], self.ys[i]
        for dx in (-1, 0, 1):
            ncx = cx + dx
            if ncx < 0 or ncx >= nc:      # HARD boundary: no wrap
                continue
            for dy in (-1, 0, 1):
                ncy = cy + dy
                if ncy < 0 or ncy >= nc:
                    continue
                bucket = cells.get((ncx, ncy))
                if not bucket:
                    continue
                for j in bucket:
                    if j == i:
                        continue
                    if euclid_dist2(xi, yi, self.xs[j], self.ys[j]) <= self.r2:
                        out.append(j)
        return out

    def _edges_cell_grid(self) -> List[Tuple[int, int]]:
        """The full edge set via the O(N) cell grid (each undirected edge once, i < j)."""
        cells = self._build_cells()
        edges: List[Tuple[int, int]] = []
        for i in range(self.n):
            for j in self._neighbours(i, cells):
                if i < j:
                    edges.append((i, j))
        return edges

    def _edges_bruteforce(self) -> List[Tuple[int, int]]:
        """O(N^2) reference edge set (all pairs, hard-boundary Euclidean distance). Used
        only to validate the cell-grid path in tests; the model uses the cell grid."""
        edges: List[Tuple[int, int]] = []
        for i in range(self.n):
            xi, yi = self.xs[i], self.ys[i]
            for j in range(i + 1, self.n):
                if euclid_dist2(xi, yi, self.xs[j], self.ys[j]) <= self.r2:
                    edges.append((i, j))
        return edges

    def build(self) -> nx.Graph:
        """Build the RGG as an ``nx.Graph`` (nodes 0..N-1, spatial edges via the cell
        grid). Deterministic given the seed."""
        g = nx.Graph()
        g.add_nodes_from(range(self.n))
        g.add_edges_from(self._edges_cell_grid())
        return g


# -- structural measurements --------------------------------------------------

def clustering_coefficient(graph: nx.Graph) -> float:
    """Average local clustering coefficient (mean over nodes of the fraction of a node's
    neighbour-pairs that are themselves connected). networkx averages the per-node value
    over ALL nodes, assigning 0 to degree<2 nodes — the standard Watts-Strogatz average
    clustering, which is the quantity the RGG bulk constant 0.5865 refers to."""
    if graph.number_of_nodes() == 0:
        return 0.0
    return nx.average_clustering(graph)


def largest_component_fraction(graph: nx.Graph) -> float:
    """Fraction of nodes in the largest connected component (0 for empty graph)."""
    n = graph.number_of_nodes()
    if n == 0:
        return 0.0
    if graph.number_of_edges() == 0:
        return 1.0 / n  # all isolated; the "largest" component is a single node
    return max(len(c) for c in nx.connected_components(graph)) / n


def measured_mean_degree(graph: nx.Graph) -> float:
    """Realised mean degree <k>_meas = 2*(#edges)/N."""
    n = graph.number_of_nodes()
    if n == 0:
        return 0.0
    return 2.0 * graph.number_of_edges() / n


# -- sweep helpers ------------------------------------------------------------

def run_single(n: int, k: float, *, seed: int = 0) -> Dict[str, Any]:
    """Build one RGG targeting mean degree <k> and return its structural summary."""
    model = RandomGeometricGraph.from_mean_degree(n, k, seed=seed)
    g = model.build()
    return {
        "n": n,
        "k_target": k,
        "r": model.r,
        "ideal_mean_degree": ideal_mean_degree(n, model.r),
        "seed": seed,
        "clustering": clustering_coefficient(g),
        "largest_component_fraction": largest_component_fraction(g),
        "measured_mean_degree": measured_mean_degree(g),
        "n_edges": g.number_of_edges(),
    }


def run_many_seeds(n: int, k: float, *, n_seeds: int = 10,
                   seed_base: int = 0) -> Dict[str, Any]:
    """Build ``n_seeds`` RGGs targeting mean degree <k> and summarise the three structural
    quantities (mean + spread + per-seed lists). Deterministic: seed ``seed_base + i``."""
    runs = [run_single(n, k, seed=seed_base + i) for i in range(n_seeds)]
    clust = [rr["clustering"] for rr in runs]
    frac = [rr["largest_component_fraction"] for rr in runs]
    kmeas = [rr["measured_mean_degree"] for rr in runs]

    def mean(xs: List[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    def std(xs: List[float]) -> float:
        if len(xs) < 2:
            return 0.0
        m = mean(xs)
        return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5

    r = runs[0]["r"]
    return {
        "n": n,
        "k_target": k,
        "r": r,
        "ideal_mean_degree": ideal_mean_degree(n, r),
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "per_seed_clustering": clust,
        "per_seed_largest_component_fraction": frac,
        "per_seed_measured_mean_degree": kmeas,
        "mean_clustering": mean(clust),
        "std_clustering": std(clust),
        "min_clustering": min(clust),
        "max_clustering": max(clust),
        "mean_largest_component_fraction": mean(frac),
        "std_largest_component_fraction": std(frac),
        "min_largest_component_fraction": min(frac),
        "max_largest_component_fraction": max(frac),
        "mean_measured_mean_degree": mean(kmeas),
        "std_measured_mean_degree": std(kmeas),
    }


def sweep(n: int, k_grid: List[float], *, n_seeds: int = 10,
          seed_base: int = 0) -> List[Dict[str, Any]]:
    """Run the full <k>-grid; one summary dict per <k>."""
    return [run_many_seeds(n, k, n_seeds=n_seeds, seed_base=seed_base) for k in k_grid]
