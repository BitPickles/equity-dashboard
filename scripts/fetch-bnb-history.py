#!/usr/bin/env python3
"""
fetch-bnb-history.py — BNB 真实历史数据生成

用 BNB 自身数据展开为每日历史（统一口径，避免双口径突跳）：
- BEP-95 每日真实销毁（506 天）
- Auto-Burn 季度展开为日均
- aBNB APY：取 snapshot 最新股东回报率反推的当前 APY（与 365d 口径一致）
- 滚动 365d 窗口计算 net_income/PE/PS/股东回报率
- mcap/price 取最新值（无日历史）

输出 data/history/bnb.json（覆盖旧序列）
"""

import json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
HISTORY_DIR = DATA_DIR / "history"


def fetch_bnb_history():
    bep95 = json.loads((DATA_DIR / "protocols/bnb/bep95-history.json").read_text(encoding="utf-8"))
    burn = json.loads((DATA_DIR / "protocols/bnb/burn-history.json").read_text(encoding="utf-8"))
    snap = json.loads((DATA_DIR / "snapshots/bnb.json").read_text(encoding="utf-8"))

    mcap = snap["balance_sheet"]["market_cap_usd"]
    price = mcap / 136357344  # BNB 流通量 ~136M

    # aBNB APY：用 snapshot 的 365d 收入倒推（burn 用最新值，剩余为 staking APY）
    inc = snap["income_statement"]["revenue"]["revenue_included"]
    burn_365d = inc.get("burn_usd_365d") or 0
    staking_365d = inc.get("staking_rewards_usd_365d") or 0
    total_365d = (inc.get("total_usd_365d") or burn_365d + staking_365d)
    # 平均日 burn（用历史数据估算，避免未来 burn 反推历史）
    burn_avg_daily = burn_365d / 365
    staking_apy = (staking_365d / mcap * 100) if mcap > 0 else 6.87  # 当前 aBNB APY ~12.46%

    # 季度 burn → map[date_str] = bnb
    burn_by_q = {}
    for q in burn.get("quarterly_burns", []):
        burn_by_q[q["date"][:7]] = q["bnb_burned"]

    # 每天: bep95_bnb(usd) + 季度 burn 日均(usd) + aBNB APY
    # 用滚动 365d 窗口计算 net_income/PE，避免日波动
    daily = bep95.get("daily", [])
    daily_revenue = []  # [(date_str, revenue_usd)]
    for d in daily:
        date_str = d["date"]
        bep95_bnb = d.get("bnb", 0)
        ym = date_str[:7]
        quarter_bnb = burn_by_q.get(ym, 0) / 90
        burn_usd = (bep95_bnb + quarter_bnb) * price
        staking_usd = mcap * staking_apy / 365 / 100
        daily_revenue.append((date_str, burn_usd + staking_usd))

    # 按 365d 滚动窗口计算（统一口径，末端不叠加 snapshot）
    records = []
    window = 365
    for i, (date_str, day_rev) in enumerate(daily_revenue):
        start = max(0, i - window + 1)
        window_sum = sum(r for _, r in daily_revenue[start:i + 1])
        days_in_window = min(i + 1, window)
        annualized_rev = window_sum * 365 / days_in_window
        net_income_usd = annualized_rev  # 平台币无成本
        pe = mcap / annualized_rev if annualized_rev > 0 else None
        ps = pe
        shr_yield = annualized_rev / mcap * 100 if mcap > 0 else None
        net_margin = 100.0
        records.append({
            "as_of": date_str,
            "net_income": round(net_income_usd, 2),
            "pe": round(pe, 3) if pe else None,
            "ps": round(ps, 3) if ps else None,
            "shareholder_yield": round(shr_yield, 4) if shr_yield else None,
            "net_margin": net_margin,
            "_period": "daily",
        })

    # 归一化：让 daily 序列末端与 snapshot 365d 值对齐（消除口径 gap，无缝衔接）
    # k = snapshot_365d / daily_最后一天_年化；整个 daily 序列乘 k（趋势形状不变）
    snap_net = snap["income_statement"]["net_income"]["net_income_usd_365d"]
    if records:
        last_daily = records[-1]["net_income"]
        if last_daily and snap_net and last_daily > 0:
            k = snap_net / last_daily
            for r in records:
                r["net_income"] = round(r["net_income"] * k, 2)
                r["pe"] = round(mcap / r["net_income"], 3) if r["net_income"] > 0 else None
                r["ps"] = r["pe"]
                r["shareholder_yield"] = round(r["net_income"] / mcap * 100, 4) if mcap > 0 else None
            print(f"  ↳ 归一化系数 k={k:.3f}（daily 末端对齐 snapshot 365d）")

    # 末端衔接 snapshot 365d 值（最后一条真实数据点，与详情页损益表一致）
    # 用 snapshot 的 as_of 作为日期；如果与 daily 最后一天同一天则跳过（避免重复）
    snap_as_of = snap.get("as_of")
    if snap_as_of and snap_as_of > records[-1]["as_of"]:
        records.append({
            "as_of": snap_as_of,
            "net_income": snap_net,
            "pe": snap["valuation"]["pe"],
            "ps": snap["valuation"]["ps"],
            "shareholder_yield": snap["holder_returns"]["summary"]["shareholder_yield_percent"],
            "net_margin": snap["income_statement"]["margins"]["net_margin_percent"],
            "_period": "snapshot",
        })

    return {"protocol": "bnb", "records": records}


def main():
    out = fetch_bnb_history()
    HISTORY_DIR.mkdir(exist_ok=True)
    (HISTORY_DIR / "bnb.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"✅ BNB 历史已写入: {len(out['records'])} 条（{out['records'][0]['as_of']} ~ {out['records'][-1]['as_of']}）")


if __name__ == "__main__":
    main()