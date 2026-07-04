"""Fermi-rule spatial Prisoner's Dilemma (Szabó & Tőke 1998) — a faithful
agent-based reproduction.

Source: Szabó, G. & Tőke, C. (1998) "Evolutionary prisoner's dilemma game on a
square lattice", Phys. Rev. E 58:69-73. doi:10.1103/PhysRevE.58.69.

This is the SAME spatial PD as Nowak-May (a square lattice of pure cooperators /
defectors), but with a fundamentally different, STOCHASTIC update — the Fermi
(pairwise-comparison) rule — which puts the model in the directed-percolation
universality class and gives it three properties the deterministic best-takes-over
model of ``nowak_may_pd`` does NOT have:

  * a continuous (second-order) C→extinction transition, not a discrete step;
  * a selection-noise parameter K that the update depends on;
  * an optimal intermediate K (noise NON-monotonicity of the survival threshold).

Rules (verified against the paper):

  * Square lattice L x L with PERIODIC (toroidal) boundaries; every site is a pure
    cooperator (C=1) or defector (D=0). Random 50/50 initial placement.
  * Weak PD payoff matrix (Szabó-Tőke rescaling): against EACH neighbour,
        R = 1   (both cooperate)
        T = b   (I defect, partner cooperates)     b > 1  (temptation)
        P = 0   (both defect)
        S = 0   (I cooperate, partner defects)
    A cooperator scores R=1 per C partner, 0 per D partner; a defector scores
    T=b per C partner, 0 per D partner.
  * NEIGHBOURHOOD: von Neumann (z=4: N,E,S,W). The 1998 PRIMARY model plays the
    z=4 neighbours AND ITSELF (``self_interaction=True``). Self-interaction adds a
    site's own-strategy self-game to its accumulated payoff (R for a C, P=0 for a
    D). It is a fixed modelling choice of the paper, exposed as a flag so P3 can be
    run on the clean no-self-interaction spec (see below), NOT so it is tuned.
  * UPDATE: random-sequential FERMI (pairwise-comparison). One elementary step:
    pick a random focal site x and one of its random neighbours y; x adopts y's
    strategy with probability
        W = 1 / (1 + exp(-(E_y - E_x) / K)),
    where E_x, E_y are the two sites' accumulated payoffs and K > 0 is the
    selection noise (temperature). A Monte-Carlo SWEEP is L*L elementary steps
    (on average one update attempt per site). This is stochastic and irreversible-
    looking: unlike best-takes-over, a lower-scoring strategy is copied with
    nonzero probability, and a higher-scoring one is NOT copied with certainty.

Order parameter (the locked grading metric): the stationary cooperator density
    c = fraction of C sites,
averaged over the last ``measure_sweeps`` MC sweeps after a ``transient`` of
sweeps (the finite-size / finite-time fluctuating steady state).

Vectorisation (keeps L=400-500 tractable): a true random-sequential sweep is
L*L sequential single-site updates. We realise one sweep as L*L elementary steps
processed in vectorised BATCHES over a random permutation of focal sites, each
with an independently drawn random neighbour direction and an independent uniform
for the Fermi acceptance. To keep the update genuinely asynchronous (a focal and
its chosen neighbour must not both be updated inside one batch from the same
frozen snapshot — that would let two sites copy each other's *stale* strategy),
each batch is filtered to a conflict-free set: within a batch no site appears as
BOTH a focal and a chosen neighbour, and no two focals share a chosen neighbour.
Payoffs are recomputed from the live lattice before each batch, so a focal always
compares against the current strategies of its four neighbours. The result is a
faithful random-sequential dynamics (each elementary step reads the live lattice
and commits immediately) at numpy speed.

Built on the neutral platform (``abm_auto._platform``): the lattice is held on a
``FermiSpatialPDModel`` (an ``AgentModel``) whose ``step`` performs one MC sweep and
whose ``DataCollector`` records the per-sweep cooperator density. Individual sites
are represented compactly as a numpy array rather than one ``Agent`` object each
(400*400 = 160k sites), but the model IS the agent population: each site is an
autonomous C/D strategy updated by a local stochastic imitation rule — a genuine
agent-based model, only stored in a structure-of-arrays layout for tractability.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from abm_auto._platform import AgentModel, DataCollector

COOPERATE = 1
DEFECT = 0

# von Neumann (z=4) neighbour offsets (drow, dcol): N, E, S, W.
VON_NEUMANN = ((-1, 0), (0, 1), (1, 0), (0, -1))


# -- Model --------------------------------------------------------------------

class FermiSpatialPDModel(AgentModel):
    """Szabó-Tőke (1998) spatial PD on a periodic square lattice under the
    random-sequential Fermi (pairwise-comparison) update.

    Construct with the lattice size ``L``, temptation ``b``, selection noise ``K``,
    the initial cooperator fraction, whether self-interaction is on, and a seed.
    ``run`` iterates ``n_sweeps`` MC sweeps (each L*L elementary Fermi steps) and
    records the per-sweep cooperator density.
    """

    def __init__(self, L: int = 400, *, b: float = 1.4, K: float = 0.1,
                 init_coop_fraction: float = 0.5, self_interaction: bool = True,
                 seed: int = 0, batch_frac: float = 0.10) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if L < 2:
            raise ValueError(f"need L >= 2 (got {L})")
        if b <= 0:
            raise ValueError(f"need b > 0 (got {b})")
        if K <= 0:
            raise ValueError(f"need K > 0 (Fermi temperature; got {K})")
        if not (0.0 <= init_coop_fraction <= 1.0):
            raise ValueError(f"need 0 <= init_coop_fraction <= 1 (got {init_coop_fraction})")
        if not (0.0 < batch_frac <= 1.0):
            raise ValueError(f"need 0 < batch_frac <= 1 (got {batch_frac})")
        self.L = int(L)
        self.n = self.L * self.L
        self.b = float(b)
        self.K = float(K)
        self.R = 1.0
        self.T = self.b
        self.P = 0.0
        self.S = 0.0
        self.init_coop_fraction = float(init_coop_fraction)
        self.self_interaction = bool(self_interaction)
        self.seed_value = int(seed)
        # A batch is this fraction of sites (a compromise: large enough to be fast,
        # small enough that the conflict-free filter keeps most of the batch).
        self.batch_size = max(1, int(self.n * float(batch_frac)))

        # A dedicated numpy Generator (seeded) drives the lattice + the update; the
        # platform's ``self.rng`` (Python random, same seed) is left for API parity.
        self.gen = np.random.default_rng(seed)

        # Random 50/50 (or init_coop_fraction) initial lattice of 1 (C) / 0 (D).
        self.grid = (self.gen.random((self.L, self.L)) < self.init_coop_fraction).astype(np.int8)

        # Precompute the flat neighbour-index table: neighbors[k, s] = flat index of
        # site s's k-th von Neumann neighbour (periodic). Shape (4, n).
        self.neighbors = self._build_neighbor_table()

        self.reporter = DataCollector({"coop_fraction": lambda m: m.cooperator_fraction()})

    # -- lattice ----------------------------------------------------------------
    def _build_neighbor_table(self) -> np.ndarray:
        L = self.L
        rows = np.repeat(np.arange(L), L)          # site s -> its row
        cols = np.tile(np.arange(L), L)            # site s -> its col
        table = np.empty((4, self.n), dtype=np.int64)
        for k, (dr, dc) in enumerate(VON_NEUMANN):
            nr = (rows + dr) % L
            nc = (cols + dc) % L
            table[k] = nr * L + nc
        return table

    # -- payoff -----------------------------------------------------------------
    def _payoffs(self, flat: np.ndarray) -> np.ndarray:
        """Accumulated payoff of every site against its von Neumann neighbours
        (plus itself if self-interaction is on), vectorised over the whole lattice.

        ``flat`` is the length-n int8 lattice (1=C, 0=D). For site s with strategy
        g_s and neighbour strategies {g_j}: a C (g_s=1) scores R=1 per C neighbour;
        a D (g_s=0) scores T=b per C neighbour. Both score 0 against a D neighbour.
        So payoff = (C-neighbour count) * (R if C else T). Self-interaction adds R
        for a C (self-game both-C) and P=0 for a D."""
        # number of cooperating neighbours of each site
        coop_neighbors = np.zeros(self.n, dtype=np.int64)
        for k in range(4):
            coop_neighbors += flat[self.neighbors[k]]
        is_coop = flat.astype(bool)
        # C sites: R per C-neighbour; D sites: T per C-neighbour.
        pay = np.where(is_coop,
                       coop_neighbors * self.R,
                       coop_neighbors * self.T).astype(np.float64)
        if self.self_interaction:
            # self-game: a C adds R (both-C), a D adds P=0.
            pay += np.where(is_coop, self.R, self.P)
        return pay

    # -- metrics ----------------------------------------------------------------
    def cooperator_fraction(self) -> float:
        return float(self.grid.mean())

    # -- one MC sweep -----------------------------------------------------------
    def step(self) -> None:
        """One Monte-Carlo sweep = n elementary random-sequential Fermi steps.

        Realised as conflict-free vectorised batches over a random permutation of
        focal sites. Before each batch the payoff field is recomputed from the LIVE
        lattice, so every focal compares against its neighbours' current strategies;
        within a batch the focal/neighbour pairs are filtered so no site is both a
        focal and a chosen neighbour and no neighbour is targeted twice, which keeps
        each elementary step's read/commit faithful to true random-sequential order.
        """
        flat = self.grid.reshape(-1)
        gen = self.gen
        n = self.n

        order = gen.permutation(n)                 # random-sequential visiting order
        pos = 0
        while pos < n:
            batch = order[pos:pos + self.batch_size]
            pos += self.batch_size

            # random neighbour direction (0..3) for each focal in the batch
            dirs = gen.integers(0, 4, size=batch.shape[0])
            targets = self.neighbors[dirs, batch]  # chosen neighbour flat index

            # conflict-free filter: keep, in order, focals whose focal-site and
            # whose chosen-neighbour have not already been claimed in this batch.
            keep = self._conflict_free_mask(batch, targets)
            f = batch[keep]
            y = targets[keep]
            if f.size == 0:
                continue

            # payoffs from the LIVE lattice (recomputed per batch)
            pay = self._payoffs(flat)
            Ex = pay[f]
            Ey = pay[y]
            gx = flat[f]
            gy = flat[y]

            # Fermi acceptance: focal x adopts y's strategy w.p. 1/(1+exp(-(Ey-Ex)/K)).
            # Only matters when strategies differ (else the copy is a no-op).
            diff = gx != gy
            w = 1.0 / (1.0 + np.exp(-(Ey - Ex) / self.K))
            u = gen.random(f.size)
            adopt = diff & (u < w)
            flat[f[adopt]] = gy[adopt]

        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    @staticmethod
    def _conflict_free_mask(focals: np.ndarray, targets: np.ndarray) -> np.ndarray:
        """Boolean mask selecting a conflict-free sub-batch: processed in the given
        order, an elementary (focal, target) pair is kept iff neither its focal site
        nor its target site has yet been claimed (as focal OR target) by an earlier
        kept pair in this batch. Guarantees every kept update reads a strategy that no
        other kept update in the same batch is simultaneously changing."""
        claimed: set = set()
        keep = np.zeros(focals.shape[0], dtype=bool)
        f_list = focals.tolist()
        t_list = targets.tolist()
        for i in range(len(f_list)):
            a = f_list[i]
            c = t_list[i]
            if a in claimed or c in claimed or a == c:
                continue
            claimed.add(a)
            claimed.add(c)
            keep[i] = True
        return keep

    # -- run --------------------------------------------------------------------
    def run(self, n_sweeps: int = 1000, *, measure_sweeps: int = 50) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate ``n_sweeps`` MC sweeps; return a run summary with the stationary
        cooperator density (mean over the last ``measure_sweeps`` sweeps) and the full
        per-sweep density series (t=0 baseline + every sweep)."""
        if measure_sweeps <= 0 or measure_sweeps > n_sweeps + 1:
            raise ValueError(
                f"measure_sweeps must be in [1, n_sweeps+1] (got {measure_sweeps}, "
                f"n_sweeps={n_sweeps})")
        self.reporter.collect(self)                # t=0 baseline
        for _ in range(n_sweeps):
            self.step()
        series = self.reporter.series("coop_fraction")
        return {
            "L": self.L,
            "n": self.n,
            "b": self.b,
            "K": self.K,
            "self_interaction": self.self_interaction,
            "init_coop_fraction": self.init_coop_fraction,
            "seed": self.seed_value,
            "n_sweeps": n_sweeps,
            "measure_sweeps": measure_sweeps,
            "stationary_c": tail_mean(series, window=measure_sweeps),
            "final_c": series[-1],
            "coop_series": series,
        }


# -- summary helpers ----------------------------------------------------------

def tail_mean(series: Sequence[float], *, window: int = 50) -> float:
    """Stationary estimate = mean of the trailing ``window`` of a series (or the
    whole series if shorter). Averaging the tail smooths the finite-size / finite-
    time fluctuations of the stochastic steady state and discards the transient."""
    if not series:
        return 0.0
    tail = list(series[-window:]) if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(L: int = 400, *, b: float = 1.4, K: float = 0.1,
               init_coop_fraction: float = 0.5, self_interaction: bool = True,
               seed: int = 0, n_sweeps: int = 1000, measure_sweeps: int = 50,
               batch_frac: float = 0.10) -> Dict[str, Any]:
    """One Fermi spatial-PD run at a given (b, K, self_interaction, seed)."""
    return FermiSpatialPDModel(
        L, b=b, K=K, init_coop_fraction=init_coop_fraction,
        self_interaction=self_interaction, seed=seed, batch_frac=batch_frac,
    ).run(n_sweeps, measure_sweeps=measure_sweeps)


def run_many_seeds(L: int = 400, *, b: float = 1.4, K: float = 0.1,
                   init_coop_fraction: float = 0.5, self_interaction: bool = True,
                   n_seeds: int = 1, seed_base: int = 0, n_sweeps: int = 1000,
                   measure_sweeps: int = 50, batch_frac: float = 0.10) -> Dict[str, Any]:
    """Run ``n_seeds`` Fermi spatial-PD runs (seed ``seed_base + i``) at fixed
    parameters and summarise the stationary cooperator density across seeds.

    Returns the per-seed stationary density values, their mean / std / min / max,
    and one representative density series (first seed) for inspection.
    """
    runs = [run_single(L, b=b, K=K, init_coop_fraction=init_coop_fraction,
                       self_interaction=self_interaction, seed=seed_base + i,
                       n_sweeps=n_sweeps, measure_sweeps=measure_sweeps,
                       batch_frac=batch_frac)
            for i in range(n_seeds)]
    per_seed_c = [rr["stationary_c"] for rr in runs]
    per_seed_final = [rr["final_c"] for rr in runs]
    mean_c = sum(per_seed_c) / n_seeds
    var_c = sum((s - mean_c) ** 2 for s in per_seed_c) / n_seeds
    return {
        "L": L, "b": b, "K": K,
        "self_interaction": self_interaction,
        "init_coop_fraction": init_coop_fraction,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_sweeps": n_sweeps, "measure_sweeps": measure_sweeps,
        "per_seed_stationary_c": per_seed_c,
        "per_seed_final_c": per_seed_final,
        "mean_stationary_c": mean_c,
        "var_stationary_c": var_c,
        "std_stationary_c": var_c ** 0.5,
        "min_stationary_c": min(per_seed_c),
        "max_stationary_c": max(per_seed_c),
        "example_coop_series": runs[0]["coop_series"],
    }


def survival_threshold(L: int = 200, *, K: float = 0.1,
                       self_interaction: bool = False, seed: int = 0,
                       b_lo: float = 1.0, b_hi: float = 2.2, tol: float = 0.02,
                       n_sweeps: int = 400, measure_sweeps: int = 40,
                       c_extinct: float = 0.02, batch_frac: float = 0.10) -> float:
    """Bisection estimate of b_cr(K): the largest temptation ``b`` at which
    cooperators still survive (stationary density > ``c_extinct``). Used for P3's
    noise non-monotonicity (b_cr peaked at intermediate K). Faithful bisection on the
    same locked model — the K grid + spec are fixed by the caller, not tuned here.

    Returns the midpoint of the final bracket. A smaller L + shorter run are used
    (this is a threshold *locator*, swept over several K, not a graded density point).
    """
    lo, hi = float(b_lo), float(b_hi)

    def survives(b: float) -> bool:
        res = run_single(L, b=b, K=K, self_interaction=self_interaction, seed=seed,
                         n_sweeps=n_sweeps, measure_sweeps=measure_sweeps,
                         batch_frac=batch_frac)
        return res["stationary_c"] > c_extinct

    # Ensure the bracket actually brackets the threshold; if not, clamp.
    if not survives(lo):
        return lo                      # cooperators die even at b_lo -> threshold <= b_lo
    if survives(hi):
        return hi                      # still alive at b_hi -> threshold >= b_hi
    while (hi - lo) > tol:
        mid = 0.5 * (lo + hi)
        if survives(mid):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
