# OKB — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 OKB 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | OKB / OKB |
| 实体类型 | `platform_token`（平台币，OKX 交易所 + X Layer L2 gas） |
| 市值（as_of 2026-08-04） | ~$1.50B |
| 股东回报率 | ~5.2%（股息 5.2% + 回购 0%） |
| 置信度 | high |
| 数据源优先级 | 官方公告（回购终止 / OKX Earn APY） > 链上（合约 mint/burn 移除可验证） > 估算 |

## 二、收入判定（核心）

**Boss 定稿口径：平台币赋能即收入；质押收益按 BNB asBNB 同口径计入；回购销毁 2025-08 已终止不计入**（2026-08-04 拍板补质押收益）

```
收入 = OKB OKX Earn 质押 APR × 市值 ≈ 5.2% × $1.50B ≈ $78M/年
回购/销毁 = 0（2025-08 永久终止，合约 mint/burn 功能移除，供应锁定 21M）
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| OKX Earn 质押收益 | OKB Flexible Staking ~5.2% APR（官方 2026-07，日结复利），按 BNB asBNB 同口径计入 | OKX 官方 2026-07 |

| 不计入 | 原因 |
|---|---|
| 回购销毁 | 2025-08 OKX 治理决议一次性销毁 65.26M OKB 后永久锁定供应 21M，合约 mint/burn 功能写死移除，无持续机制 |
| Jumpstart 打新 | 判定书 §5 明确忽略 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| OKB OKX Earn 质押收益（~5.2% APY） | `yield`（股息） | 5.2% |

- 股东回报合计 $78,170,364/年 ÷ 市值 ≈ **5.2%**（snapshot `shareholder_returns_usd_365d = $78.17M`，`shareholder_yield_percent = 5.2`，`payout_ratio = 1.0`）

## 四、关键计算逻辑（adapter.py）

`data/protocols/okb/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `config.json` + `data/all-protocols.json`，取 `market_cap_usd`（≈ $1.50B）
2. `STAKING_APY = 0.052`（OKX 官方 2026-07 Flexible Staking APR 5.2%，常量写死）
3. `staking_usd = STAKING_APY × mcap`（≈ $78.17M）；`total_rev = staking_usd`
4. 收入拆分：`burn_usd_365d = 0`（回购销毁 2025-08 终止）、`staking_rewards_usd_365d = staking_usd`、launchpad 为 null
5. 毛利/净利 = 收入（平台币无 LP 成本模型，毛利率/净利率 = 100%，标注为非经营性利润）；增发 = 0（供应永久锁定，无 mint/burn）
6. `by_mechanism` 单条 yield 机制（$78.17M / 5.2%）
7. 派生估值：`pe = ps = mcap / staking_usd`（19.23）、`payout_ratio = 1.0`
8. verification：OKX 2025-08 治理决议（链上可验证），status = verified

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| OKX Earn 质押 APR（官方 2026-07） | 季度复核（静态） | 无（静态维护） |

## 六、历史验证与注意点

- **⚠️ 回购销毁 2025-08 已终止，是「明确退出 TEV」而非暂停**：与 GMX paused（等触发条件可恢复）不同，OKB 是治理决议永久停止、合约写死；历史 buyback 数据（2025-08 之前）不延续、不外推作 TEV
- **⚠️ 质押收益 = OKX 储蓄产品利息，非协议利润**：OKX Earn 是中心化储蓄产品，详情页须注记（口径标注，非经营性利润）
- 供应永久锁定 21M（类比 BTC 限额）；OKB 仍是 OKX 平台权益代币（X Layer L2 gas / 交易折扣），但不构成销毁通缩价值捕获
- 链上证据：OKB 合约 `0x75231f58b43240c9718dd58b4967c5114342a86c` mint/burn 功能已移除，365d burn = 0
- APY 需季度复核（OKX 官方披露为准）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §5（OKB，Boss 2026-08-02 + 2026-08-04 补质押收益）
- 配置文件：`data/protocols/okb/config.json`（revenue_recognition 字段）
