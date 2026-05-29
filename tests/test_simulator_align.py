"""Tests for `_align_rows` — trajectory length alignment between sim and observed.

Without alignment, RF calibrator backend crashes on cross-domain runs
where sim trajectory length ≠ observed length. See task #53 +
docs/dogfood/codegen-opinion.md.
"""
from __future__ import annotations

import pandas as pd
import pytest

from abm_auto.calibration.simulator import _align_rows


def test_truncate_when_df_longer() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
    out = _align_rows(df, target_n=3)
    assert len(out) == 3
    assert list(out["a"]) == [1, 2, 3]


def test_pad_with_last_row_when_df_shorter() -> None:
    """Padding uses the LAST row's value (= steady-state extrapolation)."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    out = _align_rows(df, target_n=5)
    assert len(out) == 5
    assert list(out["a"]) == [1, 2, 3, 3, 3]   # last value 3 repeats


def test_no_change_when_already_target_length() -> None:
    df = pd.DataFrame({"a": [1, 2, 3]})
    out = _align_rows(df, target_n=3)
    assert out is df   # identity — no copy when no change needed


def test_pad_handles_multi_column_correctly() -> None:
    df = pd.DataFrame({"a": [1, 2], "b": [10, 20]})
    out = _align_rows(df, target_n=4)
    assert list(out["a"]) == [1, 2, 2, 2]
    assert list(out["b"]) == [10, 20, 20, 20]


def test_empty_df_returns_unchanged() -> None:
    """Edge case: zero-row df can't be padded (no last row to repeat)."""
    df = pd.DataFrame(columns=["a", "b"])
    out = _align_rows(df, target_n=5)
    assert len(out) == 0


def test_returned_df_is_a_copy_when_modified() -> None:
    """Mutating the output must not affect the input."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    out = _align_rows(df, target_n=2)
    out.iloc[0] = {"a": 999}
    assert df.iloc[0]["a"] == 1   # original unchanged


def test_index_reset_after_truncate() -> None:
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5]}, index=[10, 20, 30, 40, 50])
    out = _align_rows(df, target_n=2)
    # Result has a fresh RangeIndex, not the original
    assert list(out.index) == [0, 1]


def test_index_reset_after_pad() -> None:
    df = pd.DataFrame({"a": [1, 2]}, index=[5, 6])
    out = _align_rows(df, target_n=4)
    assert list(out.index) == [0, 1, 2, 3]
