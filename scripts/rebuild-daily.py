#!/usr/bin/env python3
"""
rebuild-daily.py — M0 僵尸数据重建（data/daily/*/latest.json 停更 5 个月 → 重建）

对每个协议：调 DefiLlama summary/fees/<slug>（费用/收入）+ CoinGecko（价格/市值）
→ 重建 data/daily/<id>/latest.json（统一结构，updated_at = 今天）

用法: python3 scripts/rebuild-daily.py [--dry-run] [--protocol aave bnb ...]
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DAILY = BASE / "data" / "daily"
DRY = "--dry-run" in sys.argv

# 冗余目录（已并入规范目录，禁止重建，待删除）
EXCLUDED_DIRS = {"curve-dex", "ether.fi", "hyperliquid"}

# 协议 → (DefiLlama slug, CoinGecko id)
# 无 DefiLlama 数据（平台币/静态协议）→ slug=None，仅刷新时间戳并保留原结构
SLUGS = {
    "aave": ("aave", "aave"),
    "aster": (None, "aster-2"),
    "bgb": (None, "bitget-token"),
    "bnb": (None, "binancecoin"),
    "compound": ("compound-v3", "compound-governance-token"),
    "curve": ("curve-dex", "curve-dao-token"),
    "dydx": ("dydx", "dydx-chain"),
    "eigenlayer": ("eigenlayer", "eigenlayer"),
    "ethena": ("ethena", "ethena"),
    "gmx": ("gmx", "gmx"),
    "hype": ("hyperliquid", "hyperliquid"),
    "jito": ("jito", "jito-governance-token"),
    "justlend": ("justlend", "just"),
    "kamino": ("kamino", "kamino"),
    "lido": ("lido", "lido-dao"),
    "maple": ("maple", "syrup"),
    "mnt": (None, "mantle"),
    "morpho": ("morpho", "morpho"),
    "okb": (None, "okb"),
    "pancakeswap": ("pancakeswap", "pancakeswap-token"),
    "pendle": ("pendle", "pendle"),
    "sky": ("sky", "maker"),
    "spark": ("spark", "spark"),
    "uniswap": ("uniswap", "uniswap"),
    "fluid": ("fluid", "instadapp"),
    "layerzero": ("layerzero-v2", "layerzero"),
}

UA = {"User-Agent": "Mozilla/5.0 (Crypto3D-TEV-Dashboard/2.0)"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get_defillama(slug):
    """返回 (daily_fees, daily_revenue, total30d_fees, total1y_fees) 或 None"""
    try:
        d = fetch(f"https://api.llama.fi/summary/fees/{slug}")
        total24h = d.get("total24h")
        total30d = d.get("total30d")
        total1y = d.get("total1y")
        return {
            "daily_fees_usd": round(total24h) if total24h is not None else None,
            "total30d_fees_usd": round(total30d) if total30d is not None else None,
            "total1y_fees_usd": round(total1y) if total1y is not None else None,
            "source": "defillama_fees",
        }
    except Exception as e:
        print(f"    ⚠ DefiLlama {slug} 失败: {e}")
        return None


def get_coingecko(coin_id):
    """返回 (price, market_cap, circulating_supply) 或 None"""
    try:
        d = fetch(f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false")
        md = d.get("market_data", {})
        return {
            "price_usd": md.get("current_price", {}).get("usd"),
            "market_cap_usd": md.get("market_cap", {}).get("usd"),
            "circulating_supply": md.get("circulating_supply"),
        }
    except Exception as e:
        print(f"    ⚠ CoinGecko {coin_id} 失败: {e}")
        return None


def rebuild(pid):
    slug, cg_id = SLUGS.get(pid, (None, None))
    daily_dir = DAILY / pid
    latest_path = daily_dir / "latest.json"
    old = {}
    if latest_path.exists():
        try:
            old = json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    today = date.today().isoformat()

    # 拉数据
    dl = get_defillama(slug) if slug else None
    cg = get_coingecko(cg_id) if cg_id else None

    # 市场数据（优先 CoinGecko，回退旧值）
    price = (cg or {}).get("price_usd") or (old.get("latest_record") or {}).get("price_usd")
    mcap = (cg or {}).get("market_cap_usd") or (old.get("latest_record") or {}).get("market_cap_usd") \
           or (old.get("metrics") or {}).get("current_market_cap_usd")

    latest_record = {
        "date": today,
        "price_usd": price,
        "market_cap_usd": mcap,
        "daily_fees_usd": (dl or {}).get("daily_fees_usd"),
        "total30d_fees_usd": (dl or {}).get("total30d_fees_usd"),
        "total1y_fees_usd": (dl or {}).get("total1y_fees_usd"),
    }

    # 保留旧 metrics 的 TEV 相关字段（这些由专属脚本维护，这里不动数值只刷时间）
    old_metrics = old.get("metrics", {})
    metrics = {
        "trailing_30d_tev_usd": old_metrics.get("trailing_30d_tev_usd"),
        "trailing_365d_tev_usd": old_metrics.get("trailing_365d_tev_usd"),
        "annualized_tev_usd": old_metrics.get("annualized_tev_usd"),
        "current_market_cap_usd": mcap,
        "tev_yield": old_metrics.get("tev_yield"),
        "tev_yield_decimal": old_metrics.get("tev_yield_decimal"),
        "calculated_at": now_iso,
    }

    new = {
        "protocol": pid,
        "updated_at": now_iso,
        "data_sources": {
            "defillama": slug or "无（平台币/静态，专属脚本维护）",
            "coingecko": cg_id,
            "note": "M0 僵尸数据重建 2026-08-02：数据来自 DefiLlama summary/fees + CoinGecko；TEV 机制字段保留原值（由专属 adapter 维护）",
        },
        "latest_record": {k: v for k, v in latest_record.items()},
        "metrics": metrics,
    }

    if DRY:
        print(f"  [DRY] {pid}: dl={'✓' if dl else '✗'} cg={'✓' if cg else '✗'} mcap={mcap}")
        return

    latest_path.write_text(json.dumps(new, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ {pid}: mcap={mcap} daily_fees={(dl or {}).get('daily_fees_usd')} cg_price={price}")


def main():
    args = sys.argv[1:]
    protos = []
    for i, a in enumerate(args):
        if a == "--protocol":
            protos = args[i + 1:].copy()
            break
    if not protos:
        protos = sorted(p.name for p in DAILY.iterdir() if p.is_dir() and p.name not in EXCLUDED_DIRS)

    print(f"{'DRY-RUN ' if DRY else ''}重建 {len(protos)} 个 data/daily latest.json（DefiLlama + CoinGecko）")
    for pid in protos:
        rebuild(pid)
        time.sleep(1.2)  # CoinGecko 限流 ~10-30 req/min
    print("完成")


if __name__ == "__main__":
    main()
