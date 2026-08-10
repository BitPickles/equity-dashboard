#!/usr/bin/env python3
"""
Ethena 专属适配器 — data/protocols/ethena/adapter.py

按判定书（docs/protocol-revenue-recognition.md ### 17. Ethena）输出 Financial Snapshot：
- 实体类型：app（basis_trading）
- 现状：sUSDe yield ~3.5-4% APY 全归 sUSDe 持有人；DAT 回购（~$890M 分批）确认为
  金库/储备出资的资本运作，非经营利润分配，不计入持续股东回报
- 定稿：**费用开关生效前 ENA 股东回报 = 0**；收入可算（近 12 月 ~$310M，净利仅 ~$0.6M）
- AI 哨兵观察点：2026Q3 费用开关激活状态（激活后 sENA 预期 >5%，届时更新）
- 股东回报 = 0（确凿为 0，非数据缺失）

数据源（本地已验证缓存 + 判定书）：
- daily/latest.json   → total1y_fees_usd（近 12 月费用，判定书 ~$310M）
- all-protocols.json  → metrics.trailing_365d_revenue_usd（DefiLlama dailyRevenue，协议留存）
- config.json         → revenue_recognition（DAT 回购排除、费用开关观察点）
- 判定书              → 净利仅 ~$0.6M（费用开关生效前）
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


def _fmt(x):
    return f"${x:,.0f}" if x else "N/A"


def build_snapshot(proto_dir):
    pid = Path(proto_dir).name
    config = _load(proto_dir / "config.json") or {}
    daily = _load(BASE_DIR / "data" / "daily" / pid / "latest.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")
    metrics = ap.get("metrics", {}) or {}

    # ── 收入（L2）──────────────────────────────────────────────
    # 近 12 月费用（判定书 ~$310M；daily latest total1y_fees_usd 更精确）
    gross_fees = (daily.get("latest_record") or {}).get("total1y_fees_usd")
    # DefiLlama dailyRevenue 365d = 协议实际留存（扣除分配给 sUSDe 后的部分）
    protocol_rev = metrics.get("trailing_365d_revenue_usd")
    # 分配给 sUSDe 持有人的收益（视为流向持有人的成本，不计入协议股东回报）
    susde_cost = round(gross_fees - protocol_rev, 2) if (gross_fees and protocol_rev) else None

    revenue_included = {
        "protocol_fees_usd_365d": gross_fees,      # 近 12 月总费用（判定书口径）
        "total_usd_365d": gross_fees,
    }

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": susde_cost,      # sUSDe yield 分配（流向持有人，非 ENA）
        "gross_profit_usd_365d": protocol_rev,     # 协议留存（DefiLlama dailyRevenue）
        "calculation_note": f"总费用 {_fmt(gross_fees)} − 分给 sUSDe 持有人 {_fmt(susde_cost)} = 协议留存 {_fmt(protocol_rev)}"
                            f"（sUSDe yield ~3.5-4% APY 全归 sUSDe 持有人，不计入 ENA 股东回报）",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "判定书未将 ENA 增发列为成本（无对价解锁作稀释注记，费用开关激活后重评估）",
    }
    # 判定书：净利仅 ~$0.6M（协议留存经运营/储备成本后）
    net_income_usd = 600_000
    net_income = {
        "net_income_usd_365d": net_income_usd,
        "operating_cost_usd_365d": round(protocol_rev - net_income_usd, 2) if protocol_rev is not None else None,
        "calculation_note": f"判定书：近 12 月收入 {_fmt(gross_fees)} 但净利仅 {_fmt(net_income_usd)}"
                            f"（绝大部分费用分配给 sUSDe + 储备/运营成本；费用开关激活前 ENA 股东回报 = 0）",
    }

    # ── 股东回报（L3）：费用开关生效前 = 0 ─────────────────────
    by_mechanism = [{
        "mechanism": "费用开关（Fee Switch）sENA 分润",
        "type": "yield",
        "usd_365d": 0,  # 确凿为 0（费用开关 2026Q3 待激活），非数据缺失
        "yield_percent": 0,
        "note": "费用开关生效前 ENA 股东回报 = 0；激活后 sENA 预期 >5%（届时更新）——AI 哨兵观察点：2026Q3 费用开关激活状态；"
                "sUSDe yield 归 sUSDe 持有人；DAT 回购（~$890M）是金库/储备出资的资本运作，非经营利润分配，不计入",
    }]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": None,
            "yield_usd_365d": None,
            "destroy_yield_percent": None,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": 0,  # 确凿为 0（费用开关生效前）
            "shareholder_yield_percent": 0,
        },
    }

    # ── margins / valuation（派生，validate 重算比对）────────
    gm = round(protocol_rev / gross_fees * 100, 4) if (protocol_rev and gross_fees) else None
    nm = round(net_income_usd / gross_fees * 100, 4) if (gross_fees and net_income_usd is not None) else None
    margins = {
        "gross_margin_percent": gm,
        "net_margin_percent": nm,
        "note": "费用开关生效前：绝大部分费用分配给 sUSDe 持有人 → 协议毛利率极低（~2.7%）、净利率 ~0.2%；股东回报 = 0",
    }

    pe = None  # 股东回报 0 → P/E 无意义
    ps = round(mcap / gross_fees, 4) if (mcap and gross_fees) else None
    payout = None  # 股东回报 0 → 派息率无意义
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "susde_yield": {"note": f"sUSDe yield ~3.5-4% APY（{_fmt(susde_cost)}/365d）全归 sUSDe 持有人，不计入 ENA 股东回报"},
                    "dat_buyback": {"note": "DAT 回购（~$890M）确认为金库/储备出资的资本运作，不计入持续股东回报"},
                    "fee_switch": {"note": "费用开关 2026Q3 待激活，激活后 sENA 预期 >5%（届时更新）——AI 哨兵观察点"},
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "official",
                    "url": "DefiLlama dailyFees/dailyRevenue（daily/latest.json + all-protocols metrics）+ Ethena 官方治理/dashboard",
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
            "method": f"近 12 月费用 {_fmt(gross_fees)}（判定书 ~$310M），协议留存 {_fmt(protocol_rev)}（DefiLlama dailyRevenue 365d），"
                      f"净利 {_fmt(net_income_usd)}（判定书）；费用开关生效前 ENA 股东回报 = 0（2026Q3 观察点）",
            "status": "estimated",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "ethena")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
