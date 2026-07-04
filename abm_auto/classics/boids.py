"""Boids flocking (Reynolds 1987) — a faithful agent-based reproduction.

Source: Reynolds, C. W. (1987), "Flocks, herds and schools: A distributed
behavioral model", Computer Graphics (SIGGRAPH '87 Proceedings) 21(4):25-34.
doi:10.1145/37402.37406.

Distinct from Vicsek (1995): a Boid carries a full velocity *vector* (not just a
heading angle at constant speed), and its motion is governed by THREE local
steering rules combined each tick, not a single align-with-noise rule:

  * SEPARATION — steer to avoid crowding very-close neighbours. For each neighbour
    within a (small) separation radius, add a repulsion vector pointing away from it,
    weighted by 1/distance so the nearest neighbours dominate.
  * ALIGNMENT — steer toward the average velocity of neighbours within the
    perception radius (match the local flock's heading and speed).
  * COHESION — steer toward the centre of mass of neighbours within the perception
    radius (move toward the local flock).

Each ``BoidAgent`` lives in an L x L PERIODIC box and carries a position (x, y) and a
velocity (vx, vy). Every tick (a SYNCHRONOUS update — all steering computed from one
start-of-tick snapshot, then all boids move):

    a_i      = w_sep * separation_i + w_align * alignment_i + w_coh * cohesion_i
    v_i(t+1) = clamp_speed( v_i(t) + a_i,  vmin, vmax )
    p_i(t+1) = ( p_i(t) + v_i(t+1) ) mod L

The speed is clamped into [vmin, vmax] (boids never freeze and never run away), and
the alignment / cohesion vectors are normalised to a target speed before the steering
difference is taken (the standard "steer = desired - current" formulation), so the
three rules combine on comparable scales.

Order parameter (the locked grading metric, shared with Vicsek):
    phi = | (1/N) * sum_i  v_i / |v_i| |   in [0, 1].
phi ~ 1 is a coherent flock with a common heading; phi ~ 0 is incoherent motion.
Cohesion is measured by the mean NEAREST-NEIGHBOUR distance (periodic): it stays
bounded if the flock holds together, and would grow without bound if it dispersed.

ALIGNMENT-OFF control (for the locked P2): the *same* model with ``w_align = 0`` —
separation + cohesion only. Everything else (N, box, radii, the other two weights,
speed clamp, seeds) is identical; only the alignment rule is removed. This is the
fair control that isolates "alignment is what creates the common heading".

Built on the neutral platform (``abm_auto._platform``): each boid is a ``BoidAgent``
carrying its own (x, y, vx, vy); ``BoidsModel`` drives the synchronous three-rule
steering + move over the ``AgentSet`` roster and records (via a ``DataCollector``) the
per-tick order parameter phi and mean nearest-neighbour distance. Neighbour lookup uses
a periodic cell list (bucket grid of cell size >= perception radius) so a tick is O(N)
rather than O(N^2); the result is identical to the brute-force all-pairs computation.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- periodic geometry helpers ------------------------------------------------

def periodic_delta(a: float, b: float, L: float) -> float:
    """Minimum-image signed displacement a-b on a periodic line of length L, in
    (-L/2, L/2]."""
    d = a - b
    d -= L * round(d / L)
    return d


def periodic_dist2(x1: float, y1: float, x2: float, y2: float, L: float) -> float:
    """Squared minimum-image (toroidal) distance between two points in an L x L box."""
    dx = periodic_delta(x1, x2, L)
    dy = periodic_delta(y1, y2, L)
    return dx * dx + dy * dy


# -- Agent --------------------------------------------------------------------

class BoidAgent(Agent):
    """One boid: position (x, y) and velocity (vx, vy).

    The Reynolds tick is a model-level synchronous update (all steering from one
    snapshot, then all move), so the per-agent ``step`` is intentionally a no-op; the
    ``_next_vx`` / ``_next_vy`` fields stage the velocity computed this tick before the
    model commits the moves.
    """

    def __init__(self, agent_id: int, model: "BoidsModel", *,
                 x: float, y: float, vx: float, vy: float) -> None:
        super().__init__(agent_id, model)
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self._next_vx = vx
        self._next_vy = vy

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        """The Reynolds tick (steer from a snapshot, then move) is a model-level
        synchronous update, not an autonomous single-agent step, so this is a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class BoidsModel(AgentModel):
    """Drives the Reynolds (1987) three-rule boids dynamics.

    Construct with N, box size L, perception radius ``r``, separation radius
    ``r_sep``, the three rule weights, the speed clamp [vmin, vmax], and a seed.
    Set ``align`` False for the alignment-OFF control (separation + cohesion only).
    ``run(n_ticks)`` advances the synchronous steer+move update and records the
    per-tick order parameter phi and mean nearest-neighbour distance.
    """

    def __init__(self, n: int = 200, *, L: float = 50.0, r: float = 7.0,
                 r_sep: float = 2.0, w_sep: float = 1.5, w_align: float = 1.0,
                 w_coh: float = 1.0, vmin: float = 0.5, vmax: float = 1.0,
                 align: bool = True, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if L <= 0 or r <= 0 or r_sep <= 0:
            raise ValueError(f"need L>0, r>0, r_sep>0 (got L={L}, r={r}, r_sep={r_sep})")
        if vmin < 0 or vmax <= 0 or vmin > vmax:
            raise ValueError(f"need 0<=vmin<=vmax, vmax>0 (got vmin={vmin}, vmax={vmax})")
        if r_sep > r:
            raise ValueError(f"need r_sep <= r (got r_sep={r_sep}, r={r})")
        self.seed_value = seed
        self.n = n
        self.L = float(L)
        self.r = float(r)
        self.r2 = self.r * self.r
        self.r_sep = float(r_sep)
        self.r_sep2 = self.r_sep * self.r_sep
        self.w_sep = float(w_sep)
        # The control removes ONLY the alignment rule: w_align is forced to 0.
        self.align = bool(align)
        self.w_align = float(w_align) if self.align else 0.0
        self.w_coh = float(w_coh)
        self.vmin = float(vmin)
        self.vmax = float(vmax)
        self.density = n / (self.L * self.L)

        # Periodic cell list: square cells of side >= r so a boid's r-neighbours all
        # lie in its own cell or the 8 adjacent ones (with wrap). n_cells>=1 (degenerate
        # small box falls back to one cell == brute force, still correct).
        self.n_cells = max(1, int(math.floor(self.L / self.r)))
        self.cell_size = self.L / self.n_cells

        # Random initial state: positions uniform in the box; velocities uniform in
        # direction with a magnitude inside the speed clamp. (Seed-dependent; this is
        # the only randomness in the whole run — the dynamics are otherwise
        # deterministic given the seeded initial draw.)
        self.agent_list: List[BoidAgent] = []
        for i in range(n):
            x = self.rng.uniform(0.0, self.L)
            y = self.rng.uniform(0.0, self.L)
            ang = self.rng.uniform(0.0, 2.0 * math.pi)
            spd = self.rng.uniform(self.vmin, self.vmax)
            agent = BoidAgent(i, self, x=x, y=y,
                              vx=spd * math.cos(ang), vy=spd * math.sin(ang))
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "phi": lambda m: m.order_parameter(),
            "mean_nn": lambda m: m.mean_nearest_neighbour_distance(),
        })

    # -- metrics --
    def order_parameter(self) -> float:
        """phi = | (1/N) sum_i v_i/|v_i| |, the coherence of headings, in [0, 1].

        A boid with zero speed (cannot happen with vmin>0, but guarded) contributes
        no direction."""
        if self.n == 0:
            return 0.0
        sx = sy = 0.0
        for a in self.agent_list:
            speed = math.hypot(a.vx, a.vy)
            if speed > 0.0:
                sx += a.vx / speed
                sy += a.vy / speed
        return math.hypot(sx, sy) / self.n

    def mean_nearest_neighbour_distance(self) -> float:
        """Mean over boids of the periodic distance to the single nearest other boid.

        Bounded if the flock holds together; grows toward the box-diagonal scale if the
        boids disperse uniformly. Uses the cell list (== brute force) for O(N)."""
        if self.n <= 1:
            return 0.0
        cells = self._build_cells()
        total = 0.0
        for a in self.agent_list:
            total += math.sqrt(self._nearest_neighbour_dist2(a, cells))
        return total / self.n

    # -- neighbour lookup (periodic cell list) --
    def _cell_of(self, x: float, y: float) -> Tuple[int, int]:
        cx = int(x / self.cell_size) % self.n_cells
        cy = int(y / self.cell_size) % self.n_cells
        return cx, cy

    def _build_cells(self) -> Dict[Tuple[int, int], List[BoidAgent]]:
        cells: Dict[Tuple[int, int], List[BoidAgent]] = {}
        for a in self.agent_list:
            key = self._cell_of(a.x, a.y)
            cells.setdefault(key, []).append(a)
        return cells

    def _neighbours(self, a: BoidAgent,
                    cells: Dict[Tuple[int, int], List[BoidAgent]]) -> List[BoidAgent]:
        """All OTHER boids within the perception radius r of a (periodic distance).
        Scans a's cell and its 8 neighbours (with wrap); cell side >= r guarantees no
        in-range neighbour is missed."""
        cx, cy = self._cell_of(a.x, a.y)
        nc = self.n_cells
        out: List[BoidAgent] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                key = ((cx + dx) % nc, (cy + dy) % nc)
                bucket = cells.get(key)
                if not bucket:
                    continue
                for b in bucket:
                    if b is a:
                        continue
                    if periodic_dist2(a.x, a.y, b.x, b.y, self.L) <= self.r2:
                        out.append(b)
        return out

    def _neighbours_bruteforce(self, a: BoidAgent) -> List[BoidAgent]:
        """O(N) reference neighbour list (all pairs, periodic distance). Used only to
        validate the cell-list path in tests; the model uses the cell list."""
        return [b for b in self.agent_list
                if b is not a and periodic_dist2(a.x, a.y, b.x, b.y, self.L) <= self.r2]

    def _nearest_neighbour_dist2(self, a: BoidAgent,
                                 cells: Dict[Tuple[int, int], List[BoidAgent]]) -> float:
        """Squared periodic distance to the single nearest OTHER boid. Searches an
        expanding ring of cells until the nearest found is provably closer than any
        boid in an unsearched ring; falls back to a full scan in the degenerate
        all-in-one-cell case."""
        cx, cy = self._cell_of(a.x, a.y)
        nc = self.n_cells
        best = float("inf")
        max_ring = (nc // 2) + 1
        for ring in range(0, max_ring + 1):
            # cells whose Chebyshev distance from (cx,cy) == ring
            found_any = False
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    if max(abs(dx), abs(dy)) != ring:
                        continue
                    key = ((cx + dx) % nc, (cy + dy) % nc)
                    bucket = cells.get(key)
                    if not bucket:
                        continue
                    for b in bucket:
                        if b is a:
                            continue
                        d2 = periodic_dist2(a.x, a.y, b.x, b.y, self.L)
                        if d2 < best:
                            best = d2
                        found_any = True
            # Once we have a candidate, any boid in ring >= k is at least
            # (k-1)*cell_size away; stop when that lower bound exceeds the best found.
            if best < float("inf"):
                lower_bound = (ring) * self.cell_size  # next ring's min distance
                if lower_bound * lower_bound > best:
                    break
            _ = found_any
        if best == float("inf"):
            # degenerate (e.g. n_cells==1): brute force
            for b in self.agent_list:
                if b is a:
                    continue
                d2 = periodic_dist2(a.x, a.y, b.x, b.y, self.L)
                if d2 < best:
                    best = d2
        return best if best != float("inf") else 0.0

    # -- steering rules --
    @staticmethod
    def _limit(vx: float, vy: float, maxmag: float) -> Tuple[float, float]:
        """Scale (vx, vy) down to magnitude maxmag if it exceeds it (else unchanged)."""
        mag = math.hypot(vx, vy)
        if mag > maxmag and mag > 0.0:
            s = maxmag / mag
            return vx * s, vy * s
        return vx, vy

    def _steer_toward(self, a: BoidAgent, dvx: float, dvy: float,
                      target_speed: float) -> Tuple[float, float]:
        """Reynolds 'steer = desired - current': normalise the desired direction
        (dvx, dvy) to target_speed, subtract the boid's current velocity, and clamp the
        steering force to a maximum. Returns a zero vector for a zero desired direction."""
        mag = math.hypot(dvx, dvy)
        if mag == 0.0:
            return 0.0, 0.0
        desired_x = dvx / mag * target_speed
        desired_y = dvy / mag * target_speed
        sx = desired_x - a.vx
        sy = desired_y - a.vy
        return self._limit(sx, sy, self.max_force)

    @property
    def max_force(self) -> float:
        """Per-rule steering-force cap (a fraction of the speed range), keeping the
        three rules on a comparable scale and the turning smooth."""
        return 0.5 * self.vmax

    def _steering(self, a: BoidAgent,
                  neigh: Sequence[BoidAgent]) -> Tuple[float, float]:
        """Combine the three Reynolds rules for boid ``a`` given its perception-radius
        neighbours, returning the acceleration (steering) vector to add to its velocity.

        SEPARATION uses only the close neighbours (within r_sep), with 1/dist weighting
        so the nearest dominate. ALIGNMENT and COHESION use all perception neighbours.
        Alignment is gated by ``self.align`` (w_align is already 0 in the control, but
        skipping the work keeps the control's velocity bit-identical to dropping the
        term)."""
        ax = ay = 0.0

        # SEPARATION: steer away from close neighbours (1/dist weighting).
        sep_x = sep_y = 0.0
        n_close = 0
        for b in neigh:
            dx = periodic_delta(a.x, b.x, self.L)
            dy = periodic_delta(a.y, b.y, self.L)
            d2 = dx * dx + dy * dy
            if d2 <= self.r_sep2 and d2 > 0.0:
                d = math.sqrt(d2)
                sep_x += dx / d / d   # away from b, weighted 1/d
                sep_y += dy / d / d
                n_close += 1
        if n_close > 0:
            sx, sy = self._steer_toward(a, sep_x, sep_y, self.vmax)
            ax += self.w_sep * sx
            ay += self.w_sep * sy

        if not neigh:
            return ax, ay

        # ALIGNMENT: steer toward neighbours' average velocity.
        if self.align and self.w_align != 0.0:
            avx = sum(b.vx for b in neigh) / len(neigh)
            avy = sum(b.vy for b in neigh) / len(neigh)
            alx, aly = self._steer_toward(a, avx, avy, self.vmax)
            ax += self.w_align * alx
            ay += self.w_align * aly

        # COHESION: steer toward neighbours' centre of mass (periodic-aware: average
        # the minimum-image offsets, which handles wrap correctly).
        cox = coy = 0.0
        for b in neigh:
            cox += periodic_delta(b.x, a.x, self.L)
            coy += periodic_delta(b.y, a.y, self.L)
        cox /= len(neigh)
        coy /= len(neigh)
        chx, chy = self._steer_toward(a, cox, coy, self.vmax)
        ax += self.w_coh * chx
        ay += self.w_coh * chy

        return ax, ay

    # -- tick --
    def step(self) -> None:
        """One synchronous Reynolds tick.

        (1) From the start-of-tick snapshot, every boid's new velocity = its current
            velocity + the combined three-rule steering, clamped into [vmin, vmax].
        (2) Then every boid moves by its NEW velocity and wraps into [0, L). Velocities
            are staged in ``_next_vx/_next_vy`` so all steering reads one consistent
            snapshot (synchronous update)."""
        cells = self._build_cells()
        for a in self.agent_list:
            neigh = self._neighbours(a, cells)
            ax, ay = self._steering(a, neigh)
            nvx = a.vx + ax
            nvy = a.vy + ay
            # clamp speed into [vmin, vmax]
            speed = math.hypot(nvx, nvy)
            if speed == 0.0:
                # keep the old heading at min speed (cannot persist a zero velocity)
                old = math.hypot(a.vx, a.vy)
                if old > 0.0:
                    nvx = a.vx / old * self.vmin
                    nvy = a.vy / old * self.vmin
                else:
                    nvx, nvy = self.vmin, 0.0
            elif speed > self.vmax:
                s = self.vmax / speed
                nvx, nvy = nvx * s, nvy * s
            elif speed < self.vmin:
                s = self.vmin / speed
                nvx, nvy = nvx * s, nvy * s
            a._next_vx = nvx
            a._next_vy = nvy
        for a in self.agent_list:
            a.vx = a._next_vx
            a.vy = a._next_vy
            a.x = (a.x + a.vx) % self.L
            a.y = (a.y + a.vy) % self.L
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_ticks: int = 400, *, measure_last: int = 100) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_ticks`` synchronous Reynolds ticks; return the run summary.

        ``measure_last`` is the trailing window over which the steady-state order
        parameter and mean nearest-neighbour distance are averaged (the transient is the
        leading n_ticks - measure_last ticks). Returns steady + final phi, steady + final
        mean-NN distance, and the full per-tick series of both.
        """
        if measure_last <= 0 or measure_last > n_ticks + 1:
            raise ValueError(
                f"measure_last must be in [1, n_ticks+1] (got {measure_last}, n_ticks={n_ticks})")
        self.reporter.collect(self)              # t=0 baseline
        for _ in range(n_ticks):
            self.step()
        phi_series = self.reporter.series("phi")
        nn_series = self.reporter.series("mean_nn")
        return {
            "n": self.n,
            "L": self.L,
            "r": self.r,
            "r_sep": self.r_sep,
            "w_sep": self.w_sep,
            "w_align": self.w_align,
            "w_coh": self.w_coh,
            "vmin": self.vmin,
            "vmax": self.vmax,
            "align": self.align,
            "density": self.density,
            "seed": self.seed_value,
            "n_ticks": n_ticks,
            "measure_last": measure_last,
            "steady_phi": tail_mean(phi_series, window=measure_last),
            "final_phi": phi_series[-1],
            "steady_mean_nn": tail_mean(nn_series, window=measure_last),
            "final_mean_nn": nn_series[-1],
            "phi_series": phi_series,
            "mean_nn_series": nn_series,
        }


# -- summary helpers ----------------------------------------------------------

def tail_mean(series: Sequence[float], *, window: int = 100) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of a series (or the whole
    series if shorter). Averaging the tail smooths finite-N jitter and discards the
    transient before measurement."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(n: int = 200, *, L: float = 50.0, r: float = 7.0, r_sep: float = 2.0,
               w_sep: float = 1.5, w_align: float = 1.0, w_coh: float = 1.0,
               vmin: float = 0.5, vmax: float = 1.0, align: bool = True, seed: int = 0,
               n_ticks: int = 400, measure_last: int = 100) -> Dict[str, Any]:
    """One boids run at a given (align, seed) and the fixed rule parameters."""
    return BoidsModel(n, L=L, r=r, r_sep=r_sep, w_sep=w_sep, w_align=w_align,
                      w_coh=w_coh, vmin=vmin, vmax=vmax, align=align, seed=seed).run(
        n_ticks, measure_last=measure_last)


def run_many_seeds(n: int = 200, *, L: float = 50.0, r: float = 7.0, r_sep: float = 2.0,
                   w_sep: float = 1.5, w_align: float = 1.0, w_coh: float = 1.0,
                   vmin: float = 0.5, vmax: float = 1.0, align: bool = True,
                   n_seeds: int = 5, seed_base: int = 0, n_ticks: int = 400,
                   measure_last: int = 100) -> Dict[str, Any]:
    """Run ``n_seeds`` boids runs (seed ``seed_base + i``) at fixed parameters and
    summarise the steady order parameter phi and mean nearest-neighbour distance across
    seeds (mean + spread).

    Returns the per-seed steady phi + steady mean-NN values, their mean / std / min /
    max, and one representative trajectory (first seed) of both series for inspection.
    """
    runs = [run_single(n, L=L, r=r, r_sep=r_sep, w_sep=w_sep, w_align=w_align,
                       w_coh=w_coh, vmin=vmin, vmax=vmax, align=align,
                       seed=seed_base + i, n_ticks=n_ticks, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_phi = [rr["steady_phi"] for rr in runs]
    per_seed_final_phi = [rr["final_phi"] for rr in runs]
    per_seed_nn = [rr["steady_mean_nn"] for rr in runs]
    per_seed_final_nn = [rr["final_mean_nn"] for rr in runs]
    mean_phi = sum(per_seed_phi) / n_seeds
    var_phi = sum((s - mean_phi) ** 2 for s in per_seed_phi) / n_seeds
    mean_nn = sum(per_seed_nn) / n_seeds
    var_nn = sum((s - mean_nn) ** 2 for s in per_seed_nn) / n_seeds
    return {
        "n": n, "L": L, "r": r, "r_sep": r_sep,
        "w_sep": w_sep, "w_align": (w_align if align else 0.0), "w_coh": w_coh,
        "vmin": vmin, "vmax": vmax, "align": align,
        "density": n / (L * L),
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_ticks": n_ticks, "measure_last": measure_last,
        "per_seed_steady_phi": per_seed_phi,
        "per_seed_final_phi": per_seed_final_phi,
        "per_seed_steady_mean_nn": per_seed_nn,
        "per_seed_final_mean_nn": per_seed_final_nn,
        "mean_steady_phi": mean_phi,
        "var_steady_phi": var_phi,
        "std_steady_phi": var_phi ** 0.5,
        "min_steady_phi": min(per_seed_phi),
        "max_steady_phi": max(per_seed_phi),
        "mean_steady_nn": mean_nn,
        "std_steady_nn": var_nn ** 0.5,
        "min_steady_nn": min(per_seed_nn),
        "max_steady_nn": max(per_seed_nn),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_phi_series": runs[0]["phi_series"],
        "example_nn_series": runs[0]["mean_nn_series"],
    }
