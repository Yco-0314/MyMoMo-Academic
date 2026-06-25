"""Characterization test for the sensitivity-tornado path in VisualizerAgent.

Both halves of this path were dead before the agents-aux-1 fix:
  1. run() read a hardcoded 'sensitivity_indices.json' that SensitivityAnalyzer
     never writes (it writes 'sensitivity_<method>.json'), so the figure was
     never produced; and
  2. _plot_sensitivity expected a dict {"params": [...], "S1": [...]} but the
     analyzer writes a LIST of per-parameter dicts, so the first real call would
     have raised AttributeError.
This pins the now-working behavior.
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")  # VisualizerAgent.run() sets this; tests call helpers directly

from abm_auto.agents.visualizer import VisualizerAgent

# Schema SensitivityAnalyzer._save_results actually writes (salib_optimizer.py).
_MORRIS = [
    {"parameter": "beta", "mu_star": 0.42, "sigma": 0.11, "mu_star_conf": 0.03},
    {"parameter": "gamma", "mu_star": 0.18, "sigma": 0.05, "mu_star_conf": 0.02},
    {"parameter": "delta", "mu_star": 0.07, "sigma": 0.02, "mu_star_conf": 0.01},
]
_SOBOL = [
    {"parameter": "beta", "S1": 0.30, "S1_conf": 0.04, "ST": 0.55, "ST_conf": 0.05},
    {"parameter": "gamma", "S1": 0.10, "S1_conf": 0.02, "ST": 0.22, "ST_conf": 0.03},
]


def test_sensitivity_path_returns_none_when_absent(tmp_path):
    assert VisualizerAgent(tmp_path)._sensitivity_path() is None


def test_sensitivity_path_finds_morris(tmp_path):
    (tmp_path / "sensitivity_morris.json").write_text(json.dumps(_MORRIS))
    assert VisualizerAgent(tmp_path)._sensitivity_path() == tmp_path / "sensitivity_morris.json"


def test_sensitivity_path_finds_sobol(tmp_path):
    (tmp_path / "sensitivity_sobol.json").write_text(json.dumps(_SOBOL))
    assert VisualizerAgent(tmp_path)._sensitivity_path() == tmp_path / "sensitivity_sobol.json"


def test_plot_sensitivity_morris_produces_png(tmp_path):
    agent = VisualizerAgent(tmp_path)
    sa = tmp_path / "sensitivity_morris.json"
    sa.write_text(json.dumps(_MORRIS))

    out = agent._plot_sensitivity(sa)

    assert out is not None
    assert out.exists()
    assert out.suffix == ".png"


def test_plot_sensitivity_sobol_produces_png(tmp_path):
    agent = VisualizerAgent(tmp_path)
    sa = tmp_path / "sensitivity_sobol.json"
    sa.write_text(json.dumps(_SOBOL))

    out = agent._plot_sensitivity(sa)

    assert out is not None and out.exists()


def test_plot_sensitivity_rejects_legacy_dict_schema(tmp_path):
    """The pre-fix code expected a dict; a dict must now degrade gracefully, not crash."""
    agent = VisualizerAgent(tmp_path)
    sa = tmp_path / "sensitivity_morris.json"
    sa.write_text(json.dumps({"params": ["a", "b"], "S1": [0.1, 0.2]}))

    assert agent._plot_sensitivity(sa) is None


def test_plot_sensitivity_empty_list_returns_none(tmp_path):
    agent = VisualizerAgent(tmp_path)
    sa = tmp_path / "sensitivity_morris.json"
    sa.write_text(json.dumps([]))

    assert agent._plot_sensitivity(sa) is None
