# Story: Ou7L

## Research Motivation

This model simulates a financial network of residents, banks, and private digital money (PDM, including stablecoins). It is designed to explore how policy measures, bank reserve ratios, market volatility, and residents' saving behavior interact to influence systemic risk, capital flows, and overall financial stability. Banks are classified by their proximity to policy nodes: Type 1 (highest proximity, closest to policy nodes), Type 2 (medium proximity), and Type 3 (lowest proximity, farthest from policy nodes).

## Research Goal

Agents:

Residents allocate their savings across different PDM categories based on income, risk perception, and interest rates.

## Agent Description

**Bank** agent with properties:
- `bank-type`
- `银行proximity`
- `1`
- `最高`
- `离政策节点最近`
- `2`
- `中等`
- `3`
- `最低`
- `离政策节点最远`
- `原有粗粒度口径`
- `deposits`
- `存款总额`
- `为兼容旧逻辑保留`
- `reserves`
- `储备金`
- `loans`
- `贷款总额`
- `npl-ratio`
- `不良贷款率`
- `risk-level`
- `风险水平`
- `liquidity-ratio`
- `流动性比率`
- `原有用于展示`
- `capital-adequacy`
- `资本充足率`
- `原有粗略口径`
- `is-active`
- `是否活跃`
- `failure-step`
- `破产步数`
- `initial-deposits`
- `初始存款`
- `node-size`
- `节点大小`
- `node-color`
- `节点颜色`
- `coreness`
- `k-core值`
- `is-core`
- `是否核心`
- `新增`
- `会计科目细分`
- `liab-demand`
- `活期存款`
- `liab-time`
- `定期存款`
- `liab-stablecoin`
- `稳定币负债`
- `银行发行`
- `托管型`
- `liab-interbank`
- `同业负债`
- `assets-bonds`
- `债券`
- `HQLA`
- `assets-interbank`
- `同业资产`
- `equity-capital`
- `所有者权益`
- `资本`
- `新增`
- `巴塞尔简化监管比率`
- `rwa`
- `风险加权资产`
- `hqla`
- `高质量流动性资产`
- `car`
- `资本充足率`
- `Capital`
- `RWA`
- `lcr`
- `流动性覆盖率`
- `leverage-ratio`
- `杠杆率`
- `Capital`
- `总资产`
- `新增`
- `利率报价`
- `deposit-rate`
- `银行存款报价`

**Household** agent with properties:
- `pdm-combination`
- `PDM组合`
- `1-5种类型`
- `assets`
- `PDM资产`
- `5个元素的列表`
- `deposit`
- `银行存款`
- `兼容旧逻辑的总额`
- `risk-tolerance`
- `风险承受能力`
- `原有`
- `income-level`
- `收入水平`
- `1`
- `低`
- `2`
- `中`
- `3`
- `高`
- `education-level`
- `教育水平`
- `1`
- `低`
- `2`
- `中`
- `3`
- `高`
- `main-bank`
- `主银行ID`
- `connected-banks`
- `连接的银行ID列表`
- `bank-deposits`
- `各银行存款分配`
- `与connected-banks对应的列表`
- `transfer-history`
- `转移历史`
- `pdm-sell-history`
- `PDM出售历史`
- `node-color`
- `节点颜色`
- `node-size`
- `节点大小`
- `coreness`
- `k-core值`
- `is-core`
- `是否核心`
- `新增`
- `家庭账户细分与偏好`
- `hh-dep-demand`
- `家庭活期`
- `hh-dep-time`
- `家庭定期`
- `hh-lambda-risk`
- `风险厌恶`
- `λ`
- `hh-phi-liq`
- `流动性偏好`
- `φ`

**Policy** agent with properties:
- `policy-type`
- `政策类型`
- `1`
- `财政`
- `2`
- `货币`
- `influence-radius`
- `影响半径`
- `coreness`
- `k-core值`
- `is-core`
- `是否核心`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

Interface controls:

Sliders: set tax rate, regulation intensity, market volatility, interest rates, and bank reserve ratios.

## Parameters of Interest

- `fiscal-policy`: range [-1.0, 1.0], default=0.0, step=1.0
- `monetary-policy`: range [-1.0, 1.0], default=0.0, step=1.0
- `base-volatility-prob`: range [0.01, 0.5], default=0.1, step=0.01
- `stablecoin-reserve-ratio`: range [0.1, 1.0], default=0.8, step=0.1
- `stablecoin-volatility`: range [0.1, 1.0], default=0.8596982223313896, step=0.1
- `bank-bailout-probability`: range [0.0, 1.0], default=0.5, step=0.1
- `num-banks`: range [1.0, 50.0], default=21.0, step=1.0
- `num-households`: range [10.0, 1000.0], default=200.0, step=10.0
- `transfer-after-bankruptcy-prob`: range [0.0, 1.0], default=0.9, step=0.05
- `max-bank-connections`: range [1.0, 5.0], default=3.0, step=1.0

## Output of Interest

- Systemic Risk
- Bank Status
- Volatility Indicators
- Deposits and Assets
- Average Deposit Share
- PDM Shares
- Network Structure

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `ou7L.nlogo`
