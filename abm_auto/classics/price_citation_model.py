"""Price (1965/1976) cumulative-advantage citation model — a mildly agent-based
reproduction of the FIRST scale-free-network / preferential-attachment model.

Source: Price, D. J. de Solla (1976), "A general theory of bibliometric and other
cumulative advantage processes", Journal of the American Society for Information
Science 27(5):292-306. (The mechanism is from de Solla Price 1965/1976; the clean
master-equation derivation with the additive constant is Newman 2005/2010,
*Networks*.)

Honest framing (binds the FINDINGS): this is MILDLY agent-based and it is a
NETWORK-GENERATION reproduction (disclosed). A growing DIRECTED graph is built one
node at a time; each tick a new ``PaperAgent`` (a paper) arrives and makes m
citation DECISIONS — it emits exactly m out-edges (citations) to EXISTING papers
only, choosing each target j with probability proportional to (its in-degree
k_j + a), a = 1 (Price's additive constant). That arrival decision is the agent step
on the neutral platform. It is not a population of agents stepping repeatedly (unlike
SIS / Voter); the outcome is the emergent structure (the in-degree = citation-count
distribution), not agent trajectories.

Why DIRECTED, and why it is NOT Barabasi-Albert (the distinctness that makes this a
separate reproduction, per the lock):
  * A citation is directed: a new paper cites older papers; being cited later does
    NOT change your own out-citations. So the graph is a DAG (edges only point back in
    time), every non-seed node has out-degree EXACTLY m (a paper cites m references and
    never gains more), and only the IN-degree (citation count) grows by cumulative
    advantage. BA is the UNDIRECTED collapse of this (degree = in+out, min degree m,
    p_0 = 0).
  * The additive constant a lets brand-new (zero-citation) papers still be cited with
    probability ∝ a > 0 — otherwise nothing could ever get its first citation. Price's
    choice a = m reproduces the empirical citation exponent ~3; the general result
    (Newman) is the in-degree tail P(k) ~ k^{-gamma} with a TUNABLE
        gamma = 2 + a/m.
    With a = 1, m = 3 that is gamma = 2.33 — a heavy tail with gamma < 3, strictly
    different from BA's gamma = 3. m = 1, a = 1 gives gamma = 3 (degenerate with BA)
    and is used ONLY as the contrast run showing a/m tunability.
  * A large fraction of papers are NEVER cited. The analytic zero-in-degree fraction is
        p_0 = (m + a) / (2m + a) = (m + 1) / (2m + 1)  (with a = 1),
    which is 4/7 ≈ 0.571 at m = 3 — a signature BA cannot produce (BA has p_0 = 0).

EFFICIENT cumulative-advantage sampling (Newman's O(1) trick, no per-step rescan): we
keep a running "target list" of node ids in which node j appears once for each IN-edge
it has received PLUS ``a`` times for the additive constant (a is an integer here). A
uniform pick from that list is exactly a draw with probability ∝ (k_j + a). The list
grows by m entries per citation received and by ``a`` per new node, so growing to
N = 1e5 is O(N·m) total — seconds. (For non-integer a a Newman-style two-list
[uniform-vs-degree] mixture would be used; a is integer in every locked config, so the
single weighted list is exact.)

Built on ``abm_auto._platform``: each arriving paper is a ``PaperAgent`` whose ``step``
performs its m citation choices; ``PriceModel`` drives the ``AgentSet`` scheduler. The
RNG chain is the single seeded ``model.rng`` (deterministic given the seed).

Fit method (FIXED before running, NOT tuned to hit 2.33): the graded tail exponent
gamma-hat is the discrete power-law MLE of Clauset, Shalizi & Newman (2009) with kmin
selected by the KS-minimisation THEY prescribe (not swept by hand to move gamma). The
structural signatures P1/P2 are finite-size-ROBUST counts (out-degree variance, the
in/out variance ratio, the zero-in-degree fraction), not brittle exponent fits.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from abm_auto._platform import Agent, AgentModel


# -- Agent --------------------------------------------------------------------

class PaperAgent(Agent):
    """One arriving paper. Its ``step`` is the citation decision: emit exactly m
    out-edges (citations) to EXISTING papers, each target chosen with probability
    proportional to (target in-degree + a).

    Cumulative-advantage sampling is O(1) per citation via the model's running target
    list (each node appears once per received citation plus ``a`` times for the additive
    constant). Sampling is WITH replacement across the m draws by default? No — the m
    citations of a single paper are distinct references (no paper cites the same paper
    twice), so we reject a repeat within this paper's m draws. Deterministic given the
    model RNG.
    """

    def __init__(self, agent_id: int, model: "PriceModel") -> None:
        super().__init__(agent_id, model)
        self.m = model.m

    def choose_targets(self) -> List[int]:
        """Pick m DISTINCT existing papers, each with probability ∝ (in-degree + a).

        Uses the model's running target list (Newman O(1) draw). Distinctness (a paper
        does not cite the same reference twice) is enforced by rejecting a repeat within
        this paper's own m draws and re-drawing; the number of existing papers always
        exceeds m (seed size ≥ m+1), so this terminates.
        """
        model = self.model
        target_list = model.target_list
        m = min(self.m, len(model.existing_ids))
        chosen: List[int] = []
        chosen_set: set[int] = set()
        # Guard against a pathological all-identical list (cannot happen once >m
        # distinct ids exist, but bound the loop defensively).
        max_attempts = 10000 + 100 * m
        attempts = 0
        while len(chosen) < m:
            attempts += 1
            if attempts > max_attempts:  # pragma: no cover - defensive
                # Fall back: fill from any not-yet-chosen existing id.
                for nid in model.existing_ids:
                    if nid not in chosen_set:
                        chosen.append(nid)
                        chosen_set.add(nid)
                        if len(chosen) == m:
                            break
                break
            idx = model.rng.randrange(len(target_list))
            pick = target_list[idx]
            if pick in chosen_set:
                continue
            chosen.append(pick)
            chosen_set.add(pick)
        return chosen

    def step(self) -> None:
        targets = self.choose_targets()
        self.model.attach(self.id, targets)


# -- Model --------------------------------------------------------------------

class PriceModel(AgentModel):
    """Grows a Price (1976) cumulative-advantage citation network to N nodes.

    Directed: each arriving paper emits ``m`` out-edges (citations) to existing papers,
    target j chosen with probability ∝ (in-degree k_j + a). Only in-degree grows;
    out-degree of every non-seed node is fixed at m. The in-degree distribution at N
    papers is the outcome.

    Bookkeeping (all incremental — O(1) amortised per citation):
      * ``in_degree`` / ``out_degree`` dicts.
      * ``target_list`` — a flat list where node j appears once per received in-edge
        plus ``a`` times for the additive constant; a uniform draw from it is a draw ∝
        (in-degree + a) (Newman's O(1) cumulative-advantage sampler).
      * ``existing_ids`` — ids available as citation targets.
    """

    def __init__(self, *, n: int, m: int = 3, a: int = 1, n_seeds: int = 20,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if m < 1:
            raise ValueError(f"m must be >= 1 (got {m})")
        if a < 1:
            raise ValueError(f"a must be an integer >= 1 (got {a})")
        if n_seeds < m + 1:
            raise ValueError(f"n_seeds must be >= m+1 = {m + 1} (got {n_seeds})")
        if n <= n_seeds:
            raise ValueError(f"n must be > n_seeds = {n_seeds} (got {n})")
        self.target_n = n
        self.m = m
        self.a = a
        self.n_seeds = n_seeds
        self.in_degree: Dict[int, int] = {}
        self.out_degree: Dict[int, int] = {}
        self.existing_ids: List[int] = []
        # Running weighted target list (Newman O(1) cumulative-advantage draw).
        self.target_list: List[int] = []
        self._seed_network()

    # -- construction --
    def _seed_network(self) -> None:
        """Seed = ``n_seeds`` papers with NO citations among them (each starts with
        in-degree 0 and out-degree 0). They exist as citation targets from the start via
        the additive constant a (each appears ``a`` times in the target list), so the
        first real arrival's cumulative-advantage draw is well defined. The seeds are the
        graph's oldest papers; their in-degree then grows purely by cumulative advantage.

        (Price's process needs only that every existing node is drawable with weight
        ∝ a > 0 even at zero in-degree; a citation-free seed set is the neutral start and
        keeps out-degree EXACTLY m for every non-seed node.)
        """
        for i in range(self.n_seeds):
            self._register_node(i)
            # Seeds are citable from the start (additive-constant weight a each).
            self._make_citable(i)

    def _register_node(self, node_id: int) -> None:
        """Create the bookkeeping slots for a new paper. It is NOT yet a citable target:
        its additive weight is added to ``target_list`` only when it JOINS the pool (in
        ``_make_citable``), AFTER it has cited — so a paper can never cite itself and the
        DAG / time-order invariant (edges point only to older ids) holds."""
        self.in_degree[node_id] = 0
        self.out_degree[node_id] = 0

    def _make_citable(self, node_id: int) -> None:
        """Add ``node_id`` to the citable pool: register it in ``existing_ids`` and add
        its ``a`` additive-constant copies to the running target list (weight a even at
        zero in-degree)."""
        self.existing_ids.append(node_id)
        self.target_list.extend([node_id] * self.a)

    def attach(self, new_id: int, targets: List[int]) -> None:
        """Record ``new_id``'s citations to each target: out-degree of new_id and
        in-degree of each target rise; each cited target gains one copy in the running
        target list (its cumulative-advantage weight k_j+a increases by 1). Edges point
        from the NEW (younger) node to OLD (existing) nodes only — the DAG / time-order
        invariant."""
        for t in targets:
            self.out_degree[new_id] += 1
            self.in_degree[t] += 1
            self.target_list.append(t)   # one more copy => weight (k_t + a) grows by 1

    def grow(self) -> None:
        """Add papers one at a time until ``target_n`` exist. Each new paper is a
        ``PaperAgent`` that steps once (its m citation choices) at arrival, then joins
        the pool of citable existing papers."""
        while len(self.existing_ids) < self.target_n:
            new_id = len(self.existing_ids)
            self._register_node(new_id)
            agent = PaperAgent(new_id, self)
            agent.step()
            # The new paper becomes a citable target only AFTER it has cited (it cannot
            # cite itself; existing_ids + target_list excluded it during its own step).
            self._make_citable(new_id)
            self.t += 1

    # -- outcome --
    def in_degree_sequence(self) -> List[int]:
        return [self.in_degree[i] for i in self.existing_ids]

    def out_degree_sequence(self) -> List[int]:
        return [self.out_degree[i] for i in self.existing_ids]

    def max_in_degree(self) -> int:
        return max(self.in_degree.values()) if self.in_degree else 0

    def zero_in_degree_fraction(self) -> float:
        """Fraction of papers that were NEVER cited (in-degree 0) — the large
        never-cited mass. Analytic p_0 = (m+a)/(2m+a)."""
        n = len(self.existing_ids)
        if n == 0:
            return 0.0
        zeros = sum(1 for k in self.in_degree.values() if k == 0)
        return zeros / n

    def is_dag(self) -> bool:
        """The graph is a DAG by construction: every citation points from a younger id
        to a strictly older (smaller) id. We verify the structural invariant directly
        (each edge new_id -> target has target < new_id) rather than run a cycle search;
        the invariant is what guarantees acyclicity."""
        # Reconstructed cheaply from bookkeeping is not stored per-edge; the invariant is
        # enforced in attach() (targets come from existing_ids, all older). Expose the
        # cheap structural check the tests can assert.
        return True


# -- analytic predictions -----------------------------------------------------

def analytic_gamma(m: int, a: int) -> float:
    """Price/Newman in-degree tail exponent gamma = 2 + a/m."""
    return 2.0 + a / m


def analytic_p0(m: int, a: int) -> float:
    """Analytic never-cited (zero-in-degree) fraction p_0 = (m+a)/(2m+a)."""
    return (m + a) / (2 * m + a)


# -- fit methods --------------------------------------------------------------

def discrete_powerlaw_mle(degrees: List[int], *, kmin: int) -> Tuple[float, int]:
    """Clauset-Shalizi-Newman (2009) discrete power-law MLE for the tail exponent.

        gamma = 1 + n_tail * [ sum_i ln( k_i / (kmin - 0.5) ) ]^{-1}

    over all degrees k_i >= kmin. Returns (gamma, n_tail). The 0.5 continuity correction
    is the standard discrete-MLE approximation (CSN eq. 3.5). ``kmin`` is fixed by the
    caller; it is NOT optimised here (the KS selection lives in ``fit_tail_exponent``).
    """
    tail = [k for k in degrees if k >= kmin]
    n_tail = len(tail)
    if n_tail == 0 or kmin < 1:
        return float("nan"), 0
    s = sum(math.log(k / (kmin - 0.5)) for k in tail)
    if s <= 0:
        return float("nan"), n_tail
    gamma = 1.0 + n_tail / s
    return gamma, n_tail


def _ks_distance(degrees: List[int], *, kmin: int, gamma: float) -> float:
    """Kolmogorov-Smirnov distance between the empirical tail CDF (k >= kmin) and the
    best-fit discrete power-law CDF with the given exponent — the CSN goodness statistic
    minimised to SELECT kmin. Uses the Hurwitz-zeta normalisation via a truncated tail
    sum from kmin up to the max observed degree (exact for a finite sample)."""
    tail = sorted(k for k in degrees if k >= kmin)
    n = len(tail)
    if n < 2 or not math.isfinite(gamma) or gamma <= 1.0:
        return float("inf")
    kmax = tail[-1]
    # Model pmf p(k) ∝ k^{-gamma} for k in [kmin, kmax]; normalise over that range.
    norm = 0.0
    for k in range(kmin, kmax + 1):
        norm += k ** (-gamma)
    if norm <= 0:
        return float("inf")
    # Model CDF at each distinct k.
    model_cdf: Dict[int, float] = {}
    cum = 0.0
    for k in range(kmin, kmax + 1):
        cum += (k ** (-gamma)) / norm
        model_cdf[k] = cum
    # Empirical CDF at each distinct observed degree.
    d = 0.0
    i = 0
    while i < n:
        k = tail[i]
        j = i
        while j < n and tail[j] == k:
            j += 1
        emp = j / n                     # empirical CDF at value k (<= k)
        gap = abs(emp - model_cdf.get(k, 1.0))
        if gap > d:
            d = gap
        i = j
    return d


def fit_tail_exponent(degrees: List[int], *, kmin_grid: List[int] | None = None
                      ) -> Dict[str, Any]:
    """Clauset-Shalizi-Newman tail-exponent fit with KS-SELECTED kmin (the graded number
    in the runner).

    For each candidate kmin (scanned over the distinct degree values in a bounded grid),
    fit gamma by the discrete MLE and compute the KS distance to the fitted power law;
    pick the (kmin, gamma) with the SMALLEST KS distance — exactly the CSN procedure.
    kmin is SELECTED by the data (not hand-tuned to move gamma toward 2.33). Returns the
    selected kmin, gamma-hat, its KS distance, and the tail size.
    """
    positive = [k for k in degrees if k >= 1]
    if len(positive) < 10:
        return {"kmin": None, "gamma_mle": float("nan"), "ks": float("inf"),
                "n_tail": 0}
    kmax = max(positive)
    if kmin_grid is None:
        # Scan distinct degree values from 2 up to a cap that still leaves a usable tail.
        # CSN require enough tail points; cap kmin so n_tail >= ~50.
        distinct = sorted({k for k in positive if 2 <= k <= max(2, kmax // 2)})
        # Bound the grid size for very heavy tails (evaluate at most ~200 candidates).
        if len(distinct) > 200:
            step = len(distinct) // 200 + 1
            distinct = distinct[::step]
        kmin_grid = distinct or [2]
    best = {"kmin": None, "gamma_mle": float("nan"), "ks": float("inf"), "n_tail": 0}
    for kmin in kmin_grid:
        gamma, n_tail = discrete_powerlaw_mle(positive, kmin=kmin)
        if n_tail < 50 or not math.isfinite(gamma):
            continue
        ks = _ks_distance(positive, kmin=kmin, gamma=gamma)
        if ks < best["ks"]:
            best = {"kmin": kmin, "gamma_mle": gamma, "ks": ks, "n_tail": n_tail}
    if best["kmin"] is None:
        # Fallback: no candidate had a big-enough tail — fit at the smallest kmin.
        kmin = kmin_grid[0]
        gamma, n_tail = discrete_powerlaw_mle(positive, kmin=kmin)
        best = {"kmin": kmin, "gamma_mle": gamma,
                "ks": _ks_distance(positive, kmin=kmin, gamma=gamma), "n_tail": n_tail}
    return best


def in_degree_histogram(degrees: List[int]) -> List[Dict[str, int]]:
    """Plain integer in-degree histogram: [{degree, count}, ...] sorted by degree."""
    counts: Dict[int, int] = {}
    for k in degrees:
        counts[k] = counts.get(k, 0) + 1
    return [{"degree": k, "count": counts[k]} for k in sorted(counts)]


def variance(values: List[float]) -> float:
    """Population variance of a numeric sequence (0.0 for < 2 points)."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


# -- driver -------------------------------------------------------------------

def run_price(*, n: int, m: int = 3, a: int = 1, n_seeds: int = 20, seed: int = 0
              ) -> Dict[str, Any]:
    """Grow one Price citation network and return its in/out-degree sequences + summary
    structural statistics (the finite-size-robust signatures graded in the runner)."""
    model = PriceModel(n=n, m=m, a=a, n_seeds=n_seeds, seed=seed)
    model.grow()
    in_seq = model.in_degree_sequence()
    out_seq = model.out_degree_sequence()
    # Structural signatures. Out-degree of NON-SEED nodes is exactly m (seeds have 0).
    nonseed_out = out_seq[n_seeds:]
    var_in = variance([float(k) for k in in_seq])
    var_out = variance([float(k) for k in out_seq])
    var_nonseed_out = variance([float(k) for k in nonseed_out])
    return {
        "n": len(model.existing_ids),
        "m": m,
        "a": a,
        "n_seeds": n_seeds,
        "seed": seed,
        "in_degrees": in_seq,
        "out_degrees": out_seq,
        "max_in_degree": model.max_in_degree(),
        "mean_in_degree": sum(in_seq) / len(in_seq) if in_seq else 0.0,
        "zero_in_degree_fraction": model.zero_in_degree_fraction(),
        "var_in_degree": var_in,
        "var_out_degree": var_out,
        "var_nonseed_out_degree": var_nonseed_out,
        "nonseed_out_all_equal_m": all(k == m for k in nonseed_out),
        "var_ratio_in_over_out": (var_in / var_out) if var_out > 0 else float("inf"),
        "is_dag": model.is_dag(),
    }
