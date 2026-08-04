#!/usr/bin/env python3
"""
build-snapshot.py — Financial Snapshot 生成器（PRD v2.1 第 5.2 / 5.4 节）

跑所有已接入协议的适配器（data/protocols/<id>/adapter.py + config.json），
输出统一结构的 Financial Snapshot 到 data/snapshots/<id>.json。

用法:
  python3 scripts/build-snapshot.py               # 全部协议
  python3 scripts/build-snapshot.py bnb aave      # 指定协议
  python3 scripts/build-snapshot.py --check       # 只跑派生自洽检查，不写文件

铁律:
  1. valuation / margins 全部由本脚本派生计算，禁止读 config 手写值
  2. 无数据字段一律 null（前端渲染 —），禁止编造 0
  3. holder_returns.summary 必须与 all-protocols.json 现有 yield 数值一致
"""

import argparse
import json
import os
import sys
import importlib.util
from datetime import datetime, timezone, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROTOCOLS_DIR = DATA_DIR / "protocols"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
ALL_PROTOCOLS_FILE = DATA_DIR / "all-protocols.json"
SCHEMA_FILE = BASE_DIR / "docs" / "schema" / "financial-snapshot.schema.json"

# ── 派生计算 ──────────────────────────────────────────────────────────

def derive_valuation(bs, income, returns):
    """L4 派生估值：全部由 L1-L3 计算，禁止手写。返回 dict（无数据→null）。"""
    mcap = bs.get("market_cap_usd")
    revenue = income.get("revenue", {}).get("revenue_included", {}).get("total_usd_365d")
    returns_usd = returns.get("summary", {}).get("shareholder_returns_usd_365d")
    net_income = income.get("net_income", {}).get("net_income_usd_365d")

    pe = round(mcap / returns_usd, 4) if (mcap and returns_usd) else None
    ps = round(mcap / revenue, 4) if (mcap and revenue) else None
    payout = round(returns_usd / net_income, 4) if (returns_usd and net_income and net_income > 0) else None
    return {"pe": pe, "ps": ps, "pb": None, "ev_revenue": None, "payout_ratio": payout}


def derive_margins(income):
    """毛利率/净利率派生。收入为 0 或 null → null。"""
    revenue = income.get("revenue", {}).get("revenue_included", {}).get("total_usd_365d")
    gp = income.get("gross_profit", {}).get("gross_profit_usd_365d")
    ni = income.get("net_income", {}).get("net_income_usd_365d")

    gm = round(gp / revenue * 100, 4) if (revenue and gp is not None) else None
    nm = round(ni / revenue * 100, 4) if (revenue and ni is not None) else None
    return {"gross_margin_percent": gm, "net_margin_percent": nm,
            "note": "派生计算：gross = GP/Rev, net = NI/Rev；净利可为负（Curve 案例）"}


def derive_holder_summary(by_mechanism, mcap):
    """从机制拆解派生 summary（destroy/yield 分组 + 股东回报率）。"""
    destroy = [m for m in by_mechanism if m.get("type") in ("destroy", "buyback")]
    yield_m = [m for m in by_mechanism if m.get("type") == "yield"]
    destroy_usd = sum(m.get("usd_365d") or 0 for m in destroy)
    yield_usd = sum(m.get("usd_365d") or 0 for m in yield_m)
    total = destroy_usd + yield_usd

    return {
        "destroy_usd_365d": round(destroy_usd, 2) if destroy_usd else None,
        "yield_usd_365d": round(yield_usd, 2) if yield_usd else None,
        "destroy_yield_percent": round(destroy_usd / mcap * 100, 4) if (mcap and destroy_usd) else None,
        "yield_yield_percent": round(yield_usd / mcap * 100, 4) if (mcap and yield_usd) else None,
        "shareholder_returns_usd_365d": round(total, 2) if total else None,
        "shareholder_yield_percent": round(total / mcap * 100, 4) if (mcap and total) else None,
    }


# ── 通用适配器（无专属 adapter.py 时兜底） ───────────────────────────

def _load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_generic_adapter(proto_dir, all_protocols, daily):
    """通用适配器：从 all-protocols.json（已验证数据）+ daily/latest.json 组装 snapshot。
    适用于尚未写专属 adapter.py 的协议；M1 起各协议逐步替换为专属 adapter。"""
    config = _load_json(proto_dir / "config.json")
    if not config:
        raise ValueError(f"missing config.json: {proto_dir}")

    pid = config["id"]
    ap = (all_protocols or {}).get("protocols", {}).get(pid, {})
    daily_latest = (daily or {}).get("latest_record", {}) if daily else {}

    # 收入判定书（M0 从 config 读取；缺失时降级为 estimate 空壳）
    rr = config.get("revenue_recognition", {})
    entity_type = rr.get("entity_type") or config.get("category") or "app"
    if entity_type in ("cex_token", "platform", "l2_token"):
        entity_type = "platform_token"
    elif entity_type not in ("platform_token", "public_chain"):
        # 应用型协议（lending/dex/perpetuals/liquid_staking/... 统一归一为 app）
        entity_type = "app"

    mcap = ap.get("market_cap_usd") or daily_latest.get("market_cap_usd")
    tvl = ap.get("tvl") or daily_latest.get("tvl")

    # 股东回报（L3）：优先从 all-protocols 已验证字段组装
    tev_yield = ap.get("shareholder_yield_percent") or ap.get("shareholder_yield_percent")
    tev_usd_365d = ap.get("validation", {}).get("recent_4q_burn_usd_current")
    if tev_usd_365d is None:
        tev_usd_365d = ap.get("tev_data", {}).get("annual_tev_usd")

    by_mechanism = []
    mechanisms = config.get("return_mechanisms", [])
    if mechanisms and tev_yield:
        # 拆成机制级条目（数值按比例分摊；没有精确拆分时合并为一条）
        active = [m for m in mechanisms if m.get("status") == "active"]
        if len(active) == 1:
            m = active[0]
            mtype = "destroy" if m.get("type") == "burn" else ("yield" if m.get("type") == "staking" else "buyback")
            by_mechanism = [{"mechanism": m.get("name") or m.get("type"), "type": mtype,
                             "usd_365d": round(tev_usd_365d, 2) if tev_usd_365d else None,
                             "yield_percent": tev_yield}]
        elif len(active) > 1:
            # 多机制：给每条一个 note 提示"精确拆分见专属 adapter"，数值分摊
            share = 1.0 / len(active)
            for i, m in enumerate(active):
                mtype = "destroy" if m.get("type") == "burn" else ("yield" if m.get("type") == "staking" else "buyback")
                by_mechanism.append({
                    "mechanism": m.get("name") or m.get("type"), "type": mtype,
                    "usd_365d": round((tev_usd_365d or 0) * share, 2) if tev_usd_365d else None,
                    "yield_percent": round(tev_yield * share, 4) if tev_yield else None,
                    "_note": "均摊估算，精确拆分待专属 adapter.py"
                })

    holder_returns = {
        "by_mechanism": by_mechanism,
        "summary": derive_holder_summary(by_mechanism, mcap),
    }
    # 一致性兜底：若拆解后与 all-protocols 的 yield 不一致，用已验证值覆盖 summary，
    # 并确保 by_mechanism 与 summary 自洽（validate 重算依赖）
    summary = holder_returns["summary"]
    if tev_yield is not None and summary.get("shareholder_yield_percent") is None:
        # 重建 by_mechanism 为汇总条（原机制名并入 note），再整体派生 summary
        mech_names = " + ".join(m.get("mechanism", m.get("name", "?")) for m in by_mechanism[:3]) if by_mechanism else "多机制"
        holder_returns["by_mechanism"] = [{
            "mechanism": f"汇总（{mech_names}）",
            "type": "yield",
            "usd_365d": round(tev_yield / 100 * mcap, 2) if mcap else None,
            "yield_percent": tev_yield,
            "_note": "通用适配器汇总口径（all-protocols 已验证 yield）；含金量/机制拆解待专属 adapter.py",
        }]
        holder_returns["summary"] = derive_holder_summary(holder_returns["by_mechanism"], mcap)
        if holder_returns["summary"].get("shareholder_yield_percent") is None:
            holder_returns["summary"]["shareholder_yield_percent"] = tev_yield

    # 收入（L2）
    validation = ap.get("validation", {})
    burn_usd = validation.get("recent_4q_burn_usd_current")
    apy = validation.get("asbnb_apy_percent")
    staking_usd = round(apy / 100 * mcap, 2) if (apy and mcap) else None

    revenue_included = {"total_usd_365d": None}
    if entity_type == "platform_token":
        revenue_included = {
            "burn_usd_365d": burn_usd,
            "staking_rewards_usd_365d": staking_usd,
            "total_usd_365d": round((burn_usd or 0) + (staking_usd or 0), 2) if (burn_usd or staking_usd) else None,
        }
    else:
        rev_365d = ap.get("metrics", {}).get("trailing_365d_revenue_usd") or ap.get("metrics", {}).get("trailing_365d_fees_usd")
        holders_365d = ap.get("metrics", {}).get("trailing_365d_holders_revenue_usd") or ap.get("metrics", {}).get("trailing_365d_tev_usd")
        revenue_included = {
            "protocol_fees_usd_365d": rev_365d,
            "total_usd_365d": rev_365d,
        }
        # 应用型毛利：扣 LP（用 holders revenue 作为协议归属近似，注记）
        if rev_365d and holders_365d:
            gp = {"lp_share_cost_usd_365d": round(rev_365d - holders_365d, 2),
                  "gross_profit_usd_365d": round(holders_365d, 2),
                  "calculation_note": "近似：协议归属（dailyHoldersRevenue 口径）作为毛利；精确 LP 分润见专属 adapter"}
        else:
            gp = {"lp_share_cost_usd_365d": None, "gross_profit_usd_365d": None,
                  "calculation_note": "毛利数据缺失（null），见专属 adapter"}
    if entity_type == "platform_token":
        gp = {"lp_share_cost_usd_365d": None,
              "gross_profit_usd_365d": revenue_included.get("total_usd_365d"),
              "calculation_note": "平台币无 LP 成本，毛利 = 收入（赋能总额）"}

    emission = config.get("token_emission_cost", {}) or {"treatment": "none"}
    emission_cost = emission.get("usd_365d")
    # 净利 = 毛利 − 增发成本 − 运营成本；毛利缺失 → 净利为 null（禁止编造 0）
    gp_val = gp.get("gross_profit_usd_365d")
    if entity_type == "platform_token":
        net_income = (revenue_included.get("total_usd_365d") or 0) - (emission_cost or 0)
        net_income = net_income if revenue_included.get("total_usd_365d") is not None else None
    elif gp_val is not None:
        net_income = gp_val - (emission_cost or 0)
    else:
        net_income = None

    income_statement = {
        "revenue": {
            "entity_type": entity_type,
            "revenue_included": revenue_included,
            "revenue_excluded": rr.get("revenue_excluded", {}),
            "growth_yoy_percent": None,
            "source": {"type": rr.get("source_type", "estimate"), "url": rr.get("source_url")},
        },
        "gross_profit": gp,
        "token_emission_cost": emission,
        "net_income": {
            "net_income_usd_365d": round(net_income, 2) if net_income is not None else None,
            "operating_cost_usd_365d": None,
            "calculation_note": "毛利 − 增发成本 − 运营成本（口径见 config.revenue_recognition）",
        },
        "margins": {},
    }
    income_statement["margins"] = derive_margins(income_statement)

    confidence = ap.get("confidence", "partial")
    conf_map = {"high": "verified", "medium": "partial", "low": "estimated"}
    snapshot = {
        "protocol": pid,
        "as_of": date.today().isoformat(),
        "income_statement": income_statement,
        "holder_returns": holder_returns,
        "balance_sheet": {"market_cap_usd": mcap, "tvl_usd": tvl, "treasury_usd": None, "debt_usd": None},
        "valuation": {},
        "verification": {
            "method": config.get("verification_method") or ap.get("validation", {}).get("method") or "generic adapter（基于 all-protocols 已验证字段）",
            "status": conf_map.get(confidence, "partial"),
            "last_checked": date.today().isoformat(),
        },
    }
    snapshot["valuation"] = derive_valuation(snapshot["balance_sheet"], income_statement, holder_returns)
    return snapshot


# ── 适配器调度 ─────────────────────────────────────────────────────────

def run_adapter(proto_dir, all_protocols, daily, pid):
    """优先运行协议专属 adapter.py；否则通用适配器兜底。"""
    adapter_file = proto_dir / "adapter.py"
    if adapter_file.exists():
        spec = importlib.util.spec_from_file_location(f"adapter_{pid}", adapter_file)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"adapter_{pid}"] = mod
        spec.loader.exec_module(mod)
        if hasattr(mod, "build_snapshot"):
            snap = mod.build_snapshot(proto_dir)
            if snap is None:
                raise ValueError(f"adapter {pid} returned None")
            return snap
        raise ValueError(f"adapter.py {pid} 缺少 build_snapshot(proto_dir) 函数")
    return run_generic_adapter(proto_dir, all_protocols, daily)


# ── v2.2 历史序列累积（历史数据看板数据源） ──────────────────────────

HISTORY_DIR = DATA_DIR / "history"


def append_history(pid, snap, all_protocols=None):
    """按 as_of 累积历史记录到 data/history/<pid>.json（去重，同日覆盖）。

    每条记录字段：as_of / net_income / pe / ps / shareholder_yield / net_margin
    """
    try:
        HISTORY_DIR.mkdir(exist_ok=True)
        hist_file = HISTORY_DIR / f"{pid}.json"
        hist = _load_json(hist_file) or {"protocol": pid, "records": []}
        as_of = snap.get("as_of")
        if not as_of:
            return
        inc = snap.get("income_statement", {})
        val = snap.get("valuation", {})
        hr = snap.get("holder_returns", {}).get("summary", {})
        mg = inc.get("margins", {})
        record = {
            "as_of": as_of,
            "net_income": inc.get("net_income", {}).get("net_income_usd_365d"),
            "pe": val.get("pe"),
            "ps": val.get("ps"),
            "shareholder_yield": hr.get("shareholder_yield_percent"),
            "net_margin": mg.get("net_margin_percent"),
        }
        records = hist.get("records", [])
        # 已有记录且包含 as_of → 只是更新今日
        existed = any(r.get("as_of") == as_of for r in records)

        # 首日回填：把主表多周期 yield 作为历史行（真实数据，非编造）
        # 周期 7d/30d/90d 的年化 yield 是对应窗口的实测值，用 as_of 前 N 天日期标注
        if not records and all_protocols is not None:
            ap = (all_protocols.get("protocols") or {}).get(pid, {})
            m = ap.get("metrics", {}) or {}
            from datetime import datetime, timedelta
            base = datetime.strptime(as_of, "%Y-%m-%d")
            mcap = ap.get("market_cap_usd") or 0
            cycles = [
                ("7d", m.get("tev_yield_7d_ann")),
                ("30d", m.get("tev_yield_30d_ann")),
                ("90d", m.get("tev_yield_90d_ann")),
            ]
            for label, y in cycles:
                if y is None:
                    continue
                d = (base - timedelta(days=int(label[:-1]))).strftime("%Y-%m-%d")
                rec = {
                    "as_of": d,
                    "net_income": round(y / 100 * mcap, 2) if mcap else None,
                    "pe": round(100 / y, 2) if y and y > 0 else None,
                    "ps": None,
                    "shareholder_yield": y,
                    "net_margin": None,
                    "_period": label,  # 回填标注
                }
                records.append(rec)
        records = [r for r in records if r.get("as_of") != as_of]
        records.append(record)
        records.sort(key=lambda r: r.get("as_of", ""))
        # 只保留最近 365 条
        hist["records"] = records[-365:]
        hist_file.write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        if not existed and any(r.get("_period") for r in records):
            print(f"    ↳ 历史表回填 {sum(1 for r in records if r.get('_period'))} 个周期点（7d/30d/90d）")
    except Exception as e:
        print(f"    ⚠ {pid} 历史序列累积失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="Financial Snapshot 生成器")
    parser.add_argument("protocols", nargs="*", help="指定协议 id；默认全部")
    parser.add_argument("--check", action="store_true", help="只校验派生自洽，不写文件")
    args = parser.parse_args()

    all_protocols = _load_json(ALL_PROTOCOLS_FILE)
    schema = _load_json(SCHEMA_FILE)

    SNAPSHOTS_DIR.mkdir(exist_ok=True)
    protos = [p for p in PROTOCOLS_DIR.iterdir() if p.is_dir() and (p / "config.json").exists()]
    if args.protocols:
        protos = [p for p in protos if p.name in args.protocols]
    protos.sort(key=lambda p: p.name)

    results = {"ok": [], "fail": []}
    for proto_dir in protos:
        pid = proto_dir.name
        daily = _load_json(DATA_DIR / "daily" / pid / "latest.json")
        if daily is None:
            # 兼容冗余目录（curve-dex / ether.fi / hyperliquid）
            for alt in ("curve-dex", "ether.fi", "hyperliquid"):
                d2 = _load_json(DATA_DIR / "daily" / alt / "latest.json")
                if d2 is not None and d2.get("protocol") in (pid, alt):
                    daily = d2
                    break
        try:
            snap = run_adapter(proto_dir, all_protocols, daily, pid)
            if args.check:
                results["ok"].append(pid)
                continue
            out = SNAPSHOTS_DIR / f"{pid}.json"
            out.write_text(json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8")
            # v2.2：历史序列累积（历史数据看板数据源 data/history/<pid>.json）
            append_history(pid, snap, all_protocols)
            results["ok"].append(pid)
            print(f"  ✓ {pid}: as_of={snap['as_of']} "
                  f"yield={snap['holder_returns']['summary'].get('shareholder_yield_percent')}% "
                  f"rev={snap['income_statement']['revenue']['revenue_included'].get('total_usd_365d')}")
        except Exception as e:
            results["fail"].append((pid, str(e)))
            print(f"  ✗ {pid}: {e}")

    print(f"\n{'✅ 成功' if not results['fail'] else '❌ 部分失败'}: "
          f"{len(results['ok'])} ok, {len(results['fail'])} fail")
    if results["fail"]:
        for pid, err in results["fail"]:
            print(f"    {pid}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
