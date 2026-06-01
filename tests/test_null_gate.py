"""Tests for NullGate — the refutation-tier Gate exemplar (ADR-013).

Verifies the parts that differ from the verification-tier AntiPatternGate:
the refutation semantics of "passed", the salient_number margin, and the
tier-honest "not refuted" rendering.
"""
from __future__ import annotations

import numpy as np

from abm_auto.analysis.critical_slowing_down import critical_slowing_down
from abm_auto.analysis.null_gate import NullGate
from abm_auto.verification.gate import Gate, Verdict


def _stat(s: np.ndarray) -> float:
    return critical_slowing_down(s).ews_strength


def _rising(n: int = 200, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    a = np.linspace(0.1, 0.95, n)
    for t in range(1, n):
        x[t] = a[t] * x[t - 1] + rng.normal(0, 0.1)
    return x


def test_gate_satisfies_protocol() -> None:
    g = NullGate(_stat)
    assert isinstance(g, Gate)
    assert g.name == "surrogate_null"
    assert g.family == "scalar_trajectory"
    assert g.tier == "refutation"


def test_rising_signal_refutes_null() -> None:
    """A real trend beats the null → noise hypothesis refuted → passed."""
    g = NullGate(_stat, null_kind="phase", seed=1)
    v = g.judge(_rising())
    assert isinstance(v, Verdict)
    assert v.passed is True
    assert v.tier == "refutation"
    p, alpha = v.salient_number
    assert p < alpha


def test_white_noise_does_not_refute_null() -> None:
    """White noise is consistent with its own null → not refuted → fail."""
    rng = np.random.default_rng(2)
    g = NullGate(_stat, null_kind="phase", seed=1)
    v = g.judge(rng.normal(0, 1, 200))
    assert v.passed is False
    p, alpha = v.salient_number
    assert p >= alpha
    assert v.reasons  # explains the non-refutation


def test_passed_renders_as_not_refuted_not_verified() -> None:
    """The anti-laundering point: a passed refutation Gate must NEVER
    render as 'verified'."""
    g = NullGate(_stat, null_kind="phase", seed=1)
    rendered = g.judge(_rising()).render()
    assert "not refuted" in rendered
    assert "verified" not in rendered


def test_salient_number_carries_margin() -> None:
    """Margin (p, alpha) is preserved, not collapsed to a bool — the
    Demo-1 lesson."""
    g = NullGate(_stat, null_kind="phase", seed=1)
    v = g.judge(_rising())
    assert v.salient_number is not None
    assert len(v.salient_number) == 2
    assert v.salient_number[1] == 0.05  # alpha


def test_self_test_passes() -> None:
    assert NullGate(_stat).self_test() is True


def test_deterministic_given_seed() -> None:
    """Same seed → same verdict (surrogate draws are reproducible)."""
    series = _rising()
    g1 = NullGate(_stat, seed=7)
    g2 = NullGate(_stat, seed=7)
    assert g1.judge(series).salient_number == g2.judge(series).salient_number
