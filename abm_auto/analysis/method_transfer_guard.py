"""Anti-spurious guard for method transfer — the ADR-012 moat.

Applying a method from another field to an ABM trajectory is cheap. The
hard, defensible part is proving the resulting signal is REAL and not an
artifact of the trajectory's trivial structure. That proof is what no
competitor bolting a method onto Mesa output bothers to build.

The guard here: a **surrogate null model**. Take the same trajectory,
destroy the temporal structure the method claims to detect (while
preserving cheap-to-fake marginals), recompute the statistic many times,
and ask whether the real value beats that null distribution.

For Critical Slowing Down the relevant structure is temporal ordering /
autocorrelation. Two surrogate nulls:

  - "shuffle": permute the series in time. Destroys ALL temporal order
    (including any genuine ramp), keeps the value distribution. A real
    pre-transition CSD ramp should beat this easily.
  - "phase": phase-randomized (Fourier) surrogate — keeps the power
    spectrum / linear autocorrelation but randomizes phase, destroying
    the directional *trend* in autocorrelation. The stricter null: a CSD
    signal that beats phase surrogates is not explainable by stationary
    linear autocorrelation alone.

A finding that does not beat its null is reported as "no signal above
null" — not hidden. Reporting non-findings is what separates this from
p-hacking.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class GuardResult:
    """Outcome of testing a statistic against its surrogate null."""
    observed: float          # statistic on the real series
    null_mean: float         # mean of the statistic over surrogates
    null_std: float          # std over surrogates
    p_value: float           # P(null >= observed), one-sided upper tail
    n_surrogates: int
    null_kind: str           # "shuffle" | "phase"

    @property
    def significant(self) -> bool:
        """Beats null at the conventional 0.05 one-sided threshold."""
        return self.p_value < 0.05

    @property
    def z_score(self) -> float:
        if self.null_std == 0.0:
            return 0.0
        return float((self.observed - self.null_mean) / self.null_std)


def _shuffle_surrogate(series: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = series.copy()
    rng.shuffle(out)
    return out


def _phase_surrogate(series: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Fourier phase-randomized surrogate: preserves power spectrum (hence
    linear autocorrelation), randomizes phases. Standard IAAFT-lite."""
    n = len(series)
    fft = np.fft.rfft(series - series.mean())
    mag = np.abs(fft)
    phases = rng.uniform(0, 2 * np.pi, len(fft))
    phases[0] = 0.0  # keep DC real
    if n % 2 == 0:
        phases[-1] = 0.0  # Nyquist real for even n
    surrogate = np.fft.irfft(mag * np.exp(1j * phases), n=n)
    return surrogate + series.mean()


def test_against_null(
    series: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    *,
    n_surrogates: int = 200,
    null_kind: str = "shuffle",
    seed: int = 0,
) -> GuardResult:
    """Test whether ``statistic(series)`` beats a surrogate null.

    Args:
        series: the real trajectory column.
        statistic: maps a series to a scalar (e.g. CSD ews_strength).
            Must accept any same-length array (real or surrogate).
        n_surrogates: number of null draws (200 gives p-resolution 0.005).
        null_kind: "shuffle" (destroy all order) or "phase" (keep
            spectrum, destroy trend). Phase is the stricter test.
        seed: RNG seed for reproducible nulls.

    Returns:
        GuardResult with observed value, null distribution summary, and a
        one-sided upper-tail p-value (fraction of surrogates >= observed).
    """
    series = np.asarray(series, dtype=float)
    rng = np.random.default_rng(seed)
    observed = float(statistic(series))

    if null_kind == "shuffle":
        gen = _shuffle_surrogate
    elif null_kind == "phase":
        gen = _phase_surrogate
    else:
        raise ValueError(f"null_kind must be 'shuffle' or 'phase', got {null_kind!r}")

    null_vals = np.array([float(statistic(gen(series, rng))) for _ in range(n_surrogates)])
    # One-sided upper tail with +1 correction (never report p=0).
    p = float((np.sum(null_vals >= observed) + 1) / (n_surrogates + 1))

    return GuardResult(
        observed=observed,
        null_mean=float(null_vals.mean()),
        null_std=float(null_vals.std()),
        p_value=p,
        n_surrogates=n_surrogates,
        null_kind=null_kind,
    )
