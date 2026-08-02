#!/usr/bin/env python3
"""
GMX 专属适配器 — data/protocols/gmx/adapter.py

按判定书（docs/protocol-revenue-recognition.md §13 GMX）输出 Financial Snapshot：
- 实体类型：app（perp_dex）
- 现状（2026-03-04 "Restore Price Discovery"）：质押分红暂停，27% 协议费用全额转国库，
  转为公开市场回购 + 国库积累（PCV）——回购但不向质押者分发（回购-留存模式）
- 恢复条件：价格阈值 $90（对应市值 ~$9 亿），当前 ~$6-7 远未触发
- 判定：收入 → 扣 LP → 净利 → 留存 27%；**股东回报 = 0**，标注「锁定至 $90」
- 数据源：DefiLlama（V2 交易费 dailyRevenue 365d）+ 提案 #5042

config.json 只读不重写（机制/口径声明 + tevRatio 0.27 = 协议费率）。
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
    pid = Path(proto_dir).name  # "gmx"
    config = _load(proto_dir / "config.json") or {}
    tev_records = _load(proto_dir / "tev-records.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    metrics = ap.get("metrics", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）──────────────────────────────────────────────
    # DefiLlama V2 交易费 dailyRevenue 365d（协议净收入，LP 分润已在数据源扣减）
    revenue = metrics.get("trailing_365d_revenue_usd")  # ~$12.68M

    # tev-records 交叉核对（DefiLlama dailyHoldersRevenue 月聚合；含暂停前历史，仅供注记）
    tev_records_365d = None
    try:
        cutoff = (date.today() - timedelta(days=365)).isoformat()
        records_365d = [
            r.get("amount_usd") for r in tev_records.get("records", [])
            if r.get("date", "") >= cutoff and r.get("amount_usd")
        ]
        tev_records_365d = sum(records_365d) if records_365d else None
    except Exception:
        tev_records_365d = None

    # ── 股东回报（L3）：锁定期内实质为 0 ───────────────────────
    # 27% 协议费全额转国库（回购-留存模式，回购进国库不流通）；恢复条件价格 ≥ $90 未触发
    # 股东回报 = 0（确凿为 0，非数据缺失）：非 null，以体现「锁定至 $90」口径
    by_mechanism = [
        {
            "mechanism": "27% 协议费回购留存（Treasury 累积，非流通）",
            "type": "buyback",
            "usd_365d": 0,  # 机制确凿为 0（回购进国库不流通），非数据缺失
            "yield_percent": 0,
            "verified": "partial",
            "note": "2026-03-04 Restore Price Discovery：质押分红暂停，27% 协议费用全额转国库（公开市场回购 + PCV 积累），"
                    "回购进国库不流通 → 股东回报 = 0；恢复条件 GMX 价格 ≥ $90（对应市值 ~$9 亿，当前 ~$6-7 远未触发），标注「锁定至 $90」",
        },
    ]

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": None,  # 无销毁
            "yield_usd_365d": None,    # 无收益型机制
            "destroy_yield_percent": None,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": 0,  # 确凿为 0（回购进国库不流通）
            "shareholder_yield_percent": 0,
        },
    }

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────
    # 判定书：收入 → 扣 LP → 净利 → 留存 27%。DefiLlama dailyRevenue 为协议净收入（LP 已扣）。
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue,
        "calculation_note": "DefiLlama dailyRevenue（V2 交易费）为协议净收入，LP 分润已在数据源扣减；毛利 = 收入",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "GMX 供应固定（~1000 万枚，无持续增发），不涉及增发成本",
    }
    net_income = {
        "net_income_usd_365d": revenue,
        "operating_cost_usd_365d": None,
        "calculation_note": "净利 = 27% 协议费（全额留存国库，回购-留存模式）；股东回报 = 0，标注「锁定至 $90」",
    }

    # ── 派生估值 / 利润率（与 build-snapshot.py 派生逻辑一致） ─
    pe = None  # 股东回报为 0 → P/E 无意义（除零），null
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = None  # 股东回报 0 → 派息率无意义
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    gm = round(revenue / revenue * 100, 4) if revenue else None
    margins = {
        "gross_margin_percent": gm,
        "net_margin_percent": gm,
        "note": "派生计算：gross = GP/Rev, net = NI/Rev；协议收入为净额口径，故为 100%",
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
                    "staking_dividends": {
                        "note": "质押分红已暂停（2026-03-04 Restore Price Discovery），改 Treasury 累积回购，等价格 ≥ $90 触发分配"
                    },
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "defillama",
                    "url": "https://api.llama.fi/summary/fees/gmx?dataType=dailyRevenue（V2 交易费）+ gov.gmx.io 提案 #5042",
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
            "method": f"净利 = DefiLlama V2 交易费 dailyRevenue 365d {_fmt(revenue)}；27% 协议费全额留存国库"
                      f"（提案 #5042，2026-03-04 Restore Price Discovery）；股东回报 = 0，锁定至 $90"
                      f"{f'；tev-records 365d {_fmt(tev_records_365d)}（含暂停前历史，仅参考）' if tev_records_365d else ''}",
            "status": "partial",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "gmx")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
