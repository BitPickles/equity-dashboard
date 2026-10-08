#!/usr/bin/env python3
"""
period_metrics.py — 多周期（7D / 30D / 90D / 365D）股东回报派生库
========================================================================
重构方案：docs/multi-window-returns-refactor-plan.md（阶段 0 产物）

【设计原则】
  「口径（哪些价值流算股东回报）」由**各协议 adapter 自行决定**；
  本库只负责机械计算：同一口径 → 按窗口聚合 → 年化 / 派息率。
  这样主表与详情页的四个周期 tab 与 365D **同源**，结构上不可能漂移。

【为什么不能通用口径】
  实测反例：lido 的 DefiLlama holdersRevenue=$706万，但股东回报应为 0；
  curve/fluid 等 ≠ holdersRevenue 直接折算；bgb/mnt/okb 状态为 none 却有 yield。
  → 故 basis 由 adapter 显式传入，本库不猜。

【adapter 用法】
    import sys; sys.path.insert(0, str(BASE_DIR))
    from scripts.lib.period_metrics import build_by_period, build_revenue_by_period

    holder_returns["by_period"] = build_by_period(
        rev_series=dl_rev,                 # [[ts, usd], ...] 日频收入序列（可 None）
        ret_series=dl_hol,                 # [[ts, usd], ...] 日频股东回报序列（可 None）
        mcap=mcap,
        basis="holders_revenue",           # holders_revenue | zero | same_as_365d | explicit
        # ret_usd_by_window={7:..,365:..}, # basis=explicit 时必填（链上模板）
        status="active", source="defillama",
    )
    revenue["by_period"] = build_revenue_by_period(rev_series=dl_rev)
"""
from __future__ import annotations

WINDOWS = (7, 30, 90, 365)
BASES = ("holders_revenue", "zero", "same_as_365d", "explicit")
_DAY = 86400


def annualize_factor(n: int) -> float:
    """N 天窗口 → 年化因子（365 天不年化，即 1.0）。"""
    if n not in WINDOWS:
        raise ValueError(f"窗口非法: {n}（可选 {WINDOWS}）")
    return 365.0 / n if n != 365 else 1.0


def sum_window(daily_pairs, n: int, asof=None):
    """[[ts, usd], ...] → 最近 n 天合计（区间 (asof-n天, asof]，左开右闭）。

    无序列 → None（禁止编造 0；"确凿为 0" 由 basis="zero" 表达）。
    """
    if not daily_pairs:
        return None
    pairs = [(int(ts), float(v or 0)) for ts, v in daily_pairs]
    last = int(asof) if asof is not None else max(ts for ts, _ in pairs)
    cutoff = last - n * _DAY
    return sum(v for ts, v in pairs if cutoff < ts <= last)


def _yield_pct(usd, mcap, n):
    if usd is None or not mcap:
        return None
    return round(usd / mcap * 100 * annualize_factor(n), 4)


def build_by_period(rev_series=None, ret_series=None, mcap=None,
                    basis="holders_revenue", ret_usd_by_window=None,
                    destroy_usd_by_window=None, status="active",
                    source="defillama", asof=None):
    """产出 `holder_returns.by_period` 结构（四窗口齐全，值可为 None）。

    basis:
      holders_revenue —— 按 DefiLlama 等日频序列逐窗口聚合（A 类 14 协议）
      zero            —— 全窗口股东回报 = 0（paused / none 协议）
      same_as_365d    —— 无日频源，四窗口同值（D 类，source 建议置 none）
      explicit        —— 直接喂 ret_usd_by_window（链上模板 B 类）
    destroy_usd_by_window:
      回购/销毁组（type destroy|buyback）各窗口值；缺省 → 全部计入 destroy，yield=0。
    """
    if basis not in BASES:
        raise ValueError(f"basis 非法: {basis}（可选 {BASES}）")
    if basis == "explicit" and not ret_usd_by_window:
        raise ValueError("basis=explicit 必须提供 ret_usd_by_window")

    explicit = ret_usd_by_window or {}
    destroy_explicit = destroy_usd_by_window or {}

    ret_365 = None
    if basis == "same_as_365d":
        ret_365 = explicit.get(365)
        if ret_365 is None and ret_series:
            ret_365 = sum_window(ret_series, 365, asof)

    out = {}
    for n in WINDOWS:
        # ── 股东回报合计（按 basis 取值）──
        if basis == "zero":
            ret = 0.0
        elif basis == "explicit":
            ret = explicit.get(n)
        elif basis == "same_as_365d":
            ret = ret_365
        else:  # holders_revenue
            ret = sum_window(ret_series, n, asof) if ret_series else None

        # ── 回购/销毁组 vs 收益型组 ──
        if destroy_explicit:
            destroy = destroy_explicit.get(n)
            yieldy = (ret - destroy) if (ret is not None and destroy is not None) else None
        else:
            destroy = ret          # 现口径下多数协议股东回报全归"回购/销毁"组
            yieldy = 0.0 if ret is not None else None

        rev_usd = sum_window(rev_series, n, asof) if rev_series else None
        payout = None
        if rev_usd and ret is not None:
            payout = round(ret / rev_usd, 4)

        out[f"{n}d"] = {
            "revenue_usd": round(rev_usd, 2) if rev_usd is not None else None,
            "shareholder_returns_usd": round(ret, 2) if ret is not None else None,
            "destroy_usd": round(destroy, 2) if destroy is not None else None,
            "yield_usd": round(yieldy, 2) if yieldy is not None else None,
            "shareholder_yield_percent": _yield_pct(ret, mcap, n),
            "buyback_yield_percent": _yield_pct(destroy, mcap, n),
            "dividend_yield_percent": _yield_pct(yieldy, mcap, n),
            "payout_ratio": payout,
            "status": status,
            "source": source,
        }
    return out


def build_revenue_by_period(rev_series=None, asof=None):
    """产出 `income_statement.revenue.by_period`（各窗口收入合计，供 Earning Yield / P/S）。"""
    out = {}
    for n in WINDOWS:
        v = sum_window(rev_series, n, asof)
        out[f"{n}d"] = {"total_usd": round(v, 2) if v is not None else None}
    return out


def consistency_errors(by_period, summary_365_usd=None, mcap=None, tol=0.005):
    """Phase 3 强制校验用：四窗口齐全 + 365d 与 summary 一致 + yield 可复算。
    返回错误字符串列表（空 = 通过）。Phase 0~2 由 validate.py 仅在 by_period 存在时调用。
    """
    errs = []
    if not isinstance(by_period, dict):
        return ["by_period 不是对象"]
    for n in WINDOWS:
        k = f"{n}d"
        blk = by_period.get(k)
        if not isinstance(blk, dict):
            errs.append(f"by_period 缺窗口 {k}")
            continue
        ru = blk.get("shareholder_returns_usd")
        act = blk.get("shareholder_yield_percent")
        exp = _yield_pct(ru, mcap, n)
        if _rel(exp, act) > tol * 100:
            errs.append(f"by_period.{k}.shareholder_yield_percent 不自洽: 文件={act} 重算={exp}")
        if n == 365:
            if _rel(ru, summary_365_usd) > tol * 100:
                errs.append(f"by_period.365d.shareholder_returns_usd={ru} 与 summary={summary_365_usd} 不一致")
    return errs


def _rel(a, b):
    """相对差异 %（None 与 0 等价）。"""
    if a is None and b is None:
        return 0.0
    if a is None or b is None:
        other = a if b is None else b
        return 0.0 if other == 0 else 100.0
    return abs(a - b) / max(abs(a), abs(b), 1e-9) * 100


if __name__ == "__main__":
    # 自检：100 天日频序列，每天收入 1000、股东回报 300
    base = 1_700_000_000
    rev = [[base - i * _DAY, 1000.0] for i in range(100)]
    ret = [[base - i * _DAY, 300.0] for i in range(100)]
    bp = build_by_period(rev_series=rev, ret_series=ret, mcap=1_000_000, basis="holders_revenue")
    for k, v in bp.items():
        print(f"{k:5} ret={v['shareholder_returns_usd']:>9}  yld={v['shareholder_yield_percent']}  "
              f"buy={v['buyback_yield_percent']}  payout={v['payout_ratio']}")
    print("errors:", consistency_errors(bp, bp["365d"]["shareholder_returns_usd"], 1_000_000))
