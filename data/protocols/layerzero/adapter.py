#!/usr/bin/env python3
"""
LayerZero 专属适配器 — data/protocols/layerzero/adapter.py

按判定书 §26（LayerZero，调研完成待定稿口径）输出 Financial Snapshot：
- 实体类型：app（跨链基础设施；DefiLlama "LayerZero V2" = 整个协议）
- 协议本体收入 = 0：消息费 0% take rate（$3.59M 流向 DVN/Executor 外部节点外包成本）；fee switch 未开启（半年公投多次未过）
- 收入 = Stargate 收入（2025-08 $110M 收购 Stargate；2026-03 起 100% Stargate 收入回购 ZRO）
- 股东回报 = Stargate 回购 ZRO（真实但量小，累计 149.5 万 ZRO/$3.14M）→ 回报率 ≈ 0.3%
- 稀释注记 ⚠️：每月解锁 ~$48M（2027 年中前持续）→ token_emission_cost.treatment = 'dilution_note'（无对价，不算成本但必须标注）
- 观察点 🔍：费用开关半年公投——开启后收入端打开（$150B+ 年化跨链量 × bps）

数据源：all-protocols.json（Stargate 回购 365d + 市值/TVL）+ 链上 Stargate 回购追踪。
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
    pid = Path(proto_dir).name  # "layerzero"
    config = _load(proto_dir / "config.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    rr = config.get("revenue_recognition", {})
    metrics = ap.get("metrics", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）──────────────────────────────────────────────
    # 协议本体收入 = 0（fee switch 未开启，消息费 0% take rate）；
    # 计入收入 = Stargate 收入（DefiLlama trailing_365d_revenue_usd，量小）
    revenue = metrics.get("trailing_365d_revenue_usd")  # ~$3.07M（Stargate 收入）
    # 毛利：极薄——gross 中 $2.28M 给 supply-side（DVN/Executor 外包），归协议 ≈ $0.78M
    # 优先复用 all-protocols 已验证 financial_snapshot 数值（2026-08-02 定稿），避免重算漂移
    fs = ap.get("financial_snapshot", {}) or {}
    gross_profit = fs.get("gross_profit_usd_365d")
    lp_share = fs.get("lp_share_cost_usd_365d")
    if gross_profit is None and revenue:
        gross_profit = round(revenue * 0.2557, 2)
    if lp_share is None and (revenue and gross_profit):
        lp_share = round(revenue - gross_profit, 2)

    # ── 毛利 / 增发（稀释注记）/ 净利 ─────────────────────────
    gp = {
        "lp_share_cost_usd_365d": lp_share,
        "gross_profit_usd_365d": gross_profit,
        "calculation_note": "Stargate 收入中 $2.28M 流向 supply-side（DVN/Executor 外包成本），归协议 ≈ $0.78M（毛利极薄）",
    }
    emission = {
        "usd_365d": None,  # 无对价解锁，不算成本（不扣减净利）
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "dilution_note",
        "calculation_note": "每月解锁 ~$48M（2027 年中前持续）——无对价解锁，不算成本但必须标注（财报页强制展示）；"
                            "回购月 ~$150K 远不足以对冲",
    }
    net_income = {
        "net_income_usd_365d": gross_profit,
        "operating_cost_usd_365d": None,
        "calculation_note": "净利 = 毛利 − 增发成本(0，稀释注记) − 运营成本(数据不可得)；归协议 ≈ $0.78M",
    }

    # ── 股东回报（L3）：Stargate 回购 ZRO（真实但量小） ───────
    buyback_usd = metrics.get("trailing_365d_shareholder_returns_usd")  # 784,539（annual Stargate 回购）
    buyback_yield = round(buyback_usd / mcap * 100, 4) if (buyback_usd and mcap) else None
    by_mechanism = [
        {
            "mechanism": "Stargate 收入回购 ZRO（100%）",
            "type": "buyback",
            "usd_365d": buyback_usd,
            "yield_percent": buyback_yield,
            "verified": "partial",
            "note": "2026-03 起 100% Stargate 收入回购 ZRO（累计 149.5 万 ZRO/$3.14M，链上可验证）；"
                    "协议本体 fee switch 未开启 → 股东回报极低（0.3%）",
        }
    ]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            # ⚠️ validate 重算把 buyback 类计入 destroy（type in destroy/buyback），
            # summary 必须与之同步，否则「文件=None 重算=有值」冲突
            "destroy_usd_365d": buyback_usd if buyback_usd else None,
            "yield_usd_365d": None,
            "destroy_yield_percent": buyback_yield if buyback_yield else None,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": buyback_usd,
            "shareholder_yield_percent": buyback_yield,
        },
    }

    # ── 派生估值 / 利润率 ──────────────────────────────────────
    pe = round(mcap / buyback_usd, 4) if (mcap and buyback_usd) else None
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = round(buyback_usd / gross_profit, 4) if (buyback_usd and gross_profit and gross_profit > 0) else None
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    gm = round(gross_profit / revenue * 100, 4) if (revenue and gross_profit) else None
    margins = {
        "gross_margin_percent": gm,
        "net_margin_percent": gm,
        "note": "派生计算：毛利极薄（supply-side 外包成本占比高）；gross = GP/Rev",
    }

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": {
                    "protocol_fees_usd_365d": 0,  # 协议本体收入 = 0（fee switch 未开启，消息费 0% take rate）
                    "stargate_fees_usd_365d": revenue,
                    "total_usd_365d": revenue,
                },
                "revenue_excluded": {
                    "protocol_fees": {
                        "note": "协议本体消息费 0% take rate（$3.59M 流向 DVN/Executor 外部节点外包成本）；fee switch 未开启（半年公投多次未过）"
                    },
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": rr.get("source_type") or "chain",
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
            "tvl_usd": tvl,
            "treasury_usd": None,
            "debt_usd": None,
        },
        "valuation": valuation,
        "verification": {
            "method": f"收入 = Stargate 收入 365d ${revenue:,.0f}（协议本体 0，fee switch OFF）；"
                      f"股东回报 = Stargate 回购 ${buyback_usd:,.0f}（100% Stargate 收入，累计 149.5 万 ZRO/$3.14M）"
                      f"；稀释注记：每月解锁 ~$48M（2027 年中前）；观察点：费用开关半年公投",
            "status": "partial",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "layerzero")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
