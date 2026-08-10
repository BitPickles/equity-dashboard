#!/usr/bin/env python3
"""
Fetch tokenomics data (allocation + unlock schedule) for TEV Dashboard protocols.

API Research Results (2026-04-13):
  - CMC /data-api/v3/cryptocurrency/detail?slug=X => works, has supplyDetails (total/circulating/max supply)
    but NO allocation or unlock schedule data
  - CMC /data-api/v3/token-unlock/summary?cryptoId=X => 404 (likely requires API key or removed)
  - CMC /data-api/v3/token-unlock/allocation?cryptoId=X => 404
  - CMC /data-api/v3/token-unlock/schedule?cryptoId=X => 404
  - CMC /data-api/v3/cryptocurrency/detail/tokenomics?slug=X => 404
  - CMC /data-api/v1/cryptocurrency/token-unlock?slug=X => 404
  - Tokenomist API (api.tokenomist.ai/v1/protocols) => 404, no public API found
  - Tokenomist website (tokenomist.ai/api/tokens) => returns HTML, no public REST API

Strategy:
  1. Fetch total_supply / circulating_supply from CMC detail endpoint (free, no key needed)
  2. Use hardcoded allocation data from public documentation / whitepapers
  3. Generate template files for protocols without known data
  4. Future: if CMC token-unlock endpoints become available, integrate them

Usage:
  python3 scripts/fetch-tokenomics.py           # fetch all protocols
  python3 scripts/fetch-tokenomics.py aave       # fetch single protocol
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "tokenomics")

# Protocol definitions: id -> { cmcSlug, token, known allocation data }
# Allocation data sourced from project documentation, whitepapers, and public disclosures.
PROTOCOLS = {
    "aave": {
        "cmcSlug": "aave",
        "token": "AAVE",
        "total_supply": 16_000_000,
        "allocation": [
            {"category": "Ecosystem Reserve", "percent": 62.5, "amount": 10_000_000, "color": "#45B7D1"},
            {"category": "Team & Founders", "percent": 18.75, "amount": 3_000_000, "color": "#FF6B6B"},
            {"category": "Investors (Migration)", "percent": 18.75, "amount": 3_000_000, "color": "#4ECDC4"},
        ],
        "unlock_schedule": [
            {"date": "2020-10-01", "amount": 13_000_000, "category": "Migration + Reserve", "cumulative_percent": 81.25},
            {"date": "2023-07-01", "amount": 16_000_000, "category": "Fully vested", "cumulative_percent": 100.0},
        ],
        "source": "Aave Documentation",
    },
    "uniswap": {
        "cmcSlug": "uniswap",
        "token": "UNI",
        "total_supply": 1_000_000_000,
        "allocation": [
            {"category": "Community", "percent": 60, "amount": 600_000_000, "color": "#FF007A"},
            {"category": "Team", "percent": 21.27, "amount": 212_660_000, "color": "#FF6B6B"},
            {"category": "Investors", "percent": 18.04, "amount": 180_440_000, "color": "#4ECDC4"},
            {"category": "Advisors", "percent": 0.69, "amount": 6_900_000, "color": "#45B7D1"},
        ],
        "unlock_schedule": [
            {"date": "2020-09-17", "amount": 150_000_000, "category": "TGE (Community Airdrop)", "cumulative_percent": 15.0},
            {"date": "2021-09-17", "amount": 400_000_000, "category": "Year 1 vesting", "cumulative_percent": 40.0},
            {"date": "2022-09-17", "amount": 650_000_000, "category": "Year 2 vesting", "cumulative_percent": 65.0},
            {"date": "2023-09-17", "amount": 830_000_000, "category": "Year 3 vesting", "cumulative_percent": 83.0},
            {"date": "2024-09-17", "amount": 1_000_000_000, "category": "Fully vested", "cumulative_percent": 100.0},
        ],
        "source": "Uniswap Blog / Governance Docs",
    },
    "pendle": {
        "cmcSlug": "pendle",
        "token": "PENDLE",
        "total_supply": 258_446_028,
        "allocation": [
            {"category": "Incentives & Ecosystem", "percent": 49.3, "amount": 127_500_000, "color": "#00F0FF"},
            {"category": "Team", "percent": 22, "amount": 56_858_000, "color": "#FF6B6B"},
            {"category": "Investors", "percent": 15.7, "amount": 40_576_000, "color": "#4ECDC4"},
            {"category": "Liquidity Bootstrapping", "percent": 7, "amount": 18_091_000, "color": "#45B7D1"},
            {"category": "Ecosystem Fund", "percent": 6, "amount": 15_507_000, "color": "#FFA07A"},
        ],
        "unlock_schedule": [
            {"date": "2021-04-28", "amount": 37_000_000, "category": "TGE + IDO", "cumulative_percent": 14.3},
            {"date": "2022-04-28", "amount": 97_000_000, "category": "Year 1 emissions", "cumulative_percent": 37.5},
            {"date": "2023-04-28", "amount": 143_000_000, "category": "Year 2 emissions", "cumulative_percent": 55.3},
            {"date": "2024-04-28", "amount": 200_000_000, "category": "Year 3 + team cliff", "cumulative_percent": 77.4},
            {"date": "2026-04-28", "amount": 258_446_028, "category": "Fully vested (est.)", "cumulative_percent": 100.0},
        ],
        "source": "Pendle Documentation",
    },
    "curve": {
        "cmcSlug": "curve-dao-token",
        "token": "CRV",
        "total_supply": 3_030_303_031,
        "allocation": [
            {"category": "Community (LP rewards)", "percent": 62, "amount": 1_878_787_879, "color": "#0000FF"},
            {"category": "Shareholders (team & investors)", "percent": 30, "amount": 909_090_909, "color": "#FF6B6B"},
            {"category": "Employees", "percent": 3, "amount": 90_909_091, "color": "#4ECDC4"},
            {"category": "Community Reserve", "percent": 5, "amount": 151_515_152, "color": "#45B7D1"},
        ],
        "unlock_schedule": [
            {"date": "2020-08-13", "amount": 151_515_152, "category": "Initial distribution", "cumulative_percent": 5.0},
            {"date": "2024-08-13", "amount": 1_500_000_000, "category": "4yr vesting + emissions", "cumulative_percent": 49.5},
            {"date": "2026-08-13", "amount": 2_200_000_000, "category": "Ongoing emissions", "cumulative_percent": 72.6},
        ],
        "source": "Curve DAO Documentation",
    },
    "dydx": {
        "cmcSlug": "dydx-chain",
        "token": "DYDX",
        "total_supply": 1_000_000_000,
        "allocation": [
            {"category": "Community Treasury", "percent": 26.1, "amount": 261_000_000, "color": "#6966FF"},
            {"category": "Trading Rewards", "percent": 25, "amount": 250_000_000, "color": "#45B7D1"},
            {"category": "Investors", "percent": 27.7, "amount": 277_000_000, "color": "#4ECDC4"},
            {"category": "Team & Founders", "percent": 15.3, "amount": 153_000_000, "color": "#FF6B6B"},
            {"category": "Liquidity & Safety", "percent": 5.9, "amount": 59_000_000, "color": "#FFA07A"},
        ],
        "unlock_schedule": [
            {"date": "2021-08-03", "amount": 75_000_000, "category": "TGE", "cumulative_percent": 7.5},
            {"date": "2023-02-03", "amount": 300_000_000, "category": "Cliff unlock", "cumulative_percent": 30.0},
            {"date": "2024-08-03", "amount": 700_000_000, "category": "Major vesting", "cumulative_percent": 70.0},
            {"date": "2026-06-01", "amount": 1_000_000_000, "category": "Fully vested", "cumulative_percent": 100.0},
        ],
        "source": "dYdX Foundation Docs",
    },
    "gmx": {
        "cmcSlug": "gmx",
        "token": "GMX",
        "total_supply": 13_250_000,
        "allocation": [
            {"category": "Floor Price Fund", "percent": 26.0, "amount": 3_445_000, "color": "#2D42FC"},
            {"category": "esGMX Reserves", "percent": 22.6, "amount": 2_000_000, "color": "#45B7D1"},
            {"category": "Migration (XVIX/GMT)", "percent": 45.3, "amount": 6_000_000, "color": "#4ECDC4"},
            {"category": "Marketing / Community", "percent": 6.1, "amount": 805_000, "color": "#FFA07A"},
        ],
        "unlock_schedule": [
            {"date": "2021-09-01", "amount": 6_000_000, "category": "Migration", "cumulative_percent": 45.3},
            {"date": "2023-01-01", "amount": 10_000_000, "category": "esGMX vesting", "cumulative_percent": 75.5},
            {"date": "2025-01-01", "amount": 13_250_000, "category": "Fully diluted", "cumulative_percent": 100.0},
        ],
        "source": "GMX Documentation",
    },
}

# Protocols that exist in the dashboard but we don't have allocation data for yet.
# We'll create template files for these.
ALL_PROTOCOL_IDS = [
    "aave", "aster", "bgb", "bnb", "compound", "curve", "dydx",
    "eigenlayer", "ethena", "fluid", "gmx", "hype",
    "jito", "justlend", "kamino", "lido", "maple", "mnt",
    "morpho", "okb", "pancakeswap", "pendle", "sky", "spark", "uniswap",
]


def fetch_cmc_supply(slug):
    """Fetch total_supply and circulating_supply from CMC detail endpoint."""
    url = f"https://api.coinmarketcap.com/data-api/v3/cryptocurrency/detail?slug={slug}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        sd = data.get("data", {}).get("supplyDetails", {})
        return {
            "total_supply": sd.get("totalSupply", {}).get("value"),
            "circulating_supply": sd.get("circulatingSupply", {}).get("value"),
            "max_supply": sd.get("maxSupply", {}).get("value"),
        }
    except Exception as e:
        print(f"  [WARN] CMC fetch failed for {slug}: {e}")
        return {}


def build_protocol_data(pid, cmc_supply=None):
    """Build the tokenomics JSON for a protocol."""
    known = PROTOCOLS.get(pid)
    today = date.today().isoformat()

    if known:
        result = {
            "protocol": pid,
            "token": known["token"],
            "total_supply": known["total_supply"],
            "allocation": known["allocation"],
            "unlock_schedule": known["unlock_schedule"],
            "source": known["source"],
            "updated_at": today,
        }
        # Merge CMC live supply if available
        if cmc_supply:
            if cmc_supply.get("circulating_supply"):
                result["circulating_supply"] = cmc_supply["circulating_supply"]
            if cmc_supply.get("total_supply") and not result.get("total_supply"):
                result["total_supply"] = cmc_supply["total_supply"]
        return result
    else:
        # Create empty template
        result = {
            "protocol": pid,
            "token": pid.upper(),
            "total_supply": None,
            "allocation": [],
            "unlock_schedule": [],
            "source": "N/A - data not yet collected",
            "updated_at": today,
        }
        if cmc_supply and cmc_supply.get("total_supply"):
            result["total_supply"] = cmc_supply["total_supply"]
        return result


def save_json(pid, data):
    """Save tokenomics data to JSON file."""
    filepath = os.path.join(DATA_DIR, f"{pid}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {filepath}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # Determine which protocols to process
    if len(sys.argv) > 1:
        targets = [a for a in sys.argv[1:] if a in ALL_PROTOCOL_IDS]
        if not targets:
            print(f"Unknown protocol(s): {sys.argv[1:]}. Available: {ALL_PROTOCOL_IDS}")
            sys.exit(1)
    else:
        targets = ALL_PROTOCOL_IDS

    print(f"Processing {len(targets)} protocol(s)...")

    for pid in targets:
        print(f"\n[{pid}]")
        known = PROTOCOLS.get(pid)
        cmc_slug = known["cmcSlug"] if known else pid

        # Try to fetch live supply data from CMC
        cmc_supply = fetch_cmc_supply(cmc_slug)
        if cmc_supply.get("total_supply"):
            print(f"  CMC supply: total={cmc_supply['total_supply']:.0f}, circ={cmc_supply.get('circulating_supply', 'N/A')}")
        else:
            print(f"  CMC supply: not available")

        data = build_protocol_data(pid, cmc_supply)
        save_json(pid, data)

        # Rate limit: be polite to CMC
        time.sleep(0.5)

    print(f"\nDone. Files saved to {DATA_DIR}/")


if __name__ == "__main__":
    main()
