# Aave (AAVE) 数据维护说明

本文档说明 Aave（AAVE）协议的**收入 / 净利 / 股东回报**数据如何计算、数据源、自动更新。

> ⚠️ **2026-10-08 重大修订**：本文件旧版本（"TEV = 固定 Buyback $30M + 动态 Safety Module holders revenue"）**已作废**。经 DefiLlama adapter 源码 + 实时序列核实，旧口径存在两处事实错误，且回购实际已暂停。本次全部更正。详见 §六。

---

## 一、机制现状（2026-10-08 核实版）

### 1. AAVE 回购计划 —— **已暂停（2026-04-19 起）**

- **起源**：AIP-73 "Aavenomics Update Part 1"（2024-07 设立，2025-04-09 起实际执行）
- **预算**：2026-03 治理由 $50M/年 下调至 **$30M/年**（99.37% 通过）
- **执行**：TokenLogic / Aave Finance Committee 用 DAO 财库 USDC/GHO 市场买入 AAVE
- **⚠️ 关键**：
  - 买来的 AAVE 存入 **Ecosystem Reserve**（`0x22740deBa78d5a0c24C58C740e3715ec29de1bFa`）+ AFC multisig
  - **不是真 burn**，是 **treasury-accumulated**，治理可 redistribute
  - **回购页面自 2026-04-19 起 Paused** → **已实现股东回报 = 0**

### 2. 为什么计入 0（Boss 2026-10-08 决策 D1）

Boss 决策：**计 0 + 标已暂停**。
- **预算 ≠ 执行**：$30M/年 是授权额度，不是实际买币额。回购暂停期间实际发生额 = 0，故股东回报计 **0**。
- 详情页显著标注 **"已暂停（Paused since 2026-04-19）"**。
- DefiLlama 历史序列（365d ≈ $18.87M）仅作**历史参考**单列，不计入当前收益率。

### 3. 质押奖励（Umbrella）—— **不计入股东回报**

- 旧 `stkAAVE`（`0x4da2...70f5`）已被 **Umbrella** 新合约替代
- 质押奖励属**激励性支出**，不构成可持续的股东价值流，按铁律不计入股东回报

---

## 二、关键更正（旧版错误）

| 旧版说法 | 事实（2026-10-08 核实） |
|---|---|
| "TEV = 固定 Buyback $30M + Safety Module holders revenue" | $30M 预算**未在执行**（2026-04-19 起暂停）→ 不应折算为收益率；已实现股东回报 = 0 |
| "DefiLlama `dailyHoldersRevenue` = Safety Module 奖励" | **错**。DefiLlama adapter 源码 `fees/aave-v3.ts` / 文档明确：`HoldersRevenue` = **"buy back AAVE tokens using Aave Treasury after 9 April 2025"**，即**回购收币代理**，与 Safety Module 无关。 |
| "Aave 完全不 burn 到 0xdead → A 口径不适用" | 此结论仍成立（回购是 treasury 累积，非 burn），但需补：holdersRevenue 反映的是回购收币，不是 SM 分发。 |

**依据**：DefiLlama dimension-adapters `fees/aave-v3.ts`——
```
HoldersRevenue = AAVE buybacks using Aave Treasury (after 9 April 2025)
收币地址 0x22740deBa78d5a0c24C58C740e3715ec29de1bFa
```

---

## 三、当前数字（2026-10-08 快照）

| 项目 | 数值 | 说明 |
|---|---|---|
| 协议收入 365d | **$92,387,330** | DefiLlama `dailyRevenue`（已扣 LP 利息） |
| 净利润 365d | **$92,387,330** | = 协议净收入 |
| **股东回报 365d** | **0** | 回购暂停 → 已实现 = 0 |
| **股东回报率** | **0%** | — |
| 状态 | **paused（已暂停）** | 自 2026-04-19 |
| payout_ratio | 0 | — |
| P/S | 29.9648 | 市值 / 收入 |
| P/E | — | 净利口径下不适用（按暂停处理） |
| 历史参考 | holdersRevenue 365d ≈ $18,869,659；最后非零日 2026-06-24 | 仅历史，不计入当前 |

---

## 四、数据源

| 数据 | 来源 | 维护 |
|---|---|---|
| 协议收入 (dailyRevenue) | DefiLlama `summary/fees/aave?dataType=dailyRevenue` | 每日 sync 自动拉 |
| 回购收币代理 (holdersRevenue) | DefiLlama `summary/fees/aave?dataType=dailyHoldersRevenue` | 每日拉，仅作历史参考 |
| 回购暂停状态 | 回购页面（自 2026-04-19 Paused） | 手动核对 |
| 市值 | CoinGecko / CMC | 主流程 |
| 链上 Buyback 校验 | **未实现**（收币地址 `0x22740deB…1bFa` 已知） | 未来扩展 |

---

## 五、链上验证（2026-04-22 核实）

```
AAVE @ 0xdead 当前: 0.2750 AAVE
AAVE → 0xdead 365d: 0.0001 AAVE（3 个 events，微不足道）
AAVE → Safety Module 365d: 315,737 AAVE（含用户质押，非纯协议分发）
```

结论：不 burn 到 0xdead → A 口径不适用；回购为 treasury 累积。

---

## 六、历史口径变更

- **2026-10-08**：更正两处事实错误（holdersRevenue 是回购收币非 SM 奖励；预算未执行）；股东回报改计 **0 + 标已暂停**
- 2026-04-19：回购页面暂停
- 2026-03：治理 Buyback 从 $50M → $30M
- 2025-04-09：回购开始实际执行（DefiLlama 以该日划分）
- 2024-07-25：AIP-73 启动 Aavenomics buyback

---

## 七、手动介入触发条件

### 1. 回购恢复执行
**症状**：回购页面取消 Paused / 出现新买入交易
**处理**：把股东回报从 0 恢复为 DefiLlama `dailyHoldersRevenue` 实际值，状态改回 active。

### 2. 治理再次调整回购预算
**处理**：查 governance.aave.com 最新 AIP，更新 config.json 的 analyst_notes。

### 3. 链上收币地址变更
**处理**：核实新地址，更新 README / adapter 注记。

---

## 八、调试

```bash
# 查 DefiLlama 三口径
for dt in dailyFees dailyRevenue dailyHoldersRevenue; do
  curl -s "https://api.llama.fi/summary/fees/aave?dataType=$dt" \
    | python3 -c "
import json,sys
c=json.load(sys.stdin)['totalDataChart']
for N in [7,30,90,365]:
  s=sum(v for _,v in c[-N:] if v); print(f'  $dt {N}d: \${s/1e6:.2f}M')
"
done

# 查当前 snapshot
python3 -c "
import json
d=json.load(open('data/snapshots/aave.json'))
print('股东回报:', d['holder_returns']['summary']['shareholder_returns_usd_365d'])
print('状态:', d['holder_returns']['summary']['status'])
print('历史参考:', d['holder_returns']['summary'].get('historical_reference'))
"
```
