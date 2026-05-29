"""Unit tests for abm_auto.calibration.identifiability — NM-restart basin detection."""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.calibration.identifiability import (
    Basin,
    IdentifiabilityReport,
    _single_link_cluster,
    identify_basins,
)


# ── Cluster algorithm ───────────────────────────────────────────────────


def _basin(p: dict, obj: float = 1.0, idx: int = 0) -> Basin:
    return Basin(params=p, objective=obj, restart_idx=idx)


def test_clusters_close_basins_into_one() -> None:
    priors = {"x": {"min": 0, "max": 10}, "y": {"min": 0, "max": 10}}
    # Three basins all within 5% of each other → one cluster
    basins = [
        _basin({"x": 1.0, "y": 1.0}),
        _basin({"x": 1.2, "y": 1.1}),
        _basin({"x": 1.4, "y": 0.9}),
    ]
    clusters = _single_link_cluster(basins, priors, rel_threshold=0.15)
    assert len(set(clusters)) == 1


def test_clusters_distant_basins_into_separate() -> None:
    priors = {"x": {"min": 0, "max": 10}, "y": {"min": 0, "max": 10}}
    # Two clearly-separated basins
    basins = [
        _basin({"x": 1.0, "y": 1.0}),
        _basin({"x": 9.0, "y": 9.0}),
    ]
    clusters = _single_link_cluster(basins, priors, rel_threshold=0.15)
    assert len(set(clusters)) == 2


def test_single_link_chains_through_intermediate() -> None:
    """A — B — C where A-B close, B-C close, but A-C far → all one cluster."""
    priors = {"x": {"min": 0, "max": 10}}
    basins = [
        _basin({"x": 1.0}),
        _basin({"x": 2.0}),
        _basin({"x": 3.0}),
    ]
    # threshold = 0.15 of range 10 = 1.5; pairwise distance 1.0 < 1.5
    # so all three single-link into one
    clusters = _single_link_cluster(basins, priors, rel_threshold=0.15)
    assert len(set(clusters)) == 1


def test_threshold_strictness() -> None:
    priors = {"x": {"min": 0, "max": 10}}
    basins = [_basin({"x": 0.0}), _basin({"x": 2.0})]
    # rel 0.15 * range 10 = threshold 1.5; distance 2.0 ≥ 1.5 → separate
    assert len(set(_single_link_cluster(basins, priors, 0.15))) == 2
    # rel 0.25 * range 10 = threshold 2.5; distance 2.0 < 2.5 → merge
    assert len(set(_single_link_cluster(basins, priors, 0.25))) == 1


# ── identify_basins end-to-end with synthetic simulator ─────────────────


class _BimodalSim:
    """Synthetic simulator with two clear basins.

    Returns sim_stats that minimise either at x≈1 or at x≈9 — whichever
    is closer. NM should land near one of them depending on start.
    """

    def __init__(self):
        self.calls = 0

    def simulate(self, params, targets):
        self.calls += 1
        x = params["x"]
        # Distance to nearer of two basins
        d1 = abs(x - 1.0)
        d2 = abs(x - 9.0)
        d = min(d1, d2)
        # Stats vector: just a single scalar so L2 norm == |d|
        return np.array([d], dtype=float)


def test_identify_basins_detects_multimodality_in_synthetic() -> None:
    sim = _BimodalSim()
    priors = {"x": {"min": 0, "max": 10}}
    obs = np.array([0.0], dtype=float)  # both basins minimise to 0
    report = identify_basins(
        sim, priors, targets=["dummy"], obs_stats=obs,
        n_restarts=10,
        evals_per_restart=30,
        cluster_rel_threshold=0.15,
        rng=np.random.default_rng(42),
    )
    # Should find both basins
    assert report.n_basins == 2
    assert report.is_multimodal
    assert "MULTIMODAL" in report.warning


def test_identify_basins_unimodal_when_basin_is_singular() -> None:
    """Single basin → all restarts converge to it → 1 cluster, no warning."""

    class _Unimodal:
        def simulate(self, params, _targets):
            return np.array([abs(params["x"] - 5.0)], dtype=float)

    priors = {"x": {"min": 0, "max": 10}}
    obs = np.array([0.0], dtype=float)
    report = identify_basins(
        _Unimodal(), priors, targets=["dummy"], obs_stats=obs,
        n_restarts=5,
        evals_per_restart=30,
        rng=np.random.default_rng(7),
    )
    assert report.n_basins == 1
    assert not report.is_multimodal
    assert report.warning == ""


def test_identify_basins_handles_failed_restarts() -> None:
    """When the simulator returns None for some calls, those restarts are dropped."""

    class _FlakySim:
        def __init__(self):
            self.n = 0
        def simulate(self, params, _targets):
            self.n += 1
            if self.n % 3 == 0:
                return None
            return np.array([abs(params["x"] - 5.0)], dtype=float)

    priors = {"x": {"min": 0, "max": 10}}
    obs = np.array([0.0], dtype=float)
    report = identify_basins(
        _FlakySim(), priors, targets=["d"], obs_stats=obs,
        n_restarts=5,
        evals_per_restart=10,
        rng=np.random.default_rng(0),
    )
    # Should not crash; some basins may be filtered out
    assert report.n_restarts == 5
    assert len(report.basins) <= 5


# ── Report rendering ────────────────────────────────────────────────────


def test_report_markdown_includes_all_basins() -> None:
    report = IdentifiabilityReport(
        n_restarts=3,
        n_basins=2,
        basins=[
            _basin({"a": 1.0, "b": 2.0}, obj=0.5, idx=0),
            _basin({"a": 9.0, "b": 8.0}, obj=0.6, idx=1),
        ],
        cluster_assignment=[0, 1],
        is_multimodal=True,
        warning="Two basins found.",
    )
    md = report.to_markdown()
    assert "Identifiability" in md
    assert "Two basins found" in md
    assert "0.5" in md
    assert "0.6" in md


def test_empty_report_renders_safely() -> None:
    report = IdentifiabilityReport(
        n_restarts=5,
        n_basins=0,
        basins=[],
        cluster_assignment=[],
        is_multimodal=False,
        warning="All NM restarts failed.",
    )
    md = report.to_markdown()
    assert "All NM restarts failed" in md
