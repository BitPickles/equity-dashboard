# dYdX — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 dYdX 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | dYdX / DYDX |
| 实体类型 | `application`（perpetuals，dYdX Chain Cosmos appchain） |
| 市值（as_of 2026-08-04） | ~$95.4M（DYDX Chain native，排除 ethDYDX 孤儿） |
| 股东回报率 | ~1.36%（股息 0.23% + 回购 1.14%） |
| 置信度 | medium |
| 数据源优先级 | dYdX Foundation 月度报告 > 链上回购账户 > 提案 #313 > DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：收入 = 净协议费（标注"含 affiliate/rebate 前、外部不可精确复算"）；回购 = 市价买入后质押（非销毁）**

```
收入 = 净协议费（DefiLlama dailyRevenue 365d）= $8,518,106（含 affiliate/rebate 前，不可精确复算）
回购 = mcap / P-F~88x = $95,400,332 / 88 = $1,084,095（提案 #313，75%）
质押分红 = 回购 × 15/75 = $216,819（USDC 分给 staker，15%）
股东回报合计 = $1,300,914 → 回报率 = 1.36%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 净协议费回购（提案 #313，75%） | 市价买入 DYDX 后质押（非销毁），存 Treasury 专用账户（dydx1zc0jd76...）；链上可验证 + Buyback Dashboard + 月度报告 | 官方月度报告 + 链上回购账户 |
| 质押分红（USDC，15%） | Cosmos x/distribution 模块按区块分给 staker；DYDX 通胀 staking 奖励 ~0.01% APY 极低 | 官方 + DefiLlama |

| 不计入 | 原因 |
|---|---|
| 前置补贴（affiliate/rebate） | 大量补贴归交易者（affiliate 30-50% 分成、Surge 50% rebate、零费率市场）——收入为毛口径，外部不可精确复算 |
| ethDYDX（ERC-20） | bridge 已永久关闭（2025-06-13），41.7M ethDYDX 滞留 ETH 主网无法兑换或 stake，持有人捕获权 = 0 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 净协议费回购（提案 #313，75%） | `buyback`（回购=质押非销毁，勿误标 destroy） | 1.14% |
| 质押分红（USDC，Cosmos x/distribution，15%） | `yield`（股息） | 0.23% |

## 四、关键计算逻辑（adapter.py）

`data/protocols/dydx/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 all-protocols.json → `metrics.trailing_365d_revenue_usd`（净协议费 = $8,518,106，含 affiliate/rebate 前）+ `market_cap_usd`（DYDX Chain native，排除 ethDYDX 孤儿）
2. 回购额：链上回购账户无公开 dashboard → 按判定书 P/F~88x 反推 `buyback_usd = mcap / 88 = $1,084,095`
3. 质押分红：提案 #313 比例 `staking_usd = buyback_usd × 15/75 = $216,819`
4. 毛利 = 净利 = 收入（永续应用无 LP 分润成本；无挖矿增发成本模型）；真实净协议费低于毛口径
5. 股东回报 by_mechanism = [{mechanism: "净协议费回购（75%）", type: "buyback", usd: $1,084,095, yield: 1.14%}, {mechanism: "质押分红 USDC（15%）", type: "yield", usd: $216,819, yield: 0.23%}]
6. 派生估值：pe = mcap/returns = 73.33，ps = 11.20，payout_ratio = 0.1527
7. 注意：buyback 类型会被系统归入 destroy 汇总组（质押非销毁、非真销毁，语义以 note 标注）

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 官方：dYdX Foundation 月度报告 + Buyback Dashboard | 月频 | ai-watch-governance.py |
| 链上：回购账户 | 日频 | update-dydx-tev.py |

## 六、历史验证与注意点

- **⚠️ 改名 Arcus 但 DYDX 未变**：交易所品牌更名 Arcus（2026-07，上线 Robinhood Chain/Arbitrum）；dYdX Chain（Cosmos）与 DYDX 代币未更名，继续社区治理
- **⚠️ 回购 = 买入后质押（非销毁）**：市价买入 DYDX 后质押于 Treasury 专用账户，勿计入销毁；链上无公开 tracker，回购额按 P/F~88x 反推（外部不可精确复算）
- **收入剧降**：非头部协议——永续量份额 ~0.4%（第 9-14 名），TVL ~$1.2 亿；收入 Q4'25 $3.3M → Q1'26 $0.99M → Q2'26 ~$0.6M
- **ethDYDX 死透**：2025-06-13 bridge 永久关闭，ethDYDX 持有 0 捕获；分母必须用 DYDX Chain native mcap
- **DefiLlama 可能混 V3/V4 数据**：V3（Ethereum zk-rollup）已 sunset，历史 365d 数据可能仍计入聚合
- **提案 #313 分配**：75% 回购 / 15% 质押 / 5% MegaVault / 5% 金库（2025-11-13 通过）；Boss 怀疑成立：大量补贴回流交易者，代币持有者实质回报很低

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §12（Boss 2026-08-02 定稿 + Agent 调研）
- 配置文件：`data/protocols/dydx/config.json`（revenue_recognition 字段，payout_ratio=0.75）
- 数据维护说明：`data/protocols/dydx/README.md`（如有）
