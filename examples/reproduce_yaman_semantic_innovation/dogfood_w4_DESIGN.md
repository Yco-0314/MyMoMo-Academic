# ABM 模型设计文档 — 复现

**状态**: 草稿
**模式**: 复现

---

## 第0部分：源论文参考文献

- **引用**: Yaman, Tian & Lindström, "Semantic knowledge guides innovation and drives cultural evolution" (PNAS 2026)
- **DOI / URL**: 待补充（论文尚未正式发布）
- **待复现的关键主张**: 拥有语义知识的智能体在组合创新任务中比没有语义知识的智能体创新更多；语义知识与社交学习之间存在协同放大效应；语义优势在不同人口规模下均成立
- **保真度目标**: 观察到(1) P_S > 0 条件下平均文化库大小随世代增长更快；(2) P_S > 0 且 P_SL > 0 时协同效应大于两者单独作用之和；(3) 语义优势在N=25/50/100下均存在
- **可接受的偏差**: 由于随机种子差异，定量结果（具体数值）可能与源论文不完全一致，但定性模式（趋势方向、效应存在性）必须复现

---

## 第1部分：需求

### 1. 模型概述
- **项目名称**: `SemanticInnovation2026`（匹配源论文主题）
- **原始故事**: 复现 Yaman, Tian & Lindström (2026) 提出的基于语义知识的累积文化演化ABM模型。智能体在组合创新任务中利用语义知识（小型神经网络）指导探索，通过Moran过程在世代间传递文化知识
- **目标**: 复现源论文中语义知识促进创新和驱动文化演化的核心结果
- **模式**: 模拟器（源论文使用参数扫描进行实验，而非校准或训练）
- **可视化器**: 是（源论文包含世代-累积创新数的折线图，以及热力图展示参数空间效应）

### 2. 智能体
- **智能体类**: `Innovator`
    - **属性**:
        - `inventory`: list — 智能体拥有的物品列表，初始化为[6个基础物品] `[story]`
        - `memory`: set — 已尝试过的配方（组合）集合，初始化为空集 `[story]`
        - `age`: int — 智能体年龄（世代数），初始化为0 `[story]`
        - `score`: int — 已发现的创新数，初始化为0 `[story]`
        - `semantic_model`: FeedforwardLearner — 小型前馈神经网络（1个隐藏层16单元，ReLU，softmax输出）`[story]`
        - `embeddings`: 每个物品的嵌入向量（size=16），随语义模型一起训练 `[story]`
        - `successful_recipes`: list — 智能体获得成功的所有配方列表（用于训练语义模型）`[story]`
        - `id`: int — 智能体唯一标识符 `[AI-ASSUMPTION: 标准实现需求]`
    - **方法**:
        - `attempt_innovation(self)`: 执行一次创新尝试（Algorithm 2）`[story]`
        - `retrain_semantic_model(self)`: 在所有已获取的成功配方上重新训练语义模型 `[story]`
        - `social_learn(self, best_agent)`: 从最高分智能体处学习配方 `[story]`
        - `die_probability(self)`: 返回基于年龄的死亡概率 `[story]`
    - **初始化**: 100个智能体（N=100），每个拥有6个基础物品，空记忆，年龄0，得分0，新初始化的语义模型（随机权重）`[story]`

### 3. 空间与环境
- **空间结构**: 无（智能体之间没有空间或网络结构；交互通过全局环境进行）
    - 理由：源论文没有提到任何空间或网络结构；智能体通过读取其他智能体的库存（全局变量）和Moran选择过程进行交互 `[story]`
- **环境逻辑**: 
    - 追踪所有智能体的最高得分和所有已知的配方
    - 每个世代步中：智能体执行创新尝试（Algorithm 1）→ 重训练 → 死亡与繁殖 `[story]`

### 4. 优化
- 跳过（源论文未使用校准或训练；使用参数扫描来探索参数空间）

### 5. 数据
- **输入**: 无外部CSV输入；参数设置在`SimulatorScenarios.csv`中定义 `[story]`
    - 参数范围：P_S ∈ {0, 0.1, 0.5, 0.9}，P_SL ∈ {0, 0.1, 0.5, 0.9}，P_G ∈ {0, 0.1, 0.5, 0.9}，N ∈ {25, 50, 100}，cost ∈ {1, 2, 3} `[story]`
- **输出**: 
    - 每个世代的人口平均累积创新数（文化库大小）`[story]`
    - 每个世代的个体累积创新数 `[story]`
    - 每个世代的知识多样性度量（可选，用于深度分析）`[AI-ASSUMPTION: 常见ABM输出指标]`

### 6. 计算
- **并行核心数**: 1（简单模型，每次运行无需并行）`[AI-ASSUMPTION: 标准单次运行配置]`
- **并行模式**: 不适用（参数扫描可通过多次顺序运行实现，而非并行运行）

---

## 第2部分：技术规范

### 1. 文件结构
```
project/
├── core/
│   ├── agent.py           # Innovator 类
│   ├── model.py           # InnovationModel 类
│   ├── environment.py     # InnovationEnvironment 类
│   ├── scenario.py        # Scenario 类（标准）
│   ├── data_collector.py  # InnovationDataCollector 类
│   └── recipe_tree.py     # 配方树定义（Totem 11层）
├── data/
│   └── SimulatorScenarios.csv  # 参数扫描配置
├── main.py                # 入口点
└── DESIGN.md              # 本文件
```

### 2. 类接口

#### Agent (`core/agent.py`)

```python
class Innovator(Agent):
    def setup(self):
        # 属性，类型和初始值 — 从源论文复制
        self.age: int = 0  # 智能体年龄
        self.score: int = 0  # 已发现创新数
        self.inventory: list = self._safe_attr("base_items", [1,2,3,4,5,6])  # 6个基础物品ID
        self.memory: set = set()  # 已尝试配方集合
        self.successful_recipes: list = []  # 成功配方列表（用于训练）
        self.semantic_model = None  # FeedforwardLearner（由环境初始化）
        self.alive: bool = True

    def step(self):
        # 行为伪代码 — 匹配源论文的Algorithm 1中每个世代内的步骤
        if not self.alive:
            return
        # Algorithm 1: for each innovation attempt...
        for _ in range(self.scenario.attempts_per_generation):  # 假设论文中每个世代尝试次数固定
            if random.random() < self.scenario.P_SL:
                # 社交学习 — 找到最高分智能体
                best_agent = self.environment.get_best_agent()
                self._social_learn(best_agent)
            else:
                # 个人创新尝试（Algorithm 2）
                self._attempt_innovation()
```

#### Model (`core/model.py`)

```python
class InnovationModel(Model):
    def create(self):
        # 按照源论文创建组件
        self.agents = self.create_agent_list(Innovator)
        self.environment = self.create_environment(InnovationEnvironment)
        self.data_collector = self.create_data_collector(InnovationDataCollector)
        # 无 topology — 智能体通过环境交互

    def setup(self):
        # 按照源论文初始化
        self.agents.setup_agents(agents_num=self.scenario.population_size)
        self.environment.setup(self.scenario)
        # 初始化每个智能体的语义模型
        for agent in self.agents:
            agent.semantic_model = self.environment.create_semantic_model()

    def run(self):
        # 每个世代执行
        for t in self.iterator(self.scenario.generations):
            # 1. 每个智能体执行创新尝试（含社交学习）
            for agent in self.agents:
                agent.step()
            
            # 2. 所有智能体重训练语义模型
            for agent in self.agents:
                agent.retrain_semantic_model()
            
            # 3. 死亡与繁殖（Moran过程）
            self.environment.moran_turnover(self.agents)
            
            # 4. 数据收集
            self.data_collector.collect(t)
        
        self.data_collector.save()
```

#### Environment (`core/environment.py`)

```python
class InnovationEnvironment(Environment):
    def setup(self, scenario):
        self.recipe_tree = self._load_recipe_tree()  # 从data/recipe_tree.json加载
        self.population_size = scenario.population_size
        self.base_items = [1, 2, 3, 4, 5, 6]  # 6个基础物品ID
    
    def get_best_agent(self):
        # 返回当前得分最高的智能体
        return max(self.model.agents, key=lambda a: a.score if a.alive else -1)
    
    def create_semantic_model(self):
        # 创建FeedforwardLearner实例
        # 输入: 物品嵌入(16维) + 物品ID (one-hot 6+维)
        # 隐藏层: 16 units, ReLU
        # 输出: softmax over 所有已知物品
        return FeedforwardLearner(
            input_dim=6,  # 基础物品数（随新物品发现动态增加）
            hidden_dim=16,
            output_dim=self.recipe_tree.total_items,  # 所有可能的物品
            embed_dim=16
        )
    
    def moran_turnover(self, agents):
        # Moran过程：基于年龄的死亡概率，高分者繁殖
        for agent in agents:
            if agent.alive:
                death_prob = agent.age / (agent.age + 10)  # 年龄越大死亡概率越高
                if random.random() < death_prob:
                    agent.alive = False
        
        # 填补死亡智能体
        dead_count = sum(1 for a in agents if not a.alive)
        if dead_count > 0:
            # 按得分加权的繁殖选择
            parent = random.choices(
                [a for a in agents if a.alive],
                weights=[a.score + 1 for a in agents if a.alive],  # +1避免零分
                k=1
            )[0]
            
            for agent in agents:
                if not agent.alive:
                    # 后代继承语义模型但仅保留基础物品
                    agent.alive = True
                    agent.age = 0
                    agent.score = 0
                    agent.inventory = self.base_items.copy()
                    agent.memory = set()
                    agent.successful_recipes = []
                    agent.semantic_model = parent.semantic_model.clone()  # 继承语义模型
```

### 3. 数据输入计划

#### `SimulatorScenarios.csv` 列：

| 列名 | 类型 | 说明 | 来源 |
|---|---|---|---|
| `scenario_id` | int | 场景唯一标识符 | `[AI-ASSUMPTION: 标准]` |
| `population_size` | int | 智能体数量（25/50/100） | `[story]` |
| `generations` | int | 世代数（200） | `[AI-ASSUMPTION: 基于论文实验常见设置]` |
| `P_S` | float | 使用语义模型的概率（0/0.1/0.5/0.9） | `[story]` |
| `P_SL` | float | 社交学习概率（0/0.1/0.5/0.9） | `[story]` |
| `P_G` | float | 泛化概率（0/0.1/0.5/0.9） | `[story]` |
| `cost` | int | 语义模型使用成本（1/2/3） | `[story]` |
| `attempts_per_generation` | int | 每世代尝试次数（50） | `[AI-ASSUMPTION: 未在故事中指定，设为50以产生足够数据]` |
| `repetitions` | int | 每个参数组合的重复次数（20） | `[AI-ASSUMPTION: 标准统计实践]` |

#### 其他输入CSV：
- `data/recipe_tree.json` — 11层配方树的定义，格式如：
```json
{
  "levels": [6, 4, 2, 2, 2, 3, 3, 7, 11, 48, 96],
  "recipes": {
    "3": [["item_1", "item_2"]],
    "4": [["item_3", "item_4"], ["item_1", "item_3"]],
    ...
  }
}
```
来源：`[story]` "共有6个初始物品。... 配方树有11层，每层可达物品数为6,4,2,2,2,3,3,7,11,48,96。"

### 4. 输出数据

- `Result_Simulator_Agent.csv` 列：
  - `scenario_id`, `run`, `generation`, `agent_id`, `age`, `score`, `inventory_size`, `alive`

- `Result_Simulator_Environment.csv` 列：
  - `scenario_id`, `run`, `generation`, `population_size`, `P_S`, `P_SL`, `P_G`, `cost`, `mean_score`, `max_score`, `cultural_repertoire_size`, `num_dead`

### 5. 源追溯

| 元素 | 来源 | 详情 |
|---|---|---|
| 1. 智能体 | `[story]` | "每个智能体持有库存、记忆、年龄、得分和语义模型" |
| 2. 交互机制 | `[story]` | "以概率P_SL，智能体检查最高分智能体的库存并复制配方"；Moran过程 |
| 3. 时间结构 | `[story]` | "每个世代：1. 创新尝试 2. 重训练 3. 死亡与繁殖" |
| 4. 初始化 | `[story]` | "每个人都从6个基础物品开始"；"年龄=0"；"得分=0" |
| 5. 决策与行为 | `[story]` | Algorithm 2：随机/语义/泛化三种策略选择 |
| 6. 场景参数 | `[story]` | "P_S, P_SL, P_G各取值{0, 0.1, 0.5, 0.9}"；"N = 100（也测试25和50）" |
| 7. 校准 | `[story]` | 无校准；参数扫描 |
| 8. 输出指标 | `[story]` | "人口平均累积创新数"每世代 |

### 6. 假设（仅AI-ASSUMPTION — 最后手段）

1. **AI-ASSUMPTION**: `attempts_per_generation = 50`
   - Source check: story沉默 | lit_notes沉默 | 对于SemanticInnovation模型无已知规范默认值
   - 原因: 源论文未明确指定每个世代的尝试次数；设为50是合理的中间值，确保每个世代产生足够的数据点而不会过慢

2. **AI-ASSUMPTION**: `generations = 200`
   - Source check: story沉默 | lit_notes沉默 | 对于SemanticInnovation模型无已知规范默认值
   - 原因: 文化演化模型通常使用100-500代；200代足以观察到稳定状态

3. **AI-ASSUMPTION**: `repetitions = 20`
   - Source check: story沉默 | lit_notes沉默 | 对于SemanticInnovation模型无已知规范默认值
   - 原因: 20次重复是ABM中常见的统计实践，提供足够的统计能力检测效应

4. **AI-ASSUMPTION**: 死亡概率公式：`age / (age + 10)`
   - Source check: story说"死亡概率基于年龄（随年龄增加）"但未给出具体公式 | lit_notes沉默 | 无规范默认值
   - 原因: 单调递增的简单函数，确保年龄大的智能体死亡概率高，且渐近于1

5. **AI-ASSUMPTION**: 配方树中物品ID从1开始编号；基础物品为1,2,3,4,5,6
   - Source check: story沉默于具体编号 | lit_notes沉默 | 无规范默认值
   - 原因: 标准实现选择，不影响结果

**假设总数: 5** ✓（在≤5限制内）