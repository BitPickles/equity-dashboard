# Hyperliquid — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解该协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Hyperliquid / HYPE |
| 实体类型 | `app`（perpetuals / Perp DEX） |
| 市值（as_of 2026-08-04） | ~$7.37B |
| 股东回报率 | ~10.39%（股息 0% + 回购 10.39%，销毁型 🟢） |
| 置信度 | high |
| 数据源优先级 | 链上（AF 地址 0xfefe... + spot 销毁地址）> DefiLlama（交叉验证） |

> ⚠️ 数据仓库 key：本项目正式 id 为 `hype`（`data/protocols/hype/` + `data/snapshots/hype.json`）；`data/protocols/hyperliquid/` 是旧别名镜像目录，adapter 正式消费路径在 hype。

## 二、收入判定（核心）

**Boss 定稿口径：手续费直接销毁 ≈ 回购，基本 99% —— 销毁流通币 = 流向所有持币人，计入股东回报 🟢**（§9，2026-08-02 定稿）

```
股东回报 = DefiLlama dailyRevenue 365d × 0.99
         = $772,987,701 × 0.99 ≈ $765,257,824
回报率   = $765.3M ÷ 市值 ≈ 10.39%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 交易手续费（spot 真销毁部分） | DefiLlama dailyRevenue（= dailyHoldersRevenue，已剥离 HLP/builder/referral/deployer），与链上 AF `entryNtl` 交叉验证差 <5% | DefiLlama + Hyperliquid API |

| 不计入 | 原因 |
|---|---|
| AF 余额（~1%） | AF 用交易费回购 HYPE 留在 AF 地址（可被 validator consensus 动用），按「只计流向流通持币人的价值流」铁律仅作注记 |
| Funding | 多空点对点支付，平台不收取 |
| 清算 | 无清算手续费；backstop 清算收益沉淀在 HLP PnL |
| HyperEVM gas | base fee + priority fee 全部 burned，属供给收缩，非利润分配 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| Assistance Fund 手续费销毁（spot 真销毁） | `destroy`（回购/销毁） | 10.39%（verified） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/hype/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `config.json` 取 `payout_ratio`；若遗留值 ≥1（如 1.0/100%）则强制按判定书修正为 `0.99`
2. 读 `all-protocols.json` → protocols 的 `hype` key → `metrics.trailing_365d_revenue_usd` ≈ $773.0M
3. `returns_usd = revenue × 0.99 = $765,257,824`；`yield_pct = returns_usd ÷ mcap = 10.3861%`
4. 毛利 = 净利 = 收入（Perp DEX 手续费直接销毁，无 LP 分润 / 无增发成本，HYPE 总供应 10 亿固定）
5. 交叉核对：`af-history.json` 旧缓存 365d（截至 2026-04-17 陈旧，窗口不重叠，仅注记）
6. 派生估值：`PE ≈ 9.63`、`PS ≈ 9.53`、`payout_ratio = 0.99`

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| spot 销毁地址 + AF 地址（链上） | 日频 | update-hype.py |
| AF 链上校验（entryNtl delta 对比 DefiLlama，偏差 >15% 告警） | 日频 | update-hype-tev.py |
| HYPE spot burn（真实永久销毁） | 日频 | fetch-hype-burns.py |
| DefiLlama dailyRevenue → yield 聚合 | 日频 | sync-tev-data.js（hype 走 SKIP_PROTOCOLS 分支） |

## 六、历史验证与注意点

- **⚠️ AF 可被动用风险**：AF 买入的 HYPE 留在 AF 地址（0xfefe...，累计 ~43.4M HYPE / entryNtl ~$1.07B），理论上可被 validator consensus 动用于救灾/补偿 —— 一旦动用，对应 TEV 部分瞬间归零
- **AF ≠ 真 burn**：真实永久销毁只有 spot 手续费销毁（~745k HYPE，约占供应 0.075%）；AF 是 treasury buyback（等效销毁口径，2026-04-19 修正"AF 买入即销毁"的错误描述）
- **DefiLlama 口径**：`dailyRevenue` = `dailyHoldersRevenue`（已验证），差值即 HLP 分成部分
- **funding / 清算 / HyperEVM gas 均不计入**，已在判定书中明确排除
- **无持续增发**：总供应 10 亿固定，回购销毁使供给收缩（负稀释）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §9
- 配置文件：`data/protocols/hype/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/hype/README.md`（TEV 公式、链上校验与手动介入触发条件）
