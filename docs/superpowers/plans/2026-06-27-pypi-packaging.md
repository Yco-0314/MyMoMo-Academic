# PyPI Packaging + Quickstart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `abm-auto` correctly pip-installable as a wheel, give a smooth first run, and make it publish-ready (build + verify + gated release workflow) — without uploading.

**Architecture:** Split `config.py`'s single `PROJECT_ROOT` into a package-data root (`_PKG_DIR`, with `runtime_templates/` moved inside the package) resolved relative to the installed `abm_auto/`, and user/runtime paths (`workspace/`, `.env`) resolved relative to the current working directory. Add a `mymomo` console alias, PyPI metadata, wheel/sdist excludes (kill the untracked-`gis/` leak), an `abm-auto quickstart` scaffold + missing-key preflight, a clean-venv build-and-verify script, and a gated release workflow.

**Tech Stack:** Python 3.11+, hatchling, uv (`uv build`, `uv venv`, `uv pip`), typer, python-dotenv, pytest.

**Spec:** `docs/superpowers/specs/2026-06-27-pypi-packaging-design.md`
**Branch:** `feat/pypi-packaging` (off `v3-substantial`). Tests: `.venv/bin/python -m pytest tests/test_packaging.py -v`.

---

## File Structure

- **Modify `abm_auto/config.py`** — split package-data vs user/runtime path roots; add `QUICKSTART_DIR`.
- **Move `runtime_templates/` → `abm_auto/runtime_templates/`** (`git mv`) so templates ship as package data.
- **Modify `pyproject.toml`** — `mymomo` script alias, metadata (keywords/classifiers/urls), wheel+sdist excludes, version `0.4.0`.
- **Create `abm_auto/quickstart_assets/`** — `env.template`, `story.md` (bundled starter, package data).
- **Modify `abm_auto/cli.py`** — `quickstart` command + `_require_api_key()` preflight wired into `run`.
- **Create `scripts/build_and_verify.sh`** — `uv build` → clean venv install → assert CLIs, data dirs, and `gis`-absence.
- **Create `.github/workflows/release.yml`** — build+verify on tag; gated publish job (no-op until token configured).
- **Modify `README.md` + `README.zh.md`** — Quickstart section.
- **Create `tests/test_packaging.py`** — path-resolution, data presence, quickstart, preflight, pyproject, workflow, README assertions (no live LLM/network).

Relevant existing facts (verified):
- `abm_auto/config.py` currently: `PROJECT_ROOT = Path(__file__).parent.parent`; `TEMPLATES_DIR = PROJECT_ROOT / "runtime_templates"`; `PROMPTS_DIR = PROJECT_ROOT / "abm_auto" / "prompts"`; `KNOWLEDGE_DIR = PROJECT_ROOT / "abm_auto" / "mymomo_knowledge"`; `WORKSPACE_DIR = PROJECT_ROOT / "workspace"`; `load_dotenv(PROJECT_ROOT / ".env", override=True)`; import is `from dotenv import load_dotenv`.
- `abm_auto/runner/executor.py` builds subprocess `PYTHONPATH` from `config.PROJECT_ROOT` (so generated model code can `import abm_auto`). It must keep working: `PROJECT_ROOT` will be redefined to `_PKG_DIR.parent` (same value as today: `Path(__file__).parent.parent`).
- `abm_auto/agents/coder.py` reads `config.TEMPLATES_DIR / "simulator"` and `/ "simulator_grid"`, `.rglob("*.py")`.
- `runtime_templates/` contains `simulator/` and `simulator_grid/` subdirs of `.py` template files.
- `abm_auto/gis/` is present on disk but **untracked** — it must never ship.

---

## Task 1: Split config path roots + move runtime_templates into the package

**Files:**
- Modify: `abm_auto/config.py`
- Move: `runtime_templates/` → `abm_auto/runtime_templates/`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_packaging.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -v`
Expected: FAIL — `AttributeError: module 'abm_auto.config' has no attribute 'QUICKSTART_DIR'`, and `TEMPLATES_DIR` still points at the repo root.

- [ ] **Step 3: Move runtime_templates into the package**

Run:
```bash
git mv runtime_templates abm_auto/runtime_templates
```
Then confirm nothing else references the old location:
```bash
grep -rn "runtime_templates" abm_auto tests --include="*.py" | grep -v "config.TEMPLATES_DIR\|abm_auto/runtime_templates"
```
Expected: no hardcoded `runtime_templates` paths outside `config.TEMPLATES_DIR` usage (callers use `config.TEMPLATES_DIR`).

- [ ] **Step 4: Rewrite the path block in `abm_auto/config.py`**

Replace the top path block (the `PROJECT_ROOT`/`load_dotenv`/`*_DIR` lines) with:

```python
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# --- Path roots -----------------------------------------------------------
# Package-data root: the installed ``abm_auto/`` directory. Bundled data
# (prompts, knowledge, runtime templates, quickstart assets) resolves from here
# so it works identically in a dev tree and an installed wheel.
_PKG_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = _PKG_DIR / "prompts"
KNOWLEDGE_DIR = _PKG_DIR / "mymomo_knowledge"
TEMPLATES_DIR = _PKG_DIR / "runtime_templates"
QUICKSTART_DIR = _PKG_DIR / "quickstart_assets"

# Kept ONLY so executor.py can put the import root on a subprocess PYTHONPATH
# (so generated model code can ``import abm_auto``). Same value as before:
# repo root in a dev tree, site-packages in an installed wheel — both correct.
PROJECT_ROOT = _PKG_DIR.parent

# User/runtime paths resolve from the working directory, never site-packages.
load_dotenv(find_dotenv(usecwd=True), override=True)  # find user's .env from CWD up
WORKSPACE_DIR = Path(os.getenv("ABM_WORKSPACE_DIR", str(Path.cwd() / "workspace")))
```

Leave the rest of `config.py` (provider/model/env logic, timeouts, memory) unchanged.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Guard against regressions in the broader suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS / skipped only. If a test assumed `WORKSPACE_DIR` was the repo-root `workspace/` via a hardcoded path (not via `config.WORKSPACE_DIR`), fix that test to reference `config.WORKSPACE_DIR`. Do not revert the config change.

- [ ] **Step 7: Commit**

```bash
git add abm_auto/config.py abm_auto/runtime_templates tests/test_packaging.py
git commit -m "feat(packaging): split package-data vs CWD path roots; move runtime_templates into package"
```

---

## Task 2: pyproject — mymomo alias, metadata, excludes, version bump

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_packaging.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -k pyproject -v`
Expected: FAIL — no `mymomo` script, version is `0.3.0`, no `tool.hatch.build` excludes, no classifiers/urls.

- [ ] **Step 3: Edit `pyproject.toml`**

Set `version = "0.4.0"`. Add after the `description` line:

```toml
keywords = ["agent-based-modeling", "abm", "simulation", "social-science", "llm", "research"]
classifiers = [
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "License :: OSI Approved :: Apache Software License",
    "Topic :: Scientific/Engineering",
    "Intended Audience :: Science/Research",
]
```

Replace the `[project.scripts]` block with:

```toml
[project.scripts]
abm-auto = "abm_auto.cli:app"
mymomo = "abm_auto.cli:app"
```

Add a `[project.urls]` block:

```toml
[project.urls]
Homepage = "https://github.com/Yco-0314/MyMoMo-Academic"
Repository = "https://github.com/Yco-0314/MyMoMo-Academic"
Issues = "https://github.com/Yco-0314/MyMoMo-Academic/issues"
```

Add hatchling build targets (kills the untracked-`gis/` leak and keeps artifacts clean):

```toml
[tool.hatch.build.targets.wheel]
packages = ["abm_auto"]
exclude = ["abm_auto/gis", "**/__pycache__", "**/*.pyc", "**/.DS_Store"]

[tool.hatch.build.targets.sdist]
exclude = ["abm_auto/gis", "workspace", ".env", "**/__pycache__", "**/*.pyc", "**/.DS_Store"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -k pyproject -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/test_packaging.py
git commit -m "feat(packaging): mymomo alias, PyPI metadata, wheel/sdist excludes (gis leak guard), v0.4.0"
```

---

## Task 3: Quickstart assets + `quickstart` command + missing-key preflight

**Files:**
- Create: `abm_auto/quickstart_assets/env.template`, `abm_auto/quickstart_assets/story.md`
- Modify: `abm_auto/cli.py`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Create the bundled starter assets**

Create `abm_auto/quickstart_assets/env.template` (NOT named `.env` — the sdist exclude `**/.env`/`.env` would otherwise strip it):

```
# MyMoMo / abm-auto — environment configuration
# Get an Anthropic API key at https://console.anthropic.com/ and paste it below.
ANTHROPIC_API_KEY=
LLM_PROVIDER=anthropic
```

Create `abm_auto/quickstart_assets/story.md`:

```markdown
# SIR epidemic on a small-world network

## The phenomenon

A disease spreads through a population connected in a small-world social
network. Each person is Susceptible, Infected, or Recovered. We want the
classic epidemic curve: infections rise, peak, then fall as the population
gains immunity.

## Agents

The population is 200 people. Each person has:
- a **state**: one of `S` (susceptible), `I` (infected), `R` (recovered);
- a fixed set of **neighbours** in the network.

## Network

A Watts–Strogatz small-world network: each person connected to `k = 6`
nearest neighbours, with rewiring probability `0.1`.

## Mechanism (each time step)

1. **Infection.** For every infected person, each susceptible neighbour
   becomes infected with probability `beta = 0.15` per contact this step.
2. **Recovery.** Every infected person recovers with probability
   `gamma = 0.05` per step. Recovered people are immune and never reinfected.

## Initial condition

5 randomly chosen people start Infected; everyone else starts Susceptible.

## What to observe

Record, at each time step, the count of people in each state (S, I, R).
Run for 100 steps. Expected result: a single epidemic wave — the infected
count rises to a peak, then decays toward zero as the susceptible pool is
depleted.
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_packaging.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -k "quickstart or preflight" -v`
Expected: FAIL — no `quickstart` command; `run` proceeds past the key check.

- [ ] **Step 4: Add the `quickstart` command + preflight to `abm_auto/cli.py`**

Add a preflight helper (near the top, after `console = Console()`):

```python
def _require_api_key() -> None:
    """Friendly preflight: exit early with guidance if no LLM API key is set."""
    if not config.get_api_key():
        console.print(
            "[red]No API key found.[/red] Set ANTHROPIC_API_KEY in your environment "
            "or a local .env file (run [bold]abm-auto quickstart[/bold] for a starter)."
        )
        raise typer.Exit(1)
```

In the `run` command, make the FIRST line of the body call it (before `from abm_auto.pipeline import Pipeline`):

```python
    _require_api_key()
```

Add the `quickstart` command (next to the other `@app.command()`s):

```python
@app.command()
def quickstart(
    directory: Path = typer.Argument(Path("."), help="Target directory for starter files (default: current dir)"),
):
    """Scaffold a starter .env and example story.md so you can run abm-auto right away."""
    assets = config.QUICKSTART_DIR
    directory.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[str] = []
    for src_name, dst_name in (("env.template", ".env"), ("story.md", "story.md")):
        dst = directory / dst_name
        if dst.exists():
            skipped.append(dst_name)
            continue
        dst.write_text((assets / src_name).read_text(encoding="utf-8"), encoding="utf-8")
        written.append(dst_name)
    for name in written:
        console.print(f"[green]created[/green] {directory / name}")
    for name in skipped:
        console.print(f"[yellow]skipped (exists)[/yellow] {directory / name}")
    console.print(
        "\nNext: put your key in [bold].env[/bold] (ANTHROPIC_API_KEY=...), "
        "then run [bold]abm-auto run story.md[/bold]."
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -k "quickstart or preflight" -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add abm_auto/quickstart_assets abm_auto/cli.py tests/test_packaging.py
git commit -m "feat(cli): 'abm-auto quickstart' scaffold + friendly missing-API-key preflight"
```

---

## Task 4: Clean-venv build-and-verify script

**Files:**
- Create: `scripts/build_and_verify.sh`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_packaging.py`:

```python
import stat


def test_build_and_verify_script_exists_and_checks_gis():
    root = Path(config.__file__).resolve().parent.parent
    script = root / "scripts" / "build_and_verify.sh"
    assert script.exists()
    assert script.stat().st_mode & stat.S_IXUSR  # executable
    body = script.read_text(encoding="utf-8")
    assert "uv build" in body
    assert "abm_auto/gis" in body  # the leak assertion
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -k build_and_verify -v`
Expected: FAIL — script does not exist.

- [ ] **Step 3: Create `scripts/build_and_verify.sh`**

```bash
#!/usr/bin/env bash
# Build the wheel + sdist and verify the artifact is installable and clean.
# Asserts: CLIs work, bundled data ships and resolves, and gis/ is NOT shipped.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf dist
uv build                                    # sdist + wheel via hatchling
WHEEL=$(ls dist/*.whl)
echo "built: $WHEEL"

# Leak guard: private GIS must never ship.
if unzip -l "$WHEEL" | grep -q "abm_auto/gis"; then
    echo "FAIL: abm_auto/gis present in wheel ($WHEEL)"; exit 1
fi
echo "OK: no gis/ in wheel"

# Clean-venv install of the built wheel.
VENV="$(mktemp -d)/venv"
uv venv "$VENV"
uv pip install --python "$VENV/bin/python" "$WHEEL"

# CLI entry points resolve.
"$VENV/bin/abm-auto" --help >/dev/null
"$VENV/bin/mymomo" --help >/dev/null
echo "OK: abm-auto + mymomo entry points work"

# Bundled data ships and resolves from the installed package.
"$VENV/bin/python" - <<'PY'
from abm_auto import config
for d in (config.PROMPTS_DIR, config.KNOWLEDGE_DIR, config.TEMPLATES_DIR, config.QUICKSTART_DIR):
    assert d.exists() and any(d.iterdir()), f"missing/empty in wheel: {d}"
assert (config.TEMPLATES_DIR / "simulator").exists(), "simulator templates missing"
assert (config.QUICKSTART_DIR / "story.md").exists(), "quickstart story missing"
print("OK: bundled data present in installed wheel")
PY

echo "build_and_verify: PASS"
```

- [ ] **Step 4: Make it executable, run the test**

```bash
chmod +x scripts/build_and_verify.sh
.venv/bin/python -m pytest tests/test_packaging.py -k build_and_verify -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_and_verify.sh tests/test_packaging.py
git commit -m "feat(packaging): clean-venv build_and_verify.sh (CLI + data + gis-leak checks)"
```

---

## Task 5: Gated release workflow

**Files:**
- Create: `.github/workflows/release.yml`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_packaging.py`:

```python
def test_release_workflow_is_gated():
    root = Path(config.__file__).resolve().parent.parent
    wf = root / ".github" / "workflows" / "release.yml"
    assert wf.exists()
    body = wf.read_text(encoding="utf-8")
    assert "build_and_verify.sh" in body
    assert "uv publish" in body
    assert "PYPI_API_TOKEN" in body  # publish gated on the token being configured
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -k release_workflow -v`
Expected: FAIL — workflow file does not exist.

- [ ] **Step 3: Create `.github/workflows/release.yml`**

```yaml
name: release

on:
  push:
    tags: ["v*"]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Build and verify
        run: bash scripts/build_and_verify.sh
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/*

  publish:
    needs: build
    runs-on: ubuntu-latest
    env:
      PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
    steps:
      - name: Skip when no token configured
        if: env.PYPI_API_TOKEN == ''
        run: echo "No PYPI_API_TOKEN — publish-ready, not publishing. Add the secret to enable."
      - uses: actions/checkout@v4
        if: env.PYPI_API_TOKEN != ''
      - uses: astral-sh/setup-uv@v5
        if: env.PYPI_API_TOKEN != ''
      - name: Build
        if: env.PYPI_API_TOKEN != ''
        run: uv build
      - name: Publish to PyPI
        if: env.PYPI_API_TOKEN != ''
        run: uv publish --token "$PYPI_API_TOKEN"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -k release_workflow -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/release.yml tests/test_packaging.py
git commit -m "ci: gated PyPI release workflow (build+verify on tag; publish no-op until token set)"
```

---

## Task 6: README quickstart section

**Files:**
- Modify: `README.md`, `README.zh.md`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_packaging.py`:

```python
def test_readme_documents_pip_install_quickstart():
    root = Path(config.__file__).resolve().parent.parent
    body = (root / "README.md").read_text(encoding="utf-8")
    assert "pip install abm-auto" in body
    assert "abm-auto quickstart" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -k readme -v`
Expected: FAIL — README has no `pip install abm-auto` quickstart.

- [ ] **Step 3: Add a Quickstart section near the top of `README.md`**

Insert after the title/intro (adapt the heading depth to the file):

```markdown
## Quickstart

```bash
pip install abm-auto            # installs the `abm-auto` (and `mymomo`) CLI
abm-auto quickstart             # scaffold a starter .env + example story.md
# edit .env: set ANTHROPIC_API_KEY=...
abm-auto run story.md           # run the full autonomous ABM pipeline
```
```

- [ ] **Step 4: Add the same to `README.zh.md`**

Insert a matching Chinese Quickstart section:

```markdown
## 快速开始

```bash
pip install abm-auto            # 安装 abm-auto（以及 mymomo）命令行
abm-auto quickstart             # 生成起步用的 .env 和示例 story.md
# 编辑 .env：填入 ANTHROPIC_API_KEY=...
abm-auto run story.md           # 运行完整的自主 ABM 流水线
```
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -k readme -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md README.zh.md tests/test_packaging.py
git commit -m "docs: add pip-install Quickstart to README (EN + ZH)"
```

---

## Task 7: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Full packaging suite**

Run: `.venv/bin/python -m pytest tests/test_packaging.py -v`
Expected: all PASS.

- [ ] **Step 2: No regression in the broader suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS / skipped only.

- [ ] **Step 3: Real acceptance — build the wheel in a clean venv**

Run: `bash scripts/build_and_verify.sh`
Expected: ends with `build_and_verify: PASS`; specifically prints `OK: no gis/ in wheel`, `OK: abm-auto + mymomo entry points work`, `OK: bundled data present in installed wheel`. This is the proof the package is actually installable and clean.

---

## Self-Review

**Spec coverage:**
- Path-resolution split (`_PKG_DIR` data root + CWD user paths) → Task 1. ✓
- `runtime_templates/` moved into the package → Task 1 (`git mv`). ✓
- `.env` via `find_dotenv(usecwd=True)`; `WORKSPACE_DIR` CWD + `ABM_WORKSPACE_DIR` → Task 1. ✓
- `PROJECT_ROOT` kept for executor PYTHONPATH → Task 1 (`_PKG_DIR.parent`). ✓
- `mymomo` alias, metadata, version 0.4.0 → Task 2. ✓
- Wheel/sdist excludes incl. `abm_auto/gis` leak guard → Task 2 (+ verified in Task 4 script). ✓
- `quickstart` command + assets (env.template not `.env`) + preflight → Task 3. ✓
- `build_and_verify.sh` (CLI + data + gis-absence in a clean venv) → Task 4. ✓
- Gated `release.yml` → Task 5. ✓
- README EN + ZH quickstart → Task 6. ✓
- Tests no live LLM/network → all in `tests/test_packaging.py`. ✓
- Final build acceptance → Task 7. ✓

**Placeholder scan:** none — every step has real code/commands.

**Type/name consistency:** `_PKG_DIR`, `PROMPTS_DIR`, `KNOWLEDGE_DIR`, `TEMPLATES_DIR`, `QUICKSTART_DIR`, `WORKSPACE_DIR`, `PROJECT_ROOT`, `_require_api_key()`, `quickstart` — all defined in Task 1/3 and used consistently in Tasks 4/6/7 and the script.

**Deviation from spec (noted):** the bundled starter is `.env` + `story.md` only (no separate README file) — the "next steps" are printed by the command instead, reducing clobber surface. The env asset is named `env.template` (written out as `.env`) so the sdist `.env` exclude can't strip it from the wheel.
