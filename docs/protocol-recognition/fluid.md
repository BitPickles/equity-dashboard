# Fluid — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解该协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Fluid / FLUID |
| 实体类型 | `app`（lending + DEX，统一 Liquidity Layer） |
| 市值（as_of 2026-08-04） | ~$92.2M |
| 股东回报率 | ~5.15%（股息 0% + 回购 5.15%） |
| 置信度 | medium |
| 数据源优先级 | 链上（reserve 钱包）> 官方公告（Instadapp Blog）> DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：35% 收入 → Treasury 回购 FLUID（reserve 钱包链上可追踪）；回购后终极用途未公开；35% 比例无链上治理投票**（fluid 无专门条目，按应用型处理）

```
股东回报 = 收入 × 35% = DefiLlama dailyHoldersRevenue 365d（$4,745,308，≈ 收入 $12.85M × 35%）
回报率   = $4.75M ÷ 市值 ≈ 5.15%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 协议收入（DefiLlama dailyRevenue） | Lending + Vault + DEX 业务产生的协议净收入，LP 分润已扣 | DefiLlama dailyHoldersRevenue |

| 不计入 | 原因 |
|---|---|
| 借贷/DEX 费用给 LP 部分 | 已在 dailyHoldersRevenue 口径内扣减；回购额 ≈ 收入 × 35% |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| Fluid Reserve Buyback（35% 收入回购） | `buyback`（回购） | 5.15%（verified: partial） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/fluid/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `all-protocols.json` → `metrics.trailing_365d_revenue_usd` = $4,745,308（即 35% 收入回购额，DailyHoldersRevenue 口径）
2. `buyback_usd = revenue`；`yield = buyback_usd ÷ mcap = 5.1467%`
3. 毛利 = 净利 = revenue（dailyHoldersRevenue 为协议净收入口径，LP 分润已扣）
4. `summary.destroy_usd_365d = buyback_usd`（⚠️ validate 重算把 buyback 计入 destroy 桶，summary 必须同步，避免「文件=None 重算=有值」冲突）
5. 派生估值：`PE = PS = mcap ÷ revenue ≈ 19.43`；`payout_ratio = 1.0`
6. 交叉核对：`tev-records.json` 链上实测 1.25M FLUID 流入 reserve 钱包 ≈ $4.61M（与 DefiLlama 差 <0.5%）

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 2 个 reserve 钱包链上追踪（0x3e6F.../0x9Afb...） | 日频 | track-fluid-buybacks-v3.py |
| DefiLlama dailyRevenue | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ 回购后 FLUID 终极用途未公开**：官方 blog 仅说"建立链上储备"，未明确 burn / 流动性 / 分配 —— 若未来转作流动性或再分配，TEV 会缩水
- **35% 比例无链上治理投票**：来自官方 2025-10 博文《FLUID Reserve: Buybacks & Growth Strategy》，未见 Snapshot 投票记录，未来可能改变
- **Reserve 钱包可被治理动用**：当前持仓占 0.11% supply，风险低，但若未来转作 inflation 分配将抵消 TEV
- **数据可靠性**：Etherscan + DefiLlama 双源校验差 <0.5%，链上可完整追踪

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md`（fluid 无专门条目，按第 3/4 批应用型通用口径处理）
- 配置文件：`data/protocols/fluid/config.json`（revenue_recognition 字段 + analyst_notes 链上调研）
