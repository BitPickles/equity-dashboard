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

    # ── 收入（L2）：2025-08 永久停止回购/销毁 → 0 ──────────────
    total_rev = 0  # 空气币：无持续赋能（合约 mint/burn 已移除，供应锁定 21M）
    revenue_included = {
        "burn_usd_365d": 0,
        "staking_rewards_usd_365d": None,
        "launchpad_launchpool_usd_365d": None,  # Jumpstart 打新忽略（判定书 §5）
        "total_usd_365d": total_rev,
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": total_rev,
        "calculation_note": "回购销毁已于 2025-08 终止，无赋能机制，毛利 = 收入 = 0",
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
        "calculation_note": "空气币：2025-08 永久停止回购/销毁，净利 = 0",
    }

    # ── 股东回报（L3）：机制确凿零（永久停止）→ summary = 0 ────
    by_mechanism = [
        {
            "mechanism": "回购销毁（已终止）",
            "type": "buyback",
            "usd_365d": 0,
            "yield_percent": 0,
            "note": "判定书 §5：回购销毁已于 2025-08 终止，无赋能机制（2025-08-13 一次性销毁 65.26M OKB 后供应锁定 21M，合约移除 mint/burn）",
        }
    ]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": 0,
            "yield_usd_365d": 0,
            "destroy_yield_percent": 0,
            "yield_yield_percent": 0,
            "shareholder_returns_usd_365d": 0,
            "shareholder_yield_percent": 0,
        },
    }

    # ── 派生估值（L4）：收入/回报为 0 → null ──────────────────
    valuation = {"pe": None, "ps": None, "pb": None, "ev_revenue": None, "payout_ratio": None}

    # ── margins：收入为 0 → null ──────────────────────────────
    margins = {
        "gross_margin_percent": None,
        "net_margin_percent": None,
        "note": "收入为 0（回购销毁已终止），毛利率/净利率无意义（null）",
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
