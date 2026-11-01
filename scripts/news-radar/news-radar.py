#!/usr/bin/env python3
import concurrent.futures
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
SOURCES_FILE = SCRIPT_DIR / "sources.json"
CACHE_FILE = SCRIPT_DIR / "summaries_cache.json"
# 写到本仓库 data/news.json。旧路径写死 /Users/aibot/.../tev-dashboard，换机器或换目录后文件落在仓外，daily-run 提交不到。
OUTPUT_FILE = REPO_ROOT / "data" / "news.json"
TZ = dt.timezone(dt.timedelta(hours=8))
LOOKBACK_HOURS = 24
MAX_SELECTED = 25
SOURCE_TIMEOUT = 15
CURL_MAX_TIME = 20
SUMMARY_TIMEOUT = 35
SUMMARY_WORKERS = 1
SUMMARY_BATCH_SIZE = 10

SOURCE_PRIORITY = {}


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def load_env_key(key: str) -> str:
    if os.environ.get(key):
        return os.environ[key].strip()
    # 环境变量 → 仓库 .env → ~/.openclaw/.env（Mac Mini 密钥习惯位置）
    for env_file in (REPO_ROOT / ".env", Path.home() / ".openclaw" / ".env"):
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip().strip('"').strip("'")
    return ""


def load_sources() -> Dict[str, Any]:
    data = json.loads(SOURCES_FILE.read_text())
    for item in data.get("rss", []) + data.get("apis", []):
        SOURCE_PRIORITY[item["name"]] = int(item.get("priority", 0))
    return data


def fetch_url(url: str, timeout: int = SOURCE_TIMEOUT) -> bytes:
    result = subprocess.run([
        'curl', '-L', '-sS', '--compressed',
        '--max-time', str(timeout), '--connect-timeout', '8',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36',
        '-H', 'Accept: application/rss+xml, application/xml, text/xml, application/json, text/html;q=0.9, */*;q=0.8',
        url,
    ], capture_output=True, timeout=timeout + 5)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode('utf-8', errors='ignore').strip() or f'curl exit {result.returncode}')
    return result.stdout


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_datetime(value: str) -> Optional[dt.datetime]:
    if not value:
        return None
    value = value.strip()
    try:
        if value.endswith("Z"):
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except Exception:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed and parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except Exception:
        return None


def within_lookback(ts: Optional[dt.datetime]) -> bool:
    if not ts:
        return True
    return ts >= now_utc() - dt.timedelta(hours=LOOKBACK_HOURS)


def rss_entries(xml_bytes: bytes, source_name: str, source_kind: str) -> List[Dict[str, Any]]:
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    # RSS items
    for node in root.findall('.//item'):
        title = strip_html((node.findtext('title') or '').strip())
        link = (node.findtext('link') or '').strip()
        desc = strip_html(node.findtext('description') or node.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or '')
        pub_raw = node.findtext('pubDate') or node.findtext('{http://purl.org/dc/elements/1.1/}date') or ''
        pub = parse_datetime(pub_raw)
        items.append({
            'title_en': title,
            'summary_en': desc[:600],
            'source': source_name,
            'source_kind': source_kind,
            'source_url': link,
            'published_at': pub or now_utc(),
        })

    # Atom entries fallback
    atom_ns = {'a': 'http://www.w3.org/2005/Atom'}
    for node in root.findall('.//a:entry', atom_ns):
        title = strip_html(node.findtext('a:title', '', atom_ns))
        link = ''
        link_node = node.find('a:link', atom_ns)
        if link_node is not None:
            link = link_node.attrib.get('href', '')
        summary = strip_html(node.findtext('a:summary', '', atom_ns) or node.findtext('a:content', '', atom_ns))
        pub_raw = node.findtext('a:updated', '', atom_ns) or node.findtext('a:published', '', atom_ns)
        pub = parse_datetime(pub_raw)
        items.append({
            'title_en': title,
            'summary_en': summary[:600],
            'source': source_name,
            'source_kind': source_kind,
            'source_url': link,
            'published_at': pub or now_utc(),
        })
    return items


def fetch_rss(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        raw = fetch_url(source['url'])
        entries = rss_entries(raw, source['name'], source['kind'])
        return [x for x in entries if x.get('title_en') and within_lookback(x.get('published_at'))]
    except Exception as e:
        print(f"[WARN] RSS failed: {source['name']}: {e}")
        return []


def blockbeats_items(payload: Dict[str, Any], source_name: str, source_kind: str) -> List[Dict[str, Any]]:
    rows = []
    data = payload.get('data') or payload.get('list') or payload.get('items') or []
    while isinstance(data, dict):
        moved = False
        for key in ('data', 'list', 'items'):
            if isinstance(data.get(key), list):
                data = data[key]
                moved = True
                break
            if isinstance(data.get(key), dict):
                data = data[key]
                moved = True
                break
        if not moved:
            break
    if not isinstance(data, list):
        return rows
    for item in data:
        title = strip_html(str(item.get('title') or item.get('name') or ''))
        summary = strip_html(str(item.get('content') or item.get('brief') or item.get('summary') or ''))
        link = item.get('link') or item.get('url') or item.get('jump_url') or item.get('share_url') or ''
        pub_raw = str(item.get('publish_time') or item.get('published_at') or item.get('ctime') or item.get('created_at') or '')
        pub = parse_datetime(pub_raw)
        if not pub and pub_raw.isdigit():
            try:
                ts = int(pub_raw)
                if ts > 10**12:
                    ts //= 1000
                pub = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
            except Exception:
                pub = None
        rows.append({
            'title_en': title,
            'summary_en': summary[:600],
            'source': source_name,
            'source_kind': source_kind,
            'source_url': link,
            'published_at': pub or now_utc(),
        })
    return [x for x in rows if x.get('title_en') and within_lookback(x.get('published_at'))]


def blockbeats_xml_items(xml_bytes: bytes, source_name: str, source_kind: str) -> List[Dict[str, Any]]:
    rows = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return rows
    for node in root.findall('.//item'):
        title = strip_html(node.findtext('title') or '')
        summary = strip_html(node.findtext('content') or node.findtext('description') or '')
        link = node.findtext('link') or node.findtext('url') or ''
        pub_raw = node.findtext('create_time') or node.findtext('publish_time') or ''
        pub = None
        if pub_raw and str(pub_raw).isdigit():
            ts = int(str(pub_raw))
            if ts > 10**12:
                ts //= 1000
            pub = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
        rows.append({
            'title_en': title,
            'summary_en': summary[:600],
            'source': source_name,
            'source_kind': source_kind,
            'source_url': link,
            'published_at': pub or now_utc(),
        })
    return [x for x in rows if x.get('title_en') and within_lookback(x.get('published_at'))]


def fetch_api(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        raw = fetch_url(source['url'])
        text = raw.decode('utf-8', errors='ignore').lstrip()
        if text.startswith('{') or text.startswith('['):
            payload = json.loads(text)
            return blockbeats_items(payload, source['name'], source['kind'])
        if text.startswith('<?xml') or text.startswith('<response'):
            return blockbeats_xml_items(raw, source['name'], source['kind'])
        raise RuntimeError('unsupported api response')
    except Exception as e:
        print(f"[WARN] API failed: {source['name']}: {e}")
        return []


def clean_title(title: str) -> str:
    t = strip_html(title).lower()
    t = re.sub(r'https?://\S+', ' ', t)
    t = re.sub(r'\b(update|live|opinion|analysis|watch|podcast|video)\b', ' ', t)
    t = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def title_signature(title: str) -> str:
    tokens = clean_title(title).split()
    if not tokens:
        return ''
    stop = {'the', 'a', 'an', 'to', 'of', 'for', 'and', 'or', 'in', 'on', 'with', 'as', 'is', 'are', 'be', 'by', 'from'}
    tokens = [t for t in tokens if t not in stop]
    return ' '.join(tokens[:12])


def is_junk(item: Dict[str, Any]) -> bool:
    text = f"{item.get('title_en','')} {item.get('summary_en','')}".lower()
    bad = [
        'sponsored', 'advertisement', 'promo', 'learn', 'how to', 'price prediction',
        'top 10', 'top ten', 'weekly recap', 'daily recap', 'morning brief', 'newsletter',
        'podcast', 'video:', 'listen:', 'watch:', 'event recap', 'market wrap'
    ]
    return any(x in text for x in bad)


def category_hint(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ['hack', 'exploit', 'breach', 'attack', 'stolen', 'security', 'vulnerability', 'malware']):
        return 'security'
    if any(k in t for k in ['sec', 'cftc', 'regulator', 'congress', 'policy', 'sanction', 'law', 'lawsuit', 'court', 'etf approval', 'regulation', 'bill', 'act', 'guidance', 'faq']):
        return 'policy'
    if any(k in t for k in ['defi', 'dex', 'lending', 'liquidation', 'restaking', 'staking', 'amm', 'yield farming', 'vault']):
        return 'defi'
    if any(k in t for k in ['funding', 'raises', 'acquires', 'acquisition', 'merger', 'earnings', 'revenue', 'ipo', 'layoff', 'lays off', 'job cuts', 'treasury firm', 'strategy set for', 'microstrategy', 'hires', 'launches product']):
        return 'business'
    if any(k in t for k in ['fed', 'treasury', 'cpi', 'inflation', 'powell', 'rates', 'macro', 'oil', 'bond', 'recession', 'tariff']):
        return 'macro'
    if any(k in t for k in ['bitcoin', 'ether', 'ethereum', 'solana', 'xrp', 'etf inflow', 'etf outflow', 'price', 'market', 'rally', 'selloff', 'stocks', 'nasdaq', 'options', 'volatility']):
        return 'markets'
    return 'technology'


def rough_score(item: Dict[str, Any]) -> int:
    s = SOURCE_PRIORITY.get(item['source'], 50)
    txt = f"{item.get('title_en','')} {item.get('summary_en','')}".lower()
    boosts = {
        10: ['etf', 'sec', 'fed', 'treasury', 'lawsuit', 'hack', 'exploit', 'approval', 'ban', 'tariff'],
        8: ['bitcoin', 'ethereum', 'solana', 'coinbase', 'binance', 'blackrock', 'microstrategy', 'stablecoin'],
        6: ['funding', 'acquisition', 'ipo', 'regulation', 'launch', 'partnership'],
    }
    for pts, keys in boosts.items():
        if any(k in txt for k in keys):
            s += pts
    if item.get('source_kind') == 'macro':
        s += 5
    return s


def dedupe_and_filter(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    kept = {}
    for item in items:
        if is_junk(item):
            continue
        title = item.get('title_en', '').strip()
        if len(title) < 12:
            continue
        sig = title_signature(title) or clean_title(title)
        item['_score'] = rough_score(item)
        item['_topic_key'] = ' '.join((clean_title(title)).split()[:6])
        prev = kept.get(sig)
        if not prev or item['_score'] > prev['_score']:
            kept[sig] = item

    # second-pass loose dedupe for near-duplicate legislation / ETF-flow / rumor headlines
    loose = {}
    for item in kept.values():
        key = item.get('_topic_key') or title_signature(item.get('title_en', ''))
        prev = loose.get(key)
        if not prev or item['_score'] > prev['_score']:
            loose[key] = item

    rows = list(loose.values())
    rows.sort(key=lambda x: (x.get('_score', 0), x.get('published_at', now_utc())), reverse=True)
    return rows


def llm_call(model: str, prompt: str, max_tokens: int, timeout: int) -> str:
    api_key = load_env_key('ZHIPUAI_API_KEY')
    if not api_key:
        raise RuntimeError('ZHIPUAI_API_KEY missing')
    payload_obj = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.2,
        'max_tokens': max_tokens,
    }
    if model == 'glm-4-flash':
        payload_obj['response_format'] = {'type': 'json_object'}
    payload = json.dumps(payload_obj, ensure_ascii=False)

    last_err = 'unknown'
    for attempt in range(5):
        result = subprocess.run([
            'curl', '-s', 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            '-H', f'Authorization: Bearer {api_key}',
            '-H', 'Content-Type: application/json',
            '-d', payload,
            '--max-time', str(timeout),
        ], capture_output=True, text=True, timeout=timeout + 5)
        if result.returncode != 0:
            last_err = result.stderr.strip() or f'curl exit {result.returncode}'
            if attempt < 4:
                time.sleep(2 + attempt * 2)
                continue
            raise RuntimeError(last_err)
        data = json.loads(result.stdout)
        if data.get('error'):
            last_err = json.dumps(data['error'], ensure_ascii=False)
            if '1302' in last_err or '速率限制' in last_err:
                if attempt < 4:
                    time.sleep(4 + attempt * 4)
                    continue
            raise RuntimeError(last_err)
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        if content:
            return content
        last_err = 'empty response'
        if attempt < 4:
            time.sleep(2 + attempt * 2)
    raise RuntimeError(last_err)


def select_top_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    bundled = []
    for i, item in enumerate(items, start=1):
        bundled.append({
            'idx': i,
            'source': item['source'],
            'published_at': item['published_at'].isoformat(),
            'title': item['title_en'],
            'summary': item.get('summary_en', '')[:120],
            'category_hint': category_hint(item['title_en'] + ' ' + item.get('summary_en', '')),
        })
    prompt = (
        '你是 Crypto + 全球金融市场新闻总编。\n'
        '从输入候选新闻中选出最重要的 20-30 条。优先标准：市场影响、政策影响、行业影响、时效性、独特性。\n'
        '额外要求：\n'
        '1. 尽量避免同一事件、同一法案进展、同一资金流主题重复入选。\n'
        '2. business / policy / markets 要分清：公司买币、裁员、融资更偏 business；监管、法案、FAQ、机构指引更偏 policy；价格、期权、ETF资金流更偏 markets。\n'
        '3. importance 要拉开层级：真正影响全市场/监管框架的给 8-10，一般快讯和局部动态给 4-6。\n'
        '输出严格 JSON，对象格式为 {"selected":[{"idx":1,"importance":1-10,"category":"markets|policy|defi|macro|business|security|technology","reason":"<=20字"}]}。\n'
        '不要输出候选里不存在的 idx。尽量返回 25 条左右。\n\n'
        f'候选新闻:\n{json.dumps(bundled, ensure_ascii=False)}'
    )
    raw = llm_call('glm-4-flash', prompt, max_tokens=3000, timeout=180)
    try:
        parsed = json.loads(raw)
        picked = parsed.get('selected', [])
    except Exception:
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match:
            raise
        parsed = json.loads(match.group(0))
        picked = parsed.get('selected', [])

    out = []
    for row in picked:
        try:
            idx = int(row['idx']) - 1
            if idx < 0 or idx >= len(items):
                continue
            base = dict(items[idx])
            base['importance'] = max(1, min(10, int(row.get('importance', 5))))
            cat = str(row.get('category') or category_hint(base['title_en'] + ' ' + base.get('summary_en', '')))
            if cat not in {'markets', 'policy', 'defi', 'macro', 'business', 'security', 'technology'}:
                cat = category_hint(base['title_en'] + ' ' + base.get('summary_en', ''))
            base['category'] = cat
            out.append(base)
        except Exception:
            continue
    # fallback if LLM too sparse
    if len(out) < 20:
        for item in items:
            if len(out) >= MAX_SELECTED:
                break
            if any(x['title_en'] == item['title_en'] and x['source'] == item['source'] for x in out):
                continue
            base = dict(item)
            base['importance'] = min(10, max(4, item.get('_score', 50) // 15))
            base['category'] = category_hint(base['title_en'] + ' ' + base.get('summary_en', ''))
            out.append(base)
    out.sort(key=lambda x: (x.get('importance', 0), x.get('published_at', now_utc())), reverse=True)
    return out[:MAX_SELECTED]


def stable_id(item: Dict[str, Any]) -> str:
    basis = f"{item['source']}|{item['title_en']}|{item.get('source_url','')}"
    digest = hashlib.md5(basis.encode('utf-8')).hexdigest()[:10]
    date_part = item.get('published_at', now_utc()).strftime('%Y%m%d')
    prefix = re.sub(r'[^a-z0-9]+', '-', item['source'].lower()).strip('-')
    return f"{prefix}-{date_part}-{digest}"


def load_cache() -> Dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return {}


def save_cache(cache: Dict[str, Any]) -> None:
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


def parse_json_object(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        cleaned = re.sub(r'^```json\s*|^```\s*|```$', '', raw.strip(), flags=re.I | re.M)
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if not match:
            return {}
        return json.loads(match.group(0))


def summarize_batch(batch: List[Dict[str, Any]], cache: Dict[str, Any]) -> List[Dict[str, Any]]:
    payload_rows = []
    for item in batch:
        item_id = stable_id(item)
        payload_rows.append({
            'id': item_id,
            'source': item['source'],
            'category': item['category'],
            'title_en': item['title_en'],
            'summary_en': item.get('summary_en', '')[:360],
        })

    prompt = (
        '你是财经新闻编辑。请为输入新闻批量生成中文标题和摘要。\n'
        '输出必须是严格 JSON 对象，格式：'
        '{"items":[{"id":"...","title_zh":"...","summary_zh":"..."}]}\n'
        '要求：\n'
        '1. 每条都必须返回，对应原 id。\n'
        '2. title_zh 要像专业资讯编辑写的，简洁、克制、准确，不标题党。\n'
        '3. summary_zh 50-100字，优先交代事实本身，其次再点明影响。\n'
        '4. 严禁脑补：不要写原文没有明确说出的判断，不要使用“这表明”“被视为”“标志着”“说明了”“意味着行业将”这类推论句。\n'
        '5. 保留 Bitcoin、Ethereum、ETF、SEC、Fed 等专有名词。\n'
        '6. 全部用中文输出，不要 markdown，不要解释。\n\n'
        f'新闻列表：\n{json.dumps(payload_rows, ensure_ascii=False)}'
    )
    raw = llm_call('glm-5', prompt, max_tokens=4000, timeout=180)
    parsed = parse_json_object(raw)
    rows = parsed.get('items', []) if isinstance(parsed, dict) else []
    by_id = {}
    for row in rows:
        item_id = str(row.get('id') or '').strip()
        title_zh = str(row.get('title_zh') or '').strip()
        summary_zh = str(row.get('summary_zh') or '').strip()
        if item_id and re.search(r'[\u4e00-\u9fff]', title_zh + summary_zh):
            by_id[item_id] = {'title_zh': title_zh, 'summary_zh': summary_zh}
            cache[item_id] = {'title_zh': title_zh, 'summary_zh': summary_zh, 'cached_at': dt.datetime.now(TZ).isoformat()}

    out = []
    missing = []
    for item in batch:
        item_id = stable_id(item)
        result = dict(item)
        result['id'] = item_id
        hit = by_id.get(item_id) or cache.get(item_id)
        if hit and re.search(r'[\u4e00-\u9fff]', hit.get('title_zh', '') + hit.get('summary_zh', '')):
            result['title_zh'] = hit['title_zh']
            result['summary_zh'] = hit['summary_zh']
            out.append(result)
        else:
            missing.append(item_id)
    if missing:
        # Save cache with partial successes before raising
        save_cache(cache)
        raise RuntimeError(f'batch missing {len(missing)}/{len(batch)} items')
    return out


def summarize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cache = load_cache()
    results = []
    pending = []

    for item in items:
        item_id = stable_id(item)
        cache_hit = cache.get(item_id)
        if cache_hit and re.search(r'[\u4e00-\u9fff]', cache_hit.get('title_zh', '') + cache_hit.get('summary_zh', '')):
            row = dict(item)
            row['id'] = item_id
            row['title_zh'] = cache_hit['title_zh']
            row['summary_zh'] = cache_hit['summary_zh']
            results.append(row)
        else:
            pending.append(dict(item))

    if pending:
        print(f"[INFO] Need GLM-5 summaries: {len(pending)}")
    else:
        print('[INFO] All summaries served from cache')

    for i in range(0, len(pending), SUMMARY_BATCH_SIZE):
        batch = pending[i:i+SUMMARY_BATCH_SIZE]
        try:
            results.extend(summarize_batch(batch, cache))
            time.sleep(2)
        except Exception as e:
            print(f"[WARN] Batch summary failed ({i}-{i+len(batch)-1}): {e}")
            print(f"[INFO] Retrying failed batch one-by-one...")
            for src in batch:
                item_id = stable_id(src)
                # Skip if already got from partial batch success
                if cache.get(item_id, {}).get('title_zh'):
                    row = dict(src)
                    row['id'] = item_id
                    row['title_zh'] = cache[item_id]['title_zh']
                    row['summary_zh'] = cache[item_id]['summary_zh']
                    results.append(row)
                    continue
                # Retry single item
                try:
                    single_result = summarize_batch([src], cache)
                    results.extend(single_result)
                    print(f"[INFO] Single retry OK: {item_id}")
                    time.sleep(1)
                except Exception as e2:
                    print(f"[WARN] Single retry failed: {item_id}: {e2}")
                    fallback = dict(src)
                    fallback['id'] = item_id
                    fallback['title_zh'] = src['title_en']
                    fallback['summary_zh'] = src.get('summary_en', '')[:100]
                    results.append(fallback)

    save_cache(cache)
    by_id = {x['id']: x for x in results}
    return [by_id[stable_id(x)] for x in items]


def post_process_item(item: Dict[str, Any]) -> Dict[str, Any]:
    text = (item.get('title_en', '') + ' ' + item.get('summary_en', '')).lower()
    if any(k in text for k in ['strategy set for', 'microstrategy', 'treasury firm', 'publicly traded', 'layoff', 'lays off', 'job cuts', 'hiring', 'funding', 'acquisition']):
        item['category'] = 'business'
    elif any(k in text for k in ['bitcoin options', 'etf inflow', 'etf outflow', 'price', 'volatility', 'rally', 'selloff']):
        item['category'] = 'markets'
    elif any(k in text for k in ['sec', 'cftc', 'guidance', 'faq', 'act', 'bill', 'lawmakers', 'commissioner']):
        item['category'] = 'policy'
    return item


def normalize_output(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    news = []
    for raw_item in items:
        item = post_process_item(dict(raw_item))
        published = item.get('published_at', now_utc())
        if published.tzinfo is None:
            published = published.replace(tzinfo=dt.timezone.utc)
        news.append({
            'id': item['id'],
            'title_en': item['title_en'],
            'title_zh': item['title_zh'],
            'summary_zh': item['summary_zh'],
            'category': item['category'],
            'importance': item['importance'],
            'source': item['source'],
            'source_url': item.get('source_url', ''),
            'published_at': published.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z'),
        })
    return {
        'updated_at': dt.datetime.now(TZ).isoformat(),
        'count': len(news),
        'news': news,
    }


def write_output(data: Dict[str, Any]) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def collect_all() -> List[Dict[str, Any]]:
    sources = load_sources()
    all_items: List[Dict[str, Any]] = []
    for source in sources.get('rss', []):
        rows = fetch_rss(source)
        print(f"[INFO] RSS {source['name']}: {len(rows)}")
        all_items.extend(rows)
    for source in sources.get('apis', []):
        rows = fetch_api(source)
        print(f"[INFO] API {source['name']}: {len(rows)}")
        all_items.extend(rows)
    return all_items


def git_push_dev() -> None:
    # 保留函数名以免外部调用直接崩。正式发布只走 scripts/daily-run.sh（main 上提交 data/）。
    # 这里不再 push dev：那条旧路径和当前「数据走 main」的发布规则相反。
    print('[INFO] news.json 已写入。提交与推送交给 daily-run.sh，本脚本不 push。')


def main() -> int:
    start = time.time()
    raw = collect_all()
    print(f"[INFO] Raw collected: {len(raw)}")
    coarse = dedupe_and_filter(raw)
    print(f"[INFO] After coarse filter: {len(coarse)}")
    if not coarse:
        print('[ERROR] No news collected after filtering')
        return 1
    selected = select_top_items(coarse[:60])
    print(f"[INFO] Selected by GLM-4-flash: {len(selected)}")
    enriched = summarize_items(selected)
    output = normalize_output(enriched)
    write_output(output)
    elapsed = time.time() - start
    print(f"[INFO] Wrote {OUTPUT_FILE} with {output['count']} items in {elapsed:.1f}s")
    if elapsed > 300:
        print('[WARN] Runtime exceeded 5 minutes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
