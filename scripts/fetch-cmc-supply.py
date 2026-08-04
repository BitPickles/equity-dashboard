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

# 协议 → CMC slug（CoinMarketCap 币种标识，2026-08-02 实测校正）
# 优先用 config.json 里已有的 cmcSlug；此处为兜底映射
CMC_SLUGS = {
    "aave": "aave", "aster": "aster", "bgb": "bitget-token-new", "bnb": "bnb",
    "compound": "compound", "curve": "curve-dao-token", "dydx": "dydx-chain",
    "eigenlayer": "eigenlayer", "ethena": "ethena",
    "fluid": "instadapp", "gmx": "gmx", "hype": "hyperliquid",
    "jito": "jito", "justlend": "just", "kamino": "kamino-finance",
    "layerzero": "layerzero", "lido": "lido-dao", "maple": "maple-finance",
    "mnt": "mantle", "morpho": "morpho", "okb": "okb",
    "pancakeswap": "pancakeswap", "pendle": "pendle", "sky": "sky",
    "spark": "spark", "uniswap": "uniswap",
}


def load_dotenv():
    """从仓库根 .env 读取 CMC_API_KEY（Mac Mini 部署：放置 .env 即可，无需手设环境变量）。
    注意：.env 已被 .gitignore 忽略，严禁提交到 GitHub。"""
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def get_api_key():
    load_dotenv()
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


def fetch_historical(pid, slug, symbol, api_key, days=90):
    """拉 CMC historical quotes（v2）→ 近 days 天每日流通量序列。
    返回 [(date_str, supply), ...] 或 None。"""
    from datetime import datetime, timedelta
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    url = ("https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical"
           f"?symbol={symbol}&time_start={start.strftime('%Y-%m-%d')}"
           f"&time_end={end.strftime('%Y-%m-%d')}&interval=daily")
    req = urllib.request.Request(url, headers={
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.loads(r.read().decode("utf-8"))
        data = d.get("data", {})
        # data 可能是 { 'SYM': [ {...}, ... ] } 或 { 'SYM': {...} }
        entries = data.get(symbol, [])
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list) or not entries:
            return None
        # 选 id 对应的条目：优先取 circulating_supply 非空的
        best = None
        for e in entries:
            quotes = e.get("quotes", [])
            if quotes and quotes[-1].get("quote", {}).get("USD", {}).get("circulating_supply"):
                best = e
                break
        if best is None:
            best = entries[0]
        quotes = best.get("quotes", [])
        points = []
        for q in quotes:
            ts = q.get("timestamp", "")[:10]
            supply = q.get("quote", {}).get("USD", {}).get("circulating_supply")
            if ts and supply is not None:
                points.append({"date": ts, "circulating_supply": supply})
        return points if points else None
    except urllib.error.HTTPError as e:
        print(f"    ⚠ CMC {pid} historical: HTTP {e.code}")
        return None
    except Exception as e:
        print(f"    ⚠ CMC {pid} historical: {e}")
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
    parser.add_argument("--days", type=int, default=365, help="历史流通量回溯天数（默认 365=12 个月，CMC 免费层上限）")
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
            sym = info.get("symbol")
            # 优先拉历史序列（90 天）→ 流通量曲线有完整走势；失败则落单点
            hist = fetch_historical(pid, slug, sym, api_key, days=args.days)
            if hist and len(hist) > 1:
                data = {"protocol": pid, "symbol": sym, "source": "CoinMarketCap",
                        "updated_at": datetime.now(timezone.utc).isoformat(), "points": hist}
                SUPPLY_DIR.mkdir(exist_ok=True)
                (SUPPLY_DIR / f"{pid}.json").write_text(
                    json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"  ✓ {pid}: {len(hist)} 天历史流通量 {hist[0]['circulating_supply']:,.0f} → {hist[-1]['circulating_supply']:,.0f} ({sym})")
            else:
                append_point(pid, info, today)
                print(f"  ✓ {pid}: {info['circulating_supply']:,.0f} ({sym}) [单点]")
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
