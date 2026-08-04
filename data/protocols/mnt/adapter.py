#!/usr/bin/env python3
"""
MNT 专属适配器 — data/protocols/mnt/adapter.py

按判定书 §2（MNT，Boss 2026-08-02 定稿，选 B + 2026-08-04 补充质押收益）输出 Financial Snapshot：
- 实体类型：platform_token（L2 链代币，交易所生态孵化，统称平台币）
- 收入口径同 BNB（赋能即收入）
- **2026-08-04 更新（Boss 拍板）**：MNT 原生质押已上线（stacky.fi 实测 ~5.0% APY，
  30% 供应质押 ≈ $647M），按 BNB asBNB 同口径补进收入（staking_usd = APY × 市值）
- 口径标注：质押收益 = 持币人质押利息（非协议利润），详情页注记
- 不计入：sequencer fees（进 BaseFeeVault 不 burn）、mETH 收益（归 mETH 持有人）
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

    # ── 收入（L2）：质押收益（2026-08-04 补充）────────────────────
    # MNT 原生质押已上线：stacky.fi 2026 实测 ~5.0% APY（30% 供应质押 ≈ $647M）
    # 按 BNB asBNB 同口径：staking_usd = APY × 市值
    STAKING_APY = 0.05  # ~5.0%（2026-08-04 stacky.fi / stakingcrypto.info 实测）
    staking_usd = round(STAKING_APY * mcap, 2) if mcap else None
    total_rev = staking_usd or 0

    revenue_included = {
        "burn_usd_365d": 0,
        "staking_rewards_usd_365d": staking_usd,  # 2026-08-04 补：原生质押收益 🟡
        "launchpad_launchpool_usd_365d": None,
        "total_usd_365d": total_rev,
        "note": "质押收益口径（Boss 2026-08-04 拍板）：MNT 原生质押 ~5.0% APY × 市值。持币人质押利息，非协议利润；sequencer fees/mETH 不计入",
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
        "calculation_note": "MNT 供应未锁定（总供应 62.2 亿 vs 流通 32.5 亿，潜在稀释）；质押收益为赋能口径，不涉及增发成本扣减",
    }
    net_income = {
        "net_income_usd_365d": total_rev,
        "operating_cost_usd_365d": None,
        "calculation_note": "平台币：净利 = 收入 = 质押收益（赋能口径，无成本模型）",
    }

    # ── 股东回报（L3）：质押收益 = 股息（收益型 🟡）────────────
    yield_pct = round(staking_usd / mcap * 100, 4) if (staking_usd and mcap) else None
    by_mechanism = [
        {
            "mechanism": "MNT 原生质押收益（~5.0% APY）",
            "type": "yield",
            "usd_365d": staking_usd,
            "yield_percent": yield_pct,
            "note": "2026-08-04 补充：MNT 原生质押已上线（stacky.fi 实测 ~5.0% APY，30% 供应质押），按 BNB asBNB 同口径计入；持币人质押利息，非协议利润",
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
            "method": "质押收益口径（2026-08-04 Boss 拍板）：stacky.fi/stakingcrypto.info 实测 ~5.0% APY × 市值；sequencer fees/mETH 不计入（判定书 §2）",
            "status": "estimated",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "mnt")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
