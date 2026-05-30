"""Unit tests for SummaryStats adapters."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from abm_auto.calibration.summary_stats import (
    COLUMN_ALIASES,
    full_trajectory,
    mean_std_last,
    normalize_columns,
    trajectory_features,
)


# ── trajectory_features (α) ─────────────────────────────────────────────


def test_trajectory_features_shape_4_per_target() -> None:
    """4 features × n_targets."""
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [10, 8, 6, 4]})
    feats = trajectory_features(df, ["a", "b"])
    assert feats.shape == (8,)   # 4 features × 2 targets


def test_trajectory_features_extracts_peak_correctly() -> None:
    """For a SIR-like infected column [3, 39, 109, 27], peak should be at tick 2 with value 109."""
    df = pd.DataFrame({"I": [3, 39, 109, 27]})
    feats = trajectory_features(df, ["I"])
    peak_tick, peak_val, final_val, mean = feats
    assert peak_tick == 2.0
    assert peak_val == 109.0
    assert final_val == 27.0
    assert mean == pytest.approx((3 + 39 + 109 + 27) / 4)


def test_trajectory_features_length_independent() -> None:
    """Two trajectories of different length should produce same-dim feature vector.

    This is the solve for task #53 (RF backend trajectory length mismatch).
    """
    short = pd.DataFrame({"x": [1, 5, 3]})         # 3 ticks
    long = pd.DataFrame({"x": [1] * 50 + [5] + [3] * 50})   # 101 ticks
    f_short = trajectory_features(short, ["x"])
    f_long = trajectory_features(long, ["x"])
    assert f_short.shape == f_long.shape == (4,)
    # peak values should match
    assert f_short[1] == f_long[1] == 5.0


def test_trajectory_features_missing_column_pads_zeros() -> None:
    df = pd.DataFrame({"a": [1, 2, 3]})
    feats = trajectory_features(df, ["a", "missing"])
    assert feats.shape == (8,)
    # Last 4 entries are zero (missing column)
    assert (feats[4:] == 0).all()


def test_trajectory_features_handles_empty_targets() -> None:
    df = pd.DataFrame({"a": [1, 2]})
    feats = trajectory_features(df, [])
    assert feats.shape == (0,)


# ── full_trajectory (existing) ──────────────────────────────────────────


def test_full_trajectory_shape() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
    feats = full_trajectory(df, ["a", "b"])
    assert feats.shape == (6,)   # 3 ticks × 2 targets


def test_full_trajectory_per_tick_block_layout() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
    feats = full_trajectory(df, ["a", "b"])
    # Per-tick blocks: [a_t0, b_t0, a_t1, b_t1, a_t2, b_t2]
    assert list(feats) == [1.0, 10.0, 2.0, 20.0, 3.0, 30.0]


# ── mean_std_last (existing) ────────────────────────────────────────────


def test_mean_std_last_shape() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
    feats = mean_std_last(df, ["a"])
    assert feats.shape == (3,)
    mean, std, last = feats
    assert mean == 3.0
    assert last == 5.0


# ── normalize_columns (existing alias bridge) ───────────────────────────


def test_normalize_columns_renames_count_s_to_susceptible() -> None:
    df = pd.DataFrame({"count_s": [1, 2], "count_i": [3, 4], "count_r": [5, 6]})
    renamed = normalize_columns(df, ["susceptible", "infected", "resistant"])
    assert "susceptible" in renamed.columns
    assert "count_s" not in renamed.columns


def test_normalize_columns_idempotent_when_already_named() -> None:
    df = pd.DataFrame({"susceptible": [1, 2], "infected": [3, 4]})
    renamed = normalize_columns(df, ["susceptible", "infected"])
    assert list(renamed.columns) == ["susceptible", "infected"]


def test_normalize_columns_handles_no_match_silently() -> None:
    """If neither name nor alias is present, leave df unchanged (downstream
    summary_fn pads zeros)."""
    df = pd.DataFrame({"unrelated": [1, 2]})
    renamed = normalize_columns(df, ["susceptible"])
    assert "susceptible" not in renamed.columns
    assert list(renamed.columns) == ["unrelated"]


# ── Cross-domain trajectory_features check ──────────────────────────────


def test_trajectory_features_works_on_opinion_dynamics_shape() -> None:
    """Opinion dynamics: mean_opinion stable, opinion_variance decays."""
    df = pd.DataFrame({
        "mean_opinion": [0.5] * 100,
        "opinion_variance": [0.25, 0.20, 0.15, 0.10, 0.08] + [0.05] * 95,
        "n_clusters": [10, 8, 6, 4, 2] + [2] * 95,
    })
    feats = trajectory_features(df, ["mean_opinion", "opinion_variance", "n_clusters"])
    assert feats.shape == (12,)
    # opinion_variance peak should be at tick 0
    assert feats[4] == 0.0   # peak_tick for variance
    assert feats[5] == 0.25  # peak_val for variance
    assert feats[6] == 0.05  # final_val for variance


def test_trajectory_features_works_on_schelling_shape() -> None:
    """Schelling: n_unhappy decays to 0, segregation_index stabilizes."""
    df = pd.DataFrame({
        "n_unhappy": [50, 30, 15, 5, 0] + [0] * 95,
        "segregation_index": [0.3, 0.5, 0.7, 0.85, 0.9] + [0.9] * 95,
        "fraction_segregated": [0.2, 0.4, 0.6, 0.75, 0.8] + [0.8] * 95,
    })
    feats = trajectory_features(df, ["n_unhappy", "segregation_index", "fraction_segregated"])
    assert feats.shape == (12,)
    # n_unhappy peak at tick 0
    assert feats[0] == 0.0    # peak_tick
    assert feats[1] == 50.0   # peak_val
    assert feats[2] == 0.0    # final_val
