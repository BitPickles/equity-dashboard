# Aster（AsterDEX）— 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Aster 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Aster (AsterDEX) / ASTER |
| 实体类型 | `application`（perp_dex，BNB Chain DEX） |
| 市值（as_of 2026-08-04） | ~$1.61B |
| 股东回报率 | ~1.46%（股息 1.46% + 回购 0%） |
| 置信度 | high |
| 数据源优先级 | 链上（新回购钱包 + 1:1 销毁记录）> 官方公告 > DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：99% 平台手续费 → TWAP 回购 ASTER → 分发给 veASTER 质押者（分配型 🟢）**

```
收入 = 平台手续费（DefiLlama dailyRevenue 365d）
股东回报 = 收入 × payout_ratio(0.99)
        = $23,699,571 × 0.99 = $23,462,575
回报率 = 股东回报 ÷ 市值 = 1.46%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 平台手续费 | DefiLlama dailyRevenue 365d = $23,699,571；99% 计入 TEV（2026-06-17 机制：99% 每日手续费→TWAP 回购 ASTER→veASTER） | DefiLlama |
| Spot 上币费 | 5 万 USDT/次并入回购（次数不可得 → 注记） | 官方 |

| 不计入 | 原因 |
|---|---|
| 1:1 储备销毁 | 烧的是未流通储备币（总供应 80亿→30亿），只减少未来潜在稀释，不构成对流通持币人的价值流；「198%」为营销话术，Boss 拍板设 99% |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| TWAP 回购 ASTER → veASTER 质押者（99% 手续费） | `yield`（股息） | 1.46% |

> **2026-08-04 口径修正**：回购后分发 = 股息 → `type=yield`（美股口径：回购后分发 = 分红/股息），非回购销毁。

## 四、关键计算逻辑（adapter.py）

`data/protocols/aster/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 all-protocols.json → `metrics.trailing_365d_revenue_usd`（DefiLlama dailyRevenue 365d = $23,699,571）；若缺失则用链上兜底 `validation.buy_365d_aster × aster_price_usd`
2. 从 config.json `revenue_recognition.calculation.payout_ratio` 读判定书口径（0.99，只读）；缺失则默认 0.99
3. `returns = revenue × payout_ratio`；`returns_yield = returns / mcap × 100%`
4. 毛利 = 净利 = 收入（dailyRevenue 已扣 LP 分润；无持续增发成本——1:1 储备销毁作注记不计入）
5. 股东回报 by_mechanism = [{mechanism: "TWAP 回购→veASTER", type: "yield", usd: $23,462,575, yield: 1.46%}]
6. 派生估值：pe = mcap/returns = 68.68，payout_ratio = 0.99

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 链上：新回购钱包 + 1:1 销毁记录（2026-06-17 后机制） | 日频 | update-aster.py |
| 官方：AI 抓公告（机制升级检测） | 事件驱动 | ai-watch-official.py |

## 六、历史验证与注意点

- **⚠️ 2026-06-17 机制更新**：99% 每日平台手续费 → TWAP 回购 ASTER → 分发给 veASTER 质押者（Loyalty Rewards：30 万基础奖励 + 当期回购量）；此前旧口径（Stage5/6 treasury buyback 60-80%）已废弃
- **⚠️ 2026-08-04 口径修正**：回购后分发给 veASTER 质押者 = 股息 `type=yield`，非回购销毁
- **1:1 储备销毁不计入**：烧未流通储备币，只减少潜在稀释；财报页作注记
- **M0/M1 修复项**：新回购钱包 + 2026-06-17 后链上数据（update-aster-tev.py / Moralis 需切换）；当前 M0 以 DefiLlama dailyRevenue 口径组装
- **Spot 上币费**：5 万 USDT/次并入回购，但次数不可得 → 仅注记

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §3（Boss 2026-08-02 定稿 + 2026-08-04 修正）
- 配置文件：`data/protocols/aster/config.json`（revenue_recognition 字段，payout_ratio=0.99）
- 数据维护说明：`data/protocols/aster/README.md`（如有）
