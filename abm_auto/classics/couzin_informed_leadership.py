"""Couzin, Krause, Franks & Levin — informed leadership in animal groups (2005).

Source: Couzin, I. D., Krause, J., Franks, N. R. & Levin, S. A. (2005), "Effective
leadership and decision-making in animal groups on the move", Nature 433:513-516.
doi:10.1038/nature03236.

Framing: **genuine-agent (zonal SPP with informed minorities, disclosed).** This is NOT a
grid CA and NOT the single-alignment Vicsek rule: each individual is an autonomous
self-propelled agent with a heading and a bounded turning rate, and it integrates the same
nested behavioural zones (repulsion / orientation / attraction) as the 2002 Couzin model.
The new ingredient is INFORMATION: a fraction ``p_inf`` of the agents are INFORMED — they
balance the social force with a fixed preferred goal direction ``g_hat`` weighted by
``omega`` — while the rest are NAIVE (social force only). The phenomena of interest are the
leader-economy (a small informed minority steers the group; the required fraction FALLS with
group size) and the averaging-vs-commitment transition when informed agents disagree.

This module is deliberately DISTINCT from ``couzin_zonal`` (the 2002 milling/hysteresis phase
portrait). Here every agent is homogeneous in its social rules; the ONLY heterogeneity is
whether an agent carries a private goal, and the locked metric is GROUP DIRECTIONAL ACCURACY
= cos(angle between the group's mean heading and the informed goal). To keep the study
self-contained and its numerics auditable in one place, the zonal core is re-implemented here
rather than imported.

Rules (the 2005 model; a 3-zone SPP substrate + informed goal-weighting):
  * N self-propelled ``InformedFishAgent``s live in continuous, UNBOUNDED 2D. Each carries a
    position p=(x,y) and a UNIT heading d=(dx,dy) and moves at constant speed ``s`` per step;
    only its DIRECTION changes.
  * Three nested zones by centre-to-centre distance r_ij:
      - Zone of Repulsion (zor): r_ij < ``zor``               — hard-core personal space.
      - Zone of Orientation:     zor <= r_ij < zor + ``dzoo`` — align heading with neighbour.
      - Zone of Attraction:      ... < r_ij < ... + ``zoa_width`` — steer toward neighbour.
  * SOCIAL desired direction ``d_soc`` each step (the 2002 rule):
      - REPULSION OVERRIDES: if any neighbour is within zor,
          d_soc = -normalize( sum_j (p_j - p_i)/|p_j - p_i| )   (steer away; ignore o/a).
      - Otherwise d_soc = normalize( sum_{zoo} d_j + sum_{zoa} (p_j-p_i)/|p_j-p_i| ).
      - If no neighbour is in any zone, d_soc = current heading (no social preference).
  * INFORMED goal-weighting (the 2005 addition, their Eq. for informed individuals):
      an informed agent with a UNIT preferred goal ``g_hat`` computes its desired direction as
          d_desired = normalize( d_soc + omega * g_hat )
      where ``omega`` is the goal weight. A naive agent uses d_desired = d_soc. When repulsion
      is active the informed agent STILL just avoids (goal is suppressed under collision
      avoidance), exactly as social repulsion overrides orientation/attraction.
  * BOUNDED TURN + NOISE: rotate the heading toward d_desired by at most ``theta_max`` rad,
    then add Gaussian heading noise s.d. ``sigma`` (rad), then move distance ``s`` along the
    new heading. The update is SYNCHRONOUS (all desired directions from one snapshot).

Group directional accuracy (the LOCKED metric):
    accuracy = cos( angle( group_mean_heading, g_hat ) ) = (mean_heading_hat . g_hat)
        in [-1, 1]; 1 = the group moves exactly toward the goal. In the two-subgroup mode the
    reference goal for the accuracy print is the ANGULAR BISECTOR of the two goals, and the
    grading metric is the SIGNED angle of the group heading relative to that bisector: near 0
    means the group AVERAGED the two goals; near +-theta/2 means it COMMITTED to one subgroup.

Built on the neutral platform (``abm_auto._platform``): each fish is an ``InformedFishAgent``
carrying its own (x, y, dx, dy) plus a goal (gx, gy) that is (0, 0) for naive agents;
``InformedLeadershipModel`` drives the synchronous zone-integration + goal-weighting +
bounded-turn + move update and records the per-step group mean-heading vector. Neighbour
lookup is brute-force all-pairs (the cohesive group is a few tens–few hundred agents).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- vector helpers -----------------------------------------------------------

def _norm(vx: float, vy: float) -> float:
    return math.hypot(vx, vy)


def _cross2d(ax: float, ay: float, bx: float, by: float) -> float:
    """2D scalar cross product a x b = a_x b_y - a_y b_x (signed z-component)."""
    return ax * by - ay * bx


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
    dot = max(-1.0, min(1.0, dx * txn + dy * tyn))
    cross = _cross2d(dx, dy, txn, tyn)
    angle = math.atan2(cross, dot)               # in (-pi, pi]
    if abs(angle) <= theta_max:
        return txn, tyn                           # can reach the target this step
    step = theta_max if angle > 0 else -theta_max
    ca, sa = math.cos(step), math.sin(step)
    nx = dx * ca - dy * sa
    ny = dx * sa + dy * ca
    m = _norm(nx, ny)
    return (nx / m, ny / m) if m > 0 else (dx, dy)


def angular_difference(a: float, b: float) -> float:
    """Signed smallest difference a - b wrapped into (-pi, pi]."""
    d = (a - b) % (2.0 * math.pi)
    if d > math.pi:
        d -= 2.0 * math.pi
    return d


# -- Agent --------------------------------------------------------------------

class InformedFishAgent(Agent):
    """One self-propelled individual: position (x, y), UNIT heading (dx, dy), and a private
    goal (gx, gy). Naive agents carry goal (0, 0) — no preferred direction; informed agents
    carry a UNIT preferred direction (gx, gy). The zonal tick is a model-level synchronous
    update, so the per-agent ``step`` is a no-op; ``_next_dx``/``_next_dy`` stage the new
    heading before the model commits the moves."""

    def __init__(self, agent_id: int, model: "InformedLeadershipModel", *,
                 x: float, y: float, dx: float, dy: float,
                 gx: float = 0.0, gy: float = 0.0) -> None:
        super().__init__(agent_id, model)
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.gx = gx
        self.gy = gy
        self._next_dx = dx
        self._next_dy = dy

    @property
    def informed(self) -> bool:
        return (self.gx != 0.0) or (self.gy != 0.0)

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        return None


# -- Model --------------------------------------------------------------------

class InformedLeadershipModel(AgentModel):
    """Drives the Couzin et al. (2005) informed-leadership dynamics on a 3-zone SPP substrate.

    Construct with N, the number of informed agents ``n_informed`` (the rest naive), the goal
    weight ``omega``, the social-zone geometry (``zor``, ``dzoo``, ``zoa_width``), motion
    (``s``, ``theta_max``, ``sigma``), and a seed. Informed agents are the FIRST
    ``n_informed`` agents by id; each is assigned a goal from ``goals`` — either a single
    shared ``goal_angle`` (radians) for every informed agent, or a per-informed list via
    ``informed_goal_angles`` (for the two-subgroup averaging-vs-commitment test).

    ``run(n_steps)`` advances the synchronous update and records the per-step group
    mean-heading vector; the tail-averaged accuracy is measured against the (single or
    bisector) reference goal.
    """

    def __init__(self, n: int = 100, *, n_informed: int = 10, omega: float = 0.5,
                 goal_angle: float = 0.0,
                 informed_goal_angles: Optional[Sequence[float]] = None,
                 s: float = 1.0, zor: float = 1.0, dzoo: float = 6.0,
                 zoa_width: float = 8.0, theta_max: float = 0.35, sigma: float = 0.05,
                 init_radius: float = 5.0, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if not (0 <= n_informed <= n):
            raise ValueError(f"need 0 <= n_informed <= n (got n_informed={n_informed}, n={n})")
        if omega < 0:
            raise ValueError(f"need omega >= 0 (got {omega})")
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
        if informed_goal_angles is not None and len(informed_goal_angles) != n_informed:
            raise ValueError(
                f"informed_goal_angles must have length n_informed={n_informed} "
                f"(got {len(informed_goal_angles)})")

        self.seed_value = seed
        self.n = n
        self.n_informed = n_informed
        self.omega = float(omega)
        self.s = float(s)
        self.zor = float(zor)
        self.dzoo = float(dzoo)
        self.zoa_width = float(zoa_width)
        self.theta_max = float(theta_max)
        self.sigma = float(sigma)
        self.init_radius = float(init_radius)

        # Derived nested radii (squared for cheap comparisons).
        self.r_orient = self.zor + self.dzoo
        self.r_attract = self.r_orient + self.zoa_width
        self.zor2 = self.zor * self.zor
        self.r_orient2 = self.r_orient * self.r_orient
        self.r_attract2 = self.r_attract * self.r_attract

        # Per-informed goal angles.
        if informed_goal_angles is not None:
            self.informed_goal_angles = [float(a) for a in informed_goal_angles]
        else:
            self.informed_goal_angles = [float(goal_angle)] * n_informed
        # Reference goal for the accuracy metric = circular mean of the informed goals
        # (this is a single goal for the single-goal sweeps, and the angular BISECTOR for the
        # two-subgroup mode). Undefined (no informed agents) -> +x axis by convention.
        if n_informed > 0:
            gsx = sum(math.cos(a) for a in self.informed_goal_angles)
            gsy = sum(math.sin(a) for a in self.informed_goal_angles)
            if _norm(gsx, gsy) > 1e-12:
                self.ref_goal_angle = math.atan2(gsy, gsx)
            else:                                 # exactly antipodal goals: use the first
                self.ref_goal_angle = self.informed_goal_angles[0]
        else:
            self.ref_goal_angle = float(goal_angle)
        self.ref_gx = math.cos(self.ref_goal_angle)
        self.ref_gy = math.sin(self.ref_goal_angle)

        # Build the roster: informed agents are the first n_informed ids.
        self.agent_list: List[InformedFishAgent] = []
        for i in range(n):
            rr = self.init_radius * math.sqrt(self.rng.random())
            ang = self.rng.uniform(0.0, 2.0 * math.pi)
            x = rr * math.cos(ang)
            y = rr * math.sin(ang)
            hang = self.rng.uniform(0.0, 2.0 * math.pi)
            if i < n_informed:
                ga = self.informed_goal_angles[i]
                gx, gy = math.cos(ga), math.sin(ga)
            else:
                gx, gy = 0.0, 0.0
            agent = InformedFishAgent(i, self, x=x, y=y,
                                      dx=math.cos(hang), dy=math.sin(hang),
                                      gx=gx, gy=gy)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "mean_dx": lambda m: m.mean_heading()[0],
            "mean_dy": lambda m: m.mean_heading()[1],
            "accuracy": lambda m: m.accuracy(),
            "heading_angle": lambda m: m.mean_heading_angle(),
            "polarization": lambda m: m.polarization(),
        })

    # -- properties --
    @property
    def p_inf(self) -> float:
        """Informed fraction n_informed / n."""
        return self.n_informed / self.n

    # -- metrics --
    def mean_heading(self) -> Tuple[float, float]:
        """The group mean heading vector (1/N) sum_i d_i (NOT normalized; magnitude is the
        polarization)."""
        if self.n == 0:
            return 0.0, 0.0
        sx = sum(a.dx for a in self.agent_list) / self.n
        sy = sum(a.dy for a in self.agent_list) / self.n
        return sx, sy

    def polarization(self) -> float:
        """p = | (1/N) sum_i d_i | in [0, 1] — heading coherence."""
        mx, my = self.mean_heading()
        return _norm(mx, my)

    def mean_heading_angle(self) -> float:
        """Angle (radians, in (-pi, pi]) of the group mean heading. Undefined if perfectly
        incoherent (zero mean vector) -> returns 0.0 by convention."""
        mx, my = self.mean_heading()
        if _norm(mx, my) < 1e-12:
            return 0.0
        return math.atan2(my, mx)

    def accuracy(self) -> float:
        """Group directional accuracy = cos(angle between the group MEAN HEADING and the
        reference goal g_hat) = mean_heading_hat . g_hat, in [-1, 1]. If the group heading is
        perfectly incoherent (zero mean vector) accuracy is 0 (no defined direction)."""
        mx, my = self.mean_heading()
        m = _norm(mx, my)
        if m < 1e-12:
            return 0.0
        return (mx * self.ref_gx + my * self.ref_gy) / m

    def signed_heading_offset(self) -> float:
        """Signed angle (radians, in (-pi, pi]) of the group mean heading RELATIVE to the
        reference goal (the bisector in the two-subgroup mode). Near 0 = the group averaged
        the goals; near +-theta/2 = it committed to one subgroup."""
        return angular_difference(self.mean_heading_angle(), self.ref_goal_angle)

    # -- social desired direction --
    def social_direction(self, a: InformedFishAgent) -> Tuple[float, float]:
        """The 2002 social desired direction for agent ``a`` from the current snapshot.

        Repulsion (any neighbour within zor) OVERRIDES: steer away from the sum of unit
        vectors toward those neighbours. Otherwise combine orientation (sum of in-zone
        neighbour headings) and attraction (sum of unit vectors toward in-zone neighbours),
        normalize. Returns (0, 0) to mean "no social preference — keep the current heading",
        AND a flag ``repelling`` telling the caller repulsion was active (the goal is
        suppressed under collision avoidance)."""
        rep_x = rep_y = 0.0
        n_rep = 0
        ori_x = ori_y = 0.0
        att_x = att_y = 0.0
        for b in self.agent_list:
            if b is a:
                continue
            rx = b.x - a.x
            ry = b.y - a.y
            d2 = rx * rx + ry * ry
            if d2 == 0.0:
                continue
            if d2 >= self.r_attract2:
                continue                          # outside all zones
            d = math.sqrt(d2)
            ux, uy = rx / d, ry / d
            if d2 < self.zor2:
                rep_x += ux
                rep_y += uy
                n_rep += 1
            elif n_rep == 0:
                if d2 < self.r_orient2:
                    ori_x += b.dx
                    ori_y += b.dy
                else:
                    att_x += ux
                    att_y += uy
        if n_rep > 0:
            m = _norm(rep_x, rep_y)
            if m == 0.0:
                return 0.0, 0.0, True             # exactly balanced repulsion
            return -rep_x / m, -rep_y / m, True
        dx = ori_x + att_x
        dy = ori_y + att_y
        m = _norm(dx, dy)
        if m == 0.0:
            return 0.0, 0.0, False
        return dx / m, dy / m, False

    def desired_direction(self, a: InformedFishAgent) -> Tuple[float, float]:
        """The 2005 desired direction: the social direction, then (for an informed agent NOT
        currently avoiding a collision) blended with its private goal:
            d_desired = normalize( d_soc + omega * g_hat ).
        A naive agent uses d_soc alone. Under active repulsion the goal is suppressed (the
        informed agent just avoids), matching how repulsion overrides orientation/attraction.
        If the social direction is (0,0) (no neighbours, no repulsion) an informed agent
        steers by its goal alone; a naive agent keeps its current heading."""
        sx, sy, repelling = self.social_direction(a)
        if not a.informed or repelling:
            return sx, sy
        # informed, not avoiding: blend social + goal
        bx = sx + self.omega * a.gx
        by = sy + self.omega * a.gy
        m = _norm(bx, by)
        if m == 0.0:
            return 0.0, 0.0
        return bx / m, by / m

    # -- tick --
    def step(self) -> None:
        """One synchronous informed-leadership tick: every agent computes its desired
        direction from the start-of-step snapshot (social + goal blend), rotates its heading
        toward it by at most theta_max, adds Gaussian noise sigma, then all move distance s
        along the NEW heading."""
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

    def run(self, n_steps: int = 300, *, measure_last: int = 100) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_steps`` synchronous ticks; return the run summary with the tail-averaged
        accuracy (mean over the trailing ``measure_last`` steps, after heading equilibration),
        plus the final accuracy and the full per-step series."""
        if measure_last <= 0 or measure_last > n_steps + 1:
            raise ValueError(
                f"measure_last must be in [1, n_steps+1] (got {measure_last}, n_steps={n_steps})")
        self.reporter.collect(self)               # t=0 baseline
        for _ in range(n_steps):
            self.step()
        acc_series = self.reporter.series("accuracy")
        pol_series = self.reporter.series("polarization")
        ang_series = self.reporter.series("heading_angle")
        # tail-averaged signed offset via the tail-mean heading angle relative to ref goal
        tail_ang = ang_series[-measure_last:] if len(ang_series) >= measure_last else ang_series
        # circular mean of the tail heading angles
        csx = sum(math.cos(x) for x in tail_ang)
        csy = sum(math.sin(x) for x in tail_ang)
        tail_mean_angle = math.atan2(csy, csx) if _norm(csx, csy) > 1e-12 else 0.0
        signed_offset = angular_difference(tail_mean_angle, self.ref_goal_angle)
        return {
            "n": self.n,
            "n_informed": self.n_informed,
            "p_inf": self.p_inf,
            "omega": self.omega,
            "ref_goal_angle": self.ref_goal_angle,
            "informed_goal_angles": list(self.informed_goal_angles),
            "zor": self.zor,
            "dzoo": self.dzoo,
            "zoa_width": self.zoa_width,
            "theta_max": self.theta_max,
            "sigma": self.sigma,
            "s": self.s,
            "seed": self.seed_value,
            "n_steps": n_steps,
            "measure_last": measure_last,
            "steady_accuracy": tail_mean(acc_series, window=measure_last),
            "final_accuracy": acc_series[-1],
            "steady_polarization": tail_mean(pol_series, window=measure_last),
            "steady_signed_offset": signed_offset,
            "accuracy_series": acc_series,
            "polarization_series": pol_series,
        }


# -- summary helpers ----------------------------------------------------------

def tail_mean(series: Sequence[float], *, window: int = 100) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of a series (or the whole
    series if shorter)."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def _n_informed_for_fraction(n: int, p: float) -> int:
    """Number of informed agents for target fraction ``p`` at group size ``n``: round to the
    nearest integer, clamped to [0, n]. (The realised fraction is n_informed/n, reported
    honestly; it may differ slightly from the target p at small n.)"""
    k = int(round(p * n))
    return max(0, min(n, k))


def run_single(n: int = 100, *, p_inf: float = 0.1, omega: float = 0.5,
               goal_angle: float = 0.0,
               informed_goal_angles: Optional[Sequence[float]] = None,
               s: float = 1.0, zor: float = 1.0, dzoo: float = 6.0,
               zoa_width: float = 8.0, theta_max: float = 0.35, sigma: float = 0.05,
               init_radius: float = 5.0, seed: int = 0,
               n_steps: int = 400, measure_last: int = 150) -> Dict[str, Any]:
    """One informed-leadership run at target informed fraction ``p_inf`` (or an explicit
    per-informed goal-angle list) and the fixed rule parameters."""
    if informed_goal_angles is not None:
        n_informed = len(informed_goal_angles)
    else:
        n_informed = _n_informed_for_fraction(n, p_inf)
    return InformedLeadershipModel(
        n, n_informed=n_informed, omega=omega, goal_angle=goal_angle,
        informed_goal_angles=informed_goal_angles, s=s, zor=zor, dzoo=dzoo,
        zoa_width=zoa_width, theta_max=theta_max, sigma=sigma, init_radius=init_radius,
        seed=seed).run(n_steps, measure_last=measure_last)


def run_many_seeds(n: int = 100, *, p_inf: float = 0.1, omega: float = 0.5,
                   goal_angle: float = 0.0,
                   informed_goal_angles: Optional[Sequence[float]] = None,
                   s: float = 1.0, zor: float = 1.0, dzoo: float = 6.0,
                   zoa_width: float = 8.0, theta_max: float = 0.35, sigma: float = 0.05,
                   init_radius: float = 5.0, n_seeds: int = 8, seed_base: int = 0,
                   n_steps: int = 400, measure_last: int = 150) -> Dict[str, Any]:
    """Run ``n_seeds`` runs (seed ``seed_base + i``) at one (n, p_inf) and summarise the
    steady group directional accuracy across seeds (mean + spread). Also returns the mean
    steady signed heading offset (for the two-subgroup averaging/commitment test) and one
    representative accuracy trajectory."""
    runs = [run_single(n, p_inf=p_inf, omega=omega, goal_angle=goal_angle,
                       informed_goal_angles=informed_goal_angles, s=s, zor=zor, dzoo=dzoo,
                       zoa_width=zoa_width, theta_max=theta_max, sigma=sigma,
                       init_radius=init_radius, seed=seed_base + i, n_steps=n_steps,
                       measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_acc = [rr["steady_accuracy"] for rr in runs]
    per_seed_offset = [rr["steady_signed_offset"] for rr in runs]
    per_seed_pol = [rr["steady_polarization"] for rr in runs]
    mean_acc = sum(per_seed_acc) / n_seeds
    var_acc = sum((v - mean_acc) ** 2 for v in per_seed_acc) / n_seeds
    realised_n_informed = runs[0]["n_informed"]
    return {
        "n": n,
        "target_p_inf": p_inf,
        "n_informed": realised_n_informed,
        "realised_p_inf": realised_n_informed / n,
        "omega": omega,
        "goal_angle": goal_angle,
        "informed_goal_angles": runs[0]["informed_goal_angles"],
        "ref_goal_angle": runs[0]["ref_goal_angle"],
        "zor": zor, "dzoo": dzoo, "zoa_width": zoa_width, "theta_max": theta_max,
        "sigma": sigma, "s": s, "init_radius": init_radius,
        "n_seeds": n_seeds, "seed_base": seed_base, "n_steps": n_steps,
        "measure_last": measure_last,
        "per_seed_accuracy": per_seed_acc,
        "mean_accuracy": mean_acc,
        "std_accuracy": var_acc ** 0.5,
        "min_accuracy": min(per_seed_acc),
        "max_accuracy": max(per_seed_acc),
        "per_seed_signed_offset": per_seed_offset,
        "mean_signed_offset": sum(per_seed_offset) / n_seeds,
        "per_seed_polarization": per_seed_pol,
        "mean_polarization": sum(per_seed_pol) / n_seeds,
        "example_accuracy_series": runs[0]["accuracy_series"],
    }


def sweep_p_inf(p_values: Sequence[float], *, n: int = 100, omega: float = 0.5,
                goal_angle: float = 0.0, s: float = 1.0, zor: float = 1.0,
                dzoo: float = 6.0, zoa_width: float = 8.0, theta_max: float = 0.35,
                sigma: float = 0.05, init_radius: float = 5.0, n_seeds: int = 8,
                seed_base: int = 0, n_steps: int = 400,
                measure_last: int = 150) -> Dict[str, Any]:
    """Sweep the informed fraction ``p_inf`` at fixed N; return the accuracy-vs-fraction
    curve (mean accuracy per realised fraction over ``n_seeds``)."""
    arms = [run_many_seeds(n, p_inf=p, omega=omega, goal_angle=goal_angle, s=s, zor=zor,
                           dzoo=dzoo, zoa_width=zoa_width, theta_max=theta_max, sigma=sigma,
                           init_radius=init_radius, n_seeds=n_seeds, seed_base=seed_base,
                           n_steps=n_steps, measure_last=measure_last)
            for p in p_values]
    return {
        "n": n, "omega": omega, "n_seeds": n_seeds,
        "target_p_inf": [a["target_p_inf"] for a in arms],
        "realised_p_inf": [a["realised_p_inf"] for a in arms],
        "n_informed": [a["n_informed"] for a in arms],
        "mean_accuracy": [a["mean_accuracy"] for a in arms],
        "std_accuracy": [a["std_accuracy"] for a in arms],
        "min_accuracy": [a["min_accuracy"] for a in arms],
        "arms": arms,
    }


def fraction_to_reach_accuracy(sweep: Dict[str, Any], target_accuracy: float) -> Optional[float]:
    """The smallest realised informed fraction in a ``sweep_p_inf`` result whose MEAN accuracy
    reaches ``target_accuracy``. Scans the fractions in ascending order (the sweep is built in
    ascending p order) and returns the first realised fraction at/above the bar, or None if no
    fraction in the sweep reaches it. This is the load-bearing 'leader economy' quantity."""
    pairs = sorted(zip(sweep["realised_p_inf"], sweep["mean_accuracy"]), key=lambda t: t[0])
    for frac, acc in pairs:
        if acc >= target_accuracy:
            return frac
    return None
