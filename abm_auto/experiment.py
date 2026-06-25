"""ADR-021 D1 — the `Experiment` seam.

A small interface over large sweep behaviour: a parameter sweep × multi-seed
ensemble is one spec file instead of a hand-written `for`-loop. Replaces the
hand-rolled lever sweeps in `examples/*/run.py`.

    Experiment.from_file("sweep.json").run() -> pandas.DataFrame

The DataFrame is tidy: one row per (parameter-tuple × seed) cell, with one column
per swept parameter, a `seed` column, and the backend's scalar metrics.

Design:

- **Backends are resolved by NAME** from a module-level registry, never by passing
  a closure — so a cell survives pickling into a `ProcessPoolExecutor` worker
  (the `batch.py` parallelism pattern, reused verbatim). A backend is
  `callable(params: dict, seed: int) -> dict[metric, value]`; it both runs the
  cell and reduces it to scalar metrics (the "reporter" of the spec).
- **`.json` is the zero-new-dep default** (stdlib). `.yaml` requires `pyyaml`;
  a missing import raises a loud, actionable error rather than failing obscurely.
- **D1 owns its own per-cell completion ledger** for resume: each finished cell
  writes a JSON sentinel under `<out_dir>/_cells/<key>.json`; `run(resume=True)`
  reads those and skips done cells. This is ORTHOGONAL to ADR-021 D2 Checkpoint
  (which resumes per-Phase WITHIN a single Pipeline run); the two compose, neither
  implements the other.

Zero changes to abm_auto/runtime, codegen, calibration. This is a new, additive
entry point; the 27-phase Pipeline is consumed unchanged.
"""
from __future__ import annotations

import itertools
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from abm_auto import config

# A backend runs one cell and returns its scalar metrics.
Backend = Callable[[Dict[str, Any], int], Dict[str, Any]]
_BACKENDS: Dict[str, Backend] = {}


def register_backend(name: str) -> Callable[[Backend], Backend]:
    """Register a backend under `name` so cells can resolve it across processes."""
    def _decorate(fn: Backend) -> Backend:
        _BACKENDS[name] = fn
        return fn
    return _decorate


def get_backend(name: str) -> Backend:
    if name not in _BACKENDS:
        raise KeyError(
            f"unknown experiment backend {name!r}; registered: {sorted(_BACKENDS)}"
        )
    return _BACKENDS[name]


class ExperimentSpec(BaseModel):
    """Validated experiment spec. Unknown keys are rejected at parse time."""

    model_config = ConfigDict(extra="forbid")

    name: str
    backend: str = "pipeline"
    base: Dict[str, Any] = Field(default_factory=dict)
    sweep: Dict[str, List[Any]] = Field(default_factory=dict)
    n_iter: int = 1
    base_seed: int = 0
    n_workers: int = 1
    reporter: str = "default"


def _cell_key(params: Dict[str, Any], seed: int) -> str:
    """Stable key for a cell, independent of dict ordering."""
    items = sorted(params.items())
    return json.dumps({"params": items, "seed": seed}, sort_keys=True, default=str)


def _expand(spec: ExperimentSpec) -> List[Dict[str, Any]]:
    """Cartesian product of the sweep × seeds → ordered list of cell descriptors."""
    keys = list(spec.sweep.keys())
    value_lists = [spec.sweep[k] for k in keys]
    combos = list(itertools.product(*value_lists)) if keys else [()]
    cells: List[Dict[str, Any]] = []
    for combo in combos:
        tuple_params = dict(zip(keys, combo))
        for k in range(spec.n_iter):
            cells.append({"params": tuple_params, "seed": spec.base_seed + k})
    return cells


def _jsonable(v: Any) -> Any:
    """Coerce a backend value to a JSON-native scalar so resume markers round-trip
    EXACTLY (a numpy scalar would otherwise be stringified by json default=str, and
    come back as a string on resume — silently corrupting the DataFrame column)."""
    # numpy scalars (np.float64 IS a python-float subclass, so check .item() FIRST,
    # before the isinstance guard, or the isinstance check would pass it through unchanged).
    item = getattr(v, "item", None)        # numpy/pandas scalar -> python scalar; python scalars lack .item()
    if callable(item):
        try:
            return v.item()
        except Exception:
            pass
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return str(v)


def _run_cell(spec: ExperimentSpec, cell: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one cell: merge base+tuple, call the backend, build one tidy row."""
    params = cell["params"]
    seed = cell["seed"]
    merged = {**spec.base, **params}
    metrics = get_backend(spec.backend)(merged, seed)
    row: Dict[str, Any] = dict(params)
    row["seed"] = seed
    row.update(metrics)
    return {k: _jsonable(v) for k, v in row.items()}


def _run_cell_worker(spec_json: str, cell: Dict[str, Any], markers_dir: str) -> Dict[str, Any]:
    """Module-level worker for ProcessPoolExecutor (local imports, no pickled closures)."""
    from abm_auto.experiment import ExperimentSpec, _run_cell, _cell_key  # local import
    spec = ExperimentSpec.model_validate_json(spec_json)
    row = _run_cell(spec, cell)
    _write_marker(Path(markers_dir), _cell_key(cell["params"], cell["seed"]), row)
    return row


def _marker_path(markers_dir: Path, key: str) -> Path:
    import hashlib
    # FULL sha256 (not truncated) — a per-cell marker collision would silently drop a
    # completed cell from the resume ledger; the full digest removes that risk.
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return markers_dir / f"{digest}.json"


def _write_marker(markers_dir: Path, key: str, row: Dict[str, Any]) -> None:
    markers_dir.mkdir(parents=True, exist_ok=True)
    path = _marker_path(markers_dir, key)
    path.write_text(json.dumps({"key": key, "row": row}, default=str), encoding="utf-8")


def _read_marker(markers_dir: Path, key: str) -> Optional[Dict[str, Any]]:
    path = _marker_path(markers_dir, key)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))["row"]


class Experiment:
    """A parameter sweep × multi-seed ensemble over a named backend."""

    def __init__(self, spec: ExperimentSpec, out_dir: Optional[Path] = None):
        self.spec = spec
        self.out_dir = Path(out_dir) if out_dir else (
            config.WORKSPACE_DIR / "experiments" / spec.name
        )

    # ---- construction ----------------------------------------------------
    @classmethod
    def from_dict(cls, data: Dict[str, Any], out_dir: Optional[Path] = None) -> "Experiment":
        return cls(ExperimentSpec.model_validate(data), out_dir=out_dir)

    @classmethod
    def from_file(cls, path: str | Path, out_dir: Optional[Path] = None) -> "Experiment":
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml  # optional; only needed for YAML specs
            except ImportError as exc:  # pragma: no cover - exercised via message
                raise ImportError(
                    "YAML experiment specs require PyYAML (`pip install pyyaml`); "
                    "use a .json spec for the zero-dependency path."
                ) from exc
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        return cls.from_dict(data, out_dir=out_dir)

    # back-compat aliases the spec names
    from_yaml = from_file
    from_json = from_file

    # ---- the ledger ------------------------------------------------------
    @property
    def _markers_dir(self) -> Path:
        return self.out_dir / "_cells"

    def _completed_cells(self) -> Dict[str, Dict[str, Any]]:
        """Map cell-key -> row for every cell whose sentinel marker exists."""
        done: Dict[str, Dict[str, Any]] = {}
        markers = self._markers_dir
        if not markers.exists():
            return done
        for marker in markers.glob("*.json"):
            payload = json.loads(marker.read_text(encoding="utf-8"))
            done[payload["key"]] = payload["row"]
        return done

    # ---- execution -------------------------------------------------------
    def run(self, resume: bool = False) -> pd.DataFrame:
        cells = _expand(self.spec)
        done = self._completed_cells() if resume else {}

        pending = [
            c for c in cells
            if _cell_key(c["params"], c["seed"]) not in done
        ]
        rows: List[Dict[str, Any]] = list(done.values())

        if self.spec.n_workers <= 1:
            for cell in pending:
                row = _run_cell(self.spec, cell)
                _write_marker(self._markers_dir, _cell_key(cell["params"], cell["seed"]), row)
                rows.append(row)
        else:
            spec_json = self.spec.model_dump_json()
            markers = str(self._markers_dir)
            with ProcessPoolExecutor(max_workers=self.spec.n_workers) as pool:
                futures = [
                    pool.submit(_run_cell_worker, spec_json, cell, markers)
                    for cell in pending
                ]
                for future in as_completed(futures):
                    rows.append(future.result())

        df = pd.DataFrame(rows)
        return _sort(df, list(self.spec.sweep.keys()))


def _sort(df: pd.DataFrame, sweep_keys: List[str]) -> pd.DataFrame:
    """Deterministic ordering: by swept params then seed (same spec ⇒ equal frame)."""
    if df.empty:
        return df
    sort_cols = [c for c in (sweep_keys + ["seed"]) if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
    return df


# --- built-in backends ----------------------------------------------------

@register_backend("_demo")
def _demo_backend(params: Dict[str, Any], seed: int) -> Dict[str, Any]:
    """Deterministic, dependency-free backend for tests + parallel parity.

    Lives at module level so a ProcessPoolExecutor worker can resolve it after a
    fresh `import abm_auto.experiment`.
    """
    numeric = sum(v for v in params.values() if isinstance(v, (int, float)))
    return {"value": float(numeric) + seed * 0.5, "n_params": len(params)}


@register_backend("pipeline")
def _pipeline_backend(params: Dict[str, Any], seed: int) -> Dict[str, Any]:
    """Run one cell through the real 27-phase Pipeline and read its result CSVs.

    `params` must include `story_path`; remaining keys are forwarded to the
    Pipeline constructor (e.g. iterations, lang, sensitivity_method). Reads
    `results/run_*/*.csv` the way batch.py does and returns mean metrics.
    """
    from abm_auto.pipeline import Pipeline  # local import (worker-safe, heavy)

    kwargs = dict(params)
    story_path = kwargs.pop("story_path", None)
    if story_path is None:
        raise ValueError("'pipeline' backend requires a 'story_path' in base/sweep")
    pipeline = Pipeline(story_path=Path(story_path), seed=seed, **kwargs)
    workspace_path = pipeline.run()

    frames = [
        pd.read_csv(csv)
        for d in sorted(workspace_path.glob("results/run_*"))
        for csv in sorted(d.glob("*.csv"))
    ]
    if not frames:
        return {"workspace": str(workspace_path), "n_runs": 0}
    combined = pd.concat(frames, ignore_index=True)
    means = {
        f"{col}_mean": float(combined[col].mean())
        for col in combined.select_dtypes("number").columns
    }
    return {"workspace": str(workspace_path), "n_runs": len(frames), **means}
