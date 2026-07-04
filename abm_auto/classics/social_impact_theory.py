"""Dynamic Social Impact Theory (Nowak, Szamrej & Latané 1990) — a faithful
agent-based reproduction.

Source: Nowak, A., Szamrej, J. & Latané, B. (1990), "From private attitudes to
public opinion: A dynamic theory of social impact", Psychological Review
97(3):362-376. doi:10.1037/0033-295X.97.3.362. Impact functional as in
Castellano, Fortunato & Loreto (2009), Rev. Mod. Phys. 81:591, Eq. 16.

Each agent sits at a FIXED site of an L x L square lattice (one agent per site,
N = L*L), and never moves — segregation/clustering happens by OPINION FLIPS, not
by relocation (contrast Schelling, where agents move and opinions are fixed). An
agent carries:

  * a binary opinion  sigma_i = +/- 1, and
  * two i.i.d. personal traits drawn once ~U[0,1] and HELD FIXED for the whole run:
      - persuasiveness  p_i  (its power to CONVERT agents of the opposite opinion),
      - supportiveness  s_i  (its power to REINFORCE agents of the same opinion).

The total social impact felt by agent i is the persuasive impact from the
OPPOSITE camp MINUS the supportive impact from its OWN camp (Latané's social-impact
law, distance-discounted):

    I_i = sum_j  p_j / g(d_ij) * (1 - sigma_i*sigma_j)          # persuasion (opposite j)
        - sum_j  s_j / g(d_ij) * (1 + sigma_i*sigma_j),         # support    (same j)

with Euclidean distance d_ij on the lattice, decay g(d) = 1 + d^alpha, alpha = 2
(inverse-square; faithful to the original), and the SELF term excluded (the
(1 - sigma_i*sigma_j) factor is 0 for j=i anyway, but support would otherwise
double-count self, so j=i is dropped from both sums via a zeroed diagonal).

DETERMINISTIC dynamics (zero social temperature, no external field h=0): agent i
flips its opinion iff the opposing (persuasive) impact exceeds the supporting
(supportive) impact, i.e. iff I_i > 0. Sweeps (synchronous: all impacts computed
from one snapshot, then all flips applied) run to a FIXED POINT — a full sweep in
which no agent flips (FREEZE). The start is f0 ~ 0.5 (each opinion i.i.d. +/-1).

Key published result reproduced here: from a near-balanced start the system does
NOT reach full consensus. The minority SURVIVES as stable, spatially COHERENT
clusters; opinions self-organise into contiguous regions. This is a ZERO-NOISE,
FINITE-SIZE phenomenon: adding social temperature or per-agent fields erodes the
frozen domains.

Efficiency: the impact is all-pairs O(N^2) per sweep. We PRECOMPUTE the N x N
weight matrix  W_ij = 1 / (1 + d_ij^2)  ONCE (numpy; diagonal zeroed to drop the
self term) and compute every sweep's impacts as exact vectorised matrix-vector
products — fast AND exact (no cutoff radius, no truncation). For N=1681 the matrix
is ~22 MB and a sweep is a couple of dense mat-vecs.

Built on the neutral platform (``abm_auto._platform``): each site is a
``SiteAgent`` carrying its opinion and fixed (p, s); ``SocialImpactModel`` holds
the lattice, the precomputed weight matrix, drives the synchronous impact-flip
sweep to a freeze, and records (via a ``DataCollector``) the per-sweep minority
fraction and same-opinion bond fraction. Deterministic given the seed.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class SiteAgent(Agent):
    """One fixed lattice site: a (row, col) position, an opinion sigma = +/-1, and
    two fixed traits persuasiveness ``p`` and supportiveness ``s`` (drawn once).

    The sweep is a model-level synchronous update (all impacts from one snapshot,
    then all flips), so the per-agent ``step`` is intentionally a no-op."""

    def __init__(self, agent_id: int, model: "SocialImpactModel", *,
                 row: int, col: int, sigma: int, p: float, s: float) -> None:
        super().__init__(agent_id, model)
        self.row = row
        self.col = col
        self.sigma = sigma
        self.p = p
        self.s = s

    def step(self) -> None:  # pragma: no cover - the sweep lives on the model
        """The impact-flip sweep is a model-level synchronous update, not an
        autonomous single-agent step, so this is a no-op."""
        return None


# -- weight matrix ------------------------------------------------------------

def build_weight_matrix(L: int, alpha: float = 2.0) -> np.ndarray:
    """The N x N distance-decay weight matrix  W_ij = 1 / (1 + d_ij^alpha)  for an
    L x L lattice (N = L*L), with the DIAGONAL ZEROED so the self term is excluded
    from both the persuasive and supportive sums.

    d_ij is the Euclidean distance between sites i and j (sites enumerated
    row-major: index = row*L + col). Symmetric, zero diagonal. ~22 MB float64 for
    L=41."""
    coords = np.array([(r, c) for r in range(L) for c in range(L)], dtype=np.float64)
    # pairwise squared Euclidean distances via broadcasting
    diff = coords[:, None, :] - coords[None, :, :]          # (N, N, 2)
    d2 = np.einsum("ijk,ijk->ij", diff, diff)               # (N, N) squared distances
    if alpha == 2.0:
        g = 1.0 + d2                                        # g(d) = 1 + d^2 directly
    else:
        g = 1.0 + np.power(np.sqrt(d2), alpha)
    w = 1.0 / g
    np.fill_diagonal(w, 0.0)                                # exclude the self term
    return w


# -- Model --------------------------------------------------------------------

class SocialImpactModel(AgentModel):
    """Drives the Nowak-Szamrej-Latane (1990) deterministic social-impact dynamics.

    Construct with lattice side ``L`` (N = L*L), the decay exponent ``alpha``, and a
    seed. The initial opinions are i.i.d. +/-1 with probability ``f0`` of being -1
    (default 0.5), and each agent's (p, s) traits are drawn once ~U[0,1] and held
    fixed. ``run`` advances the synchronous impact-flip sweep to a FREEZE (a sweep
    with no flips, or a max-sweep cap) and records the per-sweep minority fraction
    and same-opinion nearest-neighbour bond fraction.
    """

    def __init__(self, *, L: int = 41, alpha: float = 2.0, f0: float = 0.5,
                 seed: int = 0, max_sweeps: int = 200, update: str = "sequential",
                 weight_matrix: Optional[np.ndarray] = None) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if L <= 1:
            raise ValueError(f"need L > 1 (got {L})")
        if not (0.0 < f0 < 1.0):
            raise ValueError(f"need 0 < f0 < 1 (got {f0})")
        if max_sweeps <= 0:
            raise ValueError(f"need max_sweeps > 0 (got {max_sweeps})")
        if update not in ("sequential", "synchronous"):
            raise ValueError(
                f"update must be 'sequential' or 'synchronous' (got {update!r})")
        self.seed_value = seed
        self.L = int(L)
        self.N = self.L * self.L
        self.alpha = float(alpha)
        self.f0 = float(f0)
        self.max_sweeps = int(max_sweeps)
        self.update = update

        # Precompute (or accept a shared) weight matrix W_ij = 1/(1 + d_ij^2),
        # diagonal zeroed. Shared across seeds of the same (L, alpha) for speed —
        # the geometry is seed-independent.
        if weight_matrix is not None:
            if weight_matrix.shape != (self.N, self.N):
                raise ValueError(
                    f"weight_matrix shape {weight_matrix.shape} != ({self.N},{self.N})")
            self.W = weight_matrix
        else:
            self.W = build_weight_matrix(self.L, self.alpha)

        # numpy state arrays (the simulation runs on these; the SiteAgent roster is
        # the platform-faithful mirror kept in sync at construction + after run).
        rng = np.random.default_rng(seed)
        # opinions: -1 with prob f0, else +1 (i.i.d.)  -> near-balanced for f0=0.5
        self.sigma = np.where(rng.random(self.N) < self.f0, -1, 1).astype(np.int64)
        # fixed traits ~ U[0,1], drawn once
        self.p = rng.random(self.N)
        self.s = rng.random(self.N)
        self.sigma0 = self.sigma.copy()                    # the locked initial state

        # Per-agent fields: the constant Wp_i = sum_j W_ij p_j and Ws_i = sum_j W_ij s_j
        # (sigma-independent), plus the sigma-dependent Fp_i = sum_j W_ij p_j sigma_j and
        # Fs_i = sum_j W_ij s_j sigma_j maintained incrementally so a single flip is an
        # O(N) rank-1 update rather than an O(N^2) recompute (used by the sequential
        # sweep). Initialised here from the drawn p, s, sigma.
        self._Wp = self._Ws = self._Fp = self._Fs = None  # type: ignore[assignment]
        self._resync_fields()

        # platform roster: one SiteAgent per site (row-major), mirroring the arrays.
        self.agent_list: List[SiteAgent] = []
        for idx in range(self.N):
            r, c = divmod(idx, self.L)
            agent = SiteAgent(idx, self, row=r, col=c,
                              sigma=int(self.sigma[idx]),
                              p=float(self.p[idx]), s=float(self.s[idx]))
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.swept = 0
        self.frozen = False
        self.reporter = DataCollector({
            "minority_fraction": lambda m: m.minority_fraction(),
            "same_bond_fraction": lambda m: m.same_opinion_bond_fraction(),
        })

    # -- impact + sweep --
    def impacts(self) -> np.ndarray:
        """Per-agent total social impact I_i for the CURRENT opinion vector, as a
        vectorised exact computation (no truncation).

        Persuasive impact (from OPPOSITE-opinion agents) MINUS supportive impact
        (from SAME-opinion agents):

            I_i = sum_j W_ij p_j (1 - s_i s_j) - sum_j W_ij s_j (1 + s_i s_j).

        Expand with  sum_j W_ij p_j (1 - s_i s_j) = (W p)_i - s_i (W (p*sigma))_i
        and likewise for the support term, giving four dense mat-vecs. The j=i term
        vanishes because the W diagonal is zero, so self is excluded from both sums.
        This recomputes ALL fields from scratch off the current p, s, sigma (so it is
        the authoritative reference even if the traits were just edited), used by the
        synchronous sweep and the metrics."""
        sig = self.sigma.astype(np.float64)
        Wp = self.W @ self.p                  # sum_j W_ij p_j
        Ws = self.W @ self.s                  # sum_j W_ij s_j
        Fp = self.W @ (self.p * sig)          # sum_j W_ij p_j sigma_j
        Fs = self.W @ (self.s * sig)          # sum_j W_ij s_j sigma_j
        persuasive = Wp - sig * Fp            # sum_j W_ij p_j (1 - sigma_i sigma_j)
        supportive = Ws + sig * Fs            # sum_j W_ij s_j (1 + sigma_i sigma_j)
        return persuasive - supportive

    def _resync_fields(self) -> None:
        """Recompute ALL incremental fields (Wp, Ws constant; Fp, Fs sigma-dependent)
        from the current p, s, sigma. Keeps the O(N) incremental sequential path
        bit-consistent with a from-scratch mat-vec, and refreshes the constant fields
        after any trait edit (tests construct hand-built lattices by overwriting p/s)."""
        sig = self.sigma.astype(np.float64)
        self._Wp = self.W @ self.p
        self._Ws = self.W @ self.s
        self._Fp = self.W @ (self.p * sig)
        self._Fs = self.W @ (self.s * sig)

    def _flip_site(self, i: int) -> None:
        """Flip site ``i`` and apply the O(N) rank-1 update to the incremental fields
        Fp, Fs (so subsequent in-sweep impacts see the new opinion immediately)."""
        old = int(self.sigma[i])
        new = -old
        self.sigma[i] = new
        delta = float(new - old)              # +/-2
        self._Fp += self.W[:, i] * (self.p[i] * delta)
        self._Fs += self.W[:, i] * (self.s[i] * delta)

    def sweep(self) -> int:
        """One deterministic sweep to the configured update rule. Returns the number
        of flips this sweep (0 == frozen at a fixed point).

        ``synchronous``: every agent's impact is computed from one start-of-sweep
        snapshot, then all qualifying agents flip together. This can leave a 2-cycle
        (the system oscillates and never freezes), the classic parallel-update
        artifact.

        ``sequential`` (default, faithful): agents are visited in a FIXED row-major
        order; each sees the opinions already updated earlier this sweep. Deterministic
        asynchronous dynamics provably reach a TRUE fixed point (no 2-cycle), which is
        the regime the paper's frozen domains live in. Implemented with the O(N)
        incremental field update so a sweep is O(N^2), matching the synchronous cost."""
        if self.update == "synchronous":
            I = self.impacts()
            flip = I > 0.0
            n_flips = int(np.count_nonzero(flip))
            if n_flips:
                self.sigma = np.where(flip, -self.sigma, self.sigma)
                self._resync_fields()
            self.swept += 1
            return n_flips
        # sequential
        n_flips = 0
        for i in range(self.N):
            sig_i = self.sigma[i]
            I_i = (self._Wp[i] - sig_i * self._Fp[i]) - (self._Ws[i] + sig_i * self._Fs[i])
            if I_i > 0.0:
                self._flip_site(i)
                n_flips += 1
        self.swept += 1
        return n_flips

    def step(self) -> None:
        """One sweep + bookkeeping (platform tick). Mirrors the flips onto the
        SiteAgent roster and records the per-sweep metrics."""
        n_flips = self.sweep()
        if n_flips == 0:
            self.frozen = True
        # mirror onto the platform roster (keeps SiteAgent.sigma faithful)
        for agent in self.agent_list:
            agent.sigma = int(self.sigma[agent.id])
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    # -- metrics --
    def minority_fraction(self) -> float:
        """Fraction of sites holding the MINORITY opinion (in [0, 0.5]). 0 means full
        consensus; ~0.5 means a balanced (possibly frozen-noise) split."""
        n_minus = int(np.count_nonzero(self.sigma == -1))
        frac_minus = n_minus / self.N
        return min(frac_minus, 1.0 - frac_minus)

    def majority_sign(self) -> int:
        """The sign (+1 / -1) of the current majority opinion (ties -> +1)."""
        n_plus = int(np.count_nonzero(self.sigma == 1))
        return 1 if n_plus >= self.N - n_plus else -1

    def grid(self) -> np.ndarray:
        """The current opinion field as an L x L int array (row-major)."""
        return self.sigma.reshape(self.L, self.L)

    def same_opinion_bond_fraction(self) -> float:
        """Fraction of nearest-neighbour (von-Neumann, 4-adjacency, no wrap) bonds whose
        two endpoints share an opinion. ~0.5 for a random configuration; rises toward 1
        as opinions self-organise into contiguous same-opinion domains."""
        g = self.grid()
        same = 0
        total = 0
        # horizontal bonds
        same += int(np.count_nonzero(g[:, :-1] == g[:, 1:]))
        total += g.shape[0] * (g.shape[1] - 1)
        # vertical bonds
        same += int(np.count_nonzero(g[:-1, :] == g[1:, :]))
        total += (g.shape[0] - 1) * g.shape[1]
        return same / total if total else 0.0

    def cluster_sizes(self, sign: int) -> List[int]:
        """Sizes of the connected components (von-Neumann 4-adjacency, no wrap) of
        sites holding opinion ``sign``, largest first. A flood-fill over the L x L grid."""
        g = self.grid()
        mask = (g == sign)
        L = self.L
        seen = np.zeros((L, L), dtype=bool)
        sizes: List[int] = []
        for r0 in range(L):
            for c0 in range(L):
                if not mask[r0, c0] or seen[r0, c0]:
                    continue
                # iterative flood fill
                stack = [(r0, c0)]
                seen[r0, c0] = True
                size = 0
                while stack:
                    r, c = stack.pop()
                    size += 1
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < L and 0 <= nc < L and mask[nr, nc] and not seen[nr, nc]:
                            seen[nr, nc] = True
                            stack.append((nr, nc))
                sizes.append(size)
        sizes.sort(reverse=True)
        return sizes

    def largest_cluster(self, sign: int) -> int:
        """Size of the largest connected same-opinion cluster of opinion ``sign``
        (0 if none)."""
        sizes = self.cluster_sizes(sign)
        return sizes[0] if sizes else 0

    # -- run --
    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        """Run synchronous impact-flip sweeps until a FREEZE (a sweep with no flips)
        or the ``max_sweeps`` cap, then return the freeze-state summary.

        Records the per-sweep minority fraction + same-opinion bond fraction (the
        t=0 baseline first, then one record per sweep)."""
        self.reporter.collect(self)                        # t=0 baseline (random start)
        initial_minority = self.reporter.records[0]["minority_fraction"]
        initial_bond = self.reporter.records[0]["same_bond_fraction"]
        for _ in range(self.max_sweeps):
            if self.frozen:
                break
            self.step()
        maj = self.majority_sign()
        minority_sign = -maj
        maj_clusters = self.cluster_sizes(maj)
        min_clusters = self.cluster_sizes(minority_sign)
        return {
            "L": self.L,
            "N": self.N,
            "alpha": self.alpha,
            "f0": self.f0,
            "update": self.update,
            "seed": self.seed_value,
            "sweeps": self.swept,
            "frozen": self.frozen,
            "initial_minority_fraction": initial_minority,
            "initial_bond_fraction": initial_bond,
            "final_minority_fraction": self.minority_fraction(),
            "final_bond_fraction": self.same_opinion_bond_fraction(),
            "majority_sign": maj,
            "largest_majority_cluster": maj_clusters[0] if maj_clusters else 0,
            "largest_minority_cluster": min_clusters[0] if min_clusters else 0,
            "n_minority_clusters": len(min_clusters),
            "minority_cluster_sizes": min_clusters,
            "minority_fraction_series": self.reporter.series("minority_fraction"),
            "bond_fraction_series": self.reporter.series("same_bond_fraction"),
        }


# -- multi-seed helpers -------------------------------------------------------

def run_single(*, L: int = 41, alpha: float = 2.0, f0: float = 0.5, seed: int = 0,
               max_sweeps: int = 200, update: str = "sequential",
               weight_matrix: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """One full social-impact run to a freeze for a given seed."""
    model = SocialImpactModel(L=L, alpha=alpha, f0=f0, seed=seed,
                              max_sweeps=max_sweeps, update=update,
                              weight_matrix=weight_matrix)
    return model.run()


def run_many_seeds(seeds: Sequence[int], *, L: int = 41, alpha: float = 2.0,
                   f0: float = 0.5, max_sweeps: int = 200, update: str = "sequential",
                   min_cluster_threshold: int = 5) -> Dict[str, Any]:
    """Run one social-impact simulation per seed (sharing one precomputed weight
    matrix, since the geometry is seed-independent) and summarise across seeds.

    Returns per-seed rows plus the cross-seed headline statistics the locked clauses
    are graded against: mean final minority fraction (P1), mean final same-opinion
    bond fraction (P2), and the per-seed largest-majority-cluster fraction +
    survival of a minority cluster of size >= ``min_cluster_threshold`` (P3).
    """
    seeds = list(seeds)
    if not seeds:
        raise ValueError("need at least one seed")
    # one shared weight matrix for all seeds (geometry is seed-independent).
    W = build_weight_matrix(L, alpha)
    rows: List[Dict[str, Any]] = []
    for s in seeds:
        rows.append(run_single(L=L, alpha=alpha, f0=f0, seed=s,
                               max_sweeps=max_sweeps, update=update, weight_matrix=W))
    n = len(rows)
    N = L * L

    per_seed_minority = [r["final_minority_fraction"] for r in rows]
    per_seed_bond = [r["final_bond_fraction"] for r in rows]
    per_seed_maj_cluster_frac = [r["largest_majority_cluster"] / N for r in rows]
    # P3 survival: a minority cluster of size >= threshold exists this seed.
    per_seed_min_survives = [
        any(sz >= min_cluster_threshold for sz in r["minority_cluster_sizes"])
        for r in rows
    ]

    def _mean(xs: List[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    mean_minority = _mean(per_seed_minority)
    mean_bond = _mean(per_seed_bond)
    survive_count = sum(1 for b in per_seed_min_survives if b)
    survive_fraction = survive_count / n

    return {
        "seeds": seeds,
        "L": L,
        "N": N,
        "alpha": alpha,
        "f0": f0,
        "update": update,
        "max_sweeps": max_sweeps,
        "min_cluster_threshold": min_cluster_threshold,
        "n_seeds": n,
        "rows": rows,
        "per_seed_minority_fraction": per_seed_minority,
        "per_seed_bond_fraction": per_seed_bond,
        "per_seed_majority_cluster_fraction": per_seed_maj_cluster_frac,
        "per_seed_minority_survives": per_seed_min_survives,
        "mean_minority_fraction": mean_minority,
        "min_minority_fraction": min(per_seed_minority),
        "max_minority_fraction": max(per_seed_minority),
        "mean_bond_fraction": mean_bond,
        "min_bond_fraction": min(per_seed_bond),
        "max_bond_fraction": max(per_seed_bond),
        "mean_majority_cluster_fraction": _mean(per_seed_maj_cluster_frac),
        "min_majority_cluster_fraction": min(per_seed_maj_cluster_frac),
        "minority_survival_count": survive_count,
        "minority_survival_fraction": survive_fraction,
        "all_frozen": all(r["frozen"] for r in rows),
    }
