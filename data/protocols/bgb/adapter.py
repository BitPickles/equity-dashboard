#!/usr/bin/env python3
"""
BGB 专属适配器 — data/protocols/bgb/adapter.py

按判定书 §4（BGB，Boss 2026-08-02 定稿）输出 Financial Snapshot：
- 实体类型：platform_token（平台币，已与 Bitget 平台切割，赋能即收入）
- 收入 = 季度回购销毁（交易所+钱包业务利润 20%，季度执行、次季初完成）
- 不计入：打新（Boss 确认 Bitget 基本没有打新）
- 股东回报 = 季度回购销毁（按官方公告）；回报率 ≈ 年回购额 / 市值

数据源（判定书 §4，2026-08-02 定稿）：
- 官方季度公告：2025 Q1/Q2 各销毁 ≈3000 万枚（$1.2-1.4 亿/季度），取中值 $1.3 亿/季度年化
- 链上销毁地址复核（0x19de...828a28 → 0x000...000 零地址）
- config.json → market_data / revenue_recognition
- all-protocols.json → 市值

注意：2026 最新季度销毁额以官方公告为准（判定书：2026 Q2 交易量更高，
此口径保守采用 2025 官方公告数据年化，M0 阶段以本地已验证缓存组装）。
"""

import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # tev-dashboard/

# 官方公告已验证数据（判定书 §4 BGB）：2025 Q1/Q2 各销毁 ≈3000 万枚，$1.2-1.4 亿/季度
QUARTERLY_BURN_USD_LOW = 120_000_000
QUARTERLY_BURN_USD_HIGH = 140_000_000
QUARTERS_PER_YEAR = 4


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

    # ── 收入（L2）：季度回购销毁年化（官方公告中值 × 4） ────────────
    quarterly_usd = round((QUARTERLY_BURN_USD_LOW + QUARTERLY_BURN_USD_HIGH) / 2, 2)
    burn_usd = round(quarterly_usd * QUARTERS_PER_YEAR, 2)  # $520M/年
    total_rev = burn_usd

    revenue_included = {
        "burn_usd_365d": burn_usd,
        "staking_rewards_usd_365d": None,  # 无质押/打新合并科目（BGB 无 aBNB 类产品）
        "launchpad_launchpool_usd_365d": None,  # 打新不计入（判定书 §4）
        "total_usd_365d": total_rev,
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": total_rev,
        "calculation_note": "平台币无 LP 分润成本，毛利 = 收入（季度回购销毁年化）",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "BGB 无持续增发（2024-12 一次性销毁 8 亿后总供应 12 亿，100% 全流通），不涉及增发成本",
    }
    net_income = {
        "net_income_usd_365d": total_rev,
        "operating_cost_usd_365d": None,
        "calculation_note": "平台币：净利 = 收入 = 股东回报（季度回购销毁口径，无成本模型）",
    }

    # ── 股东回报（L3） ─────────────────────────────────────────
    yield_pct = round(burn_usd / mcap * 100, 4) if (burn_usd and mcap) else None
    by_mechanism = [
        {
            "mechanism": "季度回购销毁（利润 20%）",
            "type": "buyback",
            "usd_365d": burn_usd,
            "yield_percent": yield_pct,
            "note": "交易所+钱包业务利润 20% 回购销毁，次季初完成，官方公告 + 链上记录；2025 Q1/Q2 各销毁 ~3000 万枚（$1.2-1.4 亿/季度），年化取中值",
        }
    ]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": burn_usd,
            "yield_usd_365d": None,
            "destroy_yield_percent": yield_pct,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": burn_usd,
            "shareholder_yield_percent": yield_pct,
        },
    }

    # ── 派生估值（L4）──────────────────────────────────────────
    pe = round(mcap / total_rev, 4) if (mcap and total_rev) else None
    # 平台币口径（方案 A）：P/S = P/E = 1/股东回报率
    valuation = {"pe": pe, "ps": pe, "pb": None, "ev_revenue": None, "payout_ratio": None}
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
                "revenue_excluded": rr.get("revenue_excluded", {}),
                "growth_yoy_percent": None,
                "source": {
                    "type": "official",
                    "url": "https://www.bitget.com/bgb",
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
            "method": "官方季度公告（2025 Q1/Q2 各销毁 ~3000 万枚 / $1.2-1.4 亿季度）年化 + 链上销毁地址 0x000...000 复核",
            "status": "partial",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "bgb")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
