# Ethena — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Ethena 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Ethena / ENA |
| 实体类型 | `application`（basis_trading） |
| 市值（as_of 2026-08-04） | ~$848.6M |
| 股东回报率 | ~0%（股息 0% + 回购 0%） |
| 置信度 | low |
| 数据源优先级 | 官方治理/dashboard > 链上 > DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：费用开关生效前 ENA 股东回报 = 0 —— sUSDe 收益归 sUSDe 持有人，DAT 回购是资本运作，非经营利润分配**

```
收入（近 12 月总费用）≈ $338.3M
毛利（协议留存）= 总费用 − sUSDe 分配 $329.3M = $9.0M
净利 ≈ $0.6M（绝大部分费用分配给 sUSDe + 储备/运营成本）
股东回报 = 0（费用开关 2026Q3 激活前；激活后 sENA 预期 >5%，届时更新）
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议收入（近 12 月总费用） | DefiLlama dailyFees 365d ≈ $338.3M（判定书口径 ~$310M）；其中 sUSDe yield 全归 sUSDe 持有人，不计入 ENA 股东回报 | DefiLlama + Ethena 官方治理/dashboard |

| 不计入 | 原因 |
|---|---|
| sUSDe yield（~$329.3M/365d） | sUSDe yield ~3.5-4% APY 全归 sUSDe 持有人，是流向持有人的收益，非 ENA 股东回报 |
| DAT 回购（~$890M 分批） | 确认为金库/储备出资的资本运作（StablecoinX PIPE 融资），非经营利润分配，不计入持续股东回报 |
| 费用开关（Fee Switch） | 2026Q3 待激活；激活后 sENA 预期 >5%（届时更新）——AI 哨兵观察点 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 费用开关（Fee Switch）sENA 分润 | `yield`（股息） | 0%（2026Q3 待激活，确凿为 0 非数据缺失） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/ethena/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `daily/<id>/latest.json` 的 `total1y_fees_usd`（近 12 月总费用 ≈ $338.3M）
2. 读 `all-protocols.json` 的 `metrics.trailing_365d_revenue_usd`（DefiLlama dailyRevenue 365d = 协议实际留存 ≈ $9.0M）
3. `susde_cost = gross_fees − protocol_rev ≈ $329.3M`（sUSDe yield 分配，视为流向持有人成本，不计入 ENA 股东回报）
4. 毛利 = 协议留存 $9.0M；净利 = $600k（判定书，绝大部分费用分配给 sUSDe + 储备/运营成本）
5. 股东回报确凿为 0（非 null）：by_mechanism `usd_365d=0`、`shareholder_yield_percent=0`——费用开关激活前 ENA 不分润
6. 派生：毛利率 ~2.7%、净利率 ~0.2%；股东回报 0 → P/E、派息率 = null；P/S = mcap / gross_fees ≈ 2.51

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| Ethena 官方治理/dashboard（费用开关激活状态监控） | 事件驱动 | ai-watch-governance.py |
| dailyRevenue 日频 | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **🔍 AI 哨兵观察点（2026Q3）**：**费用开关激活状态**——激活后协议总费用 10-20% 将转向 sENA 质押者（回购+收益分发），sENA 预期 >5%，届时更新判定
- **⚠️ 易混淆**：sUSDe 收益（~7.83% APY）是给 sUSDe 持有人的，**不是**给 ENA 持有人；ENA 当前仅治理代币
- **⚠️ DAT/ENA 回购是资本运作**：2025 年 $570M+ 回购（$260M + $310M，部分用于 StablecoinX）资金来自 StablecoinX PIPE 融资，非协议持续利润分红，不算 TEV
- **sENA 分配比例长期为 "discretional"**：截至 2025-09 无持续协议级分润
- **收入大但净利极小**：近 12 月收入 $338M，净利仅 $0.6M（净利率 ~0.2%）——绝大多数费用流向 sUSDe 持有人与储备/运营
- ENA 增发未列为成本（无对价解锁作稀释注记，费用开关激活后重评估）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §17
- 配置文件：`data/protocols/ethena/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/ethena/README.md`（如有）
