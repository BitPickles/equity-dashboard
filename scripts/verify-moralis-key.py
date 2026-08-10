#!/usr/bin/env python3
"""MORALIS key 轮换验证脚本（2026-08-06）

用法：
  1. 在 admin.moralis.com → Web3 APIs → 复制新 API key
  2. 填入 .env: MORALIS_API_KEY=新key
  3. 运行: python3 scripts/verify-moralis-key.py
     - 用 .env 新 key 拉一次数据（应成功）
     - 用旧 key 拉一次（应失败/401 → 确认旧 key 已失效）

依赖：requests 或标准库（用 urllib）
"""
import json
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OLD_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjdmYWFmNTdkLTNiOWQtNGNhNS1hNGY3LTExZGI4Y2YyYzBlNiIsIm9yZ0lkIjoiNTAwNDkyIiwidXNlcklkIjoiNTE0OTg0IiwidHlwZUlkIjoiMjA4MzcyMWEtZmJjMC00NzQzLWEzNGItNGEyYmFlY2ExNTNlIiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NzA5OTIwNTMsImV4cCI6NDkyNjc1MjA1M30.Ef1yoypuIgSdnMMFnB9aFaDX6ILinqWuchJ8npxEZrA"

WALLET = "0xa0edBaBcb48034e368de286b49F9603C7AfA1b60"
ASTER = "0x000ae314e2a2172a039b26378814c252734f556a"


def read_new_key():
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("MORALIS_API_KEY="):
                val = line.split("=", 1)[1].strip()
                if val:
                    return val
    return None


def test_key(key, label):
    url = f"https://deep-index.moralis.io/api/v2.2/{WALLET}/erc20/transfers?chain=bsc&contract_addresses={ASTER}&limit=1"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0', 'X-API-Key': key, 'accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
            n = len(d.get('result', []))
            print(f'  {label}: ✅ 有效（返回 {n} 条）')
            return True
    except urllib.error.HTTPError as e:
        print(f'  {label}: ❌ HTTP {e.code}（{e.reason}）')
        return False
    except Exception as e:
        print(f'  {label}: ❌ {str(e)[:60]}')
        return False


def main():
    print("=== MORALIS key 轮换验证 ===")
    new_key = read_new_key()
    if not new_key:
        print("❌ .env 中 MORALIS_API_KEY 为空——请先在 admin.moralis.com 生成新 key 填入")
        return

    print(f"\n新 key（.env 中）:")
    test_key(new_key, "新 key")
    print(f"\n旧 key（历史泄露值）:")
    test_key(OLD_KEY, "旧 key")
    print("\n结论：新 key ✅ + 旧 key ❌ = 轮换成功；新 key ✅ + 旧 key ✅ = 旧 key 未失效，需在后台删除")


if __name__ == "__main__":
    main()
