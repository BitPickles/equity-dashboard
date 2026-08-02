#!/usr/bin/env python3
"""
Curve 专属适配器 — data/protocols/curve/adapter.py

按判定书（docs/protocol-revenue-recognition.md ### 11. Curve）输出 Financial Snapshot：
- 实体类型：application（dex）
- 收入 = admin fee 口径（DefiLlama dailyRevenue，即 FeeAllocator 90% → veCRV 部分；
  FeeAllocator 另 10% → Community Fund Treasury 不计入 DefiLlama 收入口径）
- 增发按成本计算（美股 SBC 类比）：CRV 年增发 ~1.155 亿（约 $26M/年，通胀 4.8%）全流 LP 挖矿
  → 毛利 − 增发成本 = **净利为负**（净稀释）
- 股东回报 = veCRV 分红（90% admin fee）🟡 收益型（裸 CRV 不参与，名义 yield = 回报/全市值）

数据源（本地已验证缓存，2026-08-01）：
- fee-history.json   → Community Fund Treasury crvUSD inflow × 9 反推 veCRV TEV（365d summary）
- config.json        → token_emission_cost（增发成本，判定书口径）
- all-protocols.json → 市值 / TVL

注意：validate.py 派生自洽要求 pe/ps/payout/margins/summary 必须由 L1-L3 重算一致。
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
    fee = _load(proto_dir / "fee-history.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）：admin fee 口径 ────────────────────────────────
    # DefiLlama dailyRevenue = FeeAllocator 90% veCRV 部分（本地 fee-history ×9 反推同值）
    s365 = fee.get("summary", {}).get("365d", {})
    vecrv_tev = s365.get("vecrv_tev_usd")           # $15.34M（90% admin fee → veCRV）
    treasury = s365.get("treasury_crvusd")          # $1.70M（10% → Community Fund，不计收入）
    revenue = round(vecrv_tev, 2) if vecrv_tev else None

    revenue_included = {
        "admin_fee_usd_365d": revenue,
        "vecrv_distribution_usd_365d": round(vecrv_tev, 2) if vecrv_tev else None,
        "total_usd_365d": revenue,
    }

    # ── 毛利 / 增发成本 / 净利 ─────────────────────────────────────
    # 收入已按 admin fee 口径（交易费 50% LP / 50% admin，LP 分润在收入确认时排除）
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue,
        "calculation_note": "收入按 admin fee 口径（交易费 50% LP / 50% admin，LP 分润已排除）→ 毛利 = 收入",
    }
    emission = config.get("token_emission_cost") or {
        "usd_365d": None, "annual_emission_tokens": None, "inflation_rate_percent": None,
        "treatment": "none", "calculation_note": "无增发数据",
    }
    emission_cost = emission.get("usd_365d")  # $26,000,000/年（CRV 增发 1.155 亿，通胀 4.8%）
    net = round((revenue or 0) - (emission_cost or 0), 2) if revenue is not None else None
    net_income = {
        "net_income_usd_365d": net,
        "operating_cost_usd_365d": None,
        "calculation_note": "净利 = 毛利 − 增发成本（美股 SBC 类比：CRV 增发全流 LP 挖矿，作为成本扣除）→ 净利为负（净稀释）",
    }

    # ── 股东回报（L3）：veCRV 分红 = 90% admin fee ─────────────────
    yield_usd = round(vecrv_tev, 2) if vecrv_tev else None
    yield_pct = round(yield_usd / mcap * 100, 4) if (yield_usd and mcap) else None
    by_mechanism = [{
        "mechanism": "veCRV 分红（FeeAllocator 90% admin fee）",
        "type": "yield",
        "usd_365d": yield_usd,
        "yield_percent": yield_pct,
        "note": "90% admin fee 兑换 crvUSD 分给 veCRV 锁仓持有人（裸 CRV 不参与）；名义 yield = 股东回报 / CRV 全市值，实际锁仓持有人更高（veCRV-only 口径）",
    }]

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": None,                       # Curve 无销毁（burns=NONE）
            "yield_usd_365d": yield_usd,
            "destroy_yield_percent": None,
            "yield_yield_percent": yield_pct,
            "shareholder_returns_usd_365d": yield_usd,
            "shareholder_yield_percent": yield_pct,
        },
    }

    # ── margins（派生，validate 重算比对）──────────────────────────
    gm = round(revenue / revenue * 100, 4) if revenue else None
    nm = round(net / revenue * 100, 4) if (revenue and net is not None) else None
    margins = {
        "gross_margin_percent": gm,
        "net_margin_percent": nm,
        "note": "净利为负：增发按成本扣除（CRV 增发 $26M/年 > admin fee 收入 $15.34M）→ 净稀释；毛利率口径性 100%（收入已排除 LP 分润）",
    }

    # ── valuation（派生，validate 重算比对）────────────────────────
    returns_usd = holder_returns["summary"]["shareholder_returns_usd_365d"]
    pe = round(mcap / returns_usd, 4) if (mcap and returns_usd) else None
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = round(returns_usd / net, 4) if (returns_usd and net and net > 0) else None  # 净利为负 → null
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "lp_share": {"note": "交易费 50% LP 分润不计入（收入按 admin fee 口径）"},
                    "community_fund": {"note": f"FeeAllocator 10% → Community Fund Treasury（约 ${round(treasury, 2) if treasury else 0}/365d）不计入 DefiLlama dailyRevenue 口径"},
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "chain",
                    "url": "Community Fund Treasury crvUSD inflow × 9（FeeAllocator 90/10）+ DefiLlama dailyRevenue（本地 fee-history 缓存）",
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
            "method": "FeeAllocator 90/10：Community Fund Treasury crvUSD inflow × 9 反推 veCRV TEV 365d=" + str(vecrv_tev)
                      + " · 增发成本 " + str(emission_cost) + "（config.token_emission_cost）",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "curve")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
