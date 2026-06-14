"""Critical Slowing Down (CSD) — early-warning signals for ABM tipping points.

Method-transfer Demo 1. Ports the regime-shift early-warning
literature (Scheffer et al. 2009; Dakos et al. 2012) from ecology/climate
onto an ABM trajectory.

The physics: as a dynamical system approaches a critical transition, it
recovers more slowly from perturbations ("critical slowing down"). Two
observable fingerprints rise BEFORE the transition shows up in the order
parameter:

  - lag-1 autocorrelation (AR1) -> trends toward 1
  - variance -> trends upward

The early-warning *signal* is a positive trend (Kendall rank correlation
tau) in these indicators over a pre-transition window. CSD is purely a
function of a single trajectory column — no graph, no extra collection.
That makes it the cheapest possible method-transfer demo: it runs on the
trajectory DataCollector already emits.

This module is the ``compute()`` half. The null-model anti-spurious guard
(the method-transfer guard) lives in ``method_transfer_guard.py``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CSDResult:
    """Output of a CSD computation over one trajectory column."""
    window_centers: np.ndarray   # tick index at each rolling-window center
    ar1_series: np.ndarray       # rolling lag-1 autocorrelation
    variance_series: np.ndarray  # rolling variance
    ar1_tau: float               # Kendall tau of AR1 trend — the EWS
    variance_tau: float          # Kendall tau of variance trend — the EWS
    window: int                  # rolling window length used

    @property
    def ews_strength(self) -> float:
        """Combined early-warning strength: mean of the two trend taus.

        Range [-1, 1]; near +1 means both indicators rise strongly
        (classic pre-transition signature)."""
        return float((self.ar1_tau + self.variance_tau) / 2.0)


def _lag1_autocorr(x: np.ndarray) -> float:
    """Lag-1 autocorrelation of a 1-D window. Returns 0.0 for degenerate
    (constant or <2-point) windows rather than NaN, so downstream trend
    statistics stay finite."""
    if len(x) < 2:
        return 0.0
    x = x - x.mean()
    denom = float(np.dot(x, x))
    if denom == 0.0:
        return 0.0
    return float(np.dot(x[:-1], x[1:]) / denom)


def rolling_ar1(series: np.ndarray, window: int) -> np.ndarray:
    """Rolling lag-1 autocorrelation. One value per window position."""
    n = len(series)
    if n < window:
        return np.array([])
    return np.array([_lag1_autocorr(series[i:i + window]) for i in range(n - window + 1)])


def rolling_variance(series: np.ndarray, window: int) -> np.ndarray:
    """Rolling variance (population). One value per window position."""
    n = len(series)
    if n < window:
        return np.array([])
    return np.array([float(np.var(series[i:i + window])) for i in range(n - window + 1)])


def _kendall_tau(y: np.ndarray) -> float:
    """Kendall rank correlation of y against its own index (i.e. the
    monotone-trend strength of the series). 0.0 if degenerate."""
    if len(y) < 2:
        return 0.0
    from scipy.stats import kendalltau
    x = np.arange(len(y))
    tau, _p = kendalltau(x, y)
    return 0.0 if (tau is None or np.isnan(tau)) else float(tau)


def critical_slowing_down(
    series: np.ndarray,
    window: int | None = None,
    detrend: bool = True,
) -> CSDResult:
    """Compute CSD early-warning indicators over a trajectory column.

    Args:
        series: 1-D trajectory (e.g. opinion_variance over ticks).
        window: rolling-window length. Defaults to len//4 (>= 5), the
            usual EWS convention (enough points for AR1, short enough to
            track the approach to transition).
        detrend: subtract a rolling mean before computing indicators, so
            a slow drift in the level doesn't masquerade as rising
            variance. Standard in the EWS literature.

    Returns:
        CSDResult with the indicator series + their trend taus.
    """
    series = np.asarray(series, dtype=float)
    n = len(series)
    if window is None:
        window = max(5, n // 4)

    work = series.copy()
    if detrend and n >= window:
        # Subtract a centered rolling mean (Gaussian-ish via uniform here)
        # to isolate fluctuations from the slow level change.
        kernel = max(3, window // 2)
        pad = kernel // 2
        padded = np.pad(work, pad, mode="edge")
        smooth = np.convolve(padded, np.ones(kernel) / kernel, mode="same")[pad:pad + n]
        work = work - smooth

    ar1 = rolling_ar1(work, window)
    var = rolling_variance(work, window)
    centers = np.arange(len(ar1)) + window // 2

    return CSDResult(
        window_centers=centers,
        ar1_series=ar1,
        variance_series=var,
        ar1_tau=_kendall_tau(ar1),
        variance_tau=_kendall_tau(var),
        window=window,
    )
