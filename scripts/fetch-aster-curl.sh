#!/bin/bash
# Fetch Aster buyback data using curl (avoid SSL issues)

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

STAGE5_WALLET="0x4786927333c0bA8aB27CA41361ADF33148C5301E"
STAGE6_WALLET="0x664827c71193018D7843f0D0F41A5D0D6dcEBE0F"

OUTPUT_DIR="data"
STAGE5_FILE="$OUTPUT_DIR/aster-stage5-raw.json"
STAGE6_FILE="$OUTPUT_DIR/aster-stage6-raw.json"

fetch_wallet() {
    local wallet=$1
    local output_file=$2
    local stage_name=$3
    
    echo "Fetching $stage_name: $wallet"
    
    local cursor=""
    local page=0
    local all_results="[]"
    
    while true; do
        page=$((page + 1))
        
        local url="https://deep-index.moralis.io/api/v2.2/${wallet}/erc20/transfers?chain=bsc&contract_addresses%5B0%5D=${TOKEN}&limit=100"
        if [ -n "$cursor" ]; then
            url="${url}&cursor=${cursor}"
        fi
        
        local response=$(curl -s "$url" -H "X-API-Key: $API_KEY")
        
        # Get cursor for next page
        cursor=$(echo "$response" | jq -r '.cursor // empty')
        
        # Get results, filter only transfers TO this wallet
        local results=$(echo "$response" | jq --arg wallet "${wallet,,}" '
            [.result[] | select(.to_address == $wallet)]
        ')
        
        local count=$(echo "$results" | jq 'length')
        echo "  Page $page: $count transfers IN"
        
        # Merge results
        all_results=$(echo "$all_results $results" | jq -s 'add')
        
        # Break if no more pages
        if [ -z "$cursor" ] || [ "$cursor" = "null" ]; then
            break
        fi
        
        # Safety limit
        if [ $page -ge 50 ]; then
            echo "  Reached page limit"
            break
        fi
        
        sleep 0.5  # Rate limit
    done
    
    # Save to file
    echo "$all_results" | jq '.' > "$output_file"
    local total=$(echo "$all_results" | jq 'length')
    echo "$stage_name total: $total transfers"
}

# Fetch both stages
fetch_wallet "$STAGE5_WALLET" "$STAGE5_FILE" "Stage5"
fetch_wallet "$STAGE6_WALLET" "$STAGE6_FILE" "Stage6"

echo ""
echo "=== Aggregating by date ==="

# Aggregate and merge
python3 << 'PYTHON'
import json
from collections import defaultdict

def load_and_aggregate(filename, stage):
    try:
        with open(filename) as f:
            data = json.load(f)
    except:
        return {}
    
    daily = defaultdict(lambda: {"aster": 0.0, "txs": 0})
    for tx in data:
        date = tx.get("block_timestamp", "")[:10]
        amount = float(tx.get("value_decimal", 0) or 0)
        if date and amount > 0:
            daily[date]["aster"] += amount
            daily[date]["txs"] += 1
    
    return {date: {"aster": v["aster"], "txs": v["txs"], "stage": stage} for date, v in daily.items()}

stage5 = load_and_aggregate("data/aster-stage5-raw.json", "stage5")
stage6 = load_and_aggregate("data/aster-stage6-raw.json", "stage6")

# Merge
all_days = {**stage5, **stage6}

# Convert to sorted list
result = []
for date in sorted(all_days.keys()):
    d = all_days[date]
    result.append({
        "date": date,
        "aster": round(d["aster"], 2),
        "txs": d["txs"],
        "stage": d["stage"],
        "data_type": "onchain",
        "source": "moralis"
    })

# Save
with open("data/aster-onchain.json", "w") as f:
    json.dump(result, f, indent=2)

# Summary
print(f"Stage 5: {sum(1 for r in result if r['stage']=='stage5')} days, {sum(r['aster'] for r in result if r['stage']=='stage5'):,.0f} ASTER")
print(f"Stage 6: {sum(1 for r in result if r['stage']=='stage6')} days, {sum(r['aster'] for r in result if r['stage']=='stage6'):,.0f} ASTER")
print(f"Total: {len(result)} days, {sum(r['aster'] for r in result):,.0f} ASTER")
print(f"Date range: {result[0]['date']} to {result[-1]['date']}")
PYTHON

echo ""
echo "Saved to data/aster-onchain.json"
