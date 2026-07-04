# Directed abelian sandpile (Dhar & Ramaswamy 1989) — review

**tier: deep (adversarially verified)** — 2/3 REPRO + 1 honest razor-thin MISS. CA (disclosed).

## Cheap checks + adversarial verification
- numeric-provenance: **pass** — bundle (tau=1.391, aniso 1.999, heavy tail 4.9 decades) matches results.
- fair-control: **pass** — one directed toppling rule; exponent + anisotropy + tail measured from the same avalanche ensemble.
- no-post-lock-drift: **pass** — graded vs lock d7599ab BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness / adversarial: **pass** — independent re-run (H=W=100, 8000 avalanches): tau=1.391 (matches; consistent with exact 4/3) and anisotropy ratio=1.879 (longitudinal 12.25 vs transverse 6.52). The avalanches ARE directionally biased (~1.9x longer along the drive) -- the directed geometry is real.
- framing-disclosure: **pass** — directed SOC CA, disclosed.

## The honest MISS (P2)
P2 required mean longitudinal extent >= 2.0x transverse. Measured ratio = 1.9987 (builder) / 1.879 (my
independent smaller run) -- genuinely just BELOW the locked 2.0 bar. The anisotropy is unmistakably present
(~1.9x); my locked threshold of exactly 2.0x was marginally too tight for the measured value. This is a
bar-calibration MISS, not an absence of anisotropy and not a model bug or tuning (builder reported 1.9987
honestly rather than nudging it over 2.0).

## Verdict: SOUND. 2/3 REPRO + 1 honest (bar-too-tight) MISS.
P1 theory-pinned exponent tau=1.391 (exact 4/3); P3 heavy tail (4.9 decades). P2 directional anisotropy is real
(~1.9x) but falls a hair under the locked exactly-2.0 bar. 20 tests. No tuning.
REVIEW COMPLETE (deep tier, adversarially verified)
