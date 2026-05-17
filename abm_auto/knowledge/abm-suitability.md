# ABM Suitability Assessment

> Internal reference for LLM design agents (phase1_design).
> Original: abm-suitability.md from ABM4ALL/melodie-skills (MIT).

## Core Definition

ABM explicitly models **how micro-level behavior gives rise to macro-level outcomes**.
This two-layer structure differentiates it from:
- System Dynamics (macro-only)
- Representative-agent macroeconomic models

## Structural Requirements (Both Necessary)

1. **Distinguishable micro and macro levels** — individual agents with heterogeneous
   states/decisions AND observable aggregate phenomena
2. **Research question requires modeling both levels** — the question is about the
   micro→macro connection, not just macro trends

## Three Motivations (At Least One Required)

| Motivation | Signal | Key question |
|---|---|---|
| **Interaction-driven** | Complex emergent phenomena, feedback loops | "Would predictions change if we removed agent interactions?" |
| **Heterogeneity-driven** | Strong distributional differences among agents | "Would a representative agent miss critical dynamics?" |
| **Bounded rationality** | Agents use heuristics / learning, not global optimisation | "Do agents adapt their rules during the simulation?" |

## When NOT to Use ABM

| Situation | Better alternative |
|---|---|
| No true micro-macro structure | Analytical methods |
| Focus only on macro equilibrium | CGE, game theory |
| Only macro trend analysis needed | System Dynamics, regression |
| Optimisation is the goal | Operations research |
| Agents don't interact; distribution unimportant | Macro statistical models |
| Abundant historical data + prediction goal | ML, time series |

## Decision Table (for LLM design agent)

```
STORY.md contains ...                     → Judgment
─────────────────────────────────────────────────────
"agent", "individual", "heterogeneous",
"emergence", "interaction" + research
question asks about micro-macro link       → ABM suitable; proceed

Two-level structure but weak motivation    → Flag assumption; note alternative

No clear micro-macro structure             → AI-ASSUMPTION: proceeding as ABM
                                             because story.md was explicitly
                                             submitted as an ABM scenario

Explicit ABM/Melodie mention              → Skip assessment; proceed directly
```

## For abm-auto (Autonomous Mode)

Stories submitted to abm-auto are **by definition intended as ABM scenarios**.
Skip suitability debate; instead use this checklist to verify the story is
**complete enough** to design from:

- [ ] Agent types identified
- [ ] Interaction mechanism described
- [ ] Time structure implied
- [ ] At least one output metric mentioned
