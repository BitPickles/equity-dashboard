import json, os, glob
print('=== data/daily/<id>/latest.json 新鲜度 ===')
files = glob.glob('data/daily/*/latest.json')
print('count:', len(files))
for f in sorted(files):
    pid = os.path.basename(os.path.dirname(f))
    try:
        d = json.load(open(f, encoding='utf-8'))
        upd = d.get('updated_at') or (d.get('latest_record') or {}).get('date') or '?'
        print('%-16s updated_at: %s' % (pid, upd))
    except Exception as e:
        print('%-16s ERROR: %s' % (pid, str(e)[:60]))
print()
print('=== data/protocols/<id>/config.json last_updated ===')
cfgs = glob.glob('data/protocols/*/config.json')
print('count:', len(cfgs))
for f in sorted(cfgs):
    pid = os.path.basename(os.path.dirname(f))
    try:
        d = json.load(open(f, encoding='utf-8'))
        print('%-16s last_updated: %s' % (pid, d.get('last_updated', '?')))
    except Exception as e:
        print('%-16s ERROR: %s' % (pid, str(e)[:60]))
