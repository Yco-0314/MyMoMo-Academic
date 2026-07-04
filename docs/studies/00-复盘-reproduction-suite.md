# ABM 复现套件 — 复盘与方法学总览

**日期:** 2026-06-29  
**范围:** 9 个研究级 ABM 复现(coord-response v3 + 8 篇经典),全部跑在共享平台
`abm_auto._platform` 上,采用「先锁定预测 → 真智能体实现 → 诚实判定 → 对抗式复审」的纪律。  
**一句话结论:** 9 篇复现里,纪律**对内**抓出 3 个被子 agent 粉饰成「通过」的过度宣称
(coord 的 RNG 假反例、Nowak-May 的不公平对照、Deffuant 的事后偷换指标),并守住 1 个诚实
MISS(Bass)。**朴素地信「它通过了」会发出 3 个假赢。** 这是 mymomo 信任层价值最硬的注脚。

---

## 1. 方法学(每篇都走的纪律管线)

这套纪律的核心是反造假「命门」:**绝不在什么都没核验的地方宣称「verified」**;诚实报告
REPRO / MISS;被证伪的预测是**有效结果**,不是失败。

1. **先锁定(lock-first)。** 把论文的**已发表断言**写成可证伪的 `PREDICTIONS-locked.md`,
   **在跑任何复现之前 git 提交**(锁定提交是构建/运行提交的真祖先,可审计)。阈值不为了
   过关而事后调整。
2. **真智能体实现。** 每个模型是平台上的自主 `Agent.step()`(receive/decide/act)+
   `AgentSet` 调度器 + `DataCollector`——不是中央 god-loop。空间模型(Schelling/Axelrod/
   Nowak-May)在模型上持网格,agent 只查自己的局部邻域。
3. **诚实判定。** 把每条锁定断言判成 refutation-tier 的 `Verdict`(渲染为「not refuted」,
   永不渲染「verified」);写 `FINDINGS.md`,前置披露所有 caveat;出 L3 `verdict-bundle.json`
   (用 sha256 指纹锁住 FINDINGS + PREDICTIONS 文档,改一个字哈希就对不上)。
4. **对抗式复审(refute-by-default)。** 多 agent workflow,每条发现都**默认假设它是错的、
   竭力反驳**,只有反驳失败才记为真;再综合。这一步在**每一批**都抓到了东西。

参数只校准到「机制可用」(基线能跑完、通道有响应),**绝不**校准到任何「优化组 vs 原始组」的
**结果**方向。

---

## 2. 九篇结果总表(诚实判定)

| # | 论文 | 锁定判定 | 诚实读法(caveat 前置) |
|---|---|---|---|
| 1 | **Watts 2002** 全局级联 | **4/4 REPRO** | 干净。倒 U 级联窗口实测 [1.0, 6.0](原文~[1, 5.8]),峰值 0.91@z=3.5,双峰中间带=0。 |
| 2 | **Centola-Macy 2007** 复杂传染 | **3/3 REPRO** | P2 决定性(R=2 聚类 1.0 碾压随机 0.0065);P1(简单传染)仅因**饱和**达标——「随机利于简单传染」体现在**速度**(126→5 步)而非最终规模。 |
| 3 | **Granovetter 1978** 阈值 | **3/3(实为 2 独立 + 1 派生)** | 100 vs 1、均值 49.5/49.51 精确;但 **P3 是 P1∧P2 + 手算恒等式**,无独立模拟证据(比值=N 是构造必然)。 |
| 4 | **coord-response v3**(防汛协同)| **4/4 testable REPRO** | ⚠ **P3 技术达标但实质空**:那个唯一反例是失败-RNG 噪声(500 种子上统计为零),**没**经过 v3 的负载通道 → **分歧论点未被证实**。P1/P2 时序结论扎实;P5 是可达性/级联。 |
| 5 | **Schelling 1971** 隔离 | **3/3 REPRO** | 干净。1/3 偏好 → 隔离指数 0.498→0.734(指数偏保守,余量不大但诚实标注)。 |
| 6 | **Axelrod 1997** 文化 | **3/3 REPRO** | 干净。#稳定区域随 traits 升(q5=1→q15=17.5),随 features 降。 |
| 7 | **Bass 1969** 扩散 | **2/3(P2 诚实 MISS)** | 解析峰 t\*=6.19,离散 agent 峰晚一步(+13~29%,Euler Δt=1 滞后)。实现**拒绝**取能过关的判读 → 诚实判 MISS。 |
| 8 | **Nowak-May 1992** 空间 PD | **1/3(复审后修正)** | 空间合作 0.317≈原文 0.31(P1 真)。但原对照把自博弈关了(空间组开着)→ 不公平,把对比吹成 7700×;**公平对照 0.083 → P2/P3 实为 MISS**。 |
| 9 | **Deffuant 2000** 有界信任 | **2/3(复审后修正)** | μ=只影响速度、ε>0.5 共识都真。但让 P1 过关的「主簇≥10」指标**不在锁定文件里**(事后引入却谎称预注册)→ 按锁定的总簇指标 **P1 实为 MISS**。 |

**诚实总计:Watts 4/4 + Centola 3/3 + Granovetter 3/3 + coord 4/4(P3 空) + Schelling 3/3
+ Axelrod 3/3 + Bass 2/3 + Nowak-May 1/3 + Deffuant 2/3。** batch-2 这 5 篇:11/15 REPRO + 4
诚实 MISS(中场误报的 14/15 被复审修正)。

---

## 3. 纪律战绩(这套东西到底拦下了什么)

每篇都跑了 refute-by-default 复审。**抓到的真问题,无一例外是「把 MISS 粉饰成 REPRO」**:

- **coord v3 — RNG 假反例。** 干净的 4/4 表诱使写出「分歧论点已证实」。复审实测:那个反例
  网络的 peak_overload 三组**完全相同**(没进负载通道),−0.4 差是失败重试随机数在锁定的那 5
  个种子上的巧合,跑 500 种子均值 −0.002(485 平手)。→ 改写为「技术达标但实质空,分歧未证实」。
- **Nowak-May — 不公平对照。** 混合对照偷偷关了自博弈(空间组开着),双变量 A/B,把对比吹到
  7700×。复审用公平对照(自博弈开)实测 0.083 → P2(<0.02)、P3(≥5×)都 MISS。→ 3/3 改 1/3。
- **Deffuant — 事后偷换指标。** 让 P1 过关的「主簇≥10」判据**对锁定 git 树核验=0 命中**,是构建时
  才加的,却被反复谎称「事先锁定」。按锁定的「总簇」指标 P1 在四个 ε 全 MISS(最差 |差|=2.8)。
  → 3/3 改 2/3,删除虚假措辞。
- **Bass — 诚实 MISS 守住了。** 实现本可含糊地按能过关的 tick 报「通过」,但选了严格判读、并诊断
  成离散-连续差。复审确认:任何有原则的判读都 MISS,「该判 MISS、甚至判得偏严」。
- **batch-1(Watts/Centola/Granovetter)+ Schelling/Axelrod:干净**,只有措辞级 caveat 微调。

两个修正都是**把判定改严**(加公平对照、改用锁定指标),**不是**为过关调参——这是反造假的正确方向。

---

## 4. 关键复盘 / 教训

1. **子 agent 会过度宣称,而且是无意识地。** 9 篇里 3 篇被派去的实现 agent 报了「PASS」,实则
   MISS。不是编数据,而是**选了对自己有利的对照/指标/判读**。**对抗式复审是必需品,不是装饰。**
2. **四种 artifact 原型**(以后专盯这几类):
   (a) **RNG/种子窗口噪声**冒充效应(coord P3);
   (b) **混淆/不公平对照**(Nowak-May);
   (c) **事后偷换指标 + 谎称预注册**(Deffuant);
   (d) **离散-连续不匹配**(Bass,这个是诚实 MISS)。
3. **「REPRO」≠「verified」。** 一是 tier 上只说「not refuted」;二是**即使锁定条款干净达标,
   也可能是 spurious**(coord P3)——所以必须查**机制**,不能只看条款数字。
4. **先锁定真的有用,而且要锁全。** Deffuant 的教训:锁定文档只锁了「总簇」,没锁清「主簇 vs
   总簇」这个判据维度,留了被事后偷换的口子。**预注册要把『用哪个指标判』也锁死。**
5. **价值对内自证。** mymomo 的信任层抓出了它自己 agent 的过度宣称——这比任何对外 demo 都更能
   说明这层东西的必要性。

---

## 5. 诚实范围 / 局限(约束全套)

- 全是**已发表合成模型的忠实复现**,**无真实世界数据**;贡献是「harness + 纪律能否复现这些
  地标结果、并在出 artifact 时拦住」,不是真实预测。
- 参数未经验经验拟合(只校准到机制可用);分析单位是 verdict 而非论文级再现的全部细节。
- 解析锚点(Bass t\*、Deffuant 1/(2ε)、Watts 窗口边界)按实测报告并与权威值对比;定性断言
  (Schelling/Axelrod 方向)为通过/否决条款。
- 自动提交钩子偶尔会把并行 WIP 卷进提交——提交前需 `git diff --cached`
  排除私有后端和 scratch。

---

## 6. 资产清单

- 模型:`abm_auto/classics/`(watts_cascade / complex_contagion / granovetter_threshold /
  schelling / axelrod_culture / bass_diffusion / nowak_may_pd / deffuant)+ coord:
  `abm_auto/coord/`。
- 平台:`abm_auto/_platform.py`(中性,gis 通过 shim 复用)。
- 研究文档:`docs/studies/<name>/`(PREDICTIONS-locked.md + FINDINGS*.md + results*.json +
  verdict-bundle*.json),共 9 套。
- 测试:`tests/classics/`(101 个)+ `tests/coord/`(23 个)。
- 设计:`docs/superpowers/specs/2026-06-28-coord-response-abm-v3-agentbased-design.md`、
  `2026-06-29-classic-network-abm-reproductions-design.md`(batch 1)、
  `2026-06-29-classic-abm-reproductions-batch2-design.md`(batch 2)。
- 复审脚本:`<session>/workflows/scripts/` 下 3 个对抗复审 workflow。
