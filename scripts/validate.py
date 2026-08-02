#!/usr/bin/env python3
"""
validate.py — Crypto3D 数据校验器（PRD v2.1 第 5.2 / 5.4 节）

校验项（对齐 docs/financial-snapshot-schema.md 第五章）:
  1. 结构校验     data/snapshots/*.json 符合 financial-snapshot.schema.json
  2. 派生自洽     valuation/margins 重算比对（差异 > 0.5% 报错）
  3. 一致性       snapshot 与 all-protocols.json 的 shareholder_yield_percent 数值一致
  4. 新鲜度       as_of 距今 > 26h 告警（防僵尸数据）；data/daily latest.json 同理
  5. null 语义    无数据必须 null，编造的 0 告警

用法:
  python3 scripts/validate.py            # 全量校验
  python3 scripts/validate.py bnb aave   # 指定协议
  python3 scripts/validate.py --strict   # 告警也置为非零退出码
"""

import argparse
import json
import sys
from datetime import datetime, timezone, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
ALL_PROTOCOLS_FILE = DATA_DIR / "all-protocols.json"
SCHEMA_FILE = BASE_DIR / "docs" / "schema" / "financial-snapshot.schema.json"

FRESHNESS_HOURS = 26

# ── 校验结果收集 ─────────────────────────────────────────────────────

class Report:
    def __init__(self, strict=False):
        self.errors = []
        self.warnings = []
        self.strict = strict

    def error(self, proto, msg):
        self.errors.append((proto, msg))
        print(f"  [ERROR] {proto}: {msg}")

    def warn(self, proto, msg):
        self.warnings.append((proto, msg))
        print(f"  [WARN ] {proto}: {msg}")

    @property
    def failed(self):
        return bool(self.errors) or (self.strict and bool(self.warnings))


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


# ── 派生重算（与 build-snapshot.py 保持一致） ───────────────────────

def recompute_valuation(bs, income, returns):
    mcap = bs.get("market_cap_usd")
    revenue = income.get("revenue", {}).get("revenue_included", {}).get("total_usd_365d")
    returns_usd = returns.get("summary", {}).get("shareholder_returns_usd_365d")
    net_income = income.get("net_income", {}).get("net_income_usd_365d")
    pe = mcap / returns_usd if (mcap and returns_usd) else None
    ps = mcap / revenue if (mcap and revenue) else None
    payout = returns_usd / net_income if (returns_usd and net_income and net_income > 0) else None
    return {"pe": round(pe, 4) if pe else None,
            "ps": round(ps, 4) if ps else None,
            "payout_ratio": round(payout, 4) if payout else None}


def recompute_margins(income):
    revenue = income.get("revenue", {}).get("revenue_included", {}).get("total_usd_365d")
    gp = income.get("gross_profit", {}).get("gross_profit_usd_365d")
    ni = income.get("net_income", {}).get("net_income_usd_365d")
    gm = gp / revenue * 100 if (revenue and gp is not None) else None
    nm = ni / revenue * 100 if (revenue and ni is not None) else None
    return {"gross_margin_percent": round(gm, 4) if gm is not None else None,
            "net_margin_percent": round(nm, 4) if nm is not None else None}


def recompute_holder_summary(by_mechanism, mcap):
    destroy_usd = sum(m.get("usd_365d") or 0 for m in by_mechanism if m.get("type") in ("destroy", "buyback"))
    yield_usd = sum(m.get("usd_365d") or 0 for m in by_mechanism if m.get("type") == "yield")
    total = destroy_usd + yield_usd
    return {"destroy_usd_365d": round(destroy_usd, 2) if destroy_usd else None,
            "yield_usd_365d": round(yield_usd, 2) if yield_usd else None,
            "destroy_yield_percent": round(destroy_usd / mcap * 100, 4) if (mcap and destroy_usd) else None,
            "yield_yield_percent": round(yield_usd / mcap * 100, 4) if (mcap and yield_usd) else None,
            "shareholder_returns_usd_365d": round(total, 2) if total else None,
            "shareholder_yield_percent": round(total / mcap * 100, 4) if (mcap and total) else None}


def pct_diff(a, b):
    """相对差异百分比（用较大的作分母）。None 与 0 视为等价：
    GMX 等机制确凿为 0 的协议，文件写 0、by_mechanism 无值重算 None，语义相同。"""
    if a is None and b is None:
        return 0.0
    if a is None or b is None:
        other = a if b is None else b
        if other == 0:
            return 0.0  # 0 ≡ None（机制确凿零 vs 数据不可得，但绝对值 0 等价）
        return 100.0
    denom = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / denom * 100


# ── 结构校验（轻量 JSON Schema） ────────────────────────────────────

def validate_structure(snap, report, proto):
    """按 financial-snapshot.schema.json 做结构校验（核心必填 + 类型）。"""
    required_top = ["protocol", "as_of", "income_statement", "holder_returns",
                    "balance_sheet", "valuation", "verification"]
    for k in required_top:
        if k not in snap:
            report.error(proto, f"缺少顶层字段 {k}")
            return False

    if snap.get("protocol") != proto:
        report.error(proto, f"protocol 字段 {snap.get('protocol')} != 目录名 {proto}")

    rr = snap.get("income_statement", {}).get("revenue", {})
    if rr.get("entity_type") not in ("platform_token", "public_chain", "app"):
        report.error(proto, f"entity_type 非法: {rr.get('entity_type')}")

    # valuation 字段必须存在（可为 null）
    for k in ("pe", "ps", "pb", "ev_revenue", "payout_ratio"):
        if k not in snap.get("valuation", {}):
            report.error(proto, f"valuation 缺少 {k}")

    ver = snap.get("verification", {})
    if ver.get("status") not in ("verified", "partial", "estimated"):
        report.warn(proto, f"verification.status 非法: {ver.get('status')}")
    return True


# ── 主校验 ───────────────────────────────────────────────────────────

def validate_snapshot(snap, all_protocols, report, proto):
    if not validate_structure(snap, report, proto):
        return

    # 2. 派生自洽
    exp_val = recompute_valuation(snap["balance_sheet"], snap["income_statement"], snap["holder_returns"])
    for k, exp in exp_val.items():
        actual = snap["valuation"].get(k)
        if pct_diff(exp, actual) > 0.5:
            report.error(proto, f"valuation.{k} 派生不自洽: 文件={actual} 重算={exp}")

    exp_margin = recompute_margins(snap["income_statement"])
    for k, exp in exp_margin.items():
        actual = snap["income_statement"]["margins"].get(k)
        if pct_diff(exp, actual) > 0.5:
            report.error(proto, f"margins.{k} 派生不自洽: 文件={actual} 重算={exp}")

    exp_summary = recompute_holder_summary(snap["holder_returns"].get("by_mechanism", []),
                                           snap["balance_sheet"].get("market_cap_usd"))
    for k in ("destroy_usd_365d", "yield_usd_365d", "shareholder_returns_usd_365d",
              "destroy_yield_percent", "yield_yield_percent", "shareholder_yield_percent"):
        exp = exp_summary.get(k)
        actual = snap["holder_returns"]["summary"].get(k)
        if pct_diff(exp, actual) > 0.5:
            report.error(proto, f"holder_returns.summary.{k} 不自洽: 文件={actual} 重算={exp}")

    # 3. 一致性：snapshot yield 与 all-protocols.json 一致
    ap = (all_protocols or {}).get("protocols", {}).get(proto, {})
    ap_yield = ap.get("tev_yield_percent") or ap.get("shareholder_yield_percent")
    snap_yield = snap["holder_returns"]["summary"].get("shareholder_yield_percent")
    if ap_yield is not None and snap_yield is not None and pct_diff(ap_yield, snap_yield) > 1.0:
        report.warn(proto, f"与 all-protocols.json 不一致: snapshot={snap_yield}% all-protocols={ap_yield}%")

    # 3.5 entity_type 一致性（M1 补：snapshot 必须与 config 判定书一致）
    config = load_json(BASE_DIR / "data" / "protocols" / proto / "config.json")
    if config:
        cfg_et = config.get("revenue_recognition", {}).get("entity_type")
        snap_et = snap.get("income_statement", {}).get("revenue", {}).get("entity_type")
        if cfg_et and cfg_et != snap_et:
            report.error(proto, f"entity_type 与 config 判定书不一致: snapshot={snap_et} config={cfg_et}")
        # config 判定书缺失时告警（新增协议必须写判定书）
        if not config.get("revenue_recognition"):
            report.warn(proto, "config 缺少 revenue_recognition（判定书）")
        if not config.get("data_pipeline"):
            report.warn(proto, "config 缺少 data_pipeline（数据源声明）")

    # 4. 新鲜度
    try:
        as_of = datetime.strptime(snap["as_of"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        hours = (datetime.now(timezone.utc) - as_of).total_seconds() / 3600
        if hours > FRESHNESS_HOURS:
            report.error(proto, f"快照过期 {hours:.0f}h (> {FRESHNESS_HOURS}h)，as_of={snap['as_of']}")
    except ValueError:
        report.error(proto, f"as_of 格式非法: {snap['as_of']}")

    # 5. null 语义：编造的 0 告警（revenue 有值但 gross/net 为 0 时）
    revenue = snap["income_statement"]["revenue"]["revenue_included"].get("total_usd_365d")
    ni = snap["income_statement"]["net_income"].get("net_income_usd_365d")
    if revenue and ni == 0:
        report.warn(proto, "收入有值但净利=0，确认是否应为 null（禁止编造 0）")


def main():
    parser = argparse.ArgumentParser(description="Crypto3D 数据校验器")
    parser.add_argument("protocols", nargs="*", help="指定协议；默认全部")
    parser.add_argument("--strict", action="store_true", help="警告也视为失败")
    args = parser.parse_args()

    report = Report(strict=args.strict)
    all_protocols = load_json(ALL_PROTOCOLS_FILE)

    snap_files = sorted(SNAPSHOTS_DIR.glob("*.json"))
    if args.protocols:
        snap_files = [f for f in snap_files if f.stem in args.protocols]

    if not snap_files:
        print("没有可校验的 snapshot（先运行 scripts/build-snapshot.py）")
        sys.exit(1)

    print(f"校验 {len(snap_files)} 个 snapshot...")
    for f in snap_files:
        proto = f.stem
        snap = load_json(f)
        if snap is None:
            report.error(proto, "JSON 解析失败")
            continue
        validate_snapshot(snap, all_protocols, report, proto)

    # data/daily 新鲜度（僵尸数据哨兵）
    print("\ndata/daily 新鲜度检查（防僵尸数据）：")
    stale_daily = []
    daily_dir = DATA_DIR / "daily"
    for d in sorted(daily_dir.iterdir()):
        if not d.is_dir():
            continue
        latest = d / "latest.json"
        if not latest.exists():
            stale_daily.append((d.name, "missing latest.json"))
            continue
        data = load_json(latest)
        if not data:
            stale_daily.append((d.name, "JSON 解析失败"))
            continue
        upd = data.get("updated_at")
        if not upd:
            stale_daily.append((d.name, "无 updated_at"))
            continue
        try:
            # 兼容多种时间格式
            upd_norm = upd.replace("Z", "+00:00")
            dt = datetime.fromisoformat(upd_norm)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            if hours > FRESHNESS_HOURS:
                stale_daily.append((d.name, f"停更 {hours:.0f}h (updated_at={upd})"))
        except ValueError:
            stale_daily.append((d.name, f"updated_at 解析失败: {upd}"))

    if stale_daily:
        for name, why in stale_daily:
            report.error(name, f"僵尸数据: {why}")
    else:
        print("  ✓ 全部 fresh")

    print(f"\n结果: {len(report.errors)} errors, {len(report.warnings)} warnings")
    if report.failed:
        sys.exit(1)
    print("✅ 校验通过")


if __name__ == "__main__":
    main()
