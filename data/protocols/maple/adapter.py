#!/usr/bin/env python3
"""
Maple 专属适配器 — data/protocols/maple/adapter.py

按判定书（docs/protocol-revenue-recognition.md ### 15. Maple）输出 Financial Snapshot：
- 实体类型：app（lending）
- 机制（MIP-021，2026-07-17 通过 99.97%）回购规则化阶梯：月收入 <$1.5M → 10%；$1.5-2M → 20%；>$2M → 30%
- 当前状态：月收入 ~$1.29M → 落在 **10% 档**（MIP-019/020 固定 25% SSF 已于 2026-Q2 结束）
- 判定：收入 → 毛利 → 净利 → 回购 10%（当前档）→ 留存 90%
- 股东回报 = 净利 × 10%（当前档，首次执行 2026-08）

数据源（本地已验证缓存 + 判定书）：
- config.json         → revenue_recognition（MIP-021 阶梯，payout_ratio 0.1）+ return_mechanisms
- tev-records.json    → DefiLlama dailyHoldersRevenue 月聚合（历史参考，MIP-019 口径）
- 判定书              → 当前月收入 ~$1.29M（maple.finance/transparency 官方仪表盘）
- all-protocols.json  → 市值 / TVL

注意：SSF 国库地址未公开、burn vs reserve 比例未披露 → verified: partial。
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


def _fmt(x):
    return f"${x:,.0f}" if x else "N/A"


def _mip021_ratio(monthly_revenue):
    """MIP-021 阶梯：月收入 <$1.5M → 10%；$1.5-2M → 20%；>$2M → 30%"""
    if monthly_revenue is None:
        return None, "数据不可得"
    if monthly_revenue < 1_500_000:
        return 0.10, f"月收入 {_fmt(monthly_revenue)} < $1.5M → 10% 档"
    if monthly_revenue <= 2_000_000:
        return 0.20, f"月收入 {_fmt(monthly_revenue)} ∈ [$1.5M, $2M] → 20% 档"
    return 0.30, f"月收入 {_fmt(monthly_revenue)} > $2M → 30% 档"


def build_snapshot(proto_dir):
    pid = Path(proto_dir).name
    config = _load(proto_dir / "config.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）──────────────────────────────────────────────
    # 判定书：当前月收入 ~$1.29M（maple.finance/transparency 官方仪表盘，2026-07）
    monthly_revenue = 1_290_000
    revenue = round(monthly_revenue * 12, 2)  # 年化 365d（当前月 × 12）
    revenue_included = {
        "protocol_fees_usd_365d": revenue,
        "total_usd_365d": revenue,
    }

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────
    # 机构借贷：收入 = 贷款利差（interest spread），无 LP 分润 → 毛利 = 收入
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue,
        "calculation_note": "机构借贷利差收入（无 LP 分润成本）→ 毛利 = 收入",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "SYRUP 总供应固定（~12.16B，2024 年由 MPL 迁移），无持续增发成本",
    }
    net_income = {
        "net_income_usd_365d": revenue,
        "operating_cost_usd_365d": None,
        "calculation_note": f"净利 = 收入（毛利 − 增发成本 0）→ 回购 {_fmt(revenue * 0.10)}（10% 档）→ 留存 {_fmt(revenue * 0.90)}",
    }

    # ── 股东回报（L3）：MIP-021 10% 档回购 ─────────────────────
    ratio, ratio_note = _mip021_ratio(monthly_revenue)
    returns_usd = round(revenue * ratio, 2) if (revenue and ratio) else None
    returns_pct = round(returns_usd / mcap * 100, 4) if (returns_usd and mcap) else None
    by_mechanism = [{
        "mechanism": "MIP-021 阶梯回购（SSF）",
        "type": "buyback",
        "usd_365d": returns_usd,
        "yield_percent": returns_pct,
        "note": f"{ratio_note}；MIP-021（2026-07-17 通过 99.97%）回购规则化，首次执行 2026-08；"
                f"MIP-019/020 固定 25% 已于 2026-Q2 结束；SSF 国库地址未公开、burn vs reserve 比例未披露 → partial",
    }]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": returns_usd,      # SSF 回购（含部分销毁），按 buyback 归入 destroy 组
            "yield_usd_365d": None,
            "destroy_yield_percent": returns_pct,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": returns_usd,
            "shareholder_yield_percent": returns_pct,
        },
    }

    # ── margins / valuation（派生，validate 重算比对）────────
    gm = round(revenue / revenue * 100, 4) if revenue else None
    margins = {
        "gross_margin_percent": gm,
        "net_margin_percent": gm,
        "note": "机构借贷利差口径（无 LP 分润）→ 毛利率/净利率 = 100%（口径标注）；净利留存 90%，回购 10%",
    }

    pe = round(mcap / returns_usd, 4) if (mcap and returns_usd) else None
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = round(returns_usd / revenue, 4) if (returns_usd and revenue) else None  # = 回购比例 10%
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "ssf_treasury_reserve": {"note": "回购金额中留作国库储备/流动性的部分非直接股东回报（比例未披露，partial）"},
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "official",
                    "url": "maple.finance/transparency 官方仪表盘（月收入 ~$1.29M）+ MIP-021 治理提案（2026-07-17）",
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
            "method": f"月收入 {_fmt(monthly_revenue)}（判定书/官方仪表盘）×12 = 年化收入 {_fmt(revenue)}；"
                      f"MIP-021 {ratio_note} → 回购 {_fmt(returns_usd)}（净利 × {ratio * 100:.0f}%）；留存 90%",
            "status": "partial",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "maple")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
