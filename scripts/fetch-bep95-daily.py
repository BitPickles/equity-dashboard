#!/usr/bin/env python3
"""Append missing BNB BEP-95 daily burns using the 0xdead balance delta.

The BSC dead address receives both continuous BEP-95 burns and quarterly
Auto-Burns. This job records only the former as an evenly allocated daily
delta; official quarterly burns remain read-only in burn-history.json.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
BNB_DIR = BASE / "data" / "protocols" / "bnb"
HISTORY_PATH = BNB_DIR / "bep95-history.json"
SNAPSHOT_PATH = BNB_DIR / "dead-balance-snapshot.json"
BURN_PATH = BNB_DIR / "burn-history.json"
DEAD_ADDRESS = "0x000000000000000000000000000000000000dEaD"
RPC_ENDPOINTS = (
    "https://bsc-dataseed.binance.org",
    "https://bsc-dataseed1.binance.org",
    "https://bsc-dataseed1.defibit.io",
    "https://bsc-dataseed1.ninicoin.io",
    "https://bsc-rpc.publicnode.com",
)
MAX_DAILY_BNB = Decimal("2000")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def latest_dead_balance():
    """Read the native BNB balance from the first healthy public BSC endpoint."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getBalance",
        "params": [DEAD_ADDRESS, "latest"],
    }).encode("utf-8")
    failures = []
    for endpoint in RPC_ENDPOINTS:
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "crypto3d-bep95-updater/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
            value = body.get("result")
            if not isinstance(value, str) or not value.startswith("0x"):
                raise ValueError(f"invalid eth_getBalance response: {body}")
            return Decimal(int(value, 16)) / Decimal(10**18), endpoint
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            failures.append(f"{endpoint}: {exc}")
    raise RuntimeError("all BSC RPC endpoints failed:\n" + "\n".join(failures))


def require_complete_daily_series(daily):
    """Reject malformed input before appending; this job never rewrites old rows."""
    if not daily:
        raise ValueError("bep95 daily[] is empty")
    parsed = [date.fromisoformat(row["date"]) for row in daily]
    if parsed != sorted(parsed) or len(set(parsed)) != len(parsed):
        raise ValueError("daily[] must be strictly increasing without duplicate dates")
    for previous, current in zip(parsed, parsed[1:]):
        if current != previous + timedelta(days=1):
            raise ValueError(f"daily[] has a gap: {previous} -> {current}")
    return parsed[-1]


def main():
    today = datetime.now(timezone.utc).date()
    history = load_json(HISTORY_PATH)
    dead_snapshot = load_json(SNAPSHOT_PATH)
    burns = load_json(BURN_PATH)
    daily = history.get("daily") or []
    last_daily_date = require_complete_daily_series(daily)
    snapshot_date = date.fromisoformat(dead_snapshot["date"])

    if snapshot_date != last_daily_date:
        raise ValueError(
            f"snapshot date ({snapshot_date}) must equal latest daily date ({last_daily_date}); refusing an ambiguous delta"
        )
    if snapshot_date > today:
        raise ValueError(f"snapshot date {snapshot_date} is in the future (UTC today: {today})")
    if snapshot_date == today:
        print(f"✓ BEP-95 already current through {today}; no rows appended")
        return 0

    current_balance, endpoint = latest_dead_balance()
    old_balance = Decimal(str(dead_snapshot["balance_bnb"]))
    raw_delta = current_balance - old_balance
    if raw_delta <= 0:
        raise RuntimeError(
            f"aborting: dead-address delta must be positive; old={old_balance}, current={current_balance}, delta={raw_delta}"
        )

    # Quarterly burns are official, manually verified data. Only subtract the
    # already-recorded ones in the delta window; this script never changes them.
    quarterly = Decimal("0")
    included_quarters = []
    for row in burns.get("quarterly_burns", []):
        burn_date = date.fromisoformat(row["date"])
        if snapshot_date < burn_date <= today:
            amount = Decimal(str(row["bnb_burned"]))
            quarterly += amount
            included_quarters.append((row.get("number"), burn_date.isoformat(), amount))

    bep95_delta = raw_delta - quarterly
    if bep95_delta <= 0:
        raise RuntimeError(
            f"aborting: delta after official quarterly-burn deduction must be positive; "
            f"raw={raw_delta}, quarterly={quarterly}, bep95={bep95_delta}, quarters={included_quarters}"
        )

    missing_days = (today - last_daily_date).days
    daily_amount = bep95_delta / Decimal(missing_days)
    if daily_amount > MAX_DAILY_BNB:
        raise RuntimeError(
            f"aborting: implausible BEP-95 average {daily_amount} BNB/day (> {MAX_DAILY_BNB}); "
            f"raw={raw_delta}, quarterly={quarterly}, days={missing_days}, quarters={included_quarters}"
        )

    # Quantise all but the final row; the final row absorbs the residual so the
    # appended serialised values reconcile exactly to the balance delta.
    appended = []
    running = Decimal("0")
    for offset in range(1, missing_days + 1):
        amount = daily_amount.quantize(Decimal("0.000000001"))
        if offset == missing_days:
            amount = bep95_delta - running
        running += amount
        appended.append({
            "date": (last_daily_date + timedelta(days=offset)).isoformat(),
            "bnb": float(amount),
            "tx_count": None,
            "source": "rpc_delta",
        })

    history["daily"] = daily + appended
    history["updated_at"] = datetime.now(timezone.utc).isoformat()
    HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SNAPSHOT_PATH.write_text(json.dumps({
        "date": today.isoformat(),
        "balance_bnb": float(current_balance),
    }, indent=2) + "\n", encoding="utf-8")
    print(
        f"✓ appended {missing_days} BEP-95 days ({appended[0]['date']} → {appended[-1]['date']}); "
        f"dead={current_balance} BNB via {endpoint}; raw_delta={raw_delta}; "
        f"quarterly_deducted={quarterly}; bep95_delta={bep95_delta}; daily={daily_amount}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"✗ {exc}", file=sys.stderr)
        raise SystemExit(1)
