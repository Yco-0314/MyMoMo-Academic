"""Axtell's Model of Firms (Axtell 1999/2001) — a faithful agent-based reproduction.

Source: Axtell, R. (1999), "The Emergence of Firms in a Population of Agents:
Local Increasing Returns, Unstable Nash Equilibria, and Power Law Size
Distributions", CSED Working Paper No. 3, Brookings Institution / SFI. See also
Axtell, R. (2001), "Zipf Distribution of U.S. Firm Sizes", Science 293:1818.

The mechanism (verified against the paper's equations):

  Population of A agents. Each agent i carries a FIXED Cobb-Douglas preference
  ``theta_i ~ U(0,1)`` over its INCOME (an equal share of its firm's output) and
  its LEISURE (``1 - e_i``), where ``e_i in [0,1]`` is its effort. Firms are groups
  of agents. A firm whose members supply a TOTAL effort ``E = sum_j e_j`` produces

      O(E) = a*E + b*E**2                                          (increasing returns)

  with base-case constants ``a = b = 1`` (the ``b*E**2`` term is the local
  increasing return — the whole point of forming a firm). Output is shared EQUALLY:
  a member of an ``n``-member firm receives income ``O(E)/n``. So a member's utility is

      U_i = ( O(E) / n ) ** theta_i  *  ( 1 - e_i ) ** (1 - theta_i).     (eq. 3)

  When an agent is ACTIVATED (random asynchronous activation, one agent at a time)
  it takes every OTHER agent's effort as fixed and, for each option in

      { stay in current firm, start a new singleton firm,
        join friend-1's firm, join friend-2's firm }

  computes its own BEST-RESPONSE effort ``e_i*`` (the effort that maximises its own
  utility inside that firm) and the utility it would then obtain; it moves to
  whichever option yields the highest utility and sets its effort to that option's
  ``e_i*``. Each agent has ``nu = 2`` FIXED random network neighbours (assigned once);
  the two "friend firms" are the firms those neighbours currently belong to. This is
  the paper's limited-information myopic best response — an agent scans only its own
  firm, a fresh singleton, and its two friends' firms, NOT all firms.

  Best-response effort (others' effort ``Ebar`` held fixed) solves the first-order
  condition ``theta*O'(S)*(1-e) = (1-theta)*O(S)`` (S = Ebar+e, O' = a+2bS), a quadratic
  in ``e`` for ``b > 0``; the best response is whichever of {0, 1, its roots in (0,1)}
  maximises the utility (the leisure-lover corner is ``e* = 0``). The reference
  implementation also exposes a numerical LINE SEARCH over ``e in [0,1]`` (the paper's
  footnote-31 method); the closed-form and line-search efforts agree to grid resolution.

  A "period" is ``A`` random activations (on average one per agent). Starting from
  all-singletons, the firm-size distribution runs to a STATIONARY shape.

Stylized facts (the locked grading metrics, evaluated in examples/repro_axtell_firms/run.py):
    P1  firm-size distribution is Zipf: rank-size log-log OLS slope in [-1.5, -0.7].
    P2  firm-size inequality is extreme: Gini of firm sizes >= 0.60, strongly right-skewed.
    P3  firm log-GROWTH-RATE distribution is tent-shaped (Laplace, not Gaussian):
        excess kurtosis of pooled log-growth rates > 1.5, AND growth-rate std
        DECREASES with firm size (Stanley et al. 1996 scaling; negative log-log slope).

Built on the neutral platform (``abm_auto._platform``): each agent is a ``FirmAgent``
carrying its own ``theta``, ``effort``, ``firm`` id, and two fixed ``friends``; the
``AxtellFirmsModel`` owns the firm registry (total effort + member count cached and
updated INCREMENTALLY on every move, so an activation is O(1) in the number of firms)
and drives random asynchronous activation over the ``AgentSet`` roster. Deterministic
given a seed. Distinct from sugarscape (individual wealth on a fixed landscape, no
groups): here FIRMS form endogenously and their SIZE distribution is the observable.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- production + utility ------------------------------------------------------

def output(E: float, a: float, b: float) -> float:
    """Firm output for total effort ``E``: O(E) = a*E + b*E**2 (increasing returns)."""
    return a * E + b * E * E


def utility(income: float, effort: float, theta: float) -> float:
    """Cobb-Douglas utility over income share and leisure (paper eq. 3):

        U = income**theta * (1 - effort)**(1 - theta).

    income = O(E)/n (the equal share); leisure = 1 - effort. Non-positive income or
    zero leisure gives utility 0 (a member with no leisure or no income is at a corner
    with no Cobb-Douglas value)."""
    leisure = 1.0 - effort
    if income <= 0.0 or leisure <= 0.0:
        return 0.0
    return (income ** theta) * (leisure ** (1.0 - theta))


def best_effort_closed_form(theta: float, Ebar: float, a: float, b: float) -> float:
    """Utility-maximising effort in [0,1] given the OTHER members' total effort ``Ebar``
    held fixed. Maximises U(e) = O(Ebar+e)**theta * (1-e)**(1-theta) (the ``1/n`` share
    is a positive constant in ``e``, so it does not move the argmax).

    Its first-order condition ``theta*O'(S)*(1-e) = (1-theta)*O(S)`` (S = Ebar + e,
    O' = a + 2bS) is a quadratic in ``e`` for the increasing-returns case ``b > 0``:

        A2 e**2 + A1 e + A0 = 0,
        A2 = -b (1 + theta),
        A1 = theta (2b - a - 2b Ebar) - (1 - theta)(a + 2b Ebar),
        A0 = theta (a + 2b Ebar) - (1 - theta)(a Ebar + b Ebar**2).

    The best response is whichever of {0, 1, the roots in (0,1)} maximises the utility
    (an interior stationary point may be a max, or the constrained optimum may sit at the
    ``e*=0`` leisure-lover corner). For ``b == 0`` (constant returns) the FOC is linear:
    e* = theta - Ebar(1 - theta) (paper eq. 6), clamped to [0,1].

    This matches a fine numerical line search over [0,1] to grid resolution (see
    ``best_effort_line_search`` and the tests); it is the fast path the model uses.
    """
    if b == 0.0:
        cand = [_clamp01(theta - Ebar * (1.0 - theta))]
    else:
        A2 = -b * (1.0 + theta)
        A1 = theta * (2.0 * b - a - 2.0 * b * Ebar) - (1.0 - theta) * (a + 2.0 * b * Ebar)
        A0 = (theta * (a + 2.0 * b * Ebar)
              - (1.0 - theta) * (a * Ebar + b * Ebar * Ebar))
        cand = [0.0, 1.0]
        disc = A1 * A1 - 4.0 * A2 * A0
        if disc >= 0.0 and A2 != 0.0:
            root = math.sqrt(disc)
            for sgn in (1.0, -1.0):
                r = (-A1 + sgn * root) / (2.0 * A2)
                if 0.0 <= r <= 1.0:
                    cand.append(r)
    # pick the candidate with the highest utility (share constant -> use n=1).
    best_e, best_u = 0.0, -1.0
    for e in cand:
        u = utility(output(Ebar + e, a, b), e, theta)
        if u > best_u:
            best_u, best_e = u, e
    return best_e


def best_effort_line_search(theta: float, Ebar: float, n: int, a: float, b: float,
                            *, grid: int = 200) -> float:
    """Reference best-response effort by a LINE SEARCH over ``e in [0,1]`` (the paper's
    footnote-31 method): pick the effort that maximises this member's utility

        U(e) = ( O(Ebar + e)/n )**theta * (1 - e)**(1-theta)

    with ``Ebar`` (the OTHER members' total effort) and firm size ``n`` held fixed.
    Used to validate the closed form in tests; the model uses the closed form."""
    best_e = 0.0
    best_u = -1.0
    for k in range(grid + 1):
        e = k / grid
        inc = output(Ebar + e, a, b) / n
        u = utility(inc, e, theta)
        if u > best_u:
            best_u = u
            best_e = e
    return best_e


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


# -- Agent --------------------------------------------------------------------

class FirmAgent(Agent):
    """One agent: a fixed preference ``theta``, a current ``effort`` in [0,1], the id
    of the ``firm`` it belongs to, and two FIXED random network ``friends`` (their
    firms are the migration candidates). The activation logic lives on the model
    (it needs the firm registry), so ``step`` delegates to it."""

    def __init__(self, agent_id: int, model: "AxtellFirmsModel", *, theta: float) -> None:
        super().__init__(agent_id, model)
        self.theta = theta
        self.effort = 0.0
        self.firm = agent_id            # starts as its own singleton firm
        self.friends: Tuple[int, int] = (agent_id, agent_id)  # set after all agents exist

    def step(self) -> None:  # pragma: no cover - activation lives on the model
        self.model.activate(self)


# -- Model --------------------------------------------------------------------

class AxtellFirmsModel(AgentModel):
    """Drives the Axtell (1999) firm-formation dynamics.

    Construct with A agents, the production constants (a, b), the number of fixed
    neighbours ``nu``, and a seed. The firm registry (``firm_effort[f]`` = total member
    effort, ``firm_size[f]`` = member count) is kept EXACT and updated incrementally on
    every effort change and every move, so an activation costs O(nu), not O(#firms).

    ``run(n_periods)`` performs ``n_periods`` periods of ``A`` random activations each,
    sampling the firm-size distribution + per-firm growth each period after a burn-in,
    and returns the stationary size sample + pooled log-growth rates.
    """

    def __init__(self, a_agents: int = 5000, *, a: float = 1.0, b: float = 1.0,
                 nu: int = 2, seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if a_agents <= 1:
            raise ValueError(f"need a_agents > 1 (got {a_agents})")
        if b < 0.0 or a < 0.0:
            raise ValueError(f"need a>=0, b>=0 (got a={a}, b={b})")
        if nu < 1:
            raise ValueError(f"need nu >= 1 (got {nu})")
        self.seed_value = seed
        self.A = int(a_agents)
        self.a = float(a)
        self.b = float(b)
        self.nu = int(nu)

        # agents: fixed theta ~ U(0,1); everyone starts in its own singleton firm.
        self.agent_list: List[FirmAgent] = []
        for i in range(self.A):
            ag = FirmAgent(i, self, theta=self.rng.random())
            self.agent_list.append(ag)
            self.add_agent(ag)

        # fixed random neighbours (distinct from self where possible).
        for ag in self.agent_list:
            ag.friends = self._draw_friends(ag.id)

        # firm registry: firm id -> (total effort, member count). Firm ids are the
        # id of the agent that founded/singleton-seeded them; a firm with size 0 is
        # defunct (dropped from the live view). Start: A singleton firms, effort 0.
        self.firm_effort: Dict[int, float] = {i: 0.0 for i in range(self.A)}
        self.firm_size: Dict[int, int] = {i: 1 for i in range(self.A)}
        self._next_firm_id = self.A     # fresh ids for newly founded firms

        # every agent takes its opening best-response effort as a singleton.
        for ag in self.agent_list:
            self._set_effort(ag, best_effort_closed_form(ag.theta, 0.0, self.a, self.b))

        self.reporter = DataCollector({
            "n_firms": lambda m: m.n_firms(),
            "mean_firm_size": lambda m: m.mean_firm_size(),
            "max_firm_size": lambda m: m.max_firm_size(),
        })

    # -- neighbour assignment --
    def _draw_friends(self, i: int) -> Tuple[int, ...]:
        """``nu`` distinct random neighbour ids (!= i when A > nu)."""
        friends: List[int] = []
        guard = 0
        while len(friends) < self.nu and guard < 100 * self.nu:
            j = self.rng.randrange(self.A)
            if j != i and j not in friends:
                friends.append(j)
            guard += 1
        while len(friends) < self.nu:            # tiny-A fallback
            friends.append(i)
        return tuple(friends)

    # -- firm registry helpers --
    def _set_effort(self, ag: FirmAgent, new_effort: float) -> None:
        """Set ``ag``'s effort and keep its firm's cached total effort exact."""
        f = ag.firm
        self.firm_effort[f] += (new_effort - ag.effort)
        ag.effort = new_effort

    def _remove_from_firm(self, ag: FirmAgent) -> None:
        f = ag.firm
        self.firm_effort[f] -= ag.effort
        self.firm_size[f] -= 1
        if self.firm_size[f] <= 0:               # firm emptied -> defunct
            self.firm_size.pop(f, None)
            self.firm_effort.pop(f, None)

    def _add_to_firm(self, ag: FirmAgent, firm_id: int, effort: float) -> None:
        self.firm_size[firm_id] = self.firm_size.get(firm_id, 0) + 1
        self.firm_effort[firm_id] = self.firm_effort.get(firm_id, 0.0) + effort
        ag.firm = firm_id
        ag.effort = effort

    # -- the activation (myopic best response over the option set) --
    def activate(self, ag: FirmAgent) -> None:
        """One agent's myopic best response: pick effort AND firm to maximise its own
        utility, taking every other agent's effort as fixed.

        Options: stay in current firm, found a new singleton firm, or join either of
        the two friends' firms. For each candidate firm, ``Ebar`` = that firm's total
        effort MINUS this agent's own contribution if it is already a member (so its own
        current effort never double-counts), and the post-move size is used for the
        income share. The agent commits to the argmax option and its best-response
        effort there."""
        a, b = self.a, self.b
        cur = ag.firm

        # candidate firms: current, a brand-new singleton (id -1 sentinel), friends'.
        candidates: List[int] = [cur, -1]
        for fj in ag.friends:
            fj_firm = self.agent_list[fj].firm
            if fj_firm not in candidates:
                candidates.append(fj_firm)

        best_u = -1.0
        best_firm = cur
        best_e = ag.effort
        for firm_id in candidates:
            if firm_id == -1:                    # new singleton: no other effort, n=1
                Ebar = 0.0
                n_after = 1
            else:
                total = self.firm_effort.get(firm_id, 0.0)
                size = self.firm_size.get(firm_id, 0)
                if firm_id == cur:               # already a member: exclude own effort
                    Ebar = total - ag.effort
                    n_after = size               # size unchanged by staying
                else:
                    Ebar = total                 # joining: others' effort is the whole firm
                    n_after = size + 1           # this agent joins
            e_star = best_effort_closed_form(ag.theta, Ebar, a, b)
            income = output(Ebar + e_star, a, b) / n_after
            u = utility(income, e_star, ag.theta)
            if u > best_u:
                best_u = u
                best_firm = firm_id
                best_e = e_star

        # commit: same firm -> just update effort; else move (registry stays exact).
        if best_firm == cur:
            self._set_effort(ag, best_e)
        else:
            self._remove_from_firm(ag)
            if best_firm == -1:                  # found a fresh singleton firm
                new_id = self._next_firm_id
                self._next_firm_id += 1
                self._add_to_firm(ag, new_id, best_e)
            else:
                self._add_to_firm(ag, best_firm, best_e)

    # -- metrics --
    def firm_sizes(self) -> List[int]:
        """Live firm sizes (members >= 1), one entry per non-defunct firm."""
        return [s for s in self.firm_size.values() if s >= 1]

    def n_firms(self) -> int:
        return len(self.firm_sizes())

    def mean_firm_size(self) -> float:
        sizes = self.firm_sizes()
        return sum(sizes) / len(sizes) if sizes else 0.0

    def max_firm_size(self) -> int:
        sizes = self.firm_sizes()
        return max(sizes) if sizes else 0

    def firm_size_map(self) -> Dict[int, int]:
        """A snapshot {firm_id: size} of all live firms (used for growth tracking)."""
        return {f: s for f, s in self.firm_size.items() if s >= 1}

    # -- period-level driving --
    def run_period(self) -> None:
        """One period = ``A`` random asynchronous activations (an average of one per
        agent; some act twice, some not at all — sampling WITH replacement, matching the
        Poisson-clock activation of the paper)."""
        for _ in range(self.A):
            ag = self.agent_list[self.rng.randrange(self.A)]
            self.activate(ag)

    def run(self, n_periods: int = 200, *, burn_in: int = 100,
            sample_gap: int = 5) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_periods`` periods. Discard the first ``burn_in`` periods as the
        transient, then every ``sample_gap`` periods record (i) the current firm-size
        distribution and (ii) the log-growth rate of every firm that survived the gap.

        Returns the final firm-size sample (the last recorded distribution), a POOLED
        list of firm-size samples across the sampling window, the pooled per-firm
        log-growth rates paired with the firm's starting size, and the per-period
        aggregate series (n_firms, mean size, max size).
        """
        if n_periods <= 0 or burn_in < 0 or burn_in >= n_periods:
            raise ValueError(
                f"need 0 <= burn_in < n_periods (got burn_in={burn_in}, n_periods={n_periods})")
        if sample_gap < 1:
            raise ValueError(f"need sample_gap >= 1 (got {sample_gap})")

        self.reporter.collect(self)              # t=0 baseline
        pooled_sizes: List[int] = []
        growth: List[Tuple[float, int]] = []     # (log growth rate, starting size)
        last_map: Optional[Dict[int, int]] = None
        final_sizes: List[int] = self.firm_sizes()

        for p in range(1, n_periods + 1):
            self.run_period()
            self.t += 1
            self.reporter.collect(self)
            if p <= burn_in:
                continue
            if (p - burn_in) % sample_gap != 0:
                continue
            # sampling tick: record the size distribution and firm growth over the gap.
            cur_map = self.firm_size_map()
            sizes_now = list(cur_map.values())
            final_sizes = sizes_now
            pooled_sizes.extend(sizes_now)
            if last_map is not None:
                for fid, s_now in cur_map.items():
                    s_prev = last_map.get(fid)
                    if s_prev is not None and s_prev > 0 and s_now > 0:
                        growth.append((math.log(s_now) - math.log(s_prev), s_prev))
            last_map = cur_map

        return {
            "A": self.A, "a": self.a, "b": self.b, "nu": self.nu, "seed": self.seed_value,
            "n_periods": n_periods, "burn_in": burn_in, "sample_gap": sample_gap,
            "final_firm_sizes": final_sizes,
            "pooled_firm_sizes": pooled_sizes,
            "growth_rates": [g for g, _ in growth],
            "growth_pairs": growth,
            "n_firms_series": self.reporter.series("n_firms"),
            "mean_firm_size_series": self.reporter.series("mean_firm_size"),
            "max_firm_size_series": self.reporter.series("max_firm_size"),
            "final_n_firms": self.n_firms(),
            "final_mean_firm_size": self.mean_firm_size(),
            "final_max_firm_size": self.max_firm_size(),
        }


# -- distribution statistics (Zipf slope, Gini, tent-shape) -------------------

def gini(values: Sequence[float]) -> float:
    """Gini coefficient of a non-negative list (0 = equal, ->1 = extreme inequality).

    Sorted-cumulative form, O(n log n): G = (2 sum_i (i+1) x_i)/(n sum x) - (n+1)/n.
    Empty / all-zero -> 0.0."""
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0:
        return 0.0
    total = sum(xs)
    if total <= 0.0:
        return 0.0
    cum = 0.0
    for i, x in enumerate(xs):
        cum += (i + 1) * x
    return (2.0 * cum) / (n * total) - (n + 1.0) / n


def ols_slope(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Ordinary-least-squares slope of ys on xs. Zero-variance x -> 0.0."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0.0:
        return 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx


def rank_size_slope(sizes: Sequence[int]) -> float:
    """Zipf rank-size log-log OLS slope: sort sizes descending, regress log(rank) on
    log(size). A Zipf law (size ~ 1/rank) gives slope ~ -1. Needs >= 2 distinct sizes."""
    xs = sorted((float(s) for s in sizes if s > 0), reverse=True)
    if len(xs) < 2:
        return 0.0
    log_size = [math.log(s) for s in xs]
    log_rank = [math.log(r + 1) for r in range(len(xs))]
    return ols_slope(log_size, log_rank)


def excess_kurtosis(values: Sequence[float]) -> float:
    """Excess kurtosis (Fisher): E[(x-mu)^4]/sigma^4 - 3. Gaussian = 0; the Laplace /
    double-exponential (tent-shaped in log-density) has excess kurtosis 3. Needs
    variance > 0 (else 0.0)."""
    n = len(values)
    if n < 2:
        return 0.0
    mu = sum(values) / n
    m2 = sum((x - mu) ** 2 for x in values) / n
    if m2 <= 0.0:
        return 0.0
    m4 = sum((x - mu) ** 4 for x in values) / n
    return m4 / (m2 * m2) - 3.0


def growth_std_by_size_slope(pairs: Sequence[Tuple[float, int]],
                             *, min_per_bin: int = 20) -> Tuple[float, List[Tuple[float, float]]]:
    """Stanley scaling: does the standard deviation of firm log-growth DECREASE with
    firm size? Bin the (growth, starting-size) pairs by starting size (log-spaced,
    unit-integer bins collapsed to distinct sizes), compute sigma_growth per size that
    has >= ``min_per_bin`` samples, and return the OLS slope of log(sigma) on log(size)
    plus the (log size, log sigma) points. A negative slope = volatility falls with
    size (the Stanley et al. 1996 result)."""
    by_size: Dict[int, List[float]] = {}
    for g, s in pairs:
        by_size.setdefault(s, []).append(g)
    pts: List[Tuple[float, float]] = []
    for s, gs in sorted(by_size.items()):
        if len(gs) < min_per_bin:
            continue
        m = sum(gs) / len(gs)
        var = sum((x - m) ** 2 for x in gs) / len(gs)
        if var <= 0.0:
            continue
        pts.append((math.log(s), 0.5 * math.log(var)))
    if len(pts) < 2:
        return 0.0, pts
    slope = ols_slope([p[0] for p in pts], [p[1] for p in pts])
    return slope, pts


# -- multi-seed helpers -------------------------------------------------------

def run_single(a_agents: int = 5000, *, a: float = 1.0, b: float = 1.0, nu: int = 2,
               seed: int = 0, n_periods: int = 200, burn_in: int = 100,
               sample_gap: int = 5) -> Dict[str, Any]:
    """One full Axtell-firms run for a given seed at the fixed production constants."""
    res = AxtellFirmsModel(a_agents, a=a, b=b, nu=nu, seed=seed).run(
        n_periods, burn_in=burn_in, sample_gap=sample_gap)
    # per-run graded statistics.
    res["rank_size_slope"] = rank_size_slope(res["final_firm_sizes"])
    res["gini_firm_size"] = gini(res["final_firm_sizes"])
    res["growth_excess_kurtosis"] = excess_kurtosis(res["growth_rates"])
    slope, pts = growth_std_by_size_slope(res["growth_pairs"])
    res["growth_std_size_slope"] = slope
    res["growth_std_size_points"] = pts
    return res


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: Sequence[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / n) ** 0.5


def run_many_seeds(a_agents: int = 5000, *, a: float = 1.0, b: float = 1.0, nu: int = 2,
                   n_seeds: int = 4, seed_base: int = 0, n_periods: int = 200,
                   burn_in: int = 100, sample_gap: int = 5) -> Dict[str, Any]:
    """Run ``n_seeds`` Axtell-firms simulations (seed ``seed_base + i``) at the fixed
    production constants and summarise the three locked stylized facts across seeds:
    the Zipf rank-size slope, the firm-size Gini, and the growth-rate tent-shape
    (excess kurtosis + the sigma-vs-size slope). Returns per-seed values, their
    mean/std/range, one pooled firm-size sample (all seeds) for a combined rank-size
    view, and one representative (first-seed) run for inspection.
    """
    runs = [run_single(a_agents, a=a, b=b, nu=nu, seed=seed_base + i,
                        n_periods=n_periods, burn_in=burn_in, sample_gap=sample_gap)
            for i in range(n_seeds)]
    slopes = [r["rank_size_slope"] for r in runs]
    ginis = [r["gini_firm_size"] for r in runs]
    kurts = [r["growth_excess_kurtosis"] for r in runs]
    std_slopes = [r["growth_std_size_slope"] for r in runs]
    n_firms = [r["final_n_firms"] for r in runs]
    mean_sizes = [r["final_mean_firm_size"] for r in runs]
    max_sizes = [r["final_max_firm_size"] for r in runs]

    pooled_final_sizes: List[int] = []
    for r in runs:
        pooled_final_sizes.extend(r["final_firm_sizes"])

    return {
        "A": a_agents, "a": a, "b": b, "nu": nu,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_periods": n_periods, "burn_in": burn_in, "sample_gap": sample_gap,
        "per_seed_rank_size_slope": slopes,
        "per_seed_gini": ginis,
        "per_seed_growth_kurtosis": kurts,
        "per_seed_growth_std_slope": std_slopes,
        "per_seed_n_firms": n_firms,
        "per_seed_mean_firm_size": mean_sizes,
        "per_seed_max_firm_size": max_sizes,
        "mean_rank_size_slope": _mean(slopes),
        "std_rank_size_slope": _std(slopes),
        "min_rank_size_slope": min(slopes) if slopes else 0.0,
        "max_rank_size_slope": max(slopes) if slopes else 0.0,
        "mean_gini": _mean(ginis),
        "std_gini": _std(ginis),
        "min_gini": min(ginis) if ginis else 0.0,
        "max_gini": max(ginis) if ginis else 0.0,
        "mean_growth_kurtosis": _mean(kurts),
        "std_growth_kurtosis": _std(kurts),
        "min_growth_kurtosis": min(kurts) if kurts else 0.0,
        "max_growth_kurtosis": max(kurts) if kurts else 0.0,
        "mean_growth_std_slope": _mean(std_slopes),
        "std_growth_std_slope": _std(std_slopes),
        "mean_final_n_firms": _mean(n_firms),
        "mean_final_mean_firm_size": _mean(mean_sizes),
        "mean_final_max_firm_size": _mean(max_sizes),
        "pooled_final_firm_sizes": pooled_final_sizes,
        "pooled_rank_size_slope": rank_size_slope(pooled_final_sizes),
        "pooled_gini": gini(pooled_final_sizes),
        # one representative run for plotting / inspection.
        "example_final_firm_sizes": runs[0]["final_firm_sizes"],
        "example_growth_rates": runs[0]["growth_rates"],
        "example_growth_std_points": runs[0]["growth_std_size_points"],
        "example_n_firms_series": runs[0]["n_firms_series"],
        "example_mean_firm_size_series": runs[0]["mean_firm_size_series"],
    }
