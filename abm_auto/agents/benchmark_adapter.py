"""ADR-021 D5 — the cross-tool `BenchmarkAdapter` seam.

Turn "we beat Mesa/NetLogo" into a measurable artefact: one small interface,
`BenchmarkAdapter.run(spec) -> dict[metric, value]`, proven by TWO real adapters —
`MesaBaseline` (pure Python) and `NetLogoBaseline` (wraps verification/netlogo_oracle).
Their metrics render next to ours via the existing `ReporterAgent` baseline_comparison.

Anti-fabrication 命门 (ADR-013): every reported baseline number comes from a REAL
Mesa / NetLogo run. An unavailable tool is omitted and explicitly marked "unavailable",
never imputed. No LLM produces a baseline number.

Import-clean without the `[benchmarks]` extra: `mesa` is imported lazily inside
`MesaBaseline`, never at module top.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict

# Default scalar metrics per known archetype (explicit — not LLM-derived).
ARCHETYPE_METRICS: Dict[str, Tuple[str, ...]] = {
    "sir_network": ("peak_infected", "final_infected"),
}


class BenchmarkSpec(BaseModel):
    """An explicit benchmark request (archetype tag + params), not LLM-free-typed."""

    model_config = ConfigDict(extra="forbid")

    archetype: str                      # e.g. "sir_network"
    params: Dict[str, float] = {}
    n_ticks: int = 50
    n_runs: int = 1
    seed: int = 0
    metrics: Tuple[str, ...] = ("peak_infected",)


class BenchmarkAdapter:
    """The seam: a named tool that runs a BenchmarkSpec and returns scalar metrics."""

    name: str = "adapter"

    def is_available(self) -> bool:
        raise NotImplementedError

    def run(self, spec: BenchmarkSpec) -> Dict[str, float]:
        raise NotImplementedError


class MesaBaseline(BenchmarkAdapter):
    """Adapter #1 — a real Mesa run of the archetype. Unavailable if `mesa` missing."""

    name = "mesa"

    def is_available(self) -> bool:
        try:
            import mesa  # noqa: F401  (lazy — keeps the module import-clean without the extra)
            return True
        except ImportError:
            return False

    def run(self, spec: BenchmarkSpec) -> Dict[str, float]:
        if spec.archetype != "sir_network":
            raise ValueError(f"MesaBaseline has no scaffold for archetype {spec.archetype!r}")
        return _mesa_sir_network(spec)


class NetLogoBaseline(BenchmarkAdapter):
    """Adapter #2 — delegates to verification/netlogo_oracle.

    Owns the reduction of `trajectory_summary()`'s per-tick DataFrame (columns
    `<col>_mean`/`<col>_std`/`n_samples`) to a scalar `{metric: value}` map
    (final-tick `<col>_mean`), matching MesaBaseline's shape.
    """

    name = "netlogo"

    def __init__(self, model_path: Optional[str] = None, experiment_name: str = ""):
        self.model_path = model_path
        self.experiment_name = experiment_name

    def is_available(self) -> bool:
        try:
            from abm_auto.verification import netlogo_oracle
        except ImportError:
            return False
        return bool(self.model_path) and netlogo_oracle.is_available()

    def run(self, spec: BenchmarkSpec) -> Dict[str, float]:
        import tempfile
        from pathlib import Path

        from abm_auto.verification import netlogo_oracle

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "table.csv"
            netlogo_oracle.run_experiment(self.model_path, self.experiment_name, out)
            df = netlogo_oracle.parse_table(out)
            summary = netlogo_oracle.trajectory_summary(df, target_cols=list(spec.metrics))
            return _reduce_trajectory(summary, spec.metrics)


def _reduce_trajectory(summary, metrics: Tuple[str, ...]) -> Dict[str, float]:
    """Final-tick mean per requested metric — the scalar reduction D5 owns."""
    out: Dict[str, float] = {}
    if summary is None or len(summary) == 0:
        return out
    last = summary.iloc[-1]
    for m in metrics:
        col = f"{m}_mean"
        if col in summary.columns:
            out[m] = float(last[col])
    return out


def run_benchmarks(
    spec: BenchmarkSpec, adapters: List[BenchmarkAdapter]
) -> Dict[str, Dict[str, Any]]:
    """Run each AVAILABLE adapter; record unavailable ones as a skip (never fabricate)."""
    results: Dict[str, Dict[str, Any]] = {}
    for adapter in adapters:
        if not adapter.is_available():
            results[adapter.name] = {"_unavailable": True}
            continue
        results[adapter.name] = dict(adapter.run(spec))
    return results


def render_comparison_table(
    our_metrics: Dict[str, float], benchmark_results: Dict[str, Dict[str, Any]]
) -> str:
    """Markdown table: our metrics vs each adapter. Unavailable adapters say so."""
    # Rows = the union of our metrics and every metric any adapter reported, so a
    # metric only a baseline produced still shows (our cell falls back to '—').
    metric_names = list(our_metrics.keys())
    for res in benchmark_results.values():
        for k in res:
            if k != "_unavailable" and k not in metric_names:
                metric_names.append(k)
    header = "| Metric | ours | " + " | ".join(benchmark_results.keys()) + " |"
    sep = "|" + "---|" * (2 + len(benchmark_results))
    lines = [header, sep]
    for m in metric_names:
        cells = [m, _fmt(our_metrics.get(m))]
        for name, res in benchmark_results.items():
            if res.get("_unavailable"):
                cells.append("_tool unavailable_")
            else:
                cells.append(_fmt(res.get(m)))
        lines.append("| " + " | ".join(cells) + " |")
    if not metric_names:
        lines.append("| _(no metrics)_ |" + " |" * (1 + len(benchmark_results)))
    return "\n".join(lines)


def _fmt(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:.4g}"


def _mesa_sir_network(spec: BenchmarkSpec) -> Dict[str, float]:
    """A real, seeded SIR-on-network Mesa run. Exercised only with `[benchmarks]`
    installed (mesa imported lazily here)."""
    import networkx as nx
    import mesa

    beta = spec.params.get("beta", 0.3)
    gamma = spec.params.get("gamma", 0.1)
    n = int(spec.params.get("n_agents", 100))
    k = int(spec.params.get("k", 4))
    rng_seed = spec.seed

    class _Person(mesa.Agent):
        def __init__(self, model, state):
            super().__init__(model)
            self.state = state  # "S" | "I" | "R"

        def step(self):
            if self.state == "I":
                for nbr in self.model.graph.neighbors(self.unique_id):
                    agent = self.model.by_id[nbr]
                    if agent.state == "S" and self.model.random.random() < beta:
                        agent.state = "I"
                if self.model.random.random() < gamma:
                    self.state = "R"

    class _SIR(mesa.Model):
        def __init__(self):
            super().__init__(seed=rng_seed)
            self.graph = nx.watts_strogatz_graph(n, k, 0.1, seed=rng_seed)
            self.by_id = {}
            for node in self.graph.nodes():
                state = "I" if node == 0 else "S"
                a = _Person(self, state)
                a.unique_id = node
                self.by_id[node] = a
            self.peak = 1

        def step(self):
            self.agents.shuffle_do("step")
            infected = sum(1 for a in self.by_id.values() if a.state == "I")
            self.peak = max(self.peak, infected)

    model = _SIR()
    for _ in range(spec.n_ticks):
        model.step()
    final_infected = sum(1 for a in model.by_id.values() if a.state == "I")
    return {"peak_infected": float(model.peak), "final_infected": float(final_infected)}
