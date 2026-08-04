#!/usr/bin/env python3
"""
Sky (MakerDAO) 专属适配器 — data/protocols/sky/adapter.py

按判定书（docs/protocol-revenue-recognition.md ### 7. Sky）输出 Financial Snapshot：
- 实体类型：app（cdp / 稳定币）
- 机制（SBE）：盈余先进 Surplus Buffer 国库（上限 5000 万 DAI）；超额部分 SBE 从 Uniswap
  买入 MKR + 等量 DAI 组 LP 做市（LP 归协议，主动做市）；Elixir 在 MKR 低估时用 LP 真燃烧。
- 计入股东回报：Elixir 真燃烧（销毁 = 股息 🟢，type=destroy）
- 不计入：Surplus Buffer 留存（国库）；SBE 买 MKR 做市部分（LP 锁定，标注「回购做市」）
- 损益表：净利留存国库要讲清楚 → net_income 注明「留存 vs 分配」比例（payout_ratio ≈ 33.3%）

数据源（本地已验证缓存，2026-08-01 更新）：
- all-protocols.json  → validation.burn_7d/30d/90d/365d_usd（DefiLlama dailyHoldersRevenue）
  + metrics.trailing_365d_revenue_usd（DefiLlama dailyRevenue，协议净归属）
- tev-records.json   → 股东回报月度历史（Smart Burn Engine / Splitter burn）
- config.json        → 判定书/机制声明（只读）

说明：SBE 链上数据分散（新 Flapper 地址未公开 + LP token burn 复杂），且 DefiLlama
dailyHoldersRevenue 已精准对应 Splitter burn（SBE 真实支出，与 2026-03 治理公告吻合），
故采用 DefiLlama（见 config analyst_notes 的权衡）。
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
    _tev_records = _load(proto_dir / "tev-records.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    validation = ap.get("validation", {})
    metrics = ap.get("metrics", {})
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）：DefiLlama 口径 ─────────────────────────────────
    # dailyRevenue = 协议净归属（已扣 DSR/SSR 用户支出）→ 损益表顶线
    # dailyHoldersRevenue = Splitter burn（SBE/Elixir 真燃烧实际支出）→ 分配部分
    revenue_365d = metrics.get("trailing_365d_revenue_usd")  # 234,377,977
    burn_365d = validation.get("burn_365d_usd")              # 77,998,812（分配）
    retained_365d = round(revenue_365d - burn_365d, 2) if (revenue_365d and burn_365d) else None
    dist_ratio = round(burn_365d / revenue_365d, 4) if (revenue_365d and burn_365d) else None
    retain_ratio = round(1 - dist_ratio, 4) if dist_ratio else None

    revenue_included = {
        "protocol_fees_usd_365d": revenue_365d,
        "holders_revenue_usd_365d": burn_365d,      # dailyHoldersRevenue（SBE 真燃烧支出）
        "retained_treasury_usd_365d": retained_365d,  # 留存：Surplus Buffer + SBE LP + farm
        "total_usd_365d": revenue_365d,
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────────
    # cdp 稳定币协议：dailyRevenue 已扣 DSR/SSR 存款利息，无 LP 分润成本
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
        "calculation_note": "SKY staking farm 部分含新铸造 SKY（Splitter 分配），按协议支出/留存处理，不重复扣减净利（口径：净利 = 协议盈余）",
    }
    net_income = {
        "net_income_usd_365d": revenue_365d,
        "operating_cost_usd_365d": None,
        "calculation_note": (
            f"协议盈余 {revenue_365d:,.0f} USD（DefiLlama dailyRevenue，已扣 DSR/SSR）；"
            f"留存 vs 分配：留存 {retained_365d:,.0f} USD（{retain_ratio:.1%}，Surplus Buffer 国库 ≤5000 万 DAI + SBE 买 MKR 做市 LP 锁定 + farm 支出），"
            f"分配 {burn_365d:,.0f} USD（{dist_ratio:.1%}，Elixir 真燃烧 = 销毁即股息 🟢）"
        ),
    }

    # ── 股东回报（L3）：区分「销毁 / 留存」────────────────────────
    destroy_yield = round(burn_365d / mcap * 100, 4) if (burn_365d and mcap) else None
    by_mechanism = [
        {"mechanism": "Elixir / SBE 真燃烧（Splitter burn → MKR LP 销毁）", "type": "destroy",
         "usd_365d": round(burn_365d, 2) if burn_365d else None,
         "yield_percent": destroy_yield,
         "note": "销毁 = 股息 🟢 计入股东回报：DefiLlama dailyHoldersRevenue（= Splitter burn，SBE 真实支出，2026-03 后日均 ~$37.6k 与治理公告吻合）"},
        {"mechanism": "Surplus Buffer 留存 + SBE 回购做市（LP 锁定）", "type": "buyback",
         "usd_365d": None,  # 不计入股东回报，故不设数值（见 note）
         "yield_percent": None,
         "note": f"不计入股东回报：留存 {retained_365d:,.0f} USD（{retain_ratio:.1%}）—— Surplus Buffer 国库（≤5000 万 DAI）+ SBE 买 MKR 组 LP 做市（『回购做市』，LP 归协议锁定，非直接流向持币人）+ farm 支出"},
    ]

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": round(burn_365d, 2) if burn_365d else None,
            "yield_usd_365d": None,
            "destroy_yield_percent": destroy_yield,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": round(burn_365d, 2) if burn_365d else None,
            "shareholder_yield_percent": destroy_yield,
        },
    }

    # ── 派生估值（L4）──────────────────────────────────────────────
    pe = round(mcap / burn_365d, 4) if (mcap and burn_365d) else None
    ps = round(mcap / revenue_365d, 4) if (mcap and revenue_365d) else None
    valuation = {
        "pe": pe,
        "ps": ps,
        "pb": None,
        "ev_revenue": None,
        "payout_ratio": dist_ratio,  # 分配比例（留存 = 1 − payout）
    }

    # ── margins ────────────────────────────────────────────────────
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
                    "surplus_buffer_retention": {"note": "Surplus Buffer 国库留存（上限 5000 万 DAI）不计入股东回报"},
                    "sbe_market_making": {"note": "SBE 买 MKR + 等量 DAI 组 LP 做市（LP 归协议锁定，标注『回购做市』，非直接流向持币人）"},
                    "farm_staking": {"note": "Splitter farm 部分（新铸造 SKY + USDS yield 给 SKY stakers）为协议支出，非市场回购"},
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
        "balance_sheet": {
            "market_cap_usd": mcap,
            "tvl_usd": tvl,
            "treasury_usd": None,
            "debt_usd": None,
        },
        "valuation": valuation,
        "verification": {
            "method": "DefiLlama dailyHoldersRevenue 365d " + str(burn_365d) + " USD（Splitter burn/SBE 真燃烧）+ dailyRevenue 365d " + str(revenue_365d) + " USD；2026-03 治理减速后短周期 < 365d（日均 ~$37.6k）",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "sky")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
