"""Prior construction for BayesianCalibrator.

Pure function. Given a scenario CSV path, optional allowlist of params to
tune, and optional spec-declared ranges, produce per-param uniform priors.

Priority order for each param:
  1. spec_overrides[name] — story-declared (min, max) win unconditionally.
  2. CSV-inferred ±50% around the default value (or [0,1]-bounded for
     probability-like values).

Without spec_overrides the prior shape depends entirely on whatever the
LLM wrote in SimulatorScenarios.csv — a unit drift (4.4 percent → 0.044
probability) silently puts priors 100× off truth. With spec_overrides
the calibration_param_specs from story.md drive the bounds directly.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import pandas as pd


# Columns that are never tunable (metadata / id)
_SKIP_COLUMNS = {"id", "run_num", "scenario_id", "period_num", "seed"}


def build_priors(
    scenario_csv_path: Path,
    allowlist: Optional[list[str]] = None,
    spec_overrides: Optional[dict[str, dict]] = None,
) -> dict[str, dict]:
    """Build uniform priors per scenario parameter.

    Args:
        scenario_csv_path: Path to SimulatorScenarios.csv. Must exist with ≥1 row.
        allowlist: When set (non-empty), ONLY return priors for these column names
                   (case-insensitive match). Critical safety filter: structural
                   params (agent_num, periods) MUST NOT be perturbed.
        spec_overrides: Map of param name → {"min": float, "max": float} from
                        story-declared ranges. These WIN over CSV-inferred bounds.

    Returns:
        Dict keyed by column name. Each value: {"min", "max", "init", "source"}
        where source ∈ {"spec", "csv"}. Empty dict if CSV missing/empty.
    """
    if not scenario_csv_path.exists():
        return {}
    try:
        df = pd.read_csv(scenario_csv_path)
    except Exception:
        return {}
    if df.empty:
        return {}

    allowlist_lower = {a.lower() for a in (allowlist or [])}
    overrides_lower = {k.lower(): v for k, v in (spec_overrides or {}).items()}
    row = df.iloc[0]
    priors: dict[str, dict] = {}

    for col in df.columns:
        if col.lower() in _SKIP_COLUMNS:
            continue
        if allowlist_lower and col.lower() not in allowlist_lower:
            continue
        try:
            val = float(row[col])
        except (ValueError, TypeError):
            continue
        if math.isnan(val):
            continue

        # Priority 1: spec-declared bounds
        if col.lower() in overrides_lower:
            ov = overrides_lower[col.lower()]
            lo, hi = ov["min"], ov["max"]
            init = min(max(val, lo), hi)  # clamp CSV default into spec range
            priors[col] = {"min": lo, "max": hi, "init": init, "source": "spec"}
            continue

        # Priority 2: CSV ±50%
        if 0.0 <= val <= 1.0:
            lo, hi = max(0.0, val - 0.3), min(1.0, val + 0.3)
        elif val > 0:
            lo, hi = val * 0.5, val * 1.5
        else:
            lo, hi = val * 1.5, val * 0.5
        priors[col] = {"min": lo, "max": hi, "init": val, "source": "csv"}

    return priors
