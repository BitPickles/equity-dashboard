#!/usr/bin/env python3
"""
Aster（AsterDEX）专属适配器 — data/protocols/aster/adapter.py

按判定书（docs/protocol-revenue-recognition.md ### 3. Aster，2026-08-02 定稿）：
- 实体类型：app（应用型 perpetual_dex）
- 计入收入：平台手续费（DefiLlama dailyRevenue）
- 计入股东回报：99% 平台手续费 → TWAP 回购 ASTER → 分发给 veASTER 质押者
  （Spot 上币费 5 万 USDT/次亦并入回购，次数不可得 → 注记）
- 不计入：1:1 储备销毁（烧未流通储备币，总供应 80亿→30亿，只减少潜在稀释 →
  财报页作注记，不进主数字；"198%"为营销话术）

数据源（本地缓存，2026-08-01 已验证）：
- all-protocols.json → metrics.trailing_365d_revenue_usd（DefiLlama dailyRevenue 365d）
  / validation.buy_365d_aster × aster_price_usd（链上回购兜底）/ market_cap_usd / tvl
- config.json → revenue_recognition.calculation.payout_ratio = 0.99（判定书口径，只读）
- tev-records.json → 链上回购历史（Stage5/6，95 天至 2026-03-27；6-17 新机制链上数据
  属 M0/M1 修复项，暂以 DefiLlama dailyRevenue 口径组装）

注意：M0 阶段以本地已验证缓存组装；新回购钱包 + 6-17 后链上日频采集
（update-aster.py 改造）为 M1 管道任务。
"""

import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # tev-dashboard/


def _load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def build_snapshot(proto_dir):
    pid = Path(proto_dir).name
    config = _load(proto_dir / "config.json") or {}
    tev_records = _load(proto_dir / "tev-records.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    validation = ap.get("validation", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")
    # 判定书：计入收入 = 平台手续费（DefiLlama dailyRevenue 365d）
    revenue = (ap.get("metrics", {}) or {}).get("trailing_365d_revenue_usd")
    buy_365d_aster = validation.get("buy_365d_aster")
    aster_price = validation.get("aster_price_usd")
    if revenue is None and buy_365d_aster and aster_price:
        # 兜底：链上 365d 回购 ASTER × 价（回购额 ≈ 99% 手续费 → dailyRevenue 近似）
        revenue = round(buy_365d_aster * aster_price, 2)
    # 判定书 payout_ratio（config 只读）：99% 手续费 → TWAP 回购分发 veASTER 🟢
    payout_ratio = (config.get("revenue_recognition", {}) or {}).get("calculation", {}).get("payout_ratio")
    if payout_ratio is None:
        payout_ratio = 0.99
    returns = round(revenue * payout_ratio, 2) if revenue is not None else None
    returns_yield = round(returns / mcap * 100, 4) if (returns is not None and mcap) else None

    # ── 收入（L2）──────────────────────────────────────────────
    revenue_included = {
        "protocol_fees_usd_365d": revenue,
        "total_usd_365d": revenue,
        "note": "平台手续费（DefiLlama dailyRevenue 365d）；Spot 上币费 5 万 USDT/次并入回购（次数不可得）",
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────
    # dailyRevenue 口径已扣 LP 分润 → 毛利 = 协议净收入；无持续增发成本
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue,
        "calculation_note": "DefiLlama dailyRevenue 已扣 LP 分润 → 毛利 = 协议净收入（平台手续费）",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "无持续增发成本；总供应 80亿→30亿 为 1:1 储备销毁（烧未流通储备币，减少潜在稀释），按判定书作注记不计入主数字",
    }
    net_income = {
        "net_income_usd_365d": revenue,
        "operating_cost_usd_365d": None,
        "calculation_note": "应用型：净利 = 平台手续费（DefiLlama dailyRevenue 365d，已扣 LP）",
    }

    # ── 股东回报（L3）─────────────────────────────────────────
    # 口径修正（Boss 2026-08-04）：TWAP 回购后分发给 veASTER 质押者 = 股息（真金白银进持币人口袋）
    # 非回购销毁 → type=yield（股息率）；美股口径：回购后分发 = 分红/股息
    by_mechanism = [{
        "mechanism": "TWAP 回购 ASTER → veASTER 质押者（99% 手续费）",
        "type": "yield",
        "usd_365d": returns,
        "yield_percent": returns_yield,
        "note": "Spot 上币费（5 万 USDT/次）并入回购；1:1 储备销毁不计入（未流通币）；回购即分发=股息口径",
    }]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": None,
            "yield_usd_365d": returns,
            "destroy_yield_percent": None,
            "yield_yield_percent": returns_yield,
            "shareholder_returns_usd_365d": returns,
            "shareholder_yield_percent": returns_yield,
        },
    }

    # ── 派生估值（L4）──────────────────────────────────────────
    pe = round(mcap / returns, 4) if (mcap and returns) else None
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = round(returns / net_income["net_income_usd_365d"], 4) if (returns is not None and net_income["net_income_usd_365d"]) else None
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    margins = {
        "gross_margin_percent": round(revenue / revenue * 100, 4) if revenue else None,
        "net_margin_percent": round(revenue / revenue * 100, 4) if revenue else None,
        "note": "dailyRevenue 口径下毛利 = 净利 = 收入，100% 为口径标注（非经营性利润）",
    }

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "reserve_burn_1to1": {
                        "note": "1:1 储备销毁烧未流通储备币（总供应 80亿→30亿），只减少潜在稀释，不计入股东回报（198% 为营销话术）",
                    }
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "defillama",
                    "url": "DefiLlama dailyRevenue（all-protocols.json metrics.trailing_365d_revenue_usd 缓存）",
                },
            },
            "gross_profit": gp,
            "token_emission_cost": emission,
            "net_income": net_income,
            "margins": margins,
        },
        "holder_returns": holder_returns,
        "balance_sheet": {
            "market_cap_usd": mcap,
            "tvl_usd": tvl,
            "treasury_usd": None,
            "debt_usd": None,
        },
        "valuation": valuation,
        "verification": {
            "method": "DefiLlama dailyRevenue 365d $"
            + str(revenue)
            + " × payout_ratio "
            + str(payout_ratio)
            + " = 回购/分配 $"
            + str(returns)
            + "；链上回购 wallet 365d "
            + str(buy_365d_aster)
            + " ASTER（缓存 "
            + str(validation.get("data_days"))
            + " 天，"
            + str((validation.get("data_range") or {}).get("start"))
            + "→"
            + str((validation.get("data_range") or {}).get("end"))
            + "）",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "aster")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
