#!/usr/bin/env python3
"""Crypto3D 每日数据海报生成器（新版浅色 1080×1920）

读取 tev-dashboard 本地数据 → 替换 template.html → Playwright 截图 PNG

数据源：
- indicators/data/ahr999.json
- indicators/data/mvrv.json
- indicators/data/btc-dominance.json
- data/governance.json
"""
import asyncio
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE = SCRIPT_DIR / "template.html"
LOGO_PATH = SCRIPT_DIR / "logo-3d.jpg"
TEV_DIR = Path.home() / ".openclaw" / "workspace-engineer" / "tev-dashboard"
INDICATORS = TEV_DIR / "indicators" / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Previous cycle MVRV at same point post-halving (~23 months after May 2020 halving = March 2022)
PREV_CYCLE_MVRV = 1.73

TZ = timezone(timedelta(hours=8))
WEEKDAYS_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
MONTHS_EN = ["", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
             "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
DAYS_EN = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


def load_json(p):
    try:
        return json.load(open(p))
    except Exception as e:
        print(f"[WARN] Failed to load {p}: {e}")
        return None


def collect_data():
    """Collect all data needed for the poster."""
    now = datetime.now(TZ)
    data = {"date": now}

    # --- AHR999 ---
    ahr = load_json(INDICATORS / "ahr999.json")
    if ahr:
        c = ahr["current"]
        h = ahr.get("history", [])
        # 7d price change
        p_now = c["price"]
        p_7d = h[-8]["close"] if len(h) > 7 else h[0]["close"]
        price_chg_7d = (p_now - p_7d) / p_7d * 100
        # 7d ahr change
        a_now = c["value"]
        a_7d = h[-8]["ahr999"] if len(h) > 7 else h[0]["ahr999"]
        ahr_chg_7d = (a_now - a_7d) / a_7d * 100
        # Price deviation from fitted (use 3D version if available)
        fitted_3d = c.get("fitted_price_v2", c["fitted_price"])
        deviation = (p_now - fitted_3d) / fitted_3d * 100

        data["btc"] = {
            "price": p_now,
            "price_chg_7d": price_chg_7d,
            "prices_7d": [x["close"] for x in h[-7:]],
        }
        data["ahr999"] = {
            "value": a_now,
            "ahr999_3d": c.get("ahr999_3d", a_now),
            "status": c["status"],
            "cost_200d": c["cost_200d"],
            "fitted_price": c["fitted_price"],
            "fitted_price_v2": fitted_3d,
            "deviation": deviation,
            "chg_7d": ahr_chg_7d,
        }

    # --- MVRV ---
    mvrv = load_json(INDICATORS / "mvrv.json")
    if mvrv:
        c = mvrv["current"]
        h = mvrv.get("history", [])
        m_now = c["value"]
        m_7d = h[-8]["mvrv"] if len(h) > 7 else h[0]["mvrv"]
        mvrv_chg_7d = (m_now - m_7d) / m_7d * 100
        # Historical percentile (rough: what % of history is below current)
        all_vals = [x["mvrv"] for x in h]
        percentile = sum(1 for v in all_vals if v < m_now) / len(all_vals) * 100 if all_vals else 50
        # Previous cycle same period MVRV
        # Current halving: April 2024. Previous: May 2020.
        # Compute months since current halving, find same offset in prev cycle
        halving_current = datetime(2024, 4, 20)
        halving_prev = datetime(2020, 5, 11)
        months_since = (now.year - halving_current.year) * 12 + (now.month - halving_current.month)
        target_date = halving_prev + timedelta(days=months_since * 30.44)
        target_str = target_date.strftime("%Y-%m")
        prev_cycle_vals = [x["mvrv"] for x in h if x["date"].startswith(target_str)]
        prev_cycle_mvrv = round(sum(prev_cycle_vals) / len(prev_cycle_vals), 2) if prev_cycle_vals else PREV_CYCLE_MVRV

        data["mvrv"] = {
            "value": m_now,
            "status": c["status"],
            "chg_7d": mvrv_chg_7d,
            "percentile": percentile,
            "prev_cycle": prev_cycle_mvrv,
            "prev_cycle_period": target_str,
        }

    # --- BTC.D ---
    btcd = load_json(INDICATORS / "btc-dominance.json")
    if btcd:
        c = btcd["current"]
        h = btcd.get("history", [])
        d_now = c["value"]
        d_7d = h[-8]["value"] if len(h) > 7 else h[0]["value"]
        btcd_chg_7d = (d_now - d_7d) / d_7d * 100
        data["btcd"] = {
            "value": d_now,
            "zone": c["zone"],
            "chg_7d": btcd_chg_7d,
        }

    # --- Governance (active + TEV related) ---
    gov = load_json(TEV_DIR / "data" / "governance.json")
    if gov:
        active_tev = [p for p in gov.get("proposals", [])
                      if p.get("status") == "active" and p.get("tev_related")]
        if active_tev:
            # Pick the one with most tev_keywords or first
            best = active_tev[0]
            data["governance"] = {
                "protocol": best.get("protocol", ""),
                "title": best.get("title", ""),
                "summary_zh": best.get("summary_zh", best.get("summary_en", "")),
                "end": best.get("end", ""),
                "status": "进行中",
                "vote_pct": 0,  # We don't have vote data in current JSON
            }

    return data


def fmt_price(v):
    """Format price like $70,759"""
    return f"${v:,.0f}"


def fmt_mcap(v_usd):
    """Format market cap like $1.40T"""
    if v_usd >= 1e12:
        return f"${v_usd/1e12:.2f}T"
    elif v_usd >= 1e9:
        return f"${v_usd/1e9:.1f}B"
    return f"${v_usd/1e6:.0f}M"


def btc_sparkline_svg(prices):
    """Generate BTC sparkline SVG path for background."""
    if not prices or len(prices) < 2:
        return ""
    mn, mx = min(prices), max(prices)
    rng = mx - mn or 1
    w, h = 960, 200
    pts = [(i * w / (len(prices) - 1), h - ((p - mn) / rng * h * 0.7) - h * 0.1)
           for i, p in enumerate(prices)]

    # Build smooth curve path
    path_d = f"M{pts[0][0]:.0f},{pts[0][1]:.0f}"
    for i in range(1, len(pts)):
        cx = (pts[i-1][0] + pts[i][0]) / 2
        path_d += f" C{cx:.0f},{pts[i-1][1]:.0f} {cx:.0f},{pts[i][1]:.0f} {pts[i][0]:.0f},{pts[i][1]:.0f}"
    fill_d = path_d + f" L{w},{h} L0,{h}Z"

    return f'''<svg width="100%" height="100%" viewBox="0 0 {w} {h}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sf" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#18181b" stop-opacity="0.08"/>
            <stop offset="100%" stop-color="#18181b" stop-opacity="0"/>
          </linearGradient>
          <linearGradient id="lineAlpha" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#18181b" stop-opacity="0"/>
            <stop offset="20%" stop-color="#18181b" stop-opacity="0.12"/>
            <stop offset="100%" stop-color="#18181b" stop-opacity="0.2"/>
          </linearGradient>
        </defs>
        <path d="{fill_d}" fill="url(#sf)"/>
        <path d="{path_d}" stroke="url(#lineAlpha)" stroke-width="2.5" stroke-linecap="round" fill="none"/>
      </svg>'''


def render_html(data):
    """Read template and replace all data placeholders."""
    html = TEMPLATE.read_text(encoding="utf-8")
    now = data["date"]

    # === Logo: relative path from output/ subdir to parent ===
    html = html.replace('src="logo-3d.jpg"', 'src="../logo-3d.jpg"')

    # === Update timestamp — show data update date, not current time ===
    # Use the latest date from indicator data files
    data_dates = []
    for key in ["ahr999", "mvrv", "btcd"]:
        d = data.get(key, {})
        # collect_data stores date in the parent data dict only
    ahr_data = load_json(INDICATORS / "ahr999.json")
    if ahr_data:
        data_dates.append(ahr_data["current"].get("date", ""))
    mvrv_data = load_json(INDICATORS / "mvrv.json")
    if mvrv_data:
        data_dates.append(mvrv_data["current"].get("date", ""))
    # Latest data date
    data_dates = [d for d in data_dates if d]
    data_dates.sort()
    ts_str = data_dates[-1] if data_dates else now.strftime("%Y-%m-%d")
    # Make title-section position:relative, add absolute-right timestamp
    html = html.replace(
        '<div class="title-section">',
        '<div class="title-section" style="position:relative;">'
    )
    ts_span = f'<span style="position:absolute;right:0;bottom:0;font-family:JetBrains Mono,monospace;font-size:14px;font-weight:500;color:#c4c4cc;">Updated {ts_str}</span>'
    html = html.replace('</div>\n  </div>\n\n  <!-- BTC',
                         f'{ts_span}</div>\n  </div>\n\n  <!-- BTC')

    # --- Date ---
    day_num = str(now.day)
    month_en = MONTHS_EN[now.month]
    day_en = DAYS_EN[now.weekday()]
    date_line = f"{month_en} {now.year} · {day_en}"

    html = re.sub(r'(<span class="title-day">)\d+(<\/span>)', rf'\g<1>{day_num}\2', html)
    html = re.sub(
        r'(MARCH|JANUARY|FEBRUARY|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{4}\s*·\s*\w+DAY',
        date_line, html
    )

    # --- BTC ---
    btc = data.get("btc", {})
    price = btc.get("price", 0)
    chg = btc.get("price_chg_7d", 0)
    chg_cls = "up" if chg >= 0 else "down"
    chg_sign = "+" if chg >= 0 else ""
    prices_7d = btc.get("prices_7d", [])

    # BTC price
    html = re.sub(
        r'(<div class="btc-price"><span class="btc-dollar">\$</span>)[^<]+(</div>)',
        rf'\g<1>{price:,.0f}\2', html
    )
    # BTC change (7d)
    html = re.sub(
        r'<span class="btc-change\s+(up|down)">[^<]+</span>',
        f'<span class="btc-change {chg_cls}">{chg_sign}{chg:.1f}% 7d</span>', html
    )

    # BTC sparkline SVG
    if prices_7d:
        spark_svg = btc_sparkline_svg(prices_7d)
        html = re.sub(
            r'(<div class="btc-spark-bg">)[\s\S]*?(</div>\s*<div style="position:relative;z-index:1;">)',
            rf'\1\n      {spark_svg}\n    \2', html
        )

    # BTC MCap estimate (price × ~19.8M supply)
    btc_supply = 19_800_000
    mcap = price * btc_supply

    # === FIX #2: Vol — we don't have volume data, replace with 7d range ===
    if prices_7d:
        lo7, hi7 = min(prices_7d), max(prices_7d)
        html = re.sub(r'Vol <b>[^<]+</b>', f'7d Low <b>${lo7:,.0f}</b>', html)
    html = re.sub(r'MCap <b>[^<]+</b>', f'MCap <b>{fmt_mcap(mcap)}</b>', html)

    # 24H Range → 7d Range (we only have daily data)
    if prices_7d:
        lo, hi = min(prices_7d), max(prices_7d)
        rng_pct = ((price - lo) / (hi - lo) * 100) if hi > lo else 50
        html = re.sub(
            r'(<div class="range-top">[\s\S]*?<span class="range-val">)\$[\d,]+(</span>[\s\S]*?)<span class="range-tag">24h Range</span>([\s\S]*?<span class="range-val">)\$[\d,]+(</span>)',
            rf'\g<1>${lo:,.0f}\2<span class="range-tag">7D RANGE</span>\3${hi:,.0f}\4', html
        )
        html = re.sub(r'(<div class="range-dot" style="left:)[\d.]+(%)', rf'\g<1>{rng_pct:.1f}\2', html)

    # vs Gold (BTC MCap / Gold MCap ~$17.1T)
    gold_mcap = 17.1e12
    gold_pct = mcap / gold_mcap * 100
    html = re.sub(r'(<div class="gold-fill" style="width:)[\d.]+(%)', rf'\g<1>{gold_pct:.1f}\2', html)
    html = re.sub(r'(<span class="gold-val">)[\d.]+(%)', rf'\g<1>{gold_pct:.1f}\2', html)

    # Total crypto market cap estimate (BTC MCap / BTC.D)
    btcd_val = data.get("btcd", {}).get("value", 58)
    total_mcap = mcap / (btcd_val / 100) if btcd_val > 0 else mcap * 1.7
    html = re.sub(r'(<div class="mcap-val">)\$[\d.]+T(</div>)', rf'\1{fmt_mcap(total_mcap)}\2', html)

    # --- AHR999 ---
    ahr = data.get("ahr999", {})
    ahr_val = ahr.get("value", 0)
    ahr_chg = ahr.get("chg_7d", 0)
    cost_200d = ahr.get("cost_200d", 0)
    fitted = ahr.get("fitted_price_v2", ahr.get("fitted_price", 0))
    deviation = ahr.get("deviation", 0)

    # AHR value
    html = re.sub(
        r'(<div class="ahr-value"[^>]*>)[\d.]+(<\/div>)',
        rf'\g<1>{ahr_val:.2f}\2', html
    )

    # AHR gauge pointer position
    if ahr_val < 0.45:
        needle_in_seg = ahr_val / 0.45
        html = re.sub(
            r'(<div class="zone-seg" style="width:36%;background:rgba\(34,197,94,0\.35\);position:relative;">[\s\S]*?left:)\d+(%)',
            rf'\g<1>{needle_in_seg * 100:.0f}\2', html, count=1
        )

    # AHR extras
    html = re.sub(r'(200D 成本</span>\s*<span class="ahr-extra-val">)\$[\d,]+(</span>)',
                   rf'\g<1>{fmt_price(cost_200d)}\2', html)
    html = re.sub(r'(拟合价格</span>\s*<span class="ahr-extra-val">)\$[\d,]+(</span>)',
                   rf'\g<1>{fmt_price(fitted)}\2', html)

    # === FIX #1: 偏离度 — 加箭头让语义更清晰（↓ 低估=绿=好事，↑ 高估=红） ===
    dev_arrow = "↓" if deviation < 0 else "↑"
    dev_color = "#16a34a" if deviation < 0 else "#dc2626"
    html = re.sub(
        r'(偏离度</span>\s*<span class="ahr-extra-val"[^>]*>)[^<]+(</span>)',
        rf'\g<1>{dev_arrow}{abs(deviation):.1f}%\2', html
    )
    html = re.sub(
        r'(偏离度</span>\s*<span class="ahr-extra-val" style="color:)[^"]+(")',
        rf'\g<1>{dev_color}\2', html
    )

    # AHR 7d change
    ahr_chg_cls = "up" if ahr_chg >= 0 else "down"
    ahr_chg_sign = "+" if ahr_chg >= 0 else ""
    html = re.sub(
        r'(card-ahr[\s\S]*?<span class="card-change )(up|down)(">)[^<]+(</span>)',
        rf'\g<1>{ahr_chg_cls}\3{ahr_chg_sign}{ahr_chg:.1f}% 7d\4', html, count=1
    )

    # --- MVRV ---
    mvrv = data.get("mvrv", {})
    mvrv_val = mvrv.get("value", 1)
    mvrv_chg = mvrv.get("chg_7d", 0)
    mvrv_pct = mvrv.get("percentile", 50)
    mvrv_prev = mvrv.get("prev_cycle", PREV_CYCLE_MVRV)

    html = re.sub(r'(<div class="mvrv-value">)[\d.]+(<\/div>)', rf'\g<1>{mvrv_val:.2f}\2', html)

    # MVRV percentile
    html = re.sub(
        r'(<div class="mvrv-chip-val">)\d+%(</div>\s*<div class="mvrv-chip-label">历史百分位)',
        rf'\g<1>{mvrv_pct:.0f}%\2', html
    )

    # === FIX #3: MVRV 上轮同期 — use real calculated value ===
    html = re.sub(
        r'(<div class="mvrv-chip-val">)[\d.]+(<\/div>\s*<div class="mvrv-chip-label">上轮同期)',
        rf'\g<1>{mvrv_prev:.2f}\2', html
    )

    # MVRV gauge pointer position
    if mvrv_val <= 1:
        mvrv_needle_pct = (mvrv_val / 1) * 32
    elif mvrv_val <= 3:
        mvrv_needle_pct = 32 + ((mvrv_val - 1) / 2) * 38
    else:
        mvrv_needle_pct = 70 + ((mvrv_val - 3) / 1) * 30
    mvrv_needle_pct = max(2, min(98, mvrv_needle_pct))

    # Replace needle position: it's inside the first zone-seg as absolute positioned div
    # We need to set left instead of right for precise positioning
    html = re.sub(
        r'(card-mvrv[\s\S]*?<div class="zone-seg" style="width:32%;background:rgba\(34,197,94,0\.2\);position:relative;">[\s\S]*?style="position:absolute;)(right:\d+)(;top:-5px)',
        rf'\g<1>left:{mvrv_needle_pct:.0f}%\3', html, count=1
    )

    # MVRV 7d change
    mvrv_chg_cls = "up" if mvrv_chg >= 0 else "down"
    mvrv_chg_sign = "+" if mvrv_chg >= 0 else ""
    html = re.sub(
        r'(card-mvrv[\s\S]*?<span class="card-change )(up|down)(">)[^<]+(</span>)',
        rf'\g<1>{mvrv_chg_cls}\3{mvrv_chg_sign}{mvrv_chg:.1f}% 7d\4', html, count=1
    )

    # --- BTC.D ---
    btcd_data = data.get("btcd", {})
    btcd_v = btcd_data.get("value", 58)
    btcd_chg = btcd_data.get("chg_7d", 0)
    eth_pct = max(1, min(30, 100 - btcd_v - 23))
    alt_pct = max(1, 100 - btcd_v - eth_pct)

    html = re.sub(r'(<span class="btcd-num">)[\d.]+(<\/span>)', rf'\g<1>{btcd_v:.1f}\2', html)

    # BTC.D bars + market caps
    html = re.sub(
        r'(BTC</span>[\s\S]*?<div class="btcd-bar-fill" style="width:)[\d.]+(%)',
        rf'\g<1>{btcd_v:.1f}\2', html, count=1
    )
    html = re.sub(
        r'(BTC</span>[\s\S]*?<span class="btcd-bar-val">)\$[\d.]+T(<\/span>)',
        rf'\g<1>{fmt_mcap(mcap)}\2', html, count=1
    )

    eth_mcap = total_mcap * (eth_pct / 100)
    html = re.sub(
        r'(ETH</span>[\s\S]*?<div class="btcd-bar-fill" style="width:)[\d.]+(%)',
        rf'\g<1>{eth_pct:.0f}\2', html, count=1
    )
    html = re.sub(
        r'(ETH</span>[\s\S]*?<span class="btcd-bar-val">)\$[\d.]+T(<\/span>)',
        rf'\g<1>{fmt_mcap(eth_mcap)}\2', html, count=1
    )

    alt_mcap = total_mcap * (alt_pct / 100)
    html = re.sub(
        r'(ALT</span>[\s\S]*?<div class="btcd-bar-fill" style="width:)[\d.]+(%)',
        rf'\g<1>{alt_pct:.1f}\2', html, count=1
    )
    html = re.sub(
        r'(ALT</span>[\s\S]*?<span class="btcd-bar-val">)\$[\d.]+T(<\/span>)',
        rf'\g<1>{fmt_mcap(alt_mcap)}\2', html, count=1
    )

    # BTC.D 7d change
    btcd_chg_cls = "up" if btcd_chg >= 0 else "down"
    btcd_chg_sign = "+" if btcd_chg >= 0 else ""
    html = re.sub(
        r'(card-btcd[\s\S]*?<span class="card-change )(up|down)(">)[^<]+(</span>)',
        rf'\g<1>{btcd_chg_cls}\3{btcd_chg_sign}{btcd_chg:.1f}% 7d\4', html, count=1
    )

    # --- Governance ---
    gov = data.get("governance")
    if gov:
        # === FIX #8: 治理投票进度 — 无数据时隐藏投票条，只显示状态 ===
        html = re.sub(r'(\[ARFC\] 激活 Aave Buyback 回购机制)', gov["title"], html)
        html = re.sub(
            r'(<div class="gov-desc">)[^<]+(</div>)',
            rf'\g<1>{gov["summary_zh"]}\2', html
        )
        html = re.sub(
            r'(<span class="gov-protocol">)[^<]+(</span>)',
            rf'\g<1>{gov["protocol"]}\2', html
        )
        end_str = gov.get("end", "")
        if end_str:
            try:
                end_dt = datetime.fromisoformat(end_str)
                end_display = f"截止 {end_dt.month}月{end_dt.day}日"
            except Exception:
                end_display = "进行中"
        else:
            end_display = "进行中"
        html = re.sub(
            r'(<span class="gov-detail">)[^<]+(</span>)',
            rf'\g<1>{end_display}\2', html
        )
        # Hide vote bar + label if no vote data (keep gov-status-row structure intact)
        vote_pct = gov.get("vote_pct", 0)
        if not vote_pct:
            html = re.sub(
                r'<div class="gov-vote-inline">[\s\S]*?<div class="gov-vote-label">[^<]*</div>\s*</div>',
                '', html, count=1
            )
    else:
        # No active governance - hide the entire card
        html = re.sub(
            r'(<div class="card card-gov">)',
            r'<div class="card card-gov" style="display:none;">',
            html, count=1
        )

    # === FIX #5: Scale up entire poster to fill 1920px ===
    # Content naturally takes ~1490px. Scale 1920/1490 ≈ 1.289x
    # Set inner dimensions to 1080/1.289 × 1920/1.289, then CSS zoom up
    SCALE = 1.289
    inner_w = round(1080 / SCALE)  # ~838
    inner_h = round(1920 / SCALE)  # ~1489

    # Replace body dimensions + add zoom
    html = html.replace(
        'width: 1080px;\n  height: 1920px;\n  background: #f5f5f7;',
        f'width: {inner_w}px;\n  height: {inner_h}px;\n  background: #f5f5f7;\n  zoom: {SCALE};'
    )
    # Replace poster dimensions
    html = html.replace(
        'width: 1080px;\n  height: 1920px;\n  padding:',
        f'width: {inner_w}px;\n  height: {inner_h}px;\n  padding:'
    )

    # Tighten top padding
    html = html.replace('padding: 56px 56px 48px;', 'padding: 32px 56px 48px;')
    # Reduce title section margin
    html = html.replace('margin-bottom: 4px;\n}', 'margin-bottom: 0;\n}')

    card_fix_css = """
/* === Card alignment fixes === */
.two-col { align-items: stretch !important; }
.two-col > .card { display: flex !important; flex-direction: column !important; }
.card-ahr .card-footer { margin-top: auto; }
.card-mvrv .mvrv-chips { margin-top: auto; }
.card-mvrv .card-footer { margin-top: 8px; }
.card-btcd .card-footer { margin-top: auto; }

/* === BTC bottom row: align the two progress bars horizontally === */
/* range-block: label(15px) + mb(6px) + track(7px) = track starts at ~21px from top
   gold-block:  label(15px) + mb(6px) + row with track = track starts at ~21px from top
   The gold-row has align-items:center with the gold-val (20px text) which pushes
   the 8px track up. Fix: give gold-row explicit top margin to push track down. */
.gold-row {
  margin-top: 3px !important;
}
.range-top {
  margin-bottom: 17px !important;
}
"""
    html = html.replace('</style>', card_fix_css + '</style>')

    # === FIX: PC viewport — fit poster to screen ===
    viewport_js = """
<script>
(function() {
  // Skip in Playwright (exact 1080 viewport)
  if (window.innerWidth === 1080) return;
  function fit() {
    var vw = window.innerWidth;
    var vh = window.innerHeight;
    // Body already has zoom:1.289 to scale content to 1080x1920
    // We need total zoom = 1.289 * fitRatio to show full poster
    var fitRatio = Math.min((vw - 40) / 1080, (vh - 40) / 1920);
    if (fitRatio > 1) fitRatio = 1;
    document.body.style.zoom = 1.289 * fitRatio;
    document.body.style.margin = '20px auto';
    document.body.style.overflow = 'visible';
    document.documentElement.style.background = '#e5e5e5';
    document.documentElement.style.display = 'flex';
    document.documentElement.style.justifyContent = 'center';
    document.documentElement.style.minHeight = '100vh';
  }
  fit();
  window.addEventListener('resize', fit);
})();
</script>
"""
    html = html.replace('</body>', viewport_js + '</body>')

    # Download button removed from poster HTML — handled by index.html wrapper

    return html


async def screenshot(html_path, png_path):
    """Take screenshot with Playwright."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.goto(f"file://{html_path}")
        await page.wait_for_timeout(2000)  # Wait for fonts to load
        await page.screenshot(path=str(png_path), type="png")
        await browser.close()


def load_env_key(key):
    """Load key from ~/.openclaw/.env"""
    env_file = Path.home() / ".openclaw" / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text().splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return ""


COMMENTS_ARCHIVE = OUTPUT_DIR / "comments.json"


def load_comment_history(limit=5):
    """Load recent comments from archive for context."""
    if not COMMENTS_ARCHIVE.exists():
        return []
    try:
        archive = json.loads(COMMENTS_ARCHIVE.read_text())
        comments = archive.get("comments", [])
        # Return latest N, sorted by date desc
        comments.sort(key=lambda x: x.get("date", ""), reverse=True)
        return comments[:limit]
    except Exception:
        return []


def save_to_archive(comment):
    """Append comment to archive file."""
    archive = {"comments": []}
    if COMMENTS_ARCHIVE.exists():
        try:
            archive = json.loads(COMMENTS_ARCHIVE.read_text())
        except Exception:
            pass

    comments = archive.get("comments", [])
    # Remove existing entry for same date
    comments = [c for c in comments if c.get("date") != comment["date"]]
    comments.append(comment)
    # Sort by date desc
    comments.sort(key=lambda x: x.get("date", ""), reverse=True)
    archive["comments"] = comments
    COMMENTS_ARCHIVE.write_text(json.dumps(archive, ensure_ascii=False, indent=2))


def build_trend_context():
    """Build monthly trend (4 years) + weekly detail for all indicators.
    Returns a string block to inject into the AI prompt."""
    from collections import defaultdict

    lines = []

    # --- Helper: aggregate monthly from history ---
    def monthly_agg(history, val_key, years=4):
        cutoff = (datetime.now(TZ) - timedelta(days=years * 365)).strftime("%Y-%m")
        months = defaultdict(list)
        for h in history:
            m = h["date"][:7]
            if m >= cutoff:
                v = h.get(val_key)
                if v is not None:
                    months[m].append(v)
        result = []
        for m in sorted(months):
            vals = months[m]
            result.append(f"{m}: avg={sum(vals)/len(vals):.2f}, min={min(vals):.2f}, max={max(vals):.2f}")
        return result

    def weekly_detail(history, val_key, n=7):
        recent = history[-n:] if len(history) >= n else history
        return [f"{h['date']}: {h.get(val_key, 'N/A')}" for h in recent]

    # --- AHR999 ---
    ahr = load_json(INDICATORS / "ahr999.json")
    if ahr and ahr.get("history"):
        h = ahr["history"]
        lines.append("【AHR999 月度趋势（近4年）】")
        lines.extend(monthly_agg(h, "ahr999"))
        lines.append("【AHR999 近7天】")
        lines.extend(weekly_detail(h, "ahr999"))
        lines.append("")

    # --- MVRV ---
    mvrv = load_json(INDICATORS / "mvrv.json")
    if mvrv and mvrv.get("history"):
        h = mvrv["history"]
        lines.append("【MVRV 月度趋势（近4年）】")
        lines.extend(monthly_agg(h, "mvrv"))
        lines.append("【MVRV 近7天】")
        lines.extend(weekly_detail(h, "mvrv"))
        lines.append("")

    # --- BTC.D ---
    btcd = load_json(INDICATORS / "btc-dominance.json")
    if btcd and btcd.get("history"):
        h = btcd["history"]
        lines.append("【BTC.D 月度趋势（近4年）】")
        lines.extend(monthly_agg(h, "value"))
        lines.append("【BTC.D 近7天】")
        lines.extend(weekly_detail(h, "value"))
        lines.append("")

    if not lines:
        return ""
    header = "\n\n历史趋势参考（请据此判断当前指标处于历史什么位置，避免把低位小幅反弹误判为上升趋势）：\n"
    return header + "\n".join(lines)


def self_check_comment(title, body, indicators_context, api_key):
    """AI self-check: verify comment only uses provided data, no fabrication."""
    import subprocess, tempfile

    check_prompt = f"""你是一个严格的数据审核员。请检查以下 AI 生成的加密市场短评是否存在问题。

【提供给 AI 的原始数据】
{indicators_context}

【AI 生成的短评】
标题: {title}
正文: {body}

【检查项】
1. 短评中引用的所有数字（价格、百分比、指标值）是否都能在原始数据中找到对应？
2. 是否编造了原始数据中不存在的数据？（如矿工成本、交易所流入流出、巨鲸数据、期货持仓等）
3. 对指标趋势的描述是否与原始数据一致？（如不能把低位说成高位、不能把微小波动说成大幅变化）
4. 是否包含表情符号（标题中的🔥除外）？
5. 是否包含网站链接？

【输出格式】严格按以下 JSON 格式输出，不要输出其他内容：
{{"pass": true}} 或 {{"pass": false, "reason": "具体问题描述"}}"""

    payload = json.dumps({
        "model": "glm-4.6",
        "messages": [{"role": "user", "content": check_prompt}],
        "temperature": 0.1,
        "max_tokens": 4000,
        "thinking": {"type": "enabled"},
    }, ensure_ascii=False)

    try:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        tmp.write(payload)
        tmp.close()
        try:
            result = subprocess.run([
                'curl', '-s', '--proxy', 'http://127.0.0.1:7890', 'https://open.bigmodel.cn/api/coding/paas/v4/chat/completions',
                '-H', f'Authorization: Bearer {api_key}',
                '-H', 'Content-Type: application/json',
                '-d', f'@{tmp.name}',
                '--max-time', '120',
            ], capture_output=True, text=True, timeout=150)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

        if result.returncode == 0:
            resp = json.loads(result.stdout)
            content = (resp.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                return json.loads(json_match.group())
        return {"pass": True}  # If check fails, don't block
    except Exception as e:
        print(f"  [WARN] Self-check error: {e}")
        return {"pass": True}  # Don't block on error


def retry_comment_with_feedback(original_prompt, feedback, api_key):
    """Retry comment generation with self-check feedback."""
    import subprocess, tempfile

    retry_prompt = f"""{original_prompt}

⚠️ 上一次生成的内容未通过审核，原因：{feedback}
请严格修正以上问题，重新生成短评。记住：只能使用上面提供的数据，禁止编造任何未提供的数据。"""

    payload = json.dumps({
        "model": "glm-4.6",
        "messages": [{"role": "user", "content": retry_prompt}],
        "temperature": 0.7,
        "max_tokens": 16000,
        "thinking": {"type": "enabled"},
        "do_sample": True,
    }, ensure_ascii=False)

    try:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        tmp.write(payload)
        tmp.close()
        try:
            result = subprocess.run([
                'curl', '-s', '--proxy', 'http://127.0.0.1:7890', 'https://open.bigmodel.cn/api/coding/paas/v4/chat/completions',
                '-H', f'Authorization: Bearer {api_key}',
                '-H', 'Content-Type: application/json',
                '-d', f'@{tmp.name}',
                '--max-time', '120',
            ], capture_output=True, text=True, timeout=150)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

        if result.returncode == 0:
            resp = json.loads(result.stdout)
            content = (resp.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            return content if content else None
        return None
    except Exception as e:
        print(f"  [WARN] Retry failed: {e}")
        return None


def generate_comment(data):
    """Generate AI daily comment using GLM-5."""
    import subprocess, tempfile

    api_key = load_env_key("ZHIPUAI_API_KEY")
    if not api_key:
        print("[WARN] No ZHIPUAI_API_KEY, skipping comment")
        return None

    # Build context
    btc = data.get("btc", {})
    ahr = data.get("ahr999", {})
    mvrv = data.get("mvrv", {})
    btcd = data.get("btcd", {})

    price = btc.get('price', 0)
    cost_200d = ahr.get('cost_200d', 0)
    fitted_3d = ahr.get('fitted_price_v2', ahr.get('fitted_price', 0))
    dev_cost = ((price - cost_200d) / cost_200d * 100) if cost_200d else 0
    dev_fitted_3d = ((price - fitted_3d) / fitted_3d * 100) if fitted_3d else 0
    ahr999_3d = ahr.get('ahr999_3d', ahr.get('value', 0))

    indicators = f"""当前指标数据（请严格使用以下数字，不要编造或四舍五入）：
- BTC 价格: ${price:,.0f}，7日变化: {btc.get('price_chg_7d', 0):+.1f}%
- AHR999(3D版): {ahr999_3d:.2f}（{ahr.get('status', '')}），7日变化: {ahr.get('chg_7d', 0):+.1f}%
- 200日定投成本: ${cost_200d:,.0f}，价格偏离: {dev_cost:+.1f}%
- MVRV: {mvrv.get('value', 0):.2f}，低于历史 {100 - mvrv.get('percentile', 50):.0f}% 的时间，上轮周期同期（{mvrv.get('prev_cycle_period', '2022-04')}）: {mvrv.get('prev_cycle', 0):.2f}
- BTC.D: {btcd.get('value', 0):.1f}%，7日变化: {btcd.get('chg_7d', 0):+.1f}%
（补充参考：3D版拟合价格 ${fitted_3d:,.0f}，偏离 {dev_fitted_3d:+.1f}%。拟合价格仅供辅助参考，不要作为标题或核心论点。）"""

    # Load major governance events (only big ones: buyback, fee switch, revenue share)
    gov_file = TEV_DIR / "data" / "governance.json"
    gov_context = ""
    if gov_file.exists():
        try:
            gd = json.load(open(gov_file))
            major_keywords = {"buyback", "fee", "revenue", "dividend", "burn", "staking reward"}
            major = []
            for p in gd.get("proposals", []):
                if not p.get("tev_related"):
                    continue
                if p.get("status") not in ("active", "passed"):
                    continue
                kws = set(p.get("tev_keywords", []))
                if kws & major_keywords:
                    analysis = p.get("analysis_zh", p.get("summary_zh", ""))[:120]
                    major.append(f"- [{p['protocol']}] {p['title'][:60]}：{analysis}")
            if major:
                gov_context = "\n\n重大治理动态（仅在你认为值得评论时提及，小事忽略）：\n" + "\n".join(major[:3])
        except Exception:
            pass

    # Load top news
    news_file = TEV_DIR / "data" / "news.json"
    news_context = ""
    if news_file.exists():
        try:
            nd = json.load(open(news_file))
            top_news = [n for n in nd.get("news", []) if n.get("importance", 0) >= 6][:5]
            if top_news:
                news_lines = []
                for n in top_news:
                    title = n.get("title_zh", n.get("title_en", ""))
                    summary = n.get("summary_zh", "")[:80]
                    news_lines.append(f"- [{n.get('category','')}] {title}：{summary}")
                news_context = "\n\n今日重要新闻：\n" + "\n".join(news_lines)
        except Exception:
            pass

    # Load historical comments for continuity
    history = load_comment_history(3)
    history_context = ""
    used_angles = []
    if history:
        lines = []
        for h in history:
            lines.append(f"[{h['date']}] {h['title']}\n{h['body'][:150]}...")
            used_angles.append(h.get('title', ''))
        history_context = "\n\n你最近几天写的短评（保持风格连贯，但【必须换全新视角】）：\n" + "\n\n".join(lines)
        history_context += f"\n\n⚠️ 以上短评已用过的角度，今天【绝对禁止】再用类似主题。必须选一个完全不同的切入点。"

    trend_context = build_trend_context()

    prompt = f"""{indicators}{trend_context}{gov_context}{news_context}{history_context}

你是一个专业的加密市场研究员，擅长链上数据分析、周期判断和资金结构推演。你同时是 Crypto3D 数据站的首席评论员。

请根据以上数据写一段每日市场短评。

【格式】
第一行：🔥开头的标题（20字以内，必须包含明确判断或锐利观点）
空一行后：正文 **100-150字**（必须精简，适合推特发布）

【视角轮换】每天必须从以下视角中选一个你最近3天没用过的：
A. 链上估值（MVRV、200日成本线、AHR999区间判断）
B. 市场结构（BTC.D、资金轮动、山寨季信号）
C. 周期定位（距减半天数、历史同期对比、上轮同期MVRV）
D. 事件驱动（重大新闻、治理提案、监管动态）
选好后在正文中自然展开，不要标注你选了哪个。

【结构要求】
1. 市场状态定义：一句话定性（横盘/筑底/趋势启动）
2. 核心指标解读：只选1个最关键指标，用数据说话
3. 推理链：2-3句逻辑推导
4. 结论：明确判断（偏多/中性/偏空）
5. 收尾：一个短问题

【精简要点】
- 只说最关键的数据和结论
- 删除所有铺垫和过渡句
- 每句话都要有信息量
- 严格控制字数在150字以内

【风格】
- 语言简洁，有压迫感
- 结论优先：先说判断，再解释
- 允许有观点，但必须有数据依据
- 绝对不要喊单、不要建议买入卖出，只用数据暗示

【禁止】
- ❌ 不要以拟合价格或拟合偏离度作为标题或核心论点（拟合价格只是模型参考值，不是市场真实数据）
- ❌ 不要连续两天使用相同角度或相似标题结构
- ❌ 只能引用上面提供的数据中出现的数字，严禁引用任何未提供的外部数据
- ❌ 禁止提及矿工成本、交易所流入流出、巨鲸动向、期货持仓等本站未提供的链上/交易数据（我们没有这些数据，你不能编造）
- ❌ 如果你想引用某个数字，先检查它是否出现在上面的数据中，没有就不要用
- 不要使用空洞情绪词（"暗流涌动""机会来了""风暴前的宁静"）
- 不要只提数据不解释意义
- 不要用指标结论直接代替分析
- 不要用 markdown 格式
- 不要加任何网站链接"""

    payload = json.dumps({
        "model": "glm-4.6",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 16000,
        "thinking": {"type": "enabled"},
        "do_sample": True,
    }, ensure_ascii=False)

    try:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        tmp.write(payload)
        tmp.close()
        try:
            result = subprocess.run([
                'curl', '-s', '--proxy', 'http://127.0.0.1:7890', 'https://open.bigmodel.cn/api/coding/paas/v4/chat/completions',
                '-H', f'Authorization: Bearer {api_key}',
                '-H', 'Content-Type: application/json',
                '-d', f'@{tmp.name}',
                '--max-time', '120',
            ], capture_output=True, text=True, timeout=150)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

        if result.returncode != 0:
            print(f"[WARN] Comment API failed: rc={result.returncode} {result.stderr[:100]}")
            return None

        resp = json.loads(result.stdout)
        msg = resp.get("choices", [{}])[0].get("message", {})
        content = (msg.get("content") or "").strip()
        if not content:
            print(f"[WARN] Empty content, finish_reason={resp.get('choices',[{}])[0].get('finish_reason','?')}")
            # Retry GLM-5.1 once more
            print(f"[INFO] Retrying GLM-5.1...")
            import time; time.sleep(3)
            try:
                tmp_retry = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                tmp_retry.write(payload)
                tmp_retry.close()
                try:
                    result2 = subprocess.run([
                        'curl', '-s', '--proxy', 'http://127.0.0.1:7890', 'https://open.bigmodel.cn/api/coding/paas/v4/chat/completions',
                        '-H', f'Authorization: Bearer {api_key}',
                        '-H', 'Content-Type: application/json',
                        '-d', f'@{tmp_retry.name}',
                        '--max-time', '120',
                    ], capture_output=True, text=True, timeout=150)
                finally:
                    Path(tmp_retry.name).unlink(missing_ok=True)
                if result2.returncode == 0:
                    resp2 = json.loads(result2.stdout)
                    content = (resp2.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            except Exception as e2:
                print(f"[WARN] Retry failed: {e2}")
            if not content:
                print("[WARN] GLM-5.1 retry also empty")
                return None

        # Parse title and body
        lines = content.split("\n")
        title = lines[0].strip()
        body = "\n".join(l for l in lines[1:] if l.strip()).strip()

        # === Self-check loop ===
        max_retries = 5
        for attempt in range(max_retries):
            check_result = self_check_comment(title, body, indicators, api_key)
            if check_result["pass"]:
                print(f"  ✅ 自检通过 (第{attempt+1}轮)")
                break
            else:
                reason = check_result.get("reason", "未知原因")
                print(f"  ❌ 自检未通过 (第{attempt+1}轮): {reason}")
                if attempt < max_retries - 1:
                    print(f"  🔄 重新生成...")
                    retry_content = retry_comment_with_feedback(prompt, reason, api_key)
                    if retry_content:
                        r_lines = retry_content.split("\n")
                        title = r_lines[0].strip()
                        body = "\n".join(l for l in r_lines[1:] if l.strip()).strip()
                    else:
                        print(f"  [WARN] 重新生成失败，使用当前版本")
                        break
                else:
                    # 5轮都失败，发 TG 通知
                    print(f"  🚨 自检连续{max_retries}轮失败，发送 TG 通知")
                    try:
                        subprocess.run([
                            'curl', '-s', '-X', 'POST',
                            f'https://api.telegram.org/bot{load_env_key("TELEGRAM_BOT_TOKEN")}/sendMessage',
                            '-d', f'chat_id=1311453837',
                            '-d', f'text=⚠️ AI短评自检连续{max_retries}轮失败\n最后原因: {reason}\n标题: {title}\n请人工检查',
                        ], timeout=10)
                    except Exception as e:
                        print(f"  [WARN] TG 通知失败: {e}")

        comment = {"title": title, "body": body, "date": data["date"].strftime("%Y-%m-%d")}

        # Generate English version
        print("  Generating English version...")
        en_prompt = f"""Translate the following crypto market daily comment into English.
Keep the same tone: confident, insightful, like a sharp crypto analyst on Twitter.
Keep the 🔥 emoji in the title. Do not add any website links.
First line is the title, then a blank line, then the body.

Chinese version:
{title}

{body}"""
        en_payload = json.dumps({
            "model": "glm-4.6",
            "messages": [{"role": "user", "content": en_prompt}],
            "temperature": 0.3,
            "max_tokens": 8000,
            "thinking": {"type": "enabled"},
        }, ensure_ascii=False)
        tmp_en = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        tmp_en.write(en_payload)
        tmp_en.close()
        try:
            result_en = subprocess.run([
                'curl', '-s', '--proxy', 'http://127.0.0.1:7890', 'https://open.bigmodel.cn/api/coding/paas/v4/chat/completions',
                '-H', f'Authorization: Bearer {api_key}',
                '-H', 'Content-Type: application/json',
                '-d', f'@{tmp_en.name}',
                '--max-time', '120',
            ], capture_output=True, text=True, timeout=70)
            if result_en.returncode == 0:
                resp_en = json.loads(result_en.stdout)
                en_content = (resp_en.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
                if en_content:
                    en_lines = en_content.split("\n")
                    comment["title_en"] = en_lines[0].strip()
                    comment["body_en"] = "\n".join(l for l in en_lines[1:] if l.strip()).strip()
                    print(f"  EN title: {comment['title_en']}")
        except Exception as e:
            print(f"  [WARN] English translation failed: {e}")
        finally:
            Path(tmp_en.name).unlink(missing_ok=True)

        return comment

    except Exception as e:
        print(f"[WARN] Comment generation failed: {e}")
        return None


async def main():
    print("[1/5] Collecting data...")
    data = collect_data()

    # Print summary
    btc = data.get("btc", {})
    print(f"  BTC: {fmt_price(btc.get('price', 0))} ({btc.get('price_chg_7d', 0):+.1f}% 7d)")
    ahr = data.get("ahr999", {})
    print(f"  AHR999: {ahr.get('value', 0):.2f} ({ahr.get('chg_7d', 0):+.1f}% 7d)")
    mvrv = data.get("mvrv", {})
    print(f"  MVRV: {mvrv.get('value', 0):.2f} (P{mvrv.get('percentile', 0):.0f}, prev cycle: {mvrv.get('prev_cycle', 0):.2f})")
    btcd = data.get("btcd", {})
    print(f"  BTC.D: {btcd.get('value', 0):.1f}%")
    gov = data.get("governance")
    if gov:
        print(f"  Governance: {gov['protocol']} - {gov['title'][:40]}...")
    else:
        print("  Governance: none active")

    print("\n[2/5] Generating AI comment...")
    comment = generate_comment(data)
    if comment:
        print(f"  Title: {comment['title']}")
        print(f"  Body: {comment['body'][:80]}...")
    else:
        print("  Skipped")

    print("\n[3/5] Rendering HTML...")
    html = render_html(data)

    now = data["date"]
    ts = now.strftime("%Y-%m-%d")
    html_path = OUTPUT_DIR / f"{ts}.html"
    png_path = OUTPUT_DIR / f"{ts}.png"
    comment_path = OUTPUT_DIR / f"{ts}-comment.json"

    html_path.write_text(html, encoding="utf-8")
    print(f"  → {html_path}")

    # Save comment + archive
    if comment:
        comment_path.write_text(json.dumps(comment, ensure_ascii=False, indent=2))
        (SCRIPT_DIR / "comment.json").write_text(json.dumps(comment, ensure_ascii=False, indent=2))
        save_to_archive(comment)
        print(f"  → {comment_path}")
        print(f"  → archive ({len(load_comment_history(100))} total)")

    print("\n[4/5] Taking screenshot...")
    await screenshot(html_path, png_path)
    print(f"  → {png_path}")

    # Also copy to output.png for quick access
    latest_path = SCRIPT_DIR / "output.png"
    import shutil
    shutil.copy2(png_path, latest_path)
    print(f"  → {latest_path} (latest)")

    print(f"\n[5/5] Done! Poster generated for {ts}")
    return str(png_path)


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nOutput: {result}")
