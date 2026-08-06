#!/usr/bin/env python3
"""Aster 链上回购采集（改造版，2026-08-06）

替代旧的模拟数据脚本。用 Moralis API 拉取 Aster 回购钱包的 ASTER 转入，
写入 data/aster-onchain.json（供 sync-tev-data.js / adapter 使用）。

钱包清单：
- S4 回购钱包（2025-12~2026-02，含 2-05 大额销毁）: 0x573ca9FF6b7f164dfF513077850d5CD796006fF4
- 6-17 新机制 TWAP 回购钱包（官方公布，执行量待显化）: 0xa0edBaBcb48034e368de286b49F9603C7AfA1b60
- 6-17 新机制上市费钱包: 0x39C473f4420e4ae9Ab3fe9e7ceDFc08F9684bB1a

用法:
  python3 scripts/update-aster.py                    # 全量
  python3 scripts/update-aster.py --wallet 0x...     # 指定钱包
依赖: MORALIS_API_KEY（环境变量或 .env）
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ASTER_CONTRACT = "0x000ae314e2a2172a039b26378814c252734f556a"
ASTER = ASTER_CONTRACT

WALLETS = {
    "s4_buyback": "0x573ca9FF6b7f164dfF513077850d5CD796006fF4",
    "new_twap_buyback": "0xa0edBaBcb48034e368de286b49F9603C7AfA1b60",
    "new_listing_fee": "0x39C473f4420e4ae9Ab3fe9e7ceDFc08F9684bB1a",
}


def get_api_key():
    key = os.environ.get("MORALIS_API_KEY", "")
    if not key:
        env = BASE / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("MORALIS_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    if not key:
        print("❌ 未设置 MORALIS_API_KEY（环境变量或 .env）")
        sys.exit(1)
    return key


API_KEY = get_api_key()


def moralis_get(url, retries=4):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0', 'X-API-Key': API_KEY, 'accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print(f'  retry{i+1}: {str(e)[:60]}')
            time.sleep(6)
    return None


def fetch_wallet_inflow(wallet, max_pages=8):
    """拉钱包的 ASTER 转入，按天聚合"""
    daily = defaultdict(float)
    tx_count = defaultdict(int)
    cursor = None
    for page in range(max_pages):
        url = f"https://deep-index.moralis.io/api/v2.2/{wallet}/erc20/transfers?chain=bsc&contract_addresses={ASTER}&limit=100&order=asc"
        if cursor:
            url += f"&cursor={cursor}"
        d = moralis_get(url)
        if not d:
            break
        res = d.get('result', [])
        if not res:
            break
        for tx in res:
            if tx.get('to_address', '').lower() == wallet.lower():
                day = tx['block_timestamp'][:10]
                val = int(tx.get('value', 0)) / 1e18
                daily[day] += val
                tx_count[day] += 1
        cursor = d.get('cursor')
        if not cursor:
            break
        time.sleep(2)
    return daily, tx_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wallet', help='只采集指定钱包')
    args = parser.parse_args()

    targets = {args.wallet: WALLETS[args.wallet]} if args.wallet else WALLETS
    all_records = []

    for name, wallet in targets.items():
        print(f'📊 {name}: {wallet}')
        daily, tx_count = fetch_wallet_inflow(wallet)
        if not daily:
            print(f'  ⚠️ 无 ASTER 转入（可能是 6-17 新机制执行量未显化）')
        total = sum(daily.values())
        print(f'  {len(daily)} 天有转入, 累计 {total:,.0f} ASTER')
        for day in sorted(daily):
            all_records.append({
                "date": day,
                "aster": round(daily[day], 2),
                "txs": tx_count[day],
                "stage": name,
                "source": "moralis",
            })
        time.sleep(2)

    # 合并到现有 aster-onchain.json（按日期去重，新记录覆盖）
    out = BASE / "data" / "aster-onchain.json"
    existing = []
    if out.exists():
        existing = json.loads(out.read_text(encoding="utf-8"))
    by_date = {r['date']: r for r in existing}
    for r in all_records:
        by_date[r['date']] = r
    merged = sorted(by_date.values(), key=lambda x: x['date'])
    out.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f'\n✅ 已写入 {out}（共 {len(merged)} 天记录）')
    if merged:
        print(f'   范围: {merged[0]["date"]} ~ {merged[-1]["date"]}')
        total_all = sum(r.get('aster', 0) for r in merged)
        print(f'   累计: {total_all:,.0f} ASTER')


if __name__ == "__main__":
    main()
