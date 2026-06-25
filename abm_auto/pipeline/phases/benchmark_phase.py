"""ADR-021 D5 — BenchmarkPhase: run cross-tool baselines, surface them in the report.

Opt-in via `--benchmark <archetype>` (an EXPLICIT archetype tag — auto-deriving the
archetype from an arbitrary design is a deferred Non-goal). When set, this phase runs
the available BenchmarkAdapters (Mesa / NetLogo) for that archetype, reads our own
metrics best-effort from the run's result CSVs, and writes a markdown comparison table
into `ctx.comparison_text` — which the existing `ReporterAgent` baseline_comparison
already renders into the manuscript. Unavailable tools are honestly marked, never imputed.

`should_run` is False unless `--benchmark` was passed ⇒ additive / off by default.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import pandas as pd

from abm_auto.agents.benchmark_adapter import (
    ARCHETYPE_METRICS,
    BenchmarkSpec,
    MesaBaseline,
    NetLogoBaseline,
    render_comparison_table,
    run_benchmarks,
)


class BenchmarkPhase:
    """Runs cross-tool baselines and appends a comparison table to ctx.comparison_text."""

    name = "Cross-tool benchmark (ADR-021 D5)"
    contract = None  # opaque to D3 contract validation

    def __init__(self, adapters: Optional[List] = None):
        self._adapters = adapters  # injectable for tests; None ⇒ Mesa + NetLogo

    def should_run(self, ctx) -> bool:
        return bool(getattr(ctx, "benchmark_archetype", None))

    def _adapter_list(self) -> List:
        if self._adapters is not None:
            return self._adapters
        return [MesaBaseline(), NetLogoBaseline()]

    def run(self, ctx) -> None:
        archetype = ctx.benchmark_archetype
        metrics = ARCHETYPE_METRICS.get(archetype, ("peak_infected",))
        spec = BenchmarkSpec(archetype=archetype, seed=ctx.seed or 0, metrics=metrics)
        results = run_benchmarks(spec, self._adapter_list())
        our = _our_metrics(ctx, metrics)
        table = render_comparison_table(our, results)
        section = f"\n\n### Cross-tool baselines — archetype `{archetype}` (ADR-021 D5)\n{table}\n"
        ctx.comparison_text = (getattr(ctx, "comparison_text", None) or "") + section


def _our_metrics(ctx, metrics) -> Dict[str, float]:
    """Best-effort: read our run's result CSVs and pull each metric whose name matches a
    column. `peak_*` → column max; otherwise → final-row value. Missing ⇒ omitted (shown
    as '—'), never fabricated."""
    out: Dict[str, float] = {}
    workspace = getattr(ctx, "workspace", None)
    if workspace is None:
        return out
    frames = []
    for d in sorted(workspace.path.glob("results/run_*")):
        for csv in sorted(d.glob("*.csv")):
            try:
                frames.append(pd.read_csv(csv))
            except Exception:
                pass
    if not frames:
        return out
    combined = pd.concat(frames, ignore_index=True)
    for m in metrics:
        col = m.replace("peak_", "").replace("final_", "")
        if m in combined.columns:
            series = combined[m]
        elif col in combined.columns:
            series = combined[col]
        else:
            continue
        series = series.dropna()
        if series.empty:
            continue  # anti-fabrication: never emit NaN — omit a metric we have no real value for
        value = float(series.max()) if m.startswith("peak_") else float(series.iloc[-1])
        if not math.isfinite(value):
            continue
        out[m] = value
    return out
