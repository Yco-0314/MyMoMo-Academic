"""Packaging / installability tests (no live LLM, no network)."""
from __future__ import annotations

import importlib
import os
from pathlib import Path

from abm_auto import config

_PKG = Path(config.__file__).resolve().parent


def test_package_data_dirs_resolve_inside_package():
    for d in (config.PROMPTS_DIR, config.KNOWLEDGE_DIR, config.TEMPLATES_DIR, config.QUICKSTART_DIR):
        d = Path(d)
        assert d.is_dir(), f"not a dir: {d}"
        assert _PKG in d.parents or d == _PKG / d.name, f"{d} is not under the package dir {_PKG}"


def test_runtime_templates_moved_into_package():
    assert config.TEMPLATES_DIR == _PKG / "runtime_templates"
    assert (config.TEMPLATES_DIR / "simulator").is_dir()


def test_prompts_and_knowledge_present():
    assert (config.PROMPTS_DIR / "analyze.md").exists()
    assert any(config.KNOWLEDGE_DIR.glob("*.md"))


def test_workspace_dir_is_cwd_relative_and_env_overridable(tmp_path, monkeypatch):
    monkeypatch.setenv("ABM_WORKSPACE_DIR", str(tmp_path / "ws"))
    reloaded = importlib.reload(config)
    try:
        assert reloaded.WORKSPACE_DIR == tmp_path / "ws"
    finally:
        monkeypatch.delenv("ABM_WORKSPACE_DIR", raising=False)
        importlib.reload(config)
