"""Martins CODA — Continuous Opinions and Discrete Actions — a faithful ABM.

Source: Martins, A.C.R. (2008). "Continuous opinions and discrete actions in
opinion dynamics problems." Int. J. Mod. Phys. C 19(4):617-624.
doi:10.1142/S0129183108012339. (arXiv:0711.1199.)

This is a GENUINE AGENT-BASED model, not a cellular automaton: each agent on an
L x L periodic lattice carries a HIDDEN, continuous belief — the probability `p`
that option A is the better choice — and exposes ONLY a DISCRETE action,
``sigma = sign(p - 0.5)`` (act for A iff p >= 0.5). No agent ever sees another's
continuous `p`; an agent observes only the discrete actions of its neighbours and
Bayesian-updates its own hidden belief from them. The unit of action is therefore
ONE ASYNCHRONOUS SINGLE-OBSERVATION UPDATE: each step a randomly chosen agent
observes ONE randomly chosen von-Neumann neighbour's action and revises its belief.

CODA's key identity (Martins 2008, Eq. 3): in the log-odds ``l = ln(p/(1-p))`` the
Bayesian update from a single binary observation is EXACTLY ADDITIVE,

    l  ->  l + nu   if the observed neighbour acts for A (sigma_j = +1)
    l  ->  l - nu   if the observed neighbour acts for B (sigma_j = -1)

with the FIXED step ``nu = ln(alpha / (1 - alpha))`` set by the (fixed) likelihood
``alpha`` that a neighbour acting for A really is in the better state. With
alpha = 0.7, ``nu = ln(0.7/0.3) = 0.8473``. Because the step is additive and
unbounded, repeated agreeing observations drive ``|l|`` to arbitrarily large values:
beliefs DIVERGE TO CERTAINTY (extremization). This INVERTS bounded-confidence
averaging (Deffuant / Hegselmann-Krause), where continuous opinions are *averaged*
toward moderation; CODA's discrete-action Bayesian update is the distinctness
signature — it cannot be produced by an averaging model.

The exposed action ``sigma`` depends only on the SIGN of `l` (sign(p - 0.5) =
sign(l)), so neighbouring agents that agree reinforce one another and contiguous
same-action DOMAINS form, while the hidden beliefs inside a domain keep
extremizing without bound. Global consensus is NOT required: distinct domains can
coexist.

Platform: built on ``abm_auto._platform`` (``Agent`` + ``AgentModel``). Each lattice
site is a ``CODAAgent`` carrying its hidden log-odds ``l``; ``CODAModel`` holds the
roster and drives the asynchronous observe-and-update dynamics. For speed over the
millions of single-observation updates the hot loop operates on a FLAT numpy array
of log-odds with PRECOMPUTED periodic von-Neumann neighbour indices (the per-agent
``CODAAgent.l`` is a live view onto that array, so the agent objects and the array
never disagree); the result is identical to stepping the agent roster one
observation at a time. Deterministic given a seed (numpy PCG64).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np

from abm_auto._platform import Agent, AgentModel


# -- the fixed Bayesian step --------------------------------------------------

def coda_nu(alpha: float = 0.7) -> float:
    """The CODA additive log-odds step ``nu = ln(alpha/(1-alpha))`` for likelihood
    ``alpha`` (Martins 2008, Eq. 3). alpha must lie strictly in (0.5, 1) so a single
    observation is informative (nu > 0)."""
    if not (0.5 < alpha < 1.0):
        raise ValueError(f"alpha must be in (0.5, 1) for nu>0 (got {alpha})")
    return math.log(alpha / (1.0 - alpha))


# -- periodic von-Neumann neighbour table -------------------------------------

def von_neumann_neighbours(L: int) -> np.ndarray:
    """Return the (N, 4) int array of the 4 von-Neumann neighbour flat-indices of
    every site on an L x L PERIODIC lattice (N = L*L).

    Site (r, c) has flat index ``r*L + c``; its neighbours are (r-1,c), (r+1,c),
    (r,c-1), (r,c+1) with wrap-around (mod L). Precomputed once so the hot update
    loop is a single array lookup. Column order is [up, down, left, right]."""
    if L <= 0:
        raise ValueError(f"L must be positive (got {L})")
    rows = np.repeat(np.arange(L), L)
    cols = np.tile(np.arange(L), L)
    up = ((rows - 1) % L) * L + cols
    down = ((rows + 1) % L) * L + cols
    left = rows * L + ((cols - 1) % L)
    right = rows * L + ((cols + 1) % L)
    return np.stack([up, down, left, right], axis=1).astype(np.int64)


# -- Agent --------------------------------------------------------------------

class CODAAgent(Agent):
    """One lattice agent: a hidden continuous belief exposed only as a discrete action.

    The belief is the log-odds ``l`` (``l = ln(p/(1-p))`` for the hidden probability
    ``p`` that A is best). ``l`` is a LIVE property backed by the model's flat array,
    so the agent object and the vectorised state never diverge. The agent exposes
    ONLY ``action`` (= sign(l), the discrete +1/-1 choice an observer can see); its
    continuous ``l`` / ``p`` are never visible to other agents.

    The CODA dynamics is an asynchronous single-observation update driven on the model
    (a randomly chosen agent observes ONE neighbour's action and revises its belief), so
    the per-agent ``step`` is intentionally a no-op — the unit of action is one observe-
    and-update on the model, not an autonomous full-agent step.
    """

    def __init__(self, agent_id: int, model: "CODAModel") -> None:
        super().__init__(agent_id, model)

    @property
    def l(self) -> float:  # noqa: E743 - 'l' is the paper's symbol for log-odds
        """Hidden log-odds belief (live view onto the model's flat state array)."""
        return float(self.model.l[self.id])

    @l.setter
    def l(self, value: float) -> None:
        self.model.l[self.id] = value

    @property
    def p(self) -> float:
        """Hidden probability that A is best, ``p = 1/(1+e^{-l})``. Never observable."""
        return 1.0 / (1.0 + math.exp(-self.model.l[self.id]))

    @property
    def action(self) -> int:
        """The DISCRETE exposed action sigma = sign(p-0.5) = sign(l): +1 (act for A)
        iff l >= 0, else -1. This is the ONLY thing other agents can observe."""
        return 1 if self.model.l[self.id] >= 0.0 else -1

    def step(self) -> None:  # pragma: no cover - dynamics live on the model
        """No-op: the CODA unit of action is one asynchronous observe-and-update on
        the model, not an autonomous per-agent step."""
        return None


# -- Model --------------------------------------------------------------------

class CODAModel(AgentModel):
    """Drives the Martins (2008) CODA dynamics on an L x L periodic lattice.

    Construct with the lattice side ``L`` (N = L*L agents), the likelihood ``alpha``
    (fixing the additive step ``nu``), the initial-belief band ``(p_lo, p_hi)`` for the
    seed draw ``p_i ~ U(p_lo, p_hi)``, and a seed. ``run(n_updates)`` advances that many
    asynchronous single-observation updates (each: a random agent observes one random
    von-Neumann neighbour's action, ``l_i += nu`` if that action is +1 else ``-= nu``).

    Hidden continuous state is the flat array ``self.l`` (log-odds); the discrete action
    field is ``sign(self.l)``. Deterministic given the seed (numpy PCG64).
    """

    def __init__(self, L: int = 50, *, alpha: float = 0.7,
                 p_lo: float = 0.4, p_hi: float = 0.6, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if L <= 0:
            raise ValueError(f"L must be positive (got {L})")
        if not (0.0 < p_lo <= p_hi < 1.0):
            raise ValueError(f"need 0<p_lo<=p_hi<1 (got p_lo={p_lo}, p_hi={p_hi})")
        self.seed_value = seed
        self.L = int(L)
        self.N = self.L * self.L
        self.alpha = float(alpha)
        self.nu = coda_nu(self.alpha)
        self.p_lo = float(p_lo)
        self.p_hi = float(p_hi)

        # Dedicated numpy generator (seeded) drives BOTH the initial belief draw and the
        # asynchronous update choices, so the whole run is reproducible from `seed`.
        self._gen = np.random.Generator(np.random.PCG64(seed))

        # Initial hidden beliefs: p_i ~ U(p_lo, p_hi) -> l_i = ln(p/(1-p)). With the
        # default band (0.4, 0.6) every agent starts with |l_i| < nu (NO extremists).
        p0 = self._gen.uniform(self.p_lo, self.p_hi, size=self.N)
        self.l = np.log(p0 / (1.0 - p0)).astype(np.float64)

        # Precomputed periodic von-Neumann neighbour table (N, 4).
        self.neighbours = von_neumann_neighbours(self.L)

        # Genuine agent roster on the platform (one CODAAgent per site, backed by self.l).
        self.agent_list: List[CODAAgent] = []
        for i in range(self.N):
            agent = CODAAgent(i, self)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self._updates_done = 0

    # -- the asynchronous CODA update --
    def update_batch(self, n_updates: int) -> None:
        """Advance ``n_updates`` asynchronous single-observation CODA updates.

        Each update: draw a target agent ``i`` uniformly, draw one of its 4 von-Neumann
        neighbours ``j`` uniformly, observe j's DISCRETE action ``sign(l_j)`` and apply
        the additive Bayesian step ``l_i += nu`` if that action is +1, else ``l_i -= nu``.

        The choices are drawn in one vectorised batch for speed, but the updates are
        applied SEQUENTIALLY (a Python loop) because each observation must read the
        possibly-just-changed neighbour state — i.e. this is a true asynchronous random-
        sequential update, identical to stepping one agent at a time. (Vectorising the
        *apply* would silently turn it synchronous, which is a different model.)

        Each update consumes EXACTLY ONE generator draw from ``[0, 4N)``, decomposed as
        ``target = v // 4`` and ``which = v % 4`` (one of the 4 von-Neumann neighbours).
        Drawing a single integer per update makes ``update_batch`` a pure prefix of the
        update stream: chunking the run (e.g. snapshotting at 2M on the way to 4M) yields
        the IDENTICAL trajectory as one un-chunked batch — essential so the P1 'double the
        run' growth check continues the same stream rather than a different one."""
        if n_updates < 0:
            raise ValueError("n_updates must be non-negative")
        if n_updates == 0:
            return
        nb = self.neighbours
        l = self.l
        nu = self.nu
        fourN = 4 * self.N
        draws = self._gen.integers(0, fourN, size=n_updates)
        for k in range(n_updates):
            v = draws[k]
            i = v >> 2            # v // 4  -> target agent
            j = nb[i, v & 3]      # v % 4   -> one of the 4 von-Neumann neighbours
            # observe j's discrete action (sign of its hidden log-odds), update i
            if l[j] >= 0.0:
                l[i] += nu
            else:
                l[i] -= nu
        self._updates_done += n_updates

    def step(self) -> None:
        """One asynchronous CODA update (a single observe-and-update). Provided so the
        platform's per-step driver maps to the model's unit of action; the ensemble API
        uses :meth:`update_batch` for speed over millions of updates."""
        self.update_batch(1)
        self.t += 1

    # -- metrics --
    def actions(self) -> np.ndarray:
        """The discrete action field: +1 where l >= 0 else -1 (the only observable
        state). Shape (N,)."""
        return np.where(self.l >= 0.0, 1, -1).astype(np.int64)

    def action_grid(self) -> np.ndarray:
        """The action field reshaped to the (L, L) lattice (+1 / -1)."""
        return self.actions().reshape(self.L, self.L)

    def abs_l_over_nu(self) -> np.ndarray:
        """Per-agent extremity ``|l|/nu`` (number of net agreeing observations of
        certainty). Shape (N,)."""
        return np.abs(self.l) / self.nu

    def max_abs_l_over_nu(self) -> float:
        """The most extreme belief in the population, ``max_i |l_i|/nu`` — the locked P1
        quantity (grows without bound under continued agreeing observation)."""
        return float(np.max(np.abs(self.l)) / self.nu)

    def median_abs_l_over_nu(self) -> float:
        """Median per-agent extremity ``median_i |l_i|/nu``."""
        return float(np.median(np.abs(self.l)) / self.nu)

    def fraction_extreme(self, threshold: float = 50.0) -> float:
        """Fraction of agents with ``|l|/nu >= threshold`` (deep in a certainty mode)."""
        return float(np.mean(self.abs_l_over_nu() >= threshold))

    def fraction_moderate(self, threshold: float = 1.0) -> float:
        """Fraction of agents with ``|l|/nu < threshold`` (still near indifference)."""
        return float(np.mean(self.abs_l_over_nu() < threshold))

    def like_neighbour_fraction(self) -> float:
        """Fraction of von-Neumann lattice bonds whose two endpoints share the SAME
        discrete action. 1.0 = perfectly ordered (one giant domain or aligned domains);
        ~0.5 = random/disordered. Each undirected bond counted once (right + down bonds
        of every site on the periodic lattice)."""
        a = self.action_grid()
        same_right = np.sum(a == np.roll(a, -1, axis=1))
        same_down = np.sum(a == np.roll(a, -1, axis=0))
        total_bonds = 2 * self.N  # right-bond + down-bond per site (periodic)
        return float((same_right + same_down) / total_bonds)

    def domain_count(self, min_size_frac: float = 0.0) -> int:
        """Number of connected same-action DOMAINS (4-connectivity, periodic) whose size
        is at least ``min_size_frac * N``. A domain is a maximal set of same-action sites
        connected through von-Neumann adjacency with wrap-around. ``min_size_frac=0``
        counts ALL components (including tiny ones); a positive threshold counts only
        MACROSCOPIC domains."""
        labels, sizes = self._label_domains()
        min_size = min_size_frac * self.N
        return int(np.sum(sizes >= min_size)) if sizes.size else 0

    def macroscopic_domain_sizes(self, min_size_frac: float = 0.05) -> List[int]:
        """Sorted (descending) sizes of the macroscopic (>= min_size_frac*N) same-action
        domains."""
        _, sizes = self._label_domains()
        min_size = min_size_frac * self.N
        macro = sorted((int(s) for s in sizes if s >= min_size), reverse=True)
        return macro

    def _label_domains(self):
        """Connected-component labelling of the same-action field under 4-connectivity
        WITH periodic wrap. Returns (labels (L,L), sizes (n_components,)).

        Uses scipy.ndimage.label per action value if available, with an explicit
        wrap-around merge across the four lattice seams; falls back to a pure-numpy
        union-find on the periodic von-Neumann graph otherwise. Same-action means both
        endpoints +1 or both -1 (the two action values are labelled separately and the
        label spaces concatenated)."""
        a = self.action_grid()
        try:
            from scipy import ndimage  # type: ignore
        except Exception:
            return self._label_domains_unionfind()
        L = self.L
        struct = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.int64)  # 4-conn
        all_labels = np.zeros((L, L), dtype=np.int64)
        offset = 0
        for val in (1, -1):
            mask = a == val
            lab, n = ndimage.label(mask, structure=struct)
            if n == 0:
                continue
            # stitch wrap-around: merge labels touching across the top/bottom & left/right
            # seams (ndimage.label does not wrap). Union-find over the n labels.
            parent = list(range(n + 1))

            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            def union(x, y):
                rx, ry = find(x), find(y)
                if rx != ry:
                    parent[max(rx, ry)] = min(rx, ry)

            # top-bottom seam: row 0 neighbours row L-1
            for c in range(L):
                if mask[0, c] and mask[L - 1, c]:
                    union(lab[0, c], lab[L - 1, c])
            # left-right seam: col 0 neighbours col L-1
            for r in range(L):
                if mask[r, 0] and mask[r, L - 1]:
                    union(lab[r, 0], lab[r, L - 1])
            # relabel with merged roots, offset into the global label space
            for r in range(L):
                for c in range(L):
                    if mask[r, c]:
                        all_labels[r, c] = offset + find(lab[r, c])
            offset += n + 1
        # compactify labels and count sizes (ignore background 0)
        flat = all_labels.ravel()
        nonzero = flat[flat > 0]
        if nonzero.size == 0:
            return all_labels, np.array([], dtype=np.int64)
        uniq, counts = np.unique(nonzero, return_counts=True)
        return all_labels, counts.astype(np.int64)

    def _label_domains_unionfind(self):
        """Pure-numpy fallback: union-find over the periodic von-Neumann graph, merging
        only same-action bonds. Returns (labels (L,L), sizes)."""
        a = self.actions()
        nb = self.neighbours
        parent = np.arange(self.N)

        def find(x):
            root = x
            while parent[root] != root:
                root = parent[root]
            while parent[x] != root:
                parent[x], x = root, parent[x]
            return root

        for i in range(self.N):
            ai = a[i]
            for k in range(4):
                j = nb[i, k]
                if a[j] == ai:
                    ri, rj = find(i), find(int(j))
                    if ri != rj:
                        parent[max(ri, rj)] = min(ri, rj)
        roots = np.array([find(i) for i in range(self.N)])
        uniq, counts = np.unique(roots, return_counts=True)
        labels = roots.reshape(self.L, self.L)
        return labels, counts.astype(np.int64)

    # -- ensemble run --
    def run(self, n_updates: int, *, snapshots: Optional[List[int]] = None  # type: ignore[override]
            ) -> Dict[str, Any]:
        """Run ``n_updates`` asynchronous CODA updates from the seeded initial state and
        return a metrics summary. ``snapshots`` is an optional sorted list of cumulative-
        update counts at which to record the full metric set (for the P1 growth check at
        2M and 4M and the P2 histogram). The final state is always recorded.

        Returns the per-snapshot metrics and the final domain / clustering / extremity
        numbers needed to grade the locked clauses.
        """
        if n_updates < 0:
            raise ValueError("n_updates must be non-negative")
        snaps = sorted(set(snapshots or [])) if snapshots else []
        snaps = [s for s in snaps if 0 < s <= n_updates]
        if not snaps or snaps[-1] != n_updates:
            snaps.append(n_updates)

        records: List[Dict[str, Any]] = []
        done = 0
        for target in snaps:
            self.update_batch(target - done)
            done = target
            records.append(self._snapshot_metrics(done))

        final = records[-1]
        return {
            "L": self.L, "N": self.N, "alpha": self.alpha, "nu": self.nu,
            "p_lo": self.p_lo, "p_hi": self.p_hi, "seed": self.seed_value,
            "n_updates": n_updates, "snapshot_updates": [r["updates"] for r in records],
            "snapshots": records,
            "final": final,
        }

    def _snapshot_metrics(self, updates: int) -> Dict[str, Any]:
        """The locked metric set at the current state (after ``updates`` updates)."""
        sizes = self.macroscopic_domain_sizes(min_size_frac=0.05)
        return {
            "updates": int(updates),
            "max_abs_l_over_nu": self.max_abs_l_over_nu(),
            "median_abs_l_over_nu": self.median_abs_l_over_nu(),
            "frac_extreme_ge50": self.fraction_extreme(50.0),
            "frac_moderate_lt1": self.fraction_moderate(1.0),
            "like_neighbour_fraction": self.like_neighbour_fraction(),
            "n_components_all": self.domain_count(min_size_frac=0.0),
            "n_macro_domains": self.domain_count(min_size_frac=0.05),
            "macro_domain_sizes": sizes,
            "frac_action_plus": float(np.mean(self.actions() == 1)),
        }


# -- ensemble API -------------------------------------------------------------

def run_single(L: int = 50, *, alpha: float = 0.7, p_lo: float = 0.4, p_hi: float = 0.6,
               seed: int = 0, n_updates: int = 2_000_000,
               snapshots: Optional[List[int]] = None) -> Dict[str, Any]:
    """One CODA run at a given seed and the fixed lattice / likelihood / init-band."""
    return CODAModel(L, alpha=alpha, p_lo=p_lo, p_hi=p_hi, seed=seed).run(
        n_updates, snapshots=snapshots)


def baseline_domain_count(L: int = 50, *, p_lo: float = 0.4, p_hi: float = 0.6,
                          seed: int = 0, min_size_frac: float = 0.05) -> Dict[str, Any]:
    """The RANDOM-START control: the same seeded initial belief draw with NO updates.

    At t=0 actions are an essentially random +/-1 field (each p_i ~ U(p_lo,p_hi) is
    independent), so same-action sites do NOT form contiguous macroscopic domains —
    there are very many tiny components. Used as the fair 'before' baseline against
    which the late-time domain count and like-neighbour fraction are compared (the lock's
    P3 demands far fewer clusters than this random-start count)."""
    m = CODAModel(L, p_lo=p_lo, p_hi=p_hi, seed=seed)
    return {
        "L": L, "N": m.N, "seed": seed,
        "n_components_all": m.domain_count(min_size_frac=0.0),
        "n_macro_domains": m.domain_count(min_size_frac=min_size_frac),
        "like_neighbour_fraction": m.like_neighbour_fraction(),
        "median_abs_l_over_nu": m.median_abs_l_over_nu(),
        "max_abs_l_over_nu": m.max_abs_l_over_nu(),
    }


def run_many_seeds(L: int = 50, *, alpha: float = 0.7, p_lo: float = 0.4, p_hi: float = 0.6,
                   n_seeds: int = 3, seed_base: int = 0, n_updates: int = 2_000_000,
                   snapshots: Optional[List[int]] = None) -> Dict[str, Any]:
    """Run ``n_seeds`` CODA runs (seed ``seed_base + i``) at fixed parameters and collect
    the per-seed snapshot metrics + the random-start baseline domain count for each seed.

    Returns the per-seed run dicts, the per-seed baselines, and convenience cross-seed
    aggregates of the locked quantities (max |l|/nu at each snapshot, late like-neighbour
    fraction, macroscopic-domain counts).
    """
    runs = [run_single(L, alpha=alpha, p_lo=p_lo, p_hi=p_hi, seed=seed_base + i,
                        n_updates=n_updates, snapshots=snapshots)
            for i in range(n_seeds)]
    baselines = [baseline_domain_count(L, p_lo=p_lo, p_hi=p_hi, seed=seed_base + i)
                 for i in range(n_seeds)]
    return {
        "L": L, "N": L * L, "alpha": alpha, "nu": coda_nu(alpha),
        "p_lo": p_lo, "p_hi": p_hi,
        "n_seeds": n_seeds, "seed_base": seed_base, "n_updates": n_updates,
        "snapshots": snapshots,
        "runs": runs,
        "baselines": baselines,
    }
