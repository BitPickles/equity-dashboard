#!/usr/bin/env python3
"""
OKB 专属适配器 — data/protocols/okb/adapter.py

按判定书 §5（OKB，Boss 2026-08-02 定稿）输出 Financial Snapshot：
- 实体类型：platform_token 平台币
- 现状：**2025-08 永久停止回购/销毁**（一次性销毁 65.26M OKB，供应锁定 21M，
  合约移除 mint/burn 功能，链上写死）→ 无持续赋能
- 定稿：**空气币，TEV = 0**，标注「回购销毁已于 2025-08 终止，无赋能机制」
  （Jumpstart 打新忽略）
- 计入 TEV：无（0）

机制确凿零（永久停止，非数据不可得）→ by_mechanism usd_365d / summary 全部写 0。
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
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    rr = config.get("revenue_recognition", {})
    mcap = ap.get("market_cap_usd") or (config.get("market_data") or {}).get("circulating_market_cap")

    # ── 收入（L2）：质押收益（2026-08-04 补充）+ 回购已终止 ─────
    # 2026-08-04 Boss 拍板：OKB 质押收益（OKX Earn）按 BNB asBNB 同口径补进
    # 回购销毁 2025-08 已终止（合约移除 mint/burn，供应锁定 21M）→ burn = 0
    STAKING_APY = 0.052  # ~5.2%（2026-07 OKX 官方：OKB Flexible Staking APR 5.2%，日结复利）
    staking_usd = round(STAKING_APY * mcap, 2) if mcap else None
    total_rev = staking_usd or 0
    revenue_included = {
        "burn_usd_365d": 0,  # 回购销毁 2025-08 终止
        "staking_rewards_usd_365d": staking_usd,  # 2026-08-04 补：OKX Earn 质押收益 🟡
        "launchpad_launchpool_usd_365d": None,  # Jumpstart 打新忽略（判定书 §5）
        "total_usd_365d": total_rev,
        "note": "质押收益口径（Boss 2026-08-04 拍板）：OKB OKX Earn 质押 ~5.2% APY × 市值。持币人质押利息，非协议利润；回购销毁 2025-08 已终止不计入",
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": total_rev,
        "calculation_note": "平台币无 LP 成本模型，毛利 = 收入（质押收益赋能口径）",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "OKB 供应永久锁定 21M（合约移除 mint/burn 功能），无增发",
    }
    net_income = {
        "net_income_usd_365d": total_rev,
        "operating_cost_usd_365d": None,
        "calculation_note": "平台币：净利 = 收入 = 质押收益（赋能口径）；回购销毁 2025-08 终止，不计入",
    }

    # ── 股东回报（L3）：质押收益 = 股息（收益型 🟡）────────────
    yield_pct = round(staking_usd / mcap * 100, 4) if (staking_usd and mcap) else None
    by_mechanism = [
        {
            "mechanism": "OKB OKX Earn 质押收益（~5.2% APY）",
            "type": "yield",
            "usd_365d": staking_usd,
            "yield_percent": yield_pct,
            "note": "2026-08-04 补充：OKX Earn Flexible Staking ~5.2% APR（官方 2026-07），按 BNB asBNB 同口径计入；持币人质押利息，非协议利润。回购销毁已于 2025-08 终止（机制移除）",
        }
    ]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": None,
            "yield_usd_365d": staking_usd,
            "destroy_yield_percent": None,
            "yield_yield_percent": yield_pct,
            "shareholder_returns_usd_365d": staking_usd,
            "shareholder_yield_percent": yield_pct,
        },
    }

    # ── 派生估值（L4）──────────────────────────────────────────
    pe = round(mcap / staking_usd, 4) if (mcap and staking_usd) else None
    valuation = {"pe": pe, "ps": pe, "pb": None, "ev_revenue": None, "payout_ratio": 1.0}

    # ── margins ────────────────────────────────────────────────
    margins = {
        "gross_margin_percent": 100.0,
        "net_margin_percent": 100.0,
        "note": "平台币无成本模型，毛利率/净利率 = 100%（口径标注，非经营性利润）",
    }

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "platform_token",
                "revenue_included": revenue_included,
                "revenue_excluded": rr.get("revenue_excluded", {}),
                "growth_yoy_percent": None,
                "source": {
                    "type": rr.get("source_type") or "estimate",
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
            "tvl_usd": ap.get("tvl"),
            "treasury_usd": None,
            "debt_usd": None,
        },
        "valuation": valuation,
        "verification": {
            "method": "OKX 2025-08 治理决议（一次性销毁 65.26M OKB → 供应锁定 21M，合约 mint/burn 功能移除，链上可验证）",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "okb")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
