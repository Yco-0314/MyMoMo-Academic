"""Shared result + fidelity types for calibration backends."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class CalibrationResult:
    """What every inference backend returns.

    Carries enough info for the orchestrator to (a) decide if calibration
    succeeded, (b) write a posterior summary, (c) apply best_params back to
    the scenario CSV.
    """
    ok: bool
    backend: str                   # "abc-rejection" | "pymc-smc" | "skipped" | ...
    n_simulator_calls: int
    best_params: dict[str, float]  # point estimate (posterior mean by convention)
    posterior_summary: pd.DataFrame  # one row per param, columns: count/mean/std/2.5%/50%/97.5%
    reason: str = ""               # populated when ok=False


@dataclass(frozen=True)
class Fidelity:
    """Sim cost knob for multi-fidelity calibration.

    Cheap coarse sims explore the prior space; expensive fine sims confirm
    the optimum. The Multi-Fidelity scheduler in `calibrator.fit` sets the
    simulator's `.fidelity` at each stage; backends (RF / ABC / PyMC / NM)
    consume it transparently via `SimulatorWrapper.simulate`.

    `periods_scale` multiplies the scenario CSV's `periods` column on each
    sim. A periods_scale of 0.4 cuts a 250-tick run to 100 ticks; the
    overall wall saving depends on how much of the sim is fixed-cost
    (subprocess startup + engine import ≈ 0.3-0.5 s) vs proportional cost.

    Preset tuning rationale (see ADR-008 OQ#1):

      - 0.2 coarse was too aggressive on SIR (50 ticks doesn't reach the
        post-peak relaxation where `gain_resistance_chance` signal lives).
        Initial cross-domain MF run: SIR 36→1250 MSE regression.
      - Bumping coarse to 0.4 (100 ticks, captures full epidemic curve)
        and medium to 0.7 (175 ticks, into late relaxation) preserves
        the speed win without misleading the surrogate.

    `label` appears in posterior reports + console logs so the operator
    can tell which fidelity produced which best_params.
    """

    periods_scale: float
    label: str

    @classmethod
    def coarse(cls) -> "Fidelity":
        """Cheap exploration — 0.4× full periods. Captures most ABM dynamics
        (epidemic peak + early decay, opinion settling, Schelling moves)
        without being too short to mislead the RF surrogate."""
        return cls(periods_scale=0.4, label="coarse")

    @classmethod
    def medium(cls) -> "Fidelity":
        """Mid-cost refinement — 0.7× full periods. Long enough to capture
        post-peak / late-stage dynamics without paying full cost."""
        return cls(periods_scale=0.7, label="medium")

    @classmethod
    def full(cls) -> "Fidelity":
        """Full sim fidelity. For NM refinement + final validation."""
        return cls(periods_scale=1.0, label="full")
