# ABM 模型设计文档 — 复现

**状态**: 草稿
**模式**: 复现

---

## 第0部分: 源论文参考

- **引用**: Yaman, Tian & Lindström, "Semantic knowledge guides innovation and drives cultural evolution", PNAS 2026
- **DOI / URL**: [未提供]
- **要复现的核心主张**: 拥有语义知识（通过小神经网络建模）的智能体在组合创新任务中表现优于没有语义知识的智能体；语义知识与社会学习协同作用，加速累积文化进化。
- **保真度目标**: 复现论文中的定性发现：(1) 语义知识提升创新成功，(2) 语义知识与社会学习相互作用产生放大效应，(3) 语义优势在不同人口规模下持续存在。
- **允许的偏差**: 随机种子、参数扫描的具体步长可调整；复现运行次数（为均值）可设为 10 次（论文未明确说明，此为标准做法）。

---

## 第一部分: 需求

### 1. 模型概述

- **项目名称**: `SemanticInnovation`
- **原始故事**: 复现 Yaman, Tian & Lindström (PNAS 2026) 的智能体模型，其中人口进行组合创新任务，智能体携带预测有用组合的语义知识。
- **目标**: 复现论文的定性结果——语义知识提高创新成功率，并与社会学习协同作用加速累积文化进化。
- **模式**: 仿真器
- **可视化器**: 是——按代际追踪人口平均累积创新数量

### 2. 智能体

- **智能体类**: `InnovatorAgent`
    - **属性**:
        - `inventory: list` — 初始为 6 个基础物品 `[story]`
        - `memory: list` — 已尝试过的配方记录（成功的和失败的）`[story]`
        - `age: int` — 代际数，从 0 开始 `[story]`
        - `score: int` — 已发现的创新数量 `[story]`
        - `semantic_model: FeedforwardLearner` — 1个隐藏层（16个神经元），ReLU激活，softmax输出，输入物品嵌入 `[story]`
        - `embeddings: dict` — 每个物品（由整数索引）到 16 维向量的映射 `[story]`
        - `alive: bool` — 表示智能体是否存活 `[AI-ASSUMPTION: 标准 ABM 实践，人口周转需要]`
    - **方法**:
        - `setup()`: 初始化属性 `[story]`
        - `step()`: 执行一次创新尝试（算法 2）`[story]`
        - `retrain_model()`: 对所有成功配方用反向传播训练语义模型 `[story]`
        - `die_probability()`: 返回基于年龄的死亡概率 `[story]`
    - **初始化**: 所有 100 个智能体从 6 个基础物品开始，空记忆，年龄=0，分数=0，随机初始化的语义模型和嵌入。`[story]`

### 3. 空间与环境

- **空间结构**: 无拓扑（无空间/网络结构）`[story: 智能体不与邻居交互，它们观察全局环境（最高得分智能体的清单）]`
- **网格规格 / 网络规格**: 不适用
- **环境逻辑**: 全局步进行为（算法 1）：
    1. 每个智能体执行固定数量的创新尝试（论文未说明具体数量，假设为 10 次 `[AI-ASSUMPTION: 未在 STORY 中找到]`）
    2. 智能体重新训练语义模型
    3. 基于年龄的死亡
    4. 死亡智能体被替换为高得分父母的子代
    5. 环境追踪：总人口创新数量、平均分数 `[story]`

### 4. 优化

- 跳过——源论文使用手动参数扫描（探索 {0, 0.1, 0.5, 0.9} 的组合），不进行自动校准。`[story]`

### 5. 数据

- **输入**: `SimulatorScenarios.csv`，列：`P_S`, `P_SL`, `P_G`, `population_size`, `innovation_attempts_per_generation`, `max_generations`, `semantic_cost_multiplier`
- **输出**: `Result_Simulator_Environment` — 按代际和/或参数组合的人口平均创新数量 `[story]`

### 6. 计算

- **并行核心**: 4（合理默认值）
- **并行模式**: process

---

## 第二部分: 技术规格

### 1. 文件结构

- `core/agent.py`: `InnovatorAgent`
- `core/model.py`: `SemanticInnovationModel`
- `core/environment.py`: `InnovationEnvironment`
- `core/scenario.py`: `InnovationScenario`
- `core/data_collector.py`: `InnovationDataCollector`
- `main.py`: 入口点

### 2. 类接口

#### Agent

```python
class InnovatorAgent(Agent):
    def setup(self):
        self.inventory = [f"base_{i}" for i in range(6)]  # 6个基础物品 [story]
        self.memory = []  # 配方记录 [story]
        self.age = 0  # [story]
        self.score = 0  # [story]
        self.alive = True  # [AI-ASSUMPTION]
        # 语义模型: 16维输入 -> 16个隐藏单元 -> 物品数量输出 [story]
        # 在 setup 中初始化，初始物品数量（6）= 输出维度
        self.semantic_model = self._init_semantic_model()
        self.embeddings = {i: np.random.randn(16) for i in range(6)}  # [story]

    def step(self):
        # 算法 2 [story]
        # 1. 决定策略：随机/语义/泛化
        # 2. 选择一个策略
        # 3. 尝试配方
        # 4. 如果新配方有效，添加到库存
        # 5. 将尝试加入记忆

    def retrain_model(self):
        # 使用所有成功配方训练语义模型 [story]
        # 配方：输入=一个物品嵌入，输出=互补物品（或多种） [story]

    def die_probability(self):
        # 基于年龄的概率 [story]
        return min(1.0, self.age * 0.01)  # [AI-ASSUMPTION: 未指定确切函数]
```

#### Model

```python
class SemanticInnovationModel(Model):
    def create(self):
        self.agents = self.create_agent_list(InnovatorAgent)
        self.environment = self.create_environment(InnovationEnvironment)
        self.data_collector = self.create_data_collector(InnovationDataCollector)

    def setup(self):
        self.agents.setup_agents(agents_num=self.scenario.population_size)  # [story]

    def run(self):
        for t in self.iterator(self.scenario.max_generations):  # [story]
            # 1. 个体创新阶段 [story]
            for agent in self.agents:
                # 社会学习机会 [story]
                if np.random.rand() < self.scenario.P_SL:
                    self._social_learn(agent)
                else:
                    for _ in range(self.scenario.innovation_attempts_per_generation):
                        agent.step()
            
            # 2. 重新训练语义模型 [story]
            for agent in self.agents:
                agent.retrain_model()
            
            # 3. 死亡与更替（Moran过程）[story]
            self._moran_turnover()
            
            # 4. 收集数据 [story]
            self.data_collector.collect(t)
        
        self.data_collector.save()

    def _social_learn(self, agent):
        # 检查最高得分智能体的库存 [story]
        # 如果可以，复制配方

    def _moran_turnover(self):
        # 杀死基于年龄的智能体 [story]
        # 用更替补充 [story]
```

### 3. 数据输入计划

- **SimulatorScenarios.csv 列**:
    - `P_S`: 使用语义模型的概率 {0.0, 0.1, 0.5, 0.9} `[story]`
    - `P_SL`: 社会学习概率 {0.0, 0.1, 0.5, 0.9} `[story]`
    - `P_G`: 在语义尝试中使用泛化的概率 {0.0, 0.1, 0.5, 0.9} `[story]`
    - `population_size`: 智能体数量 (25, 50, 100) `[story]`
    - `innovation_attempts_per_generation`: 每次尝试次数 (10 份假设) `[AI-ASSUMPTION]`
    - `max_generations`: 总代数 (100 份假设) `[AI-ASSUMPTION]`
    - `semantic_cost_multiplier`: 语义成本的乘数 (1.0, 3.0) `[story]`

### 4. 输出数据

- `Result_Simulator_Agent`: 代理ID、代际、分数、年龄、库存大小 `[story]`
- `Result_Simulator_Environment`: 代际、平均分数、总库存大小、参数组合 `[story]`

### 5. 源头追踪

| 元素 | 来源 | 详情 |
|---|---|---|
| 1. 智能体 | [story] | 100 个智能体，库存、记忆、年龄、分数、语义模型、嵌入 |
| 2. 交互 | [story] | 无拓扑——通过环境进行全局社会学习（检查最高得分智能体库存） |
| 3. 时间 | [story] | 离散代际；每个代理每代进行多次创新尝试 |
| 4. 初始化 | [story] | 所有代理以 6 个基础物品开始，空记忆，年龄=0，随机语义模型 |
| 5. 决策 | [story] | 算法 2——随机、语义或泛化策略取决于 P_S、P_SL、P_G |
| 6. 场景 | [story] | P_S、P_SL、P_G 在 {0, 0.1, 0.5, 0.9} 中；人口规模在 {25, 50, 100} 中 |
| 7. 校准 | [story] | 无——手动参数扫描 |
| 8. 输出 | [story] | 按代际的人口平均创新数量 |

### 6. 假设（AI-ASSUMPTION——最后手段）

1.  **每次尝试的创新尝试次数**：10 次
    - 来源检查: 故事中静默 | lit_notes 中静默 | 未发现《SemanticInnovation》的规范默认值
    - 理由: 需要固定数量以确保计算可管理；10 次是合理的初步选择。

2.  **最大代数**：100 代
    - 来源检查: 故事中静默 | lit_notes 中静默 | 未发现规范默认值
    - 理由: 需要上限；100 代应该足以让文化演化显现。

3.  **死亡概率函数**：`min(1.0, age * 0.01)`
    - 来源检查: 故事中静默（只说“基于年龄”）| lit_notes 中静默 | 未发现规范默认值
    - 理由: 在年龄增长概率的简单线性函数；确保老年智能体被替换。

4.  **智能体存活状态**：`alive: bool` 属性
    - 来源检查: 故事中静默 | lit_notes 中静默 | 未发现规范默认值
    - 理由: 追踪活跃与不活跃智能体的标准 ABM 实践。

5.  **初始物品嵌入**：从 N(0,1) 采样的随机 16 维向量
    - 来源检查: 故事中未指定确切初始化 | lit_notes 中静默 | 未发现规范默认值
    - 理由: 训练初始语义模型需要随机嵌入；这是标准实践。