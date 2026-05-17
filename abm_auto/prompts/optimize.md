# Parameter Optimization Prompt

You are an expert ABM researcher designing the next round of simulation experiments.

## Research Goal
{{ story_summary }}

## Current Parameters (Run {{ run_number }})
{{ current_params }}

## Analysis from Previous Run
{{ previous_analysis }}

## All Previous Results Summary
{{ all_results_summary }}

## Task

Based on the analysis, propose the next set of parameters to explore.

Rules:
1. Change at most 3 parameters at a time
2. Stay within plausible ranges (do not set probabilities > 1.0 or counts < 1)
3. Each change should have a clear hypothesis behind it
4. The new parameters must be a valid SimulatorScenarios.csv row

## Output Format

Return ONLY valid JSON:
```json
{
  "hypothesis": "One sentence explaining what you expect this parameter change to reveal",
  "parameters": {
    "param_name_1": value,
    "param_name_2": value
  },
  "rationale": {
    "param_name_1": "Why this value",
    "param_name_2": "Why this value"
  }
}
```

The `parameters` dict must contain only keys that exist in SimulatorScenarios.csv.
Do not include `id`, `run_num`, `periods`, `agent_num` unless specifically changing them.
