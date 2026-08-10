#!/usr/bin/env python3
"""
Fetch Aster buyback data from BscScan
检查所有代币转账，不限于 ASTER
"""

import requests
import json
import os
from datetime import datetime
from collections import defaultdict
import time

BSCSCAN_API = "https://api.bscscan.com/api"

# ASTER token contract on BSC
ASTER_CONTRACT = "0x000Ae314E2A2172a039B26378814C252734f556A"

# Stage 6 addresses (current)
STAGE6_AUTO = "0x664827c71193018D7843f0D0F41A5D0D6dcEBE0F"
STAGE6_STRATEGIC = "0xe5779AEEf4ccC5Ec4fD78f008063D7DC4D0A780c"

# Burn address
BURN_ADDRESS = "0x000000000000000000000000000000000000dEaD"

def get_all_token_transfers(address):
    """Get ALL token transfers for an address (not just ASTER)"""
    params = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "sort": "desc",
        "page": 1,
        "offset": 100
    }
    try:
        resp = requests.get(BSCSCAN_API, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "1":
            return data.get("result", [])
        else:
            print(f"  API message: {data.get('message', 'unknown')}")
    except Exception as e:
        print(f"Error: {e}")
    return []

def get_normal_txs(address):
    """Get normal BNB transactions"""
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "sort": "desc",
        "page": 1,
        "offset": 50
    }
    try:
        resp = requests.get(BSCSCAN_API, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "1":
            return data.get("result", [])
    except Exception as e:
        print(f"Error: {e}")
    return []

def analyze_address(address, name):
    """Analyze all activity for an address"""
    print(f"\n📍 {name}")
    print(f"   Address: {address}")
    
    # Get token transfers
    print("   Fetching token transfers...")
    transfers = get_all_token_transfers(address)
    time.sleep(0.3)  # Rate limit
    
    if transfers:
        # Group by token
        by_token = defaultdict(list)
        for tx in transfers:
            symbol = tx.get("tokenSymbol", "UNKNOWN")
            by_token[symbol].append(tx)
        
        print(f"   Found {len(transfers)} token transfers across {len(by_token)} tokens:")
        for symbol, txs in sorted(by_token.items(), key=lambda x: -len(x[1])):
            total_in = sum(int(tx["value"]) / (10 ** int(tx.get("tokenDecimal", 18))) 
                         for tx in txs if tx.get("to", "").lower() == address.lower())
            total_out = sum(int(tx["value"]) / (10 ** int(tx.get("tokenDecimal", 18))) 
                          for tx in txs if tx.get("from", "").lower() == address.lower())
            print(f"      {symbol}: {len(txs)} txs, in={total_in:,.2f}, out={total_out:,.2f}")
        
        return transfers, by_token
    else:
        print("   No token transfers found")
        
    # Get normal txs
    print("   Fetching BNB transactions...")
    normal = get_normal_txs(address)
    time.sleep(0.3)
    
    if normal:
        print(f"   Found {len(normal)} BNB transactions")
        total_in = sum(int(tx["value"]) / 1e18 for tx in normal if tx.get("to", "").lower() == address.lower())
        total_out = sum(int(tx["value"]) / 1e18 for tx in normal if tx.get("from", "").lower() == address.lower())
        print(f"      BNB: in={total_in:,.4f}, out={total_out:,.4f}")
    else:
        print("   No BNB transactions found")
    
    return [], {}

def main():
    print("=" * 60)
    print("Aster Buyback Address Analysis")
    print("=" * 60)
    
    result = {
        "protocol": "aster",
        "ticker": "ASTER",
        "updated_at": datetime.now().isoformat(),
        "addresses": {}
    }
    
    # Stage 6 Auto
    transfers, by_token = analyze_address(STAGE6_AUTO, "Stage 6 - Auto Daily (40%)")
    result["addresses"]["stage6_auto"] = {
        "address": STAGE6_AUTO,
        "tx_count": len(transfers),
        "tokens": {k: len(v) for k, v in by_token.items()}
    }
    
    time.sleep(1)
    
    # Stage 6 Strategic
    transfers, by_token = analyze_address(STAGE6_STRATEGIC, "Stage 6 - Strategic (20-40%)")
    result["addresses"]["stage6_strategic"] = {
        "address": STAGE6_STRATEGIC,
        "tx_count": len(transfers),
        "tokens": {k: len(v) for k, v in by_token.items()}
    }
    
    time.sleep(1)
    
    # Check burn for ASTER specifically
    print(f"\n🔥 Checking ASTER burned to 0xdead...")
    params = {
        "module": "account",
        "action": "tokenbalance",
        "address": BURN_ADDRESS,
        "contractaddress": ASTER_CONTRACT
    }
    try:
        resp = requests.get(BSCSCAN_API, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "1":
            burned = int(data.get("result", 0)) / 1e18
            print(f"   ASTER burned: {burned:,.0f}")
            result["burned"] = burned
    except Exception as e:
        print(f"   Error: {e}")
    
    # Save
    output_path = os.path.join(os.path.dirname(__file__), "../data/aster-buybacks.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved to {output_path}")

if __name__ == "__main__":
    main()
