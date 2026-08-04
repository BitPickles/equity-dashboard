# Pendle — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Pendle 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Pendle / PENDLE |
| 实体类型 | `application`（yield，收益代币化） |
| 市值（as_of 2026-08-04） | ~$0.24B |
| 股东回报率 | ~7.92%（股息 7.92% + 回购 0%） |
| 置信度 | medium |
| 数据源优先级 | 链上（sPENDLE 回购 executor，多链）> DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：80% 确定——80% 协议收入回购 PENDLE → 分给 sPENDLE 质押者（分配型 🟢）**

```
收入 = DefiLlama dailyRevenue 365d = $18,665,264（协议净额）
股东回报 = dailyHoldersRevenue 365d = $18,665,264（80% 分发实测）
回报率 = $18,665,264 ÷ 市值 $0.24B = 7.92%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议收入（80% 回购分发） | YT 费 5% + Swap 费 80% 归协议/voters；80% 回购 PENDLE 分给 sPENDLE 质押者（2026-01-29 起 sPENDLE 时代） | DefiLlama dailyHoldersRevenue |

| 不计入 | 原因 |
|---|---|
| LP 做市收益 | LP（PT/YT 做市商）收益来自市场价差与手续费分成，不计入协议收入；dailyRevenue 为协议净额 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| sPENDLE 回购 + 分发（80% 协议收入） | `yield`（股息） | 7.92% |

## 四、关键计算逻辑（adapter.py）

`data/protocols/pendle/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 config.json → `payout_ratio = 0.8`（判定书：80% 确定）；all-protocols.json → `metrics.trailing_365d_revenue_usd`（dailyRevenue = $18,665,264）+ `trailing_365d_tev_usd`（dailyHoldersRevenue = $18,665,264）
2. 股东回报数值 = dailyHoldersRevenue 365d（sPENDLE 分发实测）；`yield_pct = holders_365d / mcap × 100% = 7.92%`
3. 用 tev-records.json 365d 窗口（完整 12 个日历月）交叉核对（$18,819,548）
4. 毛利 = 净利 = 协议净收入（80% 回购分发 sPENDLE 计入股东回报，20% 留存 treasury）；无持续大额增发
5. 股东回报 by_mechanism = [{mechanism: "sPENDLE 回购+分发（80%）", type: "yield", usd: $18,665,264, yield: 7.92%, verified: "partial"}]
6. 派生估值：pe = ps = mcap/total_returns = 12.63，payout_ratio = 1.0

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 链上：sPENDLE 回购 executor（多链） | 日频 | update-pendle-tev.py |
| DefiLlama dailyRevenue | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ 80% 比例链上不可独立验证**：Pendle 多链部署（8+ 条链：Ethereum/Arbitrum/BSC/Optimism/Mantle/Base/Berachain/Sonic），无公开单一 buyback executor 合约 → verification=partial
- **⚠️ sPENDLE 入金混杂**：staking 合约 0x07282... 入金含（a）用户 stake（b）协议 distribution（c）跨链 bridge，无法链上分离
- **sPENDLE 机制**：2026-01-29 起 vePENDLE sunset → sPENDLE（14 天解锁冷却期，或支付 5% 费用即时赎回）；vePENDLE 锁定冻结
- **2025-09 治理变更**：协议收入分配从 100% → 80%（留 20% treasury），原始提案文档未在 gov.pendle.finance 找到，可信度依赖官方宣称
- **数据核对**：DefiLlama dailyHoldersRevenue $22.25M 占 dailyRevenue $26.17M 的 85%，接近官方 80% 比例 → 相对合理
- **收入来源**：YT fees 5% + Swap fees 80%（vePENDLE/sPENDLE voters）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §10（Boss 2026-08-02 定稿）
- 配置文件：`data/protocols/pendle/config.json`（revenue_recognition 字段，payout_ratio=0.8）
- 数据维护说明：`data/protocols/pendle/README.md`（如有）
