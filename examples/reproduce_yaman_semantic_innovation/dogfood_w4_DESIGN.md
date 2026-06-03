好的，作为一名专家级ABM架构师，我将严格遵循工作流程和约束，为“语义知识引导创新驱动文化演化”这篇论文生成一个高保真度的DESIGN.md设计文档。

---

# ABM Model Design Document — Reproduction

**Status**: Draft
**Mode**: REPRODUCE

---

## Part 0: Source Paper Reference

- **Citation**: Yaman, M., Tian, Y., & Lindström, B. (2026). Semantic knowledge guides innovation and drives cultural evolution. *Proceedings of the National Academy of Sciences*.
- **DOI / URL**: [Not yet available; referenced from `STORY.md` as PNAS 2026]
- **Key claim being reproduced**: 在累积文化演化（cumulative cultural evolution）任务中，拥有可学习的语义知识（semantic knowledge）的智能体，其创新能力更高，并且这种优势与社会学习（social learning）之间存在协同效应（synergistic effect）。
- **Fidelity target**: 复现论文中的核心定性结果：
    1.  有语义知识（`P_S > 0`）的群体比没有语义知识（`P_S = 0`）的群体能发现更多的创新（累积物品数/文化库大小）。
    2.  同时使用语义知识和高水平的社会学习（`P_S > 0` 且 `P_SL > 0`）比单独使用任何一种策略都能带来更高的创新水平。
    3.  语义知识带来的优势在不同的人口规模下均能持续。
- **Acceptable deviation**: 假设的随机种子和运行批次可以根据计算资源调整。`P_S`, `P_SL`, `P_G` 的参数扫描范围可能从论文的 `{0, 0.1, 0.5, 0.9}` 中选择一个有代表性的子集（例如 `{0, 0.5, 0.9}`），以在性能和复现结果之间取得平衡。年龄相关的死亡函数的具体参数，如果论文未明确给出，将使用一个合理的默认值（见 `AI-ASSUMPTION`）。

---

## Part 1: Requirements

### 1. Model Overview
- **Project Name**: `Yaman2026SemanticInnovation`
- **Original Story**: 本模型忠实再现了Yaman, Tian & Lindström在PNAS 2026发表的论文中描述的ABM。该模型旨在研究语义知识（一种关于哪些物品能组合在一起的知识）如何在群体层面引导创新，并最终驱动累积文化演化。
- **Goal**: 复现论文中的核心发现：语义知识引导探索，提高创新成功率，并与社会学习协同加速文化演化。
- **Mode**: Simulator
- **Visualizer**: Yes (需要生成论文中典型的“代际 vs. 累积文化库大小”的比较曲线图。)

### 2. Agents
- **Agent Class**: `Individual`
    - **Attributes**:
        - `id`: int, 智能体唯一标识符。`[story]`
        - `age`: int, 初始化为0，每代增加1。`[story]`
        - `score`: int, 智能体发现的总创新（新物品）数量，初始化为0。`[story]`
        - `inventory`: `List[int]`, 智能体拥有的物品ID列表，初始化为6个基础物品的ID（`[1, 2, 3, 4, 5, 6]`）。`[story]`
        - `memory`: `List[Tuple[int, ...]]`, 智能体已经尝试过的所有配方组合，初始化为空列表。`[story]`
        - `semantic_model`: 一个`FeedforwardLearner`实例，表示智能体的语义知识。`[story, paper-canonical]`。详见`#1. Technical Specification`。
        - `alive`: bool, 智能体是否存活，初始化 `True`。`[paper-canonical, MoranProcess]`
        - `fitness`: float, 一个用于Moran过程的归一化分数，与`score`相关。`[paper-canonical, MoranProcess]`
    - **Methods**:
        - `setup()`: 初始化所有属性。`[story]`
        - `step()`: 执行一次创新尝试的逻辑，包含随机、语义和泛化三种策略。`[story, paper-canonical]`
        - `copy_inventory_for_social():` 返回一个可直接访问的`inventory`副本，供其他智能体在社交学习中读取。`[AI-ASSUMPTION: 需要一种方法来安全地读取其他智能体的库存。这是实现细节而非模型机制。]`
    - **Initialization**: 生成 `N` (`self.scenario.agent_num`) 个智能体，年龄设为0，分数设为0，库存初始化为包含6个基础物品ID的列表，记忆为空，并初始化一个新的 `FeedforwardLearner` 作为其语义模型。`[story]`

### 3. Space & Environment
- **Space Structure**: None (智能体之间没有空间或固定的网络结构。交互通过环境进行，例如社交学习）。`[paper-canonical, Topology Decision Tree]`
- **Grid Specs / Network Specs**: 不适用。
- **Environment Logic**: 环境充当智能体间交互的协调器，并托管“Totem”创新树数据。
    - `recipe_tree`: `RuleTable`实例，从`rules_tidied.csv`文件加载。每个配方的ID、成分（最多3个）、产出物品ID被加载。`[story, paper-canonical]`
    - `step()`: 每代调用一次，依次执行：
        1.  更新`Population`对象以进行Moran过程（死亡与繁殖）。`[story, paper-canonical, MoranProcess]`
        2.  触发所有存活智能体的 `step()` (在其内部决定是社交学习还是个体学习)。`[story]`
        3.  触发所有存活智能体对其`semantic_model`进行`retrain`。`[story]`

### 4. Optimization
- 不适用。此模型是纯模拟，不涉及校准或训练。

### 5. Data
- **Inputs**:
    - `rules_tidied.csv`: 来自论文OSF仓库的“Totem”创新树数据。`[story]`
    - `SimulatorScenarios.csv`: 包含所有实验参数及其范围的CSV文件。`[template, paper-canonical]`
- **Outputs**:
    - `Result_Simulator_Environment.csv`: 按代记录群体级的聚合指标。`[template, paper-canonical]`

### 6. Computing
- **Parallel Cores**: 4 (一个合理的默认值，用于处理中等规模的计算)
- **Parallel Mode**: process

---

## Part 2: Technical Specification

### 1. File Structure
- `core/agent.py`: `Individual` (智能体类)
- `core/model.py`: `YamanModel` (模型类)
- `core/environment.py`: `YamanEnvironment` (环境类)
- `core/scenario.py`: `YamanScenario` (场景类)
- `core/data_collector.py`: `YamanDataCollector` (数据收集器类)
- `main.py`: entry point (入口点)
- `data/`: 存放`rules_tidied.csv`和`SimulatorScenarios.csv`。

### 2. Class Interfaces

#### Agent (`core/agent.py`)

```python
class Individual(Agent):
    def setup(self):
        # 属性初始化，来源于论文
        self.age = 0
        self.score = 0
        self.inventory = [1, 2, 3, 4, 5, 6]  # 6个基础物品
        self.memory = []
        # 语义模型是一个小型的FeedforwardLearner: 输入: 16维嵌入, 输出: 下一个物品的概率分布
        self.semantic_model = FeedforwardLearner(...) # 运行时提供的 API
        self.alive = True
        self.fitness = 0.0

    def step(self):
        # 执行一次创新尝试的算法
        p_s = self.scenario.p_s
        p_g = self.scenario.p_g
        p_sl = self.scenario.p_sl

        # 1. 决定是进行社交学习(Social Learning)还是个体学习(Individual Exploration)
        if random() < p_sl:
            self._social_learning_step()
        else:
            self._individual_exploration_step(p_s, p_g)

        # 2. 更新分数
        # (逻辑在 *_step 方法中处理)
```

**`_individual_exploration_step(self, p_s, p_g)`**:
- 如果 `random() < p_s`: (语义策略)
    - 如果 `random() < p_g`: (泛化)
        1. 从`memory`中随机选择一个成功（产生新物品）的配方。
        2. 选择配方中的一个成分，并用语义模型预测出在嵌入空间中最近的物品来替换它。
    - 否则: (语义探索)
        1. 从`inventory`中随机选择一个物品`item_A`。
        2. 使用`semantic_model`预测最可能与之互补的物品`item_B`。
        3. 尝试组合 `(item_A, item_B)`。如果配方需要3个物品，用同样的方法预测`item_C`。
- 否则: (随机策略)
    - 从`inventory`中随机选择1-3个物品作为候选组合。
- **验证尝试结果**:
    - 将尝试的组合添加到`memory`。
    - 检查组合是否存在于`environment.recipe_tree`中且为有效配方。
    - 如果有效且`inventory`中没有产出物品，则添加该物品到`inventory`，`score`加1。

**`_social_learning_step(self)`**:
1. 找到`environment`中的最高分智能体 (`best_agent`)。
2. 检查`best_agent.inventory`中是否有自己`inventory`没有的物品。
3. 对于那些缺失的物品，检查是否能用自己的`inventory`组合出来（即检查是否能通过`recipe_tree`至少找到一个缺失的物品所需的配方）。
4. 如果能，则将该配方加入到自己的`memory`中，并尝试组合。如果成功，则将新物品加入`inventory`，`score`加1。
5. 如果不能，则回退到`_individual_exploration_step(self, p_s, p_g)`。

---

#### Model (`core/model.py`)

```python
class YamanModel(Model):
    def create(self):
        self.agents = self.create_agent_list(Individual)
        self.environment = self.create_environment(YamanEnvironment)
        self.data_collector = self.create_data_collector(YamanDataCollector)
        # 不需要空间或网络拓扑
        self.moran_process = self.create_moran_process() # 运行时提供的API

    def setup(self):
        self.agents.setup_agents(agents_num=self.scenario.agent_num)
        self.environment.setup(self)  # 传递Model引用，以加载数据

    def run(self):
        for t in self.iterator(self.scenario.periods):
            # 1. 环境执行一代的全局逻辑 (Moran过程, 然后触发智能体行为)
            self.environment.step(self.agents, self.moran_process)
            # 2. 数据收集
            self.data_collector.collect(t, self.agents, self.environment)
        self.data_collector.save()
```

#### Environment (`core/environment.py`)

```python
class YamanEnvironment(Environment):
    def setup(self, model):
        super().setup()
        # 从 data/ 目录加载‘Totem’规则表
        self.recipe_tree = load_rule_table('data/rules_tidied.csv')
        # 注册本世代最高分的智能体
        self.best_agent = None

    def step(self, agents, moran_process):
        # 1. 执行Moran过程 (根据论文的描述)
        moran_process.apply(agents, self)  # 处理死亡和繁殖

        # 2. 更新 best_agent 的信息
        self._update_best_agent(agents)

        # 3. 让所有存活的智能体行动
        for agent in agents:
            if agent.alive:
                agent.step()

        # 4. 所有智能体重训它们的语义模型
        for agent in agents:
            if agent.alive:
                # 使用其memory里的成功配方进行训练
                if len(agent.memory) > 0:
                     agent.semantic_model.update(agent.memory)

```

### 3. Data Inputs Plan
- **SimulatorScenarios.csv columns**:
    - `id_scenario`: int
    - `agent_num`: int (100, 50, 25)
    - `p_s`: float (0, 0.1, 0.5, 0.9)
    - `p_sl`: float (0, 0.1, 0.5, 0.9)
    - `p_g`: float (0, 0.1, 0.5, 0.9)
    - `periods`: int (例如，最大代数，比如500)
    - `semantic_cost_factor`: float (1.0, 2.0, 3.0)   # 代表使用语义模型的成本因子。`[AI-ASSUMPTION]`
    - `death_prob_base`: float # 基础死亡概率。`[AI-ASSUMPTION]`
    - `death_prob_age_factor`: float # 年龄对死亡概率的影响因子。`[AI-ASSUMPTION]`
- **Other input CSVs**:
    - `data/rules_tidied.csv`: 规则参考表，列包括：`item`, `c1`, `c2`, `c3`, `point`, `given`等。`[story, paper-canonical]`

### 4. Output Data
- `Result_Simulator_Environment.csv`:
    - `id_scenario`
    - `id_run`
    - `generation`: int (代)
    - `mean_agent_score`: float (该世代所有存活智能体的平均分数)
    - `max_agent_score`: float (该世代最高分)
    - `mean_inventory_size`: float (该世代所有存活智能体的平均库存大小)
    - `total_population_curated_recipes`: int (群体中所有发现过的独特配方的总和)
    - `alive_agent_count`: int (存活智能体数量)

### 5. Source Trace

| Element | Source | Detail |
|---|---|---|
| 1. Agents | `[story, paper-canonical]` | 100个智能体；拥有库存、记忆、分数、年龄和语义模型（`[paper-canonical, FeedforwardLearner]`）。 |
| 2. Interaction mechanism | `[story]` | 无空间/网络结构。智能体之间的交互是通过环境定义的社会学习（观察最高分者）和在Moran过程中的繁殖。 |
| 3. Time structure | `[story]` | 一个时间步代表一个“代”（Generation）。每代内，所有智能体行动并重训模型。 |
| 4. Initialization | `[story, paper-canonical]` | 所有智能体拥有相同的初始库存（6个基础物品），年龄为0，分数为0，记忆为空，并拥有一个新训练的语义模型。 |
| 5. Decisions & behavior | `[story]` | 使用`P_S`概率选择随机或语义策略；在语义策略内使用`P_G`概率选择泛化或语义预测；使用`P_SL`概率进行社交学习。回退机制。 |
| 6. Scenario parameters | `[story]` | `N (agent_num)`, `P_S`, `P_SL`, `P_G`。 |
| 7. Calibration | `[paper-canonical]` | 无。这是一个模拟模型。 |
| 8. Output metrics | `[story]` | 累积群体文化库大小（平均分数、最大分数、总独特配方数）。 |

### 6. Assumptions (AI-ASSUMPTION only — last resort)

1.  **AI-ASSUMPTION**: 年龄相关死亡函数的具体形式和参数。
    - Source check: story silent | lit_notes silent | no canonical default known for Yaman2026
    - Reason: 论文提到“Agents die with an age-based probability (older agents more likely);”，但没有给出概率函数或参数。我们将使用一个简单的线性增长函数：`death_prob = min(1.0, death_prob_base + agent.age * death_prob_age_factor)`。`death_prob_base`和`death_prob_age_factor`将作为场景参数，允许探索其对结果的影响。取值范围将通过小规模预试验确定，确保成年智能体（例如，年龄>10）有显著死亡概率。

2.  **AI-ASSUMPTION**: `FeedforwardLearner`的训练细节（学习率、优化器、批次大小）。
    - Source check: story silent | lit_notes silent | no canonical default known for Yaman2026
    - Reason: 虽然论文提到使用标准NLL和反向传播，但具体学习率（例如，`lr=0.01`）和优化器（例如，SGD或Adam）未指定。我们将使用运行时默认提供的`FeedforwardLearner`的默认配置（`lr=0.01`, optimizer='adam'），该配置被设计为通用且表现良好。

3.  **AI-ASSUMPTION**: 运行重复次数（run repetitions）。
    - Source check: story silent | lit_notes silent | no canonical default known for Yaman2026
    - Reason: 为了得到稳健的平均结果，每个参数组合将运行5次，并使用不同随机种子。这是ABM的常见做法。`[AI-ASSUMPTION: 这是计算稳定性所需的标准做法，而非对模型机制的假设。]`

4.  **AI-ASSUMPTION**: 泛化（Generalization）的具体机制实现细节。
    - Source check: story silent | lit_notes silent | no canonical default known for Yaman2026
    - Reason: 论文描述：“take one remembered successful recipe and replace one of its items with the item that is nearest in embedding space”。我们将假设“nearest in embedding space”是通过计算智能体`semantic_model`的嵌入层中，所有物品的嵌入向量之间的余弦相似度来实现的。替换的物品是从原始配方中随机抽取的。

5.  **AI-ASSUMPTION**: 社交学习（Social Learning）时如何“检查能否组合” (check if it can craft) 的具体逻辑。
    - Source check: story silent | lit_notes silent | no canonical default known for Yaman2026
    - Reason: 论文描述：“if it can craft a missing item from its own inventory”。我们将实现为：对于每个`best_agent`有而自己没有的物品，检查`recipe_tree`中需要哪些物质成分。如果这些成分都在自己的`inventory`中，则视为“可以”。否则，为了计算效率，最多检查3个缺失的物品。