# abm-auto

[![Tests](https://github.com/Yco-0314/MyMoMo-Academic/actions/workflows/ci.yml/badge.svg)](https://github.com/Yco-0314/MyMoMo-Academic/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> 📖 English: [README.md](README.md)
>
> 又名 **MyMoMo-Academic**(仓库 / 项目名)。`abm-auto` 是 Python 包与命令行工具;两者指同一系统。

**自主智能体建模研究流水线** —— 一条命令,从自然语言到仿真结果。

`abm-auto` 是一个全自主的 ABM(基于智能体的建模)研究系统:输入一段纯文本研究场景,自动产出可执行仿真、参数探索,以及学术质量的研究报告 —— 全程零人工干预。

## 快速开始

```bash
pip install abm-auto            # 安装 abm-auto(以及 mymomo)命令行
abm-auto quickstart             # 生成起步用的 .env 和示例 story.md
# 编辑 .env:填入 ANTHROPIC_API_KEY=...
abm-auto run story.md           # 运行完整的自主 ABM 流水线
```

## GIS 模式

可选的**空间 ABM 层**(`abm_auto.gis`),面向地理参考模型 —— 道路网络、栅格、多边形、点云,以及把它们耦合起来的算子。它是**附加且导入隔离**的:GIS 相关依赖放在可选 extra 里,基础安装保持轻量。

```bash
pip install abm-auto[gis]
```

它提供地理参考的空间容器(`GeoNetwork`、`RasterSpace`、`PolygonSpace`、`PointSpace`、`RasterTimeline`)、耦合算子(逐边洪水深度、点-边风险、矢量叠加、DE-9IM 谓词)、Mesa 形态的平台层(`GISAgent`/`GISModel`,不依赖 Mesa)、动态模型(拥堵路由、洪水疏散)、空间统计、由代码生成保真门把关的 spec→代码生成,以及栅格/网络验证。完整介绍见 [`abm_auto/gis/README.zh.md`](abm_auto/gis/README.zh.md)。

## 更新内容(v0.3 — 2026-05-31)

横跨三条主线的 10 个提交:**dogfood 覆盖**(originate 模式 + Grid 模型 + 跨域 CI)、**标定诊断**(α 轨迹特征 + β 可辨识性 + ε 执行验证器),以及**多保真标定**基础设施。外加一份替换底层 Melodie 引擎的 5 阶段路线图([ADR-009](docs/decisions/ADR-009-engine-replacement-roadmap.md))。

跨域精简 CI 现在每个领域跑**三道独立质量门**:

1. **MSE 阈值** —— 标定收敛到接近真值
2. **β profile_likelihood** —— 参数逐个可辨识
3. **ε verify_execution** —— 定性方向与 story.md 一致

最新可复现(`seed=42`)基线:

| 领域 | MSE | β | ε |
|---|---|---|---|
| SIR(virus) | 152(≤200) | 全部可辨识 | 全部吻合 |
| Opinion(deffuant) | 0.025(≤0.5) | 全部可辨识 | 全部吻合 |
| Schelling | 0.000(≤0.5) | 全部可辨识 | 全部吻合 |

CI 总墙钟约 6 分钟;`DEEPSEEK_API_KEY` 缺失时 ε 自动跳过(fork PR 保持零 LLM 成本)。

完整历史见 [CHANGELOG.md](CHANGELOG.md)。

## 架构

```
story.md → [设计 Agent] → [编码 Agent] → [验证&修复循环] → [仿真器]
                                                                ↓
              [报告 Agent] ← [优化 Agent] ← [分析 Agent] ← 结果
```

**核心创新**:LLM 驱动的自主研究循环,具备自愈式代码生成、合理性检查、敏感性分析与跨轮记忆。

### 流水线阶段

1. **设计** —— LLM 读 story.md,产出含智能体规格、参数和 ODD 协议的 DESIGN.md
2. **代码生成** —— LLM 据设计生成完整 Python 仿真代码
3. **验证与自愈** —— 自动编译并修错(最多 5 轮重试)
4. **执行** —— 用 MyMoMo Runtime ABM 框架作为运行引擎跑仿真
5. **合理性检查** —— 检测退化输出(常量列、无状态转移)
6. **分析** —— LLM 解读 CSV 结果,提炼洞见
7. **参数优化** —— LLM 提出假设驱动的参数调整
8. **迭代** —— 重复 跑→分析→优化 循环 N 次
9. **敏感性分析** —— 可选的 SALib Morris/Sobol 分析
10. **报告生成** —— 产出结构化研究报告

## 快速开始

```bash
# 1. 安装
cd abm-auto
uv sync

# 2. 设置 API key(Claude 或 DeepSeek)
cp .env.example .env
# 编辑 .env: ANTHROPIC_API_KEY=sk-ant-...
#       或: DEEPSEEK_API_KEY=sk-... + LLM_PROVIDER=deepseek

# 3. 端到端跑一个标定示例(virus-on-a-network SIR —— 约 5 分钟,约 $0.03)
uv run abm-auto run examples/calibration_challenge_virus/story.md \
    --mode reproduce \
    --no-lit-review \
    --iterations 2 \
    --observed examples/calibration_challenge_virus/observed.csv

# 4. 跳过代码生成,用预制仿真器(单独基准标定用)
uv run abm-auto run examples/calibration_challenge_virus/story.md \
    --external-model examples/calibration_challenge_virus/handcrafted_model \
    --observed examples/calibration_challenge_virus/observed.csv

# 5. 快速迭代标定器(快反馈循环,无 LLM)
uv run python benchmark_calibration_lean.py 3
```

## 用法

```bash
# 基本运行
abm-auto run story.md

# 英文论文输出 + 更多迭代
abm-auto run story.md --lang en --iterations 5

# 带文献笔记作上下文
abm-auto run story.md --lit-notes lit_notes.md

# 在已有 workspace 上续跑优化
abm-auto optimize workspace/20241201_143022_abc123/ --iterations 2

# 导入 NetLogo 模型
abm-auto ingest-netlogo ~/models/Virus.nlogo -o examples/virus/story.md

# 从 CoMSES 计算模型库抓取模型
abm-auto ingest-comses "opinion dynamics" -n 5 -o examples/opinion/
```

## 模型导入

`abm-auto` 可自动转换外部来源的模型:

- **NetLogo**(.nlogo/.nlogox)—— 解析代码、滑块、图表和文档为 story.md
- **CoMSES**(comses.net API)—— 抓取模型元数据并生成 story.md

## 已验证模型

流水线已在 15+ 个领域的 **50 个模型** 上测试:

| 领域 | 示例模型 | 成功率 |
|---|---|---|
| 流行病学 | SIR、Virus、HIV、Virus on Network | 100% |
| 生态学 | Wolf Sheep、Rabbits Grass、Daisyworld | 100% |
| 社会科学 | Segregation、Ethnocentrism、Voting、Rebellion | 100% |
| 经济学 | Wealth Distribution、Sugarscape、Hotelling's Law | 100% |
| 博弈论 | PD Evolutionary、Minority Game、Public Goods | 100% |
| 网络科学 | Small Worlds、Preferential Attachment | 100% |
| 观点动力学 | Bounded Confidence、Axelrod Culture | 100% |
| 集体行为 | Flocking、Ants、Termites、Slime | 100% |

## 项目结构

```
abm_auto/
├── agents/          # LLM agent 模块(designer、coder、verifier、analyzer……)
├── analysis/        # 轨迹分析、敏感性分析
├── ingest/          # NetLogo & CoMSES 模型转换器
├── memory/          # 跨轮洞见记忆存储
├── prompts/         # LLM 提示模板
├── runner/          # Workspace 管理 & 仿真执行器
├── pipeline.py      # 主编排器
└── cli.py           # 命令行入口

runtime_templates/   # 仿真代码模板(MyMoMo Runtime 框架)
examples/            # 50+ 已验证模型场景
```

## 配置

环境变量(`.env`):

| 变量 | 说明 | 默认 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude 的 API key | 必填 |
| `ANTHROPIC_BASE_URL` | 自定义 API 端点 | Anthropic 默认 |
| `ABM_MODEL` | 标准 agent 用的模型 | claude-sonnet-4-6 |
| `ABM_STRONG_MODEL` | 设计/编码/报告用的模型 | claude-sonnet-4-6 |

## 许可证

[Apache License 2.0](LICENSE) —— Copyright 2026 Cong Yu。另见 [NOTICE](NOTICE)。
