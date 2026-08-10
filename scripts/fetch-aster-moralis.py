#!/usr/bin/env python3
"""
Fetch Aster buyback data from Moralis API
Get all ASTER token transfers to buyback wallets
"""

import requests
import os
import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# ⚠️ 安全修复 2026-08-06：key 曾硬编码，已改为环境变量/.env 读取
API_KEY = os.environ.get("MORALIS_API_KEY", "")
if not API_KEY:
    _env = Path(__file__).resolve().parent.parent / ".env"
    if _env.exists():
        for _line in _env.read_text(encoding="utf-8").splitlines():
            if _line.startswith("MORALIS_API_KEY="):
                API_KEY = _line.split("=", 1)[1].strip()
                break
if not API_KEY:
    raise SystemExit("❌ 未设置 MORALIS_API_KEY 环境变量（或 .env）。请配置后运行。")

ASTER_TOKEN = "0x000ae314e2a2172a039b26378814c252734f556a"

# Buyback wallets (correct addresses from Aster skill)
WALLETS = {
    "stage5": "0x4786927333c0bA8aB27CA41361ADF33148C5301E",
    "stage6": "0x664827c71193018D7843f0D0F41A5D0D6dcEBE0F"
}

def fetch_transfers(wallet_address, stage_name):
    """Fetch all ASTER transfers TO the wallet"""
    url = f"https://deep-index.moralis.io/api/v2.2/{wallet_address}/erc20/transfers"
    headers = {"X-API-Key": API_KEY}
    
    all_transfers = []
    cursor = None
    page = 0
    
    while True:
        params = {
            "chain": "bsc",
            "contract_addresses[0]": ASTER_TOKEN,
            "limit": 100
        }
        if cursor:
            params["cursor"] = cursor
            
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if "result" not in data:
            print(f"Error: {data}")
            break
            
        # Filter only transfers TO this wallet (buybacks)
        for tx in data["result"]:
            if tx["to_address"].lower() == wallet_address.lower():
                all_transfers.append({
                    "date": tx["block_timestamp"][:10],
                    "timestamp": tx["block_timestamp"],
                    "amount": float(tx["value_decimal"]),
                    "tx_hash": tx["transaction_hash"],
                    "stage": stage_name
                })
        
        page += 1
        print(f"{stage_name} page {page}: {len(data['result'])} records")
        
        cursor = data.get("cursor")
        if not cursor:
            break
    
    return all_transfers

def aggregate_by_date(transfers):
    """Aggregate transfers by date"""
    daily = defaultdict(lambda: {"aster": 0, "txs": 0, "stage": None})
    
    for tx in transfers:
        date = tx["date"]
        daily[date]["aster"] += tx["amount"]
        daily[date]["txs"] += 1
        daily[date]["stage"] = tx["stage"]
    
    return daily

def main():
    all_transfers = []
    
    for stage_name, wallet in WALLETS.items():
        print(f"\nFetching {stage_name}: {wallet}")
        transfers = fetch_transfers(wallet, stage_name)
        print(f"Total {stage_name} transfers: {len(transfers)}")
        all_transfers.extend(transfers)
    
    # Aggregate by date
    daily = aggregate_by_date(all_transfers)
    
    # Sort by date
    sorted_dates = sorted(daily.keys())
    
    print(f"\n=== Daily Summary ===")
    print(f"Date range: {sorted_dates[0]} to {sorted_dates[-1]}")
    print(f"Total days: {len(sorted_dates)}")
    
    total_aster = sum(d["aster"] for d in daily.values())
    print(f"Total ASTER: {total_aster:,.0f}")
    
    # Output as JSON
    result = []
    for date in sorted_dates:
        d = daily[date]
        result.append({
            "date": date,
            "aster": round(d["aster"], 2),
            "txs": d["txs"],
            "stage": d["stage"],
            "source": "moralis"
        })
    
    # Save to file
    output_file = "data/aster-onchain.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {output_file}")
    
    # Print last 5 days
    print("\n=== Last 5 days ===")
    for entry in result[-5:]:
        print(f"{entry['date']}: {entry['aster']:,.0f} ASTER ({entry['txs']} txs) - {entry['stage']}")

if __name__ == "__main__":
    main()
