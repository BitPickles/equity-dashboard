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

    # ── Auto-Burn 平滑：识别链上单日大额销毁（>1000 BNB，= Auto-Burn 执行日）──
    # BEP-95 链上抓取会把 Auto-Burn 转账也计入（都转 0xdead），平时 BEP-95 每天只有几百 BNB，
    # 单日 >1000 BNB 即为季度 Auto-Burn 执行日。把该日金额均摊到「上次执行日 → 本次执行日」
    # 之间的每一天，消除单日巨峰（2026-07-16 的 161.6 万 BNB 就属于这种情况）。
    daily = bep95.get("daily", [])
    AUTO_BURN_THRESHOLD = 1000  # BNB
    # 找出所有 Auto-Burn 执行日（含 burn-history 公告的 + 链上抓到的）
    exec_days = []  # [(date_str, bnb)]
    for d in daily:
        bnb = d.get("bnb", 0)
        if bnb > AUTO_BURN_THRESHOLD:
            exec_days.append((d["date"], bnb))
    # 合并 burn-history 公告日（如果链上没抓到）
    for q in burn.get("quarterly_burns", []):
        qd = q["date"]
        if qd not in [e[0] for e in exec_days]:
            exec_days.append((qd, q["bnb_burned"]))
    exec_days.sort(key=lambda x: x[0])
    # 若没有执行日（异常），fallback 到 burn-history 的月份均摊
    if not exec_days:
        exec_days = [(q["date"], q["bnb_burned"]) for q in burn.get("quarterly_burns", [])]

    # 每天: bep95_bnb(usd，排除 Auto-Burn 执行日) + Auto-Burn 区间均摊 + aBNB APY
    # 用滚动 365d 窗口计算 net_income/PE，避免日波动
    daily_revenue = []  # [(date_str, revenue_usd)]
    exec_set = {e[0] for e in exec_days}
    # 每个执行日负责「上一个执行日(不含) → 本执行日(含)」区间的均摊
    # 均摊区间天数 = 距上一个执行日的天数
    for i, d in enumerate(daily):
        date_str = d["date"]
        bep95_bnb = d.get("bnb", 0)
        # 若当天是 Auto-Burn 执行日：从 bep95 里剔除（该金额另行均摊）
        if date_str in exec_set:
            bep95_bnb = 0
        # 找当天所属的 Auto-Burn 区间：最近的执行日 <= 当天
        recent_exec = [e for e in exec_days if e[0] <= date_str]
        if not recent_exec:
            quarter_bnb = 0  # 数据起始前无执行日
        else:
            cur_date, cur_amount = recent_exec[-1]
            # 区间天数：cur_date → 下一个执行日；若没有下一个执行日（最新一季），
            # 按季度惯例摊满 90 天（Boss 2026-08-03：Auto-Burn 按季度销毁，应摊满季度
            # 而不是只摊到数据末尾——之前只摊 18 天导致 72M 平台）
            next_dates = [e[0] for e in exec_days if e[0] > cur_date]
            if next_dates:
                end = next_dates[0]
            else:
                from datetime import timedelta
                end = (datetime.strptime(cur_date, "%Y-%m-%d") + timedelta(days=90)).strftime("%Y-%m-%d")
            span = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(cur_date, "%Y-%m-%d")).days
            span = max(span, 1)
            quarter_bnb = cur_amount / span if date_str >= cur_date else 0
            # 只在执行日当天起才均摊（执行日之前不摊）
            if date_str < cur_date:
                quarter_bnb = 0
        burn_usd = (bep95_bnb + quarter_bnb) * price
        staking_usd = mcap * staking_apy / 365 / 100
        daily_revenue.append((date_str, burn_usd + staking_usd))

    # 累计总量（TradingView 风格：折线显示累计，柱状显示单期值）
    cumulative = 0.0
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
        cumulative += day_rev
        records.append({
            "as_of": date_str,
            "net_income": round(net_income_usd, 2),
            "daily_value": round(day_rev, 2),      # 单期统计值（柱状图）
            "cumulative": round(cumulative, 2),    # 累计总量（折线图）
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
                r["daily_value"] = round(r["daily_value"] * k, 2)
                r["cumulative"] = round(r["cumulative"] * k, 2)
                r["pe"] = round(mcap / r["net_income"], 3) if r["net_income"] > 0 else None
                r["ps"] = r["pe"]
                r["shareholder_yield"] = round(r["net_income"] / mcap * 100, 4) if mcap > 0 else None
            print(f"  ↳ 归一化系数 k={k:.3f}（daily 末端对齐 snapshot 365d）")

    # 末端衔接 snapshot 365d 值（最后一条真实数据点，与详情页损益表一致）
    # 用 snapshot 的 as_of 作为日期；如果与 daily 最后一天同一天则跳过（避免重复）
    snap_as_of = snap.get("as_of")
    if snap_as_of and snap_as_of > records[-1]["as_of"]:
        # snapshot 行的 daily_value/cumulative 沿用上一条（避免突跳）
        last_dv = records[-1].get("daily_value")
        last_cum = records[-1].get("cumulative")
        records.append({
            "as_of": snap_as_of,
            "net_income": snap_net,
            "daily_value": last_dv,
            "cumulative": last_cum,
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