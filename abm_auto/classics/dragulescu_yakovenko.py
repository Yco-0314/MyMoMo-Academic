"""Dragulescu-Yakovenko statistical mechanics of money (2000) — a faithful
agent-based reproduction.

Source: Dragulescu, A. & Yakovenko, V.M. (2000), "Statistical mechanics of
money", Eur. Phys. J. B 17:723-729. doi:10.1007/s100510070114.

The model is a *conserved kinetic exchange*. N agents each hold money m_i >= 0.
The total M = sum_i m_i is conserved for all time. Repeatedly a random ordered
pair (i, j) with i != j is drawn; the two pool their money s = m_i + m_j and a
fraction epsilon ~ U[0, 1) is redrawn:

    m_i <- epsilon * s
    m_j <- (1 - epsilon) * s

This is the FULL-REPARTITION (no-saving) rule: after the trade the whole pooled
amount is randomly reassigned between the pair, with NO saving propensity kept
back (the model has lambda = 0). A hard NO-DEBT boundary is enforced: no balance
may go below 0. Because epsilon in [0, 1) with s >= 0 already keeps both new
balances in [0, s], the no-debt boundary is never actually violated by the
full-repartition rule; the check is retained as a guard (and would reject any
transaction that tried to drive a balance < 0, e.g. under a different rule).

Starting from a DELTA initial condition (every agent has exactly M/N), the
stationary money distribution relaxes to the Boltzmann-Gibbs EXPONENTIAL

    P(m) ~ exp(-m / T),   with money-temperature  T = <m> = M / N,

the direct money analogue of the equilibrium energy distribution of an ideal
gas: random conservative exchange maximizes entropy at fixed total, and the
maximum-entropy distribution on m >= 0 at fixed mean is the exponential. The
exponential has Gini exactly 1/2 and coefficient of variation exactly 1.

WHAT WOULD BREAK IT (kept out on purpose): adding a saving propensity lambda > 0
(each agent keeps lambda of its money and only (1 - lambda) enters the pool)
turns the stationary distribution into a PEAKED Gamma distribution (mode > 0,
Gini < 1/2) — the Chakraborti-Chakrabarti signature. This module implements only
lambda = 0, so an interior peak (mode well away from 0) would be a genuine
falsification, not an expected outcome.

Distinctness: unlike Sugarscape (spatial harvesting, NON-conserved sugar, a
landscape-set Gini with no thermal signature) or Zero-Intelligence trading
(allocative efficiency, no wealth accumulation), here money is strictly
conserved and the emergent inequality is pinned by statistical mechanics to the
universal exponential fixed point (Gini = 1/2). That thermal/entropy signature
is unique to this model.

Built on the neutral platform (``abm_auto._platform``): each agent is a
``MoneyAgent`` holding its own balance; ``MoneyExchangeModel`` owns the conserved
money vector (a numpy array for speed — N=5000 x 5000 sweeps is fast), drives the
random-pair exchange over the ``AgentSet`` roster, and records (via a
``DataCollector``) the per-sweep Gini and coefficient of variation. One sweep =
N pairwise exchanges (so on average each agent trades ~twice per sweep, matching
the paper's "one transaction per pair" bookkeeping at the sweep scale). The
per-agent balances on the ``MoneyAgent`` objects are kept in sync with the money
vector so the agent roster is a faithful view of the same conserved state.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- inequality + distribution statistics -------------------------------------

def gini(values: Sequence[float]) -> float:
    """Gini coefficient of a non-negative money list (0 = equal, ->1 = unequal).

    Standard mean-absolute-difference form G = sum_i sum_j |x_i - x_j| /
    (2 n^2 mean), computed in O(n log n) via the sorted-cumulative identity.
    Empty or all-zero input -> 0.0. The exponential distribution has Gini = 1/2.
    """
    xs = np.sort(np.asarray(values, dtype=float))
    n = xs.size
    if n == 0:
        return 0.0
    total = float(xs.sum())
    if total <= 0.0:
        return 0.0
    # G = (2 * sum_i (i+1) x_i) / (n * sum x) - (n + 1) / n   (1-indexed)
    idx = np.arange(1, n + 1, dtype=float)
    cum = float(np.dot(idx, xs))
    return (2.0 * cum) / (n * total) - (n + 1.0) / n


def coefficient_of_variation(values: Sequence[float]) -> float:
    """CV = std(m) / mean(m). The exponential distribution has CV = 1 exactly
    (its std equals its mean). Population std (ddof=0). Empty / zero-mean -> 0.0."""
    xs = np.asarray(values, dtype=float)
    if xs.size == 0:
        return 0.0
    mean = float(xs.mean())
    if mean == 0.0:
        return 0.0
    return float(xs.std()) / mean


def histogram(values: Sequence[float], *, n_bins: int, m_max: float
              ) -> Tuple[np.ndarray, np.ndarray]:
    """Normalized density histogram P(m) of money over [0, m_max] in ``n_bins``
    equal bins. Returns (bin_centres, density). ``density`` integrates to ~1 over
    the covered range (values above m_max are dropped from the density, matching
    the paper's finite plotting window)."""
    xs = np.asarray(values, dtype=float)
    edges = np.linspace(0.0, m_max, n_bins + 1)
    counts, _ = np.histogram(xs, bins=edges)
    width = edges[1] - edges[0]
    density = counts / (xs.size * width)
    centres = 0.5 * (edges[:-1] + edges[1:])
    return centres, density


def mode_bin_centre(values: Sequence[float], *, n_bins: int, m_max: float) -> float:
    """Money value at the peak of the histogram P(m). For an exponential the peak
    is in the lowest bin (mode at m = 0)."""
    centres, density = histogram(values, n_bins=n_bins, m_max=m_max)
    return float(centres[int(np.argmax(density))])


def exponential_loglinear_fit(values: Sequence[float], *, mean_m: float,
                              lo_frac: float = 0.2, hi_frac: float = 3.0,
                              n_bins: int = 40) -> Dict[str, float]:
    """Log-linear OLS of ln P(m) vs m over the bulk window m in
    [lo_frac*<m>, hi_frac*<m>], the exponential-tail test.

    Returns the fitted decay rate ``beta`` (P ~ exp(-beta m), so the fitted
    temperature is 1/beta), the intercept, and the coefficient of determination
    ``r2``. Only non-empty (positive-density) bins in the window enter the fit.
    """
    lo = lo_frac * mean_m
    hi = hi_frac * mean_m
    # Histogram over a window a bit wider than the fit range for stable bins.
    centres, density = histogram(values, n_bins=n_bins, m_max=hi * 1.5)
    mask = (centres >= lo) & (centres <= hi) & (density > 0.0)
    x = centres[mask]
    p = density[mask]
    if x.size < 3:
        return {"beta": float("nan"), "temperature": float("nan"),
                "intercept": float("nan"), "r2": 0.0, "n_points": int(x.size)}
    y = np.log(p)
    # OLS slope/intercept of y = a + b x ; decay rate beta = -b.
    b, a = np.polyfit(x, y, 1)
    beta = -float(b)
    yhat = a + b * x
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 0.0
    temperature = 1.0 / beta if beta != 0.0 else float("inf")
    return {"beta": beta, "temperature": temperature, "intercept": float(a),
            "r2": r2, "n_points": int(x.size)}


def _aic(log_likelihood: float, k_params: int) -> float:
    """Akaike Information Criterion = 2k - 2 ln L (lower is better)."""
    return 2.0 * k_params - 2.0 * log_likelihood


def exp_vs_power_aic(values: Sequence[float], *, mean_m: float,
                     lo_frac: float = 0.2, hi_frac: float = 3.0
                     ) -> Dict[str, float]:
    """Compare an EXPONENTIAL vs a POWER-LAW fit to the money data over the bulk
    window [lo_frac*<m>, hi_frac*<m>] by AIC (lower AIC = better).

    Both are fit by maximum likelihood on the *individual* money values that fall
    in the window (not on binned densities), so the likelihoods are comparable:
      - exponential (1 free param, the rate): truncated-exponential MLE on
        [lo, hi];
      - power law m^{-alpha} (1 free param, alpha): truncated-Pareto MLE on
        [lo, hi].
    Returns both AICs and the exponential-minus-powerlaw margin (negative =>
    exponential preferred). The exponential should win for DY money.
    """
    xs = np.asarray(values, dtype=float)
    lo = lo_frac * mean_m
    hi = hi_frac * mean_m
    w = xs[(xs >= lo) & (xs <= hi)]
    n = w.size
    if n < 5:
        return {"aic_exp": float("nan"), "aic_powerlaw": float("nan"),
                "delta_exp_minus_pl": float("nan"), "n_points": int(n),
                "exp_preferred": False}

    # --- truncated exponential MLE on [lo, hi] ---
    # density f(m) = lam e^{-lam m} / (e^{-lam lo} - e^{-lam hi}); solve for lam
    # numerically by matching the mean of a truncated exponential to the sample.
    # Everything is written in terms of d = lam*(hi - lo) >= 0 after factoring out
    # the common e^{-lam lo}, so no e^{-lam*money} term underflows the denominator.
    sample_mean = float(w.mean())
    span = hi - lo

    def trunc_exp_mean(lam: float) -> float:
        # E[m] of a truncated exponential on [lo, hi]. As lam -> 0 the mean -> the
        # window midpoint; as lam -> inf it -> lo. Numerically stable via e^{-d}.
        if lam <= 1e-12:
            return 0.5 * (lo + hi)
        d = lam * span
        e = math.exp(-d)                 # in (0, 1], never underflows the denom to 0
        den = 1.0 - e                    # >= 0; ~ d for small d
        if den <= 1e-300:
            return lo                    # lam huge: all mass piles at lo
        # E[m] = lo + (1/lam) - span*e/(1 - e)
        return lo + (1.0 / lam) - span * e / den

    # bisection on lam so that trunc_exp_mean(lam) == sample_mean (mean is
    # monotone decreasing in lam over (lo, hi)).
    lam_lo, lam_hi = 1e-9, 1e4
    lam = 1.0 / max(sample_mean, 1e-9)
    for _ in range(300):
        mid = 0.5 * (lam_lo + lam_hi)
        if trunc_exp_mean(mid) > sample_mean:
            lam_lo = mid
        else:
            lam_hi = mid
        lam = mid
    # log-likelihood of the truncated exponential (stable normalizer):
    #   f(m) = lam e^{-lam(m - lo)} / (1 - e^{-lam span})
    #   log f(m) = log(lam) - lam(m - lo) - log(1 - e^{-lam span})
    d = lam * span
    log_norm = math.log1p(-math.exp(-d)) if d > 0 else float("-inf")
    if not math.isfinite(log_norm):
        ll_exp = float("-inf")
    else:
        ll_exp = float(np.sum(math.log(lam) - lam * (w - lo) - log_norm))
    aic_exp = _aic(ll_exp, 1)

    # --- truncated power-law (Pareto on [lo, hi]) MLE ---
    # f(m) = (alpha - 1) / (lo^{1-alpha} - hi^{1-alpha}) * m^{-alpha}? Use the
    # standard truncated-Pareto MLE via the log-mean; solve alpha by matching.
    logs = np.log(w)
    mean_log = float(logs.mean())

    def trunc_pareto_neg_ll(alpha: float) -> float:
        # log density: log(alpha-1) - log(lo^{1-alpha} - hi^{1-alpha}) ... guard.
        if alpha <= 1.0 + 1e-9:
            alpha = 1.0 + 1e-9
        # normalization C so that integral_lo^hi C m^{-alpha} dm = 1.
        if abs(alpha - 1.0) < 1e-9:
            Z = math.log(hi) - math.log(lo)
        else:
            Z = (hi ** (1.0 - alpha) - lo ** (1.0 - alpha)) / (1.0 - alpha)
        if Z <= 0.0:
            return float("inf")
        logC = -math.log(Z)
        ll = n * logC - alpha * n * mean_log
        return -ll

    # 1-D minimize over alpha by a coarse-then-fine scan (deterministic).
    best_alpha, best_nll = 2.0, float("inf")
    for alpha in np.linspace(0.5, 6.0, 111):
        nll = trunc_pareto_neg_ll(float(alpha))
        if nll < best_nll:
            best_nll, best_alpha = nll, float(alpha)
    lo_a, hi_a = max(0.5, best_alpha - 0.1), best_alpha + 0.1
    for alpha in np.linspace(lo_a, hi_a, 201):
        nll = trunc_pareto_neg_ll(float(alpha))
        if nll < best_nll:
            best_nll, best_alpha = nll, float(alpha)
    ll_pl = -best_nll
    aic_pl = _aic(ll_pl, 1)

    delta = aic_exp - aic_pl
    return {"aic_exp": aic_exp, "aic_powerlaw": aic_pl,
            "delta_exp_minus_pl": delta, "n_points": int(n),
            "alpha_powerlaw": best_alpha, "lambda_exp": lam,
            "exp_preferred": bool(aic_exp < aic_pl)}


# -- Agent --------------------------------------------------------------------

class MoneyAgent(Agent):
    """One economic agent holding a non-negative money balance.

    The DY exchange is a model-level random-pair update (pick two agents, pool +
    redraw), not an autonomous single-agent step, so the per-agent ``step`` is a
    no-op. The ``balance`` mirrors the model's conserved money vector at ``index``
    and is refreshed by the model after each sweep so the agent roster is a
    faithful view of the same conserved state."""

    def __init__(self, agent_id: int, model: "MoneyExchangeModel", *,
                 balance: float) -> None:
        super().__init__(agent_id, model)
        self.index = agent_id
        self.balance = float(balance)

    def step(self) -> None:  # pragma: no cover - the exchange lives on the model
        """The DY pairwise exchange is a model-level update, not an autonomous
        single-agent step, so this is a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class MoneyExchangeModel(AgentModel):
    """Drives the Dragulescu-Yakovenko conserved kinetic-exchange dynamics.

    Construct with N agents, mean money ``mean_money`` = <m> = M/N (delta start:
    every agent begins with exactly <m>), and a seed. ``run(n_sweeps,
    burn_in_frac)`` advances ``n_sweeps`` sweeps (each = N random-pair full-
    repartition exchanges with the no-debt guard), records the per-sweep Gini and
    CV, and returns the run summary including the time-averaged post-burn-in money
    sample (pooled across the recorded post-burn-in sweeps) used to estimate the
    stationary P(m).

    NO saving propensity (lambda = 0): the whole pooled amount is redistributed.
    """

    def __init__(self, n: int = 5000, *, mean_money: float = 100.0,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n < 2:
            raise ValueError(f"need n >= 2 agents (got {n})")
        if mean_money <= 0.0:
            raise ValueError(f"need mean_money > 0 (got {mean_money})")
        self.seed_value = seed
        self.n = n
        self.mean_money = float(mean_money)
        self.total_money = self.mean_money * n     # conserved M

        # numpy RNG for the fast inner loop (seeded, deterministic).
        self._np_rng = np.random.default_rng(seed)

        # DELTA initial condition: every agent starts with exactly <m> = M/N.
        self.money = np.full(n, self.mean_money, dtype=float)
        self.initial_total = float(self.money.sum())

        # Genuine agent roster (a faithful view of the conserved money vector).
        self.agent_list: List[MoneyAgent] = []
        for i in range(n):
            agent = MoneyAgent(i, self, balance=self.money[i])
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({
            "gini": lambda m: gini(m.money),
            "cv": lambda m: coefficient_of_variation(m.money),
            "min_money": lambda m: float(m.money.min()),
            "total_money": lambda m: float(m.money.sum()),
        })

    # -- one sweep of pairwise exchanges --
    def _sweep(self) -> None:
        """One sweep = N random-pair full-repartition exchanges with a no-debt
        guard. Each exchange: pick a random ordered pair (i != j), pool
        s = m_i + m_j, draw epsilon ~ U[0,1), set m_i = eps*s, m_j = (1-eps)*s.
        The no-debt guard rejects any transaction that would drive a balance < 0
        (never triggered by full-repartition since eps in [0,1) keeps both new
        balances in [0, s], but retained as a faithful boundary)."""
        m = self.money
        n = self.n
        rng = self._np_rng
        i_arr = rng.integers(0, n, size=n)
        j_arr = rng.integers(0, n, size=n)
        eps_arr = rng.random(size=n)
        for k in range(n):
            i = int(i_arr[k])
            j = int(j_arr[k])
            if i == j:
                continue
            s = m[i] + m[j]
            eps = eps_arr[k]
            new_i = eps * s
            new_j = s - new_i
            # NO-DEBT guard: reject any transaction driving a balance < 0.
            if new_i < 0.0 or new_j < 0.0:
                continue
            m[i] = new_i
            m[j] = new_j

    def _sync_agents(self) -> None:
        """Refresh the per-agent balances from the conserved money vector so the
        MoneyAgent roster stays a faithful view of the same state."""
        for a in self.agent_list:
            a.balance = float(self.money[a.index])

    # -- tick --
    def step(self) -> None:
        """One sweep of the DY exchange, then sync the agent roster + collect the
        per-sweep Gini and CV."""
        self._sweep()
        self._sync_agents()
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_sweeps: int = 5000, *, burn_in_frac: float = 0.5,
            sample_every: int = 1) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_sweeps`` sweeps; discard the first ``burn_in_frac`` fraction as
        burn-in; time-average the stationary statistics + pool the post-burn-in
        money snapshots (one every ``sample_every`` sweeps) into a single money
        sample used to estimate P(m).

        Returns the config, the conservation diagnostics, the stationary Gini/CV
        (mean over post-burn-in sweeps), the full per-sweep Gini/CV series, and
        the pooled post-burn-in money sample (a flat numpy array, returned as a
        list for JSON-friendliness by the caller if needed)."""
        if not (0.0 <= burn_in_frac < 1.0):
            raise ValueError(f"burn_in_frac must be in [0, 1) (got {burn_in_frac})")
        if sample_every < 1:
            raise ValueError(f"sample_every must be >= 1 (got {sample_every})")

        self.reporter.collect(self)                 # t=0 baseline (delta start)
        burn_in = int(round(burn_in_frac * n_sweeps))
        pooled: List[np.ndarray] = []
        for sweep in range(1, n_sweeps + 1):
            self.step()
            if sweep > burn_in and (sweep - burn_in - 1) % sample_every == 0:
                pooled.append(self.money.copy())

        gini_series = self.reporter.series("gini")
        cv_series = self.reporter.series("cv")
        min_series = self.reporter.series("min_money")
        total_series = self.reporter.series("total_money")

        # stationary means over the post-burn-in window (sweeps burn_in+1 .. end).
        # series index 0 == t=0 baseline, so post-burn-in slice starts at burn_in+1.
        post = slice(burn_in + 1, None)
        gini_post = gini_series[post]
        cv_post = cv_series[post]
        stationary_gini = float(np.mean(gini_post)) if gini_post else 0.0
        stationary_cv = float(np.mean(cv_post)) if cv_post else 0.0

        if pooled:
            money_sample = np.concatenate(pooled)
        else:
            money_sample = self.money.copy()

        # conservation diagnostics over the WHOLE run.
        max_rel_dM = max(
            abs(tot - self.initial_total) / self.initial_total for tot in total_series
        ) if self.initial_total > 0 else 0.0
        min_ever = min(min_series)

        return {
            "n": self.n,
            "mean_money": self.mean_money,
            "total_money": self.total_money,
            "seed": self.seed_value,
            "n_sweeps": n_sweeps,
            "burn_in_frac": burn_in_frac,
            "burn_in_sweeps": burn_in,
            "sample_every": sample_every,
            "stationary_gini": stationary_gini,
            "stationary_cv": stationary_cv,
            "final_gini": gini_series[-1],
            "final_cv": cv_series[-1],
            "max_rel_dM": max_rel_dM,
            "min_money_ever": min_ever,
            "gini_series": gini_series,
            "cv_series": cv_series,
            "money_sample": money_sample,     # pooled post-burn-in balances
        }


# -- multi-seed helpers -------------------------------------------------------

def run_single(n: int = 5000, *, mean_money: float = 100.0, seed: int = 0,
               n_sweeps: int = 5000, burn_in_frac: float = 0.5,
               sample_every: int = 50) -> Dict[str, Any]:
    """One full DY run for a given seed (default: sample the money vector every
    50 post-burn-in sweeps to pool a large stationary sample without keeping every
    sweep)."""
    return MoneyExchangeModel(n, mean_money=mean_money, seed=seed).run(
        n_sweeps, burn_in_frac=burn_in_frac, sample_every=sample_every)


def run_many_seeds(n: int = 5000, *, mean_money: float = 100.0,
                   n_seeds: int = 20, seed_base: int = 0, n_sweeps: int = 5000,
                   burn_in_frac: float = 0.5, sample_every: int = 50
                   ) -> Dict[str, Any]:
    """Run ``n_seeds`` DY simulations (seed ``seed_base + i``) at fixed parameters
    and seed-average the stationary distribution + inequality statistics.

    Pools every run's post-burn-in money sample into one big seed+time-averaged
    money sample, then computes the seed-averaged stationary Gini and CV plus the
    exponential-shape diagnostics (log-linear fit R^2 and slope, mode bin, and the
    exponential-vs-power-law AIC) on the pooled sample — the headline numbers the
    locked clauses P1-P3 are graded against.
    """
    per_seed: List[Dict[str, Any]] = []
    pooled_money: List[np.ndarray] = []
    for i in range(n_seeds):
        res = run_single(n, mean_money=mean_money, seed=seed_base + i,
                         n_sweeps=n_sweeps, burn_in_frac=burn_in_frac,
                         sample_every=sample_every)
        per_seed.append(res)
        pooled_money.append(res["money_sample"])

    all_money = np.concatenate(pooled_money)

    per_seed_gini = [r["stationary_gini"] for r in per_seed]
    per_seed_cv = [r["stationary_cv"] for r in per_seed]
    mean_gini = float(np.mean(per_seed_gini))
    mean_cv = float(np.mean(per_seed_cv))

    # exponential-shape diagnostics on the pooled seed+time sample.
    fit = exponential_loglinear_fit(all_money, mean_m=mean_money)
    aic = exp_vs_power_aic(all_money, mean_m=mean_money)
    mode_m = mode_bin_centre(all_money, n_bins=40, m_max=6.0 * mean_money)
    centres, density = histogram(all_money, n_bins=40, m_max=6.0 * mean_money)

    # conservation diagnostics (worst over seeds).
    max_rel_dM = max(r["max_rel_dM"] for r in per_seed)
    min_money_ever = min(r["min_money_ever"] for r in per_seed)

    return {
        "n": n, "mean_money": mean_money, "n_seeds": n_seeds,
        "seed_base": seed_base, "n_sweeps": n_sweeps,
        "burn_in_frac": burn_in_frac, "sample_every": sample_every,
        "per_seed_stationary_gini": per_seed_gini,
        "per_seed_stationary_cv": per_seed_cv,
        "mean_stationary_gini": mean_gini,
        "std_stationary_gini": float(np.std(per_seed_gini)),
        "min_stationary_gini": float(np.min(per_seed_gini)),
        "max_stationary_gini": float(np.max(per_seed_gini)),
        "mean_stationary_cv": mean_cv,
        "std_stationary_cv": float(np.std(per_seed_cv)),
        # exponential-shape diagnostics on the pooled sample.
        "fit_r2": fit["r2"],
        "fit_beta": fit["beta"],
        "fit_temperature": fit["temperature"],
        "fit_n_points": fit["n_points"],
        "aic_exp": aic["aic_exp"],
        "aic_powerlaw": aic["aic_powerlaw"],
        "aic_delta_exp_minus_pl": aic["delta_exp_minus_pl"],
        "aic_exp_preferred": aic["exp_preferred"],
        "powerlaw_alpha": aic.get("alpha_powerlaw", float("nan")),
        "mode_money": mode_m,
        "mode_frac_of_mean": mode_m / mean_money if mean_money else float("nan"),
        # conservation.
        "max_rel_dM": max_rel_dM,
        "min_money_ever": min_money_ever,
        # a representative histogram + one gini/cv trajectory for plotting.
        "hist_centres": centres.tolist(),
        "hist_density": density.tolist(),
        "pooled_sample_size": int(all_money.size),
        "example_gini_series": per_seed[0]["gini_series"],
        "example_cv_series": per_seed[0]["cv_series"],
    }
