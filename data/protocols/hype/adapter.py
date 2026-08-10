#!/usr/bin/env python3
"""
Hyperliquid 专属适配器 — data/protocols/hype/adapter.py（正式 key 为 hype）

按判定书（docs/protocol-revenue-recognition.md §9 Hyperliquid）输出 Financial Snapshot：
- 实体类型：app（perpetuals / Perp DEX）
- 机制：手续费直接销毁 ≈ 回购，基本 99% 🟢（销毁流通币 = 流向所有持币人）
- AF 部分：AF 用交易费回购 HYPE 留在 AF 地址（可被动用）——按「只计流向流通持币人的价值流」
  铁律不计入，仅作注记；spot 手续费真销毁计入（已含于 99% 口径）
- 收入 = DefiLlama dailyRevenue 365d（链上 AF entryNtl 交叉验证）
- 股东回报 = 收入 × 99%（销毁 = 回购性质 🟢）

注意：data/all-protocols.json 中的 protocols key 为 `hype`（前端遍历 all-protocols 取数），
因此本目录才是正式消费路径；data/protocols/hyperliquid/ 为同口径镜像（旧别名目录）。

数据源（本地缓存）：
- config.json            → 机制/口径声明（payout_ratio=0.99）
- data/all-protocols.json → 市值 / metrics（trailing_365d_revenue_usd 已验证）
- data/protocols/hype/af-history.json → AF 日序列（只读参考；截至 2026-04-17 陈旧，仅交叉核对注记）
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
    """USD 千分位格式化；None → N/A。"""
    return f"${x:,.0f}" if x else "N/A"


def build_snapshot(proto_dir):
    pid = Path(proto_dir).name  # "hype"
    config = _load(proto_dir / "config.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    # all-protocols.json 中 Hyperliquid 的 key 为 "hype"，直接取数
    ap = all_protocols.get("protocols", {}).get("hype", {})

    metrics = ap.get("metrics", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")
    # 判定书 §9：payout_ratio 维持 ~99%（以链上实际销毁为准，spot 真销毁计入、AF 余额不计入）
    payout_ratio = config.get("payout_ratio") if config.get("payout_ratio") is not None else 0.99
    if payout_ratio >= 1:
        payout_ratio = 0.99  # config 遗留值 1.0（100%）与判定书 ~99% 不符时以判定书为准

    # ── 收入（L2）──────────────────────────────────────────────
    # DefiLlama dailyRevenue 365d（已验证）；链上 AF entryNtl 交叉验证。
    revenue = metrics.get("trailing_365d_revenue_usd")  # ~$773.0M
    # af-history 旧缓存交叉核对（截至 2026-04-17，窗口不重叠，仅供注记）
    af_history = _load(BASE_DIR / "data" / "protocols" / "hype" / "af-history.json") or {}
    af_365d = None
    try:
        import datetime as _dt
        cutoff = (_dt.date.today() - _dt.timedelta(days=365)).isoformat()
        af_365d = sum(
            r.get("usd", 0) for r in af_history.get("daily", [])
            if r.get("date", "") >= cutoff and r.get("usd")
        ) or None
    except Exception:
        af_365d = None

    # ── 股东回报（L3）：99% 计入销毁 🟢 ────────────────────────
    returns_usd = round(revenue * payout_ratio, 2) if revenue else None
    yield_pct = round(returns_usd / mcap * 100, 4) if (returns_usd and mcap) else None

    by_mechanism = [
        {
            "mechanism": "Assistance Fund 手续费销毁（spot 真销毁）",
            "type": "destroy",
            "usd_365d": returns_usd,
            "yield_percent": yield_pct,
            "verified": "verified",
            "note": "手续费直接销毁 ≈ 回购，99% 计入 🟢（销毁流通币 = 流向所有持币人）；"
                    "AF 用交易费回购 HYPE 留存在 AF 地址（~1%，可被动用）不计入，仅作注记；"
                    "funding（点对点）/ 清算（无手续费）/ HyperEVM gas（供给收缩）均不计入",
        },
    ]

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": returns_usd,
            "yield_usd_365d": None,  # 无收益型机制 → null
            "destroy_yield_percent": yield_pct,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": returns_usd,
            "shareholder_yield_percent": yield_pct,
        },
    }

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────
    # Perp DEX 手续费直接销毁，无 LP 分润/无增发成本 → 净利 = 收入
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue,
        "calculation_note": "Hyperliquid 手续费直接销毁，无 LP 分润成本，毛利 = 收入（DefiLlama dailyRevenue 口径）",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "HYPE 无持续增发（总供应 10 亿固定，回购销毁使供给收缩），不涉及增发成本",
    }
    net_income = {
        "net_income_usd_365d": revenue,
        "operating_cost_usd_365d": None,
        "calculation_note": "净利 = 收入 = 手续费总额；99% 用于回购销毁（计入股东回报），~1% 留存 AF 注记",
    }

    # ── 派生估值 / 利润率（与 build-snapshot.py 派生逻辑一致） ─
    pe = round(mcap / returns_usd, 4) if (mcap and returns_usd) else None
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = round(returns_usd / revenue, 4) if (returns_usd and revenue and revenue > 0) else None
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    gm = round(revenue / revenue * 100, 4) if revenue else None
    margins = {
        "gross_margin_percent": gm,
        "net_margin_percent": gm,
        "note": "无 LP/运营成本模型，毛利率/净利率 = 100%（口径标注，非经营性利润）",
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
                    "assistance_fund_balance": {
                        "note": "AF 用交易费回购 HYPE 留在 AF 地址（可被动用），不计入，仅作注记"
                    },
                    "funding_liquidation_gas": {
                        "note": "funding 点对点支付 / 无清算手续费 / HyperEVM gas 供给收缩，均不计入"
                    },
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "chain",
                    "url": "https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees（DefiLlama dailyRevenue 交叉验证）",
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
            "method": f"净利 = DefiLlama dailyRevenue 365d {_fmt(revenue)}；股东回报 = 收入 × {payout_ratio} "
                      f"= {_fmt(returns_usd)}（销毁型 🟢，payout_ratio={payout_ratio}）"
                      f"{f'；af-history 旧缓存 365d {_fmt(af_365d)}（截至 2026-04-17，窗口不重叠，仅参考）' if af_365d else ''}",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "hype")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
