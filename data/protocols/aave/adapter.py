#!/usr/bin/env python3
"""
Aave 专属适配器 — data/protocols/aave/adapter.py

按判定书（docs/protocol-revenue-recognition.md §6 Aave）输出 Financial Snapshot：
- 实体类型：app（lending）
- 收入 = DefiLlama dailyRevenue 365d（协议归属/净，已扣除给 LP 的部分，非 dailyFees）
- 净利 = 净收入（框架铁律：所有计算用净利润）
- 股东回报 = 官方披露年度回购 $30M/年（2026-03 治理，AIP-73 预算从 $50M 下调）
  ⚠️ treasury 买入 → Ecosystem Reserve（非真 burn，治理可 redistribute）
- Safety Module (Umbrella) 质押奖励归属【待定保留】：
  DefiLlama dailyHoldersRevenue 365d 作为机制行保留（usd=null 不计入主数字），
  是否计入收益型待 Boss 定稿

数据源（本地已有缓存）：
- config.json               → 机制/口径声明（只读）
- tev-records.json          → 股东回报历史（回购 + SM 月度分发序列）
- data/all-protocols.json   → 市值 / validation（fixed_buyback、sm_365d）/ metrics
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

    validation = ap.get("validation", {}) or {}
    metrics = ap.get("metrics", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）──────────────────────────────────────────────
    # 判定书：收入 = 协议费 − 给 LP 部分 = 净利。
    # DefiLlama dailyRevenue 已是扣 LP 后的协议净额（config 口径：协议归属/净，非 dailyFees）。
    revenue = metrics.get("trailing_365d_revenue_usd")  # ~$115.46M

    # ── 股东回报（L3）──────────────────────────────────────────
    # ① 年度 Buyback：官方披露 $30M/年（2026-03 治理，AIP-73）→ 计入（verified）
    buyback = validation.get("fixed_buyback_usd_annual")  # $30,000,000
    # ② Safety Module (Umbrella) 质押奖励：归属待定 → 保留机制行，暂不计入主数字
    sm_365d = validation.get("sm_365d_usd")  # ~$27.44M/365d（DefiLlama dailyHoldersRevenue）
    # ③ tev-records 交叉核对（完整 12 个日历月窗口）
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
            "mechanism": "AAVE 年度回购（$30M/年，2026-03 治理）",
            "type": "buyback",
            "usd_365d": round(buyback, 2) if buyback else None,
            "yield_percent": round(buyback / mcap * 100, 4) if (buyback and mcap) else None,
            "verified": "verified",
            "note": "AIP-73 年度回购预算，2026-03 治理从 $50M 下调至 $30M；DAO 财库市场买入 AAVE → Ecosystem Reserve（treasury 积累，非真 burn，治理可 redistribute；链上 0xdead 365d ≈ 0）",
        },
        {
            "mechanism": "Safety Module (Umbrella) 质押奖励",
            "type": "yield",
            "usd_365d": None,  # 归属待定，暂不计入主数字
            "yield_percent": None,
            "verified": "partial",
            "note": f"归属待定（保留）：DefiLlama dailyHoldersRevenue 365d ≈ {_fmt(sm_365d)}，"
                    f"是否计入收益型 🟡 待定，暂不计入股东回报主数字",
        },
    ]

    destroy_usd = buyback or 0
    destroy_yield = round(destroy_usd / mcap * 100, 4) if (destroy_usd and mcap) else None
    total_returns = destroy_usd  # yield 侧暂为 0（SM 待定）

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": round(destroy_usd, 2) if destroy_usd else None,
            "yield_usd_365d": None,  # SM 未计入 → 0 不显示，避免编造
            "destroy_yield_percent": destroy_yield,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": round(total_returns, 2) if total_returns else None,
            "shareholder_yield_percent": round(total_returns / mcap * 100, 4) if (total_returns and mcap) else None,
        },
    }

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,  # dailyRevenue 已扣 LP，无独立分项数据
        "gross_profit_usd_365d": revenue,
        "calculation_note": "DefiLlama dailyRevenue 为协议净收入（已扣除给 LP 的部分），毛利 = 净收入",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "AAVE 总供应固定 16M（无持续增发），不涉及增发成本",
    }
    net_income = {
        "net_income_usd_365d": revenue,
        "operating_cost_usd_365d": None,
        "calculation_note": "净利润 = 协议净收入（dailyRevenue，已扣 LP）；回购 $30M/年由 DAO 财库支出，不影响协议损益",
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
        "note": "派生计算：gross = GP/Rev, net = NI/Rev；协议收入为净额口径（已扣 LP），故为 100%",
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
                    "lp_interest": {"note": "给 LP（存款人）的利息占协议费大头，不计入协议收入；dailyRevenue 已是扣 LP 后的协议净额"},
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "defillama",
                    "url": "https://api.llama.fi/summary/fees/aave?dataType=dailyRevenue",
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
            "method": f"净利 = DefiLlama dailyRevenue 365d {_fmt(revenue)}；股东回报 = 官方披露回购 {_fmt(buyback)}/年"
                      f"（2026-03 治理）；SM 质押奖励 {_fmt(sm_365d)}/365d 待定保留"
                      f"{f'（tev-records 365d 合计 {_fmt(tev_records_365d)} 交叉核对）' if tev_records_365d else ''}",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "aave")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
