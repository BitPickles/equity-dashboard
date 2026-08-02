#!/usr/bin/env python3
"""
fetch-protocol-history.py — M2 协议历史数据生成（通用版）

数据源：DefiLlama /summary/fees/{id}?dataType=dailyRevenue（免费、无 key、几千天历史）

对每个协议：
1. 拉 DefiLlama 每日收入历史（≥ 730 天，保证 TTM 窗口足够）
2. 计算：每日单期值（daily_value）= 当日收入；TTM 累计总量（net_income）
   = 滚动 365 天窗口和（每天加新增一期、减掉超一年那期）
3. 派生 pe/ps/shareholder_yield/net_margin（用 snapshot 的市值）
4. 写入 data/history/<pid>.json（与 BNB 同结构，前端直接消费）

用法：
  python scripts/fetch-protocol-history.py --all
  python scripts/fetch-protocol-history.py aave pendle
"""

import argparse
import json
import sys
import urllib.request
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
HISTORY_DIR = BASE / "data" / "history"
SNAP_DIR = BASE / "data" / "snapshots"

# 协议 → DefiLlama fees id（需人工确认一次）
DEFILLAMA_IDS = {
    "aave": "aave",
    "hyperliquid": "hyperliquid",
    "sky": "sky",
    "uniswap": "uniswap",
    "pendle": "pendle",
    "curve": "curve-dex",       # DefiLlama 用 curve-dex
    "dydx": "dydx",
    "gmx": "gmx",
    "etherfi": "ether.fi",      # DefiLlama 用 ether.fi
    # aster 在 DefiLlama 无 fee 面板 → 保留 4 条周期回填
}


def fetch_daily_revenue(pid):
    """拉 DefiLlama dailyRevenue 历史，返回 [(timestamp, revenue_usd), ...] 升序。"""
    dl_id = DEFILLAMA_IDS.get(pid)
    if not dl_id:
        return None
    url = f"https://api.llama.fi/summary/fees/{dl_id}?dataType=dailyRevenue"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"    ⚠ {pid}: DefiLlama 拉取失败 {e}")
        return None
    chart = d.get("totalDataChart", [])
    if not chart:
        print(f"    ⚠ {pid}: totalDataChart 为空")
        return None
    return [(ts, rev) for ts, rev in chart if rev is not None]


def build_history(pid, daily_rev, snap):
    """由每日收入序列 + snapshot 计算 TTM 历史。"""
    mcap = (snap.get("balance_sheet") or {}).get("market_cap_usd")
    records = []
    cumulative = 0.0
    # 归一化：末端对齐 snapshot 的 net_income（口径一致，避免 TTM 与损益表差）
    snap_net = (snap.get("income_statement") or {}).get("net_income", {}).get("net_income_usd_365d")
    # 先按原始收入算 TTM，再末端归一化
    revs = [r for _, r in daily_rev]
    dates = [datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") for ts, _ in daily_rev]
    window = 365
    raw_ttm = []
    for i in range(len(revs)):
        start = max(0, i - window + 1)
        wsum = sum(revs[start:i + 1])
        days_in = min(i + 1, window)
        raw_ttm.append(wsum * 365 / days_in)
    # 归一化系数：末端 raw_ttm 对齐 snap_net
    k = 1.0
    if snap_net and raw_ttm and raw_ttm[-1] > 0:
        k = snap_net / raw_ttm[-1]
    for i in range(len(revs)):
        date_str = dates[i]
        daily_value = revs[i] * k
        cumulative += daily_value
        ttm = raw_ttm[i] * k
        pe = mcap / ttm if (mcap and ttm > 0) else None
        ps = mcap / ttm if (mcap and ttm > 0) else None  # 近似（平台币 P/S=PE）
        shr_yield = ttm / mcap * 100 if (mcap and ttm > 0) else None
        net_margin = (snap.get("income_statement") or {}).get("margins", {}).get("net_margin_percent")
        records.append({
            "as_of": date_str,
            "net_income": round(ttm, 2),          # TTM 累计总量（折线）
            "daily_value": round(daily_value, 2),  # 单日值（柱状）
            "pe": round(pe, 3) if pe else None,
            "ps": round(ps, 3) if ps else None,
            "shareholder_yield": round(shr_yield, 4) if shr_yield else None,
            "net_margin": net_margin,
            "_period": "daily",
        })
    # 末端补 snapshot 点（保证最新值 = 损益表）
    snap_as_of = snap.get("as_of")
    if snap_as_of and records and snap_as_of > records[-1]["as_of"]:
        last = records[-1]
        records.append({
            "as_of": snap_as_of,
            "net_income": snap_net if snap_net else last["net_income"],
            "daily_value": last["daily_value"],
            "pe": (snap.get("valuation") or {}).get("pe"),
            "ps": (snap.get("valuation") or {}).get("ps"),
            "shareholder_yield": (snap.get("holder_returns") or {}).get("summary", {}).get("shareholder_yield_percent"),
            "net_margin": net_margin,
            "_period": "snapshot",
        })
    return {"protocol": pid, "records": records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("protocols", nargs="*", help="协议 id；默认全部（有 DefiLlama id 的）")
    parser.add_argument("--all", action="store_true", help="全部")
    args = parser.parse_args()
    HISTORY_DIR.mkdir(exist_ok=True)
    protos = args.protocols or list(DEFILLAMA_IDS.keys())
    ok = fail = 0
    for pid in protos:
        print(f"处理 {pid} ...")
        snap = None
        sf = SNAP_DIR / f"{pid}.json"
        if sf.exists():
            snap = json.loads(sf.read_text(encoding="utf-8"))
        daily = fetch_daily_revenue(pid)
        if not daily:
            fail += 1
            continue
        hist = build_history(pid, daily, snap or {})
        (HISTORY_DIR / f"{pid}.json").write_text(
            json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        n = len(hist["records"])
        print(f"  ✓ {pid}: {n} 条历史（{hist['records'][0]['as_of']} ~ {hist['records'][-1]['as_of']}）")
        ok += 1
        time.sleep(1.1)  # 限流保护
    print(f"\n完成: {ok} ok, {fail} fail")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())