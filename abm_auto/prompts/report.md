# Final Report Generation Prompt

You are an expert computational social scientist writing up an ABM simulation study.

## Research Question
{{ story_summary }}

## Model Design Summary
{{ design_summary }}

## Calibration Parameters (declared units — DO NOT misinterpret)
{{ param_units_block }}

When discussing parameter values in the report, you MUST honor the units
above. For example, if a parameter is declared in `percent` and its value
is 4.4, that means 4.4% (probability 0.044), NOT 4.4 as a probability.
Misreading percent values as probabilities has caused embarrassing
mis-explanations in past reports.

## All Simulation Runs ({{ total_runs }} runs)
{{ all_runs_summary }}

## Parameter Evolution
{{ params_history }}

## Hard Constraint — Iteration Count
{{ iteration_constraint }}

## Task

Write a concise research report in Chinese (中文) covering the full simulation study.

## Report Structure

```markdown
# [Model Name] 仿真研究报告

## 研究背景与目的
[研究问题、动机、ABM方法的选择理由]

## 模型设计
[Agent定义、环境设置、关键参数]

## 实验设计
[{{ total_runs }}轮迭代的参数变化逻辑]

## 主要发现
[跨所有迭代的核心结论，涌现规律]

## 参数敏感性分析
[哪些参数对结果影响最大]

## 与已有研究的对比
[结果是否符合理论预期，有何新发现]

## 局限性与未来工作
[当前模型的假设和局限，下一步可以做什么]

## 结论
[一段话总结]
```

Write in academic but accessible style. Use specific numbers from the results data.
