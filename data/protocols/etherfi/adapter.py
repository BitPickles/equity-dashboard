#!/usr/bin/env python3
"""
ether.fi 专属适配器 — data/protocols/etherfi/adapter.py

按判定书（docs/protocol-revenue-recognition.md ### 16. ether.fi，2026-08-02 定稿）：
- 实体类型：app（liquid_staking）
- 双回购引擎：提现费 100% 周度回购 + 协议收入 25% 月度回购，均回购 ETHFI
  分给 sETHFI 质押者（本质"质押者股息"）；叠加 DAO $50M 公开市场回购（unverified，不计入）
- 股东回报：回购 $16-24M/年 ÷ 市值 ~$400M ≈ 4-6%
- 计入收入：协议收入（Stake/Liquid/Cash）；协议收入（dailyRevenue）本地不可得 → null

数据源（本地缓存，2026-08-01 已验证）：
- tev-records.json → summary.total_tev_usd（DefiLlama dailyHoldersRevenue 365d ≈ $16.7M，
  落在判定书 $16-24M 区间下沿）
- buyback-history.json → sETHFI 合约入金上界（含用户 stake / 跨链 bridge，不可分离，
  仅作监控，不作主数字）
- all-protocols.json → 市值 / tvl / validation（ethfi_price_usd 等）
- daily/latest.json → dailyFees 365d ≈ $225M（含 staking 收益，多数归 eETH 用户，
  非协议收入，注记）

注意：M0 阶段以本地已验证缓存组装；Token Terminal/Dune 精确协议收入与单引擎
回购拆分为 M1 管道任务（update-etherfi-buybacks.py）。
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
    tev_records = _load(proto_dir / "tev-records.json") or {}
    buyback = _load(proto_dir / "buyback-history.json") or {}
    all_protocols = _load(BASE_DIR / "data" / "all-protocols.json") or {}
    ap = all_protocols.get("protocols", {}).get(pid, {})

    validation = ap.get("validation", {}) or {}
    mcap = ap.get("market_cap_usd")
    tvl = ap.get("tvl")

    # ── 收入（L2）：协议收入（Stake/Liquid/Cash）本地不可得 → null ──
    # dailyFees 365d 存在但含 staking 收益（多数归 eETH 用户），不作协议收入
    daily = _load(BASE_DIR / "data" / "daily" / pid / "latest.json") or {}
    fees_1y = (daily.get("latest_record") or {}).get("total1y_fees_usd")
    revenue = None

    revenue_included = {
        "protocol_fees_usd_365d": revenue,
        "total_usd_365d": revenue,
        "note": "DefiLlama dailyFees 365d ≈ $"
        + str(fees_1y)
        + " 含 staking 收益（多数归 eETH 用户），非协议收入；协议收入（Token Terminal/Dune 口径）未缓存 → null",
    }

    # ── 毛利/增发/净利 ─────────────────────────────────────────
    gp = {
        "lp_share_cost_usd_365d": None,
        "gross_profit_usd_365d": None,
        "calculation_note": "协议收入/毛利不可得（Token Terminal/Dune 未缓存）→ null",
    }
    emission = {
        "usd_365d": None,
        "annual_emission_tokens": None,
        "inflation_rate_percent": None,
        "treatment": "none",
        "calculation_note": "未获取 ETHFI 增发/解锁数据；若有解锁按无对价稀释注记（待 M1 补）",
    }
    net_income = {
        "net_income_usd_365d": None,
        "operating_cost_usd_365d": None,
        "calculation_note": "协议收入不可得 → 净利 null（禁止编造）",
    }

    # ── 股东回报（L3）：双引擎回购（判定书 4-6%）────────────────
    # DefiLlama dailyHoldersRevenue 365d ≈ $16.7M（本地 tev-records，落在 $16-24M 区间）
    returns = tev_records.get("summary", {}).get("total_tev_usd")
    returns = round(returns, 2) if returns is not None else None
    returns_yield = round(returns / mcap * 100, 4) if (returns is not None and mcap) else None

    # 口径修正（Boss 2026-08-04）：双引擎回购后分发给 sETHFI 质押者 = 股息（真金白银进持币人口袋）
    # 非回购销毁 → type=yield（股息率）；DAO $50M 公开市场回购保留 buyback 但 usd=None 不计入
    by_mechanism = [
        {
            "mechanism": "提现费 100% 周度回购 → sETHFI 质押者",
            "type": "yield",
            "usd_365d": returns,
            "yield_percent": returns_yield,
            "note": "DefiLlama dailyHoldersRevenue 365d 合计口径（含协议收入 25% 月度回购），无单引擎拆分；回购即分发=股息口径",
        },
        {
            "mechanism": "协议收入 25% 月度回购 → sETHFI 质押者",
            "type": "yield",
            "usd_365d": None,
            "yield_percent": None,
            "note": "已含于上一条合计口径",
        },
        {
            "mechanism": "DAO $50M 公开市场回购",
            "type": "buyback",
            "usd_365d": None,
            "yield_percent": None,
            "note": "unverified（执行进度透明度一般），不计入股东回报",
        },
    ]
    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": {
            "destroy_usd_365d": None,
            "yield_usd_365d": returns,
            "destroy_yield_percent": None,
            "yield_yield_percent": returns_yield,
            "shareholder_returns_usd_365d": returns,
            "shareholder_yield_percent": returns_yield,
        },
    }

    # ── 派生估值（L4）──────────────────────────────────────────
    pe = round(mcap / returns, 4) if (mcap and returns) else None
    ps = None  # 收入不可得
    valuation = {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": None}

    margins = {
        "gross_margin_percent": None,
        "net_margin_percent": None,
        "note": "收入/毛利不可得 → 利润率 null",
    }

    sethfi_365d = validation.get("sethfi_inflow_365d_ethfi")
    sethfi_upper = validation.get("sethfi_inflow_365d_usd_upper")

    return {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": {
            "revenue": {
                "entity_type": "app",
                "revenue_included": revenue_included,
                "revenue_excluded": {
                    "dao_50m_buyback": {
                        "note": "DAO $50M 公开市场回购执行进度透明度一般（unverified），不计入",
                    }
                },
                "growth_yoy_percent": None,
                "source": {
                    "type": "official",
                    "url": "Token Terminal / Dune + 官方 + tokenomics.com（本地未缓存协议收入）",
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
            "method": "DefiLlama dailyHoldersRevenue 365d ≈ $"
            + str(returns)
            + "（tev-records 缓存，判定书 4-6% 区间：$16-24M ÷ 市值 ~$400M）；sETHFI 入金上界 "
            + str(sethfi_upper)
            + " USD（"
            + str(sethfi_365d)
            + " ETHFI，含用户 stake 不可分离，仅监控）",
            "status": "estimated",
            "last_checked": date.today().isoformat(),
        },
    }


if __name__ == "__main__":
    snap = build_snapshot(BASE_DIR / "data" / "protocols" / "etherfi")
    print(json.dumps(snap, indent=2, ensure_ascii=False))
