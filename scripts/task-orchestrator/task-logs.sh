#!/bin/bash
# task-logs.sh — 查询任务日志（通用版）
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPERS="$SCRIPT_DIR/helpers.py"
export TASK_CONFIG="${TASK_CONFIG:-$SCRIPT_DIR/config.json}"

_cfg() { python3 "$HELPERS" read_config "$1" 2>/dev/null; }
_expand() { echo "$1" | sed "s|~|$HOME|g"; }

LOGS_DIR=$(_expand "$(_cfg paths.logs_dir)")
SLOG="$LOGS_DIR/task-events.jsonl"

# 参数
AGENT=""
EVENT=""
MINUTES=0
ERRORS=false
ALL=false
LIMIT=20

while [ $# -gt 0 ]; do
  case "$1" in
    -a|--agent) AGENT="$2"; shift 2 ;;
    -e|--event) EVENT="$2"; shift 2 ;;
    -t|--time) MINUTES="$2"; shift 2 ;;
    -n|--limit) LIMIT="$2"; shift 2 ;;
    --errors) ERRORS=true; shift ;;
    --all) ALL=true; shift ;;
    -h|--help)
      echo "用法: task-logs.sh [选项]"
      echo "  -a, --agent <name>  按 Agent 过滤"
      echo "  -e, --event <type>  按事件类型过滤 (nudge/reset/done_signal/heartbeat/...)"
      echo "  -t, --time <min>    最近 N 分钟"
      echo "  -n, --limit <N>     最多显示 N 条 (默认 20)"
      echo "  --errors            只看错误"
      echo "  --all               显示所有日志摘要"
      exit 0 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

if [ "$ALL" = true ]; then
  echo "=== 事件日志 (最近 $LIMIT 条) ==="
  tail -"$LIMIT" "$SLOG" 2>/dev/null | python3 -c "
import sys,json
for line in sys.stdin:
    try:
        d=json.loads(line.strip())
        print(f\"{d['ts'][:19]} {d['event']:20s} {d.get('agent',''):12s} {d.get('detail','')[:60]}\")
    except: pass
"
  echo ""
  echo "=== 监控日志 (最近 10 行) ==="
  tail -10 "$LOGS_DIR/task-monitor.log" 2>/dev/null
  echo ""
  echo "=== 看门狗 (最近 5 行) ==="
  tail -5 "$LOGS_DIR/watchdog.log" 2>/dev/null
  exit 0
fi

# 过滤查询
python3 -c "
import json, sys, time
now = time.time()
minutes = $MINUTES
agent = '$AGENT'
event = '$EVENT'
errors = $( [ "$ERRORS" = true ] && echo "True" || echo "False" )
limit = $LIMIT
results = []

with open('$SLOG') as f:
    for line in f:
        try:
            d = json.loads(line.strip())
            if agent and d.get('agent') != agent: continue
            if event and d.get('event') != event: continue
            if errors and 'error' not in d.get('event','').lower() and 'alert' not in d.get('event','').lower(): continue
            if minutes > 0:
                from datetime import datetime, timezone
                ts = datetime.fromisoformat(d['ts'].replace('Z','+00:00')).timestamp()
                if now - ts > minutes * 60: continue
            results.append(d)
        except: pass

for d in results[-limit:]:
    print(f\"{d['ts'][:19]} {d['event']:20s} {d.get('agent',''):12s} {d.get('detail','')[:80]}\")

if not results:
    print('无匹配记录')
" 2>/dev/null
