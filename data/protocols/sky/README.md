# Sky (MakerDAO) 数据维护说明

本文档说明 Sky（原 MakerDAO）协议的**收入 / 净利 / 股东回报**数据如何计算、数据源、自动更新。

> **品牌变化**：Maker 于 2024-08 重品牌为 Sky，MKR → SKY（1:24000 转换）。本 dashboard 已按 Sky 时代口径维护（Splitter / SBE / SKY stakers）。

> ⚠️ **2026-10-08 重大修订**：本文件旧版本（"SBE 把 LP token burn 到 0xdead = TEV"、"Farm 部分不算 TEV"）**已作废**。经 DefiLlama adapter 源码 + 实时序列核实，旧口径存在两处事实错误，本次全部更正。详见 §六。

---

## 一、价值分配机制（2026-10-08 核实版）

Sky 协议盈余（Stability Fee 等，已扣 DSR/SSR 用户存款利息）→ **Surplus Buffer** → **Splitter** 分流：

```
协议盈余 (DefiLlama dailyRevenue)
  = $201,440,351 (365d)
        │
        ├── Surplus Buffer 留存 ──────────────► 国库留存（70.2%，$141,389,931）
        │                                         不计入股东回报
        │
        └── SBE (Smart Burn Engine) 回购支出 ──► 买入 SKY 交国库（29.8%，$60,050,420）
                                                   计入股东回报（混合代理，见 §二）
        └── SKY staking farm 部分 ─────────────► 付给 SKY stakers 的 USDS 奖励
                                                   （已含在 DefiLlama holdersRevenue 内）
```

### 🔑 关键更正（旧版错误）

| 旧版说法 | 事实（2026-10-08 核实） |
|---|---|
| "SBE 市场买 MKR + LP → LP token burn（真销毁）" | **2024-09 起 SBE 是「买 SKY 交国库」**，库存受治理支配、**可再分配**，≠ 销毁。真正的 burn 事件只有 2025-06-30 一次 426,292,860.23 SKY 的**供应校正**（supply correction），不是经营性回购销毁。 |
| "Farm 部分（付给 stakers）不算 TEV" | **错**。付给 SKY stakers 的 USDS 奖励**就是流向流通持币人的价值流**，应计入股东回报。DefiLlama `holdersRevenue` 也正是这么定义的（见 §二）。 |

**依据**：DefiLlama dimension-adapters 源码 `fees/makerdao.ts`——
```js
addCGToken('sky', sky_buyback_24h, TokenBuyBack)      // SKY 回购
addCGToken('usds', ..., StakingRewards)               // 付给 SKY stakers 的 USDS 奖励
```
即 Sky 的 `HoldersRevenue` = **SKY 回购 + SKY stakers 质押奖励**，是**混合口径**，不是"纯 burn"。

---

## 二、回报口径（Boss 2026-10-08 定稿）

**股东回报 = DefiLlama `dailyHoldersRevenue`（sky slug）** — 维持 DefiLlama 混合代理口径

- **含义**：SKY 回购（买币数量 × 当日市价）**+** 付给 SKY stakers 的 USDS 质押奖励
- **性质**：**混合代理（mixed proxy）**——既非纯现金支出，也非纯销毁。前端与详情页必须显著标注，不得表述为"销毁"。
- **收入（Earning）= DefiLlama `dailyRevenue`**：协议归属总收入（已扣 DSR/SSR）
- **payout_ratio** = holdersRevenue / revenue ≈ **0.2981**（2026-10-08）

### D3 决策：保留但重标注 + 单列实际买币额

Boss 决策（2026-10-08）：
- ✅ **保留** DefiLlama `holdersRevenue` 作为股东回报口径（因为它是唯一覆盖"回购 + 质押奖励"双流的数据）
- ✅ **重标注**：全部文案明确写"混合代理，非纯销毁"；删除所有"真燃烧 / LP burn"表述
- ✅ **单列实际买币发生额**：财报页另附 **实际 SBE 买币金额**（来源 https://info.sky.money/buyback），与混合口径金额并行展示，让用户看到"其中真正回购了多少"

---

## 三、当前数字（2026-10-08 快照）

| 项目 | 数值 | 来源 |
|---|---|---|
| 协议收入 365d | **$201,440,351** | DefiLlama `dailyRevenue` |
| 净利润 365d | **$201,440,351** | 协议盈余（CDP 无 LP 分润，毛利=净利） |
| 股东回报 365d | **$60,050,420** | DefiLlama `dailyHoldersRevenue`（混合代理） |
| 股东回报率 365d | **2.8682%** | 60,050,420 / 市值 |
| payout_ratio | **0.2981** | 60,050,420 / 201,440,351 |
| P/S | 10.3935 | 市值 / 收入 |
| P/E | 34.8651 | 市值 / 净利 |
| 留存 365d | $141,389,931（70.2%） | 收入 − 股东回报 |

---

## 四、数据源与自动化

| 数据 | 来源 | 频率 | 维护 |
|---|---|---|---|
| 股东回报 (holdersRevenue) | DefiLlama `summary/fees/sky?dataType=dailyHoldersRevenue` | 每日 | `scripts/sync-holders-revenue.py`（daily-run.sh 步骤 2.5） |
| 收入 (dailyRevenue) | DefiLlama `summary/fees/sky?dataType=dailyRevenue` | 每日 | 同上 |
| 实际买币发生额 | https://info.sky.money/buyback | 手动核对 | 季度复核 |
| 市值 / 价格 | CoinGecko id = `sky` | 每日 | update-prices.py（main 分支） |

**根因修复（2026-10-08）**：旧版 adapter 读取的 `all-protocols.json` `metrics.trailing_*` 字段自 ~2026-08-02 起**不再被重算**（旧 `sync-tev-data.js` 停用），导致 snapshot 永久冻结在 08-02 数值。现由 `sync-holders-revenue.py` 在每日流水线中重算这些字段（步骤 2.5），adapter 再据此产出 snapshot。

---

## 五、为什么不做严格链上（像 Uniswap 那样）

- MKR/SKY @ 0xdead 历史上几乎为 0（无真 burn 到 0xdead）
- SBE 自 2024-09 起是**买币进国库**，不是销毁——链上"销毁地址"路径不成立
- 要做严格链上需追踪 SBE 收款地址的买入交易（info.sky.money/buyback 已公开），工作量大且 DefiLlama 已足够贴近

**权衡**：采用 DefiLlama 混合代理 + 前端重标注 + 单列实际买币额（D3）。若未来 Boss 要求严格链上回购追踪，再迁移到 SBE 地址逐笔解析。

---

## 六、历史口径变更

- **2026-10-08**：更正两处事实错误（SBE 非真 burn / 质押奖励应收录）；口径改为 DefiLlama 混合代理 + 重标注 + 单列实际买币额
- 2026-04-22：从 `fixedTevUsd: $13.724M`（写死）改为动态 `dailyHoldersRevenue`
- 2026-03：SBE 治理减速（$300k/天 → $37.6k/天）
- 2024-09：SBE 由"销毁"改为"买 SKY 交国库"（可再分配）
- 2024-08：Maker 重品牌为 Sky，MKR → SKY 1:24000

---

## 七、调试

```bash
# 查 DefiLlama 三口径（快速校验）
for dt in dailyFees dailyRevenue dailyHoldersRevenue; do
  curl -s "https://api.llama.fi/summary/fees/sky?dataType=$dt" \
    | python3 -c "
import json,sys
d=json.load(sys.stdin); c=d['totalDataChart']
for N in [7,30,90,365]:
  s=sum(v for _,v in c[-N:] if v); print(f'  $dt {N}d: \${s/1e6:.2f}M')
"
done

# 查当前 snapshot
python3 -c "
import json
d=json.load(open('data/snapshots/sky.json'))
print('股东回报率:', d['holder_returns']['summary']['shareholder_yield_percent'])
print('状态:', d['holder_returns']['summary']['status'])
print('收入 365d:', d['income_statement']['revenue']['revenue_included']['total_usd_365d'])
"
```

---

## 八、手动介入触发条件

### 1. Splitter / SBE 参数再次调整
**症状**：`dailyHoldersRevenue` 7d/30d 日均突然跳变
**处理**：查 forum.sky.money 治理投票，更新 config.json 的 analyst_notes。

### 2. SBE 恢复"真销毁"（治理变更）
**症状**：治理公告宣布 SBE 重新销毁而非进国库
**处理**：把股东回报口径从"混合代理"升级为"含销毁"，前端文案相应调整。

### 3. DefiLlama 口径变化
**症状**：`dailyHoldersRevenue` 与 info.sky.money/buyback 实际买币额偏差扩大
**处理**：核对 DefiLlama 方法学变更；若偏差持续 >10%，考虑迁移到 SBE 地址链上追踪。
