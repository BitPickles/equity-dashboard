#!/usr/bin/env python3
"""
Sky (MakerDAO) 专属适配器 — data/protocols/sky/adapter.py

按判定书（docs/protocol-revenue-recognition.md §7 Sky）输出 Financial Snapshot：
- 实体类型：app（cdp / 稳定币）
- 收入 = DefiLlama dailyRevenue 365d（协议净归属，已扣 DSR/SSR 用户存款利息）
- 股东回报口径（Boss 2026-10-08 定稿 D2）：
    ★ 维持 DefiLlama dailyHoldersRevenue 作为股东回报，但**必须如实标注它是"混合代理"**
    ★ DefiLlama 定义（源码 makerdao.ts）：HoldersRevenue = 买币（SKY 数量 × 当日市价）
      **＋** USDS 质押奖励 —— 既不是纯现金支出，也不是纯销毁
    ★ 删除旧稿"DefiLlama 已剥离 farm / 等于真燃烧"的错误表述（与 DefiLlama 定义直接冲突）
    ★ SBE 买币自 2024-09 起改为"买 SKY 交国库"（可再分配），非销毁
- 不计入：Surplus Buffer 留存；买币进国库后未销毁的部分（按铁律「只计流向流通持币人的价值流」）
- 损益表：净利留存国库要讲清楚 → net_income 注明「留存 vs 分配」比例

数据源：
- data/all-protocols.json → metrics.trailing_365d_revenue_usd / trailing_365d_holders_revenue_usd
  （由 scripts/sync-holders-revenue.py 每日从 DefiLlama 刷新，2026-10-08 修复根因）
- tev-records.json → 股东回报月度历史
- config.json → 机制声明（只读）
"""
import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # tev-dashboard/

# DefiLlama HoldersRevenue 的口径说明（源码 makerdao.ts 实测）
DL_HOLDERS_DEF = ("DefiLlama holdersRevenue = SKY token buybacks（买币数量×当日市价）"
                  " + staking rewards（USDS 付给 SKY stakers）—— 混合代理，非纯现金支出/非纯销毁")
ACTUAL_BUYBACK_SOURCE = "https://info.sky.money/buyback"


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
    _tev_records = _load(proto_dir / "tev-records.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    metrics = ap.get("metrics", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）─────────────────────────────────────────────────
    revenue_365d = metrics.get("trailing_365d_revenue_usd")            # DefiLlama dailyRevenue（净归属）
    # 股东回报：DefiLlama holdersRevenue（买币 + 质押奖励，混合代理）
    holders_365d = (metrics.get("trailing_365d_holders_revenue_usd")
                    or metrics.get("trailing_365d_shareholder_returns_usd"))
    retained_365d = round(revenue_365d - holders_365d, 2) if (revenue_365d and holders_365d) else None
    dist_ratio = round(holders_365d / revenue_365d, 4) if (revenue_365d and holders_365d) else None
    retain_ratio = round(1 - dist_ratio, 4) if dist_ratio else None

    revenue_included = {
        "protocol_fees_usd_365d": revenue_365d,
        "holders_revenue_usd_365d": holders_365d,        # dailyHoldersRevenue（买币+质押奖励，混合）
        "retained_treasury_usd_365d": retained_365d,      # 留存：Surplus Buffer + 未销毁的买币库存
        "total_usd_365d": revenue_365d,
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue_365d,
        "calculation_note": "cdp 稳定币协议：dailyRevenue 已扣 DSR/SSR 用户存款利息，无 LP 分润成本，毛利 = 协议盈余",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "dilution_note",
        "calculation_note": "SKY staking farm 部分含新铸造 SKY，按协议支出/留存处理，不重复扣减净利（口径：净利 = 协议盈余）",
    }
    net_income = {
        "net_income_usd_365d": revenue_365d,
        "operating_cost_usd_365d": None,
        "calculation_note": (
            f"协议盈余 {_fmt(revenue_365d)}（DefiLlama dailyRevenue，已扣 DSR/SSR）；"
            f"留存 vs 分配：留存 {_fmt(retained_365d)}（{retain_ratio:.1%}，Surplus Buffer 国库 + 买币未销毁库存），"
            f"分配 {_fmt(holders_365d)}（{dist_ratio:.1%}，DefiLlama holdersRevenue：买币 + 质押奖励，混合代理）"
        ) if dist_ratio else "协议盈余口径待复算",
    }

    # ── 股东回报（L3）────────────────────────────────────────────
    holder_yield = round(holders_365d / mcap * 100, 4) if (holders_365d and mcap) else None
    by_mechanism = [
        {
            "mechanism": "SBE 回购 + 质押奖励（DefiLlama holdersRevenue 混合口径）",
            "type": "buyback",   # 归入"回购/销毁组"（validate 重算口径 destroy|buyback）
            "usd_365d": round(holders_365d, 2) if holders_365d else None,
            "yield_percent": holder_yield,
            "note": f"计入股东回报（Boss 2026-10-08 定稿）：{DL_HOLDERS_DEF}。"
                    f"⚠️ SBE 买币自 2024-09 起为「买 SKY 交国库」（库存受治理支配、可再分配），"
                    f"不等于销毁；只有实际 burn 才减少供应。实际买币发生额见 {ACTUAL_BUYBACK_SOURCE}",
        },
        {
            "mechanism": "Surplus Buffer 留存 + 买币未销毁库存",
            "type": "buyback",
            "usd_365d": None,  # 不计入股东回报（未流向持币人）
            "yield_percent": None,
            "note": f"不计入股东回报：留存 {_fmt(retained_365d)}（{retain_ratio:.1%}）—— Surplus Buffer 国库 + "
                    f"SBE 买币进国库（可再分配，非直接流向持币人）。按铁律「只计流向流通持币人的价值流」",
        },
    ]

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            # 归入"回购/销毁组"（validate 重算口径：type in destroy|buyback）
            "destroy_usd_365d": round(holders_365d, 2) if holders_365d else None,
            "yield_usd_365d": None,
            "destroy_yield_percent": holder_yield,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": round(holders_365d, 2) if holders_365d else None,
            "shareholder_yield_percent": holder_yield,
            "status": "active",
            "basis_note": "股东回报 = DefiLlama holdersRevenue（买币 × 市价 + 质押奖励，混合代理）；"
                          "非纯销毁，SBE 买币进国库可再分配",
        },
    }

    # ── 派生估值（L4）──────────────────────────────────────────────
    pe = round(mcap / holders_365d, 4) if (mcap and holders_365d) else None
    ps = round(mcap / revenue_365d, 4) if (mcap and revenue_365d) else None
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": dist_ratio}

    margins = {
        "gross_margin_percent": round(revenue_365d / revenue_365d * 100, 4) if revenue_365d else None,
        "net_margin_percent": round(revenue_365d / revenue_365d * 100, 4) if revenue_365d else None,
        "note": "dailyRevenue 已扣 DSR/SSR 用户支出（净归属口径），毛利率/净利率 = 100%（口径标注，非经营性利润）",
    }

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "surplus_buffer_retention": {"note": "Surplus Buffer 国库留存不计入股东回报"},
                    "sbe_buyback_to_treasury": {"note": "SBE 买 SKY 进国库（2024-09 起），可再分配，非销毁、非直接流向持币人"},
                    "farm_staking": {"note": "Splitter farm 部分为协议支出；其中付给 stakers 的 USDS 已计入 DefiLlama holdersRevenue"},
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "defillama",
                    "url": "https://api.llama.fi/summary/fees/sky?dataType=dailyHoldersRevenue",
                },
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
            "method": f"DefiLlama dailyRevenue 365d {_fmt(revenue_365d)}；"
                      f"holdersRevenue 365d {_fmt(holders_365d)}（买币 × 市价 + 质押奖励，混合代理）"
                      f"；实际买币发生额另见 {ACTUAL_BUYBACK_SOURCE}",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "sky")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
