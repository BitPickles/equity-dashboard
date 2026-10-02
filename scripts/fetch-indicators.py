#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指标板块每日更新（btc-price / fred-macro / ahr999 / marketcap / btc-dominance / mvrv）

数据源（全部免费或已配置）：
  - BTC 价格 / 市值 / 总市值：CoinMarketCap（CMC_API_KEY）
  - FRED 宏观：fred.stlouisfed.org CSV（免费，无需 key；BMRI 的输入）
  - MVRV：bitcoin-data.com（免费，无需 key）

设计原则：
  - 增量追加：读入现有 history，只补最后日期之后的新数据
  - 字段结构 100% 沿用原文件，各文件保持自己的 JSON 格式（避免 diff 膨胀）
  - 幂等：重复运行不会重复插入

BMRI（indicators/data/bmri.json）不在本脚本内，也没有可用的仓库内生成器：
scripts/recalc-bmri.py 的口径与线上序列对不上（MAE≈15），详见 docs/skill/indicators/bmri.md。
恢复 openclaw operator 链路前，请勿覆盖线上 bmri.json。
用法：python3 scripts/fetch-indicators.py [--dry-run]
"""
import json
import math
import os
import sys
import csv
import io
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / 'indicators' / 'data'
SHARED = DATA / 'shared'
TODAY = date.today()
DRY = '--dry-run' in sys.argv

# BTC 创世区块日（AHR999 币龄估值起点）
GENESIS = date(2009, 1, 3)
# BMRI 依赖的 FRED 序列
FRED_SERIES = ['DGS10', 'DFII10', 'WALCL', 'DTWEXBGS', 'VIXCLS', 'BAMLH0A0HYM2']


def log(*a):
    print(*a, flush=True)


# ---------------- HTTP ----------------
def http_json(url, headers=None, timeout=40):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def http_text(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': 'crypto3d/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8')


def cmc_key():
    k = os.environ.get('CMC_API_KEY')
    if k:
        return k.strip()
    env = REPO / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            if line.startswith('CMC_API_KEY'):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('❌ 未找到 CMC_API_KEY（.env 或环境变量）')


CMC_BASE = 'https://pro-api.coinmarketcap.com/v1'


def cmc(path, params):
    url = f'{CMC_BASE}{path}?{urllib.parse.urlencode(params)}'
    return http_json(url, headers={'X-CMC_PRO_API_KEY': cmc_key(), 'Accept': 'application/json'})


def save(path, obj, compact=False, indent=2):
    """compact=True → separators=(',',':')；compact=False → indent 指定；indent=None → 默认分隔符。"""
    if DRY:
        log(f'   [dry-run] 跳过写入 {path.relative_to(REPO)}')
        return
    with open(path, 'w', encoding='utf-8') as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
        elif indent is None:
            json.dump(obj, f, ensure_ascii=False)
        else:
            json.dump(obj, f, ensure_ascii=False, indent=indent)


# ---------------- 1) BTC 价格（shared/btc-price.json）----------------
def fetch_btc_price_daily(start_date):
    """CMC BTC 日频价格。返回 {date_str: price}。"""
    end = TODAY
    count = (end - start_date).days + 10
    d = cmc('/cryptocurrency/quotes/historical',
            {'id': 1, 'interval': '1d', 'count': count, 'convert': 'USD',
             'time_start': start_date.isoformat(), 'time_end': end.isoformat()})
    out = {}
    for row in d.get('data', {}).get('quotes', []):
        dt = row['timestamp'][:10]
        u = row['quote']['USD']
        if u.get('price') is not None:
            out[dt] = round(float(u['price']), 2)
    return out


def update_btc_price():
    fp = SHARED / 'btc-price.json'
    doc = json.load(open(fp, encoding='utf-8'))
    hist = doc['history']
    last = hist[-1]['date']
    start = date.fromisoformat(last) + timedelta(days=1)
    if start > TODAY:
        log('btc-price: 已是最新'); return 0
    prices = fetch_btc_price_daily(start)
    existing = {h['date'] for h in hist}
    added = []
    for ds in sorted(prices):
        if ds > last and ds not in existing:
            hist.append({'date': ds, 'price': prices[ds]})
            added.append(ds)
    if added:
        doc['updated_at'] = added[-1]
        doc['source'] = doc.get('source') or 'glassnode/coingecko'
        save(fp, doc, indent=2)
    log(f'btc-price: +{len(added)} 条 → {added[-1] if added else last}')
    return len(added)


# ---------------- 2) FRED 宏观（shared/fred-macro.json）----------------
def fred_series(series_id):
    txt = http_text(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}')
    out = {}
    for row in csv.reader(io.StringIO(txt)):
        if len(row) < 2 or row[0] == 'DATE' or row[1] in ('.', ''):
            continue
        try:
            out[row[0]] = float(row[1])
        except ValueError:
            continue
    return out


def update_fred_macro():
    fp = SHARED / 'fred-macro.json'
    doc = json.load(open(fp, encoding='utf-8'))
    series = doc.setdefault('series', {})
    total_new = 0
    for sid in FRED_SERIES:
        try:
            vals = fred_series(sid)
        except Exception as e:
            log(f'  ⚠️ FRED {sid} 失败: {e}'); continue
        cur = series.setdefault(sid, {})
        new = 0
        for d, v in vals.items():
            if d < '2013-01-01':      # 与原文件范围对齐（BMRI 只用 2013 起）
                continue
            if d not in cur:
                cur[d] = v; new += 1
            elif cur[d] != v:
                cur[d] = v  # 官方修正
        total_new += new
        last = max(vals) if vals else '—'
        log(f'  FRED {sid}: +{new} 条（最新 {last}）')
    if total_new:
        doc['updated_at'] = TODAY.isoformat()
        save(fp, doc, indent=None)
    log(f'fred-macro: 共 +{total_new} 条')
    return total_new


# ---------------- 3) AHR999（由 BTC 价格计算）----------------
def ahr999_values(closes, upto):
    """closes: 按日期升序的 [(date, price)]，upto: 计算到该日期（含）。返回 dict date→记录。"""
    out = {}
    prices = [p for _, p in closes]
    dates = [d for d, _ in closes]
    for i, d in enumerate(dates):
        if d < upto:
            continue
        window = prices[max(0, i - 199):i + 1]
        if len(window) < 200:
            continue
        cost = math.exp(sum(math.log(p) for p in window) / len(window))
        age = (date.fromisoformat(d) - GENESIS).days
        fitted = 10 ** (5.84 * math.log10(age) - 17.01)
        price = prices[i]
        out[d] = {
            'date': d, 'close': price,
            'ahr999': round((price / cost) * (price / fitted), 4),
            'cost_200d': round(cost, 2),
            'fitted_price': round(fitted, 2),
        }
    return out


def ahr999_status(v):
    if v < 0.45:
        return '抄底区'
    if v <= 1.2:
        return '定投区'
    return '观望区'


def update_ahr999():
    fp = DATA / 'ahr999.json'
    doc = json.load(open(fp, encoding='utf-8'))
    hist = doc['history']
    last = hist[-1]['date']
    bp = json.load(open(SHARED / 'btc-price.json', encoding='utf-8'))['history']
    closes = [(h['date'], h['price']) for h in bp]
    vals = ahr999_values(closes, last)
    added = [d for d in sorted(vals) if d > last]
    for d in added:
        hist.append(vals[d])
    if added:
        lastrec = vals[added[-1]]
        doc['updated_at'] = added[-1]
        doc['current'] = {
            'date': added[-1], 'value': lastrec['ahr999'], 'price': lastrec['close'],
            'cost_200d': lastrec['cost_200d'], 'fitted_price': lastrec['fitted_price'],
            'status': ahr999_status(lastrec['ahr999']),
        }
        save(fp, doc, indent=2)
    log(f'ahr999: +{len(added)} 条 → {added[-1] if added else last}')
    return len(added)


# ---------------- 4) marketcap + 5) btc-dominance（CMC）----------------
def fetch_cmc_btc_mcap(start_date):
    n = (TODAY - start_date).days + 10
    d = cmc('/cryptocurrency/quotes/historical',
            {'id': 1, 'interval': '1d', 'count': n, 'convert': 'USD',
             'time_start': start_date.isoformat(), 'time_end': TODAY.isoformat()})
    return {r['timestamp'][:10]: float(r['quote']['USD']['market_cap'])
            for r in d.get('data', {}).get('quotes', []) if r['quote']['USD'].get('market_cap')}


def fetch_cmc_total_mcap(start_date):
    n = (TODAY - start_date).days + 10
    d = cmc('/global-metrics/quotes/historical',
            {'interval': '1d', 'count': n, 'convert': 'USD',
             'time_start': start_date.isoformat(), 'time_end': TODAY.isoformat()})
    return {r['timestamp'][:10]: float(r['quote']['USD']['total_market_cap'])
            for r in d.get('data', {}).get('quotes', []) if r['quote']['USD'].get('total_market_cap')}


def update_marketcap():
    fp = DATA / 'marketcap.json'
    rows = json.load(open(fp, encoding='utf-8'))
    last = rows[-1]['date']
    start = date.fromisoformat(last) + timedelta(days=1)
    if start > TODAY:
        log('marketcap: 已是最新'); return 0, {}
    btc_m = fetch_cmc_btc_mcap(start)
    tot_m = fetch_cmc_total_mcap(start)
    added = []
    dom = {}
    for ds in sorted(set(btc_m) & set(tot_m)):
        if ds <= last:
            continue
        rows.append({'date': ds, 'total_mcap': round(tot_m[ds], 2), 'btc_mcap': round(btc_m[ds], 2)})
        dom[ds] = round(btc_m[ds] / tot_m[ds] * 100, 4)
        added.append(ds)
    if added:
        save(fp, rows, indent=None)
    log(f'marketcap: +{len(added)} 条 → {added[-1] if added else last}')
    return len(added), dom


def update_btc_dominance(dom):
    fp = DATA / 'btc-dominance.json'
    doc = json.load(open(fp, encoding='utf-8'))
    hist = doc['history']
    last = hist[-1]['date']
    added = [d for d in sorted(dom) if d > last]
    for d in added:
        hist.append({'date': d, 'value': dom[d]})
    if added:
        v = dom[added[-1]]
        doc['updated_at'] = added[-1]
        doc['current'] = {'value': v, 'zone': 'BALANCED' if 50 < v < 70 else ('HIGH' if v >= 70 else 'LOW'), 'date': added[-1]}
        save(fp, doc, compact=True)
    log(f'btc-dominance: +{len(added)} 条 → {added[-1] if added else last}')
    return len(added)


# ---------------- 6) MVRV（bitcoin-data.com）----------------
def mvrv_status(v):
    if v < 1.0:
        return '低估区', 'Undervalued'
    if v <= 3.0:
        return '合理区', 'Fair Value'
    return '高估区', 'Overvalued'


def update_mvrv():
    fp = DATA / 'mvrv.json'
    doc = json.load(open(fp, encoding='utf-8'))
    hist = doc['history']
    last = hist[-1]['date']
    feed = http_json('https://bitcoin-data.com/api/v1/mvrv')
    feed = {x['d']: round(float(x['mvrv']), 4) for x in feed if x.get('mvrv')}
    added = [d for d in sorted(feed) if d > last]
    for d in added:
        hist.append({'date': d, 'mvrv': feed[d]})
    if added:
        v = feed[added[-1]]
        st, st_en = mvrv_status(v)
        doc['updated_at'] = added[-1]
        doc['current'] = {'date': added[-1], 'value': v, 'status': st, 'status_en': st_en}
        save(fp, doc, indent=2)
    log(f'mvrv: +{len(added)} 条 → {added[-1] if added else last}')
    return len(added)


def main():
    log(f'=== 指标板块更新 {TODAY} ===')
    if DRY:
        log('（dry-run：不写文件）')
    log('[1/6] btc-price'); update_btc_price()
    log('[2/6] fred-macro'); update_fred_macro()
    log('[3/6] ahr999'); update_ahr999()
    log('[4/6] marketcap'); _, dom = update_marketcap()
    log('[5/6] btc-dominance'); update_btc_dominance(dom)
    log('[6/6] mvrv'); update_mvrv()
    log('=== 完成（BMRI 未包含：等待 openclaw operator 链路恢复）===')


if __name__ == '__main__':
    main()
