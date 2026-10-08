#!/usr/bin/env python3
"""
sync-all-protocols-from-snapshots.py — 从 27 个 snapshot 同步 all-protocols.json

背景（Boss 2026-08-04 反馈）：主表排名靠后协议 Revenue/Net Income 空。
根因：all-protocols.json 生成于 08-02 14:47（M2/M3 之前），14 个协议 yield 过时
（如 bgb 0 vs snapshot 27.54%），且 revenue/net_income 缺失。

本脚本以 snapshot 为权威源（M2/M3 adapter 产出），覆盖 all-protocols.json 的：
- shareholder_yield_percent        ← holder_returns.summary.shareholder_yield_percent
- total_yield_percent    ← destroy_yield_percent + yield_yield_percent（总收益型）
- dividend_yield_percent   ← summary.yield_yield_percent
- buyback_yield_percent    ← summary.destroy_yield_percent
- revenue_usd_365d         ← income_statement.revenue.revenue_included.total_usd_365d
- gross_profit_usd_365d    ← income_statement.gross_profit.gross_profit_usd_365d
- net_income_usd_365d      ← income_statement.net_income.net_income_usd_365d
- net_margin_percent       ← income_statement.margins.net_margin_percent
- payout_ratio (payout_ratio)  ← valuation.payout_ratio（若有）
- ⚠️ market_cap_usd / tvl **不覆盖**——由 update-prices.py（CoinGecko/CMC 实时）维护
- metrics.shareholder_yield_365d_ann ← 同上（保持兼容）

用法: python3 scripts/sync-all-protocols-from-snapshots.py [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ALL_FILE = BASE / "data" / "all-protocols.json"
SNAP_DIR = BASE / "data" / "snapshots"

if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
from scripts.lib.period_metrics import annualize_factor as _ann_factor  # noqa: E402


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

        rev_incl = (inc.get("revenue", {}) or {}).get("revenue_included", {}) or {}
        gp = inc.get("gross_profit", {}) or {}
        ni = inc.get("net_income", {}) or {}
        mg = inc.get("margins", {}) or {}

        updates = {
            "shareholder_yield_percent": hr.get("shareholder_yield_percent"),
            "dividend_yield_percent": hr.get("yield_yield_percent"),
            "buyback_yield_percent": hr.get("destroy_yield_percent"),
            "revenue_usd_365d": rev_incl.get("total_usd_365d"),
            "gross_profit_usd_365d": gp.get("gross_profit_usd_365d"),
            "net_income_usd_365d": ni.get("net_income_usd_365d"),
            "net_margin_percent": mg.get("net_margin_percent"),
            # ⚠️ market_cap_usd / tvl 不从此同步——由 update-prices.py（CoinGecko/CMC
            #    实时）维护；snapshot 的市值是 build 时的旧快照，覆盖会回退价格（2026-08-04 bug）
        }
        # total_yield_percent（Earning Yield / 收入收益率）= 年化收入 ÷ 最新市值
        # —— P/S 列的分母（PS = 100 ÷ total_yield）。用 update-prices 维护的最新市值，
        #    不用 snapshot 旧市值（2026-08-05 清洗旧残留值）
        rev = updates.get("revenue_usd_365d")
        mcap = p.get("market_cap_usd")  # all-protocols 最新市值（update-prices 维护）
        if rev is not None and mcap:
            updates["total_yield_percent"] = round(rev / mcap * 100, 4)
        elif "total_yield_percent" in p:
            # 收入不可得 → 删除旧残留，避免展示过期数字
            updates["total_yield_percent"] = None
        # payout_ratio：snapshot 有就用（可能为 None 保留原值）
        if val.get("payout_ratio") is not None:
            updates["payout_ratio"] = val["payout_ratio"]

        # metrics 兼容（前端 yieldMap 读 metrics.shareholder_yield_365d_ann）
        metrics = p.setdefault("metrics", {})
        if hr.get("shareholder_yield_percent") is not None:
            metrics["shareholder_yield_365d_ann"] = hr["shareholder_yield_percent"]

        # ── 多周期（by_period，阶段1 试点）─────────────────────────────
        # 口径由 adapter 定义一次（holder_returns.by_period），此处只做机械派生，
        # 令前端 4 个周期 tab（读 metrics.*_{7,30,90}d_ann）与 365D 同源。
        # 仅对已产出 by_period 的协议生效；其余协议保持原状（阶段2 批量迁移）。
        bp = snap.get("holder_returns", {}).get("by_period")
        if isinstance(bp, dict):
            _mcap = p.get("market_cap_usd")   # 用 update-prices 维护的最新市值年化
            for n in (7, 30, 90, 365):
                blk = bp.get(f"{n}d") or {}
                _ru = blk.get("shareholder_returns_usd")
                _rev = blk.get("revenue_usd")
                if _mcap and _rev:
                    metrics[f"total_yield_{n}d_ann"] = round(_rev / _mcap * 100 * _ann_factor(n), 4)
                if _ru is None or not _mcap:
                    continue
                metrics[f"shareholder_yield_{n}d_ann"] = round(_ru / _mcap * 100 * _ann_factor(n), 4)
                _by = blk.get("destroy_usd")
                if _by is not None:
                    metrics[f"buyback_yield_{n}d_ann"] = round(_by / _mcap * 100 * _ann_factor(n), 4)
                _dv = blk.get("yield_usd")
                if _dv is not None:
                    metrics[f"dividend_yield_{n}d_ann"] = round(_dv / _mcap * 100 * _ann_factor(n), 4)
                metrics[f"trailing_{n}d_shareholder_returns_usd"] = round(_ru, 2)
                if _rev:
                    p[f"payout_ratio_{n}d"] = round(_ru / _rev, 4)

        for k, v in updates.items():
            if k in ("payout_ratio",):
                if v is not None:
                    p[k] = v
                continue
            p[k] = v  # None 也覆盖（避免残留旧值误导）

        # 兼容旧消费者的嵌套财务快照也必须与当前 snapshot 同步。
        # 否则主表已经更新、嵌套对象仍停在 08-02，会造成同一协议两套 TTM。
        legacy_financial = p.get("financial_snapshot")
        if isinstance(legacy_financial, dict):
            legacy_financial.update({
                "revenue_usd_365d": rev_incl.get("total_usd_365d"),
                "gross_profit_usd_365d": gp.get("gross_profit_usd_365d"),
                "net_income_usd_365d": ni.get("net_income_usd_365d"),
                "gross_margin_percent": mg.get("gross_margin_percent"),
                "net_margin_percent": mg.get("net_margin_percent"),
                "pe": val.get("pe"),
                "ps": val.get("ps"),
                "payout_ratio": val.get("payout_ratio"),
                "shareholder_returns_usd_365d": hr.get("shareholder_returns_usd_365d"),
                "as_of": snap.get("as_of"),
            })

        updated += 1
        if args.dry_run:
            print(f"  [DRY] {pid}: yld={p.get('shareholder_yield_percent')} rev={p.get('revenue_usd_365d')} net={p.get('net_income_usd_365d')}")

    if args.dry_run:
        print(f"\n[DRY] 将更新 {updated} 个协议（未写文件）")
        return 0

    allp["generated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    ALL_FILE.write_text(json.dumps(allp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ 已从 {updated} 个 snapshot 同步 all-protocols.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
