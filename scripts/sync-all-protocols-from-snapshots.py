#!/usr/bin/env python3
"""
sync-all-protocols-from-snapshots.py — 从 27 个 snapshot 同步 all-protocols.json

背景（Boss 2026-08-04 反馈）：主表排名靠后协议 Revenue/Net Income 空。
根因：all-protocols.json 生成于 08-02 14:47（M2/M3 之前），14 个协议 yield 过时
（如 bgb 0 vs snapshot 27.54%），且 revenue/net_income 缺失。

本脚本以 snapshot 为权威源（M2/M3 adapter 产出），覆盖 all-protocols.json 的：
- tev_yield_percent        ← holder_returns.summary.shareholder_yield_percent
- earning_yield_percent    ← destroy_yield_percent + yield_yield_percent（总收益型）
- dividend_yield_percent   ← summary.yield_yield_percent
- buyback_yield_percent    ← summary.destroy_yield_percent
- revenue_usd_365d         ← income_statement.revenue.revenue_included.total_usd_365d
- gross_profit_usd_365d    ← income_statement.gross_profit.gross_profit_usd_365d
- net_income_usd_365d      ← income_statement.net_income.net_income_usd_365d
- net_margin_percent       ← income_statement.margins.net_margin_percent
- payout_ratio (tevRatio)  ← valuation.payout_ratio（若有）
- market_cap_usd / tvl     ← balance_sheet
- metrics.tev_yield_365d_ann ← 同上（保持兼容）

用法: python3 scripts/sync-all-protocols-from-snapshots.py [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ALL_FILE = BASE / "data" / "all-protocols.json"
SNAP_DIR = BASE / "data" / "snapshots"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    allp = json.loads(ALL_FILE.read_text(encoding="utf-8"))
    protocols = allp.setdefault("protocols", {})
    snap_files = sorted(SNAP_DIR.glob("*.json"))
    updated = 0
    for sf in snap_files:
        pid = sf.stem
        # 跳过镜像（hype 用 hyperliquid 数据，主 key 是 hype）
        if pid not in protocols:
            continue
        snap = json.loads(sf.read_text(encoding="utf-8"))
        p = protocols[pid]

        hr = snap.get("holder_returns", {}).get("summary", {})
        inc = snap.get("income_statement", {})
        val = snap.get("valuation", {})
        bs = snap.get("balance_sheet", {})

        rev_incl = (inc.get("revenue", {}) or {}).get("revenue_included", {}) or {}
        gp = inc.get("gross_profit", {}) or {}
        ni = inc.get("net_income", {}) or {}
        mg = inc.get("margins", {}) or {}

        updates = {
            "tev_yield_percent": hr.get("shareholder_yield_percent"),
            "dividend_yield_percent": hr.get("yield_yield_percent"),
            "buyback_yield_percent": hr.get("destroy_yield_percent"),
            "revenue_usd_365d": rev_incl.get("total_usd_365d"),
            "gross_profit_usd_365d": gp.get("gross_profit_usd_365d"),
            "net_income_usd_365d": ni.get("net_income_usd_365d"),
            "net_margin_percent": mg.get("net_margin_percent"),
            "market_cap_usd": bs.get("market_cap_usd"),
            "tvl": bs.get("tvl_usd"),
        }
        # payout_ratio：snapshot 有就用（可能为 None 保留原值）
        if val.get("payout_ratio") is not None:
            updates["tevRatio"] = val["payout_ratio"]

        # metrics 兼容（前端 yieldMap 读 metrics.tev_yield_365d_ann）
        metrics = p.setdefault("metrics", {})
        if hr.get("shareholder_yield_percent") is not None:
            metrics["tev_yield_365d_ann"] = hr["shareholder_yield_percent"]

        for k, v in updates.items():
            if k in ("tevRatio",):
                if v is not None:
                    p[k] = v
                continue
            p[k] = v  # None 也覆盖（避免残留旧值误导）

        updated += 1
        if args.dry_run:
            print(f"  [DRY] {pid}: yld={p.get('tev_yield_percent')} rev={p.get('revenue_usd_365d')} net={p.get('net_income_usd_365d')}")

    if args.dry_run:
        print(f"\n[DRY] 将更新 {updated} 个协议（未写文件）")
        return 0

    allp["generated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    ALL_FILE.write_text(json.dumps(allp, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 已从 {updated} 个 snapshot 同步 all-protocols.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
