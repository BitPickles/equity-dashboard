# Kamino — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解该协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Kamino Finance / KMNO |
| 实体类型 | `app`（lending，Solana） |
| 市值（as_of 2026-08-04） | ~$93.8M |
| 股东回报率 | ~0%（股息 0% + 回购 0%，治理代币） |
| 置信度 | low |
| 数据源优先级 | 官方治理（Kamino gov）> DefiLlama（dailyRevenue 为协议净收入口径） |

## 二、收入判定（核心）

**Boss 定稿口径：治理代币 —— 只统计利润；股东回报 = 0（KMNO 不回购）**（§19-25 第 6 批统一口径）

```
净利 = DefiLlama dailyRevenue 365d（$12,082,624）
股东回报 = 0
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议收入 | DefiLlama dailyRevenue（协议净收入，借贷 fees 给 LP 部分已扣） | DefiLlama dailyFees/dailyRevenue |

| 不计入 | 原因 |
|---|---|
| KMNO staking boost 奖励 | 是 farming 奖励加成（起始 3% 每天 +0.1%），奖励来自代币国库排放（季度 100M），非协议 fee 分润 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 治理代币（无股东回报） | `yield`（股息） | 0%（不回购/不分红/不销毁） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/kamino/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `all-protocols.json` → `metrics.trailing_365d_revenue_usd` = $12,082,624（DefiLlama dailyRevenue 协议净收入）
2. 毛利 = 净利 = revenue（dailyRevenue 为协议净收入口径，借贷 fees 给 LP 部分已扣）
3. 增发处理：KMNO 季度 100M 排放（Season 奖励）为无对价稀释 → 按判定书不扣成本，`treatment = "none"`
4. `by_mechanism.usd_365d = 0`（机制确凿为 0，非数据缺失）
5. 派生估值：`PS = mcap ÷ revenue ≈ 7.76`；`PE = null`（无股东回报）
6. verification 标注：KMNO 不回购（staking 为 farming boost 非分润），净利留存协议

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| DefiLlama dailyFees/dailyRevenue | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ KMNO staking 非真 TEV**：staking 只提供 farming boost（3% → 100% 上限），奖励来自代币国库 inflation，不是协议 fee 分润（2026-04-27 从 PARTIAL 降级为 NONE）
- **季度 100M KMNO 排放 + 6 个月 vesting = 无对价稀释**（negative TEV），非分润
- **借贷 fees 100% 给 LP**：Kamino 是优秀 Solana 借贷协议（$3.34B AUM，零坏账），但 KMNO 目前无 fee distribution 机制
- **观察点**：2026 路线图专注机构产品（固定利率、链下抵押品），若未来引入 fee switch / buyback 需重新评估

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §19-25（第 6 批治理代币统一口径）
- 配置文件：`data/protocols/kamino/config.json`（revenue_recognition 字段）
