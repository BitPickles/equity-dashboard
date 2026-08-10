# PancakeSwap — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 PancakeSwap 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | PancakeSwap / CAKE |
| 实体类型 | `application`（dex） |
| 市值（as_of 2026-08-04） | ~$453.7M |
| 股东回报率 | ~12.93%（股息 0% + 回购 12.93%） |
| 置信度 | high |
| 数据源优先级 | 链上（0xdead 销毁）> 官方文档 > DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：增发按成本计算 → 增发 ~$1170 万 < 回购销毁 ~$5867 万 → 净利为正（净通缩，连续 34 个月）**

```
收入（协议收入口径）= 总费用 $270.5M − LP 分润 $176.7M ≈ $93.87M
毛利 = 协议收入 $93.87M
净利 = 毛利 − 增发成本 $11.7M = $82.17M（正）
股东回报 = 回购销毁 $58.67M ≈ 协议收入 60-65%（payout_ratio 0.625）🟢
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议费（协议收入口径） | 总费用中扣除 LP 分润（~65%）后的部分；回购销毁 ≈ 总费用 22% / 协议收入 60-65%；现货 15-23%、永续 20%、CAKE.PAD 100% | DefiLlama dailyHoldersRevenue + docs.pancakeswap.finance/cake-tokenomics |

| 不计入 | 原因 |
|---|---|
| LP 分润 | 总费用 $270.5M 中 LP 分润 $176.7M（~65%）归 LP 持有人，收入按协议收入口径 |
| 链上 gas 手续费 | 交易费口径已含 buyback 路由部分，避免重复计算 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| CAKE 回购销毁（Tokenomics 3.0） | `destroy`（回购/销毁） | 12.93% |

## 四、关键计算逻辑（adapter.py）

`data/protocols/pancakeswap/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `burn-history.json` 的 `net_burns.365.burn_usd`（= DefiLlama dailyHoldersRevenue 365d，CAKE buyback&burn 的 USD 金额，gross 口径 ≈ $58.67M）
2. 读 `daily/<id>/latest.json` 的 `total1y_fees_usd`（总费用 365d ≈ $270.5M）
3. 用 config `revenue_recognition.calculation.payout_ratio`（0.625，判定书 60-65%）反推协议收入：`protocol_revenue = buyback_burn / 0.625 ≈ $93.87M`
4. `lp_share = total_fees − protocol_revenue ≈ $176.7M`（详情页展示「收入 − LP」）
5. 毛利 = 协议收入；增发成本 = config `token_emission_cost.usd_365d`（$11.7M，treatment=cost，日增发 2.25 万 CAKE farm 激励，美股 SBC 类比）；净利 = 毛利 − 增发成本 = $82.17M
6. 股东回报 = 回购销毁 365d；`yield = buyback_burn / mcap ≈ 12.93%`；销毁型 🟢，CAKE → 0x000...dEaD 链上可验证

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 官方 Tokenomics 文档 + Burn Dashboard | 周频 | ai-watch-official.py |
| dailyRevenue 日频 | 日频 | fetch-defillama.js |
| 日增发 2.25 万 CAKE + 回购销毁链上 | 日频 | update-pancake-tev.py |

## 六、历史验证与注意点

- **⚠️ 口径回退（2026-06-14）**：2026 上半年公共 BSC RPC 全行业取消 archive 节点支持（1rpc/Ankr/publicnode/bscrpc 全部拒绝历史 state），Etherscan V2 免费 key 不覆盖 BSC——原链上 net-deflation 口径无法运行（burn-history 的 net_burns 退化为空，前端 yield 曾失真为 0 约 47 天），故回退 DefiLlama dailyHoldersRevenue（gross）口径
- **gross vs net 口径差异**：DefiLlama gross 口径不扣 LP 增发对冲，较原链上净通缩定义略高，但 365d 量级一致（~$65M）；短周期年化偏低（7d ~4.6%）是近月 buyback 放缓的真实反映
- **Burn 完全链上可验证**：CAKE → 0x000...dEaD，资金来自真实 trading fee，无 pocket-to-pocket 风险
- **veCAKE 已 sunset（2025-04-23）**：旧 5% revenue share 于 2025-05-07 结束，Tokenomics 3.0 后 100% 回购直接 burn 到 0xdead
- **payout_ratio 已更新**：0.15（旧低估）→ 0.625（判定书 60-65% 计入）；已累计销毁 4.04 亿 CAKE（初始供应 7.5 亿目标）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §14
- 配置文件：`data/protocols/pancakeswap/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/pancakeswap/README.md`（如有）
