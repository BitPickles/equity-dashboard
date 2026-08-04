# Sky (MakerDAO) TEV 数据维护说明

本文档说明 Sky（原 MakerDAO）协议的 TEV（Token Economic Value）数据如何计算、数据源、自动更新。

> **品牌变化**：Maker 于 2024-08 重品牌为 Sky，MKR → SKY（1:24000 转换）。本 dashboard 继续用 MKR 作为 ticker 显示（历史连续性）；但 价值分配机制数据已对齐到 Sky 时代（Splitter/SBE）。

---

## 一、价值分配机制

### Smart Burn Engine (SBE)

Sky 协议盈余 → **Surplus Buffer** → **Splitter** 分流：

```
Splitter
├── Burn 部分 → SBE（市场买 MKR + LP → LP token burn）  ← TEV
└── Farm 部分 → SKY stakers（新铸造 SKY + USDS yield）  ← 不算 TEV
```

**为什么 Farm 部分不算 TEV**：
- 新铸造 SKY 给 stakers 是**增发 + 分配**，不是市场回购
- 经济上类似 inflation reward（支出性分配），对现有持有人是稀释
- 真正对全体持有人的价值传递只有 SBE burn

### SBE 如何 burn

```
Surplus DAI/USDS
  → Flapper (Uniswap v2 MKR/DAI adapter)
  → 市场买 MKR
  → 和 DAI 组成 UniV2 LP
  → LP token 发到 0xdead-style 地址（真销毁）
```

**LP token 销毁 = MKR 永久锁死在 Uniswap pool**（不是 transfer to 0xdead），这是和 Uniswap 的 A 口径的关键区别。

---

## 二、回报口径（2026-04-22 切换）

**TEV = DefiLlama `dailyHoldersRevenue`（Sky slug）**

为什么：
- 它精准反映 Splitter 的 burn 部分实际支出
- 最近 30d 日均 $37.5k，和 2026-03 治理公告的 "$37,600/天" 完全吻合
- 比之前的 `fixedTevUsd: $13.724M` 写死值更动态，能反映参数变化

**Earning Yield = DefiLlama `dailyRevenue`**（协议归属总收入，已扣除 DSR/SSR 支出）

**动态 payout_ratio** = holdersRevenue / revenue ≈ 0.48（Splitter 当前 burn 比例）

---

## 三、各周期数字（2026-04-22 快照）

| 周期 | HoldersRevenue | Revenue | Shareholder Yield | Earning Yield |
|---|---|---|---|---|
| 7d | $0.26M | $3.34M | 0.76% | 9.60% |
| 30d | $1.13M | $14.25M | 0.75% | 9.55% |
| 90d | $15.63M | $48.95M | 3.49% | 10.94% |
| **365d** | $120.90M | $250.28M | **6.66%** | **13.79%** |

**短周期 TEV < 365d TEV** 反映 2026-03 治理减速——这不是"价值损失"，是"burn 速度调整"。

---

## 四、数据源与自动化

| 数据 | 来源 | 波动 | 维护 |
|---|---|---|---|
| HoldersRevenue (TEV) | DefiLlama `sky` slug `dailyHoldersRevenue` | 每日 | sync-tev-data.js Sky 专属分支 |
| Revenue (Earning) | DefiLlama `sky` slug `dailyRevenue` | 每日 | sync-tev-data.js |
| 市值 / 价格 | CoinGecko `maker` / CMC `sky` | 每日 | sync-tev-data.js |
| 链上 SBE 校验 | **未实现**（新 Flapper 地址未公开追踪）| — | 待做 |

---

## 五、为什么不做严格链上（像 Uniswap 那样）

Uniswap 的 A 口径直查 0xdead 接收的 UNI——简单直接。

Sky 不能这么做：
- **MKR @ 0xdead 过去 365d 只有 0.0001 MKR**（几乎为 0）
- **SKY @ 0xdead 只有 4.82 SKY**
- 说明 SBE **不把 MKR burn 到 0xdead**，而是 burn LP token

真正要追链上需要：
1. 新 Flapper 合约地址（已迁移到哪个不公开）
2. 追踪 LP token 的 transfer 到 burn 地址
3. 核对 LP token 对应的 MKR + DAI 价值

工作量大，且 DefiLlama 已经准确（和治理公告吻合 <1% 误差）。采用 DefiLlama 是合理权衡。

如果未来 Boss 要求严格链上，需要：
- 从 Sky forum 或 makerburn.com 找当前 active Flapper 地址
- 写脚本追踪 Flapper 的 DAI/USDS 流出

---

## 六、历史口径变更

- 2026-04-22: 从 `fixedTevUsd: $13.724M`（写死）改为动态 `dailyHoldersRevenue`；payout_ratio 从 0.7 静态改为动态计算（当前 ~0.483）
- 2026-03: SBE 治理减速生效（$300k/天 → $37.6k/天，-87.5%）
- 2024-08: Maker 重品牌为 Sky，MKR → SKY 1:24000 转换

---

## 七、调试

```bash
# 重跑 sky yield
cd ~/.openclaw/workspace-engineer/tev-dashboard
node scripts/sync-tev-data.js sky

# 查 DefiLlama 口径（快速校验）
for dt in dailyFees dailyRevenue dailyHoldersRevenue; do
  curl -s "https://api.llama.fi/summary/fees/sky?dataType=$dt" \
    | python3 -c "
import json,sys
d=json.load(sys.stdin); c=d['totalDataChart']
for N in [7,30,90,365]:
  s=sum(v for _,v in c[-N:] if v); print(f'  $dt {N}d: \${s/1e6:.2f}M')
"
done

# 查当前主表数字
python3 -c "
import json
d=json.load(open('data/all-protocols.json'))['protocols']['sky']
print('TEV 365d:', d['shareholder_yield_percent'])
print('Earning 365d:', d['total_yield_percent'])
print('payout_ratio:', d['payout_ratio'])
print('validation:', json.dumps(d.get('validation', {}), indent=2, ensure_ascii=False))
"
```

---

## 八、手动介入触发条件

### 1. Splitter 参数再次调整

**症状**：`dailyHoldersRevenue` 7d/30d 日均突然跳变

**处理**：查 forum.sky.money 的最新治理投票，更新 analyst_notes 的"历史口径变更"段。

### 2. MKR → SKY 完全转换完成

**症状**：MKR 流通量归零或治理投票弃用 MKR

**处理**：改 `config.json` 的 ticker 从 MKR → SKY，检查 CoinGecko/CMC slug 是否需调整。

### 3. DefiLlama 口径变化

**症状**：`dailyHoldersRevenue` 和链上 SBE 实际支出（链上可观察到 Flapper 调用）偏差扩大

**处理**：核对 DefiLlama 方法学变更，如偏差持续 >10%，考虑迁移到链上 Flapper 追踪。
