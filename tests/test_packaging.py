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


import tomllib


def _pyproject() -> dict:
    root = Path(config.__file__).resolve().parent.parent
    with open(root / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def test_pyproject_has_mymomo_alias_and_version():
    pp = _pyproject()
    scripts = pp["project"]["scripts"]
    assert scripts["abm-auto"] == "abm_auto.cli:app"
    assert scripts["mymomo"] == "abm_auto.cli:app"
    assert pp["project"]["version"] == "0.4.0"


def test_pyproject_excludes_gis_from_wheel():
    pp = _pyproject()
    wheel = pp["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert "abm_auto/gis" in wheel["exclude"]
    assert wheel["packages"] == ["abm_auto"]


def test_pyproject_has_classifiers_and_urls():
    pp = _pyproject()
    assert pp["project"]["urls"]["Repository"]
    assert any("Apache" in c for c in pp["project"]["classifiers"])


from typer.testing import CliRunner

from abm_auto.cli import app

_runner = CliRunner()


def test_quickstart_scaffolds_starter_files(tmp_path):
    result = _runner.invoke(app, ["quickstart", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".env").exists()
    assert (tmp_path / "story.md").exists()
    assert (tmp_path / "story.md").read_text(encoding="utf-8").strip()
    assert "ANTHROPIC_API_KEY" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_quickstart_does_not_clobber_existing(tmp_path):
    (tmp_path / ".env").write_text("KEEP=me", encoding="utf-8")
    result = _runner.invoke(app, ["quickstart", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "KEEP=me"  # untouched
    assert (tmp_path / "story.md").exists()  # the missing one is still created


def test_run_preflights_missing_api_key(tmp_path, monkeypatch):
    from abm_auto import config
    monkeypatch.setattr(config, "get_api_key", lambda: "")
    story = tmp_path / "story.md"
    story.write_text("# x", encoding="utf-8")
    result = _runner.invoke(app, ["run", str(story)])
    assert result.exit_code != 0
    assert "API key" in result.stdout
