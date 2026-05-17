# ODD Protocol Generation Prompt

You are an expert ABM modeler. Generate a complete **ODD Protocol** document (Grimm et al. 2020) based on the DESIGN.md below.

ODD is the standard description protocol for Agent-Based Models, required for publication.

## DESIGN.md
{{ design }}

---

## Output Format

Produce a complete `ODD.md` with exactly these 7 sections:

```markdown
# ODD Protocol: {{ project_name }}

> Grimm, V. et al. (2020). The ODD Protocol for Describing Agent-Based and Other Simulation Models.
> *JASSS*, 23(2), 7. https://doi.org/10.18564/jasss.4259

---

## 1. Purpose and Patterns

### 1.1 Purpose
[What question does this model address? What system does it represent?]

### 1.2 Patterns
[What emergent patterns should the model reproduce to be considered valid?
E.g. "epidemic curve should be unimodal", "segregation index should increase over time"]

---

## 2. Entities, State Variables, and Scales

### 2.1 Agents
| Entity | State Variables | Range / Type |
|--------|----------------|--------------|
| [AgentName] | [attribute] | [type, range] |

### 2.2 Environment
| Variable | Description | Range / Type |
|----------|-------------|--------------|

### 2.3 Scales
- **Temporal**: [time step unit, total duration]
- **Spatial**: [grid size or network size, if applicable]

---

## 3. Process Overview and Scheduling

Each time step, processes execute in this order:

1. [Process 1] — [who executes it, what it does]
2. [Process 2] — ...
3. [Data collection] — environment-level metrics recorded

[Note any synchronous vs. asynchronous updating]

---

## 4. Design Concepts

| Concept | Present? | Description |
|---------|----------|-------------|
| **Emergence** | Yes/No | [What macro-level patterns emerge from micro-level rules?] |
| **Adaptation** | Yes/No | [Do agents change behavior based on local conditions?] |
| **Objectives** | Yes/No | [Do agents have explicit goals to maximize/minimize?] |
| **Learning** | Yes/No | [Do agents update strategies over time?] |
| **Prediction** | Yes/No | [Do agents anticipate future states?] |
| **Sensing** | Yes/No | [What can agents perceive about their environment/neighbors?] |
| **Interaction** | Yes/No | [How do agents interact — direct/indirect, local/global?] |
| **Stochasticity** | Yes/No | [What processes are probabilistic? What seed is used?] |
| **Collectives** | Yes/No | [Are there groups or aggregates of agents?] |
| **Observation** | Yes/No | [What data is collected and how?] |

---

## 5. Initialization

- **Population size**: [N agents]
- **Initial state distribution**: [How are initial attribute values assigned]
- **Random seed**: [Fixed / variable across runs]
- **Input files**: [SimulatorScenarios.csv columns and default values]

---

## 6. Input Data

[Does the model use time-series or empirical data during the run?]
- If No: "The model does not use external time-series data. All parameters are set in SimulatorScenarios.csv."
- If Yes: [Describe each input file, source, and how it is used]

---

## 7. Submodels

For each process listed in Section 3, provide a precise description:

### 7.X [Process Name]
**Purpose**: [What does this process represent?]
**Equation / Algorithm**:
```
[Pseudocode or mathematical formula]
```
**Parameters**: [Which scenario parameters govern this process]
**References**: [If based on published model, cite it]
```

Fill in all sections completely based on the DESIGN.md. Use precise language suitable for a peer-reviewed journal submission.
