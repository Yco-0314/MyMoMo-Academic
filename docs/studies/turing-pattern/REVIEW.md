# Turing diffusion-driven instability (Gierer-Meinhardt) — review

**tier: minimal** (all-REPRO 3/3, comfortable margins; no MISS). Reaction-diffusion CA.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (patterned CoV 1.06, |Δk|/k* 0.046, stationarity 0.0005) matches bundle/results.
- fair-control: **pass** — P1 is a clean A/B: the SAME kinetics with Dv/Du=1 (or diffusion off) stay homogeneous (control CoV<0.05) vs the Turing regime that patterns (CoV 1.06).
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; L3 gate ok.
- mechanism-aliveness: **pass** — the diffusion-DRIVEN instability is alive: stable-without-diffusion → patterned-with-diffusion, and the emergent wavelength matches the linear dispersion relation (k* derived from the Jacobian + diffusion, then compared to the measured spectral peak).
- framing-disclosure: **pass** — reaction-diffusion PDE on a grid (CA), disclosed.

## Verdict: SOUND. 3/3 REPRO.
P1 diffusion-driven instability gate (homogeneous control CoV≈0 vs patterned CoV 1.06); P2 wavelength
matches the dispersion relation (|k_meas−k*|/k* = 0.046 ≤ 0.35); P3 stationary non-oscillatory pattern
(amplitude flat 0.0005). Turing's central claim — a system stable to uniform perturbations goes unstable
under diffusion (inhibitor faster than activator) to a wavelength-selected pattern — reproduces. 23 tests.
Built by a builder that completed before a process restart; verified + committed centrally. No tuning.

REVIEW COMPLETE
