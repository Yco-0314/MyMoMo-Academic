"""Huth & Wissel fish schooling (1992) — a faithful agent-based reproduction.

Source: Huth, A. & Wissel, C. (1992), "The simulation of the movement of fish
schools", Journal of Theoretical Biology 156(3):365-385.
doi:10.1016/S0022-5193(05)80681-2.

Framing: genuine-agent (zonal SPP fish, disclosed). This is NOT a grid CA and NOT the
single-alignment Vicsek rule. Each individual is an autonomous self-propelled fish with a
heading and a bounded turning rate, integrating the standard nested behavioural zones
(repulsion / parallel-orientation / attraction) every step, in continuous, UNBOUNDED 2D.

The locked A/B contrast (the distinctness of this reproduction — see PREDICTIONS-locked.md):
the INTEGRATION RULE for combining neighbour influences, with ALL zonal forces held
identical between the two arms:

  * AVERAGING rule ("averaging" / all-neighbours): the fish AVERAGES the desired directions
    induced by ALL relevant neighbours — sum the in-orientation-zone neighbour headings and
    the unit vectors toward the in-attraction-zone neighbours, then normalise. (This is the
    classic multi-neighbour zonal integration used by boids/couzin.)
  * DECISION rule ("decision" / one-neighbour): the fish PICKS ONE neighbour — the
    highest-priority relevant neighbour (the NEAREST orientation-or-attraction neighbour) —
    and follows ONLY the desired direction that single neighbour induces (align to it if it
    is in the orientation zone, else steer toward it). This is Huth & Wissel's "decision"
    integration: react to the most-relevant single fish rather than averaging the crowd.

Both arms share the SAME zonal forces: the repulsion override is byte-identical (collision
avoidance is reflexive in both), the orientation and attraction radii, speed, bounded turn,
and noise are identical, and both arms compute the desired direction from the SAME
start-of-step snapshot. ONLY the integration of the orientation+attraction influence differs
(average-the-crowd vs follow-the-single-nearest). Nothing else is dialled.

Rules (the standard zonal SPP core, all forces shared by both arms):
  * N self-propelled ``FishAgent``s in continuous, UNBOUNDED 2D. Each carries a position
    p = (x, y) and a UNIT heading d = (dx, dy). Every fish moves at the SAME constant speed
    ``s`` per step; only its DIRECTION changes.
  * Three nested zones, by centre-to-centre distance r_ij:
      - Zone of Repulsion (zor): r_ij < ``zor`` — a hard-core personal space.
      - Zone of Orientation: zor <= r_ij < zor + ``dzoo`` — align heading with the neighbour.
      - Zone of Attraction: zor + dzoo <= r_ij < zor + dzoo + ``zoa_width`` — steer toward it.
  * Desired direction each step:
      - REPULSION OVERRIDES (identical in both arms): if any neighbour is within zor, the
        desired direction is -normalize(sum of unit vectors toward those neighbours) — steer
        directly AWAY; orientation and attraction are ignored.
      - Otherwise combine orientation + attraction by the arm's INTEGRATION RULE:
          AVERAGING:  d_desired = normalize( sum_{j in zoo} d_j  +  sum_{j in zoa} u_ij )
          DECISION:   pick the single NEAREST orientation-or-attraction neighbour j*; if it
                      is in the orientation zone,  d_desired = normalize(d_j*), else
                      d_desired = normalize(u_ij*)   (u_ij = unit vector from i toward j).
        If no orientation/attraction neighbour exists, the fish keeps its current heading.
  * BOUNDED TURN + NOISE: the fish rotates its heading toward d_desired by at most
    ``theta_max`` radians this step, THEN a Gaussian heading noise of s.d. ``sigma`` (radians)
    is added. Finally it moves distance ``s`` along the new heading.
  * The update is SYNCHRONOUS: every fish's desired direction is computed from the SAME
    start-of-step snapshot, then all fish turn, add noise, and move. Deterministic given the
    seeded RNG draw sequence.

Order parameters (the locked grading metrics), computed on the school each step:
    polarization p = | (1/N) sum_i d_i |               in [0, 1]
        — heading coherence; p ~ 1 is a parallel, coherently moving school.
    nearest-neighbour distance (NND): for each fish, the distance to its single nearest
        other fish. The school's cohesion is summarised by the COEFFICIENT OF VARIATION of
        the NND, CV(NND) = std(NND)/mean(NND) over the fish — a smaller CV means more
        tightly / uniformly regulated spacing (tighter cohesion), the locked P2 metric.

Built on the neutral platform (``abm_auto._platform``): each fish is a ``FishAgent`` carrying
its own (x, y, dx, dy); ``HuthWisselModel`` drives the synchronous zone-integration +
bounded-turn + move update over the ``AgentSet`` roster and records (via a ``DataCollector``)
the per-step polarization p and CV(NND). Neighbour lookup is brute-force all-pairs (O(N^2))
over the cohesive school (N is a few tens–hundred, and attraction holds the group compact so
a periodic box / cell list buys little).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector

AVERAGING = "averaging"
DECISION = "decision"
_RULES = (AVERAGING, DECISION)


# -- vector helpers -----------------------------------------------------------

def _norm(vx: float, vy: float) -> float:
    return math.hypot(vx, vy)


def rotate_toward(dx: float, dy: float, tx: float, ty: float,
                  theta_max: float) -> Tuple[float, float]:
    """Rotate the unit heading (dx, dy) toward the unit target (tx, ty) by at most
    ``theta_max`` radians, returning the new unit heading.

    If the signed angle between them is within theta_max the heading snaps to the target;
    otherwise it rotates theta_max in the direction (CCW/CW) that reduces the angle. A zero
    target leaves the heading unchanged (nothing to steer toward).
    """
    tmag = _norm(tx, ty)
    if tmag == 0.0:
        return dx, dy
    txn, tyn = tx / tmag, ty / tmag
    dot = max(-1.0, min(1.0, dx * txn + dy * tyn))     # cos(angle) between unit vectors
    cross = dx * tyn - dy * txn                          # sin(angle) (2D scalar cross)
    angle = math.atan2(cross, dot)                       # signed angle in (-pi, pi]
    if abs(angle) <= theta_max:
        return txn, tyn                                  # can reach the target this step
    step = theta_max if angle > 0 else -theta_max
    ca, sa = math.cos(step), math.sin(step)
    nx = dx * ca - dy * sa
    ny = dx * sa + dy * ca
    m = _norm(nx, ny)
    return (nx / m, ny / m) if m > 0 else (dx, dy)


# -- Agent --------------------------------------------------------------------

class FishAgent(Agent):
    """One self-propelled fish: position (x, y) and UNIT heading (dx, dy).

    The Huth-Wissel tick is a model-level synchronous update (all desired directions from
    one snapshot, then all turn/noise/move), so the per-agent ``step`` is intentionally a
    no-op; the ``_next_dx`` / ``_next_dy`` fields stage the heading computed this step before
    the model commits the moves.
    """

    def __init__(self, agent_id: int, model: "HuthWisselModel", *,
                 x: float, y: float, dx: float, dy: float) -> None:
        super().__init__(agent_id, model)
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self._next_dx = dx
        self._next_dy = dy

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        """The Huth-Wissel tick (integrate zones from a snapshot, turn, then move) is a
        model-level synchronous update, not an autonomous single-agent step, so this is a
        no-op."""
        return None


# -- Model --------------------------------------------------------------------

class HuthWisselModel(AgentModel):
    """Drives the Huth & Wissel (1992) zonal self-propelled-fish dynamics.

    Construct with N, speed ``s``, repulsion radius ``zor``, orientation-zone WIDTH
    ``dzoo``, attraction-zone width ``zoa_width``, max turn ``theta_max`` (radians/step),
    heading noise s.d. ``sigma`` (radians), an initial-cluster radius ``init_radius`` for the
    seeded start, the integration ``rule`` ("averaging" or "decision"), and a seed. All zonal
    forces are identical between the two rules; ONLY the orientation+attraction integration
    differs. ``run(n_steps)`` advances the synchronous update and records per-step
    polarization p and CV(NND).
    """

    def __init__(self, n: int = 60, *, s: float = 1.0, zor: float = 1.0,
                 dzoo: float = 3.0, zoa_width: float = 6.0, theta_max: float = 0.35,
                 sigma: float = 0.05, init_radius: float = 4.0, rule: str = AVERAGING,
                 seed: int = 0,
                 _positions: Optional[Sequence[Tuple[float, float]]] = None,
                 _headings: Optional[Sequence[Tuple[float, float]]] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if s < 0:
            raise ValueError(f"need s >= 0 (got {s})")
        if zor <= 0 or zoa_width < 0:
            raise ValueError(f"need zor>0, zoa_width>=0 (got zor={zor}, zoa_width={zoa_width})")
        if dzoo < 0:
            raise ValueError(f"need dzoo >= 0 (got {dzoo})")
        if theta_max <= 0:
            raise ValueError(f"need theta_max > 0 (got {theta_max})")
        if sigma < 0:
            raise ValueError(f"need sigma >= 0 (got {sigma})")
        if rule not in _RULES:
            raise ValueError(f"unknown rule {rule!r}; expected one of {_RULES}")
        self.seed_value = seed
        self.n = n
        self.s = float(s)
        self.zor = float(zor)
        self.dzoo = float(dzoo)
        self.zoa_width = float(zoa_width)
        self.theta_max = float(theta_max)
        self.sigma = float(sigma)
        self.init_radius = float(init_radius)
        self.rule = rule

        # Derived nested radii. orientation ends at zor+dzoo; attraction ends at
        # zor+dzoo+zoa_width. Squared for cheap comparisons.
        self.r_orient = self.zor + self.dzoo
        self.r_attract = self.r_orient + self.zoa_width
        self.zor2 = self.zor * self.zor
        self.r_orient2 = self.r_orient * self.r_orient
        self.r_attract2 = self.r_attract * self.r_attract

        self.agent_list: List[FishAgent] = []
        if _positions is not None and _headings is not None:
            if len(_positions) != n or len(_headings) != n:
                raise ValueError("supplied positions/headings must have length n")
            for i in range(n):
                px, py = _positions[i]
                hx, hy = _headings[i]
                m = _norm(hx, hy)
                if m == 0:
                    hx, hy, m = 1.0, 0.0, 1.0
                agent = FishAgent(i, self, x=float(px), y=float(py),
                                  dx=hx / m, dy=hy / m)
                self.agent_list.append(agent)
                self.add_agent(agent)
        else:
            # Random initial state: positions uniform in a disc of radius init_radius about
            # the origin, headings uniform in direction. Seed-dependent; besides the per-step
            # Gaussian noise this is the only randomness in the run.
            for i in range(n):
                rr = self.init_radius * math.sqrt(self.rng.random())   # uniform in disc
                ang = self.rng.uniform(0.0, 2.0 * math.pi)
                x = rr * math.cos(ang)
                y = rr * math.sin(ang)
                hang = self.rng.uniform(0.0, 2.0 * math.pi)
                agent = FishAgent(i, self, x=x, y=y,
                                  dx=math.cos(hang), dy=math.sin(hang))
                self.agent_list.append(agent)
                self.add_agent(agent)

        self.reporter = DataCollector({
            "polarization": lambda m: m.polarization(),
            "cv_nnd": lambda m: m.cv_nnd(),
        })

    # -- metrics --
    def polarization(self) -> float:
        """p = | (1/N) sum_i d_i |, the coherence of headings, in [0, 1]. Each d_i is a unit
        heading, so the sum's magnitude over N is in [0, 1]."""
        if self.n == 0:
            return 0.0
        sx = sum(a.dx for a in self.agent_list)
        sy = sum(a.dy for a in self.agent_list)
        return _norm(sx, sy) / self.n

    def nearest_neighbour_distances(self) -> List[float]:
        """For each fish, the Euclidean distance to its single nearest OTHER fish
        (brute-force all-pairs; the school is compact so O(N^2) is fine). Returns a list of
        N NND values (0.0 for a lone fish, n<=1)."""
        if self.n <= 1:
            return [0.0] * self.n
        out: List[float] = []
        for a in self.agent_list:
            best2 = float("inf")
            for b in self.agent_list:
                if b is a:
                    continue
                dx = b.x - a.x
                dy = b.y - a.y
                d2 = dx * dx + dy * dy
                if d2 < best2:
                    best2 = d2
            out.append(math.sqrt(best2) if best2 != float("inf") else 0.0)
        return out

    def mean_nnd(self) -> float:
        """Mean nearest-neighbour distance over the school."""
        nnds = self.nearest_neighbour_distances()
        return sum(nnds) / len(nnds) if nnds else 0.0

    def cv_nnd(self) -> float:
        """Coefficient of variation of NND = std(NND) / mean(NND) over the school, in [0, ∞).

        The locked cohesion metric (P2): a SMALLER CV means more tightly / uniformly regulated
        spacing (tighter cohesion). Returns 0.0 if the mean NND is 0 (degenerate)."""
        nnds = self.nearest_neighbour_distances()
        if not nnds:
            return 0.0
        mean = sum(nnds) / len(nnds)
        if mean <= 0.0:
            return 0.0
        var = sum((v - mean) ** 2 for v in nnds) / len(nnds)
        return math.sqrt(var) / mean

    # -- desired direction (the integration rule is the locked A/B) --
    def desired_direction(self, a: FishAgent) -> Tuple[float, float]:
        """The desired UNIT direction for fish ``a`` from the current snapshot.

        Repulsion (any neighbour within zor) OVERRIDES everything — steer away from the sum
        of unit vectors toward those neighbours (identical in both arms). Otherwise the
        orientation+attraction influence is integrated by the arm's rule:
          - AVERAGING: normalise( sum of in-zoo neighbour headings + sum of unit vectors
            toward in-zoa neighbours ).
          - DECISION: pick the single NEAREST orientation-or-attraction neighbour; align to
            it if it is in the orientation zone, else steer toward it.
        Returns (0, 0) meaning "no preference — keep the current heading" (no relevant
        neighbours).
        """
        rep_x = rep_y = 0.0
        n_rep = 0
        # averaging accumulators
        ori_x = ori_y = 0.0
        att_x = att_y = 0.0
        # decision: track the single nearest orientation/attraction neighbour
        best_d2 = float("inf")
        best_is_orient = False
        best_ux = best_uy = 0.0
        best_bdx = best_bdy = 0.0
        for b in self.agent_list:
            if b is a:
                continue
            rx = b.x - a.x
            ry = b.y - a.y
            d2 = rx * rx + ry * ry
            if d2 == 0.0:
                continue
            if d2 >= self.r_attract2:
                continue                                 # outside all zones
            d = math.sqrt(d2)
            ux, uy = rx / d, ry / d
            if d2 < self.zor2:
                # repulsion: accumulate unit vector toward b (we steer away from the sum)
                rep_x += ux
                rep_y += uy
                n_rep += 1
                continue
            # orientation vs attraction (only relevant when no repulsion neighbour exists;
            # if one appears later in the scan, repulsion overrides at the end and these are
            # discarded).
            in_orient = d2 < self.r_orient2
            # AVERAGING accumulators (all relevant neighbours)
            if in_orient:
                ori_x += b.dx
                ori_y += b.dy
            else:
                att_x += ux
                att_y += uy
            # DECISION: is this the nearest orientation/attraction neighbour so far?
            if d2 < best_d2:
                best_d2 = d2
                best_is_orient = in_orient
                best_ux, best_uy = ux, uy
                best_bdx, best_bdy = b.dx, b.dy

        if n_rep > 0:
            # steer AWAY from repulsion neighbours (override, identical in both arms)
            m = _norm(rep_x, rep_y)
            if m == 0.0:
                return 0.0, 0.0                          # exactly balanced: no preference
            return -rep_x / m, -rep_y / m

        if best_d2 == float("inf"):
            return 0.0, 0.0                              # no orientation/attraction neighbour

        if self.rule == AVERAGING:
            dx = ori_x + att_x
            dy = ori_y + att_y
            m = _norm(dx, dy)
            if m == 0.0:
                return 0.0, 0.0
            return dx / m, dy / m

        # DECISION: follow ONLY the single nearest orientation/attraction neighbour.
        if best_is_orient:
            m = _norm(best_bdx, best_bdy)                # align to its heading
            if m == 0.0:
                return 0.0, 0.0
            return best_bdx / m, best_bdy / m
        return best_ux, best_uy                          # steer toward it (already unit)

    # -- tick --
    def step(self) -> None:
        """One synchronous Huth-Wissel zonal tick.

        (1) From the start-of-step snapshot, every fish computes its desired direction
            (repulsion override, else orientation+attraction by the arm's integration rule),
            rotates its heading toward it by at most theta_max, then adds Gaussian heading
            noise sigma. A zero desired direction leaves the heading unchanged before noise.
        (2) Then every fish moves distance s along its NEW heading. Headings are staged in
            ``_next_dx/_next_dy`` so all desired directions read one consistent snapshot
            (synchronous update)."""
        for a in self.agent_list:
            tx, ty = self.desired_direction(a)
            ndx, ndy = rotate_toward(a.dx, a.dy, tx, ty, self.theta_max)
            if self.sigma > 0.0:
                noise = self.rng.gauss(0.0, self.sigma)
                ca, sa = math.cos(noise), math.sin(noise)
                rx = ndx * ca - ndy * sa
                ry = ndx * sa + ndy * ca
                m = _norm(rx, ry)
                if m > 0:
                    ndx, ndy = rx / m, ry / m
            a._next_dx = ndx
            a._next_dy = ndy
        for a in self.agent_list:
            a.dx = a._next_dx
            a.dy = a._next_dy
            a.x += self.s * a.dx
            a.y += self.s * a.dy
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_steps: int = 400, *, measure_last: int = 150) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_steps`` synchronous ticks; return the run summary.

        ``measure_last`` is the trailing window over which steady-state polarization and
        CV(NND) are averaged (the transient is the leading n_steps - measure_last ticks).
        Returns steady + final p and CV(NND), the steady mean NND, and the full per-step
        series of both metrics.
        """
        if measure_last <= 0 or measure_last > n_steps + 1:
            raise ValueError(
                f"measure_last must be in [1, n_steps+1] (got {measure_last}, n_steps={n_steps})")
        self.reporter.collect(self)                       # t=0 baseline
        for _ in range(n_steps):
            self.step()
        p_series = self.reporter.series("polarization")
        cv_series = self.reporter.series("cv_nnd")
        return {
            "n": self.n,
            "s": self.s,
            "zor": self.zor,
            "dzoo": self.dzoo,
            "zoa_width": self.zoa_width,
            "r_orient": self.r_orient,
            "r_attract": self.r_attract,
            "theta_max": self.theta_max,
            "sigma": self.sigma,
            "rule": self.rule,
            "seed": self.seed_value,
            "n_steps": n_steps,
            "measure_last": measure_last,
            "steady_polarization": tail_mean(p_series, window=measure_last),
            "steady_cv_nnd": tail_mean(cv_series, window=measure_last),
            "steady_mean_nnd": self.mean_nnd(),
            "final_polarization": p_series[-1],
            "final_cv_nnd": cv_series[-1],
            "polarization_series": p_series,
            "cv_nnd_series": cv_series,
        }


# -- summary helpers ----------------------------------------------------------

def tail_mean(series: Sequence[float], *, window: int = 150) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of a series (or the whole
    series if shorter). Averaging the tail smooths finite-N jitter and discards the transient
    before measurement."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(rule: str = AVERAGING, *, n: int = 60, s: float = 1.0, zor: float = 1.0,
               dzoo: float = 3.0, zoa_width: float = 6.0, theta_max: float = 0.35,
               sigma: float = 0.05, init_radius: float = 4.0, seed: int = 0,
               n_steps: int = 400, measure_last: int = 150) -> Dict[str, Any]:
    """One Huth-Wissel run under one integration ``rule`` at a given seed and the fixed
    (shared) zonal-force parameters."""
    return HuthWisselModel(
        n, s=s, zor=zor, dzoo=dzoo, zoa_width=zoa_width, theta_max=theta_max,
        sigma=sigma, init_radius=init_radius, rule=rule, seed=seed).run(
        n_steps, measure_last=measure_last)


def run_many_seeds(rule: str = AVERAGING, *, n: int = 60, s: float = 1.0, zor: float = 1.0,
                   dzoo: float = 3.0, zoa_width: float = 6.0, theta_max: float = 0.35,
                   sigma: float = 0.05, init_radius: float = 4.0, n_seeds: int = 8,
                   seed_base: int = 0, n_steps: int = 400,
                   measure_last: int = 150) -> Dict[str, Any]:
    """Run ``n_seeds`` runs (seed ``seed_base + i``) under one integration ``rule`` at the
    fixed shared parameters and summarise the steady polarization p and steady CV(NND) across
    seeds (mean + spread).

    Both arms of the locked experiment call this with matched parameters and the SAME seed
    set; only ``rule`` differs. Returns per-seed steady p and CV(NND), their mean / std / min
    / max, per-seed steady mean-NND, and one representative trajectory (first seed) of both
    series for inspection.
    """
    runs = [run_single(rule, n=n, s=s, zor=zor, dzoo=dzoo, zoa_width=zoa_width,
                       theta_max=theta_max, sigma=sigma, init_radius=init_radius,
                       seed=seed_base + i, n_steps=n_steps, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_p = [rr["steady_polarization"] for rr in runs]
    per_seed_cv = [rr["steady_cv_nnd"] for rr in runs]
    per_seed_nnd = [rr["steady_mean_nnd"] for rr in runs]
    mean_p = sum(per_seed_p) / n_seeds
    var_p = sum((v - mean_p) ** 2 for v in per_seed_p) / n_seeds
    mean_cv = sum(per_seed_cv) / n_seeds
    var_cv = sum((v - mean_cv) ** 2 for v in per_seed_cv) / n_seeds
    return {
        "rule": rule,
        "n": n, "s": s, "zor": zor, "dzoo": dzoo, "zoa_width": zoa_width,
        "theta_max": theta_max, "sigma": sigma, "init_radius": init_radius,
        "n_seeds": n_seeds, "seed_base": seed_base, "n_steps": n_steps,
        "measure_last": measure_last,
        "per_seed_polarization": per_seed_p,
        "per_seed_cv_nnd": per_seed_cv,
        "per_seed_mean_nnd": per_seed_nnd,
        "mean_polarization": mean_p,
        "std_polarization": var_p ** 0.5,
        "min_polarization": min(per_seed_p),
        "max_polarization": max(per_seed_p),
        "mean_cv_nnd": mean_cv,
        "std_cv_nnd": var_cv ** 0.5,
        "min_cv_nnd": min(per_seed_cv),
        "max_cv_nnd": max(per_seed_cv),
        "mean_mean_nnd": sum(per_seed_nnd) / n_seeds,
        "example_polarization_series": runs[0]["polarization_series"],
        "example_cv_nnd_series": runs[0]["cv_nnd_series"],
    }


def compare_rules(*, n: int = 60, s: float = 1.0, zor: float = 1.0, dzoo: float = 3.0,
                  zoa_width: float = 6.0, theta_max: float = 0.35, sigma: float = 0.05,
                  init_radius: float = 4.0, n_seeds: int = 8, seed_base: int = 0,
                  n_steps: int = 400, measure_last: int = 150) -> Dict[str, Any]:
    """Run BOTH integration rules at MATCHED parameters and the SAME seed set, and return
    both seed-averaged summaries plus the averaging-advantage deltas the locked clauses grade:
    the polarization gap (p_avg - p_dec) and the CV(NND) gap (cv_avg - cv_dec)."""
    avg = run_many_seeds(AVERAGING, n=n, s=s, zor=zor, dzoo=dzoo, zoa_width=zoa_width,
                         theta_max=theta_max, sigma=sigma, init_radius=init_radius,
                         n_seeds=n_seeds, seed_base=seed_base, n_steps=n_steps,
                         measure_last=measure_last)
    dec = run_many_seeds(DECISION, n=n, s=s, zor=zor, dzoo=dzoo, zoa_width=zoa_width,
                         theta_max=theta_max, sigma=sigma, init_radius=init_radius,
                         n_seeds=n_seeds, seed_base=seed_base, n_steps=n_steps,
                         measure_last=measure_last)
    return {
        "averaging": avg,
        "decision": dec,
        "polarization_gap": avg["mean_polarization"] - dec["mean_polarization"],
        "cv_nnd_gap": avg["mean_cv_nnd"] - dec["mean_cv_nnd"],
    }
