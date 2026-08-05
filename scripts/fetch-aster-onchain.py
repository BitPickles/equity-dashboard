#!/usr/bin/env python3
"""
使用 Moralis API 获取 Aster 回购钱包的真实链上交易数据
"""

import requests
import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import os
import time

# ⚠️ 安全修复 2026-08-06：Moralis key 曾硬编码在此文件并进入 git 历史（public 仓库）。
# 已改为环境变量读取。历史版本若被第三方抓取，请在 Moralis 后台轮换此 key。
MORALIS_API_KEY = os.environ.get("MORALIS_API_KEY", "")
if not MORALIS_API_KEY:
    _env = Path(__file__).resolve().parent.parent / ".env"
    if _env.exists():
        for _line in _env.read_text(encoding="utf-8").splitlines():
            if _line.startswith("MORALIS_API_KEY="):
                MORALIS_API_KEY = _line.split("=", 1)[1].strip()
                break
if not MORALIS_API_KEY:
    raise SystemExit("❌ 未设置 MORALIS_API_KEY 环境变量（或 .env）。请配置后运行。")

ASTER_CONTRACT = "0x000Ae314E2A2172a039B26378814C252734f556A"

# 回购钱包
WALLETS = {
    "stage6": "0x664827c71193018D7843f0D0F41A5D0D6dcEBE0F",
    "stage5": "0x4786927333c0bA8aB27CA41361ADF33148C5301E",
}

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "../data/aster-buybacks.json"


def get_token_transfers(wallet: str, cursor: str = None) -> dict:
    """获取钱包的 ASTER 转入记录"""
    url = f"https://deep-index.moralis.io/api/v2/{wallet}/erc20/transfers"
    params = {
        "chain": "bsc",
        "contract_addresses": ASTER_CONTRACT,
        "limit": 100
    }
    if cursor:
        params["cursor"] = cursor
    
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    return resp.json()


def fetch_all_transfers(wallet: str, wallet_name: str) -> list:
    """获取钱包所有的转入记录"""
    print(f"\n📥 Fetching transfers for {wallet_name}...")
    print(f"   Wallet: {wallet}")
    
    all_transfers = []
    cursor = None
    page = 0
    
    while True:
        page += 1
        print(f"   Page {page}...", end=" ")
        
        data = get_token_transfers(wallet, cursor)
        
        if "result" not in data:
            print(f"Error: {data}")
            break
        
        transfers = data["result"]
        print(f"{len(transfers)} records")
        
        # 只保留转入记录 (to_address = wallet)
        incoming = [t for t in transfers if t["to_address"].lower() == wallet.lower()]
        all_transfers.extend(incoming)
        
        cursor = data.get("cursor")
        if not cursor or not transfers:
            break
        
        time.sleep(0.3)  # Rate limit
    
    print(f"   Total incoming: {len(all_transfers)}")
    return all_transfers


def aggregate_by_date(transfers: list) -> dict:
    """按日期聚合转账"""
    daily = defaultdict(lambda: {"aster": 0, "count": 0, "txs": []})
    
    for t in transfers:
        date = t["block_timestamp"][:10]  # YYYY-MM-DD
        value = float(t.get("value_decimal", 0)) or int(t["value"]) / 1e18
        
        daily[date]["aster"] += value
        daily[date]["count"] += 1
        daily[date]["txs"].append(t["transaction_hash"])
    
    return dict(daily)


def main():
    print("=" * 60)
    print("Fetching Aster Buyback On-Chain Data (Moralis)")
    print("=" * 60)
    
    all_daily_data = []
    
    # Stage 6
    transfers6 = fetch_all_transfers(WALLETS["stage6"], "Stage 6")
    daily6 = aggregate_by_date(transfers6)
    
    for date, data in sorted(daily6.items()):
        all_daily_data.append({
            "date": date,
            "aster": round(data["aster"], 2),
            "usd": None,
            "stage": "6",
            "data_type": "onchain",
            "tx_count": data["count"]
        })
    
    # Stage 5
    transfers5 = fetch_all_transfers(WALLETS["stage5"], "Stage 5")
    daily5 = aggregate_by_date(transfers5)
    
    for date, data in sorted(daily5.items()):
        all_daily_data.append({
            "date": date,
            "aster": round(data["aster"], 2),
            "usd": None,
            "stage": "5",
            "data_type": "onchain",
            "tx_count": data["count"]
        })
    
    # 加载现有数据（Stage 1-4 保留估算）
    existing = {}
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            existing = json.load(f)
    
    # 保留 Stage 1-4 的估算数据
    stage14_data = [d for d in existing.get("daily_buybacks", []) if d.get("stage") == "1-4"]
    
    # 合并
    all_daily_data = stage14_data + all_daily_data
    all_daily_data.sort(key=lambda x: x["date"])
    
    # 统计
    total_aster = sum(d["aster"] for d in all_daily_data)
    stage6_aster = sum(d["aster"] for d in all_daily_data if d.get("stage") == "6")
    stage5_aster = sum(d["aster"] for d in all_daily_data if d.get("stage") == "5")
    stage14_aster = sum(d["aster"] for d in all_daily_data if d.get("stage") == "1-4")
    
    # 保存
    output = {
        "protocol": "aster",
        "ticker": "ASTER",
        "total_supply": 1_000_000_000,
        "updated_at": datetime.now().isoformat(),
        
        "summary": {
            "total_buyback_aster": round(total_aster, 2),
            "stage14_aster": round(stage14_aster, 2),
            "stage5_aster": round(stage5_aster, 2),
            "stage6_aster": round(stage6_aster, 2),
            "total_days": len(all_daily_data),
            "start_date": all_daily_data[0]["date"] if all_daily_data else None,
            "end_date": all_daily_data[-1]["date"] if all_daily_data else None,
            "note": "Stage 1-4 为历史报道估算，Stage 5-6 为链上真实数据"
        },
        
        "stages": existing.get("stages", []),
        "daily_buybacks": all_daily_data
    }
    
    with open(DATA_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to {DATA_FILE}")
    print(f"\n📊 Summary:")
    print(f"   Stage 1-4 (估算): {stage14_aster:,.0f} ASTER")
    print(f"   Stage 5 (链上): {stage5_aster:,.0f} ASTER")
    print(f"   Stage 6 (链上): {stage6_aster:,.0f} ASTER")
    print(f"   Total: {total_aster:,.0f} ASTER ({total_aster/1e9*100:.2f}%)")


if __name__ == "__main__":
    main()
