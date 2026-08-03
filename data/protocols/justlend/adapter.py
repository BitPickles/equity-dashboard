#!/usr/bin/env python3
"""
JustLend 专属适配器 — data/protocols/justlend/adapter.py

按判定书（docs/protocol-revenue-recognition.md ### 18. JustLend）输出 Financial Snapshot：
- 实体类型：app（lending）
- 定稿：**TEV = 0**，标注「宣称 100% 净收入回购销毁，但链上核实为 pocket-to-pocket 做账式
  （孙宇晨金库 → executor → TRON Black Hole，无市场买入证据）」
- 链上事实（保留为供给侧记录，非 TEV 来源）：2025-10 / 2026-01 / 2026-04 / 2026-07 共 4 次 burn，
  累计 1,604,586,131 JST；全部来自孙宇晨生态中央金库 TFTWNgDBkQ5wQoP8RXpRznnHvAVV8x5jLu
- 判定：净收入照算（DefiLlama ~$500k/年 interest spread，estimate）；股东回报 = 0（做账式销毁不支撑价格）
- 数据源：链上（burn-history.json / tev-records.json）+ DefiLlama（interest spread）+ config.json

注意：by_mechanism 中 usd=0 表示「机制确凿为 0（做账式销毁非真市场 buyback）」，非数据缺失。
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


def build_snapshot(proto_dir):
    pid = Path(proto_dir).name
    config = _load(proto_dir / "config.json") or {}
    burn = _load(proto_dir / "burn-history.json") or {}
    tev_records = _load(proto_dir / "tev-records.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")
    validation = ap.get("validation", {})

    # ── 收入（L2）：净收入照算（DefiLlama interest spread ~$500k/年） ──
    revenue = 500_000
    revenue_included = {
        "protocol_fees_usd_365d": revenue,
        "total_usd_365d": revenue,
    }

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────
    # 借贷利差收入（无 LP 分润）→ 毛利 = 收入；无增发成本
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue,
        "calculation_note": "借贷利差（interest spread，DefiLlama ~$500k/年）→ 毛利 = 收入",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "JST 总供应固定（~8.8B，无持续增发）",
    }
    net_income = {
        "net_income_usd_365d": revenue,
        "operating_cost_usd_365d": None,
        "calculation_note": "净收入照算（判定书）；宣称 100% 净收入回购销毁，但链上核实为做账式 → 股东回报 = 0",
    }

    # ── 股东回报（L3）：TEV = 0（做账式销毁） ─────────────────
    by_mechanism = [{
        "mechanism": "宣称 100% 净收入回购销毁（链上核实做账式）",
        "type": "buyback",
        "usd_365d": 0,  # 确凿为 0（pocket-to-pocket 做账销毁，非真市场 buyback），非数据缺失
        "yield_percent": 0,
        "note": "链上核实为 pocket-to-pocket 做账式：孙宇晨金库 TFTWNgDBkQ5wQoP8RXpRznnHvAVV8x5jLu（持 HTX/WIN/TUSD 等）"
                "→ executor → TRON Black Hole，无 USDT 市场买入证据；销毁的 JST 本不在流通 → 对流通量和价格无实际支撑，"
                "TEV = 0；链上累计 burn 1,604,586,131 JST（2025-10/2026-01/2026-04/2026-07，burn-history.json）仅作供给侧记录",
    }]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": None,
            "yield_usd_365d": None,
            "destroy_yield_percent": None,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": 0,  # 确凿为 0（做账式销毁）
            "shareholder_yield_percent": 0,
        },
    }

    # ── margins / valuation（派生，validate 重算比对）────────
    gm = round(revenue / revenue * 100, 4) if revenue else None
    margins = {
        "gross_margin_percent": gm,
        "net_margin_percent": gm,
        "note": "借贷利差口径（无 LP 分润）→ 毛利率/净利率 = 100%；净收入照算但股东回报 = 0（做账式销毁不计入）",
    }

    pe = None  # 股东回报 0 → P/E 无意义
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = None  # 股东回报 0 → 派息率无意义
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "buyback_burn": {"note": "做账式销毁不计入股东回报（金库转 Black Hole，无市场买入证据）"},
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "estimate",
                    "url": "DefiLlama justlend slug interest spread（~$500k/年）+ 链上 burn-history.json（做账式核实）",
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
            "method": f"净收入照算（DefiLlama interest spread ~$500k/年）；链上核实（burn-history.json）：累计 burn "
                      f"{validation.get('total_burned_jst') or 1_604_586_131} JST（{validation.get('burn_events') or 4} 次）"
                      f"全部来自孙宇晨金库 TFTWNgDBkQ5wQoP8RXpRznnHvAVV8x5jLu，无 USDT 市场买入证据 → TEV = 0",
            "status": "estimated",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "justlend")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
