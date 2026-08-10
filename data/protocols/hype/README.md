# Hyperliquid TEV 数据维护说明

本文档说明 Hyperliquid（HYPE）协议的 TEV（Token Economic Value）数据如何计算、从哪里来、怎么自动更新。

---

## 一、价值分配机制（关键澄清）

Hyperliquid 有**两个独立的供给相关机制**，容易混淆：

| 机制 | 量级 | 性质 |
|---|---|---|
| **AF (Assistance Fund) 买入** | ~43M HYPE（$1.07B 累计买入成本）| **Treasury buyback**：HYPE 留在 AF 地址 `0xfefe...fefe`，理论上可被 validator consensus 动用 |
| **Spot 手续费销毁** | ~745k HYPE（0.075%）| **真正的永久销毁**：spot 交易中用 HYPE 支付的手续费直接销毁 |

### 回报口径选择

crypto3d 采用 **"AF buyback + spot burn"** 作为 TEV，因为：
- AF 累积对流通供给确实有**收缩效应**（等效销毁，至少在 AF 不动用时）
- 历史上 AF 从未被大规模动用（JELLY 事件由 HLP 解决）
- 但需要在前端 **显著标注 AF 可被动用风险**

**不算 TEV 的部分**：
- HLP 分成：归流动性提供者，不归 token 持有人
- Funding：多空点对点支付，平台不收取
- HyperEVM gas burn：供给收缩，但不属于 token 持有人价值分配

---

## 二、公式

```
Shareholder Yield = (AF buyback USD + spot burn USD) ÷ market_cap × 年化因子
         ≈ DefiLlama dailyRevenue ÷ market_cap
```

**为什么 DefiLlama dailyRevenue 能直接用**：
已验证 `dailyRevenue` = `dailyHoldersRevenue`（DefiLlama 已剥离 HLP/builder/referral），且累计值与链上 AF `entryNtl` 误差 <5%。

### 各周期

| 周期 | 公式 |
|---|---|
| 7d / 30d / 90d | `sum(revenue[last N days]) × 365/N ÷ market_cap` |
| 365d | `sum(revenue[last 365 days]) ÷ market_cap` |

---

## 三、数据源与自动化

| 数据 | 文件 | 波动 | 自动化脚本 | 数据源 |
|---|---|---|---|---|
| AF 买入 USD | `data/protocols/hype/af-history.json` | 每日 | seed 脚本 + sync-tev-data.js 主用 DefiLlama | DefiLlama `dailyRevenue` |
| AF 链上校验 | `data/protocols/hype/af-snapshot.json` | 每日 | `update-hype-tev.py` | Hyperliquid API `spotClearinghouseState` |
| Spot burn | `data/hype-burns.json` | 每日 | `fetch-hype-burns.py` | Hyperliquid API `tokenDetails` |
| HYPE 市值 | `data/all-protocols.json → hype.market_cap_usd` | 每日 | sync-tev-data.js | CoinGecko / CMC |
| 最终 yield | `data/all-protocols.json → hype.*` | 每日 | sync-tev-data.js（SKIP_PROTOCOLS 分支）| 聚合 |

### 主流程（每日 9:03 / 21:03 cron）

```
Step 3: TEV + 协议数据
  ├── fetch-tev-market.py        市场价格
  ├── fetch-bnb-data.py          BSC TVL
  ├── update-bnb-tev.py          BNB 专属
  ├── update-hype-tev.py     ←── HYPE 链上 AF 校验（本脚本）
  ├── fetch-hype-burns.py        HYPE 真实 burn
  └── ...

Step 4: TEV 协议汇总
  └── sync-tev-data.js           hype 走 SKIP_PROTOCOLS 分支，拉 DefiLlama 算 yield
```

---

## 四、校验脚本 update-hype-tev.py

**职责**：每日校验 DefiLlama 数据与链上 AF 状态一致性，**不修改主数据流**。

### 三步流程

1. 查链上 AF 余额：Hyperliquid API `spotClearinghouseState(0xfefe...)`
   - 拿 HYPE `total`（余额）和 `entryNtl`（累计买入 USD）
2. 对比上次 snapshot（`af-snapshot.json`）
   - `delta_entry_ntl = 今日 entryNtl - 上次 entryNtl`
3. 从 DefiLlama 拉同期 revenue 累加
   - 两口径差异 > 15% → 告警

### 告警条件

- **差异 > 15%**：可能 DefiLlama 口径变化 / AF 卖出过 HYPE / 统计边界错位
- **delta_entry_ntl < 0**：AF 净减仓 —— 这是 TEV 假设的重大变化，需人工排查链上 tx 并更新 caveats

---

## 五、文件清单

| 文件 | 用途 | 维护方式 |
|---|---|---|
| `data/protocols/hype/config.json` | 元数据、机制、analyst_notes | 手写；脚本回写计算字段 |
| `data/protocols/hype/af-history.json` | AF 买入 USD 日时间序列 | `scripts/seed-hype-af-history.py` 种子 + 未来可扩展增量 |
| `data/protocols/hype/af-snapshot.json` | 上次链上 AF 状态（校验基准）| `update-hype-tev.py` 自动维护 |
| `data/hype-burns.json` | HYPE spot burn 数据 | `fetch-hype-burns.py` |
| `data/all-protocols.json → hype` | 主表渲染数据 | `sync-tev-data.js` |

---

## 六、手动介入触发条件

### 1. AF 被动用（未发生过）

**症状**：`update-hype-tev.py` 告警 `AF entry_ntl 减少 ... AF 出售过 HYPE`

**处理**：
1. 查链上 AF 地址的 outgoing tx（purrsec.com / blockscout）
2. 确认是合法动用（救灾/清算补偿）还是异常
3. 更新 config.json 的 `caveats`，在 analyst_notes 里记录事件

### 2. DefiLlama 口径变化

**症状**：连续多天 DefiLlama vs 链上 delta 差异 > 15%

**处理**：
1. 查 DefiLlama 协议页面看是否有方法学公告
2. 若口径变化，考虑切换数据源：直接用链上 AF `entryNtl` delta 作为 TEV 主源

### 3. HYPE tokenomics 变更

**处理**：重写 analyst_notes，更新 return_mechanisms

---

## 七、调试

```bash
# 手动跑链上校验
python3 ~/crypto3d-updater/scripts/update-hype-tev.py

# 查看 AF 当前状态
curl -s -X POST https://api.hyperliquid.xyz/info \
  -H "Content-Type: application/json" \
  -d '{"type":"spotClearinghouseState","user":"0xfefefefefefefefefefefefefefefefefefefefe"}' \
  | python3 -c "import json,sys; bal=json.load(sys.stdin)['balances']; [print(b) for b in bal if b['coin'].upper()=='HYPE']"

# 重跑 hype 的 yield 聚合
cd ~/.openclaw/workspace-engineer/tev-dashboard
node scripts/sync-tev-data.js hype

# 查当前 hype 主表数据
python3 -c "
import json
d = json.load(open('data/all-protocols.json'))['protocols']['hype']
print('shareholder_yield_percent:', d.get('shareholder_yield_percent'))
print('market_cap_usd:', d.get('market_cap_usd'))
print('metrics:', json.dumps(d.get('metrics'), indent=2))
"

# 重新 seed af-history.json（从 DefiLlama 拉完整历史）
cd ~/.openclaw/workspace-engineer/tev-dashboard
python3 scripts/seed-hype-af-history.py
```

---

## 八、历史记录

- 2026-04-19: 修正 "AF 买入即销毁" 错误描述；SKIP_PROTOCOLS 分支加 365d 字段；新增 update-hype-tev.py 链上校验
- 2026-02/03: 初版 AF 口径（理解有误，当 burn 处理）
