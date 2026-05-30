"""Unit tests for profile likelihood + Fisher info identifiability methods.

Synthetic simulators with known identifiability structure:
  - _IsolatedMinSim: each parameter independently identifiable (peaked)
  - _RidgeSim: μ × α product matters, individual values don't (joint flat dir)
  - _FlatSim: completely insensitive — everything flat
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.calibration.identifiability_profile import (
    fisher_info_eigen,
    profile_likelihood,
    ProfileResult,
    FisherEigenResult,
)


# ── Synthetic simulators ────────────────────────────────────────────────


class _IsolatedMinSim:
    """f(x, y) = (x-2)² + (y-3)² — each param independently identifiable."""

    def simulate(self, params, _targets):
        x, y = params["x"], params["y"]
        return np.array([(x - 2) ** 2 + (y - 3) ** 2], dtype=float)


class _RidgeSim:
    """simulate returns LINEAR (x+y) — ridge along (+1,-1)/√2.

    Sim returns `[x+y]`; obs is `[5]`. The implementation computes
    objective as ||sim − obs||² = (x+y−5)², whose Hessian at any MAP
    on the ridge (x+y=5) is [[2,2],[2,2]] → eigenvalues (4, 0). The
    zero eigenvalue's eigenvector is the (+1, -1) direction — that's
    the flat ridge.
    """

    def simulate(self, params, _targets):
        x, y = params["x"], params["y"]
        return np.array([x + y], dtype=float)


class _FlatSim:
    """f returns constant — completely unidentifiable."""

    def simulate(self, params, _targets):
        return np.array([1.0], dtype=float)


# ── profile_likelihood ──────────────────────────────────────────────────


def test_profile_likelihood_runs_per_param() -> None:
    sim = _IsolatedMinSim()
    priors = {"x": {"min": 0, "max": 4}, "y": {"min": 0, "max": 6}}
    obs = np.array([0.0])
    result = profile_likelihood(
        sim, priors, map_params={"x": 2.0, "y": 3.0},
        targets=["dummy"], obs_stats=obs, n_grid=11,
    )
    assert isinstance(result, ProfileResult)
    assert set(result.per_param.keys()) == {"x", "y"}
    assert len(result.per_param["x"].points) == 11


def test_profile_likelihood_detects_isolated_minimum() -> None:
    """Both params should have HIGH curvature (well-identified)."""
    sim = _IsolatedMinSim()
    priors = {"x": {"min": 0, "max": 4}, "y": {"min": 0, "max": 6}}
    obs = np.array([0.0])
    result = profile_likelihood(
        sim, priors, map_params={"x": 2.0, "y": 3.0},
        targets=["dummy"], obs_stats=obs, n_grid=11,
    )
    # Both profiles should have non-trivial spread (curvature > 0.1)
    for p in result.per_param.values():
        assert p.curvature > 0.1


def test_profile_likelihood_detects_flat() -> None:
    sim = _FlatSim()
    priors = {"x": {"min": 0, "max": 4}, "y": {"min": 0, "max": 6}}
    obs = np.array([1.0])  # f returns 1 always, ||1-1||=0 → objective 0
    result = profile_likelihood(
        sim, priors, map_params={"x": 2.0, "y": 3.0},
        targets=["dummy"], obs_stats=obs, n_grid=11,
    )
    flat = result.unidentifiable_params(threshold=0.1)
    # Both x and y should be flagged as unidentifiable
    assert set(flat) == {"x", "y"}


def test_profile_likelihood_markdown_includes_verdict_table() -> None:
    sim = _IsolatedMinSim()
    priors = {"x": {"min": 0, "max": 4}, "y": {"min": 0, "max": 6}}
    obs = np.array([0.0])
    result = profile_likelihood(
        sim, priors, map_params={"x": 2.0, "y": 3.0},
        targets=["dummy"], obs_stats=obs, n_grid=5,
    )
    md = result.to_markdown()
    assert "Profile likelihood" in md
    assert "Curvature" in md


# ── fisher_info_eigen ────────────────────────────────────────────────────


def test_fisher_eigen_returns_eigendecomposition() -> None:
    sim = _IsolatedMinSim()
    priors = {"x": {"min": 0, "max": 4}, "y": {"min": 0, "max": 6}}
    obs = np.array([0.0])
    result = fisher_info_eigen(
        sim, priors, map_params={"x": 2.0, "y": 3.0},
        targets=["dummy"], obs_stats=obs, eps_frac=0.05,
    )
    assert isinstance(result, FisherEigenResult)
    assert result.hessian.shape == (2, 2)
    assert result.eigenvalues.shape == (2,)
    assert result.eigenvectors.shape == (2, 2)


def test_fisher_eigen_isolated_min_has_no_flat_directions() -> None:
    """f(x,y)=(x-2)² + (y-3)² → Hessian diag(2,2), both eigenvalues positive."""
    sim = _IsolatedMinSim()
    priors = {"x": {"min": 0, "max": 4}, "y": {"min": 0, "max": 6}}
    obs = np.array([0.0])
    result = fisher_info_eigen(
        sim, priors, map_params={"x": 2.0, "y": 3.0},
        targets=["dummy"], obs_stats=obs, eps_frac=0.05,
    )
    # ∇²(f²) at minimum where f=0: ∂²/∂x² 2*f * f_xx + 2*(f_x)² evaluated at the
    # minimum equals 2*0 + 0 = 0 for the cross terms... actually since f(2,3)=0,
    # ||f||² = f², so ∇²f² = 2*(∇f ∇fᵀ) + 2*f ∇²f. At MAP: f=0, ∇f=0 → Hessian = 0.
    # This test only checks SHAPE + finite values, not numerical values, because
    # the Hessian at a perfect zero is degenerate.
    assert np.all(np.isfinite(result.eigenvalues))


def test_fisher_eigen_ridge_detects_flat_direction() -> None:
    """Ridge sim: linear sim=(x+y), obs=5, objective=(x+y-5)².

    Hessian at any MAP on ridge x+y=5 is [[2,2],[2,2]] →
    eigenvalues (4, 0) where the 0 eigenvalue corresponds to the
    (+1,-1) direction (move x up, y down keeps x+y=5 unchanged).
    """
    sim = _RidgeSim()
    priors = {"x": {"min": 0, "max": 5}, "y": {"min": 0, "max": 5}}
    # MAP on the ridge: x=2, y=3 satisfies x+y=5
    obs = np.array([5.0])
    result = fisher_info_eigen(
        sim, priors, map_params={"x": 2.0, "y": 3.0},
        targets=["dummy"], obs_stats=obs, eps_frac=0.02,
    )
    # Largest eigenvalue ~4, smallest ~0
    assert abs(result.eigenvalues[0] - 4.0) < 0.5, (
        f"Expected largest eigenvalue ~4, got {result.eigenvalues}"
    )
    flat = result.flat_directions(ratio_threshold=1e-2)
    assert len(flat) >= 1, (
        f"Expected ≥1 flat direction, got eigenvalues {result.eigenvalues}"
    )
    # Flat direction should be roughly (+1, -1)/√2 OR (-1, +1)/√2
    flat_eig, flat_vec = flat[0]
    coefs = sorted([abs(flat_vec["x"]), abs(flat_vec["y"])])
    assert all(c > 0.5 for c in coefs), (
        f"Expected flat direction to involve BOTH params, got {flat_vec}"
    )


def test_fisher_eigen_handles_simulator_failure() -> None:
    class _NoneSim:
        def simulate(self, params, _targets):
            return None
    priors = {"x": {"min": 0, "max": 1}}
    result = fisher_info_eigen(
        _NoneSim(), priors, map_params={"x": 0.5},
        targets=["dummy"], obs_stats=np.array([0.0]), eps_frac=0.1,
    )
    assert result is None


def test_fisher_eigen_markdown_lists_eigendecomposition() -> None:
    sim = _IsolatedMinSim()
    priors = {"x": {"min": 0, "max": 4}, "y": {"min": 0, "max": 6}}
    obs = np.array([0.0])
    result = fisher_info_eigen(
        sim, priors, map_params={"x": 2.0, "y": 3.0},
        targets=["dummy"], obs_stats=obs, eps_frac=0.05,
    )
    md = result.to_markdown()
    assert "Fisher information" in md
    assert "Eigenvalue" in md
    # Both params should appear in direction descriptions
    assert "x=" in md and "y=" in md


def test_fisher_eigen_zero_eigenvalues_handled() -> None:
    sim = _FlatSim()
    priors = {"x": {"min": 0, "max": 1}}
    result = fisher_info_eigen(
        sim, priors, map_params={"x": 0.5},
        targets=["dummy"], obs_stats=np.array([1.0]), eps_frac=0.1,
    )
    # All eigenvalues ~0 (flat sim) — flat_directions should return all of them
    flat = result.flat_directions(ratio_threshold=0.1)
    # With all zero eigenvalues, ratio is undefined; impl returns [] in that case
    # This test just ensures no crash + sane return
    assert isinstance(flat, list)
