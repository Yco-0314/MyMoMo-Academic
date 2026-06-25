"""Tests for abm_auto.analysis.statistics.cohens_d (analysis-6).

Pins the near-zero-variance guard: before the fix, an exact `pooled_std == 0`
check let a tiny-but-nonzero pooled std (float noise) through and the division
blew the effect size up into a spurious "large".
"""
from __future__ import annotations

import numpy as np

from abm_auto.analysis.statistics import cohens_d


def test_cohens_d_insufficient_data():
    assert cohens_d(np.array([1.0]), np.array([2.0, 3.0])) == (0.0, "insufficient_data")


def test_cohens_d_exact_zero_variance():
    out = cohens_d(np.array([5.0, 5.0, 5.0]), np.array([9.0, 9.0, 9.0]))
    assert out == (0.0, "zero_variance")


def test_cohens_d_negligible_variance_is_not_spurious_large():
    # Tiny-but-nonzero variance with a real mean gap. The exact-zero check used to
    # miss this and return a meaningless huge d labelled "large".
    a = np.array([5.0, 5.0, 5.0 + 1e-12])
    b = np.array([9.0, 9.0, 9.0])
    d, label = cohens_d(a, b)
    assert label == "zero_variance"
    assert d == 0.0


def test_cohens_d_normal_case():
    d, label = cohens_d(np.array([1.0, 2.0, 3.0, 4.0]), np.array([3.0, 4.0, 5.0, 6.0]))
    assert np.isfinite(d) and d > 0
    assert label in {"negligible", "small", "medium", "large"}
