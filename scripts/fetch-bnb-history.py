#!/usr/bin/env python3
"""
fetch-bnb-history.py — BNB 真实历史数据生成

用 BNB 自身数据展开为每日历史：
- BEP-95 每日真实销毁（506 天）
- Auto-Burn 季度展开为日均
- aBNB APY 6.87% 固定
- mcap/price 取最新值（无日历史）

输出 data/history/bnb.json（覆盖现有 4 行周期回填）
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
HISTORY_DIR = DATA_DIR / "history"


def fetch_bnb_history():
    bep95 = json.loads((DATA_DIR / "protocols/bnb/bep95-history.json").read_text(encoding="utf-8"))
    burn = json.loads((DATA_DIR / "protocols/bnb/burn-history.json").read_text(encoding="utf-8"))
    snap = json.loads((DATA_DIR / "snapshots/bnb.json").read_text(encoding="utf-8"))
    latest = json.loads((DATA_DIR / "daily/bnb/latest.json").read_text(encoding="utf-8"))

    mcap = snap["balance_sheet"]["market_cap_usd"]
    price = mcap / 136357344  # BNB 流通量 ~136M
    asbnb_apy = burn.get("asbnb_apy_percent", 6.87) / 100

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
        staking_usd = mcap * asbnb_apy / 365
        daily_revenue.append((date_str, burn_usd + staking_usd))

    # 按 365d 滚动窗口计算
    records = []
    window = 365
    for i, (date_str, day_rev) in enumerate(daily_revenue):
        # 滚动窗口起点（往前 365 天）
        start = max(0, i - window + 1)
        window_sum = sum(r for _, r in daily_revenue[start:i + 1])
        # 折算年化（窗口不满 365 天按实际天数）
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

    # 今日：latest record（覆盖最后一天 + 增加 365d 真实值）
    as_of = snap.get("as_of") or datetime.now().strftime("%Y-%m-%d")
    today_inc = snap["income_statement"]
    today_hr = snap["holder_returns"]["summary"]
    records.append({
        "as_of": as_of,
        "net_income": today_inc["net_income"]["net_income_usd_365d"],
        "pe": snap["valuation"]["pe"],
        "ps": snap["valuation"]["ps"],
        "shareholder_yield": today_hr["shareholder_yield_percent"],
        "net_margin": today_inc["margins"]["net_margin_percent"],
        "_period": "snapshot",
    })
    # 去重 + 排序
    seen = set()
    unique = []
    for r in sorted(records, key=lambda x: x["as_of"]):
        if r["as_of"] not in seen:
            unique.append(r)
            seen.add(r["as_of"])
    return {"protocol": "bnb", "records": unique}


def main():
    out = fetch_bnb_history()
    HISTORY_DIR.mkdir(exist_ok=True)
    (HISTORY_DIR / "bnb.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"✅ BNB 历史已写入: {len(out['records'])} 条（{out['records'][0]['as_of']} ~ {out['records'][-1]['as_of']}）")


if __name__ == "__main__":
    main()