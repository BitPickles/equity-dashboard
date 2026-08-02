# Financial Snapshot 统一 Schema（v2）

> **位置**：机器可校验版 → `docs/schema/financial-snapshot.schema.json`（JSON Schema draft-07）
> **权威定义**：PRD v2.1 第 5.2 节（本文为其落地说明）
> **产出**：`data/snapshots/<protocol>.json`，由 `scripts/build-snapshot.py` 生成
> **消费方**：`sync-tev-data.js`（聚合 → all-protocols.json）、`validate.py`（校验）、前端财报页

---

## 一、设计铁律（违反即 validate 失败）

1. **派生字段禁止手写**：`valuation`（pe/ps/pb/ev_revenue/payout_ratio）与 `margins`（gross/net margin）必须由 `build-snapshot.py` 从 L1–L3 数据**计算派生**，任何协议 config 里出现手写的派生值 → validate 报错。
2. **无数据一律 `null`，禁止编造 0**：数据不可得 → `null` → 前端渲染 `—`。
3. **只计流向流通持币人的价值流**：未流通储备的内部变动（销毁/划转）不计入股东回报，最多作 `note` 注记。
4. **所有计算基于净利润**：收入 ≠ 总协议费，必须扣除 LP 分润后再进入净利口径。
5. **增发成本配比原则**：有对价换当期收入（LP 挖矿/gauge/farm）→ `treatment: "cost"` 从净利扣除；无对价 → `treatment: "dilution_note"` 仅作稀释注记。
6. **holder_returns 与 all-protocols.json 数值一致**：`summary.shareholder_yield_percent` 必须等于现有 `shareholder_yield_percent`（旧 `tev_yield_percent`）字段，post-pass 校验。

## 二、字段结构总览

```jsonc
{
  "protocol": "bnb",                          // 协议 id
  "as_of": "2026-08-02",                      // 快照数据日期
  "income_statement": {                       // 损益表
    "revenue": {                              // 收入（3.3 判定框架，实体分轨）
      "entity_type": "platform_token|public_chain|app",
      "revenue_included": { ... },            // 计入科目（打新/质押/销毁/协议费）
      "revenue_excluded": { ... },            // 明确不计入的科目 + 理由
      "growth_yoy_percent": null,             // 收入同比
      "source": { "type": "defillama|chain|official|estimate", "url": "..." }
    },
    "gross_profit": {                         // 毛利 = 收入 − LP 分润等直接成本
      "lp_share_cost_usd_365d": ...,
      "gross_profit_usd_365d": ...,
      "calculation_note": "..."
    },
    "token_emission_cost": {                  // 增发成本（SBC 类比）
      "usd_365d": ..., "annual_emission_tokens": ..., "inflation_rate_percent": ...,
      "treatment": "cost|dilution_note|none",
      "calculation_note": "..."
    },
    "net_income": {                           // 净利 = 毛利 − 增发成本 − 运营成本
      "net_income_usd_365d": ..., "operating_cost_usd_365d": ..., "calculation_note": "..."
    },
    "margins": {                              // ★派生，禁止手写
      "gross_margin_percent": null, "net_margin_percent": null, "note": "..."
    }
  },
  "holder_returns": {                         // 股东回报（L3）
    "by_mechanism": [                         // 机制拆解 + 含金量
      { "mechanism": "auto_burn", "type": "destroy", "usd_365d": ..., "yield_percent": ... }
    ],
    "summary": {                              // ★汇总（与 all-protocols 一致性校验）
      "destroy_usd_365d": ..., "yield_usd_365d": ...,
      "destroy_yield_percent": ..., "yield_yield_percent": ...,
      "shareholder_returns_usd_365d": ..., "shareholder_yield_percent": ...
    }
  },
  "balance_sheet": {                          // L1 市场数据 + 简化资产负债
    "market_cap_usd": ..., "tvl_usd": ..., "treasury_usd": null, "debt_usd": null
  },
  "valuation": {                              // ★派生，禁止手写（P1 用 pe/ps/payout，P2 补 pb/ev）
    "pe": null, "ps": null, "pb": null, "ev_revenue": null, "payout_ratio": null
  },
  "verification": {                           // 验证状态
    "method": "...", "status": "verified|partial|estimated", "last_checked": "2026-08-02"
  }
}
```

## 三、实体分轨与收入构成

### 3.1 平台币（platform_token）—— 赋能即收入

| 科目 | revenue_included 键 | 数据源 |
|---|---|---|
| 打新（Launchpad/Launchpool） | `launchpad_launchpool_usd_365d` | aBNB APY 推算（含质押） |
| 质押奖励 | `staking_rewards_usd_365d` | aBNB APY（StakeHub 链上） |
| 销毁 | `burn_usd_365d` | 链上 0xdead（Auto-Burn + BEP-95） |

- 手续费（gas fee）→ `revenue_excluded.fees`，注明理由。
- **平台币收入 = 股东回报（赋能总额）**，两者重合是本框架的设计。

### 3.2 应用型（app）—— 协议费收入

| 科目 | revenue_included 键 | 数据源 |
|---|---|---|
| 协议费（协议归属部分） | `protocol_fees_usd_365d` | DefiLlama `dailyRevenue`（非 dailyFees） |

- 必须扣除 LP 分润：`gross_profit.lp_share_cost_usd_365d`。

### 3.3 含金量标注（展示用，非是否计入）

| type | 含义 | 例子 |
|---|---|---|
| `destroy` | 销毁型，真金白银回收 🟢 | Auto-Burn、BEP-95、Firepit |
| `yield` | 收益型，增发/生态资源支付 🟡 | 打新、质押（aBNB） |
| `dividend` | 分红型（fee 分配给 ve/staker） | veCRV、sPENDLE |
| `buyback` | 回购型（回购销毁或回购后分发） | Aave 回购、BGB 季度回购 |

## 四、派生规则（build-snapshot.py 内置，禁止 config 手写）

```
gross_margin_percent = gross_profit_usd_365d / revenue_usd_365d × 100   (收入为 0/null → null)
net_margin_percent   = net_income_usd_365d  / revenue_usd_365d × 100     (同上)
shareholder_yield_percent = shareholder_returns_usd_365d / market_cap_usd × 100
pe    = market_cap_usd / shareholder_returns_usd_365d   (股东回报口径；平台币 = ps 同值)
ps    = market_cap_usd / revenue_usd_365d
payout_ratio = shareholder_returns_usd_365d / net_income_usd_365d  (净利 ≤ 0 → null)
destroy_yield_percent  = destroy_usd_365d  / market_cap_usd × 100
yield_yield_percent    = yield_usd_365d    / market_cap_usd × 100
```

> 平台币口径（方案 A，Boss 拍板）：`ps == pe`（收入 = 股东回报），tooltip 标注「收入 = 赋能口径」。

## 五、校验项（validate.py 按此执行）

1. **结构校验**：对 `data/snapshots/*.json` 跑 JSON Schema（`docs/schema/financial-snapshot.schema.json`）。
2. **派生自洽**：重算 valuation/margins 与文件内数值比对，差异 > 0.5% → 报错。
3. **一致性**：snapshot 与 `data/all-protocols.json` 的 `shareholder_yield_percent`（旧 `tev_yield_percent`）数值一致。
4. **新鲜度**：`as_of` 距今天数 > 26h → 告警（防僵尸数据）。
5. **null 语义**：无数据必须为 `null`，出现编造的 `0`（且原数据源为空）→ 告警。

## 六、生成流程

```
data/protocols/<id>/config.json（机制/口径/源声明）
        │
        ▼
scripts/build-snapshot.py   ← 读 config + data/daily/<id>/latest.json + 派生计算
        │
        ▼
data/snapshots/<id>.json    ← 统一 schema 输出
        │
        ▼
scripts/sync-tev-data.js（消费 snapshot → all-protocols.json）
scripts/validate.py（一致性/新鲜度/派生自洽）
scripts/ai-self-check.py（AI 审计哨兵）
```
