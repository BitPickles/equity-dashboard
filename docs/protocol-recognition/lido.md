# Lido — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Lido 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Lido / LDO |
| 实体类型 | `app`（应用型，liquid_staking；前端标「治理代币」） |
| 市值（as_of 2026-08-04） | ~$270M |
| 股东回报率 | ~0%（股息 0% + 回购 0%） |
| 置信度 | low |
| 数据源优先级 | 链上 > 官方治理 > 估算 > DefiLlama（dailyRevenue） |

## 二、收入判定（核心）

**Boss 定稿口径（第 6 批治理代币统一）：只统计利润（毛利、净利能看出来就行）——收入 → 毛利（扣 LP/成本）→ 净利照算并展示；股东回报 = 0（不回购）**

```
收入 = DefiLlama dailyRevenue 365d ≈ $38.92M（staking fee 中 DAO 归属部分，协议净收入）
净利 = 收入 − 增发(0) − 运营成本(数据不可得) ≈ $38.92M
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议费（protocol fees） | DefiLlama dailyRevenue（staking fee 中 DAO 归属部分） | DefiLlama `dailyRevenue` |

| 不计入 | 原因 |
|---|---|
| stETH 质押收益 | ~3% ETH staking yield 归 stETH 持有人，非 LDO 股东回报 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 治理代币（无股东回报） | `yield`（机制确凿为 0） | 0% |

- snapshot `shareholder_returns_usd_365d = 0`、`shareholder_yield_percent = 0`（机制确凿为 0，非数据缺失）；`pe = null`（回报为 0 → P/E 无意义）

## 四、关键计算逻辑（adapter.py）

`data/protocols/lido/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `config.json` + `data/all-protocols.json`，取 `market_cap_usd`（≈ $270M）、`tvl`（≈ $18.99B）
2. `revenue = metrics.trailing_365d_revenue_usd`（≈ $38.92M）
3. 毛利 = 收入（dailyRevenue 为协议净收入，staking fee 中 DAO 归属部分）
4. 净利 = 收入（增发 0、运营成本数据不可得）；净利留存 Lido DAO Treasury
5. `by_mechanism` 单条「治理代币（无股东回报）」：`usd_365d = 0`、`yield_percent = 0`（不回购，写 0 而非 null）
6. 派生估值：`pe = null`、`ps = mcap / revenue`（6.93）、`payout = null`
7. verification：净利 = dailyRevenue 365d；LDO 不回购（fee switch OFF）；status = estimated

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| DefiLlama dailyFees / dailyRevenue | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ 净利留存 Lido DAO Treasury**：协议收入 100% 进 DAO 国库，LDO 持有人不分润；损益表「留存」行标注去向（国库/协议支出）
- **stETH 收益不计入 LDO 股东回报**：staking 收益归 stETH 持有人（~3% ETH staking yield）
- **LDO 供应可持续增发**（治理可增发），但无对价收入模型，不涉及增发成本扣减
- 潜在 fee switch 基数大：365d 协议费用 ~$78M，若未来开启 fee switch 给 LDO，需重新评估（AI 哨兵观察治理提案）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §19-25（第 6 批：Lido 等治理代币统一口径）
- 配置文件：`data/protocols/lido/config.json`（revenue_recognition 字段）
