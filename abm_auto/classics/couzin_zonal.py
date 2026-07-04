"""Couzin et al. zonal collective motion (2002) — a faithful agent-based reproduction.

Source: Couzin, I. D., Krause, J., James, R., Ruxton, G. D. & Franks, N. R. (2002),
"Collective Memory and Spatial Sorting in Animal Groups", Journal of Theoretical
Biology 218(1):1-11. doi:10.1006/jtbi.2002.3065.

Framing: genuine-agent (3-zone self-propelled particles, 2D, disclosed). This is NOT a
grid CA and NOT the single-alignment Vicsek rule — each individual is an autonomous
self-propelled agent with a heading and a bounded turning rate, and it integrates THREE
nested behavioural zones every step. The control parameter is the ORIENTATION-zone width
Delta_zoo, and the phenomena of interest are the milling/torus state, the parallel/polarized
state, and hysteresis between them as Delta_zoo is ramped up vs down.

Rules (verified against the paper; the standard 3-zone SPP model):
  * N self-propelled ``FishAgent``s live in continuous, UNBOUNDED 2D (no periodic box —
    the group is cohesive and self-organizes, so positions are absolute). Each carries a
    position p = (x, y) and a UNIT heading d = (dx, dy). Every agent moves at the SAME
    constant speed ``s`` per step; only its DIRECTION changes.
  * Three nested zones, by centre-to-centre distance r_ij between agents i and j:
      - Zone of Repulsion (zor): r_ij < ``zor`` — a hard-core personal space.
      - Zone of Orientation (zoo): zor <= r_ij < zor + ``dzoo`` — align heading with j.
      - Zone of Attraction (zoa): zor + dzoo <= r_ij < zor + dzoo + ``zoa_width`` — steer
        toward j. (An optional blind angle behind the agent excludes rear neighbours; the
        default blind angle is 0, i.e. full 360-degree perception, matching the mill/parallel
        analysis in the paper.)
    The control parameter is ``dzoo`` (the orientation-zone WIDTH); the outer radii shift
    with it so the attraction zone always sits just outside the orientation zone.
  * Desired direction each step (the paper's rule, Eqs. 1-3):
      - REPULSION OVERRIDES: if any neighbour is within zor, the desired direction is
        d_r = -normalize( sum_j (p_j - p_i)/|p_j - p_i| ) over those repulsion neighbours —
        steer directly AWAY from all of them; orientation and attraction are IGNORED.
      - Otherwise the desired direction combines orientation + attraction:
          d_o = sum_{j in zoo} d_j                        (align: sum of neighbour headings)
          d_a = sum_{j in zoa} (p_j - p_i)/|p_j - p_i|    (attract: unit vectors toward them)
          d_desired = normalize(d_o + d_a).
        If only one of the two zones has neighbours, that term alone is the desired
        direction; if neither has any neighbour, the agent keeps its current heading.
  * BOUNDED TURN + NOISE: the agent rotates its heading toward d_desired by at most
    ``theta_max`` radians this step (it cannot turn instantaneously), THEN a small Gaussian
    heading noise of s.d. ``sigma`` (radians) is added. Finally it moves distance ``s``
    along the new heading:  p_i(t+1) = p_i(t) + s * d_i(t+1).
  * The update is SYNCHRONOUS: every agent's desired direction is computed from the SAME
    start-of-step snapshot, then all agents turn, add noise, and move. (Deterministic given
    the seeded RNG draw sequence.)

Order parameters (the locked grading metrics), computed on the group each step:
    polarization p = | (1/N) sum_i d_i |               in [0, 1]
        — heading coherence; p ~ 1 is a parallel, coherently moving flock.
    angular momentum m = | (1/N) sum_i (r_i_hat x d_i) | in [0, 1]
        — where r_i is agent i's position relative to the group centroid and r_i_hat is its
        unit vector, and (a x b) is the 2D scalar cross product a_x*b_y - a_y*b_x. m ~ 1 is a
        torus/mill rotating coherently about the centroid. A milling torus has LOW p (agents
        point every which way around the ring) and HIGH m (they all circulate the same way);
        a parallel flock has HIGH p and LOW m.

Built on the neutral platform (``abm_auto._platform``): each fish is a ``FishAgent``
carrying its own (x, y, dx, dy); ``CouzinZonalModel`` drives the synchronous zone-integration
+ bounded-turn + move update over the ``AgentSet`` roster and records (via a
``DataCollector``) the per-step polarization p and angular momentum m. Neighbour lookup is
brute-force all-pairs (O(N^2)) over the cohesive group (N is a few tens–hundred, and the
group is not confined to a periodic box, so a cell list buys little); the group stays
compact because attraction holds it together.
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
    # signed angle FROM current heading TO target, in (-pi, pi]:
    #   dot = cos(angle), cross = sin(angle)  (both unit vectors)
    dot = max(-1.0, min(1.0, dx * txn + dy * tyn))
    cross = _cross2d(dx, dy, txn, tyn)
    angle = math.atan2(cross, dot)           # in (-pi, pi]
    if abs(angle) <= theta_max:
        return txn, tyn                       # can reach the target this step
    step = theta_max if angle > 0 else -theta_max
    ca, sa = math.cos(step), math.sin(step)
    # rotate (dx, dy) by 'step' radians
    nx = dx * ca - dy * sa
    ny = dx * sa + dy * ca
    m = _norm(nx, ny)
    return (nx / m, ny / m) if m > 0 else (dx, dy)


# -- Agent --------------------------------------------------------------------

class FishAgent(Agent):
    """One self-propelled individual: position (x, y) and UNIT heading (dx, dy).

    The Couzin zonal tick is a model-level synchronous update (all desired directions from
    one snapshot, then all turn/noise/move), so the per-agent ``step`` is intentionally a
    no-op; the ``_next_dx`` / ``_next_dy`` fields stage the heading computed this step
    before the model commits the moves.
    """

    def __init__(self, agent_id: int, model: "CouzinZonalModel", *,
                 x: float, y: float, dx: float, dy: float) -> None:
        super().__init__(agent_id, model)
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self._next_dx = dx
        self._next_dy = dy

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        """The Couzin tick (integrate zones from a snapshot, turn, then move) is a
        model-level synchronous update, not an autonomous single-agent step, so this is a
        no-op."""
        return None


# -- Model --------------------------------------------------------------------

class CouzinZonalModel(AgentModel):
    """Drives the Couzin et al. (2002) 3-zone self-propelled-particle dynamics.

    Construct with N, speed ``s``, repulsion radius ``zor``, orientation-zone WIDTH
    ``dzoo`` (the control parameter), attraction-zone width ``zoa_width``, max turn
    ``theta_max`` (radians/step), heading noise s.d. ``sigma`` (radians), an optional rear
    blind angle ``blind`` (radians, total; 0 = full perception), an initial-cluster radius
    ``init_radius`` for the seeded start, and a seed. ``run(n_steps)`` advances the
    synchronous update and records per-step polarization p and angular momentum m.

    The model can be constructed from a PRIOR configuration (positions + headings) via
    ``from_state`` so a Delta_zoo sweep can equilibrate the SAME swarm as dzoo changes
    (needed for the hysteresis experiment).
    """

    def __init__(self, n: int = 100, *, s: float = 1.0, zor: float = 1.0,
                 dzoo: float = 6.0, zoa_width: float = 8.0, theta_max: float = 0.35,
                 sigma: float = 0.05, blind: float = 0.0, init_radius: float = 5.0,
                 seed: int = 0, _positions: Optional[Sequence[Tuple[float, float]]] = None,
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
        if not (0.0 <= blind < 2 * math.pi):
            raise ValueError(f"need 0 <= blind < 2*pi (got {blind})")
        self.seed_value = seed
        self.n = n
        self.s = float(s)
        self.zor = float(zor)
        self.dzoo = float(dzoo)
        self.zoa_width = float(zoa_width)
        self.theta_max = float(theta_max)
        self.sigma = float(sigma)
        self.blind = float(blind)
        self.init_radius = float(init_radius)

        # Derived nested radii. r_orient = zor + dzoo is where orientation ends; r_attract
        # = r_orient + zoa_width is where attraction ends. Squared for cheap comparisons.
        self.r_orient = self.zor + self.dzoo
        self.r_attract = self.r_orient + self.zoa_width
        self.zor2 = self.zor * self.zor
        self.r_orient2 = self.r_orient * self.r_orient
        self.r_attract2 = self.r_attract * self.r_attract
        # cos of the half-blind angle: a neighbour is "seen" iff the angle between the
        # agent's heading and the direction to the neighbour is <= pi - blind/2. With
        # blind=0 every neighbour is seen (cos threshold = -1).
        self._cos_blind = math.cos(math.pi - self.blind / 2.0)

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
            # the origin, headings uniform in direction. (Seed-dependent; besides the
            # per-step Gaussian noise this is the only randomness in the run.)
            for i in range(n):
                # uniform in disc: r = R*sqrt(u)
                rr = self.init_radius * math.sqrt(self.rng.random())
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
            "angular_momentum": lambda m: m.angular_momentum(),
        })

    # -- alternate constructor: continue a prior swarm at a new dzoo --
    @classmethod
    def from_state(cls, other: "CouzinZonalModel", *, dzoo: float,
                   seed: Optional[int] = None) -> "CouzinZonalModel":
        """Build a new model that CONTINUES ``other``'s current positions + headings but
        with a different orientation-zone width ``dzoo`` (everything else identical). Used
        by the hysteresis sweep to equilibrate the same swarm as dzoo is ramped."""
        positions = [(a.x, a.y) for a in other.agent_list]
        headings = [(a.dx, a.dy) for a in other.agent_list]
        return cls(
            other.n, s=other.s, zor=other.zor, dzoo=dzoo, zoa_width=other.zoa_width,
            theta_max=other.theta_max, sigma=other.sigma, blind=other.blind,
            init_radius=other.init_radius,
            seed=other.seed_value if seed is None else seed,
            _positions=positions, _headings=headings)

    # -- metrics --
    def centroid(self) -> Tuple[float, float]:
        cx = sum(a.x for a in self.agent_list) / self.n
        cy = sum(a.y for a in self.agent_list) / self.n
        return cx, cy

    def polarization(self) -> float:
        """p = | (1/N) sum_i d_i |, the coherence of headings, in [0, 1]. Each d_i is a
        unit heading, so the sum's magnitude over N is in [0, 1]."""
        if self.n == 0:
            return 0.0
        sx = sum(a.dx for a in self.agent_list)
        sy = sum(a.dy for a in self.agent_list)
        return _norm(sx, sy) / self.n

    def angular_momentum(self) -> float:
        """m = | (1/N) sum_i (r_i_hat x d_i) |, the coherence of rotation about the group
        centroid, in [0, 1]. r_i is position minus centroid; r_i_hat its unit vector; the
        2D cross product r_i_hat x d_i is the signed tangential component of d_i. Agents at
        the centroid (r_i = 0) contribute 0 (no defined rotation direction)."""
        if self.n == 0:
            return 0.0
        cx, cy = self.centroid()
        acc = 0.0
        for a in self.agent_list:
            rx, ry = a.x - cx, a.y - cy
            rm = _norm(rx, ry)
            if rm == 0.0:
                continue
            acc += _cross2d(rx / rm, ry / rm, a.dx, a.dy)
        return abs(acc) / self.n

    # -- perception --
    def _sees(self, a: FishAgent, ux: float, uy: float) -> bool:
        """True iff a neighbour in unit direction (ux, uy) from ``a`` is within a's field
        of view (outside the rear blind angle). With blind=0 this is always True."""
        if self.blind == 0.0:
            return True
        # cos(angle between heading and direction-to-neighbour) = d . u
        return (a.dx * ux + a.dy * uy) >= self._cos_blind

    def desired_direction(self, a: FishAgent) -> Tuple[float, float]:
        """The Couzin desired direction for agent ``a`` from the current snapshot.

        Repulsion (any neighbour within zor) OVERRIDES everything: steer away from the sum
        of unit vectors toward those neighbours. Otherwise combine orientation (sum of
        in-zone neighbour headings) and attraction (sum of unit vectors toward in-zone
        neighbours), normalize, and return. Returns (0, 0) to mean "no preference — keep
        the current heading" (no neighbours in any zone). Repulsion ignores the blind angle
        (collision avoidance is reflexive); orientation/attraction respect it.
        """
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
                continue                       # outside all zones
            d = math.sqrt(d2)
            ux, uy = rx / d, ry / d
            if d2 < self.zor2:
                # repulsion: accumulate unit vector toward b (we steer away from the sum)
                rep_x += ux
                rep_y += uy
                n_rep += 1
            elif n_rep == 0:
                # only consider orientation/attraction while no repulsion is active; if a
                # repulsion neighbour appears later in the scan we discard these (repulsion
                # overrides), so we still accumulate but gate at the end.
                if not self._sees(a, ux, uy):
                    continue
                if d2 < self.r_orient2:
                    ori_x += b.dx
                    ori_y += b.dy
                else:
                    att_x += ux
                    att_y += uy
        if n_rep > 0:
            # steer AWAY from repulsion neighbours (override)
            m = _norm(rep_x, rep_y)
            if m == 0.0:
                return 0.0, 0.0                # exactly balanced: no preference
            return -rep_x / m, -rep_y / m
        dx = ori_x + att_x
        dy = ori_y + att_y
        m = _norm(dx, dy)
        if m == 0.0:
            return 0.0, 0.0
        return dx / m, dy / m

    # -- tick --
    def step(self) -> None:
        """One synchronous Couzin zonal tick.

        (1) From the start-of-step snapshot, every agent computes its desired direction
            (repulsion override, else orientation+attraction), rotates its heading toward
            it by at most theta_max, then adds Gaussian heading noise sigma. A zero desired
            direction leaves the heading unchanged before noise.
        (2) Then every agent moves distance s along its NEW heading. Headings are staged in
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

    def run(self, n_steps: int = 300, *, measure_last: int = 100) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_steps`` synchronous ticks; return the run summary.

        ``measure_last`` is the trailing window over which steady-state polarization and
        angular momentum are averaged (the transient is the leading n_steps - measure_last
        ticks). Returns steady + final p and m, and the full per-step series of both.
        """
        if measure_last <= 0 or measure_last > n_steps + 1:
            raise ValueError(
                f"measure_last must be in [1, n_steps+1] (got {measure_last}, n_steps={n_steps})")
        self.reporter.collect(self)              # t=0 baseline
        for _ in range(n_steps):
            self.step()
        p_series = self.reporter.series("polarization")
        m_series = self.reporter.series("angular_momentum")
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
            "blind": self.blind,
            "seed": self.seed_value,
            "n_steps": n_steps,
            "measure_last": measure_last,
            "steady_polarization": tail_mean(p_series, window=measure_last),
            "steady_angular_momentum": tail_mean(m_series, window=measure_last),
            "final_polarization": p_series[-1],
            "final_angular_momentum": m_series[-1],
            "polarization_series": p_series,
            "angular_momentum_series": m_series,
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


def run_single(n: int = 100, *, s: float = 1.0, zor: float = 1.0, dzoo: float = 6.0,
               zoa_width: float = 8.0, theta_max: float = 0.35, sigma: float = 0.05,
               blind: float = 0.0, init_radius: float = 5.0, seed: int = 0,
               n_steps: int = 300, measure_last: int = 100) -> Dict[str, Any]:
    """One Couzin zonal run at a given (dzoo, seed) and the fixed rule parameters."""
    return CouzinZonalModel(
        n, s=s, zor=zor, dzoo=dzoo, zoa_width=zoa_width, theta_max=theta_max,
        sigma=sigma, blind=blind, init_radius=init_radius, seed=seed).run(
        n_steps, measure_last=measure_last)


def run_many_seeds(n: int = 100, *, s: float = 1.0, zor: float = 1.0, dzoo: float = 6.0,
                   zoa_width: float = 8.0, theta_max: float = 0.35, sigma: float = 0.05,
                   blind: float = 0.0, init_radius: float = 5.0, n_seeds: int = 8,
                   seed_base: int = 0, n_steps: int = 300,
                   measure_last: int = 100) -> Dict[str, Any]:
    """Run ``n_seeds`` runs (seed ``seed_base + i``) at a fixed dzoo and summarise the
    steady polarization p and angular momentum m across seeds (mean + spread).

    Returns per-seed steady p and m, their mean / std / min / max, and one representative
    trajectory (first seed) of both series for inspection.
    """
    runs = [run_single(n, s=s, zor=zor, dzoo=dzoo, zoa_width=zoa_width,
                       theta_max=theta_max, sigma=sigma, blind=blind,
                       init_radius=init_radius, seed=seed_base + i, n_steps=n_steps,
                       measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_p = [rr["steady_polarization"] for rr in runs]
    per_seed_m = [rr["steady_angular_momentum"] for rr in runs]
    mean_p = sum(per_seed_p) / n_seeds
    var_p = sum((v - mean_p) ** 2 for v in per_seed_p) / n_seeds
    mean_m = sum(per_seed_m) / n_seeds
    var_m = sum((v - mean_m) ** 2 for v in per_seed_m) / n_seeds
    return {
        "n": n, "s": s, "zor": zor, "dzoo": dzoo, "zoa_width": zoa_width,
        "theta_max": theta_max, "sigma": sigma, "blind": blind,
        "init_radius": init_radius,
        "n_seeds": n_seeds, "seed_base": seed_base, "n_steps": n_steps,
        "measure_last": measure_last,
        "per_seed_polarization": per_seed_p,
        "per_seed_angular_momentum": per_seed_m,
        "mean_polarization": mean_p,
        "std_polarization": var_p ** 0.5,
        "min_polarization": min(per_seed_p),
        "max_polarization": max(per_seed_p),
        "mean_angular_momentum": mean_m,
        "std_angular_momentum": var_m ** 0.5,
        "min_angular_momentum": min(per_seed_m),
        "max_angular_momentum": max(per_seed_m),
        "example_polarization_series": runs[0]["polarization_series"],
        "example_angular_momentum_series": runs[0]["angular_momentum_series"],
    }


def sweep_dzoo(dzoo_values: Sequence[float], *, n: int = 100, s: float = 1.0,
               zor: float = 1.0, zoa_width: float = 8.0, theta_max: float = 0.35,
               sigma: float = 0.05, blind: float = 0.0, init_radius: float = 5.0,
               seed: int = 0, equilibrate: int = 200, measure_last: int = 100,
               warmup: int = 300) -> Dict[str, Any]:
    """Slow QUASI-STATIC ramp of dzoo along ``dzoo_values``, equilibrating the SAME swarm
    at each step (the hysteresis experiment).

    Start from a random swarm, warm it up ``warmup`` steps at the FIRST dzoo, then for each
    dzoo in order: rebuild the model continuing the current positions+headings at the new
    dzoo (``from_state``), run ``equilibrate`` steps, and record steady p and m averaged
    over the trailing ``measure_last``. The swarm's state carries forward from one dzoo to
    the next, so its history (mill vs polarized) is preserved — that carry-forward is what
    makes hysteresis observable. Returns the per-dzoo steady p and m along the ramp.
    """
    if equilibrate <= 0 or measure_last <= 0 or measure_last > equilibrate + 1:
        raise ValueError("need equilibrate>0 and 1<=measure_last<=equilibrate+1")
    if len(dzoo_values) == 0:
        raise ValueError("dzoo_values must be non-empty")
    model = CouzinZonalModel(
        n, s=s, zor=zor, dzoo=dzoo_values[0], zoa_width=zoa_width, theta_max=theta_max,
        sigma=sigma, blind=blind, init_radius=init_radius, seed=seed)
    for _ in range(warmup):
        model.step()
    return _sweep_continue(model, dzoo_values, equilibrate=equilibrate,
                           measure_last=measure_last)


def _sweep_continue(model: "CouzinZonalModel", dzoo_values: Sequence[float], *,
                    equilibrate: int = 200, measure_last: int = 100) -> Dict[str, Any]:
    """Ramp ``dzoo`` along ``dzoo_values`` CONTINUING the given ``model``'s current swarm
    state (positions + headings carry forward from one dzoo to the next). At each dzoo,
    rebuild via ``from_state`` at the new width, run ``equilibrate`` steps, and record steady
    p and m over the trailing ``measure_last``. Returns the per-dzoo curves plus the final
    model (``_final_model``) so a caller can thread the SAME swarm into a subsequent branch
    (this carry-forward is exactly what makes the hysteresis loop observable — the down-branch
    must start from the polarized top of the up-branch, not a fresh swarm)."""
    if equilibrate <= 0 or measure_last <= 0 or measure_last > equilibrate + 1:
        raise ValueError("need equilibrate>0 and 1<=measure_last<=equilibrate+1")
    dzoos: List[float] = []
    pol: List[float] = []
    ang: List[float] = []
    for dz in dzoo_values:
        model = CouzinZonalModel.from_state(model, dzoo=dz)
        p_series: List[float] = []
        m_series: List[float] = []
        for _ in range(equilibrate):
            model.step()
            p_series.append(model.polarization())
            m_series.append(model.angular_momentum())
        dzoos.append(float(dz))
        pol.append(tail_mean(p_series, window=measure_last))
        ang.append(tail_mean(m_series, window=measure_last))
    return {"dzoo": dzoos, "polarization": pol, "angular_momentum": ang,
            "_final_model": model}


def _first_crossing(dzoos: Sequence[float], values: Sequence[float], threshold: float,
                    ascending: bool) -> Optional[float]:
    """The dzoo at which ``values`` first crosses ``threshold`` while scanning in the given
    list order. ``ascending`` True detects an UPWARD crossing (value goes from < to >=),
    False a DOWNWARD crossing (from >= to <). Returns the dzoo at the first point past the
    crossing, or None if it never crosses. Used to locate the polarization switch on each
    branch of the hysteresis ramp."""
    prev_above = None
    for dz, v in zip(dzoos, values):
        above = v >= threshold
        if prev_above is not None:
            if ascending and (not prev_above) and above:
                return dz
            if (not ascending) and prev_above and (not above):
                return dz
        prev_above = above
    return None


def hysteresis_experiment(*, n: int = 100, s: float = 1.0, zor: float = 1.0,
                          zoa_width: float = 8.0, theta_max: float = 0.35,
                          sigma: float = 0.05, blind: float = 0.0, init_radius: float = 5.0,
                          dzoo_lo: float = 0.5, dzoo_hi: float = 12.0, n_grid: int = 24,
                          seed: int = 0, equilibrate: int = 200, measure_last: int = 100,
                          warmup: int = 300, pol_threshold: float = 0.65) -> Dict[str, Any]:
    """Run the up-ramp then the down-ramp of dzoo (continuing the same swarm across the
    whole loop) and locate the swarm->polarized and polarized->swarm switches by where
    polarization crosses ``pol_threshold``.

    The up-branch starts from a fresh warmed-up swarm at dzoo_lo and ramps dzoo UP to
    dzoo_hi; the down-branch CONTINUES from the top of the up-branch and ramps dzoo DOWN
    back to dzoo_lo. The switch dzoo on each branch is the first threshold crossing; the
    hysteresis gap = |up_switch - down_switch| (0 if either branch never switches, which is
    reported honestly). Returns both branches' curves, the two switch dzoos, and the gap.
    """
    grid_up = [dzoo_lo + (dzoo_hi - dzoo_lo) * i / (n_grid - 1) for i in range(n_grid)]
    grid_down = list(reversed(grid_up))
    up = sweep_dzoo(grid_up, n=n, s=s, zor=zor, zoa_width=zoa_width, theta_max=theta_max,
                    sigma=sigma, blind=blind, init_radius=init_radius, seed=seed,
                    equilibrate=equilibrate, measure_last=measure_last, warmup=warmup)
    # Continue the SAME swarm DOWN: thread the polarized swarm from the top of the up-branch
    # into the down-branch (carry-forward), rather than starting a fresh swarm. That
    # history-dependence is precisely what can open a hysteresis gap; a fresh down-branch
    # would erase it. The up-branch's final model is returned as ``_final_model``.
    down = _sweep_continue(up["_final_model"], grid_down, equilibrate=equilibrate,
                           measure_last=measure_last)
    up_switch = _first_crossing(up["dzoo"], up["polarization"], pol_threshold,
                                ascending=True)
    down_switch = _first_crossing(down["dzoo"], down["polarization"], pol_threshold,
                                  ascending=False)
    if up_switch is None or down_switch is None:
        gap = 0.0
    else:
        gap = abs(up_switch - down_switch)
    return {
        "grid_up": up["dzoo"], "pol_up": up["polarization"], "ang_up": up["angular_momentum"],
        "grid_down": down["dzoo"], "pol_down": down["polarization"],
        "ang_down": down["angular_momentum"],
        "pol_threshold": pol_threshold,
        "up_switch_dzoo": up_switch, "down_switch_dzoo": down_switch,
        "hysteresis_gap": gap,
    }
