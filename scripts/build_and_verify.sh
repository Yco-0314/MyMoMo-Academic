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
