#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan-aster-onchain.py — 直连 BSC RPC 扫描 Aster 回购钱包链上转入（不依赖 Moralis）

⚠️ 状态（2026-10-07）：手动工具，未接入 daily-run（公共 RPC 限流不可控）。
  - 公共 bsc-dataseed 有请求量限流，长窗口扫描易触发 limit exceeded；
  - 本机网络实测：Etherscan v2 免费层不支持 BSC、ankr 需 key、meowrpc 不支持 getLogs。
  - 结论：可靠的常态化采集仍需 Moralis key（Mac Mini .env 配置 MORALIS_API_KEY）。
  - 2026-10-07 用本脚本思路（eth_getLogs 直查）核实：6-17 新机制三钱包转入≈0，
    TWAP 钱包余额仅 30 ASTER——采集停摆期间链上确无执行量，数据缺口非故障。

用法:
  python3 scripts/scan-aster-onchain.py [--dry-run] [--from 2026-06-17]
依赖: 无（公共 RPC，无需 key）；--from 控制扫描起点
"""
import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone, date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "aster-onchain.json"

ASTER = "0x000ae314e2a2172a039b26378814c252734f556a"
WALLETS = {
    "s4_buyback": "0x573ca9FF6b7f164dfF513077850d5CD796006fF4",
    "new_twap_buyback": "0xa0edBaBcb48034e368de286b49F9603C7AfA1b60",
    "new_listing_fee": "0x39C473f4420e4ae9Ab3fe9e7ceDFc08F9684bB1a",
}
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

RPCS = [
    "https://bsc-dataseed.binance.org/",
    "https://bsc-dataseed1.defibit.io/",
    "https://bsc-dataseed1.ninicoin.io/",
    "https://bsc-dataseed2.defibit.io/",
    "https://bsc-dataseed2.ninicoin.io/",
    "https://bsc-dataseed3.defibit.io/",
    "https://bsc-dataseed3.ninicoin.io/",
    "https://bsc-dataseed4.defibit.io/",
    "https://bsc-dataseed4.ninicoin.io/",
]
STEP = 15000  # 实测 bsc-dataseed 单次 20000 块 OK；15000 留余量（≈1.9h 链上时间/页）
PAGE_SLEEP = 3.0  # 页间限速，避免公共节点 limit exceeded


def rpc(method, params, rpc_i=[0]):
    last_err = None
    for attempt in range(len(RPCS) * 3):
        url = RPCS[rpc_i[0] % len(RPCS)]
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                headers={"Content-Type": "application/json"},
            )
            r = json.loads(urllib.request.urlopen(req, timeout=45).read())
            if "error" in r:
                raise RuntimeError(r["error"].get("message", "rpc error"))
            return r["result"]
        except Exception as e:
            last_err = e
            rpc_i[0] += 1  # rotate RPC
            time.sleep(min(2 + attempt * 2, 15))  # 退避：2s → 15s
    raise RuntimeError(f"all RPCs failed: {last_err}")


def pad(a):
    return "0x" + "0" * 24 + a[2:].lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from", dest="from_date", default="2026-06-17")
    args = ap.parse_args()
    target = date.fromisoformat(args.from_date)

    cur = int(rpc("eth_blockNumber", []), 16)
    # 实测块距动态估起点（BSC 0.45s/块，粗估后用块时间戳二分校准一次）
    b_now = rpc("eth_getBlockByNumber", [hex(cur), False])
    t_now = int(b_now["timestamp"], 16)
    target_ts = datetime.fromisoformat(args.from_date).replace(tzinfo=timezone.utc).timestamp()
    est = cur - int((t_now - target_ts) / 0.45)
    est = max(est, 1)
    b_est = rpc("eth_getBlockByNumber", [hex(est), False])
    t_est = int(b_est["timestamp"], 16)
    # 线性修正一轮
    est2 = est + int((target_ts - t_est) / 0.45)
    est2 = max(est2, 1)
    print(f"扫描窗口: block {est2} → {cur}（{args.from_date} 起，{cur - est2:,} 块）")

    records = []
    CHUNK = 2_000_000  # 实测 bsc-dataseed 单窗口 250 万块 OK（aster 转账稀疏）；
    # 顺向分块（每块 ≤CHUNK），请求数 = 窗口/CHUNK ≈ 11 次/钱包。
    # ⚠️ 教训（2026-10-07 三次失败）：超大窗口首发 + 二分重试会触发请求量限流
    # （limit exceeded 风暴）；必须用有界分块顺向走。

    def get_logs_chunked(wallet, lo, hi):
        """顺向有界分块拉取 [lo, hi] 的 Transfer 日志。"""
        out = []
        start = lo
        while start <= hi:
            end = min(start + CHUNK - 1, hi)
            logs = rpc("eth_getLogs", [{
                "address": ASTER,
                "topics": [TRANSFER_TOPIC, None, pad(wallet)],
                "fromBlock": hex(start), "toBlock": hex(end),
            }])
            if logs is None:
                logs = []
            out.extend(logs)
            done = end - lo + 1
            total_blocks = hi - lo + 1
            print(f"    block {start:,}~{end:,}（{done * 100 // total_blocks}%）累计 {len(out)} 条", flush=True)
            start = end + 1
            time.sleep(PAGE_SLEEP)
        return out

    for name, wallet in WALLETS.items():
        total_amt, total_tx = 0.0, 0
        logs = get_logs_chunked(wallet, est2, cur)
        for lg in logs:
            val = int(lg["data"], 16) / 1e18 if lg["data"] not in ("0x", "") else 0
            blk = int(lg["blockNumber"], 16)
            total_amt += val
            total_tx += 1
            records.append({"_block": blk, "_val": val, "_tx": lg["transactionHash"], "stage": name})
        print(f"📊 {name}: {total_tx} 笔转入, 共 {total_amt:,.2f} ASTER（{args.from_date} 起）")

    # 块时间戳批量转日期（同块只查一次）
    blk_cache = {}
    for r in records:
        if r["_block"] not in blk_cache:
            b = rpc("eth_getBlockByNumber", [hex(r["_block"]), False])
            blk_cache[r["_block"]] = datetime.fromtimestamp(int(b["timestamp"], 16), timezone.utc).strftime("%Y-%m-%d")

    daily = {}
    txcount = {}
    for r in records:
        d = blk_cache[r["_block"]]
        key = (d, r["stage"])
        daily[key] = daily.get(key, 0) + r["_val"]
        txcount[key] = txcount.get(key, 0) + 1

    new_records = [
        {"date": d, "aster": round(v, 2), "txs": txcount[(d, s)], "stage": s, "source": "bsc_rpc"}
        for (d, s), v in sorted(daily.items())
    ]

    if args.dry_run:
        print(f"[dry-run] 将写入 {len(new_records)} 天记录:")
        for r in new_records[-10:]:
            print("  ", r)
        return

    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    by_key = {(r["date"], r.get("stage", "")): r for r in existing}
    for r in new_records:
        by_key[(r["date"], r["stage"])] = r
    merged = sorted(by_key.values(), key=lambda x: (x["date"], x.get("stage", "")))
    OUT.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ 已写入 {OUT.name}（共 {len(merged)} 天记录，新增 {len(new_records)}）")


if __name__ == "__main__":
    main()
