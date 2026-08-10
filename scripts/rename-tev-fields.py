#!/usr/bin/env python3
"""
rename-tev-fields.py — TEV → 美股术语字段名替换（阶段 1）

Boss 2026-08-04 拍板：全改（含目录/仓库）。
本脚本只处理字段名/键名（结构性替换，不影响英文单词内容）：

  shareholder_yield_percent        → shareholder_yield_percent
  payout_ratio                → payout_ratio
  payout_ratio                 → payout_ratio
  return_mechanisms           → return_mechanisms
  total_yield_percent    → total_yield_percent

用法: python3 scripts/rename-tev-fields.py [--dry-run]
"""
import argparse
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", ".workbuddy", "__pycache__"}
# 精确整词替换（不误伤英文单词如 "steve"）
REPLACEMENTS = {
    "tev_yield_percent": "shareholder_yield_percent",
    "tev_ratio": "payout_ratio",
    "tevRatio": "payout_ratio",
    "tev_mechanisms": "return_mechanisms",
    "earning_yield_percent": "total_yield_percent",
    # metrics 嵌套键（阶段 1 漏改，2026-08-05 补——口径如下）
    #   tev_yield_*_ann = 股东回报率周期 → shareholder_yield_*_ann
    #   earning_yield_*_ann = 收入收益率周期 → total_yield_*_ann
    #   trailing_*_tev_usd = 股东回报金额 → trailing_*_shareholder_returns_usd
    "tev_yield_7d_ann": "shareholder_yield_7d_ann",
    "tev_yield_30d_ann": "shareholder_yield_30d_ann",
    "tev_yield_90d_ann": "shareholder_yield_90d_ann",
    "tev_yield_365d_ann": "shareholder_yield_365d_ann",
    "earning_yield_7d_ann": "total_yield_7d_ann",
    "earning_yield_30d_ann": "total_yield_30d_ann",
    "earning_yield_90d_ann": "total_yield_90d_ann",
    "trailing_30d_tev_usd": "trailing_30d_shareholder_returns_usd",
    "trailing_365d_tev_usd": "trailing_365d_shareholder_returns_usd",
    # 展示/周期字段（前端同步改，2026-08-05 补）
    "tevRatio_7d": "payout_ratio_7d",
    "tevRatio_30d": "payout_ratio_30d",
    "tevRatio_90d": "payout_ratio_90d",
    "tevRatio_365d": "payout_ratio_365d",
    "tevRatioNote": "payout_ratio_note",
    "tevStatus": "return_status",
    "tev_summary": "return_summary",
}


def iter_files():
    for p in BASE.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(BASE)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.suffix not in (".py", ".js", ".json", ".md", ".html", ".css"):
            continue
        yield p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    changed_files = []
    total_repl = 0
    for p in iter_files():
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        orig = text
        n = 0
        for old, new in REPLACEMENTS.items():
            # 整词边界替换（词前/后不能是字母数字下划线）
            text, cnt = re.subn(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])", new, text)
            n += cnt
        if text != orig:
            changed_files.append(p)
            total_repl += n
            if not args.dry_run:
                p.write_text(text, encoding="utf-8")

    print(f"替换了 {total_repl} 处，涉及 {len(changed_files)} 个文件")
    if args.dry_run:
        print("[DRY] 未写文件")
    else:
        print("✅ 已写入")
    return 0


if __name__ == "__main__":
    sys.exit(main())
