#!/usr/bin/env python3
"""
dYdX 专属适配器 — data/protocols/dydx/adapter.py

按判定书（docs/protocol-revenue-recognition.md ### 12. dYdX）输出 Financial Snapshot：
- 实体类型：application（perpetuals）
- 收入 = 净协议费（DefiLlama dailyRevenue 毛口径，**含 affiliate/rebate 前、外部不可精确复算**；
  收入剧降：Q1'26 $0.99M → Q2'26 ~$0.6M；交易所已更名 Arcus（2026-07），DYDX 代币/Chain 未更名）
- 股东回报 = **回购额（市价买入后质押，非销毁 → type='buyback'，勿误标 destroy）**
  - 链上回购账户（dydx1zc0jd76...）无公开 dashboard → 按判定书 P/F~88x 反推回购额 ≈ $1.08M
  - 质押分红（USDC 经 Cosmos x/distribution 给 staker）≈ 15% 净协议费（提案 #313）；
    DYDX 通胀 staking 奖励 ~0.01% APY 极低
- 数据源：dYdX Foundation 月度报告 + 链上回购账户 + 提案 #313 + DefiLlama

注意：validate.py 派生自洽要求 pe/ps/payout/margins/summary 必须由 L1-L3 重算一致；
buyback 类型会被系统归入 destroy 汇总组（质押非销毁，非真销毁，语义以 note 标注）。
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
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    mcap = ap.get("market_cap_usd")          # DYDX Chain native 流通市值（排除 ethDYDX 孤儿）
    tvl = ap.get("tvl")

    # ── 收入（L2）：净协议费（DefiLlama dailyRevenue 365d 缓存）────
    metrics = ap.get("metrics", {}) or {}
    revenue = metrics.get("trailing_365d_revenue_usd")  # $8.52M（含 affiliate/rebate 前，不可精确复算）
    revenue_included = {
        "net_fees_usd_365d": revenue,
        "total_usd_365d": revenue,
    }

    # ── 毛利 / 增发 / 净利 ─────────────────────────────────────────
    # 永续应用无 LP 分润；affiliate/rebate 前置补贴属运营口径（标注不可复算）
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": revenue,
        "calculation_note": "永续应用无 LP 分润成本 → 毛利 = 收入；affiliate 30-50% 分成 / Surge 50% rebate 等前置补贴归交易者（含 affiliate/rebate 前、外部不可精确复算）",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "DYDX 无挖矿增发成本模型（判定书未按增发成本处理，仅通胀解锁，不作成本扣除）",
    }
    net_income = {
        "net_income_usd_365d": revenue,
        "operating_cost_usd_365d": None,
        "calculation_note": "净利 = 收入（净协议费毛口径）；真实净协议费含 affiliate/rebate 前不可精确复算，实际低于此值",
    }

    # ── 股东回报（L3）─────────────────────────────────────────────
    # 回购：链上回购账户无公开 tracker → 按判定书 P/F~88x 反推（mcap/88）
    # 真实净协议费 = 回购 / 0.75 ≈ $1.45M（大量补贴回流交易者，DefiLlama 毛收入仅 17% 留存）
    buyback_usd = round(mcap / 88, 2) if mcap else None
    # 提案 #313 分配：75% 回购 / 15% 质押 / 5% MegaVault / 5% 金库
    staking_usd = round(buyback_usd * 15 / 75, 2) if buyback_usd else None

    by_mechanism = [
        {
            "mechanism": "净协议费回购（提案 #313，75%）",
            "type": "buyback",                              # 勿误标 destroy
            "usd_365d": buyback_usd,
            "yield_percent": round(buyback_usd / mcap * 100, 4) if (buyback_usd and mcap) else None,
            "note": "回购(质押非销毁)：市价买入 DYDX 后质押于 Treasury 专用账户（dydx1zc0jd76...），非销毁勿计销毁；链上无公开 tracker，按判定书 P/F~88x 反推（外部不可精确复算）",
        },
        {
            "mechanism": "质押分红（USDC，Cosmos x/distribution）",
            "type": "yield",
            "usd_365d": staking_usd,
            "yield_percent": round(staking_usd / mcap * 100, 4) if (staking_usd and mcap) else None,
            "note": "提案 #313 15% 净协议费以 USDC 分给 staker；DYDX 通胀 staking 奖励 ~0.01% APY 极低",
        },
    ]

    destroy_usd = buyback_usd     # 系统把 buyback 归入 destroy 汇总组（质押非销毁，非真销毁）
    yield_usd = staking_usd
    returns_usd = round((destroy_usd or 0) + (yield_usd or 0), 2) if (destroy_usd or yield_usd) else None
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": round(destroy_usd, 2) if destroy_usd else None,
            "yield_usd_365d": round(yield_usd, 2) if yield_usd else None,
            "destroy_yield_percent": round(destroy_usd / mcap * 100, 4) if (destroy_usd and mcap) else None,
            "yield_yield_percent": round(yield_usd / mcap * 100, 4) if (yield_usd and mcap) else None,
            "shareholder_returns_usd_365d": returns_usd,
            "shareholder_yield_percent": round(returns_usd / mcap * 100, 4) if (returns_usd and mcap) else None,
        },
    }

    # ── margins（派生，validate 重算比对）──────────────────────────
    gm = round(revenue / revenue * 100, 4) if revenue else None
    nm = round(revenue / revenue * 100, 4) if revenue else None
    margins = {
        "gross_margin_percent": gm,
        "net_margin_percent": nm,
        "note": "无 LP/成本模型 → 毛利率/净利率口径性 100%；真实净协议费含 affiliate/rebate 前不可精确复算",
    }

    # ── valuation（派生，validate 重算比对）────────────────────────
    pe = round(mcap / returns_usd, 4) if (mcap and returns_usd) else None
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = round(returns_usd / revenue, 4) if (returns_usd and revenue and revenue > 0) else None
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "affiliate_rebate": {"note": "大量前置补贴归交易者（affiliate 30-50% 分成、Surge 50% rebate、零费率市场）——收入为净协议费毛口径，外部不可精确复算"},
                    "ethdydx": {"note": "ethDYDX（ERC-20）bridge 已永久关闭（2025-06-13），持有人 0 股东回报，不计入"},
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "defillama",
                    "url": "DefiLlama dailyRevenue 365d 缓存 + 判定书（dYdX Foundation 月度报告 / 链上回购账户 / 提案 #313）",
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
            "method": "DefiLlama dailyRevenue 365d=" + str(revenue)
                      + " · 回购额按判定书 P/F~88x 反推（mcap/88）· 提案 #313 比例（75% 回购/15% 质押）",
            "status": "partial",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "dydx")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
