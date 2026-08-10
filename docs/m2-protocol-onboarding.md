# M2 协议接入手册（Agent 操作指南）

> **适用范围**：M2 Top 10 协议批量接入的并行 agent。
> **目标**：每个协议产出 `data/protocols/<id>/adapter.py`（专属适配器）+ 重新生成 `data/snapshots/<id>.json`。
> **铁律**：只碰自己的 `data/protocols/<id>/` 目录 + 自己的 snapshot；**禁止改共享文件**（build-snapshot.py / validate.py / protocol.html / 其他协议目录）。

## 一、协议分配与口径（判定书出处：docs/protocol-revenue-recognition.md）

| Agent | 协议 | 口径要点 |
|---|---|---|
| A1 | aave | 应用型(lending)：收入=协议费−给LP→净利；回购 $30M/年（官方披露，2026-03 治理）；Safety Module 待定保留 |
| A1 | pendle | 应用型(yield)：80% 协议收入回购 PENDLE → sPENDLE 质押者 🟢；sPENDLE 时代 2026-01-29 起 |
| A2 | hyperliquid | 应用型(perp)：手续费直接销毁 ≈ 回购 99% 🟢（销毁流通币=流向所有持币人） |
| A2 | gmx | 应用型(perp)：留存 27%，回购进国库不流通；**股东回报 = 0**，标注「锁定至 $90」 |
| A3 | sky | 应用型(cdp)：SBE 回购做市 + Elixir 真燃烧（销毁=股息 🟢）；留存国库要讲清「留存 vs 分配」 |
| A3 | uniswap | 应用型(dex)：收入=抽成手续费；Firepit 销毁=回购 🟢（fee switch 2025-12-28 开启）；链上 0xdead/Firepit |
| A4 | curve | 应用型：**净利为负**（增发按成本）；销毁+增发成本 |
| A4 | dydx | 应用型(perp)：收入=净协议费（含 affiliate/rebate 前，不可精确复算）；回购=买入后质押**非销毁**；质押奖励 ~0.01% |
| A5 | aster | 应用型(perp_dex)：99% 手续费 → TWAP 回购分发 veASTER 🟢；1:1 储备销毁不进主数字（注记） |
| A5 | ~~etherfi~~ | ❌ 已删除（2026-08-04）：协议收入数据不可得，主表 Rev/Net 缺失，Boss 决定移除 |

## 二、产出物

每个协议 `<id>` 在 `data/protocols/<id>/` 下：

1. **adapter.py** —— 复制 `data/protocols/bnb/adapter.py` 为模板改写：
   - 读 config.json（机制/口径声明，**已存在，不要重写**，只读）
   - 读本地数据：`<id>/tev-records.json`（股东回报历史）、`data/all-protocols.json`（市值/流通量/validation）、可能的数据文件（fee-history.json / burn-history.json / buyback-history.json）
   - 输出 Financial Snapshot dict（结构与 BNB 一致：income_statement / holder_returns / balance_sheet / valuation）
   - `build_snapshot(proto_dir)` 函数签名必须与 BNB 一致
2. **重新生成 snapshot**：不要自己写文件！在 `scripts/` 目录跑 `build-snapshot.py --protocol <id>`（只影响自己）确认输出。

## 三、Financial Snapshot 结构（必须与 BNB 一致）

```jsonc
{
  "protocol": "<id>",
  "as_of": "2026-08-03",
  "income_statement": {
    "revenue": { "entity_type": "application", "revenue_included": {...}, "revenue_excluded": {...}, "growth_yoy_percent": null, "source": {...} },
    "gross_profit": { "lp_share_cost_usd_365d": ..., "gross_profit_usd_365d": ..., "calculation_note": ... },
    "token_emission_cost": { "usd_365d": ..., "annual_emission_tokens": ..., "inflation_rate_percent": ..., "treatment": "none|cost|dilution_note", "calculation_note": ... },
    "net_income": { "net_income_usd_365d": ..., "operating_cost_usd_365d": null, "calculation_note": ... },
    "margins": { "gross_margin_percent": ..., "net_margin_percent": ..., "note": ... }
  },
  "holder_returns": {
    "by_mechanism": [ { "type": "buyback|buyback_burn|staking_reward|fee_sharing|ve_distribution|airdrop|aggregate|burn|direct_distribution", "label": "...", "usd_365d": ..., "note": "...", "verified": "verified|partial|estimated" } ],
    "summary": { "destroy_usd_365d": ..., "yield_usd_365d": ..., "destroy_yield_percent": ..., "yield_yield_percent": ..., "shareholder_returns_usd_365d": ..., "shareholder_yield_percent": ... }
  },
  "balance_sheet": { "market_cap_usd": ..., "tvl_usd": ..., "treasury_usd": null, "debt_usd": null },
  "valuation": { "pe": ..., "ps": ..., "pb": null, ... }
}
```

### 计算口径铁律（PRD 3.3 + 判定书）
1. **所有计算用净利润**（收入 → 扣 LP/成本 → 净利）
2. **只计流向流通持币人的价值流**
3. 增发成本配比原则：有对价换收入 → 成本扣减（如 Curve/Pancake）；无对价 → 稀释注记
4. `—`（null）而非 0：数据不可得时用 null

## 四、数据源优先级（CLAUDE.md 铁律）
链上 > 官方治理 > 估算 > DefiLlama

## 五、自检清单（交付前）
- [ ] `adapter.py` 语法正确（`python -m py_compile`）
- [ ] `build-snapshot.py --protocol <id>` 跑通，无报错
- [ ] snapshot 结构 keys 与 BNB 完全一致（可 diff）
- [ ] 数值与判定书口径一致（股东回报率 ~ 预期区间）
- [ ] 没有改任何共享文件或他人协议目录
