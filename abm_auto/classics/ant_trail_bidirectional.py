"""Ant-trail flow CA (Chowdhury, Guttal, Nishinari & Schadschneider 2002) — a
faithful reproduction of a pheromone-coupled single-lane exclusion process.

Source: Chowdhury, D., Guttal, V., Nishinari, K. & Schadschneider, A. (2002)
"A cellular-automata model of flow in ant trails: non-monotonic variation of
speed with density", J. Phys. A: Math. Gen. 35(41):L573-L577.
doi:10.1088/0305-4470/35/41/103.

IMPORTANT (honesty, binds the FINDINGS): this is a CELLULAR AUTOMATON (CA,
disclosed). There is no agent roster that perceives / decides / acts and no
per-agent scheduler; it is a synchronous (parallel) update rule applied to two
1D fields on a periodic ring. We disclose the CA framing exactly as the
btw_sandpile / game_of_life reproductions disclose theirs. The lock-first +
honest-verdict + L3-bundle discipline still fully applies. The model IS a
genuine exclusion process (hard-core ants, at most one per site) coupled to an
evaporating stigmergic pheromone field — the mechanism of the paper.

Rules (the ant-trail CA, single-lane / uni-directional, NaSch-like vmax = 1):
  * A periodic RING of ``L`` sites (default 500). Two binary fields:
        occ[i]  in {0, 1}  — 1 iff an ant occupies site i (hard-core exclusion).
        pher[i] in {0, 1}  — 1 iff site i carries a pheromone mark.
  * Each tick is a SYNCHRONOUS (parallel) update in two ordered sub-steps:

      (1) ANT HOP (exclusion). An ant at site i can hop to i+1 only if i+1 is
          currently empty (exclusion). Its hop probability depends on whether
          the target site AHEAD already carries pheromone:
                p_hop = Q   if pher[i+1] == 1   (pheromone ahead — follow trail)
                p_hop = q   if pher[i+1] == 0   (no trail — hesitant)
          with q < Q (defaults Q = 0.75, q = 0.25). All hops are decided from
          the FROZEN current configuration and applied together; because vmax=1
          and a target site is claimed by at most the single ant directly behind
          it, no two ants can land on the same site (the exclusion is exact).

      (2) PHEROMONE UPDATE (deposit then evaporate), applied AFTER the hops so it
          sees the NEW positions:
            - DEPOSIT: every site that an ant now occupies is marked pher = 1
              (ants lay/refresh pheromone on the trail under them).
            - EVAPORATE: a pheromone-marked site with NO ant on it loses its mark
              (pher -> 0) with probability f per tick. Marks under an ant never
              evaporate (they are continuously refreshed).
          This is the stigmergy: ants build a shared trail that decays at rate f
          when unused. Small f -> persistent trail (ants help the ant behind);
          f -> 1 -> the mark is gone almost immediately, recovering plain NaSch
          (vmax=1) with a single uniform hop probability.

Observable (the fundamental diagram):
  * mean velocity  <v>  = fraction of ants that actually hopped this tick,
    averaged over all measured post-transient ticks. (With vmax=1 a hop moves an
    ant exactly one site, so the per-ant displacement equals the hop indicator
    and <v> is the mean displacement per ant per tick.)
  * flow  q = rho * <v>  — the fundamental-diagram observable.
The pheromone coupling makes this diagram ANOMALOUS relative to plain NaSch:
because a moving ant leaves a fresh mark that speeds up the ant behind it, ants
form loose co-moving clusters and the mean velocity stays high (a "plateau")
over an intermediate density band, and the flow peak is pushed to higher
density — instead of the symmetric NaSch diagram peaking near rho ~ 0.5.

Determinism / locality: each ant reads only its own site and the site directly
ahead (a local neighbourhood on the ring); the only global coupling is the
shared occupancy + pheromone of the ring. One seeded RNG chain places the ants
and draws every hop / evaporation decision, so a run replays bit-for-bit from a
seed. NumPy is used only to vectorize the synchronous sweep; the result is the
canonical CA outcome.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

# Default hop probabilities (q < Q): pheromone ahead enhances the hop.
Q_DEFAULT = 0.75  # hop prob when the target site ahead carries pheromone
Q_LOW_DEFAULT = 0.25  # hop prob when the target site ahead is unmarked


# -- core CA: the ant-trail ring ------------------------------------------------

class AntTrailModel:
    """A pheromone-coupled single-lane exclusion process on a periodic ring.

    ``occ`` and ``pher`` are length-``L`` uint8 arrays (occupancy, pheromone).
    ``step`` performs one synchronous tick: parallel exclusion hops (with the
    pheromone-dependent hop probability) followed by the deposit + evaporation
    of the pheromone field. Deterministic given ``seed``.
    """

    def __init__(self, L: int = 500, rho: float = 0.3, *, Q: float = Q_DEFAULT,
                 q: float = Q_LOW_DEFAULT, f: float = 0.005, seed: int = 0) -> None:
        if L <= 0:
            raise ValueError("L must be positive")
        if not (0.0 < rho < 1.0):
            raise ValueError("rho must be in (0, 1)")
        if not (0.0 <= q <= 1.0) or not (0.0 <= Q <= 1.0):
            raise ValueError("Q and q must be in [0, 1]")
        if q > Q:
            raise ValueError("require q <= Q (pheromone must not slow ants down)")
        if not (0.0 <= f <= 1.0):
            raise ValueError("f must be in [0, 1]")
        self.L = int(L)
        self.rho = float(rho)
        self.Q = float(Q)
        self.q = float(q)
        self.f = float(f)
        self.rng = np.random.default_rng(seed)

        n = int(round(rho * L))
        n = max(0, min(L, n))
        self.n_ants = n
        # Place n ants at random distinct sites.
        self.occ = np.zeros(L, dtype=np.uint8)
        if n > 0:
            sites = self.rng.choice(L, size=n, replace=False)
            self.occ[sites] = 1
        # Pheromone starts wherever an ant sits (a consistent initial trail).
        self.pher = self.occ.copy()

    # -- one synchronous tick --------------------------------------------------

    def step(self) -> int:
        """Advance one tick. Returns the number of ants that hopped this tick.

        Parallel exclusion hop: an ant at i may hop to i+1 iff i+1 is currently
        empty; it does so with probability Q if pher[i+1]==1 else q. Because
        vmax=1 on a ring, the ant directly behind an empty target is the ONLY
        ant that can move into it, so accepting every drawn hop is collision-free
        (exclusion is exact — no conflict resolution needed).
        """
        L = self.L
        occ = self.occ
        pher = self.pher

        ahead = np.roll(occ, -1)          # occ[i+1]
        pher_ahead = np.roll(pher, -1)    # pher[i+1]

        # Candidate movers: occupied sites whose next site is empty.
        can_move = (occ == 1) & (ahead == 0)
        # Per-site hop probability depends on pheromone at the TARGET (i+1).
        p_hop = np.where(pher_ahead == 1, self.Q, self.q)
        draws = self.rng.random(L)
        movers = can_move & (draws < p_hop)   # ants (indexed by current site i) that hop

        n_moved = int(movers.sum())
        if n_moved > 0:
            # Apply the parallel move: clear moved-from sites, set moved-to sites.
            new_occ = occ.copy()
            new_occ[movers] = 0
            dest = np.roll(movers, 1)          # site i+1 for each mover at i
            new_occ[dest] = 1
            self.occ = new_occ
            occ = new_occ

        # Pheromone update (deposit then evaporate), on the NEW positions.
        # Deposit: every occupied site is (re)marked.
        pher = pher | occ
        # Evaporate: marked sites with no ant lose the mark with prob f.
        evap_candidates = (pher == 1) & (occ == 0)
        if self.f > 0.0 and evap_candidates.any():
            evap_draws = self.rng.random(L)
            evaporate = evap_candidates & (evap_draws < self.f)
            pher = pher.copy()
            pher[evaporate] = 0
        self.pher = pher.astype(np.uint8)

        return n_moved

    # -- observables -----------------------------------------------------------

    def occupied_fraction(self) -> float:
        return float(self.occ.mean())

    def pheromone_fraction(self) -> float:
        return float(self.pher.mean())


# -- single-density steady-state run -------------------------------------------

def run_density(L: int, rho: float, *, Q: float = Q_DEFAULT, q: float = Q_LOW_DEFAULT,
                f: float = 0.005, seed: int = 0, transient: int = 2000,
                measure: int = 2000) -> Dict[str, Any]:
    """Run one density to steady state and tail-average the mean velocity.

    Burns a ``transient`` of ticks (not measured), then averages the hop
    fraction over ``measure`` ticks. Mean velocity <v> = (total hops) /
    (n_ants * measure) = mean fraction of ants that moved per tick. flow =
    rho * <v>. Deterministic given ``seed``.
    """
    m = AntTrailModel(L, rho, Q=Q, q=q, f=f, seed=seed)
    n_ants = m.n_ants
    for _ in range(transient):
        m.step()
    total_hops = 0
    pher_frac_sum = 0.0
    for _ in range(measure):
        total_hops += m.step()
        pher_frac_sum += m.pheromone_fraction()
    if n_ants == 0 or measure == 0:
        mean_v = 0.0
    else:
        mean_v = total_hops / (n_ants * measure)
    flow = rho * mean_v
    return {
        "L": L,
        "rho": rho,
        "n_ants": n_ants,
        "Q": Q,
        "q": q,
        "f": f,
        "seed": seed,
        "transient": transient,
        "measure": measure,
        "mean_velocity": mean_v,
        "flow": flow,
        "mean_pheromone_fraction": pher_frac_sum / measure if measure else 0.0,
    }


def fundamental_diagram(L: int, densities: Sequence[float], *, Q: float = Q_DEFAULT,
                        q: float = Q_LOW_DEFAULT, f: float = 0.005,
                        seeds: Sequence[int] = (0,), transient: int = 2000,
                        measure: int = 2000) -> Dict[str, Any]:
    """Fundamental diagram <v>(rho) and flow(rho) over a density grid.

    For each density, runs every seed and averages the (seed-mean) velocity and
    flow. Returns the per-density mean velocity + flow arrays, the argmax-flow
    density rho*, and per-seed detail. Deterministic given the seed set.
    """
    densities = list(densities)
    seeds = list(seeds)
    mean_v = []
    flow = []
    pher = []
    per_seed_v = []
    for rho in densities:
        vs = []
        fs = []
        phs = []
        for s in seeds:
            r = run_density(L, rho, Q=Q, q=q, f=f, seed=s, transient=transient,
                            measure=measure)
            vs.append(r["mean_velocity"])
            fs.append(r["flow"])
            phs.append(r["mean_pheromone_fraction"])
        mean_v.append(float(np.mean(vs)))
        flow.append(float(np.mean(fs)))
        pher.append(float(np.mean(phs)))
        per_seed_v.append(vs)
    flow_arr = np.asarray(flow)
    peak_idx = int(np.argmax(flow_arr))
    return {
        "L": L,
        "densities": densities,
        "seeds": seeds,
        "Q": Q,
        "q": q,
        "f": f,
        "transient": transient,
        "measure": measure,
        "mean_velocity": mean_v,
        "flow": flow,
        "mean_pheromone_fraction": pher,
        "per_seed_velocity": per_seed_v,
        "peak_flow": float(flow_arr[peak_idx]),
        "rho_star": float(densities[peak_idx]),
        "peak_index": peak_idx,
    }


# -- band-variation metric (P1 / P3) -------------------------------------------

def velocity_band_variation(densities: Sequence[float], mean_v: Sequence[float],
                            lo: float = 0.2, hi: float = 0.5) -> Dict[str, Any]:
    """Relative variation of <v> across the density band [lo, hi].

    Selects the grid densities within [lo, hi] (inclusive, with a tiny epsilon
    to admit endpoints landing exactly on the grid) and returns the relative
    spread (max - min) / max over that band, plus the band's min/max velocity.
    A flat "plateau" gives a small relative variation; a monotone decline gives
    a large one. Returns variation = 0.0 if fewer than two band points.
    """
    densities = np.asarray(list(densities), dtype=float)
    mean_v = np.asarray(list(mean_v), dtype=float)
    eps = 1e-9
    mask = (densities >= lo - eps) & (densities <= hi + eps)
    band_v = mean_v[mask]
    band_rho = densities[mask]
    if band_v.size < 2:
        return {"variation": 0.0, "band_min_v": float(band_v.min()) if band_v.size else 0.0,
                "band_max_v": float(band_v.max()) if band_v.size else 0.0,
                "n_band": int(band_v.size), "band_densities": band_rho.tolist(),
                "band_velocities": band_v.tolist()}
    vmax = float(band_v.max())
    vmin = float(band_v.min())
    variation = (vmax - vmin) / vmax if vmax > 0 else 0.0
    return {
        "variation": variation,
        "band_min_v": vmin,
        "band_max_v": vmax,
        "n_band": int(band_v.size),
        "band_densities": band_rho.tolist(),
        "band_velocities": band_v.tolist(),
    }
