#!/usr/bin/env python3
"""为没有同口径日频来源的协议重置历史图。

这些协议仍展示最新 TTM，但不把旧年化均摊、0 或缓存回购伪装为单日净收益。
一旦接入可复算的日频来源，再用专属 history builder 替换本脚本的占位记录。
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SNAPSHOTS = BASE / "data" / "snapshots"
HISTORY = BASE / "data" / "history"

UNAVAILABLE = {
    "aster": "当前 TTM 有验证缓存，但没有同口径的 DefiLlama 日频净收入序列。",
    "bgb": "季度销毁可验证；没有可复算的日频回购执行数据。",
    "compound": "当前协议收入没有可复算的日频净收入来源。",
    "mnt": "TTM 来自平台币赋能口径，DefiLlama Mantle 日费并非同一收入定义。",
    "okb": "TTM 来自平台币质押收益口径，缺少同口径日频来源。",
}


def main():
    HISTORY.mkdir(exist_ok=True)
    for pid, note in UNAVAILABLE.items():
        snap = json.loads((SNAPSHOTS / f"{pid}.json").read_text(encoding="utf-8"))
        income = snap.get("income_statement", {})
        record = {
            "as_of": snap["as_of"],
            "net_income": income.get("net_income", {}).get("net_income_usd_365d"),
            "pe": snap.get("valuation", {}).get("pe"),
            "ps": snap.get("valuation", {}).get("ps"),
            "shareholder_yield": snap.get("holder_returns", {}).get("summary", {}).get("shareholder_yield_percent"),
            "net_margin": income.get("margins", {}).get("net_margin_percent"),
            "daily_value": None,
            "daily_value_status": "unavailable",
            "daily_value_note": note,
        }
        out = {"protocol": pid, "records": [record]}
        (HISTORY / f"{pid}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"  ✓ {pid}: 单日净收益标记为不可得")


if __name__ == "__main__":
    main()
