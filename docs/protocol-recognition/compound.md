# Compound — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Compound 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Compound / COMP |
| 实体类型 | `app`（应用型，lending；前端标「治理代币」） |
| 市值（as_of 2026-08-04） | ~$166M |
| 股东回报率 | ~0%（股息 0% + 回购 0%） |
| 置信度 | low |
| 数据源优先级 | 链上 > 官方治理 > 估算 > DefiLlama（dailyRevenue） |

## 二、收入判定（核心）

**Boss 定稿口径（第 6 批治理代币统一）：只统计利润（毛利、净利能看出来就行）——收入 → 毛利（扣 LP/成本）→ 净利照算并展示；股东回报 = 0（不回购）**

```
收入 = DefiLlama dailyRevenue 365d ≈ $216.7K（reserve factor 口径，协议净收入）
净利 = 收入 − 增发(0) − 运营成本(数据不可得) ≈ $216.7K
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议费（protocol fees） | DefiLlama dailyRevenue（reserve factor 口径，协议净收入） | DefiLlama `dailyRevenue` |

| 不计入 | 原因 |
|---|---|
| 借贷 fees 给 LP | 借贷 fees（~$180M+/年）100% 给 LP；协议端 reserve factor 收入很小（fee switch OFF，多次治理讨论未通过） |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 治理代币（无股东回报） | `yield`（机制确凿为 0） | 0% |

- snapshot `shareholder_returns_usd_365d = 0`、`shareholder_yield_percent = 0`（机制确凿为 0，非数据缺失）；`pe = null`（回报为 0 → P/E 无意义）、`ps = 765.51`

## 四、关键计算逻辑（adapter.py）

`data/protocols/compound/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `config.json` + `data/all-protocols.json`，取 `market_cap_usd`（≈ $166M）、`tvl`（≈ $1.42B）
2. `revenue = metrics.trailing_365d_revenue_usd`（≈ $216.7K，reserve factor 口径）
3. 毛利 = 收入（LP 分润已在数据源扣减）；净利 = 收入（增发 0、运营成本数据不可得）；净利留存协议储备
4. `by_mechanism` 单条「治理代币（无股东回报）」：`usd_365d = 0`、`yield_percent = 0`（不回购，写 0 而非 null）
5. 派生估值：`pe = null`、`ps = mcap / revenue`（765.51）、`payout = null`
6. verification：净利 = dailyRevenue 365d（reserve factor 口径）；COMP 不回购（fee switch OFF）；status = estimated

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| DefiLlama dailyFees / dailyRevenue | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ 借贷 fees 100% 给 LP**：Compound 协议费（~$180M+/年）绝大部分归 LP，协议端收入仅 reserve factor 部分（$216.7K/365d），fee switch 从未开启
- **fee switch 提案多次讨论未通过**：社区多次讨论开启费用分配但未通过治理投票；若未来开启，潜在 TEV 基数较大
- COMP 供应上限 1000 万（接近全流通），无持续增发成本
- 净利留存协议储备，不回购的钱进国库/支出 → 损益表「留存」行标注去向

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §19-25（第 6 批：Compound 等治理代币统一口径）
- 配置文件：`data/protocols/compound/config.json`（revenue_recognition 字段）
