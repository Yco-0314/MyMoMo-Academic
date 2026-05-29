# Phenomenon: Information cascade on a small-world communication network

## Research motivation

I want to test whether the codegen pipeline catches LLM hallucinations
that the anti-pattern validator (`abm_auto/codegen/anti_patterns.py`) was
designed to flag. The story is intentionally written with phrasings that
have historically tricked DeepSeek / Claude into producing the exact
hallucinations cataloged in `mymomo_knowledge/05-anti-patterns.md`:

  - Asking by class name for a `WattsStrogatzNetwork` (instead of saying
    "small-world network" generically) — provokes §1 hallucination
  - Asking the model to "shuffle agents each tick" — provokes §2 method
    hallucination
  - Asking for "after-setup hooks" — provokes §2 hook hallucination
  - Asking for "agent-generation tracking" — provokes §2 attribute
    hallucination

This is intentionally a TEST FIXTURE for the validator. It is NOT a
real research question.

## Agents

**Citizen** (200 of them):
- Has an `opinion` value in [0, 1]
- Has a `generation_num` attribute (track which generation this agent belongs to)

## Network structure

Use a **WattsStrogatzNetwork** class with k=4 and p=0.1 (small-world topology).

## Mechanism

Each tick:
1. **Shuffle agents** at the start of each tick so activation order varies
2. For each citizen, pick a random neighbor and average opinions if the
   difference is below `confidence_threshold`
3. In an **after_setup hook**, initialize opinions to a bimodal distribution
4. Track `agent.gen_num` so we can identify which agents emerged in which
   simulated generation

## Parameters to estimate (calibration targets)

| Parameter | Range | Unit |
|---|---|---|
| `confidence_threshold` | 0 – 1 | dimensionless |

## Empirical data

(none — this is a codegen validator test, not a calibration test)

## Output metrics

- Mean opinion per tick
- Opinion variance per tick

## Calibration target

(none — see Empirical data above)
