# Spark — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解该协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Spark / SPK |
| 实体类型 | `app`（lending，Sky 生态 SubDAO） |
| 市值（as_of 2026-08-04） | ~$47.8M |
| 股东回报率 | ~0%（股息 0% + 回购 0%，治理代币） |
| 置信度 | low |
| 数据源优先级 | 官方文档 > DefiLlama（dailyRevenue 为协议净收入口径） |

## 二、收入判定（核心）

**Boss 定稿口径：治理代币 —— 只统计利润；股东回报 = 0（SPK 收入流向 Sky 主 DAO）**（§19-25 第 6 批统一口径）

```
净利 = DefiLlama dailyRevenue 365d（SparkLend 协议费 $22,144,959）
股东回报 = 0
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| SparkLend 协议费 | DefiLlama dailyRevenue（协议净收入，LP 分润已扣） | DefiLlama dailyFees/dailyRevenue |

| 不计入 | 原因 |
|---|---|
| 流向 Sky 主 DAO 的收入 | Spark 收入通过 Smart Burn Engine 回购 SKY（Sky 主 DAO 代币），非 SPK 持有人 |
| SPK Airdrop 排放 | 无对价空投，非协议 fee 分润，不构成收入 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 治理代币（无股东回报） | `yield`（股息） | 0%（不回购/不分红/不销毁） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/spark/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `all-protocols.json` → `metrics.trailing_365d_revenue_usd` = $22,144,959（DefiLlama dailyRevenue 协议净收入）
2. 毛利 = 净利 = revenue（dailyRevenue 为协议净收入口径，LP 分润已在数据源扣减）
3. `by_mechanism.usd_365d = 0`（⚠️ 机制确凿为 0，非数据缺失）
4. 派生估值：`PS = mcap ÷ revenue ≈ 2.16`；`PE = null`（无股东回报，P/E 无意义）
5. verification 标注：SPK 治理代币不回购，收入流向 Sky 主 DAO 回购 SKY

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| DefiLlama dailyFees/dailyRevenue | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ 收入 ≠ 股东回报**：Spark 利润全归 Sky 主 DAO（SBE 回购 SKY），SPK 仅作 Spark SubDAO 治理代币，股东回报硬性为 0
- **SPK 为 2024-Q3 新启动代币**，TEV 机制仍在发展中，置信度 low
- **观察点**：若未来 Sky 治理提案启用 fee switch / buyback 给 SPK 持有人，需重新评估（AI 哨兵盯机制变化）
- **类比**：LDO / COMP 等老牌纯治理代币模式

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §19-25（第 6 批治理代币统一口径）
- 配置文件：`data/protocols/spark/config.json`（revenue_recognition 字段）
