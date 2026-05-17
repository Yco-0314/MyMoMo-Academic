# Academic Paper Generation Prompt

You are an expert computational social scientist writing an ABM research paper for submission to a peer-reviewed journal (JASSS, CMOT, or Complexity).

## Research Context
{{ story_summary }}

## Model Design
{{ design_summary }}

## Simulation Results ({{ total_runs }} runs)
{{ all_runs_summary }}

## Parameter Evolution
{{ params_history }}

## Task

Write a complete academic research paper following IMRAD (Introduction, Methods, Results, And Discussion) structure. Target journal: JASSS (Journal of Artificial Societies and Social Simulation).

## Paper Structure

```markdown
# [Descriptive Title]: An Agent-Based Modeling Approach

## Abstract
[150-250 words. Background → Gap → Method → Key findings → Implications]

## 1. Introduction
### 1.1 Research Problem
[Motivate the research question with real-world significance]
### 1.2 Why Agent-Based Modeling?
[Justify ABM over equation-based or statistical approaches — micro-macro link, heterogeneity, emergence]
### 1.3 Research Contributions
[Explicitly state 2-3 contributions to theory, method, or empirical understanding]

## 2. Literature Review
### 2.1 Theoretical Background
[Position the work within relevant theoretical frameworks]
### 2.2 Related ABM Studies
[Review prior ABM work on this topic — what has been done, what gaps remain]
### 2.3 Research Gap
[Derive the specific gap this paper addresses]

## 3. Model Description (ODD Protocol)
### 3.1 Purpose and Patterns
### 3.2 Entities, State Variables, and Scales
### 3.3 Process Overview and Scheduling
### 3.4 Design Concepts
[Emergence, Adaptation, Objectives, Learning, Prediction, Sensing, Interaction, Stochasticity, Collectives, Observation]
### 3.5 Initialization
### 3.6 Input Data
### 3.7 Submodels

## 4. Experimental Design
### 4.1 Parameter Space
[Table of parameters, ranges, and justification for values]
### 4.2 Simulation Protocol
[Number of runs, iterations, convergence criteria]
### 4.3 Sensitivity Analysis
[Method (Morris/Sobol), sample size, metric selection]

## 5. Results
### 5.1 Baseline Dynamics
[What happens under default parameters?]
### 5.2 Parameter Sensitivity
[Which parameters drive model behavior? Use SALib indices.]
### 5.3 Emergent Patterns
[Trajectory clustering results — what behavioral modes exist?]
### 5.4 Critical Transitions
[Phase transitions, tipping points, path dependence]

## 6. Discussion
### 6.1 Interpretation of Findings
[What do the results mean theoretically?]
### 6.2 Comparison with Prior Work
[How do findings relate to existing literature and theory?]
### 6.3 Validation Against Baseline
{{ baseline_comparison }}
### 6.4 Implications
[Theoretical and practical implications]
### 6.5 Limitations
[Model assumptions, parameter choices, scope boundaries]

## 7. Conclusion
[Summary of contributions, key takeaway, future directions. One concise paragraph.]

## References
{{ citations }}
```

## Writing Guidelines
- Use precise, formal academic English throughout
- Include specific numerical results (means, standard deviations, sensitivity indices)
- Every claim must be supported by simulation evidence
- Distinguish between correlation and causation
- Acknowledge limitations honestly
- Target word count: 5000-7000 words
