"""Kuramoto synchronization (Kuramoto 1975) — a faithful agent-based reproduction.

Source: Kuramoto, Y. (1975), "Self-entrainment of a population of coupled non-linear
oscillators", in: International Symposium on Mathematical Problems in Theoretical
Physics, Lecture Notes in Physics 39, Springer, pp. 420-422.
doi:10.1007/BFb0013365. (See also Strogatz, Physica D 143 (2000) 1-20 for the
mean-field review.)

Rules (the canonical mean-field / all-to-all Kuramoto model):
  * N ``OscillatorAgent``s. Each carries a phase ``theta`` (radians) and a FIXED natural
    frequency ``omega`` drawn once at construction from N(0, 1) (seeded). Initial phases are
    uniform in [0, 2*pi) (seeded).
  * All-to-all coupling of strength K. Euler step dt:
        theta_i(t+dt) = theta_i(t) + ( omega_i + (K/N) * sum_j sin(theta_j - theta_i) ) * dt
    Every phase is advanced SYNCHRONOUSLY from the start-of-tick snapshot (the coupling
    sum reads the phases at the start of the tick, then all phases commit). The update is
    order-independent, hence deterministic given the seeded omega/theta draws.

Order parameter (the locked grading metric):
    r * e^{i*psi} = (1/N) * sum_j e^{i*theta_j}   ->   r = | (1/N) sum_j e^{i theta_j} |  in [0, 1].
r ~ 0 is an incoherent (desynchronized) population; r ~ 1 is a phase-locked (synchronized)
population. Kuramoto's result: a coupling-driven synchronization transition — r stays near
0 below a critical coupling K_c and rises toward 1 above it. For omega ~ N(0,1) the
mean-field critical coupling is K_c = 2 / (pi * g(0)) = 2 / (pi / sqrt(2*pi)) = 2*sqrt(2/pi)
~ 1.596 (g is the natural-frequency density, g(0) = 1/sqrt(2*pi)). r is measured as the
mean over the TAIL of the run (after the transient).

Built on the neutral platform (``abm_auto._platform``): each oscillator is an
``OscillatorAgent`` carrying its own (theta, omega); ``KuramotoModel`` drives the
synchronous Euler update over the ``AgentSet`` roster and records (via a ``DataCollector``)
the per-tick order parameter r. The coupling sum is computed in O(N) per tick using the
mean-field identity sum_j sin(theta_j - theta_i) = Im( e^{-i theta_i} * sum_j e^{i theta_j} )
= R * sin(psi - theta_i) where R*e^{i psi} = sum_j e^{i theta_j}; this is algebraically
identical to the brute-force O(N^2) all-pairs sum, only faster (verified in tests).
"""
from __future__ import annotations

import cmath
import math
from typing import Any, Dict, List, Sequence

from abm_auto._platform import Agent, AgentModel, DataCollector


# -- Agent --------------------------------------------------------------------

class OscillatorAgent(Agent):
    """One phase oscillator: phase ``theta`` (radians) and FIXED natural frequency
    ``omega``.

    The Kuramoto update is a model-level synchronous tick (all new phases from one
    snapshot, then all commit), so the per-agent ``step`` is intentionally a no-op; the
    ``_next_theta`` field stages the phase computed this tick before the model commits.
    """

    def __init__(self, agent_id: int, model: "KuramotoModel", *,
                 theta: float, omega: float) -> None:
        super().__init__(agent_id, model)
        self.theta = theta
        self.omega = omega
        self._next_theta = theta

    def step(self) -> None:  # pragma: no cover - the tick lives on the model
        """The Kuramoto tick (advance every phase from a snapshot) is a model-level
        synchronous update, not an autonomous single-agent step, so this is a no-op."""
        return None


# -- Model --------------------------------------------------------------------

class KuramotoModel(AgentModel):
    """Drives the mean-field (all-to-all) Kuramoto phase-oscillator dynamics.

    Construct with N, coupling K, Euler step dt, and a seed (the seed fixes both the
    natural-frequency draw and the initial phases). ``run(n_steps, measure_last=...)``
    advances the synchronous Euler update and records the per-tick order parameter r;
    ``order_parameter`` reads the current r.
    """

    def __init__(self, n: int = 500, *, K: float = 1.0, dt: float = 0.05,
                 seed: int = 0) -> None:
        super().__init__(seed=seed, schedule="sequential")
        if n <= 0:
            raise ValueError(f"need n > 0 (got {n})")
        if dt <= 0:
            raise ValueError(f"need dt > 0 (got {dt})")
        if K < 0:
            raise ValueError(f"need K >= 0 (got {K})")
        self.seed_value = seed
        self.n = n
        self.K = float(K)
        self.dt = float(dt)

        # Seed-dependent initial state. The omega draw and the theta draw are the only
        # randomness; everything after is deterministic. omega_i ~ N(0,1) (the natural
        # frequencies are FIXED for the whole run); theta_i ~ U[0, 2*pi).
        self.agent_list: List[OscillatorAgent] = []
        for i in range(n):
            omega = self.rng.gauss(0.0, 1.0)
            theta = self.rng.uniform(0.0, 2.0 * math.pi)
            agent = OscillatorAgent(i, self, theta=theta, omega=omega)
            self.agent_list.append(agent)
            self.add_agent(agent)

        self.reporter = DataCollector({"r": lambda m: m.order_parameter()})

    # -- metrics --
    def _mean_field(self) -> complex:
        """The complex order parameter R * e^{i psi} = (1/N) sum_j e^{i theta_j}."""
        if self.n == 0:
            return 0j
        acc = 0j
        for a in self.agent_list:
            acc += cmath.exp(1j * a.theta)
        return acc / self.n

    def order_parameter(self) -> float:
        """r = | (1/N) sum_j e^{i theta_j} |, the phase coherence, in [0, 1]."""
        return abs(self._mean_field())

    # -- coupling reference (O(N^2), used to validate the mean-field path in tests) --
    def _coupling_bruteforce(self, a: OscillatorAgent) -> float:
        """sum_j sin(theta_j - theta_i), the raw all-pairs coupling term for agent ``a``.
        O(N) per agent / O(N^2) per tick; the model uses the algebraically-identical
        mean-field identity instead."""
        ti = a.theta
        return math.fsum(math.sin(b.theta - ti) for b in self.agent_list)

    # -- tick --
    def step(self) -> None:
        """One synchronous Euler tick.

        From the start-of-tick snapshot compute the complex mean field z = R e^{i psi} =
        sum_j e^{i theta_j} ONCE; then for every oscillator the coupling sum is
            sum_j sin(theta_j - theta_i) = Im( e^{-i theta_i} * z ) = R * sin(psi - theta_i),
        which is exactly the brute-force all-pairs sum. Each new phase is staged in
        ``_next_theta`` (so the whole tick reads one consistent snapshot) and then all
        phases commit (synchronous update)."""
        # z = sum_j e^{i theta_j}  (un-normalised mean field; the (K/N) prefactor carries
        # the 1/N, so we keep the bare sum here).
        z = 0j
        for a in self.agent_list:
            z += cmath.exp(1j * a.theta)
        k_over_n = self.K / self.n
        for a in self.agent_list:
            coupling = (cmath.exp(-1j * a.theta) * z).imag   # = sum_j sin(theta_j - theta_i)
            a._next_theta = a.theta + (a.omega + k_over_n * coupling) * self.dt
        for a in self.agent_list:
            a.theta = a._next_theta
        self.t += 1
        if self.reporter is not None:
            self.reporter.collect(self)

    def run(self, n_steps: int = 2000, *, measure_last: int = 1000) -> Dict[str, Any]:  # type: ignore[override]
        """Run ``n_steps`` synchronous Euler ticks; return the run summary.

        ``measure_last`` is the trailing window over which the steady-state order
        parameter r is averaged (the transient is the leading n_steps - measure_last
        ticks). Returns the steady r, the final r, and the full per-tick r series.
        """
        if measure_last <= 0 or measure_last > n_steps + 1:
            raise ValueError(
                f"measure_last must be in [1, n_steps+1] (got {measure_last}, n_steps={n_steps})")
        self.reporter.collect(self)              # t=0 baseline
        for _ in range(n_steps):
            self.step()
        series = self.reporter.series("r")
        steady = steady_r(series, window=measure_last)
        return {
            "n": self.n,
            "K": self.K,
            "dt": self.dt,
            "seed": self.seed_value,
            "n_steps": n_steps,
            "measure_last": measure_last,
            "steady_r": steady,
            "final_r": series[-1],
            "r_series": series,
        }


# -- summary helpers ----------------------------------------------------------

def steady_r(series: Sequence[float], *, window: int = 1000) -> float:
    """Steady-state order parameter = mean of the trailing ``window`` of the r series
    (or the whole series if shorter). Averaging the tail smooths the finite-N jitter and
    discards the transient before measurement."""
    if not series:
        return 0.0
    tail = series[-window:] if len(series) >= window else list(series)
    return sum(tail) / len(tail)


def critical_coupling_normal(sigma: float = 1.0) -> float:
    """Mean-field critical coupling for a normal frequency distribution N(0, sigma^2):
    K_c = 2 / (pi * g(0)) with g(0) = 1 / (sigma * sqrt(2*pi)), i.e. K_c =
    2 * sigma * sqrt(2/pi). For sigma = 1 this is ~1.596."""
    return 2.0 * sigma * math.sqrt(2.0 / math.pi)


def run_single(n: int = 500, *, K: float = 1.0, dt: float = 0.05, seed: int = 0,
               n_steps: int = 2000, measure_last: int = 1000) -> Dict[str, Any]:
    """One Kuramoto run at a given (K, seed)."""
    return KuramotoModel(n, K=K, dt=dt, seed=seed).run(n_steps, measure_last=measure_last)


def run_many_seeds(n: int = 500, *, K: float = 1.0, dt: float = 0.05, n_seeds: int = 5,
                   seed_base: int = 0, n_steps: int = 2000,
                   measure_last: int = 1000) -> Dict[str, Any]:
    """Run ``n_seeds`` Kuramoto runs (seed ``seed_base + i``) at fixed parameters and
    summarise the steady order parameter r across seeds (mean + spread).

    Returns the per-seed steady r values, their mean / std / min / max, and one
    representative r trajectory (first seed) for plotting/inspection.
    """
    runs = [run_single(n, K=K, dt=dt, seed=seed_base + i,
                       n_steps=n_steps, measure_last=measure_last)
            for i in range(n_seeds)]
    per_seed_steady = [rr["steady_r"] for rr in runs]
    per_seed_final = [rr["final_r"] for rr in runs]
    mean_steady = sum(per_seed_steady) / n_seeds
    var_steady = sum((s - mean_steady) ** 2 for s in per_seed_steady) / n_seeds
    return {
        "n": n,
        "K": K,
        "dt": dt,
        "n_seeds": n_seeds,
        "seed_base": seed_base,
        "n_steps": n_steps,
        "measure_last": measure_last,
        "per_seed_steady": per_seed_steady,
        "per_seed_final": per_seed_final,
        "mean_steady_r": mean_steady,
        "var_steady_r": var_steady,
        "std_steady_r": var_steady ** 0.5,
        "min_steady_r": min(per_seed_steady),
        "max_steady_r": max(per_seed_steady),
        # one representative trajectory (first seed) for plotting/inspection.
        "example_series": runs[0]["r_series"],
    }
