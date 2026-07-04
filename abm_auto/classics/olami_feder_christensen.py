"""Olami-Feder-Christensen earthquakes (Olami, Feder & Christensen 1992) — a
faithful reproduction of self-organized criticality (SOC) in a driven,
nonconservative cellular automaton.

Source: Olami, Z., Feder, H. J. S. & Christensen, K. (1992), "Self-organized
criticality in a continuous, nonconservative cellular automaton modeling
earthquakes", Phys. Rev. Lett. 68(8):1244-1247. doi:10.1103/PhysRevLett.68.1244.

FRAMING DISCLOSURE — this is a DRIVEN-THRESHOLD CELLULAR AUTOMATON (a model of
self-organized criticality), **NOT autonomous-agent-stepping**. There is no agent
that perceives neighbours and chooses an action each tick; instead a uniform
external "tectonic" drive loads a continuous force field until the most-loaded
site reaches threshold, and the resulting topple/redistribution cascade is a
deterministic relaxation rule. We still build it on the neutral ``abm_auto._platform``
floor — each lattice site is an ``Agent`` (a force-carrying cell) held in the model's
``AgentSet`` roster — but the dynamics live at the model level (drive + avalanche),
exactly as the boids/forest-fire CA reproductions in this suite do, and the per-cell
``step`` is intentionally a no-op. We disclose this so the reproduction is not
over-claimed as "agent-based" in the multi-agent-decision sense.

Mechanism (the Olami-Feder-Christensen rule, zero-velocity driving limit):

  * STATE — an L x L lattice of continuous "forces" F_i, initialised ~ U[0, 1).
  * DRIVE — add a single uniform increment to ALL sites so the maximum site
    reaches the threshold F_th = 1.0:  delta = F_th - max_i(F_i); F_i += delta
    everywhere. This is the slow-driving (zero loading-velocity) limit: the system
    is loaded just up to the next instability, with no avalanche running during loading.
  * RELAX (avalanche) — any site with F >= F_th topples: it resets to 0 and adds
    alpha * F_old to EACH of its 4 von-Neumann (nearest) neighbours. OPEN boundary:
    force sent toward an off-lattice neighbour (across an edge / out of a corner) is
    LOST. A topple can push a neighbour over threshold, so toppling cascades until no
    site is >= F_th. ``alpha`` is the redistribution/conservation parameter,
    alpha <= 0.25; alpha = 0.25 is the conservative case (a topple gives away 4*alpha
    = 1.0 of the released force, an interior site loses nothing), alpha < 0.25 is
    dissipative (an interior topple loses a fraction 1 - 4*alpha of the released force).
  * EVENT SIZE — s = number of topplings triggered by one drive step (one site may
    topple more than once within an avalanche; each toppling counts once). s >= 1 for
    every drive (the driven site always topples at least once). The event-size
    distribution over many drives is the seismic moment / Gutenberg-Richter analogue.

The avalanche is implemented with an explicit relaxation QUEUE (a site is enqueued
when it first crosses threshold, re-checked when popped), so the cost is O(#topplings)
rather than a full-lattice rescan per micro-step; the drive step is O(L^2) (find the
max, add the increment). A transient is discarded so the system reaches its
self-organized stationary critical state before events are collected.

Order parameters / observables (the locked grading metric, see PREDICTIONS-locked.md):
the per-drive event-size series s_1, s_2, ... and, from it, the mean, max, median over
nonzero events, the number of decades the size range spans, and a coarse logarithmic
histogram. Determinism: the whole run is fixed by the seed (the only randomness is the
seeded initial force draw; the drive + avalanche rule is otherwise deterministic).
"""
from __future__ import annotations

import math
from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class SiteAgent(Agent):
    """One lattice cell: a continuous force ``f`` at integer grid coordinate (r, c).

    The Olami-Feder-Christensen dynamics (uniform drive, then a threshold-driven
    topple/redistribution cascade) are a model-level relaxation, not an autonomous
    per-site decision, so the per-agent ``step`` is intentionally a no-op; the force
    field lives on a flat array on the model for O(1) drive + topple, and these agents
    are the platform-roster view of the same field."""

    def __init__(self, agent_id: int, model: "OFCModel", *,
                 row: int, col: int) -> None:
        super().__init__(agent_id, model)
        self.row = row
        self.col = col

    @property
    def f(self) -> float:
        """This site's current force (read through to the model's force field)."""
        return self.model.force[self.id]

    def step(self) -> None:  # pragma: no cover - the dynamics live on the model
        """OFC is a driven-CA relaxation at the model level (drive then avalanche
        cascade), not an autonomous single-site step, so this is a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class OFCModel(AgentModel):
    """Drives the Olami-Feder-Christensen (1992) earthquake CA.

    Construct with lattice side ``L``, the redistribution parameter ``alpha``
    (<= 0.25), the threshold ``f_th`` (1.0), and a seed. The force field is a flat
    length-L*L array indexed ``row * L + col``; ``SiteAgent``s are the platform-roster
    view of that field. ``run(n_events, transient)`` discards ``transient`` drive
    steps to reach the stationary critical state, then records the event size of the
    next ``n_events`` drives.
    """

    def __init__(self, L: int = 50, *, alpha: float = 0.2, f_th: float = 1.0,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if L <= 1:
            raise ValueError(f"need L > 1 (got {L})")
        if not (0.0 < alpha <= 0.25):
            raise ValueError(f"need 0 < alpha <= 0.25 (got {alpha})")
        if f_th <= 0.0:
            raise ValueError(f"need f_th > 0 (got {f_th})")
        self.seed_value = seed
        self.L = int(L)
        self.alpha = float(alpha)
        self.f_th = float(f_th)
        self.n_sites = self.L * self.L

        # Continuous force field, F_i ~ U[0, f_th); flat, indexed row*L + col.
        self.force: List[float] = [self.rng.uniform(0.0, self.f_th)
                                   for _ in range(self.n_sites)]

        # Precompute the von-Neumann neighbour index list per site (open boundary:
        # an off-lattice neighbour is simply absent, so that share of the force is lost).
        self._neighbours: List[Tuple[int, ...]] = [self._compute_neighbours(i)
                                                   for i in range(self.n_sites)]

        # Platform-roster view of the same field (one SiteAgent per cell).
        self.agent_list: List[SiteAgent] = []
        for i in range(self.n_sites):
            agent = SiteAgent(i, self, row=i // self.L, col=i % self.L)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "event_size": lambda m: m.last_event_size,
        })
        self.last_event_size = 0

    # -- geometry --
    def idx(self, row: int, col: int) -> int:
        """Flat index of grid cell (row, col)."""
        return row * self.L + col

    def _compute_neighbours(self, i: int) -> Tuple[int, ...]:
        """Flat indices of the (up to 4) von-Neumann neighbours of site ``i``.

        OPEN boundary: a neighbour that would fall off an edge or out of a corner is
        omitted, so an interior site has 4 neighbours, an edge site 3, a corner site 2;
        the missing shares of redistributed force are lost from the lattice."""
        r, c = i // self.L, i % self.L
        out: List[int] = []
        if r > 0:
            out.append(self.idx(r - 1, c))
        if r < self.L - 1:
            out.append(self.idx(r + 1, c))
        if c > 0:
            out.append(self.idx(r, c - 1))
        if c < self.L - 1:
            out.append(self.idx(r, c + 1))
        return tuple(out)

    # -- the OFC micro-rules --
    def drive_to_threshold(self) -> float:
        """Slow-driving step: add a uniform increment to EVERY site so the maximum
        site reaches threshold. Returns the increment ``delta`` added. After this,
        max(force) == f_th exactly (the just-critical site is the avalanche seed)."""
        m = max(self.force)
        delta = self.f_th - m
        if delta < 0.0:
            delta = 0.0   # already at/over threshold (defensive; shouldn't happen post-relax)
        for i in range(self.n_sites):
            self.force[i] += delta
        return delta

    def relax(self) -> int:
        """Run the avalanche from the current (just-driven) field to completion and
        return the event size = number of topplings.

        Toppling rule: a site with F >= f_th resets to 0 and adds alpha * F_old to each
        present neighbour; force toward an absent (off-lattice) neighbour is lost.
        Uses an explicit relaxation queue (cost O(#topplings)): a site is enqueued the
        first time it crosses threshold and re-checked when popped (it may have been
        pushed further over by another topple in the meantime), so a site can topple
        more than once, each counted. Continues until the queue drains with no site
        >= threshold."""
        f_th = self.f_th
        alpha = self.alpha
        force = self.force
        neighbours = self._neighbours

        queue: deque[int] = deque(i for i in range(self.n_sites) if force[i] >= f_th)
        in_queue = [force[i] >= f_th for i in range(self.n_sites)]
        topples = 0

        while queue:
            i = queue.popleft()
            in_queue[i] = False
            if force[i] < f_th:
                continue
            # topple site i
            released = force[i]
            force[i] = 0.0
            topples += 1
            share = alpha * released
            for j in neighbours[i]:
                force[j] += share
                if force[j] >= f_th and not in_queue[j]:
                    in_queue[j] = True
                    queue.append(j)
        return topples

    def drive_step(self) -> int:
        """One full Olami-Feder-Christensen event: drive the field up to threshold,
        then relax the triggered avalanche to completion. Returns the event size."""
        self.drive_to_threshold()
        s = self.relax()
        self.last_event_size = s
        return s

    # -- platform tick --
    def step(self) -> None:
        """One platform tick == one OFC drive+avalanche event; records the event size."""
        self.drive_step()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    # -- experiment driver --
    def run(self, n_events: int = 10000, *, transient: int = 5000) -> Dict[str, Any]:  # type: ignore[override]
        """Discard a ``transient`` of drive steps (to reach the self-organized
        stationary critical state), then collect the event size of the next
        ``n_events`` drives and summarise the distribution.

        Returns the full post-transient event-size series, the mean / max /
        median-over-nonzero, the number of decades the size range spans, a coarse
        log-spaced histogram of event sizes, and the config. The series is exactly
        ``n_events`` long; the transient events are NOT recorded.
        """
        if n_events <= 0:
            raise ValueError(f"need n_events > 0 (got {n_events})")
        if transient < 0:
            raise ValueError(f"need transient >= 0 (got {transient})")

        # transient: drive without recording (reach the stationary state)
        for _ in range(transient):
            self.drive_step()

        sizes: List[int] = []
        for _ in range(n_events):
            sizes.append(self.drive_step())

        return _summarise_sizes(sizes, extra={
            "L": self.L, "alpha": self.alpha, "f_th": self.f_th,
            "seed": self.seed_value, "n_events": n_events, "transient": transient,
        })


# -- summary helpers ----------------------------------------------------------

def log_histogram(sizes: Sequence[int], *, bins_per_decade: int = 4) -> Dict[str, List[float]]:
    """A coarse log-spaced histogram of (positive) event sizes.

    Bins are spaced ``bins_per_decade`` per decade in log10(size); returns the bin
    left edges (in size units) and the count in each bin. Sizes are all >= 1 for OFC
    (every drive topples >= 1 site), so there is no zero-size bin to special-case."""
    pos = [s for s in sizes if s >= 1]
    if not pos:
        return {"bin_left_edges": [], "counts": []}
    lo = 0.0                                  # log10(1)
    hi = math.log10(max(pos))
    n_bins = max(1, int(math.ceil((hi - lo) * bins_per_decade)) + 1)
    edges = [10.0 ** (lo + k / bins_per_decade) for k in range(n_bins + 1)]
    counts = [0] * n_bins
    for s in pos:
        # bin by log10(s) * bins_per_decade, clamped into range
        k = int(math.floor(math.log10(s) * bins_per_decade))
        if k < 0:
            k = 0
        if k >= n_bins:
            k = n_bins - 1
        counts[k] += 1
    return {"bin_left_edges": edges[:n_bins], "counts": [float(c) for c in counts]}


def _median(values: Sequence[float]) -> float:
    """Plain median of a non-empty sequence (mean of the two central order statistics
    for an even count)."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0


def _summarise_sizes(sizes: Sequence[int], *, extra: Optional[Dict[str, Any]] = None
                     ) -> Dict[str, Any]:
    """Summarise an event-size series: mean / max / min, median over nonzero events,
    decades spanned (log10(max) - log10(min nonzero)), a coarse log histogram, and the
    raw series. ``extra`` (config) is merged into the result."""
    sizes = list(sizes)
    n = len(sizes)
    nonzero = [s for s in sizes if s > 0]
    max_s = max(sizes) if sizes else 0
    min_nonzero = min(nonzero) if nonzero else 0
    mean_s = sum(sizes) / n if n else 0.0
    median_nonzero = _median(nonzero) if nonzero else 0.0
    if max_s >= 1 and min_nonzero >= 1:
        decades = math.log10(max_s) - math.log10(min_nonzero)
    else:
        decades = 0.0
    out: Dict[str, Any] = {
        "n_events": n,
        "event_sizes": sizes,
        "mean_event_size": mean_s,
        "max_event_size": max_s,
        "min_nonzero_event_size": min_nonzero,
        "median_nonzero_event_size": median_nonzero,
        "decades_spanned": decades,
        "max_over_median_nonzero": (max_s / median_nonzero) if median_nonzero > 0 else float("inf"),
        "histogram": log_histogram(sizes),
        "n_nonzero": len(nonzero),
    }
    if extra:
        out.update(extra)
    return out


def run_single(L: int = 50, *, alpha: float = 0.2, f_th: float = 1.0, seed: int = 0,
               n_events: int = 10000, transient: int = 5000) -> Dict[str, Any]:
    """One OFC run at a given (alpha, seed): discard ``transient`` drives, then collect
    + summarise ``n_events`` event sizes."""
    return OFCModel(L, alpha=alpha, f_th=f_th, seed=seed).run(
        n_events, transient=transient)


def run_many_seeds(L: int = 50, *, alpha: float = 0.2, f_th: float = 1.0,
                   n_seeds: int = 3, seed_base: int = 0, n_events: int = 10000,
                   transient: int = 5000) -> Dict[str, Any]:
    """Run ``n_seeds`` OFC runs (seed ``seed_base + i``) at fixed (L, alpha) and
    summarise the event-size distribution across seeds.

    Returns the per-seed summary stats (mean / max / median-nonzero / decades), their
    across-seed mean, a pooled summary over all events from all seeds, and one
    representative event-size series (first seed) for inspection.
    """
    runs = [run_single(L, alpha=alpha, f_th=f_th, seed=seed_base + i,
                       n_events=n_events, transient=transient)
            for i in range(n_seeds)]
    per_seed_mean = [r["mean_event_size"] for r in runs]
    per_seed_max = [r["max_event_size"] for r in runs]
    per_seed_median = [r["median_nonzero_event_size"] for r in runs]
    per_seed_decades = [r["decades_spanned"] for r in runs]

    pooled_sizes: List[int] = []
    for r in runs:
        pooled_sizes.extend(r["event_sizes"])
    pooled = _summarise_sizes(pooled_sizes)

    mean_of_means = sum(per_seed_mean) / n_seeds
    var_mean = sum((m - mean_of_means) ** 2 for m in per_seed_mean) / n_seeds
    return {
        "L": L, "alpha": alpha, "f_th": f_th,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_events": n_events, "transient": transient,
        "per_seed_mean_event_size": per_seed_mean,
        "per_seed_max_event_size": per_seed_max,
        "per_seed_median_nonzero": per_seed_median,
        "per_seed_decades_spanned": per_seed_decades,
        "mean_event_size": mean_of_means,
        "std_event_size": var_mean ** 0.5,
        "min_mean_event_size": min(per_seed_mean),
        "max_mean_event_size": max(per_seed_mean),
        "pooled_mean_event_size": pooled["mean_event_size"],
        "pooled_max_event_size": pooled["max_event_size"],
        "pooled_median_nonzero": pooled["median_nonzero_event_size"],
        "pooled_decades_spanned": pooled["decades_spanned"],
        "pooled_max_over_median": pooled["max_over_median_nonzero"],
        "pooled_histogram": pooled["histogram"],
        # one representative event-size series (first seed) for inspection.
        "example_event_sizes": runs[0]["event_sizes"],
    }
