# Candidate #10 — Reproduction Bundle (L3 trust-layer artifact)

A single, **reviewer-re-runnable**, content-addressed reproduction of Anshuka et al.
2026 on the real Ba catchment DEM. This is the ADR-023 L3 / ADR-024 ladder-#6 artifact:
locked predictions + a deterministic gate verdict + content fingerprints + provenance,
so a third party can verify the result **without trusting whoever produced it**.

## Headline

**EARNED** — the fidelity test-stone passes (H1 + H2 REPRO; the decisive synthetic-grid
P2 MISS → REPRO on real terrain). Honest scope and the H3/H5 nuances are in FINDINGS.md.

## The bundle (what a reviewer reads)

| File | Role |
|---|---|
| [PREDICTIONS-locked.md](PREDICTIONS-locked.md) | the 6 hypotheses, committed BEFORE the run (the contract) |
| [FINDINGS.md](FINDINGS.md) | the per-hypothesis verdict + honest scope, from the real run |
| [verdict-bundle.json](verdict-bundle.json) | machine-readable: gate Verdicts (value, threshold), data/doc **sha256 fingerprints**, code commit, environment |
| [DATA-acquisition.md](DATA-acquisition.md) | exact public data source + the one-line fetch |
| [design spec](../../superpowers/specs/2026-06-24-anshuka-real-dem-design.md) | the single-variable (geometry-only) design |

## How a reviewer re-runs and verifies (the L3 contract)

```bash
# 1. re-fetch the SAME public input (the bundle records its sha256; data/ is gitignored)
curl -L -o data/anshuka_ba/cop_s18e177.tif \
  https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_S18_00_E177_00_DEM/Copernicus_DSM_COG_10_S18_00_E177_00_DEM.tif
# 2. prep (clip to Ba floodplain, reproject to UTM 60S -> data/anshuka_ba/ba_dem_utm.tif)
#    (rasterio one-liner; see DATA-acquisition.md / the session log)
# 3. re-run — regenerates verdict-bundle.json deterministically
.venv/bin/python examples/reproduce_anshuka_real/run.py
# 4. diff the regenerated bundle against the committed one:
#    - data.ba_dem_utm.sha256 must match (same inputs)
#    - each verdict's passed + salient_number must match (the gate agreed)
git diff docs/reproduce/anshuka-2026-real-dem/verdict-bundle.json

# 5. run the bundle integrity gate (schema + portable paths + committed doc hashes)
.venv/bin/python - <<'PY'
from pathlib import Path
from abm_auto.gis._repro_bundle import repro_bundle_integrity_gate

repo = Path.cwd()
ok, desc = repro_bundle_integrity_gate(
    repo / "docs/reproduce/anshuka-2026-real-dem/verdict-bundle.json",
    repo=repo,
)
print(("PASS" if ok else "FAIL") + ": " + desc)
raise SystemExit(0 if ok else 1)
PY
```

A fabricated or altered result is structurally visible: the data fingerprint won't match,
or a verdict / committed document hash will differ. Trust moves from the generator's word
to a hash + a re-runnable gate (ADR-013 "artifact before conclusion", made
machine-checkable). The integrity gate is deliberately narrower than a rerun: it checks
the package structure, paths, and committed hashes; the reproduction runner checks the
scientific verdicts against the real DEM.

## Honest ceiling (stated, not hidden)

This certifies **auditability, not truth**: "these gates produced these verdicts on inputs
with these hashes, and you can replay to confirm." The refutation-tier verdicts mean
"survived these challenges", never "verified true". Homes/shelters/river are DEM-heuristic
(not real OSM locations), so exact counts are placement-sensitive — the robust claim is the
direction+scale of every magnitude movement and the decisive H2 recovery (see FINDINGS §scope).
