#!/usr/bin/env python3
"""
Kamino 专属适配器 — data/protocols/kamino/adapter.py

按判定书 §19-25（第 6 批治理代币统一口径，Boss 2026-08-02 定稿）输出 Financial Snapshot：
- 实体类型：app（lending）
- 只统计利润：收入（DefiLlama dailyRevenue，协议净收入）→ 毛利（扣 LP/成本）→ 净利照算并展示
- 股东回报 = 0（不回购）：by_mechanism usd_365d 写 0，note 标注「治理代币，无股东回报」
- 不回购的钱进国库/支出 → 留存行标注去向
- KMNO staking 是 farming reward boost（奖励来自代币国库排放），非协议 fee 分润

数据源：all-protocols.json（DefiLlama dailyRevenue 365d + 市值/TVL，2026-08 已验证）。
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
    pid = Path(proto_dir).name  # "kamino"
    config = _load(proto_dir / "config.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    rr = config.get("revenue_recognition", {})
    metrics = ap.get("metrics", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）：DefiLlama dailyRevenue（协议净收入）──
    revenue = metrics.get("trailing_365d_revenue_usd")

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue,
        "calculation_note": "DefiLlama dailyRevenue 为协议净收入口径（借贷 fees 给 LP 部分已在数据源扣减），毛利 = 收入",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "KMNO 季度 100M 排放（Season 奖励，来自代币国库）为无对价稀释，按判定书不扣成本（不做增发成本）",
    }
    net_income = {
        "net_income_usd_365d": revenue,
        "operating_cost_usd_365d": None,
        "calculation_note": "净利 = 收入 − 增发(0，稀释注记) − 运营成本(数据不可得)；净利留存协议，股东回报 = 0（治理代币）",
    }

    # ── 股东回报（L3）：机制确凿为 0 ───────────────────────────
    by_mechanism = [
        {
            "mechanism": "治理代币（无股东回报）",
            "type": "yield",
            "usd_365d": 0,  # 机制确凿为 0（不回购），非数据缺失
            "yield_percent": 0,
            "verified": "estimated",
            "note": "治理代币，无股东回报（不回购/不分红/不销毁）；KMNO staking 是 farming reward boost（奖励来自代币国库排放），非协议 fee 分润",
        }
    ]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": None,  # 无销毁
            "yield_usd_365d": None,    # 无收益型机制
            "destroy_yield_percent": None,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": 0,  # 确凿为 0
            "shareholder_yield_percent": 0,
        },
    }

    # ── 派生估值 / 利润率 ──────────────────────────────────────
    pe = None  # 股东回报为 0 → P/E 无意义，null
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = None
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
                    "staking_boost_rewards": {
                        "note": "KMNO staking 提供 farming boost（起始 3% 每天 +0.1%），奖励来自代币国库排放（季度 100M），非协议 fee 分润，不计入股东回报"
                    },
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": rr.get("source_type") or "defillama",
                    "url": rr.get("source_url"),
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
            "method": f"净利 = DefiLlama dailyRevenue 365d ${revenue:,.0f}（协议净收入）；"
                      f"KMNO 治理代币不回购（staking 为 farming boost 非分润）；净利留存协议",
            "status": "estimated",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "kamino")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
