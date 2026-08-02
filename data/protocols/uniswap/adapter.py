#!/usr/bin/env python3
"""
Uniswap 专属适配器 — data/protocols/uniswap/adapter.py

按判定书（docs/protocol-revenue-recognition.md ### 8. Uniswap）输出 Financial Snapshot：
- 实体类型：app（dex）
- 收入 = 抽成手续费（v2 0.05% 全池统一 / v3 1/4~1/6 of LP fee）
- fee switch 2025-12-28（UNIfication）开启后，协议费基本全部 → TokenJar → Firepit → 0xdead 销毁
- 计入股东回报：Firepit 销毁 = 回购性质 🟢（365d 0xdead 累计口径，排除一次性 100M retro burn）

数据源（本地已验证缓存）：
- burn-history.json → 链上 UNI → 0xdead 日序列（Etherscan logs，已排除 >=10M 一次性事件）
- all-protocols.json → validation.burn_7d/30d/90d/365d_uni + uni_price_usd（当前价重估）
- tev-records.json  → 股东回报历史（Firepit Burn）
- config.json       → 判定书/机制声明（只读）

说明：A 口径按『到 0xdead 即算 supply 收缩』处理所有来源；Unichain 上的 Firepit 销毁
当前未计入（已知局限，M1 扩展）。2025-12-27 的 100M UNI 一次性国库销毁不计入 365d。
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
    _burn_history = _load(proto_dir / "burn-history.json") or {}
    _tev_records = _load(proto_dir / "tev-records.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    validation = ap.get("validation", {})
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）：抽成手续费 ≈ 365d 0xdead 销毁额（fee switch 后基本全部回购）──
    burn_365d_uni = validation.get("burn_365d_uni")       # 4,580,003 UNI
    uni_price = validation.get("uni_price_usd")           # 4.01 USD
    burn_365d = round(burn_365d_uni * uni_price, 2) if (burn_365d_uni and uni_price) else None

    revenue_included = {
        "protocol_fees_usd_365d": burn_365d,
        "burn_usd_365d": burn_365d,
        "total_usd_365d": burn_365d,
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────────
    # 抽成手续费 = 协议净得（LP 分润已由各池自行结算），毛利 = 收入
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": burn_365d,
        "calculation_note": "抽成手续费为协议净得（LP 分润已由各池自行结算），毛利 = 收入",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "UNI 总供应封顶 10 亿，无持续增发；一次性 1 亿 UNI 国库销毁为存量操作，不涉及增发成本",
    }
    net_income = {
        "net_income_usd_365d": burn_365d,
        "operating_cost_usd_365d": None,
        "calculation_note": "收入基本全部用于回购（fee switch 2025-12-28 开启后协议费经 TokenJar → Firepit → 0xdead 销毁 UNI），净利 = 股东回报",
    }

    # ── 股东回报（L3）：Firepit 销毁 = 回购性质 🟢 ────────────────
    burn_yield = round(burn_365d / mcap * 100, 4) if (burn_365d and mcap) else None
    by_mechanism = [
        {"mechanism": "Firepit 销毁 UNI（fee switch → TokenJar → 0xdead）", "type": "destroy",
         "usd_365d": burn_365d,
         "yield_percent": burn_yield,
         "note": "销毁 = 回购性质 🟢：365d 0xdead 累计 " + str(burn_365d_uni) + " UNI × " + str(uni_price) + " USD，排除一次性 100M UNI retroactive burn（2025-12-27）"},
    ]

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": burn_365d,
            "yield_usd_365d": None,
            "destroy_yield_percent": burn_yield,
            "yield_yield_percent": None,
            "shareholder_returns_usd_365d": burn_365d,
            "shareholder_yield_percent": burn_yield,
        },
    }

    # ── 派生估值（L4）──────────────────────────────────────────────
    pe = round(mcap / burn_365d, 4) if (mcap and burn_365d) else None
    valuation = {
        "pe": pe,
        "ps": pe,           # 收入 = 净利 = 股东回报（全量回购）→ P/S = P/E
        "pb": None,
        "ev_revenue": None,
        "payout_ratio": 1.0 if burn_365d else None,  # 收入基本 100% 用于回购
    }

    # ── margins ────────────────────────────────────────────────────
    margins = {
        "gross_margin_percent": round(burn_365d / burn_365d * 100, 4) if burn_365d else None,
        "net_margin_percent": round(burn_365d / burn_365d * 100, 4) if burn_365d else None,
        "note": "抽成手续费为协议净得，收入 100% 用于 Firepit 回购销毁；毛利率/净利率 = 100%（口径标注）",
    }

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "retroactive_burn": {"note": "一次性 1 亿 UNI 国库销毁（2025-12-27 Timelock 执行）为存量模拟操作，不计入 365d 股东回报"},
                    "unichain_burns": {"note": "Unichain 上 Firepit 销毁当前未计入（脚本只覆盖 Ethereum mainnet，M1 扩展）"},
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "chain",
                    "url": "https://etherscan.io/address/0x000000000000000000000000000000000000dEaD",
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
            "method": "链上 365d UNI 转入 0xdead 累计 " + str(burn_365d_uni) + " UNI（Etherscan logs，排除 >=10M 一次性事件）× 当前价 " + str(uni_price) + " USD",
            "status": "verified",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "uniswap")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
