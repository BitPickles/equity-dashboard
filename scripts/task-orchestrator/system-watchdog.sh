#!/bin/bash
# system-watchdog.sh — 系统级看门狗，launchd 每 30 分钟调度
# 通用化：从 config.json 读取所有参数
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPERS="$SCRIPT_DIR/helpers.py"
export TASK_CONFIG="${TASK_CONFIG:-$SCRIPT_DIR/config.json}"

[ -f "$HOME/.openclaw/.env" ] && source "$HOME/.openclaw/.env"

_cfg() { python3 "$HELPERS" read_config "$1" 2>/dev/null; }
_expand() { echo "$1" | sed "s|~|$HOME|g"; }

LOGS_DIR=$(_expand "$(_cfg paths.logs_dir)")
STATE_DIR=$(_expand "$(_cfg paths.state_dir)")
CHAT_ID=$(_cfg telegram.chat_id)
TG_TOKEN_ENV=$(_cfg telegram.bot_token_env)
TG_PROXY=$(_cfg telegram.proxy)
AGENTS=($(python3 "$HELPERS" list_agents))

eval "TG_TOKEN=\${$TG_TOKEN_ENV:-}"
TG_CURL_OPTS=""
[ -n "${TG_PROXY:-}" ] && TG_CURL_OPTS="--proxy $TG_PROXY"

mkdir -p "$LOGS_DIR" "$STATE_DIR"
LOG="$LOGS_DIR/watchdog.log"
NOW=$(date +%s)

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

send_alert() {
  local msg="$1"
  ALERT_FILE="$STATE_DIR/watchdog-alert"
  if [ -f "$ALERT_FILE" ]; then
    ALERT_AGE=$(( (NOW - $(cat "$ALERT_FILE")) / 60 ))
    [ "$ALERT_AGE" -lt 60 ] && { log "ALERT_COOLDOWN: $msg"; return; }
  fi
  echo "$NOW" > "$ALERT_FILE"
  log "🚨 ALERT: $msg"

  # 直接 curl Telegram（data-urlencode 避免特殊字符问题）
  if [ -n "$TG_TOKEN" ]; then
    curl -s -X POST $TG_CURL_OPTS \
      "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${CHAT_ID}" \
      --data-urlencode "text=🚨 看门狗警报：${msg}" \
      --max-time 15 > /dev/null 2>&1
  fi
  # 也通过 openclaw 发（双保险）
  nohup openclaw agent --agent main -m "🚨 看门狗警报：$msg" --deliver --channel telegram > /dev/null 2>&1 &
}

# 检查是否有活跃任务
if ! grep -q "活跃持续任务" "$HOME/clawd/HEARTBEAT.md" 2>/dev/null; then
  log "OK: 无活跃任务"
  exit 0
fi

# 1. Gateway 进程
if ! pgrep -f "openclaw" > /dev/null 2>&1; then
  send_alert "Gateway 进程不存在！尝试重启..."
  openclaw gateway start 2>/dev/null &
  exit 1
fi

# 2. 心跳是否在执行
LAST_HB_TS=$(cat "$STATE_DIR/last-heartbeat-ts" 2>/dev/null || echo "0")
if [ "$LAST_HB_TS" -gt 0 ]; then
  HB_AGE=$(( (NOW - LAST_HB_TS) / 60 ))
  if [ "$HB_AGE" -gt 15 ]; then
    send_alert "心跳 ${HB_AGE} 分钟未执行！"
    bash "$SCRIPT_DIR/task-monitor.sh" >> "$LOG" 2>&1 &
  else
    log "OK: 心跳 ${HB_AGE}m 前执行"
  fi
else
  log "WARN: 无心跳记录"
fi

# 3. Agent 全停检测
ALL_DEAD=true
for agent in "${AGENTS[@]}"; do
  SESSION_INFO=$(python3 "$HELPERS" last_session_ts "$agent" 2>/dev/null)
  SESSION_TS=$(echo "$SESSION_INFO" | awk '{print $1}')
  if [ "${SESSION_TS:-0}" -gt 0 ]; then
    IDLE=$(( (NOW - SESSION_TS) / 60 ))
    [ "$IDLE" -lt 60 ] && ALL_DEAD=false
  fi
done

if [ "$ALL_DEAD" = true ]; then
  send_alert "所有 Agent 超过 1 小时无活动！"
fi

log "看门狗完成"

# 日志轮换
[ -f "$LOG" ] && [ "$(wc -l < "$LOG" | tr -d ' ')" -gt 500 ] && tail -300 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
