# EigenLayer — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 EigenLayer 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | EigenLayer / EIGEN |
| 实体类型 | `app`（应用型，restaking；前端标「治理代币」） |
| 市值（as_of 2026-08-04） | ~$163M |
| 股东回报率 | ~0%（股息 0% + 回购 0%） |
| 置信度 | low |
| 数据源优先级 | 链上 > 官方治理 > 估算 > DefiLlama（dailyRevenue） |

## 二、收入判定（核心）

**Boss 定稿口径（第 6 批治理代币统一）：只统计利润；股东回报 = 0（不回购）。当前协议层不抽成 → 收入 = 0**

```
收入 = DefiLlama dailyRevenue 365d = $0（AVS 费用全流向 operator/restaker，协议端无收入）
净利 = $0（协议无收入；AVS fee 归 operator/restaker）
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议费（protocol fees） | 当前为 $0——AVS 费用全流向 operator/restaker（持 ETH/LST），EIGEN 无收入分配权 | DefiLlama `dailyRevenue` |

| 不计入 | 原因 |
|---|---|
| AVS 费用 | 全流向 operator/restaker（持 ETH/LST）；fee switch OFF，EIGEN 无收入分配权 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 治理代币（无股东回报） | `yield`（机制确凿为 0） | 0% |

- snapshot `shareholder_returns_usd_365d = 0`、`shareholder_yield_percent = 0`（机制确凿为 0，非数据缺失）；`pe = null`（回报为 0 → P/E 无意义）

## 四、关键计算逻辑（adapter.py）

`data/protocols/eigenlayer/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `config.json` + `data/all-protocols.json`，取 `market_cap_usd`（≈ $163M）、`tvl`（≈ $8.72B）
2. `revenue = metrics.trailing_365d_revenue_usd`（= 0，协议端无收入）
3. 毛利 = 收入（= 0）；净利 = 收入（增发 0、运营成本数据不可得）
4. `by_mechanism` 单条「治理代币（无股东回报）」：`usd_365d = 0`、`yield_percent = 0`（不回购，写 0 而非 null）
5. 派生估值：`pe = null`、`ps = null`（收入为 0 → 除零）、`payout = null`
6. verification：dailyRevenue 365d = $0（AVS 费用流向 operator/restaker）；EIGEN 不回购（fee switch OFF）；status = estimated

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| DefiLlama dailyFees / dailyRevenue | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ 协议端收入 = 0**：AVS (Actively Validated Services) 收取 fees，但 fee 分给 operator + restaker（持 ETH/LST），不给 EIGEN 持有人；restaking rewards 全流向 validator
- **EIGEN restaking 不创造持有人收益**：仅用于 EIGEN 内部 slashing / 治理
- **EIGEN 存在 unlock / 再质押排放**（无对价），当前无协议收入模型，不涉及增发成本扣减，但需关注稀释
- 若未来治理推出 fee switch 给 EIGEN，重新评估（AI 哨兵观察治理提案）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §19-25（第 6 批：EigenLayer 等治理代币统一口径）
- 配置文件：`data/protocols/eigenlayer/config.json`（revenue_recognition 字段）
