# Maple — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Maple 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Maple Finance / SYRUP |
| 实体类型 | `application`（lending） |
| 市值（as_of 2026-08-04） | ~$182.5M |
| 股东回报率 | ~0.85%（股息 0% + 回购 0.85%） |
| 置信度 | medium |
| 数据源优先级 | 官方仪表盘（maple.finance/transparency）> 治理提案（MIP）> DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：MIP-021 阶梯回购（2026-07-17 通过 99.97%）：月收入 <$1.5M → 10%；$1.5-2M → 20%；>$2M → 30%**

```
收入（年化）= 月收入 $1.29M × 12 = $15.48M
毛利 = 收入（机构借贷利差，无 LP 分润）
净利 = 收入 − 增发成本 0 = $15.48M
股东回报 = 净利 × 10%（当前档，MIP-021）= $1.55M → 留存 90%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议费（贷款利差 interest spread） | 机构借贷利差收入；当前月收入 ~$1.29M → 落在 10% 档 | maple.finance/transparency 官方仪表盘 |

| 不计入 | 原因 |
|---|---|
| 回购金额中留作国库储备/流动性的部分 | SSF 回购中 burn vs reserve 比例未披露（partial），留作国库储备的部分非直接股东回报 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| MIP-021 阶梯回购（SSF） | `buyback`（回购） | 0.85%（10% 档） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/maple/adapter.py` → `build_snapshot(proto_dir)`：

1. 月收入 = $1,290,000（判定书/maple.finance/transparency 官方仪表盘，2026-07）；`revenue = 月收入 × 12 = $15,480,000`
2. `_mip021_ratio(monthly_revenue)` 阶梯判断：$1.29M < $1.5M → 返回 0.10（10% 档）
3. 毛利 = 收入（机构借贷利差，无 LP 分润成本）；增发 = none（SYRUP 总供应固定 ~12.16B，2024 年由 MPL 迁移）
4. 净利 = 收入 → 回购 `$15.48M × 10% = $1.548M` → 留存 `$15.48M × 90% = $13.93M`
5. 股东回报 = 回购 $1,548,000；`yield = 回购 / 市值 ≈ 0.85%`；SSF 国库地址未公开、burn vs reserve 比例未披露 → verified: partial

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| maple.finance/transparency 官方仪表盘 + MIP 提案（月度收入、回购档位复核） | 月频 | ai-watch-governance.py |

## 六、历史验证与注意点

- **⚠️ MIP-021 切换（2026-07-17）**：回购规则化（通过率 99.97%），首次执行 2026-08；**MIP-019/020 固定 25% SSF 回购已于 2026-Q2 结束**，不能再按 25% 口径
- **⚠️ 当前档位**：月收入 ~$1.29M → 10% 档（2026 年回购放缓，仅 $375K，资金转向增长与储备）；月收入上行至 $1.5-2M / >$2M 时档位自动切换 20% / 30%
- **SSF 国库地址未公开**：Maple 团队未发布回购执行钱包，无法链上逐笔验证 burn vs reserve 比例（类 ether.fi 地址不公开问题）；若大部分留作国库储备而非销毁，实际供应收缩 < 10%，名义 yield 虚高
- **历史数据时间跨度不足**：DefiLlama dailyHoldersRevenue 从 2025-11 才开始记录，原 365d 数字有外推高估风险——现已改用官方仪表盘月收入 × 12 口径
- SSF 国库持仓可被治理动用（类 Hyperliquid AF 风险），不等同永久销毁
- payout_ratio 已从 0.25 改为动态阶梯（当前档 0.1）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §15
- 配置文件：`data/protocols/maple/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/maple/README.md`（如有）
