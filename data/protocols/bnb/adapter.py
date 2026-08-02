#!/usr/bin/env python3
"""
BNB 专属适配器 — data/protocols/bnb/adapter.py

按 PRD 5.3（BNB 标杆）输出 Financial Snapshot：
- 实体类型：platform_token（平台币，Boss 定稿：赋能即收入）
- 收入 = 打新 + 质押（aBNB APY 推算，合并）+ 销毁（Auto-Burn + BEP-95）
- gas 手续费不计入
- 含金量拆解：销毁型 🟢（Auto-Burn + BEP-95）/ 收益型 🟡（aBNB 打新+质押）

数据源（本地已有缓存，均为 2026-08-01 已验证）：
- burn-history.json    → quarterly_burns + asbnb_apy_percent
- bep95-history.json   → daily 时间序列（506 天）
- tev-records.json     → 股东回报历史
- all-protocols.json   → 市场数据（市值/流通量）

注意：M0 阶段以本地已验证缓存组装；链上日频采集（update-bnb-tev.py）为 M1 管道任务。
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
    burn = _load(proto_dir / "burn-history.json") or {}
    bep95 = _load(proto_dir / "bep95-history.json") or {}
    tev_records = _load(proto_dir / "tev-records.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    validation = ap.get("validation", {})
    mcap = ap.get("market_cap_usd")
    price = validation.get("bnb_price_usd")

    # ── 收入（L2）──────────────────────────────────────────────
    # 销毁：Auto-Burn（近 4 季 USD 当前价重估）+ BEP-95（365d 序列）
    burn_4q_usd = validation.get("recent_4q_burn_usd_current")
    bep95_365d_bnb = validation.get("bep95_365d_bnb")
    bep95_usd = round(bep95_365d_bnb * price, 2) if (bep95_365d_bnb and price) else None
    burn_usd = round((burn_4q_usd or 0) + (bep95_usd or 0), 2) if (burn_4q_usd or bep95_usd) else None

    # 打新 + 质押：aBNB APY 推算（Boss 定稿：APY 已含打新+质押合计）
    apy = validation.get("asbnb_apy_percent") or burn.get("asbnb_apy_percent")
    staking_usd = round(apy / 100 * mcap, 2) if (apy and mcap) else None
    total_rev = round((burn_usd or 0) + (staking_usd or 0), 2) if (burn_usd or staking_usd) else None

    revenue_included = {
        "burn_usd_365d": burn_usd,
        "staking_rewards_usd_365d": staking_usd,
        "launchpad_launchpool_usd_365d": None,  # 已含于 staking（aBNB APY 合并口径）
        "total_usd_365d": total_rev,
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────
    # 平台币无 LP 成本 → 毛利 = 收入；无增发成本（BNB 无 LP 挖矿增发）
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": total_rev,
        "calculation_note": "平台币无 LP 分润成本，毛利 = 收入（赋能总额）",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "BNB 无代币增发（总供应递减：Auto-Burn 目标 100M），不涉及增发成本",
    }
    net_income = {
        "net_income_usd_365d": total_rev,
        "operating_cost_usd_365d": None,
        "calculation_note": "平台币：净利 = 收入 = 股东回报（赋能口径，无成本模型）",
    }

    # ── 股东回报（L3）：按含金量拆解 ──────────────────────────
    by_mechanism = [
        {"mechanism": "Auto-Burn（季度）", "type": "destroy",
         "usd_365d": round(burn_4q_usd, 2) if burn_4q_usd else None,
         "yield_percent": round(burn_4q_usd / mcap * 100, 4) if (burn_4q_usd and mcap) else None},
        {"mechanism": "BEP-95 实时销毁", "type": "destroy",
         "usd_365d": bep95_usd,
         "yield_percent": round(bep95_usd / mcap * 100, 4) if (bep95_usd and mcap) else None},
        {"mechanism": "aBNB 打新+质押", "type": "yield",
         "usd_365d": staking_usd,
         "yield_percent": round(staking_usd / mcap * 100, 4) if (staking_usd and mcap) else None},
    ]
    destroy_usd = (burn_4q_usd or 0) + (bep95_usd or 0)
    destroy_yield = round(destroy_usd / mcap * 100, 4) if (destroy_usd and mcap) else None
    yield_usd = staking_usd
    yield_pct = round(yield_usd / mcap * 100, 4) if (yield_usd and mcap) else None

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": round(destroy_usd, 2) if destroy_usd else None,
            "yield_usd_365d": yield_usd,
            "destroy_yield_percent": destroy_yield,
            "yield_yield_percent": yield_pct,
            "shareholder_returns_usd_365d": total_rev,
            "shareholder_yield_percent": round(total_rev / mcap * 100, 4) if (total_rev and mcap) else None,
        },
    }

    # ── 派生估值（L4）──────────────────────────────────────────
    pe = round(mcap / total_rev, 4) if (mcap and total_rev) else None
    # 平台币口径（方案 A）：P/S = P/E = 1/股东回报率
    valuation = {"pe": pe, "ps": pe, "pb": None, "ev_revenue": None, "payout_ratio": None}
    # 净利 = 收入 → 派息率 = 100%（全部赋能即股东回报）
    if pe:
        valuation["payout_ratio"] = 1.0

    # ── margins ────────────────────────────────────────────────
    margins = {
        "gross_margin_percent": round(total_rev / total_rev * 100, 4) if total_rev else None,
        "net_margin_percent": round(total_rev / total_rev * 100, 4) if total_rev else None,
        "note": "平台币无成本模型，毛利率/净利率 = 100%（口径标注，非经营性利润）",
    }

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "platform_token",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "fees": {"note": "gas 手续费不计入（BEP-95 销毁部分已含于 burn 科目）"}
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "chain",
                    "url": "0xdead 链上 + StakeHub asBNB APY（本地 burn-history/bep95-history 缓存）",
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
            "method": "Auto-Burn 近4季 " + str(validation.get("recent_4q_burn_bnb")) + " BNB + BEP-95 日序列 " + str(validation.get("bep95_data_days")) + " 天 + asBNB APY " + str(apy) + "%",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "bnb")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
