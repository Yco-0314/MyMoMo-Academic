"""Pastor-Satorras & Vespignani (2001) — SIS on scale-free networks (the vanishing
epidemic threshold) — a faithful hybrid reproduction.

Source: Pastor-Satorras, R. & Vespignani, A. (2001) "Epidemic spreading in scale-free
networks", Phys. Rev. Lett. 86:3200-3203. doi:10.1103/PhysRevLett.86.3200.

The result: run susceptible-infected-susceptible (SIS) dynamics ON a network. The
heterogeneous mean-field (HMF) epidemic threshold is

    lambda_c = <k> / <k^2>

(the control parameter lambda is the per-S->I-link infection rate; the recovery rate is
fixed to 1, so lambda = infection/recovery). On a scale-free network (Barabasi-Albert,
degree exponent gamma ~= 3) the second moment <k^2> DIVERGES as N -> infinity, so
lambda_c -> 0: there is NO epidemic threshold, an infection with arbitrarily small lambda
survives at a finite endemic prevalence. On a HOMOGENEOUS network (Erdos-Renyi / regular,
same <k>) <k^2> is finite, so lambda_c is finite (~ 1/<k>) and small-lambda infections die
out. PSV also derived that near threshold on the SF network the prevalence is STRETCHED-
EXPONENTIAL, rho ~ exp(-1/(m*lambda)) (for the m=const BA graph), rather than the
power-law rho ~ (lambda - lambda_c) of the homogeneous case.

HONEST FRAMING (binds the FINDINGS): this is a HYBRID reproduction — a network GENERATOR
(BA growth / ER / regular) composed with SIS AGENT DYNAMICS run on the generated network.
Two distinct pieces are disclosed: (1) the structure (which we reuse the BA preferential-
attachment idiom for), and (2) the epidemic process on it. The emergent claim (vanishing
threshold on SF vs finite threshold on homogeneous) belongs to neither piece alone — the
well-mixed / homogeneous SIS has a finite threshold; a bare BA generator has no dynamics.

Update rule (discrete-time SYNCHRONOUS SIS, faithful contact process; committed from a
start-of-step snapshot). We discretise the continuous-time process with a fixed time step
``dt`` so that ``lambda`` stays the true rate RATIO infection/recovery (recovery rate 1):

    per-step recovery probability      mu       = dt              (recovery rate 1)
    per-link per-step infection prob.   lambda*dt                 (infection rate lambda)

    for each node i (from the start-of-step state s):
      * if s[i] == I:  recover to S with probability dt
      * if s[i] == S:  n_inf = number of infected neighbours (start-of-step);
                       become I with probability 1 - (1 - lambda*dt)^n_inf
    commit all next states at once.

Near the absorbing state 1 - (1-lambda*dt)^n ~= lambda*dt*n, so the S->I inflow linearises
to lambda*dt*(expected infected neighbours) while recovery removes a dt fraction; the dt
CANCELS in the balance, giving the map Theta(t+1) ~= lambda*(<k^2>/<k>)*Theta(t), i.e.
threshold lambda_c = <k>/<k^2> exactly — the PSV result, with NO extra factor from the
nonlinearity (that only bends the curve above threshold). ``dt = 1`` recovers the crude
"recover every step" automaton, which sits at a noticeably higher EFFECTIVE finite-size
threshold (an infected must reinfect within one step or the chain breaks); the smaller
``dt = 0.5`` default is the faithful contact-process limit PSV studied (infecteds get
several steps to transmit), and is what makes the endemic phase visible at small lambda.
For a homogeneous <k>=6 graph the operational threshold lands near 1/<k> ~ 0.15-0.20.

Metastable / QUASI-STATIONARY prevalence sampler (the standard way to measure rho(lambda)
in a finite system that has an absorbing state at rho=0): run the SIS process; whenever it
hits the absorbing state (all recovered), RESTORE the configuration from a randomly chosen
previously-visited ACTIVE state (the Marro-Dickman / de Oliveira-Dickman QS method), so the
sampler averages over the SURVIVING metastable ensemble rather than being dragged to 0 by a
single finite-size extinction. rho is the mean infected fraction over a trailing window
after a relaxation transient.

Two execution paths, verified equal on small N (see the tests):
  * ``NetworkSISModel`` — a faithful platform (`abm_auto._platform`) path: one ``NodeAgent``
    per node, a synchronous staged update on the neutral ``AgentSet`` + ``DataCollector``.
    Readable and idiomatic; used for correctness pinning at modest N.
  * ``sis_qs_run`` — a fast CSR/numpy synchronous updater over the same rule + the same QS
    restart, for the large-N (N=1e5) sweeps the lock requires. It is NOT a different model;
    it is the identical update rule vectorised, and the tests assert the two agree.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from abm_auto._platform import Agent, AgentModel, DataCollector

S, I = 0, 1


# =============================================================================
# Network generation (returns a CSR neighbour structure; no networkx dependency)
# =============================================================================

class Network:
    """An undirected simple graph stored in CSR form for fast neighbour scans.

    ``indptr`` / ``indices`` are the standard compressed-sparse-row neighbour arrays:
    the neighbours of node ``i`` are ``indices[indptr[i]:indptr[i+1]]``. ``degree`` is
    the per-node degree. All arrays are numpy int arrays. This is the shared substrate
    both the faithful platform path and the fast numpy path run SIS on.
    """

    def __init__(self, n: int, adjacency: List[set]) -> None:
        self.n = n
        deg = np.fromiter((len(adjacency[i]) for i in range(n)), dtype=np.int64, count=n)
        indptr = np.zeros(n + 1, dtype=np.int64)
        np.cumsum(deg, out=indptr[1:])
        indices = np.empty(int(indptr[-1]), dtype=np.int64)
        for i in range(n):
            start = indptr[i]
            row = sorted(adjacency[i])
            indices[start:start + len(row)] = row
        self.indptr = indptr
        self.indices = indices
        self.degree = deg
        self.adjacency = adjacency  # kept for the faithful platform path / tests

    # -- degree moments (drive the HMF threshold lambda_c = <k>/<k^2>) --
    def mean_degree(self) -> float:
        return float(self.degree.mean()) if self.n else 0.0

    def second_moment(self) -> float:
        return float((self.degree.astype(np.float64) ** 2).mean()) if self.n else 0.0

    def hmf_threshold(self) -> float:
        """lambda_c = <k> / <k^2> (heterogeneous mean-field). Finite for homogeneous
        graphs, -> 0 as <k^2> grows on scale-free graphs."""
        k2 = self.second_moment()
        return (self.mean_degree() / k2) if k2 > 0 else float("inf")


def build_ba(n: int, m: int, *, seed: int) -> Network:
    """Grow a Barabasi-Albert network to ``n`` nodes with ``m`` edges per arrival, via
    degree-weighted (preferential) attachment without replacement — the same mechanism
    as ``abm_auto.classics.barabasi_albert``. <k> -> 2m; <k^2> grows with N (heavy tail).

    Fast target-list realisation (the classic Barabasi-Albert 1999 / networkx algorithm):
    a running ``repeated_nodes`` list holds each node once per incident edge, so a uniform
    draw from it is exactly a degree-proportional draw. This gives O(1)-amortised sampling
    per edge (O(N*m) total), so N=1e5 builds in well under a second — the exact same
    preferential-attachment law as the O(N)-scan version in ``barabasi_albert.py``, just
    without the per-arrival linear rescan. Attachment is WITHOUT replacement within an
    arrival (redrawn on a collision) so each new node gets m DISTINCT targets.
    """
    if m < 1:
        raise ValueError("m must be >= 1")
    if n <= m:
        raise ValueError("n must be > m")
    rng = random.Random(seed)
    adjacency: List[set] = [set() for _ in range(n)]
    seed_size = m + 1
    # Seed clique on m+1 nodes (each starts with degree m; first draw well-defined).
    repeated_nodes: List[int] = []
    for i in range(seed_size):
        for j in range(i + 1, seed_size):
            adjacency[i].add(j)
            adjacency[j].add(i)
            repeated_nodes.append(i)
            repeated_nodes.append(j)
    for new_id in range(seed_size, n):
        targets: set = set()
        while len(targets) < m:
            # degree-proportional draw = uniform draw from the repeated-node list
            targets.add(repeated_nodes[rng.randrange(len(repeated_nodes))])
        for t in targets:
            adjacency[new_id].add(t)
            adjacency[t].add(new_id)
            repeated_nodes.append(t)          # each endpoint gains an incident edge
            repeated_nodes.append(new_id)
    return Network(n, adjacency)


def build_er(n: int, mean_degree: float, *, seed: int) -> Network:
    """Erdos-Renyi G(n, p) at target ``mean_degree`` (p = mean_degree/(n-1)), sampled
    with the Batagelj-Brandes (2005) geometric-skip method (exact, O(edges), no O(n^2)).
    Homogeneous control: Poisson degrees, <k^2> ~= <k>^2 + <k> (finite), so lambda_c is
    finite. Same generator idiom as ``abm_auto.classics.barabasi_albert.er_max_degree``.
    """
    if n < 2:
        raise ValueError("n must be >= 2")
    rng = random.Random(seed)
    p = mean_degree / (n - 1)
    adjacency: List[set] = [set() for _ in range(n)]
    if p <= 0:
        return Network(n, adjacency)
    log1mp = math.log(1.0 - p)
    v = 1
    w = -1
    while v < n:
        r = rng.random()
        w = w + 1 + int(math.floor(math.log(1.0 - r) / log1mp))
        while w >= v and v < n:
            w = w - v
            v = v + 1
        if v < n:
            adjacency[v].add(w)
            adjacency[w].add(v)
    return Network(n, adjacency)


def build_regular(n: int, k: int, *, seed: int) -> Network:
    """A random k-regular graph (configuration-model pairing with rejection of self/multi
    edges, retried on failure). Every node has degree exactly k, so <k^2> = k^2 exactly —
    the cleanest homogeneous control (lambda_c = k/k^2 = 1/k). ``n*k`` must be even.
    """
    if k < 1 or k >= n:
        raise ValueError("require 1 <= k < n")
    if (n * k) % 2 != 0:
        raise ValueError("n*k must be even for a k-regular graph")
    rng = random.Random(seed)
    # Stub-pairing configuration model with an EDGE-SWAP repair on each collision (a
    # single self/multi-edge does not discard the whole graph — it triggers a local
    # swap against an already-placed edge). Far more reliable than full-restart pairing
    # at k=6, n large. Retry the whole build a few times only if repair stalls.
    for _attempt in range(50):
        adjacency: List[set] = [set() for _ in range(n)]
        edges: List[Tuple[int, int]] = []
        stubs: List[int] = []
        for node in range(n):
            stubs.extend([node] * k)
        rng.shuffle(stubs)
        stalled = False
        for idx in range(0, len(stubs), 2):
            a, b = stubs[idx], stubs[idx + 1]
            if a != b and b not in adjacency[a]:
                adjacency[a].add(b)
                adjacency[b].add(a)
                edges.append((a, b))
                continue
            # Collision: swap endpoints with a random existing edge (c, d) -> (a, c) & (b, d)
            # (or (a, d) & (b, c)) if that yields two valid simple edges.
            placed = False
            for _try in range(200):
                if not edges:
                    break
                ei = rng.randrange(len(edges))
                c, d = edges[ei]
                for x, y in ((c, d), (d, c)):
                    if (a != x and b != y and x not in adjacency[a] and y not in adjacency[b]
                            and a not in adjacency[x] and b not in adjacency[y]):
                        # remove old edge (c,d), add (a,x) and (b,y)
                        adjacency[c].discard(d)
                        adjacency[d].discard(c)
                        adjacency[a].add(x)
                        adjacency[x].add(a)
                        adjacency[b].add(y)
                        adjacency[y].add(b)
                        edges[ei] = (a, x)
                        edges.append((b, y))
                        placed = True
                        break
                if placed:
                    break
            if not placed:
                stalled = True
                break
        if not stalled and all(len(adjacency[i]) == k for i in range(n)):
            return Network(n, adjacency)
    raise RuntimeError("failed to build a simple k-regular graph; retry with another seed")


# =============================================================================
# Faithful platform SIS path (one agent per node) — correctness pinning at modest N
# =============================================================================

class NodeAgent(Agent):
    """One network node running SIS. ``state`` is S/I; ``_next`` is staged from the
    start-of-step snapshot and committed by the model (synchronous update)."""

    def __init__(self, agent_id: int, model: "NetworkSISModel", *, state: int = S) -> None:
        super().__init__(agent_id, model)
        self.state = state
        self._next = state

    def stage(self) -> None:
        model = self.model
        if self.state == I:
            # recover with prob mu = dt (recovery rate 1 over a step of length dt)
            self._next = S if model.rng.random() < model.mu else I
        else:
            # count infected neighbours from the start-of-step snapshot
            nbrs = model.net.adjacency[self.id]
            n_inf = 0
            snap = model._snap
            for j in nbrs:
                if snap[j] == I:
                    n_inf += 1
            if n_inf == 0:
                self._next = S
            else:
                # per-link per-step infection prob = lambda*dt (infection rate lambda)
                p = 1.0 - (1.0 - model.lam * model.dt) ** n_inf
                self._next = I if model.rng.random() < p else S


class NetworkSISModel(AgentModel):
    """Faithful SIS-on-network on the neutral platform. One ``NodeAgent`` per node; a
    synchronous staged update (snapshot -> stage -> commit) each tick; a ``DataCollector``
    records the infected count. Metastable prevalence = mean I/N over a trailing window,
    with quasi-stationary restart on extinction (restore a saved active configuration)."""

    def __init__(self, net: Network, *, lam: float, dt: float = 0.5, rho0: float = 0.1,
                 ticks: int = 200, tail: int = 100, seed: int = 0,
                 qs: bool = True) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if lam < 0:
            raise ValueError("lam must be >= 0")
        if not (0 < dt <= 1):
            raise ValueError("dt must be in (0, 1]")
        if not (0 < tail <= ticks):
            raise ValueError("tail must be in (0, ticks]")
        self.net = net
        self.lam = lam
        self.dt = dt
        self.mu = dt          # per-step recovery probability (recovery rate 1)
        self.ticks = ticks
        self.tail = tail
        self.qs = qs
        self._snap = np.empty(net.n, dtype=np.int8)
        self.nodes: List[NodeAgent] = []
        for k in range(net.n):
            node = NodeAgent(k, self, state=S)
            self.nodes.append(node)
            self.add_agent(node)
        # seed rho0 fraction infected
        n_seed = max(1, int(round(rho0 * net.n)))
        for k in self.rng.sample(range(net.n), n_seed):
            self.nodes[k].state = I
            self.nodes[k]._next = I
        self._qs_history: List[np.ndarray] = []
        self.reporter = DataCollector({"I": lambda m: m.count_infected()})

    def count_infected(self) -> int:
        return sum(1 for nd in self.nodes if nd.state == I)

    def _state_vector(self) -> np.ndarray:
        return np.fromiter((nd.state for nd in self.nodes), dtype=np.int8, count=self.net.n)

    def step(self) -> None:
        # snapshot start-of-step states
        for k, nd in enumerate(self.nodes):
            self._snap[k] = nd.state
        self.agents.do("stage")
        for nd in self.nodes:
            nd.state = nd._next
        n_inf = self.count_infected()
        if n_inf == 0 and self.qs and self._qs_history:
            # quasi-stationary restart: restore a random previously-seen active config
            restore = self._qs_history[self.rng.randrange(len(self._qs_history))]
            for k, nd in enumerate(self.nodes):
                nd.state = int(restore[k])
        elif n_inf > 0 and self.qs:
            self._qs_history.append(self._state_vector())
            if len(self._qs_history) > 50:
                self._qs_history.pop(0)
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self) -> Dict[str, Any]:  # type: ignore[override]
        self.reporter.collect(self)
        for _ in range(self.ticks):
            self.step()
        i_series = self.reporter.series("I")
        tail_I = i_series[-self.tail:]
        prevalence = (sum(tail_I) / len(tail_I)) / self.net.n if tail_I else 0.0
        return {
            "lam": self.lam, "dt": self.dt, "n": self.net.n,
            "ticks": self.ticks, "tail": self.tail,
            "prevalence": prevalence,
            "I_final": i_series[-1], "I_series": i_series,
        }


# =============================================================================
# Fast CSR / numpy SIS path (identical rule, vectorised) — large-N sweeps
# =============================================================================

def sis_qs_run(net: Network, *, lam: float, dt: float = 0.5, rho0: float = 0.1,
               ticks: int = 200, tail: int = 100, seed: int = 0,
               qs: bool = True) -> Dict[str, Any]:
    """The SAME synchronous SIS update rule as ``NetworkSISModel``, vectorised over the
    CSR arrays with numpy, with the same quasi-stationary restart on extinction. Returns
    the metastable prevalence (mean I/N over the trailing ``tail`` ticks).

    Vectorised update each step (from the start-of-step state ``s``), with the ``dt``
    discretisation (lambda = infection/recovery rate ratio, recovery rate 1):
      * infected-neighbour count per node = CSR segment-sum of s over neighbours;
      * S->I with prob 1-(1-lam*dt)^n_inf; I->S with prob mu = dt; commit synchronously.
    """
    if not (0 < dt <= 1):
        raise ValueError("dt must be in (0, 1]")
    rng = np.random.default_rng(seed)
    n = net.n
    indptr = net.indptr
    indices = net.indices
    s = np.zeros(n, dtype=np.int8)
    n_seed = max(1, int(round(rho0 * n)))
    seed_nodes = rng.choice(n, size=min(n_seed, n), replace=False)
    s[seed_nodes] = 1

    mu = dt
    one_minus_lam = 1.0 - lam * dt
    i_series: List[int] = [int(s.sum())]
    qs_history: List[np.ndarray] = []
    # Prefix-sum boundaries for a robust CSR segment-sum (handles empty rows and the final
    # segment without reduceat's out-of-bounds / empty-row quirks): n_inf[i] =
    # cumsum[indptr[i+1]] - cumsum[indptr[i]], with cumsum[0] = 0.
    for _ in range(ticks):
        # infected-neighbour count per node: sum of s over each node's CSR neighbour slice
        inf_at_edge = s[indices].astype(np.int64)      # infected flag of each edge endpoint
        prefix = np.empty(inf_at_edge.size + 1, dtype=np.int64)
        prefix[0] = 0
        np.cumsum(inf_at_edge, out=prefix[1:])
        n_inf = prefix[indptr[1:]] - prefix[indptr[:-1]]

        is_S = s == 0
        is_I = s == 1
        p_inf = 1.0 - one_minus_lam ** n_inf           # per-node S->I probability
        draw = rng.random(n)
        new_infections = is_S & (draw < p_inf) & (n_inf > 0)
        if mu >= 1.0:
            recover = is_I                              # dt=1 -> recover every step
        else:
            recover = is_I & (rng.random(n) < mu)

        nxt = s.copy()
        nxt[new_infections] = 1
        nxt[recover] = 0
        s = nxt

        n_now = int(s.sum())
        if n_now == 0 and qs and qs_history:
            s = qs_history[int(rng.integers(len(qs_history)))].copy()
            n_now = int(s.sum())
        elif n_now > 0 and qs:
            qs_history.append(s.copy())
            if len(qs_history) > 50:
                qs_history.pop(0)
        i_series.append(n_now)

    tail_I = i_series[-tail:]
    prevalence = (sum(tail_I) / len(tail_I)) / n if tail_I else 0.0
    return {
        "lam": lam, "dt": dt, "n": n, "ticks": ticks, "tail": tail,
        "prevalence": prevalence, "I_final": i_series[-1],
        "mean_degree": net.mean_degree(), "second_moment": net.second_moment(),
        "hmf_threshold": net.hmf_threshold(),
    }


def sis_prevalence_ensemble(net_builder, *, lam: float, dt: float = 0.5,
                            rho0: float = 0.1, ticks: int = 200, tail: int = 100,
                            n_realizations: int = 4, seed_base: int = 0,
                            qs: bool = True) -> Dict[str, Any]:
    """Average the metastable prevalence over ``n_realizations`` independent
    (network, dynamics) realizations. ``net_builder(seed) -> Network`` regenerates a
    fresh network per realization so the result is not tied to one graph sample.
    Returns the mean/std prevalence and the per-realization list.
    """
    prevalences: List[float] = []
    k1_list: List[float] = []
    k2_list: List[float] = []
    for r in range(n_realizations):
        net = net_builder(seed_base + r)
        res = sis_qs_run(net, lam=lam, dt=dt, rho0=rho0, ticks=ticks, tail=tail,
                         seed=1000 + seed_base + r, qs=qs)
        prevalences.append(res["prevalence"])
        k1_list.append(net.mean_degree())
        k2_list.append(net.second_moment())
    mean = sum(prevalences) / len(prevalences)
    var = sum((p - mean) ** 2 for p in prevalences) / len(prevalences)
    return {
        "lam": lam, "dt": dt, "n_realizations": n_realizations,
        "prevalences": prevalences,
        "mean_prevalence": mean, "std_prevalence": var ** 0.5,
        "mean_degree": sum(k1_list) / len(k1_list),
        "second_moment": sum(k2_list) / len(k2_list),
        "hmf_threshold": (sum(k1_list) / len(k1_list)) / (sum(k2_list) / len(k2_list)),
    }


# =============================================================================
# Threshold estimation + stretched-exponential fit (locked grading metrics)
# =============================================================================

def estimate_threshold(lambdas: Sequence[float], prevalences: Sequence[float],
                       *, rho_star: float = 0.01) -> float:
    """Estimate the effective epidemic threshold as the smallest lambda at which the
    metastable prevalence rises above a small reference level ``rho_star`` (linear
    interpolation between the bracketing grid points). This is a finite-size operational
    threshold, not the thermodynamic one; it is used ONLY to compare BA(N=1e3) vs
    BA(N=1e5) (P1: the estimate must SHRINK with N) and to place the homogeneous
    threshold (P2). It is a fixed rule, not tuned per family.
    """
    lam = list(lambdas)
    rho = list(prevalences)
    # find first index where prevalence crosses rho_star
    for idx in range(1, len(lam)):
        if rho[idx] >= rho_star:
            if rho[idx - 1] >= rho_star:
                # already above at the previous point too; threshold is at/below lam[idx-1]
                return lam[idx - 1] if idx == 1 else lam[0]
            # linear interpolation in (lambda, rho) between idx-1 and idx
            r0, r1 = rho[idx - 1], rho[idx]
            l0, l1 = lam[idx - 1], lam[idx]
            if r1 == r0:
                return l1
            frac = (rho_star - r0) / (r1 - r0)
            return l0 + frac * (l1 - l0)
    return float("inf")  # never crossed rho_star in this lambda range


def fit_stretched_exponential(lambdas: Sequence[float],
                              prevalences: Sequence[float]) -> Dict[str, Any]:
    """Fit rho = A * exp(-C / lambda) by ordinary least squares of ln(rho) on 1/lambda.

        ln rho = ln A - C * (1/lambda)

    Returns C (= -slope), A (= exp(intercept)), and R^2 of the linear fit. Only points
    with rho > 0 are used. This is the PSV stretched-exponential prediction; C is expected
    ~ 1/m for the BA(m) graph. Fixed method — no point dropping to improve R^2.
    """
    xs: List[float] = []
    ys: List[float] = []
    for lam, rho in zip(lambdas, prevalences):
        if rho > 0 and lam > 0:
            xs.append(1.0 / lam)
            ys.append(math.log(rho))
    if len(xs) < 2:
        return {"C": float("nan"), "A": float("nan"), "r_squared": float("nan"),
                "n_points": len(xs)}
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    if sxx == 0:
        return {"C": float("nan"), "A": float("nan"), "r_squared": float("nan"),
                "n_points": n}
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    # R^2
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {
        "C": -slope, "A": math.exp(intercept), "r_squared": r_squared,
        "n_points": n, "xs_inv_lambda": xs, "ys_ln_rho": ys,
    }
