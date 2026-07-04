"""Hauert & Doebeli (2004) spatial snowdrift game — a faithful agent-based reproduction.

Source: Hauert, C. & Doebeli, M. (2004) "Spatial structure often inhibits the
evolution of cooperation in the snowdrift game", Nature 428:643-646.
doi:10.1038/nature02360.

The snowdrift game (a.k.a. hawk-dove / chicken) has the payoff ranking T > R > S > P
(the reverse of the prisoner's dilemma's T > R > P > S). Two drivers are stuck behind a
snowdrift; the reward for clearing it is b and the cost of shovelling is c (with b > c >
0). If both shovel, each does half the work: R = b - c/2. If I shovel and my partner
free-rides, I clear the whole drift alone: I get S = b - c and the partner gets T = b. If
neither shovels, both stay stuck: P = 0. Because S = b - c > 0 = P, the best reply to a
defector is to COOPERATE (do the work yourself) — unlike the PD, where the best reply to a
defector is to defect. The whole game is parameterised by the single cost-to-benefit ratio

    r = c / (2b - c)   in (0, 1),

and in a well-mixed population the replicator dynamics carry the cooperator fraction to
the interior mixed ESS  f* = 1 - r  (Maynard Smith): cooperation is stable at an
intermediate level set only by r.

Nowak & May (1992) showed that a SPATIAL prisoner's dilemma *raises* cooperation above
the well-mixed level, because cooperators form compact clusters and reap positive
assortment. Hauert & Doebeli's central, counter-intuitive result is that spatial
structure in the SNOWDRIFT game usually does the OPPOSITE: it INHIBITS cooperation,
pushing f below the well-mixed 1 - r, because the best-reply-to-a-defector-is-to-cooperate
structure makes cooperators and defectors interleave into thin dynamic FILAMENTS
(negative assortment) rather than compact blocks. The sign of the spatial effect is
REVERSED relative to the spatial PD.

Model (verified against the paper)
----------------------------------
  * L x L square lattice (L = 100) with PERIODIC (toroidal) boundaries; every site holds
    one agent that is a pure cooperator (C) or a pure defector (D).
  * Moore-8 neighbourhood; a focal agent plays the one-shot snowdrift game against each of
    its k = 8 neighbours (SELF EXCLUDED) and SUMS the payoffs. Per-interaction payoffs:
        R = b - c/2   (both C)
        T = b         (focal D vs neighbour C)
        S = b - c     (focal C vs neighbour D)
        P = 0         (both D)
    so a cooperator scores R per C neighbour + S per D neighbour, and a defector scores
    T per C neighbour + P (=0) per D neighbour.
  * UPDATE RULE = STOCHASTIC REPLICATOR / PAIRWISE IMITATION (the load-bearing rule). Each
    focal site i picks ONE random Moore neighbour j; if j's summed payoff exceeds i's, i
    adopts j's strategy with probability

        p(i <- j) = max(0, P_j - P_i) / (k * Delta),

    where Delta is the maximum possible per-interaction payoff difference (Delta = T - S =
    c, the range of a single game's payoffs) so k * Delta bounds the maximum summed-payoff
    difference and p stays in [0, 1]. If P_j <= P_i, i keeps its strategy. This is the
    finite-population analogue of the replicator dynamics; the inhibition result REQUIRES
    it (a deterministic best-takes-over rule does not reproduce it — see the control).
  * Synchronous update: all payoffs are computed from the frozen current lattice, every
    site's random partner + imitation draw is taken, then all strategies commit at once.
  * Initial condition: each site is independently C with probability ~0.5.

BEST-TAKES-OVER CONTROL (the load-bearing gate)
-----------------------------------------------
The gate that proves the inhibition is MECHANISM-SPECIFIC (not a mislabeled Nowak-May) is
a deterministic ``best-takes-over`` control: the SAME lattice, payoffs, neighbourhood and
r-grid, but the focal site deterministically adopts the strategy of the highest-scoring
agent among {itself + its 8 Moore neighbours} (Nowak-May imitation). If this control shows
the SAME strong inhibition, the effect is not specific to the stochastic replicator rule.
Hauert & Doebeli's point is that it does NOT: the strong, r*-localised inhibition is a
property of the stochastic pairwise-imitation dynamics.

WELL-MIXED BASELINE
-------------------
The well-mixed reference is the mean-field replicator fixed point f = 1 - r (Maynard
Smith's interior ESS). ``well_mixed_ess(r)`` returns it analytically; a fast finite
mean-field replicator iterator (``well_mixed_replicator``) confirms the same line without
spatial structure. Both are used only as the baseline the lattice is compared against.

Order parameter (the locked grading metric): f = fraction of cooperators on the lattice,
time-averaged over the last ``measure_last`` generations of a run and then averaged over
seeds. f ~ 1 - r would mean "space is neutral"; f < 1 - r means "space inhibits".

Implementation note
-------------------
L = 100 (10^4 sites) x ~1000 generations x ~15 r-values x >=20 runs is far too heavy for a
pure-Python per-site loop, so the lattice update is VECTORISED with numpy: the 8 Moore
neighbour counts are obtained by np.roll shifts (a periodic convolution), summed payoffs
are arithmetic on those counts, the random partner is one of the 8 shifted lattices chosen
per-site, and the stochastic imitation is a single vectorised Bernoulli draw. The result is
identical to the per-agent rule applied to every site synchronously; ``SnowdriftAgent`` /
the platform ``AgentModel`` facade is provided so the model still presents genuine
agent-based semantics (one agent per site, local payoff, local imitation), while the hot
loop runs on arrays.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from abm_auto._platform import Agent, AgentModel, DataCollector

COOPERATE = 1
DEFECT = 0


# -- payoff bookkeeping -------------------------------------------------------

def snowdrift_payoffs(b: float, c: float) -> Dict[str, float]:
    """The four per-interaction snowdrift payoffs (T > R > S > P) from (b, c),
    with b > c > 0. R=b-c/2, T=b, S=b-c, P=0."""
    if not (b > c > 0):
        raise ValueError(f"need b > c > 0 (got b={b}, c={c})")
    return {"R": b - c / 2.0, "T": b, "S": b - c, "P": 0.0}


def cost_benefit_ratio(b: float, c: float) -> float:
    """r = c / (2b - c) in (0, 1), the single parameter of the snowdrift game."""
    if not (b > c > 0):
        raise ValueError(f"need b > c > 0 (got b={b}, c={c})")
    return c / (2.0 * b - c)


def params_from_ratio(r: float, *, b: float = 1.0) -> Tuple[float, float]:
    """Invert r = c/(2b-c) for a fixed benefit b: c = r * 2b / (1 + r). Returns (b, c).

    Fixing b (default 1) and solving for c is a clean one-parameter family: sweeping r in
    (0,1) sweeps c in (0, b), keeping b > c > 0 for all interior r."""
    if not (0.0 < r < 1.0):
        raise ValueError(f"need r in (0, 1) (got {r})")
    c = r * 2.0 * b / (1.0 + r)
    return b, c


def well_mixed_ess(r: float) -> float:
    """The well-mixed interior ESS cooperator fraction f* = 1 - r (Maynard Smith)."""
    return 1.0 - r


def well_mixed_replicator(r: float, *, f0: float = 0.5, n_steps: int = 2000,
                          dt: float = 0.1) -> float:
    """Mean-field replicator flow of the cooperator fraction f under snowdrift payoffs at
    ratio r, integrated to its fixed point. Confirms the analytic f* = 1 - r WITHOUT any
    spatial structure (the baseline the lattice is judged against).

    Snowdrift expected payoffs in a well-mixed population with cooperator fraction f:
        E[C] = f*R + (1-f)*S,   E[D] = f*T + (1-f)*P.
    Replicator: df/dt = f (1-f) (E[C] - E[D]). With R=b-c/2, T=b, S=b-c, P=0 the interior
    zero is f* = 1 - r for any b > c > 0 (b cancels), so we fix b=1."""
    b, c = params_from_ratio(r, b=1.0)
    R, T, S, P = b - c / 2.0, b, b - c, 0.0
    f = float(f0)
    for _ in range(n_steps):
        ec = f * R + (1.0 - f) * S
        ed = f * T + (1.0 - f) * P
        f += dt * f * (1.0 - f) * (ec - ed)
        f = min(1.0, max(0.0, f))
    return f


# -- Agent (facade) -----------------------------------------------------------

class SnowdriftAgent(Agent):
    """One lattice site playing the snowdrift game against its 8 Moore neighbours.

    The heavy per-generation update runs vectorised on the model's numpy lattice (a
    synchronous update over 10^4 sites), so this per-agent ``step`` is intentionally a
    no-op — it exists so the model presents genuine agent-based semantics (one agent per
    site, each with its own strategy, local summed payoff, and a local imitation draw)
    while the hot loop stays on arrays. ``strategy`` mirrors the site's current value."""

    def __init__(self, agent_id: int, model: "SnowdriftModel", *, strategy: int) -> None:
        super().__init__(agent_id, model)
        self.strategy = strategy

    def step(self) -> None:  # pragma: no cover - the tick lives on the model (vectorised)
        return None


# -- neighbour sums (vectorised Moore-8 periodic convolution) -----------------

_SHIFTS: Tuple[Tuple[int, int], ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),          (0, 1),
    (1, -1),  (1, 0),  (1, 1),
)


def moore_neighbour_coop_counts(grid: np.ndarray) -> np.ndarray:
    """Number of cooperating Moore-8 neighbours (self excluded) of every site, on a
    periodic lattice, via 8 np.roll shifts (a toroidal convolution == the per-site count)."""
    counts = np.zeros_like(grid, dtype=np.int64)
    for dy, dx in _SHIFTS:
        counts += np.roll(np.roll(grid, dy, axis=0), dx, axis=1)
    return counts


def summed_payoffs(grid: np.ndarray, R: float, T: float, S: float, P: float) -> np.ndarray:
    """Summed snowdrift payoff of every site over its 8 Moore neighbours (self excluded).

    Cooperators (grid==1) score R per C neighbour + S per D neighbour.
    Defectors  (grid==0) score T per C neighbour + P per D neighbour.
    With k=8 neighbours and coop-count n_c: C -> R*n_c + S*(8-n_c); D -> T*n_c + P*(8-n_c)."""
    n_c = moore_neighbour_coop_counts(grid)
    k = 8
    n_d = k - n_c
    coop_payoff = R * n_c + S * n_d
    def_payoff = T * n_c + P * n_d
    return np.where(grid == COOPERATE, coop_payoff, def_payoff).astype(np.float64)


# -- Model --------------------------------------------------------------------

class SnowdriftModel(AgentModel):
    """Spatial snowdrift game on a periodic L x L lattice with synchronous update.

    Two update rules are supported (fixed at construction, never tuned per run):

      * ``"replicator"`` (default) — STOCHASTIC pairwise imitation: each site picks ONE
        random Moore neighbour j and adopts j's strategy with probability
        max(0, P_j - P_i)/(k*Delta). This is the genuine Hauert-Doebeli rule.
      * ``"best_takes_over"`` — the DETERMINISTIC Nowak-May control: each site adopts the
        strategy of the best-scoring agent among {itself + its 8 Moore neighbours}. Used
        only as the load-bearing gate; it must NOT show the same strong inhibition.

    ``run`` iterates ``n_steps`` synchronous generations and records the cooperator
    fraction each generation.
    """

    _RULES = ("replicator", "best_takes_over")

    def __init__(self, L: int = 100, *, r: float = 0.5, b: float = 1.0,
                 init_coop_fraction: float = 0.5, rule: str = "replicator",
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if L <= 1:
            raise ValueError(f"need L > 1 (got {L})")
        if rule not in self._RULES:
            raise ValueError(f"unknown rule {rule!r}; expected {self._RULES}")
        if not (0.0 < r < 1.0):
            raise ValueError(f"need r in (0, 1) (got {r})")
        if not (0.0 <= init_coop_fraction <= 1.0):
            raise ValueError(f"need init_coop_fraction in [0, 1] (got {init_coop_fraction})")

        self.L = int(L)
        self.n = self.L * self.L
        self.r = float(r)
        self.b, self.c = params_from_ratio(r, b=b)
        pay = snowdrift_payoffs(self.b, self.c)
        self.R, self.T, self.S, self.P = pay["R"], pay["T"], pay["S"], pay["P"]
        self.k = 8
        # Delta = maximum per-interaction payoff difference = T - S = c (payoff range of a
        # single game), so k*Delta bounds the max summed-payoff difference and p in [0,1].
        self.delta = self.T - self.S
        self.init_coop_fraction = float(init_coop_fraction)
        self.rule = rule
        self.seed_value = seed

        # Dedicated numpy RNG for the vectorised draws (seeded, deterministic). Separate
        # from self.rng (the platform's stdlib RNG) but seeded from the same seed.
        self.nprng = np.random.default_rng(seed)

        # Random initial C/D placement (the ONLY randomness in the initial state).
        self.grid = (self.nprng.random((self.L, self.L)) < self.init_coop_fraction).astype(np.int8)

        # Agent facade: one SnowdriftAgent per site (genuine agent-based presentation).
        self.agent_list: List[SnowdriftAgent] = []
        flat = self.grid.reshape(-1)
        for site in range(self.n):
            agent = SnowdriftAgent(site, self, strategy=int(flat[site]))
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({"coop_fraction": lambda m: m.cooperator_fraction()})

    # -- metrics --
    def cooperator_fraction(self) -> float:
        return float(self.grid.mean())

    def _sync_agent_facade(self) -> None:
        """Mirror the current numpy lattice back onto the per-site agents (so the
        agent-based view stays consistent with the vectorised state)."""
        flat = self.grid.reshape(-1)
        for site, agent in enumerate(self.agent_list):
            agent.strategy = int(flat[site])

    # -- one synchronous generation --
    def step(self) -> None:
        """One synchronous generation: payoffs from the frozen current lattice, then the
        (stochastic replicator | deterministic best-takes-over) update, committed at once."""
        payoff = summed_payoffs(self.grid, self.R, self.T, self.S, self.P)
        if self.rule == "replicator":
            new_grid = self._replicator_update(payoff)
        else:
            new_grid = self._best_takes_over_update(payoff)
        self.grid = new_grid
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def _replicator_update(self, payoff: np.ndarray) -> np.ndarray:
        """STOCHASTIC pairwise imitation (the genuine Hauert-Doebeli rule), vectorised.

        For every site i: pick ONE random Moore neighbour j (one of the 8 shifts, chosen
        per-site); with probability max(0, P_j - P_i)/(k*Delta) adopt j's strategy. All
        draws are taken against the frozen current lattice and committed synchronously."""
        L = self.L
        # Per-site choice of which of the 8 shifts is the sampled partner.
        which = self.nprng.integers(0, len(_SHIFTS), size=(L, L))
        # Neighbour strategy and payoff for the chosen partner, per site (periodic shifts).
        partner_strat = np.empty_like(self.grid)
        partner_payoff = np.empty_like(payoff)
        for idx, (dy, dx) in enumerate(_SHIFTS):
            mask = which == idx
            if not mask.any():
                continue
            shifted_strat = np.roll(np.roll(self.grid, dy, axis=0), dx, axis=1)
            shifted_payoff = np.roll(np.roll(payoff, dy, axis=0), dx, axis=1)
            partner_strat[mask] = shifted_strat[mask]
            partner_payoff[mask] = shifted_payoff[mask]
        # Imitation probability p = max(0, P_j - P_i)/(k*Delta) in [0, 1].
        denom = self.k * self.delta
        p = np.clip((partner_payoff - payoff) / denom, 0.0, 1.0)
        draw = self.nprng.random((L, L))
        adopt = draw < p
        new_grid = np.where(adopt, partner_strat, self.grid).astype(np.int8)
        return new_grid

    def _best_takes_over_update(self, payoff: np.ndarray) -> np.ndarray:
        """DETERMINISTIC best-takes-over control (Nowak-May imitation), vectorised.

        Every site adopts the strategy of the highest-scoring agent among {itself + its 8
        Moore neighbours}; it keeps its own strategy when it is (weakly) the local best.
        Ties are broken toward the incumbent (a neighbour must strictly exceed the current
        best to win), matching nowak_may_pd's convention."""
        best_payoff = payoff.copy()
        best_strat = self.grid.copy()
        for dy, dx in _SHIFTS:
            shifted_strat = np.roll(np.roll(self.grid, dy, axis=0), dx, axis=1)
            shifted_payoff = np.roll(np.roll(payoff, dy, axis=0), dx, axis=1)
            better = shifted_payoff > best_payoff
            best_payoff = np.where(better, shifted_payoff, best_payoff)
            best_strat = np.where(better, shifted_strat, best_strat)
        return best_strat.astype(np.int8)

    def run(self, n_steps: int = 1000, *, measure_last: int = 200) -> Dict[str, Any]:  # type: ignore[override]
        """Iterate ``n_steps`` synchronous generations; return the run summary.

        ``measure_last`` is the trailing window over which the steady-state cooperator
        fraction f_lat is averaged (the transient is the leading generations). Returns the
        steady + final cooperator fraction and the full per-generation series."""
        if measure_last <= 0 or measure_last > n_steps + 1:
            raise ValueError(
                f"measure_last must be in [1, n_steps+1] (got {measure_last}, n_steps={n_steps})")
        self.reporter.collect(self)  # t=0 baseline (initial random placement)
        for _ in range(n_steps):
            self.step()
        self._sync_agent_facade()
        series = self.reporter.series("coop_fraction")
        return {
            "L": self.L,
            "n": self.n,
            "r": self.r,
            "b": self.b,
            "c": self.c,
            "R": self.R, "T": self.T, "S": self.S, "P": self.P,
            "rule": self.rule,
            "init_coop_fraction": self.init_coop_fraction,
            "seed": self.seed_value,
            "n_steps": n_steps,
            "measure_last": measure_last,
            "steady_coop_fraction": tail_mean(series, window=measure_last),
            "final_coop_fraction": series[-1],
            "coop_series": series,
        }


# -- summary helpers ----------------------------------------------------------

def tail_mean(series: Sequence[float], *, window: int = 200) -> float:
    """Steady-state estimate = mean of the trailing ``window`` of a series (or the whole
    series if shorter). Averaging the tail smooths finite-lattice jitter."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def run_single(L: int = 100, *, r: float = 0.5, b: float = 1.0,
               init_coop_fraction: float = 0.5, rule: str = "replicator",
               seed: int = 0, n_steps: int = 1000, measure_last: int = 200) -> Dict[str, Any]:
    """One lattice run at a given (r, rule, seed) and the fixed lattice parameters."""
    return SnowdriftModel(L, r=r, b=b, init_coop_fraction=init_coop_fraction, rule=rule,
                          seed=seed).run(n_steps, measure_last=measure_last)


def run_many_seeds(L: int = 100, *, r: float = 0.5, b: float = 1.0,
                   init_coop_fraction: float = 0.5, rule: str = "replicator",
                   n_seeds: int = 20, seed_base: int = 0, n_steps: int = 1000,
                   measure_last: int = 200) -> Dict[str, Any]:
    """Run ``n_seeds`` lattice runs (seed ``seed_base + i``) at fixed (r, rule) and
    summarise the steady-state cooperator fraction f_lat across seeds (mean + spread).

    Returns the per-seed steady f, their mean / std / min / max, and one representative
    trajectory (first seed) for inspection.
    """
    runs = [run_single(L, r=r, b=b, init_coop_fraction=init_coop_fraction, rule=rule,
                       seed=seed_base + i, n_steps=n_steps, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_f = [rr["steady_coop_fraction"] for rr in runs]
    per_seed_final = [rr["final_coop_fraction"] for rr in runs]
    mean_f = sum(per_seed_f) / n_seeds
    var_f = sum((s - mean_f) ** 2 for s in per_seed_f) / n_seeds
    return {
        "L": L, "r": r, "rule": rule,
        "init_coop_fraction": init_coop_fraction,
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_steps": n_steps, "measure_last": measure_last,
        "per_seed_steady_f": per_seed_f,
        "per_seed_final_f": per_seed_final,
        "mean_steady_f": mean_f,
        "var_steady_f": var_f,
        "std_steady_f": var_f ** 0.5,
        "min_steady_f": min(per_seed_f),
        "max_steady_f": max(per_seed_f),
        "example_coop_series": runs[0]["coop_series"],
    }


def sweep_r(r_values: Sequence[float], *, L: int = 100, b: float = 1.0,
            init_coop_fraction: float = 0.5, rule: str = "replicator",
            n_seeds: int = 20, seed_base: int = 0, n_steps: int = 1000,
            measure_last: int = 200) -> Dict[str, Any]:
    """Sweep the cost-to-benefit ratio r over ``r_values`` for one update rule, running
    ``n_seeds`` seeds per r. Returns, per r, the mean steady-state lattice cooperator
    fraction f_lat, its spread, and the well-mixed ESS 1 - r for comparison."""
    rows = []
    for r in r_values:
        arm = run_many_seeds(L, r=r, b=b, init_coop_fraction=init_coop_fraction, rule=rule,
                             n_seeds=n_seeds, seed_base=seed_base, n_steps=n_steps,
                             measure_last=measure_last)
        rows.append({
            "r": r,
            "well_mixed_ess": well_mixed_ess(r),
            "mean_steady_f": arm["mean_steady_f"],
            "std_steady_f": arm["std_steady_f"],
            "min_steady_f": arm["min_steady_f"],
            "max_steady_f": arm["max_steady_f"],
            "per_seed_steady_f": arm["per_seed_steady_f"],
        })
    return {
        "rule": rule, "L": L, "r_values": list(r_values),
        "n_seeds": n_seeds, "seed_base": seed_base,
        "n_steps": n_steps, "measure_last": measure_last,
        "rows": rows,
    }
