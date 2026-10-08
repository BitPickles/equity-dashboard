#!/usr/bin/env python3
"""
sync-holders-revenue.py — 每日刷新 DefiLlama 收入 / 持有人收入合计到 all-protocols.json

【背景 / 根因】
data/protocols/<id>/adapter.py 读的是 data/all-protocols.json 的
  metrics.trailing_{7,30,90,365}d_revenue_usd
  validation.holders_* / burn_* 等
但自 2026-08 起，这些字段**已无任何脚本重算**（旧 sync-tev-data.js 已停用），
导致适配器长期用 08-02 的旧输入产出旧快照 —— 即"机制数据冻结在 08-02"。

【本脚本做什么】
对每个有 DefiLlama slug 的协议，拉取 summary/fees/<slug> 的逐日序列，
计算 7/30/90/365 天合计，写回 all-protocols.json：
  metrics.trailing_{7,30,90,365}d_revenue_usd          ← dailyRevenue
  metrics.trailing_{30,90,365}d_holders_revenue_usd    ← dailyHoldersRevenue
  validation.holders_{30,90,365}d_usd                  ← dailyHoldersRevenue（供适配器/校验）
数据源不可得（平台币 / 无 DefiLlama fee 面板）的协议**跳过并保留原值**，不写 0。

用法:
  python3 scripts/sync-holders-revenue.py [--dry-run] [--protocol sky aave ...]
"""
import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ALL_FILE = BASE / "data" / "all-protocols.json"
PROTO_DIR = BASE / "data" / "protocols"
API = "https://api.llama.fi/summary/fees/{slug}?dataType={dt}"
PERIODS = [7, 30, 90, 365]

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _http_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40, context=_CTX) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def trailing_sums(chart):
    """chart: [[ts, val], ...] → {N: sum of last N days} for PERIODS。"""
    pairs = [(int(ts), float(v or 0)) for ts, v in (chart or [])]
    if not pairs:
        return {}
    last = max(ts for ts, _ in pairs)
    out = {}
    for n in PERIODS:
        cutoff = last - n * 86400
        out[n] = sum(v for ts, v in pairs if ts > cutoff)
    return out


def get_slug(pid):
    cfg = PROTO_DIR / pid / "config.json"
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    slug = (data.get("token") or {}).get("defillama_id") or data.get("defillama_slug")
    return slug or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--protocol", nargs="*", default=None)
    args = ap.parse_args()

    allp = json.loads(ALL_FILE.read_text(encoding="utf-8"))
    protocols = allp.get("protocols", {})
    targets = args.protocol or sorted(protocols.keys())

    updated, skipped, failed = 0, 0, 0
    for pid in targets:
        if pid not in protocols:
            continue
        slug = get_slug(pid)
        if not slug:
            skipped += 1
            print(f"  - {pid:14} 无 DefiLlama slug，跳过（保留原值）")
            continue
        try:
            rev = _http_json(API.format(slug=slug, dt="dailyRevenue"))
            hol = _http_json(API.format(slug=slug, dt="dailyHoldersRevenue"))
        except urllib.error.HTTPError as e:
            failed += 1
            print(f"  ! {pid:14} HTTP {e.code}，保留原值")
            continue
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ! {pid:14} 失败 {e}，保留原值")
            continue

        rev_sum = trailing_sums(rev.get("totalDataChart"))
        hol_sum = trailing_sums(hol.get("totalDataChart"))
        if not rev_sum:
            failed += 1
            print(f"  ! {pid:14} 收入序列为空，保留原值")
            continue

        p = protocols[pid]
        m = p.setdefault("metrics", {})
        v = p.setdefault("validation", {})
        for n, val in rev_sum.items():
            m[f"trailing_{n}d_revenue_usd"] = round(val, 2)
        for n in (30, 90, 365):
            if n in hol_sum:
                m[f"trailing_{n}d_holders_revenue_usd"] = round(hol_sum[n], 2)
                v[f"holders_{n}d_usd"] = round(hol_sum[n], 2)
        m["revenue_source"] = "defillama_dailyRevenue"
        m["holders_revenue_source"] = "defillama_dailyHoldersRevenue"
        updated += 1
        tag = "DRY " if args.dry_run else ""
        print(f"  {tag}✓ {pid:14} rev365={rev_sum.get(365, 0):>15,.0f}  holders365={hol_sum.get(365, 0):>15,.0f}")

    print(f"\n同步完成：更新 {updated} / 跳过 {skipped} / 失败 {failed}")
    if args.dry_run:
        print("[DRY] 未写文件")
        return 0
    ALL_FILE.write_text(json.dumps(allp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {ALL_FILE.relative_to(BASE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
