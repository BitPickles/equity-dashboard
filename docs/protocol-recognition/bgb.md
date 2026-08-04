# BGB — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 BGB 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Bitget Token / BGB |
| 实体类型 | `platform_token`（平台币，已与 Bitget 平台切割） |
| 市值（as_of 2026-08-04） | ~$1.89B |
| 股东回报率 | ~27.54%（股息 0% + 回购 27.54%） |
| 置信度 | low |
| 数据源优先级 | 官方公告（季度销毁）> 链上销毁地址 > DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：季度回购销毁 = 交易所+钱包业务利润的 20%（分配型 🟢 真金白银）**

```
收入 = 季度回购销毁年化
    = 官方公告中值 $1.3 亿/季度 × 4 = $520M/年
回报率 = $520M ÷ 市值 $1.89B = 27.54%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 季度回购销毁 | 每季度交易所+钱包业务利润的 20%（现货/合约/杠杆手续费 + Wallet Swap/合约/NFT 收入）；季度执行、次季初完成、每次公布数量 + 链上记录 | 官方公告 + 链上销毁地址 |

| 不计入 | 原因 |
|---|---|
| 打新（Launchpad） | Boss 确认：Bitget 基本没有打新，不计入 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 季度回购销毁（利润 20%） | `buyback`（回购销毁） | 27.54% |

## 四、关键计算逻辑（adapter.py）

`data/protocols/bgb/adapter.py` → `build_snapshot(proto_dir)`：

1. 官方公告已验证常量：`QUARTERLY_BURN_USD_LOW=$1.2 亿 / HIGH=$1.4 亿`（2025 Q1/Q2 各销毁 ~3000 万枚）
2. `quarterly_usd = (1.2 亿 + 1.4 亿) / 2 = $1.3 亿`；`burn_usd = $1.3 亿 × 4 = $520M`（年化）
3. 市值取 all-protocols.json `market_cap_usd`（或 config.market_data 兜底）
4. `yield_pct = burn_usd / mcap × 100% = 27.54%`
5. 毛利 = 净利 = 收入（平台币无 LP 分润成本；无持续增发——2024-12 一次性销毁 8 亿后总供应 12 亿，100% 全流通）
6. 股东回报 by_mechanism = [{mechanism: "季度回购销毁（利润 20%）", type: "buyback", usd: $520M, yield: 27.54%}]
7. 派生估值：pe = ps = mcap/burn = 3.63，payout_ratio = 1.0

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 官方：AI 抓季度销毁公告（数量 + 日期） | 季度 + 日复核 | ai-watch-official.py |
| 链上：销毁地址复核（0x19de...828a28 → 0x000...000） | 日频 | update-bgb-tev.py |

## 六、历史验证与注意点

- **⚠️ 销毁源头钱包未公开**：Bitget 未公开 buyback executor 钱包，无法链上验证销毁的 BGB 是市场真金白银买回还是公司金库自持转账（类 JustLend pocket-to-pocket 嫌疑）→ confidence=low
- **⚠️ 口径更新**：config 原标 unverified / tevRatio=0；判定书（2026-08-02）按官方公告口径更新为利润 20% 季度回购销毁
- **供应历史**：2024-12 一次性销毁 8 亿枚（总供应 40%，$5B+）→ 总供应 20亿 → 12 亿，100% 全流通
- **参考数值**：2025 Q1/Q2 各销毁 ≈3000 万枚（$1.2-1.4 亿）；2026 Q2 交易量更高，最新季度以官方公告为准（当前保守用 2025 数据年化）
- **不可仅靠 DefiLlama**：CEX 数据不透明，需官方公告 + 链上销毁地址双源

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §4（Boss 2026-08-02 定稿 + 最新调研）
- 配置文件：`data/protocols/bgb/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/bgb/README.md`（如有）
