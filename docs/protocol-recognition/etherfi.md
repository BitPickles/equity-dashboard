# ether.fi — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解该协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | ether.fi / ETHFI |
| 实体类型 | `app`（liquid_staking 流动性质押） |
| 市值（as_of 2026-08-04） | ~$389.9M |
| 股东回报率 | ~4.29%（股息 4.29% + 回购 0%） |
| 置信度 | low |
| 数据源优先级 | 链上 > 官方治理（Token Terminal / Dune）> DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：双回购引擎 —— 提现费 100% 周度回购 + 协议收入 25% 月度回购，均回购 ETHFI 分给 sETHFI 质押者（本质"质押者股息"）**（2026-08-02 定稿 / 2026-08-04 修正类型）

```
股东回报 = DefiLlama dailyHoldersRevenue 365d（≈ $16.71M，含双引擎合计）
回报率   = 回报 ÷ 市值 ≈ 4.29%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 提现费 100% 周度回购 | 用户 eETH 提现费 → 回购 ETHFI → 分给 sETHFI 质押者 | DefiLlama dailyHoldersRevenue / tev-records |
| 协议收入 25% 月度回购 | 协议收入（Stake/Liquid/Cash，Cash 占 ~55%）的 25% 回购分发 | 同上（无单引擎拆分，含于合计口径） |

| 不计入 | 原因 |
|---|---|
| DAO $50M 公开市场回购 | 执行进度透明度一般，标 unverified，不计入股东回报 |
| dailyFees 365d（≈ $225M） | 含 staking 收益（多数归 eETH 用户），非协议收入，不作收入科目 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 提现费 100% 周度回购 → sETHFI 质押者 | `yield`（股息） | 4.29%（合计口径） |
| 协议收入 25% 月度回购 → sETHFI 质押者 | `yield`（股息） | 已含于上一条 |
| DAO $50M 公开市场回购 | `buyback`（回购） | 0%（unverified 不计入） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/etherfi/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `tev-records.json` → `summary.total_tev_usd`（DefiLlama dailyHoldersRevenue 365d ≈ $16.7M，落在判定书 $16-24M 区间下沿）
2. 读 `all-protocols.json` → `market_cap_usd`（$389.86M）、`validation.sethfi_inflow_*`（监控用）
3. 收入：`daily/latest.json` 的 dailyFees 365d ≈ $225M 含 staking 收益（多数归 eETH 用户）→ 非协议收入，`revenue = None`
4. 毛利 / 净利：协议收入（Token Terminal/Dune 口径）未缓存 → `null`（禁止编造）
5. 股东回报 = `returns`（$16.71M）；`yield = returns ÷ mcap = 4.286%`
6. **口径修正（Boss 2026-08-04）**：双引擎回购后分发 = 股息（真金白银进持币人口袋）→ `type=yield`，DAO $50M 保留 `type=buyback` 但 `usd=None` 不计入
7. 派生估值：`PE = mcap ÷ returns ≈ 23.33`；`PS = null`（收入不可得）

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 协议收入/回购（Token Terminal / Dune + 官方公告） | 周频 | ai-watch-official.py |
| 周度提现费回购 + 月度收入回购链上 | 周频 | update-etherfi-buybacks.py |

## 六、历史验证与注意点

- **⚠️ 2026-08-04 Boss 修正**：回购后分发 = 股息，`type=yield`（此前口径在 buyback/股息间反复，以此版为准）
- **eETH 收益 ≠ ETHFI TEV**：eETH 持有人拿 ~3.2% ETH 原生收益，ETHFI TEV 是 sETHFI 质押者拿到的回购分配，两者易混淆
- **裸 ETHFI 不参与**：必须 stake → sETHFI 才能接收回购分配
- **历史 TEV 曾归零（2026-04-26）**：链上 Foundation Multisig 365d 入金 = 0、sETHFI 入金混入用户 stake、Uni V3 主池无大单 buyback → 曾类比 JustLend 归零；现按判定书官方口径恢复（DefiLlama holdersRevenue），`sETHFI 上界 $47.4M 仅作监控不作主数字`
- **收入/净利为 null**：协议收入本地未缓存，禁止编造数字

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §16
- 配置文件：`data/protocols/etherfi/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/etherfi/README.md`（TEV 公式与链上验证方法）
