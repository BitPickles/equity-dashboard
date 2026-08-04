# Aave — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Aave 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Aave / AAVE |
| 实体类型 | `app`（应用型，lending 借贷） |
| 市值（as_of 2026-08-04） | ~$1.80B |
| 股东回报率 | ~1.67%（股息 0% + 回购 1.67%） |
| 置信度 | high |
| 数据源优先级 | 官方治理（回购金额） > DefiLlama（dailyRevenue / dailyHoldersRevenue） > 链上 |

## 二、收入判定（核心）

**Boss 定稿口径：收入 ≠ 所有协议费——扣除给 LP（存钱的人）的部分，算协议净利润**（框架铁律：所有计算用净利润，见 PRD 3.3）

```
收入 = DefiLlama dailyRevenue 365d（协议归属/净，已扣给 LP 的部分，非 dailyFees）
净利 = 收入（dailyRevenue 即协议净额，回购由 DAO 财库支出不影响损益）
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议费（protocol fees） | DefiLlama dailyRevenue（协议归属/净，reserve factor + 清算费等） | DefiLlama `dailyRevenue` |

| 不计入 | 原因 |
|---|---|
| 给 LP（存款人）的利息 | 占协议费大头，已由 dailyRevenue 数据源扣减，避免重复计算 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| AAVE 年度回购（$30M/年，2026-03 治理） | `buyback`（回购） | 1.67% |
| Safety Module (Umbrella) 质押奖励 | `yield`（股息） | 待定（暂不计入主数字） |

- 股东回报合计 $30M/年 ÷ 市值 ≈ **1.67%**（snapshot `shareholder_returns_usd_365d = $30,000,000`，`shareholder_yield_percent = 1.6675`）
- Safety Module 365d DefiLlama dailyHoldersRevenue ≈ $27.44M，归属**待定保留**（usd=null 不计入）

## 四、关键计算逻辑（adapter.py）

`data/protocols/aave/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `config.json`（口径声明）+ `tev-records.json`（回购 + SM 月度分发历史）+ `data/all-protocols.json`（市值 / validation / metrics）
2. `revenue = metrics.trailing_365d_revenue_usd`（≈ $115.46M，DefiLlama dailyRevenue 365d）
3. `buyback = validation.fixed_buyback_usd_annual`（$30M/年，2026-03 治理定稿）
4. `sm_365d = validation.sm_365d_usd`（≈ $27.44M/365d）→ 归属待定，by_mechanism 保留机制行但 `usd_365d = null`
5. tev-records 交叉核对：365d 窗口合计 ≈ $27.72M（与 DefiLlama SM 数据互验）
6. `destroy_usd = buyback`；`total_returns = buyback`（yield 侧 SM 未计入 → 0 不显示，避免编造）
7. 派生估值：`pe = mcap / total_returns`（59.97）、`ps = mcap / revenue`（15.58）、`payout = total_returns / revenue`（0.26）；毛利率/净利率 = 100%（净额口径）

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 治理提案/月报（回购金额变化） | 事件驱动 | ai-watch-governance.py |
| DefiLlama dailyRevenue（协议收入） | 日频 | fetch-defillama.js |
| DefiLlama dailyHoldersRevenue（SM 分发） | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ 回购是 treasury-accumulated，不是真 burn**：DAO 财库市场买入 AAVE → Ecosystem Reserve（`0x25F2...6491`）+ AFC multisig，治理可 redistribute；链上 365d AAVE → 0xdead ≈ 0.0001 AAVE（确认不销毁）。因买走的币不在流通中，仍算 TEV，但前端须显著标注「treasury-accumulated, governance-reversible」
- **⚠️ Safety Module 脉冲式分发**：每 1-2 周一次大包（$200k~$6M），其余天为 0；最近 50+ 天 SM = $0，可能是 Umbrella 新合约（2025 年中迁移，替代旧 stkAAVE）DefiLlama 追踪滞后，或真暂停分发
- **2026-03 治理**：年度回购预算从 $50M 下调至 $30M（99.37% 通过），早期文档 $50M 已过时，以最新官方披露为准
- 短周期（7d/30d）碰巧抓不到 SM 大包 → 回报率显示 1.67%，反映的是「SM 分发周期」而非价值下降；365d 稳定态分配率 ~57%

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §6（Aave）
- 配置文件：`data/protocols/aave/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/aave/README.md`（TEV 双源公式 + 手动介入触发条件）
