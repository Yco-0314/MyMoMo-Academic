"""Tests for ADR-021 D1 — the Experiment seam.

No LLM / no API key: cells run through registered in-process backends. The
module-level `_demo` backend is picklable into ProcessPool workers.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from abm_auto.experiment import (
    Experiment,
    ExperimentSpec,
    _expand,
    register_backend,
)


# --- 1. spec parse + validate --------------------------------------------

def test_from_dict_parses_and_defaults():
    exp = Experiment.from_dict({"name": "t", "sweep": {"a": [1, 2]}})
    assert exp.spec.name == "t"
    assert exp.spec.backend == "pipeline"  # default
    assert exp.spec.n_iter == 1 and exp.spec.base_seed == 0


def test_unknown_key_rejected():
    with pytest.raises(Exception):
        ExperimentSpec.model_validate({"name": "t", "bogus": 1})


def test_json_and_yaml_parse_to_same_spec(tmp_path):
    data = {"name": "t", "backend": "_demo", "sweep": {"a": [1, 2]}, "n_iter": 2}
    jp = tmp_path / "s.json"
    jp.write_text(json.dumps(data), encoding="utf-8")
    j_spec = Experiment.from_file(jp).spec

    yaml = pytest.importorskip("yaml")  # .json is the zero-dep default; yaml optional
    yp = tmp_path / "s.yaml"
    yp.write_text(yaml.safe_dump(data), encoding="utf-8")
    y_spec = Experiment.from_file(yp).spec
    assert j_spec == y_spec


# --- 2. sweep expansion + seed fan-out -----------------------------------

def test_expand_counts_single_param():
    spec = ExperimentSpec(name="t", sweep={"belief": [0.1, 0.4, 0.7]}, n_iter=10)
    cells = _expand(spec)
    assert len(cells) == 30  # 3 tuples × 10 seeds
    seeds_for_first = [c["seed"] for c in cells[:10]]
    assert seeds_for_first == list(range(10))


def test_expand_cartesian_product():
    spec = ExperimentSpec(name="t", sweep={"a": [1, 2], "b": [10, 20, 30]}, n_iter=2)
    cells = _expand(spec)
    assert len(cells) == 2 * 3 * 2  # |a| × |b| × n_iter


def test_expand_no_sweep_is_seed_only():
    spec = ExperimentSpec(name="t", sweep={}, n_iter=4)
    assert len(_expand(spec)) == 4


# --- 3. single-cell execution + reporter (runtime mock backend) ----------

def test_single_cell_merges_base_and_tuple():
    seen = {}

    @register_backend("_mock_capture")
    def _b(params, seed):
        seen["params"] = params
        seen["seed"] = seed
        return {"out": params["a"] * 100 + seed}

    spec = ExperimentSpec(
        name="t", backend="_mock_capture", base={"k": 9}, sweep={"a": [3]}, n_iter=1
    )
    from abm_auto.experiment import _run_cell
    row = _run_cell(spec, {"params": {"a": 3}, "seed": 0})
    assert seen["params"] == {"k": 9, "a": 3}  # base merged with tuple
    assert row == {"a": 3, "seed": 0, "out": 300}


# --- 4. end-to-end DataFrame, serial -------------------------------------

def test_run_serial_shape_columns_and_determinism(tmp_path):
    spec = ExperimentSpec(
        name="t", backend="_demo", sweep={"a": [1, 2, 3]}, n_iter=4, n_workers=1
    )
    df1 = Experiment(spec, out_dir=tmp_path / "r1").run()
    assert len(df1) == 3 * 4
    assert set(["a", "seed", "value", "n_params"]).issubset(df1.columns)
    # deterministic ordering: same spec ⇒ equal frame
    df2 = Experiment(spec, out_dir=tmp_path / "r2").run()
    assert df1.equals(df2)
    # sorted by (a, seed)
    assert df1[["a", "seed"]].values.tolist() == sorted(df1[["a", "seed"]].values.tolist())


# --- 5. parallel path matches serial -------------------------------------

def test_parallel_matches_serial(tmp_path):
    base = dict(name="t", backend="_demo", sweep={"a": [1, 2, 3, 4]}, n_iter=3)
    serial = Experiment(ExperimentSpec(**base, n_workers=1), out_dir=tmp_path / "s").run()
    parallel = Experiment(ExperimentSpec(**base, n_workers=4), out_dir=tmp_path / "p").run()
    assert serial.equals(parallel)


# --- 7. resume ledger (D1 owns it) ---------------------------------------

def test_resume_skips_completed_cells(tmp_path):
    calls = {"n": 0}

    @register_backend("_mock_counting")
    def _b(params, seed):
        calls["n"] += 1
        return {"v": params["a"] + seed}

    spec = ExperimentSpec(
        name="t", backend="_mock_counting", sweep={"a": [1, 2]}, n_iter=2
    )
    out = tmp_path / "exp"
    df1 = Experiment(spec, out_dir=out).run()
    assert calls["n"] == 4  # 2 tuples × 2 seeds, all fresh
    # markers were written
    assert len(list((out / "_cells").glob("*.json"))) == 4

    # resume: every cell already done ⇒ zero new backend calls, equal frame
    df2 = Experiment(spec, out_dir=out).run(resume=True)
    assert calls["n"] == 4  # no new calls
    assert df1.sort_index(axis=1).equals(df2.sort_index(axis=1))


def test_resume_runs_only_missing_cells(tmp_path):
    calls = {"n": 0}

    @register_backend("_mock_partial")
    def _b(params, seed):
        calls["n"] += 1
        return {"v": params["a"] + seed}

    out = tmp_path / "exp"
    # first: only the a=1 tuple
    Experiment(ExperimentSpec(name="t", backend="_mock_partial", sweep={"a": [1]}, n_iter=2),
               out_dir=out).run()
    assert calls["n"] == 2
    # widen the sweep to a=[1,2]; resume should run only the 2 new a=2 cells
    df = Experiment(ExperimentSpec(name="t", backend="_mock_partial", sweep={"a": [1, 2]}, n_iter=2),
                    out_dir=out).run(resume=True)
    assert calls["n"] == 4  # +2 only
    assert len(df) == 4


def test_yaml_without_pyyaml_gives_clear_error(tmp_path, monkeypatch):
    # simulate PyYAML absence
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "yaml":
            raise ImportError("no yaml")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    yp = tmp_path / "s.yaml"
    yp.write_text("name: t\n", encoding="utf-8")
    with pytest.raises(ImportError, match="PyYAML"):
        Experiment.from_file(yp)
