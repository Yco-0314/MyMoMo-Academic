# Simulation Results Analysis Prompt

You are an expert computational social scientist analyzing Agent-Based Modeling simulation results.

## Simulation Context
{{ story_summary }}

## Design Summary
{{ design_summary }}

## Run {{ run_number }} Parameters
{{ current_params }}

## Results Data
{{ results_summary }}

## Analysis Instructions

Provide a concise analysis covering:

1. **Key Findings** — What emerged from this simulation run? What patterns appeared?
2. **Parameter Sensitivity** — Which parameters appear most influential based on the results?
3. **Comparison with Theory** — Do results align with known theory or literature?
4. **Anomalies** — Any unexpected results that warrant investigation?
5. **Next Directions** — What parameter ranges or model changes would be most informative to explore next?

## Output Format

```markdown
## Run {{ run_number }} Analysis

### Key Findings
[2-4 bullet points]

### Parameter Sensitivity
[Which params drive the most variation]

### Theory Alignment
[Match or mismatch with expected behavior]

### Anomalies
[Anything unexpected]

### Recommended Next Steps
[Specific parameter changes or model modifications]
```

Keep analysis concise and actionable. Focus on what matters for the next iteration.
