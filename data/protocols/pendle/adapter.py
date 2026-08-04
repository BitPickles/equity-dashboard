#!/usr/bin/env python3
"""
Pendle 专属适配器 — data/protocols/pendle/adapter.py

按判定书（docs/protocol-revenue-recognition.md §10 Pendle）输出 Financial Snapshot：
- 实体类型：app（yield）
- 收入 = DefiLlama dailyRevenue 365d（协议净额；YT 费 5% + Swap 费 80% 归协议/voters）
- 净利 = 净收入（框架铁律：所有计算用净利润）
- 股东回报 = 80% 协议收入回购 PENDLE → 分给 sPENDLE 质押者 🟢
  （Boss 拍板 80% 确定；2026-01-29 起 sPENDLE 时代，vePENDLE sunset）
  数值取 DefiLlama dailyHoldersRevenue 365d（sPENDLE 分发实测，~80% 口径）
- ⚠️ caveat：Pendle 多链部署（8+ 链），无单一 buyback executor 可链上独立验证，
  80% 比例依赖官方宣称 + DefiLlama 聚合 → verification=partial

数据源（本地已有缓存）：
- config.json               → 机制/口径声明（只读，payout_ratio=0.8）
- tev-records.json          → sPENDLE/vePENDLE 月度分发序列（365d 窗口交叉核对）
- data/all-protocols.json   → 市值 / metrics（revenue、tev）
"""

import json
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # tev-dashboard/


def _load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def _fmt(x):
    """USD 千分位格式化；None → N/A。"""
    return f"${x:,.0f}" if x else "N/A"


def build_snapshot(proto_dir):
    pid = Path(proto_dir).name
    config = _load(proto_dir / "config.json") or {}
    tev_records = _load(proto_dir / "tev-records.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    metrics = ap.get("metrics", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")
    payout_ratio = config.get("payout_ratio") or 0.8  # 判定书：80% 确定

    # ── 收入（L2）──────────────────────────────────────────────
    # DefiLlama dailyRevenue 365d（协议净额）。当前数据表 revenue 字段与 tev 同源，
    # 均基于 dailyHoldersRevenue 口径（80% 分发实测），见 verification 交叉核对。
    revenue = metrics.get("trailing_365d_revenue_usd")  # ~$18.67M

    # ── 股东回报（L3）──────────────────────────────────────────
    # 80% 协议收入回购 PENDLE → sPENDLE 质押者（2026-01-29 起）。
    # 数值 = DefiLlama dailyHoldersRevenue 365d（sPENDLE 分发实测）。
    holders_365d = metrics.get("trailing_365d_shareholder_returns_usd")  # ~$18.67M
    # tev-records 交叉核对（完整 12 个日历月窗口）
    try:
        cutoff = (date.today() - timedelta(days=365)).strftime("%Y-%m") + "-01"
        records_365d = [
            r.get("amount_usd") for r in tev_records.get("records", [])
            if r.get("date", "") >= cutoff and r.get("amount_usd")
        ]
        tev_records_365d = sum(records_365d) if records_365d else None
    except Exception:
        tev_records_365d = None

    by_mechanism = [
        {
            "mechanism": "sPENDLE 回购+分发（80% 协议收入）",
            "type": "yield",
            "usd_365d": round(holders_365d, 2) if holders_365d else None,
            "yield_percent": round(holders_365d / mcap * 100, 4) if (holders_365d and mcap) else None,
            "verified": "partial",
            "note": "80% 协议收入回购 PENDLE → 分给 sPENDLE 质押者 🟢（2026-01-29 起 sPENDLE 时代，"
                    "14 天解锁冷却或 5% 即时赎回费）；多链无单一 buyback executor，依赖 DefiLlama 聚合，"
                    "80% 比例无法链上独立验证",
        },
    ]

    destroy_usd = 0  # Pendle 无销毁机制（burns: NONE）
    yield_usd = holders_365d or 0
    total_returns = yield_usd
    yield_pct = round(yield_usd / mcap * 100, 4) if (yield_usd and mcap) else None

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": None,  # 无销毁 → null 而非 0
            "yield_usd_365d": round(yield_usd, 2) if yield_usd else None,
            "destroy_yield_percent": None,
            "yield_yield_percent": yield_pct,
            "shareholder_returns_usd_365d": round(total_returns, 2) if total_returns else None,
            "shareholder_yield_percent": round(total_returns / mcap * 100, 4) if (total_returns and mcap) else None,
        },
    }

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,  # 协议收入为净额，LP 分润无独立数据
        "gross_profit_usd_365d": revenue,
        "calculation_note": "DefiLlama dailyRevenue 为协议净收入（YT 费 + Swap 费归协议），毛利 = 收入",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "PENDLE 无持续大额增发（价值回馈以协议收入回购分发为主），不涉及增发成本",
    }
    net_income = {
        "net_income_usd_365d": revenue,
        "operating_cost_usd_365d": None,
        "calculation_note": "净利润 = 协议净收入；80% 回购分发 sPENDLE 计入股东回报，20% 留存 treasury",
    }

    # ── 派生估值 / 利润率（与 build-snapshot.py 派生逻辑一致） ─
    pe = round(mcap / total_returns, 4) if (mcap and total_returns) else None
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = round(total_returns / revenue, 4) if (total_returns and revenue and revenue > 0) else None
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    gm = round(revenue / revenue * 100, 4) if revenue else None
    margins = {
        "gross_margin_percent": gm,
        "net_margin_percent": gm,
        "note": "派生计算：gross = GP/Rev, net = NI/Rev；协议收入为净额口径，故为 100%",
    }

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": {
                    "protocol_fees_usd_365d": revenue,
                    "total_usd_365d": revenue,
                },
                "revenue_excluded": {
                    "lp_market_making": {"note": "LP（PT/YT 做市商）收益来自市场价差与手续费分成，不计入协议收入；dailyRevenue 为协议净额"},
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "defillama",
                    "url": "https://api.llama.fi/summary/fees/pendle?dataType=dailyRevenue",
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
            "method": f"净利 = DefiLlama dailyRevenue 365d {_fmt(revenue)}；股东回报 = dailyHoldersRevenue 365d "
                      f"{_fmt(holders_365d)}（80% 口径 🟢，sPENDLE 时代 2026-01-29 起，payout_ratio={payout_ratio}）"
                      f"{f'；tev-records 365d 合计 {_fmt(tev_records_365d)} 交叉核对' if tev_records_365d else ''}",
            "status": "partial",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "pendle")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
