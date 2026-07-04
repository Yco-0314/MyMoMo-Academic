# Anshuka Prior-Experience Gate Phase 1

## Summary

Add the missing P5 mechanism knob described in the Anshuka reproduction findings:
when an uninformed agent receives flood information through social interaction,
acting on that information can be gated by prior flood experience.

This phase adds the mechanism as an explicit, default-off parameter. It does not
rewrite the locked synthetic or real-DEM reproduction, and it does not change the
published verdict bundle.

## Scope

- Extend `AgentState` with optional prior-experience state.
- Add `prior_experience_frac: Optional[float] = None` to the shared Anshuka
  scenario mechanism.
- Preserve byte-identical legacy behavior when `prior_experience_frac is None`.
- When `prior_experience_frac` is provided, social collaboration uptake requires
  both:
  - the existing belief draw; and
  - the agent having prior experience.
- Expose the same optional parameter from `run_scenario(...)`,
  `run_scenario_real(...)`, and the `mean_outcome*` wrappers through `**kwargs`.
- Add a deterministic gate proving prior-experience gating reduces the
  collaboration lift on synthetic truth.

## Non-Goals

- No change to existing locked Anshuka verdicts.
- No claim that P5 is now fully reproduced on real Ba.
- No calibration against the paper's figures.
- No road traffic, evacuation-flow, congestion, or social-network realism claim.
- No edits to `abm_auto/runtime/`, `abm_auto/codegen/`, `abm_auto/calibration/`,
  `abm_auto/agents/`, or `abm_auto/pipeline/`.

## API

`prior_experience_frac=None` keeps the current behavior exactly.

`prior_experience_frac=0.0` means social information is heard but no agent has the
prior experience needed to act on it. Collaboration should therefore have little
or no effect compared with collaboration off, apart from randomness already
introduced by the explicit new mechanism path.

`prior_experience_frac=1.0` means every agent passes the prior-experience gate, so
social uptake behaves close to the legacy collaboration mechanism.

Add:

`prior_experience_collaboration_gate(...) -> tuple[bool, str]`

The gate compares:

- legacy/default collaboration lift;
- prior-experience-gated collaboration lift.

It passes only when gated social uptake reduces the collaboration effect relative
to the legacy/default path and reports the boundary: this is P5 mechanism
evidence, not a real-data reproduction fix.

## Tests

Extend or add tests covering:

- default `run_scenario(...)` golden behavior stays unchanged;
- with `prior_experience_frac=0.0`, collaboration on/off has materially reduced
  lift compared with legacy/default collaboration;
- `prior_experience_frac` rejects values outside `[0, 1]` and booleans;
- `run_scenario_real(...)` forwards the optional parameter without changing its
  default behavior;
- `prior_experience_collaboration_gate(...)` passes and emits cautious wording.

## Verification

Run:

```bash
.venv/bin/python -m pytest tests/gis/test_anshuka_prior_experience.py tests/gis/test_anshuka_real.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```
