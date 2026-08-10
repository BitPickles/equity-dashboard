# GMX — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 GMX 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | GMX / GMX |
| 实体类型 | `application`（perp_dex） |
| 市值（as_of 2026-08-04） | ~$64.1M |
| 股东回报率 | ~0%（股息 0% + 回购 0%） |
| 置信度 | low |
| 数据源优先级 | 链上（gov.gmx.io 提案 #5042）> 官方治理 > DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：锁定期内股东回报实质为 0 —— 27% 协议费用全额转国库（回购但不向质押者分发，回购-留存模式）**

```
收入（365d）→ 扣 LP（已在 DefiLlama dailyRevenue 扣减）→ 净利 $12.68M → 留存 27% → 股东回报 = 0
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 平台费（V2 perp + spot 交易费） | DefiLlama dailyRevenue 365d，协议净收入（LP 分润已扣）；365d ≈ $12.68M | DefiLlama `summary/fees/gmx?dataType=dailyRevenue` |

| 不计入 | 原因 |
|---|---|
| 质押分红 | 已暂停（2026-03-04 "Restore Price Discovery"），27% 协议费用全额转国库（公开市场回购 + PCV 积累），不再向 sGMX 实时分发 ETH/AVAX |
| DefiLlama dailyHoldersRevenue | 365d $12.3M 含暂停前历史数据，不代表当前 staker 实际收益（30d 滚动 ~$0.6M 才是近期实况） |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 27% 协议费回购留存（Treasury 累积，非流通） | `buyback`（回购） | 0%（锁定至 $90） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/gmx/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `all-protocols.json` 的 `metrics.trailing_365d_revenue_usd`（DefiLlama V2 交易费 dailyRevenue 365d，协议净收入 ≈ $12.68M，LP 分润已在数据源扣减）
2. 读 `tev-records.json` 交叉核对 DefiLlama dailyHoldersRevenue 月聚合（含暂停前历史，仅注记，不入主数字）
3. 股东回报确凿为 0（非 null）：by_mechanism `usd_365d=0`、`shareholder_yield_percent=0`——回购进国库不流通，触发条件 GMX 价格 ≥ $90 未达
4. 毛利 = 收入（dailyRevenue 已是净额口径，无 LP 成本列）；增发 = none（供应固定 ~1000 万枚）；净利 = $12.68M（全额留存国库，回购-留存模式）
5. 派生：P/S = mcap / revenue ≈ 5.06；股东回报 0 → P/E、派息率 = null

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| gov.gmx.io 提案 #5042 监控（价格阈值 $90 恢复条件） | 事件驱动 | ai-watch-governance.py |
| V2 交易费日频（dailyRevenue） | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ 分红暂停（2026-03-04 起）**：ETH/AVAX 实时分红机制停止，改 Treasury 累积 GMX 回购，等价格 ≥ $90 才解锁分配
- **⚠️ 恢复条件是价格阈值 $90**（不是市值；Boss 记法有误，对应市值 ~$9 亿）。当前价格 ~$6-7，**远未触发**（差 12 倍）；附加条件：质押余额不得低于峰值 80%，否则累积奖励（Staking Power）永久作废
- **"Staking Power" 累积权利 ≠ 真 TEV**：持有人只在累积权利，没有现金流入；Loyalty 机制可能因持仓回撤归零
- **DefiLlama 365d $12.3M 是历史数据**：含暂停前实时分红时期；30d 滚动 ~$0.6M 才是近期实况——前端 yield 必须标 0，勿用 365d 口径
- **esGMX（vesting token）不是真 TEV**：vesting 期满回流，非对流通持币人的价值流
- config 中 payout_ratio 0.27 = 协议费率（机制声明），不等于股东回报比例；`return_data.has_returns=false`

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §13
- 配置文件：`data/protocols/gmx/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/gmx/README.md`（如有）
