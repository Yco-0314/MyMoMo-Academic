# Knowledge Base — Source Record

This directory contains reference documentation used by the abm-auto pipeline's LLM agents
to improve code generation quality.

## Origin

- **Source repository**: https://github.com/ABM4ALL/melodie-skills
- **Source path**: `skills_en/melodie-reference/`
- **License**: MIT (see LICENSE file in this directory)
- **Copied**: 2026-04-23
- **Commit SHA**: `main` branch at time of copy (ABM4ALL/melodie-skills)

## File Mapping

| This file | Original file |
|---|---|
| `runtime-framework.md` | `melodie-framework.md` |
| `runtime-quickref.md` | `melodie-quickref.md` |
| `runtime-code-templates.md` | `melodie-code-templates.md` |
| `runtime-data-guide.md` | `melodie-data-guide.md` |
| `tab2dict-guide.md` | `tab2dict-guide.md` (unchanged) |
| `abm-agent-design.md` | `abm-agent-design.md` (unchanged) |
| `abm-suitability.md` | `abm-suitability.md` (unchanged) |
| ~~`change-impact.md`~~ | Moved to `docs/change-impact.md` — human reference only, not loaded by LLM agents |
| `modules/module-grid.md` | `modules/module-grid.md` (unchanged) |
| `modules/module-network.md` | `modules/module-network.md` (unchanged) |
| `modules/module-calibrator.md` | `modules/module-calibrator.md` (unchanged) |
| `modules/module-trainer.md` | `modules/module-trainer.md` (unchanged) |

## Usage

These documents are loaded by the LLM agents in abm-auto as internal reference context.
They are **not** part of the public API and are never shown to end users directly.

The runtime referenced in these docs maps to `abm_auto.runtime` (see `abm_auto/runtime/__init__.py`).
When these docs refer to `from Melodie import X`, in generated code always use
`from abm_auto.runtime import X` instead.
