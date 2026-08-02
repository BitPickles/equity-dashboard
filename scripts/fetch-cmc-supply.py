#!/usr/bin/env python3
"""
fetch-cmc-supply.py — 代币流通量采集（v2.2，CMC 数据源）

每日拉取 27 协议 circulating_supply → data/supply/<pid>.json（时间序列）
历史看板「代币流通量曲线」数据源。

配置：
  环境变量 CMC_API_KEY（免费 Basic 层 15K 次/月，不入仓库）
  未配置时以 --dry-run 输出占位说明，不阻塞

用法:
  python3 scripts/fetch-cmc-supply.py               # 全量 27 协议
  python3 scripts/fetch-cmc-supply.py --protocol bnb aave
  python3 scripts/fetch-cmc-supply.py --dry-run     # 只测连接/打印计划
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SUPPLY_DIR = BASE / "data" / "supply"

# 协议 → CMC slug（CoinMarketCap 币种标识）
# 优先用 config.json 里已有的 cmcSlug；此处为兜底映射
CMC_SLUGS = {
    "aave": "aave", "aster": "aster", "bgb": "bitget-token", "bnb": "bnb",
    "compound": "compound", "curve": "curve-dao-token", "dydx": "dydx-chain",
    "eigenlayer": "eigenlayer", "ethena": "ethena", "etherfi": "ether-fi",
    "fluid": "instadapp", "gmx": "gmx", "hype": "hyperliquid",
    "jito": "jito-governance-token", "justlend": "just", "kamino": "kamino",
    "layerzero": "layerzero", "lido": "lido-dao", "maple": "syrup",
    "mnt": "mantle", "morpho": "morpho", "okb": "okb",
    "pancakeswap": "pancakeswap", "pendle": "pendle", "sky": "maker",
    "spark": "spark", "uniswap": "uniswap",
}


def get_api_key():
    return os.environ.get("CMC_API_KEY", "").strip()


def fetch_quotes(slug, api_key):
    """调 CMC /v2/cryptocurrency/quotes/latest 拿流通量。返回 (circulating_supply, symbol) 或 None。"""
    url = f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?slug={slug}"
    req = urllib.request.Request(url, headers={
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        # v2 返回 { data: { id: {...} } }
        first = next(iter(d.get("data", {}).values()), None)
        if not first:
            return None
        return {
            "circulating_supply": first.get("circulating_supply"),
            "symbol": first.get("symbol"),
            "cmc_rank": first.get("cmc_rank"),
        }
    except urllib.error.HTTPError as e:
        print(f"    ⚠ CMC {slug}: HTTP {e.code} {e.reason}")
        return None
    except Exception as e:
        print(f"    ⚠ CMC {slug}: {e}")
        return None


def append_point(pid, supply_info, today):
    """累积流通量时间序列 data/supply/<pid>.json。"""
    SUPPLY_DIR.mkdir(exist_ok=True)
    f = SUPPLY_DIR / f"{pid}.json"
    data = {}
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    points = data.get("points", [])
    # 同日去重
    points = [p for p in points if p.get("date") != today]
    points.append({"date": today, "circulating_supply": supply_info.get("circulating_supply")})
    points.sort(key=lambda p: p.get("date", ""))
    data["protocol"] = pid
    data["symbol"] = supply_info.get("symbol", "")
    data["source"] = "CoinMarketCap"
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["points"] = points[-730:]  # 最多保留 2 年
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="CMC 代币流通量采集")
    parser.add_argument("--protocol", nargs="*", help="指定协议；默认全部")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不调用 API")
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        print("⚠ 未配置 CMC_API_KEY（免费 Basic 层：pro.coinmarketcap.com 申请）")
        print("  以 --dry-run 展示计划；数据将写入 data/supply/<pid>.json")
        if not args.dry_run:
            print("  跳过 API 调用。设置 CMC_API_KEY 后重跑。")
            return 0

    protos = args.protocol or sorted(CMC_SLUGS)
    today = date.today().isoformat()
    print(f"CMC 流通量采集: {len(protos)} 协议 | {today} | key={'✓' if api_key else '✗'}")

    ok = fail = 0
    for pid in protos:
        slug = CMC_SLUGS.get(pid)
        if not slug:
            print(f"  SKIP {pid}: 无 CMC slug")
            continue
        if args.dry_run:
            print(f"  [DRY] {pid}: slug={slug}")
            continue
        info = fetch_quotes(slug, api_key)
        if info and info.get("circulating_supply") is not None:
            append_point(pid, info, today)
            print(f"  ✓ {pid}: {info['circulating_supply']:,.0f} ({info.get('symbol')})")
            ok += 1
        else:
            fail += 1
        time.sleep(1.1)  # 限流保护（50 req/min 上限，留余量）

    print(f"\n完成: {ok} ok, {fail} fail")
    if fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
