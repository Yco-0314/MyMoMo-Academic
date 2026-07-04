# PyPI packaging + quickstart — design

**Date:** 2026-06-27
**Status:** Approved (brainstorming) — ready for implementation plan
**Area:** `pyproject.toml`, `abm_auto/config.py`, `abm_auto/runtime_templates/` (moved), `abm_auto/cli.py` (quickstart + preflight), `abm_auto/quickstart_assets/` (new package data), `scripts/`, `.github/workflows/`, `tests/test_packaging.py`, README. Public repo `MyMoMo-Academic`, branch `feat/pypi-packaging` off `v3-substantial`.

## Problem

`abm-auto` is not actually installable as a wheel. `config.py` resolves everything from `PROJECT_ROOT = Path(__file__).parent.parent` (the repo root in a dev tree), which becomes `site-packages/` in an installed wheel. That conflates two different roots:

- **Package data** (`prompts/`, `mymomo_knowledge/`) lives inside `abm_auto/` and happens to resolve, but `runtime_templates/` (used by codegen) lives at the **repo root**, outside the package — so an installed wheel has no `runtime_templates/` and **codegen breaks**.
- **User/runtime paths** (`workspace/` output, `.env`) resolve to `site-packages/workspace` and `site-packages/.env` when installed — wrong place to write, and the user's local `.env` is never found.

There is also a leak risk: an **untracked `gis/`** directory sits in the working tree; a naive build could ship private GIS code to PyPI.

Goal: make `abm-auto` correctly pip-installable, give a smooth first run, and make it **publish-ready** — without actually uploading this round.

## Decisions (locked)

- **Publish scope:** prepare-only. Build + verify + an automated release process; **no upload** (no token needed, zero irreversible risk).
- **Distribution name:** stays `abm-auto`. Add a second console script `mymomo` (same entry point). The `mymomo` PyPI name is **not** claimed.
- **Quickstart:** an `abm-auto quickstart [dir]` scaffold command + a friendly missing-API-key preflight.
- **Version:** bump `0.3.0 → 0.4.0`.

## Design

### 1. Path-resolution split (core) — `abm_auto/config.py`

Separate the two roots explicitly.

- `_PKG_DIR = Path(__file__).resolve().parent` — the installed `abm_auto/` directory. **Package data** resolves from here:
  - `PROMPTS_DIR = _PKG_DIR / "prompts"`
  - `KNOWLEDGE_DIR = _PKG_DIR / "mymomo_knowledge"`
  - `TEMPLATES_DIR = _PKG_DIR / "runtime_templates"`
- `git mv runtime_templates abm_auto/runtime_templates` so the templates ship as package data. `coder.py` reads `config.TEMPLATES_DIR`, so no change there.
- **User/runtime paths** resolve from the current working directory:
  - `WORKSPACE_DIR = Path(os.getenv("ABM_WORKSPACE_DIR", Path.cwd() / "workspace"))` — run outputs land in the user's CWD, never in `site-packages`.
  - `.env`: `load_dotenv(find_dotenv(usecwd=True), override=True)` (search from CWD upward), replacing the pinned `PROJECT_ROOT / ".env"`. `find_dotenv` returns `""` when absent → `load_dotenv("")` is a harmless no-op, so real env vars still work.
- `PROJECT_ROOT` is **kept** (defined as `_PKG_DIR.parent`) only for `executor.py`'s subprocess `PYTHONPATH` (so generated model code can `import abm_auto` — `_PKG_DIR.parent` is `site-packages` when installed and the repo root in dev; both correct). It is **no longer used for data**.

This makes dev (editable) and installed (wheel) behaviour identical for data, and CWD-relative for user output.

### 2. Packaging config — `pyproject.toml`

- Add the alias: `[project.scripts]` gets `mymomo = "abm_auto.cli:app"` alongside `abm-auto`.
- PyPI metadata polish: `keywords`, `classifiers` (Python 3.11/3.12, License :: OSI Approved :: Apache, Topic :: Scientific/Engineering), `[project.urls]` (Homepage/Repository/Issues).
- **Explicit wheel/sdist excludes** to kill the leak risk and keep the artifact clean:
  `[tool.hatch.build.targets.wheel]` and `.sdist` exclude `gis`, `workspace`, `.env`, `**/.DS_Store`, `**/__pycache__`. The wheel `packages = ["abm_auto"]`; `runtime_templates/`, `prompts/`, `mymomo_knowledge/`, `quickstart_assets/` ship because they live under `abm_auto/` (hatchling includes non-`.py` package files by default).
- Bump `version = "0.4.0"`.

### 3. Quickstart UX — `abm_auto/cli.py` + `abm_auto/quickstart_assets/`

- **`abm-auto quickstart [DIR]`** (default `DIR=.`): copies the bundled starter assets into `DIR` — `.env` template (`ANTHROPIC_API_KEY=` + `LLM_PROVIDER=anthropic`), a short self-contained example `story.md` (a classic, well-understood ABM — SIR epidemic on a small network), and a one-line `README` — then prints next steps (`set your key in .env`, then `abm-auto run story.md`). Refuses to overwrite existing files (warns + skips) so it's safe to re-run.
- Assets live in `abm_auto/quickstart_assets/` (package data, ship in the wheel); the command reads them via `config`-style `_PKG_DIR` resolution.
- **Missing-key preflight:** a small check used by `run` (and any command that needs the LLM) — if `config.get_api_key()` is empty, print a friendly message (`No API key found. Set ANTHROPIC_API_KEY in your environment or .env — run 'abm-auto quickstart' for a starter.`) and `raise typer.Exit(1)` BEFORE constructing the pipeline, instead of failing deep in the SDK.

### 4. Build + verify (the publish-ready core)

- **`scripts/build_and_verify.sh`:** `python -m build` (sdist + wheel via hatchling) → create a clean throwaway venv → `pip install dist/*.whl` → assert: `abm-auto --help` and `mymomo --help` exit 0; the installed package's `config.PROMPTS_DIR / KNOWLEDGE_DIR / TEMPLATES_DIR` exist and are non-empty; and **`gis/` is absent from the wheel** (`unzip -l dist/*.whl | grep -q gis` must fail) — the leak check. Non-zero exit on any failure.
- **`.github/workflows/release.yml`:** on tag push (`v*`), build + run the verify checks; an upload job is present but **gated** (runs only if a `PYPI_API_TOKEN` secret / trusted-publishing is configured, which it is not yet) — so the repo is publish-ready and the user flips it on later.

### 5. Testing — `tests/test_packaging.py` (no live LLM, no network)

- Path resolution: `config.PROMPTS_DIR`, `KNOWLEDGE_DIR`, `TEMPLATES_DIR` are under `_PKG_DIR` (inside `abm_auto/`) and exist; `WORKSPACE_DIR` is CWD-relative (and honours `ABM_WORKSPACE_DIR`).
- Data presence: the three data dirs contain their expected files (e.g. `analyze.md` under prompts).
- `quickstart`: invoking it (CliRunner) into a `tmp_path` writes `.env`, `story.md`, `README`; re-running does not clobber; the example `story.md` is non-empty.
- Preflight: with the API key env cleared (monkeypatch), `run` prints the friendly message and exits non-zero **without** importing/constructing the pipeline.
- (The wheel-build leak check lives in `scripts/build_and_verify.sh`, not pytest, to avoid build/venv deps in the unit suite. A lightweight source-tree test asserts the pyproject excludes list contains `gis`.)

### 6. Security / leak guardrails

- pyproject excludes (`gis`, `workspace`, `.env`, `.DS_Store`, `__pycache__`) + the verify script's `gis`-absent assertion + a pytest asserting the exclude is configured.
- The standing pre-push scan (no secrets / private-fork refs / abs paths / strategy ADRs) still runs before any push.

### 7. README

Add a concise **Quickstart** section: `pip install abm-auto` → `abm-auto quickstart` → set key in `.env` → `abm-auto run story.md`. Mirror one line into `README.zh.md`.

## Error handling

- Missing API key → friendly preflight message + exit 1 (not an SDK stack trace).
- `quickstart` into a non-empty dir → warn and skip existing files; never overwrite.
- Missing data dir at runtime (corrupt install) → the existing loaders raise a clear `FileNotFoundError` with the resolved path; the verify script catches this class of breakage before release.

## Non-goals

- Actually uploading to PyPI/TestPyPI this round.
- Claiming the `mymomo` distribution name.
- GIS packaging (GIS stays private / on `v4-GIS`).
- Refactoring data access to `importlib.resources` (filesystem `Path` access is sufficient for an unpacked wheel; revisit only if zip-import is ever needed).

## Where it lives

- `abm_auto/config.py` (path split), `abm_auto/runtime_templates/` (moved into package), `abm_auto/cli.py` (`quickstart` + preflight), `abm_auto/quickstart_assets/` (new), `pyproject.toml` (alias, metadata, excludes, version), `scripts/build_and_verify.sh`, `.github/workflows/release.yml`, `tests/test_packaging.py`, `README.md` + `README.zh.md`.
- Branch `feat/pypi-packaging` off `v3-substantial`.
