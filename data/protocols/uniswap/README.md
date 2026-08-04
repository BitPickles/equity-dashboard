# Uniswap TEV 数据维护说明

本文档说明 Uniswap（UNI）协议的 TEV（Token Economic Value）数据如何计算、从哪里来、怎么自动更新。

---

## 一、TEV 口径（A 口径，Boss 2026-04-22 定）

**TEV = 过去 365 天 UNI 转入 0xdead 地址的累计（USD 当前价重估）**

排除条件：
- 单笔 ≥ 10M UNI 的**一次性治理事件**（如 2025-12-27 Timelock 执行的 100M retroactive burn）
- 原因：这些事件不可持续，年化会严重高估未来 TEV

不用 DefiLlama `dailyRevenue` 的原因：
- 它反映"协议费流入 treasury"，不等于"已 burn"
- 类似 Hyperliquid AF 陷阱——钱进了协议控制地址但没真销毁
- A 口径只认**链上真实 supply 收缩**

---

## 二、公式

```
TEV Yield(N天) = Σ(过去 N 天 UNI → 0xdead，扣除 >=10M 单笔) × 当前 UNI 价 ÷ 市值 × 年化因子
```

其中：
- 年化因子：7/30/90d 用 365/N；365d = 1（不年化）
- UNI 价：市值 ÷ 流通量（~634M，CoinGecko 口径）

---

## 三、数据源与自动化

| 数据 | 文件 | 波动 | 自动化脚本 | 数据源 |
|---|---|---|---|---|
| UNI → 0xdead 转账 | `data/protocols/uniswap/burn-history.json` | 每日 | seed 一次性 + update-uni-tev.py 每日增量 | Etherscan V2 logs API（chainid=1，ETH mainnet）|
| UNI 市值/价格 | `data/all-protocols.json → uniswap.market_cap_usd` | 每日 | `update-uni-tev.py` | CoinGecko API |
| TEV Yield | `data/all-protocols.json → uniswap.*` | 每日 | `sync-tev-data.js`（uniswap 专属分支）| 聚合 |

### 主流程（每日 9:03 / 21:03 cron）

```
Step 3: TEV + 协议数据
  ├── fetch-tev-market.py        市场价格
  ├── fetch-bnb-data.py          BSC TVL
  ├── update-bnb-tev.py          BNB 专属
  ├── update-hype-tev.py         HYPE 链上 AF 校验
  ├── fetch-hype-burns.py        HYPE 真实 burn
  ├── fetch-uni-burns.py         UNI 供应/价格（保留，但 TEV 不再依赖）
  ├── update-uni-tev.py      ←── UNI TEV 核心更新（本脚本）
  └── ...

Step 4: TEV 协议汇总
  └── sync-tev-data.js           uniswap 走专属分支，从 burn-history 按窗口汇总
```

---

## 四、update-uni-tev.py 细节

位置：`~/crypto3d-updater/scripts/update-uni-tev.py`

### 三步流程

1. **更新 UNI 市值**（CoinGecko）
2. **拉最近 3 天的 UNI → 0xdead Transfer events**（Etherscan V2 logs API，分页）
   - LOOKBACK_DAYS = 3，覆盖时区差异 + 补漏
3. **合并到 burn-history.json**
   - 按日汇总，去重（同一天重跑会覆盖）
   - 单笔 ≥ 10M UNI → 标为 retro event，单独记入 `retro_events[]`，告警

### Retro 检测阈值

`RETRO_THRESHOLD_UNI = 10,000,000`——超过 10M UNI 的单笔转账视为一次性治理事件。

历史已知：
- 2025-12-27, 100,000,000 UNI, from `0x1a9c...35bc` (Uniswap Governor Timelock), tx `0x091f0083...`

---

## 五、burn-history.json 结构

```json
{
  "source": "Etherscan V2 getLogs (UNI Transfer to 0xdead)",
  "seeded_at": "2026-04-22T...",
  "updated_at": "2026-04-22T...",
  "from_block": 22324846,
  "retro_events": [
    { "date": "2025-12-27", "amount": 100000000, "from": "0x1a9c...35bc", "tx": "0x091f...2c1e" }
  ],
  "daily": [
    { "date": "2025-06-07", "uni": 3.58, "tx_count": 1 },
    ...
  ]
}
```

`daily[].uni` = 当日 Transfer 到 0xdead 的 UNI 数量（扣除 retro）。

---

## 六、已知局限（重要！）

1. **仅覆盖 Ethereum mainnet**
   - Firepit 同时部署在 **Unichain**（Uniswap 的 OP-stack L2）
   - Unichain 上的 UNI 销毁**未计入**
   - 需扩展 `update-uni-tev.py` 查询 Unichain 链上数据（Unichain explorer/RPC）

2. **from 地址分布复杂**
   - 365d 内 63 个不同 from 地址
   - Top 包括 L2 桥代理（`L1ChugSplashProxy`）、`TransparentUpgradeableProxy`、EOA 等
   - 并非全部是 Firepit 合约——部分是用户个人 burn / bot 自动化
   - A 口径按"到 0xdead 即算 supply 收缩"处理，无论来源
   - 如果后续需要严格的"协议机制 TEV"，要 whitelist Firepit 合约地址

3. **fee switch 启动前 365d 窗口为 0**
   - burn 活动从 2025-06 才开始（fee switch 相关机制上线）
   - 365d 窗口前半段（2025-04 到 2025-06）完全没有 burn
   - 短周期 yield 高于 365d 反映加速趋势，不是"TEV 下降"

4. **未查 Unichain sequencer revenue 流向**
   - Unichain 85% sequencer revenue 归 Uniswap Foundation
   - 但目前未追踪它是否被用于额外 UNI 回购
   - 潜在有更多 TEV 来源未被计入

---

## 七、手动介入触发条件

### 1. 新的一次性 >=10M UNI burn

**症状**：`update-uni-tev.py` 告警 `⚠️⚠️⚠️ 新检测到 >10M UNI burn`

**处理**：
1. 查 tx 上下文（Etherscan）
2. 确认是一次性治理事件（不应计入 TEV）还是异常（需重新评估）
3. 已自动加入 `retro_events[]`，无需手工改文件；但应确认逻辑无误并在 analyst_notes 补记

### 2. Fee Switch 被关闭

**症状**：burn 量突然接近 0 持续数日

**处理**：查 Uniswap governance forum，可能需更新 analyst_notes 标注"fee switch 已关闭"

### 3. Unichain 数据需要接入

**处理**：扩展 `update-uni-tev.py`，加 Unichain RPC 调用；更新 burn-history.json schema 记录 chain 来源

---

## 八、调试

```bash
# 手动跑 UNI TEV 更新
python3 ~/crypto3d-updater/scripts/update-uni-tev.py

# 重跑 yield 聚合
cd ~/.openclaw/workspace-engineer/tev-dashboard
node scripts/sync-tev-data.js uniswap

# 查当前数字
python3 -c "
import json
d = json.load(open('data/all-protocols.json'))['protocols']['uniswap']
print('shareholder_yield_percent:', d.get('shareholder_yield_percent'))
print('validation:', json.dumps(d.get('validation', {}), indent=2))
"

# 查 UNI@0xdead 当前余额（验证）
curl -s -X POST https://ethereum.publicnode.com -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"0x1f9840a85d5af5bf1d1762f925bdaddc4201f984","data":"0x70a08231000000000000000000000000000000000000000000000000000000000000dead"},"latest"],"id":1}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print('UNI@0xdead:', int(r['result'],16)/1e18, 'UNI')"
```

---

## 九、历史记录

- 2026-04-22: A 口径上线；切换到 Etherscan V2 链上直查；每日增量 `update-uni-tev.py`；发现 top from 地址多为 L2 桥/EOA，A 口径按 supply 收缩视角处理
- 2026-03-02: 初版使用 DefiLlama revenue 估算
