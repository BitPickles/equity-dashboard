# Aave TEV 数据维护说明

Aave（AAVE）协议的 TEV（Token Economic Value）数据口径、数据源、自动更新。

---

## 一、TEV 双源机制

Aave 的 TEV = **固定 Buyback** + **动态 Safety Module holders revenue**，两个独立 signal。

### 1. 年度 Buyback（固定 $30M/年，2026-03 治理）

- **起源**：AIP-73 "Aavenomics Update Part 1"（2024-07）设立
- **2026-03 治理**：从 $50M/年 下调至 $30M/年（99.37% 通过）
- **执行**：TokenLogic / Aave Finance Committee (AFC) 用 DAO 财库 USDC/GHO 市场买入 AAVE
- **⚠️ 关键 caveats**：
  - 买来的 AAVE 存入 **Ecosystem Reserve** (`0x25F2...6491`) + AFC multisig
  - **不是真 burn**，是 **treasury-accumulated**，类似 Hyperliquid AF
  - 治理可 redistribute（用于 Umbrella stakers 激励 / contributor grants）
  - 链上验证：365d AAVE → 0xdead = **0.0001 AAVE**（确认不 burn）

**为什么仍算 TEV**：从流通市场买走的 AAVE 不在流通中，即便 re-distribute 给 stakers 也是重新分配给持有人群体，对全体持有人有价值。但必须在前端显著标注"treasury-accumulated, governance-reversible"。

### 2. Safety Module (Umbrella) holders revenue（动态，按窗口）

- **来源**：Aave 协议 reserve factor 收入 + liquidation fees
- **数据源**：DefiLlama `dailyHoldersRevenue`（Aave slug）
- **特点**：**脉冲式分发**——每 1-2 周一次大包（$200k~$6M），其他天为 0
- **Umbrella 迁移**：2025 年 Umbrella 新合约替代旧 `stkAAVE (0x4da2...70f5)`

---

## 二、TEV 公式

```
TEV_Nd = $30M (Buyback 年化) + (DefiLlama holdersRevenue sum_Nd × 365/N)
      ÷ marketCap × 年化因子
```

| 周期 | Buyback 部分 | SM 部分 | 合计 |
|---|---|---|---|
| 7d | $30M（年化固定）| holdersRevenue_7d × 52 | × 1/mcap |
| 30d | $30M | holdersRevenue_30d × 12.17 | 同上 |
| 90d | $30M | holdersRevenue_90d × 4.06 | 同上 |
| 365d | $30M | holdersRevenue_365d（不年化）| 同上 |

---

## 三、方案 A：按窗口严格累加（Boss 2026-04-22 定）

选择的代价：
- 短周期（7/30d）**碰巧没抓到 SM 分发大包**时，TEV 会降到只剩 buyback
- 最近 50+ 天 SM = $0（Umbrella 迁移期？），所以 7d/30d TEV = **1.67%**
- 90d/365d 抓到若干分发，TEV 回升到 **3.19% / 3.91%**

这不是"TEV 下降"，是 Aave 的 Safety Module 分发**不是每天**。用户需要理解脉冲式节奏。

**备选方案（未采用）**：
- 方案 B：所有周期都用 365d SM 平均 = 稳定 3.91%，但切周期无变化
- 方案 C：近 3 次 payout 平均，复杂但更稳

---

## 四、当前数字（2026-04-22 快照）

| 周期 | TEV | Earning | 分配率 |
|---|---|---|---|
| 7d | **1.67%** | 8.65% | 19.31% |
| 30d | **1.67%** | 5.18% | 32.24% |
| 90d | **3.19%** | 5.63% | 56.66% |
| 365d | **3.91%** | 6.91% | 56.58% |

365d 分配率 ~57% 是稳定态。短周期低是 SM 暂停的真实信号。

---

## 五、数据源

| 数据 | 来源 | 维护 |
|---|---|---|
| Buyback 固定 $30M/年 | `scripts/sync-tev-data.js` aave 分支 `fixedBuybackUsd` | 手动同步治理变更 |
| SM holders revenue | DefiLlama `dailyHoldersRevenue` (slug=aave) | 每日 sync 自动拉 |
| 协议 Revenue (Earning) | DefiLlama `dailyRevenue` (slug=aave) | 每日 sync 自动拉 |
| 市值 | CoinGecko / CMC | 主流程 |
| 链上 Buyback 校验 | **未实现**（TokenLogic 执行合约地址待核实）| 未来扩展 |

---

## 六、链上验证（2026-04-22 核实）

```
AAVE @ 0xdead 当前: 0.2750 AAVE
AAVE → 0xdead 365d: 0.0001 AAVE（3 个 events，微不足道）
AAVE → Safety Module 365d: 315,737 AAVE（10,000+ events，含用户质押）
```

结论：
- **完全不 burn 到 0xdead** → A 口径（Uniswap 那种）不适用
- Safety Module 有大量 AAVE 活动，但混合了用户质押 + 协议分发

---

## 七、手动介入触发条件

### 1. 治理再次调整 Buyback 预算

**处理**：
1. 查 governance.aave.com 最新 AIP
2. 更新 `scripts/sync-tev-data.js` 里 `fixedBuybackUsd` 或 PROTOCOL_CONFIG 的 `fixedTevUsd`
3. 在 analyst_notes 追加历史记录

### 2. Umbrella DefiLlama 追踪恢复

**症状**：dailyHoldersRevenue 最近几天突然回升

**处理**：无需代码改动，脚本会自动抓新数据；更新 analyst_notes 确认 "Umbrella 已正常追踪"

### 3. Buyback 执行合约变更

**处理**：扩展 `sync-tev-data.js` 加 TokenLogic 执行合约的链上校验（类似 Hyperliquid `update-hype-tev.py`）

---

## 八、调试

```bash
# 重跑 aave yield
node scripts/sync-tev-data.js aave

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

# 查链上 AAVE @ 0xdead
# (etherscan V2 tokenbalance API)

# 查当前主表
python3 -c "
import json
d=json.load(open('data/all-protocols.json'))['protocols']['aave']
print('tev_yield:', d.get('shareholder_yield_percent'))
print('payout_ratio 各周期:', d.get('payout_ratio_7d'), d.get('payout_ratio_30d'), d.get('payout_ratio_90d'), d.get('payout_ratio_365d'))
print('validation:', json.dumps(d.get('validation', {}), indent=2, ensure_ascii=False))
"
```

---

## 九、历史口径变更

- 2026-04-22: 双源组合（Buyback + SM holdersRevenue），各周期独立；明确 buyback 是 treasury 非 burn；payout_ratio 按周期
- 2026-03: 治理 Buyback 从 $50M → $30M
- 2024-07-25: AIP-73 启动 Aavenomics buyback
