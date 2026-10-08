#!/usr/bin/env python3
"""
Aave 专属适配器 — data/protocols/aave/adapter.py

按判定书（docs/protocol-revenue-recognition.md §6 Aave）输出 Financial Snapshot：
- 实体类型：app（lending）
- 收入 = DefiLlama dailyRevenue 365d（协议归属/净，已扣除给 LP/存款人的部分，非 dailyFees）
- 股东回报口径（Boss 2026-10-08 定稿 D1）：
    ★ 回购自 2026-04-19 起暂停 → **已实现股东回报计 0**，并标注 status=paused
    ★ **不得**把 $30M/年"年度预算"当作已实现回报（预算 ≠ 执行；且完整预算载荷链未锁定）
    ★ 纠正旧稿错误：DefiLlama dailyHoldersRevenue **不是** "Safety Module 质押奖励"，
      其定义为 "buy back AAVE tokens using Aave Treasury after 9 April 2025"（回购收币代理）
      —— 旧稿把它当 SM 奖励，且另加 $30M 固定回购，存在**重复计算回购**风险
    ★ 回购为 treasury 累积（买入 AAVE → Ecosystem Reserve，治理可 redistribute），**非真 burn**

数据源：
- data/all-protocols.json → metrics.trailing_365d_revenue_usd / trailing_365d_holders_revenue_usd
  （由 scripts/sync-holders-revenue.py 每日从 DefiLlama 刷新）
- tev-records.json → 股东回报月度历史
- config.json → 机制声明（只读）
"""
import json
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # tev-dashboard/

BUDGET_USD_ANNUAL = 30_000_000          # 2026-03 治理由 $50M 下调（预算，非已实现）
BUDGET_PRIOR_USD = 50_000_000           # 早期文档口径
BUYBACK_PAUSED_SINCE = "2026-04-19"
BUYBACK_SAFE = "0x22740deBa78d5a0c24C58C740e3715ec29de1bFa"   # DefiLlama 回购收币地址
DL_HOLDERS_DEF = ('DefiLlama holdersRevenue = "buy back AAVE tokens using Aave Treasury '
                  'after 9 April 2025"（回购收币代理，混合口径），不是 Safety Module 奖励')


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
    tev_records = _load(proto_dir / "tev-records.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    metrics = ap.get("metrics", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）：dailyRevenue 已是扣 LP（存款人）后的协议净额 ──
    revenue = metrics.get("trailing_365d_revenue_usd")

    # ── 股东回报（L3）：回购已暂停 → 已实现 = 0（D1）──────────────
    holders_365d_dl = (metrics.get("trailing_365d_holders_revenue_usd")
                       or metrics.get("trailing_365d_shareholder_returns_usd"))  # 历史参考
    holders_30d_dl = metrics.get("trailing_30d_holders_revenue_usd")
    realized_returns = 0.0   # 暂停期已实现股东回报 = 0（不把预算当已实现）

    tev_records_365d = None
    try:
        cutoff = (date.today() - timedelta(days=365)).strftime("%Y-%m") + "-01"
        recs = [r.get("amount_usd") for r in tev_records.get("records", [])
                if r.get("date", "") >= cutoff and r.get("amount_usd")]
        tev_records_365d = sum(recs) if recs else None
    except Exception:  # noqa: BLE001
        tev_records_365d = None

    by_mechanism = [
        {
            "mechanism": f"AAVE 回购计划（预算 ${BUDGET_USD_ANNUAL/1e6:.0f}M/年，{BUYBACK_PAUSED_SINCE} 起暂停）",
            "type": "buyback",
            "usd_365d": 0,               # 已实现 = 0
            "yield_percent": 0,
            "status": "paused",
            "verified": "verified",
            "note": f"预算 ${BUDGET_USD_ANNUAL/1e6:.0f}M/年（2026-03 治理由 ${BUDGET_PRIOR_USD/1e6:.0f}M 下调，"
                    f"完整预算载荷链未锁定）。回购页面自 {BUYBACK_PAUSED_SINCE} 起 Paused，"
                    f"**已实现股东回报 = 0**（预算 ≠ 执行）。DAO 财库买入 AAVE → Ecosystem Reserve"
                    f"（treasury 累积，非真 burn，治理可 redistribute）。",
        },
        {
            "mechanism": "回购收币代理（DefiLlama holdersRevenue，混合口径）",
            "type": "buyback",
            "usd_365d": None,            # 不计入当前回报，仅历史参考
            "yield_percent": None,
            "verified": "partial",
            "note": f"{DL_HOLDERS_DEF}；收币地址 {BUYBACK_SAFE}。"
                    f"近 30/90 天 = 0，最后非零 2026-06-24；365d ≈ {_fmt(holders_365d_dl)} 仅作历史参考，"
                    f"不计入当前股东回报。",
        },
    ]

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": 0,
            "yield_usd_365d": None,      # Safety Module 归属仍待定，未计入 → 不显示（避免编造）
            "destroy_yield_percent": 0,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": realized_returns,
            "shareholder_yield_percent": 0,
            "status": "paused",
            "basis_note": f"回购 {BUYBACK_PAUSED_SINCE} 起暂停 → 已实现股东回报 = 0；"
                          f"预算 ${BUDGET_USD_ANNUAL/1e6:.0f}M/年不折算为收益率",
            "historical_reference": {
                "holders_revenue_365d_usd": round(holders_365d_dl, 2) if holders_365d_dl else None,
                "holders_revenue_30d_usd": round(holders_30d_dl, 2) if holders_30d_dl is not None else None,
                "last_nonzero_date": "2026-06-24",
                "note": "DefiLlama 回购收币代理（混合口径），仅供历史参考",
            },
        },
    }

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue,
        "calculation_note": "DefiLlama dailyRevenue 为协议净收入（已扣除给 LP/存款人的部分），毛利 = 净收入",
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
        "calculation_note": "净利润 = 协议净收入（dailyRevenue，已扣 LP）；回购若执行由 DAO 财库支出，不影响协议损益",
    }

    # ── 派生估值 / 利润率 ──────────────────────────────────────
    pe = round(mcap / realized_returns, 4) if (mcap and realized_returns) else None   # 回报为 0 → PE 不适用
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = round(realized_returns / revenue, 4) if (realized_returns and revenue and revenue > 0) else 0
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
                "revenue_included": {"protocol_fees_usd_365d": revenue, "total_usd_365d": revenue},
                "revenue_excluded": {
                    "lp_interest": {"note": "给 LP（存款人）的利息占协议费大头，不计入协议收入；dailyRevenue 已是扣 LP 后的协议净额"},
                },
                "growth_yoy_percent": None,
                "source": {"type": "defillama", "url": "https://api.llama.fi/summary/fees/aave?dataType=dailyRevenue"},
            },
            "gross_profit": gp,
            "token_emission_cost": emission,
            "net_income": net_income,
            "margins": margins,
        },
        "holder_returns": holder_returns,
        "balance_sheet": {"market_cap_usd": mcap, "tvl_usd": tvl, "treasury_usd": None, "debt_usd": None},
        "valuation": valuation,
        "verification": {
            "method": f"净利 = DefiLlama dailyRevenue 365d {_fmt(revenue)}；"
                      f"股东回报 = 0（回购 {BUYBACK_PAUSED_SINCE} 起暂停，预算 ${BUDGET_USD_ANNUAL/1e6:.0f}M 不计入）"
                      f"{f'（tev-records 365d 合计 {_fmt(tev_records_365d)} 交叉核对，历史参考）' if tev_records_365d else ''}",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "aave")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
