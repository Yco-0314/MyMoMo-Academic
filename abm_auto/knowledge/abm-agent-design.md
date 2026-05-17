# ABM Agent Design Patterns

> Internal reference for LLM design and code generation agents.
> Original: abm-agent-design.md from ABM4ALL/melodie-skills (MIT).

## Core Principle

> "The aesthetics of ABM lies in: producing rich macro phenomena through interaction
> mechanisms with the **simplest possible** agent behavior."

More complex agents risk obscuring whether outcomes stem from individual intelligence
or from the interaction rules themselves. Start simple; add complexity only when the
research question explicitly demands it.

## Four Patterns (Increasing Complexity)

### 1. Zero-Intelligence
Agents act randomly with no decision-making logic.
- **Purpose**: Isolate whether macro patterns emerge from mechanisms alone, not intelligence.
- **When to use**: Baseline / benchmark; testing whether interaction rules drive the phenomenon.
- **Implementation**: `step()` selects actions uniformly at random.

### 2. Reactive ⭐ (Most common in ABM)
Agents respond to current state using **fixed behavioral rules**.
- **Purpose**: Examine how heterogeneity and local rules produce macro outcomes.
- **When to use**: Default choice unless research explicitly needs expectation-formation or learning.
- **Rules range**: From simple if-else to complex response functions.
- **Implementation**: `step()` reads `self.state` and environment signals, applies rule, updates state.

```python
def step(self):
    if self.state == SUSCEPTIBLE and self.infected_neighbours > 0:
        if random.random() < self.infection_prob:
            self.state = INFECTED
```

### 3. Deliberative
Agents form **future expectations** then optimise.
- **Purpose**: Model expectation-formation (moving averages, adaptive forecasts).
- **When to use**: Research question focuses on how agents predict and plan ahead.
- **Caution**: Computationally heavy; may obscure the role of interaction mechanisms.
- **Implementation**: `step()` maintains a history buffer, computes forecast, selects action to maximise expected utility.

### 4. Introspective
Agents **modify their own behavioral rules** during simulation (online learning).
- **Purpose**: Study behavioral evolution, adaptive strategies.
- **When to use**: Research question is explicitly about learning / rule adaptation.
- **Implementation**: Genetic algorithm over behavioral parameters (→ use Trainer module),
  or reinforcement learning (custom `step()` that updates policy weights).

## Pattern Selection Logic

```
Research goal?
├── "Do macro patterns emerge from rules alone?" → Zero-intelligence baseline
├── "How does heterogeneity affect outcomes?" → Reactive
├── "How do agents form expectations?" → Deliberative
└── "How do strategies evolve over time?" → Introspective
```

**Default recommendation**: Start with **Reactive**. Upgrade only if the research question
explicitly requires it and you can justify the added complexity.

## AI-ASSUMPTION Rule for Agent Design

When the DESIGN.md doesn't specify a pattern, default to **Reactive** and tag:
```python
# ⚠️ AI-ASSUMPTION: Using reactive pattern (fixed rules).
#    DESIGN.md does not specify agent intelligence level.
```
