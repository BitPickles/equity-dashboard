#!/usr/bin/env python3
"""
MNT 专属适配器 — data/protocols/mnt/adapter.py

按判定书 §2（MNT，Boss 2026-08-02 定稿，选 B）输出 Financial Snapshot：
- 实体类型：platform_token（L2 链代币，交易所生态孵化，统称平台币）
- 收入口径同 BNB（赋能即收入），但**当前无赋能机制**
  （sequencer fees 进 BaseFeeVault 不 burn 给 MNT、mETH 收益归 mETH 持有人、Staking planned）
- 展示：收入显示 0% + 标注「当前无赋能机制，治理代币」（选 B：时间性状态，非本质无 TEV）
- 将来：MNT Staking 上线后按质押收益 🟡 补进收入

机制确凿零（非数据不可得）→ by_mechanism usd_365d / summary 全部写 0。
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

    # ── 收入（L2）：当前无赋能机制 → 0 ─────────────────────────
    total_rev = 0  # 机制确凿零：sequencer fees 不 burn、mETH 收益独立、Staking 未上线
    revenue_included = {
        "burn_usd_365d": 0,
        "staking_rewards_usd_365d": None,  # Staking 未上线（planned），上线后按质押收益 🟡 补进
        "launchpad_launchpool_usd_365d": None,
        "total_usd_365d": total_rev,
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": total_rev,
        "calculation_note": "当前无赋能机制（治理代币），毛利 = 收入 = 0",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "MNT 供应未锁定（总供应 62.2 亿 vs 流通 32.5 亿，潜在稀释）；当前无收入模型，不涉及增发成本扣减",
    }
    net_income = {
        "net_income_usd_365d": total_rev,
        "operating_cost_usd_365d": None,
        "calculation_note": "当前无赋能机制，净利 = 0；Staking 上线后按质押收益 🟡 补进收入",
    }

    # ── 股东回报（L3）：机制确凿零 → summary = 0 ──────────────
    by_mechanism = [
        {
            "mechanism": "无赋能机制（治理代币）",
            "type": "yield",
            "usd_365d": 0,
            "yield_percent": 0,
            "note": "判定书 §2：当前无赋能机制，治理代币（sequencer fees 进 BaseFeeVault 不 burn、mETH 收益归 mETH 持有人、Staking planned 将来补）",
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
        "note": "收入为 0（当前无赋能机制），毛利率/净利率无意义（null）",
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
            "method": "机制判定：L2 sequencer fees 进 BaseFeeVault 不 burn、mETH 收益独立、Treasury Burn 提案未执行、Staking planned（判定书 §2）",
            "status": "partial",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "mnt")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
