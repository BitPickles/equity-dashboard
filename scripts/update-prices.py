#!/usr/bin/env python3
"""
update-prices.py — 27 协议价格/市值/流通量每日更新

Boss 2026-08-04 反馈：代币价格数据不准（hype -47%、sky +40%、aave +27% 偏差）。
根因：all-protocols.json 市值停在 08-02，无每日价格管道。

本脚本：从 CoinGecko 免费 API 拉 27 协议实时 price/market_cap/circulating_supply
→ 同步三处：
1. data/protocols/<id>/config.json 的 market_data
2. data/all-protocols.json 的 market_cap_usd + metrics
3. data/daily/<id>/latest.json 的 metrics.current_market_cap_usd（若有）

限流保护：6s 间隔（免费层实测 ~10 req/min）+ 429 重试 3 次。

用法:
  python3 scripts/update-prices.py                # 全量 27 协议
  python3 scripts/update-prices.py --protocol bnb  # 指定
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Crypto3D-TEV-Dashboard/2.0)"}

# 协议 → CoinGecko id（与 rebuild-daily.py SLUGS 对齐，2026-08-04 校验）
# ⚠️ sky 用 CMC 而非 CoinGecko：CG 的 'maker' 已迁移改名返回 mcap=0（2026-08-04 实测）
CG_IDS = {
    "aave": "aave", "aster": "aster-2", "bgb": "bitget-token", "bnb": "binancecoin",
    "compound": "compound-governance-token", "curve": "curve-dao-token", "dydx": "dydx-chain",
    "eigenlayer": "eigenlayer", "ethena": "ethena",
    "fluid": "instadapp", "gmx": "gmx", "hype": "hyperliquid", "jito": "jito-governance-token",
    "justlend": "just", "kamino": "kamino", "layerzero": "layerzero", "lido": "lido-dao",
    "maple": "syrup", "mnt": "mantle", "morpho": "morpho", "okb": "okb",
    "pancakeswap": "pancakeswap-token", "pendle": "pendle",
    "spark": "spark", "uniswap": "uniswap",
    # sky 用 CMC slug（在 fetch_cmc 处理）；spark CG 404 → CMC 兜底
    "sky": "sky",  # ← CMC slug，标记走 CMC
}

# 走 CMC 的协议（CoinGecko 无数据或异常）：slug → CMC slug
CMC_SLUGS = {
    "sky": "sky",      # CG maker 改名返回 0
    "spark": "spark",  # CG 无 spark id（404）
}


def fetch(coin_id):
    url = (f"https://api.coingecko.com/api/v3/coins/{coin_id}"
           f"?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    md = d.get("market_data", {})
    return {
        "price_usd": md.get("current_price", {}).get("usd"),
        "market_cap_usd": md.get("market_cap", {}).get("usd"),
        "circulating_supply": md.get("circulating_supply"),
    }


def fetch_cmc(slug):
    """CMC 兜底（sky/spark 等 CoinGecko 无数据的协议）。env CMC_API_KEY 必需。"""
    key = os_environ_get()
    url = f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?slug={slug}"
    req = urllib.request.Request(url, headers={"X-CMC_PRO_API_KEY": key, "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    first = next(iter(d.get("data", {}).values()))
    q = first["quote"]["USD"]
    return {
        "price_usd": q["price"],
        "market_cap_usd": q["market_cap"],
        "circulating_supply": first.get("circulating_supply"),
    }


def os_environ_get():
    import os
    # 尝试 .env
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("CMC_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("CMC_API_KEY", "").strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", nargs="*")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    protos = args.protocol or sorted(CG_IDS)
    now = datetime.now(timezone.utc).isoformat()

    # 读 all-protocols（一次性）
    allp_path = BASE / "data" / "all-protocols.json"
    allp = json.loads(allp_path.read_text(encoding="utf-8"))

    ok = fail = 0
    for pid in protos:
        cid = CG_IDS.get(pid)
        if not cid:
            print(f"  SKIP {pid}: 无 CoinGecko id")
            continue
        if args.dry_run:
            print(f"  [DRY] {pid}: cg_id={cid}")
            continue
        try:
            if pid in CMC_SLUGS:
                # CMC 兜底（sky/spark）——无 429 重试逻辑（CMC 配额独立）
                info = fetch_cmc(CMC_SLUGS[pid])
            else:
                for attempt in range(3):  # 429 限流重试 3 次
                    try:
                        info = fetch(cid)
                        break
                    except urllib.error.HTTPError as e:
                        if e.code == 429 and attempt < 2:
                            print(f"    ⚠ {pid} 429 限流，等待重试 ({attempt+1}/2)")
                            time.sleep(20 * (attempt + 1))
                        else:
                            raise
            if not info.get("price_usd"):
                raise ValueError("no price")
            # ① config.json market_data
            cfg_path = BASE / "data" / "protocols" / pid / "config.json"
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                cfg.setdefault("market_data", {})
                cfg["market_data"].update({
                    "price_usd": info["price_usd"],
                    "circulating_market_cap": info["market_cap_usd"],
                    "circulating_supply": info["circulating_supply"],
                    "price_updated_at": now,
                })
                cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
            # ② all-protocols.json
            if pid in allp.get("protocols", {}):
                p = allp["protocols"][pid]
                if info["market_cap_usd"]:
                    p["market_cap_usd"] = info["market_cap_usd"]
                p["last_updated"] = now[:10]
                p.setdefault("metrics", {})
                p["metrics"]["current_market_cap_usd"] = info["market_cap_usd"]
                p["metrics"]["current_price_usd"] = info["price_usd"]
            # ③ data/daily/latest.json
            daily_path = BASE / "data" / "daily" / pid / "latest.json"
            if daily_path.exists():
                daily = json.loads(daily_path.read_text(encoding="utf-8"))
                daily.setdefault("metrics", {})
                daily["metrics"]["current_market_cap_usd"] = info["market_cap_usd"]
                daily["metrics"]["calculated_at"] = now
                daily["updated_at"] = now
                daily_path.write_text(json.dumps(daily, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  ✓ {pid}: ${info['price_usd']:.2f}  mcap=${(info['market_cap_usd'] or 0)/1e9:.2f}B  circ={info['circulating_supply']:,.0f}")
            ok += 1
        except Exception as e:
            print(f"  ✗ {pid}: {str(e)[:70]}")
            fail += 1
        time.sleep(6.0)  # 免费层实测 ~10 req/min（429 后 6s 保险）

    if not args.dry_run:
        allp["generated_at"] = now
        allp_path.write_text(json.dumps(allp, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n完成: {ok} ok, {fail} fail | 时间 {now[:16]}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
