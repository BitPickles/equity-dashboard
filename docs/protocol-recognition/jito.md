# Jito — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解该协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Jito / JTO |
| 实体类型 | `app`（liquid_staking + MEV，Solana） |
| 市值（as_of 2026-08-04） | ~$245.0M |
| 股东回报率 | ~0%（股息 0% + 回购 0%，治理代币） |
| 置信度 | low |
| 数据源优先级 | 官方文档（docs.jito.network）> DefiLlama（dailyRevenue 为协议净收入口径） |

## 二、收入判定（核心）

**Boss 定稿口径：治理代币 —— 只统计利润；股东回报 = 0（JTO 纯治理，MEV 归 JitoSOL）**（§19-25 第 6 批统一口径）

```
净利 = DefiLlama dailyRevenue 365d（MEV 小费 $13,763,565）
股东回报 = 0
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| MEV 小费（协议净收入） | DefiLlama dailyRevenue（MEV 分润给 JitoSOL 部分已扣） | DefiLlama dailyFees/dailyRevenue |

| 不计入 | 原因 |
|---|---|
| MEV tips（96% 归 JitoSOL） | JitoSOL 持有人拿 ~5% APY（含 staking + MEV），JTO 不分润 |
| JTO staking 收入分成 | 仍为 planned（规划中），未生效 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 治理代币（无股东回报） | `yield`（股息） | 0%（不回购/不分红/不销毁） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/jito/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `all-protocols.json` → `metrics.trailing_365d_revenue_usd` = $13,763,565（DefiLlama dailyRevenue 协议净收入）
2. 毛利 = 净利 = revenue（dailyRevenue 为协议净收入口径，MEV 分润给 JitoSOL 部分已扣）
3. 增发处理：JTO 供应上限 10 亿（流通 4.3 亿，持续 unlock 为无对价稀释）→ 不涉及增发成本扣减
4. `by_mechanism.usd_365d = 0`（机制确凿为 0，非数据缺失）
5. 派生估值：`PS = mcap ÷ revenue ≈ 17.80`；`PE = null`（无股东回报）
6. verification 标注：JTO 不回购（MEV 归 JitoSOL），净利留存 Jito Foundation，JTO staking 收入分成 planned

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| DefiLlama dailyFees/dailyRevenue | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ MEV 收益归 JitoSOL 不归 JTO（易混淆）**：JitoSOL 持有人拿 ~5% APY（staking + MEV），JTO 持有人为 0；MEV 收益按 96% 归 JitoSOL + 4% Jito Foundation
- **JTO staking 在规划中**：收入分成提案讨论中，若启动需重新评估股东回报
- **JTO 持续 unlock**：供应上限 10 亿、流通 4.3 亿，解锁为无对价稀释（注记，不算成本）
- **类比**：LDO / COMP 等老牌纯治理代币模式

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §19-25（第 6 批治理代币统一口径）
- 配置文件：`data/protocols/jito/config.json`（revenue_recognition 字段）
