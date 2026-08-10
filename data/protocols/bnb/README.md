# BNB TEV 数据维护说明

本文档说明 BNB 协议的 TEV（Token Economic Value）数据如何计算、从哪里来、怎么自动更新。

> **前提**：其他协议的 TEV 计算由 `scripts/sync-tev-data.js` 通用分支处理（基于 `payout_ratio × DefiLlama revenue`）。**BNB 不适用通用公式**（CEX token，没有 fee 分润机制），所以独立维护。

---

## 一、TEV 公式

```
Shareholder Yield = Burn Yield + asBNB APY
         = (Auto-Burn USD + BEP-95 USD) ÷ 市值 + asBNB APY
```

**Auto-Burn**（季度事件，双口径）：
- 7d / 30d / 90d：近 4 季 burn 的 `usd_value` 累加（每次 burn 公告时的历史 USD 值）
- 365d：近 4 季 burn 的 `bnb_burned` 合计 × 当前 BNB 价

**BEP-95**（每区块持续销毁，按窗口从时间序列求和）：
- 7d：近 7 天 BNB × 365/7 × 当前价
- 30d：近 30 天 BNB × 365/30 × 当前价
- 90d：近 90 天 BNB × 365/90 × 当前价
- 365d：近 365 天 BNB 累计 × 当前价

**asBNB APY**：固定 6.87%（Aster 官方披露，含 Staking + Launchpool/HODLer/Megadrop）

**Earning Yield** = BEP-95 + asBNB APY（不含 Auto-Burn，因为 Auto-Burn 是公式销毁不是协议"收入"）

---

## 二、数据源与自动化

| 数据 | 文件 | 波动 | 自动化脚本 | 数据源 |
|---|---|---|---|---|
| Auto-Burn 季度事件 | `burn-history.json → quarterly_burns[]` | 季度一次 | `update-bnb-tev.py` 检测告警（不自动写） | BSC RPC + bnbburn.info（人工确认） |
| BEP-95 日销毁 | `bep95-history.json → daily[]` | 每日 | `update-bnb-tev.py` 累积法 | BSC RPC（dead address 余额差分） |
| BNB 市值/价格 | `data/all-protocols.json → protocols.bnb.market_cap_usd` | 每日 | `update-bnb-tev.py` | CoinGecko API |
| asBNB APY | `burn-history.json → asbnb_apy_percent` | 季度 | **未自动化**，需人工更新 | Aster 官方 earn 页面 |
| 最终 TEV/Earning Yield | `data/all-protocols.json → protocols.bnb.*` | 每日 | `scripts/sync-tev-data.js`（BNB 专属分支） | 以上 4 源聚合 |

---

## 三、运行时序

由 LaunchAgent `com.crypto3d.data-updater` 每日 9:03 / 21:03 触发，调用 `~/crypto3d-updater/update.sh`，内部顺序：

```
Step 3: TEV + 协议数据
  ├── fetch-tev-market.py        市场价格
  ├── fetch-bnb-data.py          BSC TVL + BNB 供应量
  ├── update-bnb-tev.py      ←── BNB TEV 核心更新（本脚本）
  ├── fetch-uni-burns.py         其他协议
  └── ...

Step 4: TEV 协议汇总
  └── sync-tev-data.js           聚合所有协议，重算 yield
```

`update-bnb-tev.py` 必须在 `sync-tev-data.js` **之前**跑——因为后者读取前者更新的市值和 BEP-95 时间序列来重算 TEV yield。

---

## 四、update-bnb-tev.py 细节

位置：`~/crypto3d-updater/scripts/update-bnb-tev.py`

### 四步流程

1. **更新 BNB 市值**（每次必跑）
   - `https://api.coingecko.com/api/v3/simple/price?ids=binancecoin`
   - 写入 `data/all-protocols.json` 的 `protocols.bnb.market_cap_usd`

2. **查 dead address 余额**（BSC RPC 轮询）
   - 节点：Binance/defibit/ninicoin/publicnode（4 个公共 RPC，fallback）
   - 方法：`eth_getBalance(0x000...dEaD, latest)`
   - 返回 BNB 数量（wei / 1e18）

3. **Auto-Burn 新事件检测**
   - 读 `dead-balance-snapshot.json` 的上次余额
   - delta = 今日余额 - 上次余额
   - 如果 `delta - 已记录 quarterly_burns > 10 万 BNB`：**告警**
   - 告警后需人工介入：到 https://www.bnbburn.info/ 确认，补 `burn-history.json.quarterly_burns`（**脚本不自动写入 quarterly_burns**，避免误判）

4. **BEP-95 累积**
   - bep95_delta = delta - 已记录的 quarterly_burn
   - 按 (last_date, today] 区间天数平摊，每天一条追加到 `bep95-history.json.daily`
   - 更新 snapshot

### 首次运行行为

- `dead-balance-snapshot.json` 不存在 → 仅初始化快照，不写 bep95-history
- 从次日起每日 delta = 当日销毁量

### 同一天重复运行

- 检测到 snapshot.date == today → 跳过 BEP-95 累积
- 但**市值仍会更新**（每次必跑）

---

## 五、文件清单

| 文件 | 用途 | 维护方式 |
|---|---|---|
| `data/protocols/bnb/config.json` | 协议元数据、价值分配机制、analyst_notes | 手写；脚本回写计算字段 |
| `data/protocols/bnb/burn-history.json` | quarterly_burns 历史 + asbnb_apy | 手动补新 burn；asbnb_apy 手动季度更新 |
| `data/protocols/bnb/bep95-history.json` | BEP-95 日时间序列 | Dune 种子 + 每日 RPC 累积 |
| `data/protocols/bnb/bep95-dune-seed.csv` | Dune 一次性种子数据 | 保留审计，可重跑 `scripts/seed-bep95-from-csv.py` |
| `data/protocols/bnb/dead-balance-snapshot.json` | 上次余额快照（内部状态）| 脚本自动维护 |
| `data/all-protocols.json` → bnb | 主表渲染数据 | `update-bnb-tev.py` 更新市值，`sync-tev-data.js` 更新 yield |

---

## 六、手动介入触发条件

以下情况需要人工处理，**脚本会告警但不自动操作**：

### 1. 新季度 Auto-Burn（约每 90 天）

**症状**：`update-bnb-tev.py` 日志出现 `⚠️⚠️⚠️ 检测到未记录的大额销毁`

**处理**：
1. 打开 https://www.bnbburn.info/ 确认新 burn 数据
2. 编辑 `data/protocols/bnb/burn-history.json`，追加 `quarterly_burns`：
   ```json
   {
     "number": 36,
     "date": "YYYY-MM-DD",
     "bnb_burned": 1234567.89,
     "bnb_price": 650,
     "usd_value": 802469128
   }
   ```
3. 同时编辑 `data/protocols/bnb/config.json` 的 `burn_history[]`（历史展示用）
4. 下次 `sync-tev-data.js` 运行时会自动用新数据

### 2. asBNB APY 变化

**触发**：每季度去 https://www.asterdex.com/en/earn/astoken?token=slisBNB 核对 APY

**处理**：更新 `burn-history.json.asbnb_apy_percent` 字段

### 3. BEP-95 数据中断

**症状**：bep95-history.json 长时间未更新

**处理**：
- 检查 `dead-balance-snapshot.json` 是否损坏，删除可重新初始化
- 或重跑 Dune query 导出最新数据 → 放到 `bep95-dune-seed.csv` → 运行 `python3 scripts/seed-bep95-from-csv.py`

---

## 七、调试

```bash
# 手动跑一次 BNB TEV 更新
python3 ~/crypto3d-updater/scripts/update-bnb-tev.py

# 查看日志
tail -50 ~/crypto3d-updater/logs/bnb-tev.log

# 只重跑 BNB 的 yield 聚合
cd ~/.openclaw/workspace-engineer/tev-dashboard
node scripts/sync-tev-data.js bnb

# 查当前 BNB 主表数据
python3 -c "
import json
d = json.load(open('data/all-protocols.json'))['protocols']['bnb']
print('shareholder_yield_percent:', d.get('shareholder_yield_percent'))
print('market_cap_usd:', d.get('market_cap_usd'))
print('metrics:', d.get('metrics'))
"

# 查 dead address 余额（手动验证 RPC）
python3 -c "
from urllib.request import urlopen, Request
import json
req = Request('https://bsc-dataseed.binance.org/',
  data=json.dumps({'jsonrpc':'2.0','method':'eth_getBalance','params':['0x000000000000000000000000000000000000dEaD','latest'],'id':1}).encode(),
  headers={'Content-Type':'application/json'})
r = json.loads(urlopen(req).read())
print('Dead balance:', int(r['result'],16)/1e18, 'BNB')
"
```

---

## 八、历史记录

- 2026-04-19: 初版 `update-bnb-tev.py` 上线；Dune 种子一次性导入 2025-03-14 → 2026-04-18 共 401 天 BEP-95 数据；发现并补录 35th Auto-Burn (2026-04-15)
- 2026-04-19: Shareholder Yield 改为真实的按周期计算（之前所有周期共用同一值）
- 2026-03-01: 从 slisBNB 单一 proxy 改为 Burn + asBNB 双源
