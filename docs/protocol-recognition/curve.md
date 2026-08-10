# Curve — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Curve 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Curve / CRV |
| 实体类型 | `application`（dex，稳定币 DEX） |
| 市值（as_of 2026-08-04） | ~$0.32B |
| 股东回报率 | ~4.84%（股息 4.84% + 回购 0%） |
| 置信度 | high |
| 数据源优先级 | 链上（Community Fund Treasury × 9 反推）> 官方周报 > DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：增发按成本计算（美股 SBC 类比）——收入 − LP 分润 = 毛利；毛利 − 增发成本 = 净利为负（净稀释）**

```
收入 = admin fee 口径（dailyRevenue 365d）= $15,335,813（FeeAllocator 90% → veCRV）
增发成本 = CRV 年增发 ~1.155 亿（约 $26M/年，通胀 4.8%）treatment=cost
净利 = 毛利 − 增发成本 = $15.34M − $26M = -$10.66M（净利为负）
股东回报 = veCRV 分红 $15,335,813 → 回报率 = $15.34M ÷ $0.32B = 4.84%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| admin fee → veCRV 分红 | 交易费 50% LP / 50% admin fee → veCRV；crvUSD 利息 FeeSplitter 动态 50/50（scrvUSD/veCRV）；FeeAllocator 90% → veCRV（10% → Community Fund） | 链上 Treasury × 9 反推 + DefiLlama |

| 不计入 | 原因 |
|---|---|
| 交易费 50% LP 分润 | 收入按 admin fee 口径，LP 分润在收入确认时排除 |
| FeeAllocator 10% Community Fund | ~$1.70M/365d 进社区基金国库，不计入 DefiLlama dailyRevenue 口径 |
| Bribes（Convex / Stake DAO 投票贿选） | 来自外部协议买票，非 Curve 自身分润 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| veCRV 分红（FeeAllocator 90% admin fee） | `yield`（股息，🟡 收益型） | 4.84% |

> 裸 CRV 持有人不参与分红（必须 lock 换 veCRV）；名义 yield = 股东回报 / CRV 全市值，实际锁仓持有人接近 veCRV-only 口径（4.25%）。

## 四、关键计算逻辑（adapter.py）

`data/protocols/curve/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 fee-history.json → `summary.365d.vecrv_tev_usd`（$15.34M，90% admin fee → veCRV）+ `treasury_crvusd`（$1.70M，10% Community Fund，不计收入）
2. `revenue = vecrv_tev`（admin fee 口径，LP 分润已排除）→ 毛利 = 收入
3. 增发成本：config.token_emission_cost（usd_365d = $26M，treatment = cost，通胀 4.8%）
4. `net = revenue − emission_cost = $15,335,813 − $26,000,000 = -$10,664,187`（净利为负）
5. 股东回报 by_mechanism = [{mechanism: "veCRV 分红（FeeAllocator 90% admin fee）", type: "yield", usd: $15,335,813, yield: 4.84%}]；无销毁（burns=NONE）
6. 派生估值：pe = ps = mcap/returns = 20.66；payout_ratio = null（净利为负）
7. 净利率 = net/revenue = -69.54%（净稀释）

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 官方：官方周报 news.curve.finance / docs / gov.curve.fi 提案 + crvhub | 周频 | ai-watch-official.py |
| DefiLlama dailyRevenue | 日频 | fetch-defillama.js |
| 链上：增发量验证 | 日频 | update-curve-tev.py |

## 六、历史验证与注意点

- **⚠️ FeeAllocator × 9 反推**：老 3CRV FeeDistributor 0xA464...8922Dc 已停转（inflow ≈ 0），新 90% veCRV 流向未在单一合约识别 → 观察 10% Community Fund Treasury（0x6508...）crvUSD 入金 × 9 反推 90% veCRV 部分
- **⚠️ 假设 90/10 比例不变**：FeeAllocator 2025-06-27 上线，治理可改比例，变化会影响推算精度
- **双口径 yield**：nominal（全市值分母，主表显示 4.84%）+ veCRV-only（锁仓 TVL 分母 4.25%，详情页另展示）；实际锁仓持有人更接近 veCRV-only
- **净利为负是口径结果**：增发 $26M/年 > admin fee 收入 $15.34M → 净稀释；详情页需展示完整计算过程（admin fee $X − 增发 $26M = 净利为负）
- **CRV 锁仓**：链上 855M CRV（56.8% 流通）锁仓，veCRV TVL ~$193.8M
- **增发全流 LP 挖矿**：CRV 年增发 ~1.155 亿全流给 LP 挖矿（有对价换收入 → 作为成本扣除）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §11（Boss 2026-08-02 定稿）
- 配置文件：`data/protocols/curve/config.json`（revenue_recognition + token_emission_cost 字段）
- 数据维护说明：`data/protocols/curve/README.md`（如有）
