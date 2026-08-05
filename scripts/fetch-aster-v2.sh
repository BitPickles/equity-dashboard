#!/bin/bash
# Fetch Aster buyback data - fixed version

API_KEY="${MORALIS_API_KEY:-}"
# ⚠️ 安全修复 2026-08-06：key 曾硬编码，改为环境变量 MORALIS_API_KEY（或 .env）
if [ -z "$API_KEY" ] && [ -f "$(dirname "$0")/../.env" ]; then
  API_KEY=$(grep -E "^MORALIS_API_KEY=" "$(dirname "$0")/../.env" | cut -d= -f2 | tr -d "
")
fi
if [ -z "$API_KEY" ]; then
  echo "❌ 未设置 MORALIS_API_KEY" >&2; exit 1
fi
TOKEN="0x000ae314e2a2172a039b26378814c252734f556a"

# Stage 5 wallet (lowercase)
STAGE5="0x4786927333c0ba8ab27ca41361adf33148c5301e"
# Stage 6 wallet (lowercase) 
STAGE6="0x664827c71193018d7843f0d0f41a5d0d6dcebe0f"

fetch_all() {
    local wallet=$1
    local stage=$2
    local outfile="data/aster-${stage}-transfers.json"
    
    echo "Fetching $stage: $wallet"
    
    local all_results="[]"
    local cursor=""
    local page=0
    
    while true; do
        page=$((page + 1))
        
        local url="https://deep-index.moralis.io/api/v2.2/${wallet}/erc20/transfers?chain=bsc&contract_addresses%5B0%5D=${TOKEN}&limit=100"
        if [ -n "$cursor" ]; then
            url="${url}&cursor=${cursor}"
        fi
        
        local response=$(curl -s "$url" -H "X-API-Key: $API_KEY")
        
        cursor=$(echo "$response" | jq -r '.cursor // empty')
        
        # Filter transfers TO this wallet using jq with hardcoded address
        local results=$(echo "$response" | jq --arg w "$wallet" '[.result[] | select(.to_address == $w)]')
        local count=$(echo "$results" | jq 'length')
        
        echo "  Page $page: $count transfers IN"
        
        all_results=$(echo "$all_results" "$results" | jq -s 'add')
        
        if [ -z "$cursor" ] || [ "$cursor" = "null" ]; then
            break
        fi
        
        if [ $page -ge 50 ]; then
            echo "  Reached page limit"
            break
        fi
        
        sleep 0.3
    done
    
    echo "$all_results" > "$outfile"
    local total=$(echo "$all_results" | jq 'length')
    local sum=$(echo "$all_results" | jq '[.[].value_decimal | tonumber] | add // 0')
    echo "$stage total: $total transfers, $sum ASTER"
    echo ""
}

fetch_all "$STAGE5" "stage5"
fetch_all "$STAGE6" "stage6"

echo "=== Merging data ==="
python3 << 'PYTHON'
import json
from collections import defaultdict

def load_transfers(filename, stage):
    try:
        with open(filename) as f:
            data = json.load(f)
        return [(tx["block_timestamp"][:10], float(tx["value_decimal"]), stage) for tx in data if float(tx.get("value_decimal", 0)) > 0]
    except:
        return []

s5 = load_transfers("data/aster-stage5-transfers.json", "stage5")
s6 = load_transfers("data/aster-stage6-transfers.json", "stage6")

all_txs = s5 + s6
daily = defaultdict(lambda: {"aster": 0.0, "txs": 0, "stage": None})
for date, amount, stage in all_txs:
    daily[date]["aster"] += amount
    daily[date]["txs"] += 1
    daily[date]["stage"] = stage

result = []
for date in sorted(daily.keys()):
    d = daily[date]
    result.append({
        "date": date,
        "aster": round(d["aster"], 2),
        "txs": d["txs"],
        "stage": d["stage"],
        "data_type": "onchain",
        "source": "moralis"
    })

with open("data/aster-onchain.json", "w") as f:
    json.dump(result, f, indent=2)

s5_total = sum(r["aster"] for r in result if r["stage"] == "stage5")
s6_total = sum(r["aster"] for r in result if r["stage"] == "stage6")
print(f"Stage 5: {sum(1 for r in result if r['stage']=='stage5')} days, {s5_total:,.0f} ASTER")
print(f"Stage 6: {sum(1 for r in result if r['stage']=='stage6')} days, {s6_total:,.0f} ASTER")
print(f"Total: {len(result)} days, {s5_total + s6_total:,.0f} ASTER")
if result:
    print(f"Range: {result[0]['date']} to {result[-1]['date']}")
PYTHON
