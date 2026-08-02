#!/bin/bash
# task-monitor.sh — 通用持续任务监控脚本
# 由 launchd 每 5 分钟调度，不依赖任何 Agent
# 所有 Python 逻辑通过 helpers.py 调用
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPERS="$SCRIPT_DIR/helpers.py"
export TASK_CONFIG="${TASK_CONFIG:-$SCRIPT_DIR/config.json}"

# 并发锁：防止上一轮未结束时重叠执行（mkdir 原子操作，macOS 兼容）
LOCK_DIR="/tmp/task-orchestrator-monitor.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  # 检查锁是否过期（超过 10 分钟视为僵尸锁）
  if [ -d "$LOCK_DIR" ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo "0") ))
    if [ "$LOCK_AGE" -gt 600 ]; then
      rm -rf "$LOCK_DIR"
      mkdir "$LOCK_DIR" 2>/dev/null || { echo "[$(date)] 锁竞争失败" >> "$HOME/clawd/logs/task-monitor.log"; exit 0; }
    else
      echo "[$(date)] 上一轮仍在运行（${LOCK_AGE}s），跳过" >> "$HOME/clawd/logs/task-monitor.log"
      exit 0
    fi
  fi
fi
trap "rm -rf '$LOCK_DIR'" EXIT

# 加载环境变量（TG_BOT_TOKEN 等）
[ -f "$HOME/.openclaw/.env" ] && source "$HOME/.openclaw/.env"

# 配置验证
python3 "$HELPERS" validate_config >/dev/null 2>&1 || { echo "配置无效，跳过"; exit 1; }

#=== 读取配置 ===
_cfg() { python3 "$HELPERS" read_config "$1" 2>/dev/null; }
_expand() { echo "$1" | sed "s|~|$HOME|g"; }
_acfg() { python3 "$HELPERS" agent_config "$1" "$2" 2>/dev/null; }

PROJECT_NAME=$(_cfg project.name)
PROJECT_DIR=$(_expand "$(_cfg project.dir)")
MAIN_BRANCH=$(_cfg project.branch)
CHAT_ID=$(_cfg telegram.chat_id)
TG_TOKEN_ENV=$(_cfg telegram.bot_token_env)
TG_PROXY=$(_cfg telegram.proxy)
STATE_DIR=$(_expand "$(_cfg paths.state_dir)")
LOGS_DIR=$(_expand "$(_cfg paths.logs_dir)")
CHECKS_FILE=$(_expand "$(_cfg paths.checks_file)")
TASK_REGISTRY=$(_expand "$(_cfg paths.task_registry)")

NUDGE_MIN=$(_cfg thresholds.nudge_minutes); NUDGE_MIN=${NUDGE_MIN:-30}
RESET_MIN=$(_cfg thresholds.reset_minutes); RESET_MIN=${RESET_MIN:-120}
COOLDOWN_MIN=$(_cfg thresholds.nudge_cooldown_minutes); COOLDOWN_MIN=${COOLDOWN_MIN:-15}
SESSION_MAX=$(_cfg thresholds.session_max_lines); SESSION_MAX=${SESSION_MAX:-300}

AGENTS=($(python3 "$HELPERS" list_agents))

# 读 TG bot token
eval "TG_TOKEN=\${$TG_TOKEN_ENV:-}"
TG_CURL_OPTS=""
[ -n "${TG_PROXY:-}" ] && TG_CURL_OPTS="--proxy $TG_PROXY"

mkdir -p "$STATE_DIR/nudge-cooldown" "$LOGS_DIR"
touch "$STATE_DIR/completed-agents"

NOW=$(date +%s)
LOG="$LOGS_DIR/task-monitor.log"
SLOG="$LOGS_DIR/task-events.jsonl"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }
slog() {
  echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"event\":\"$1\",\"agent\":\"${2:-}\",\"detail\":\"${3:-}\"}" >> "$SLOG"
}

# 直接 curl Telegram（不绕 Agent，纯文本模式避免格式问题）
tg_send() {
  local msg="$1"
  if [ -z "$TG_TOKEN" ]; then
    log "WARN: TG_TOKEN 为空，跳过发送"
    return 1
  fi
  local result
  result=$(curl -s -X POST $TG_CURL_OPTS \
    "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${msg}" \
    --max-time 15 2>&1)
  if echo "$result" | grep -q '"ok":true'; then
    log "TG_SEND: OK"
  else
    log "TG_SEND_FAIL: $result"
  fi
}

REPORT_LINES=""
NUDGE_LOG=""
NEED_COMMANDER=false
COMMANDER_REASON=""

#=== 检查各 Agent ===
for agent in "${AGENTS[@]}"; do
  ADIR=$(_expand "$(_acfg "$agent" worktree)")
  ABRANCH=$(_acfg "$agent" branch)
  AROLE=$(_acfg "$agent" role)

  # 跳过已完成
  if grep -q "^${agent}$" "$STATE_DIR/completed-agents" 2>/dev/null; then
    REPORT_LINES="$REPORT_LINES\n- $agent: ✅ 已完成"
    continue
  fi

  # --- Commit 检查 ---
  COMMIT_IDLE=9999
  COMMITS_10M=0
  if [ -d "$ADIR" ]; then
    LAST_TS=$(git -C "$ADIR" log --format="%ct" -1 2>/dev/null || echo "0")
    [ "$LAST_TS" -gt 0 ] && COMMIT_IDLE=$(( (NOW - LAST_TS) / 60 ))
    COMMITS_10M=$(git -C "$ADIR" log --oneline --since='10 minutes ago' 2>/dev/null | wc -l | tr -d ' ')
  fi

  # --- Session 检查 ---
  SESSION_INFO=$(python3 "$HELPERS" last_session_ts "$agent" 2>/dev/null)
  SESSION_TS=$(echo "$SESSION_INFO" | awk '{print $1}')
  SESSION_LINES=$(echo "$SESSION_INFO" | awk '{print $2}')
  SESSION_FILE=$(echo "$SESSION_INFO" | awk '{$1=$2=""; print $0}' | xargs)
  SESSION_IDLE=9999
  [ "${SESSION_TS:-0}" -gt 0 ] && SESSION_IDLE=$(( (NOW - SESSION_TS) / 60 ))

  # --- 结构化完成信号检测 ---
  DONE_SIGNAL=$(python3 "$HELPERS" check_done_signal "$ADIR" 2>/dev/null)
  if [ "$DONE_SIGNAL" = "done" ]; then
    echo "$agent" >> "$STATE_DIR/completed-agents"
    python3 "$HELPERS" mark_agent_done "$agent" 2>/dev/null
    NEED_COMMANDER=true
    COMMANDER_REASON="$COMMANDER_REASON $agent:完成信号(.done/[DONE]tag);"
    REPORT_LINES="$REPORT_LINES\n- $agent: ✅ 刚完成"
    log "DONE_SIGNAL: $agent"
    slog "done_signal" "$agent" "structured"
    continue
  fi

  # --- 假忙检测 ---
  FAKE_STATUS=""
  FAKE_SUGGESTION=""
  if [ -n "$SESSION_FILE" ] && [ "$SESSION_IDLE" -lt 10 ] && [ "$COMMIT_IDLE" -ge "$NUDGE_MIN" ]; then
    FAKE_RESULT=$(python3 "$HELPERS" check_fake_busy "$SESSION_FILE" 2>/dev/null)
    FAKE_STATUS=$(echo "$FAKE_RESULT" | cut -d'|' -f1)
    FAKE_SUGGESTION=$(echo "$FAKE_RESULT" | cut -d'|' -f2-)
    [ "$FAKE_STATUS" = "ok" ] && FAKE_STATUS="" && FAKE_SUGGESTION=""
  fi

  # --- 未提交改动检查 ---
  UNCOMMITTED=0
  [ -d "$ADIR" ] && UNCOMMITTED=$(git -C "$ADIR" status --short 2>/dev/null | wc -l | tr -d ' ')

  # --- 状态判定 ---
  if [ "$COMMIT_IDLE" -lt 10 ]; then
    STATUS="🟢 活跃（${COMMITS_10M}/10m）"
  elif [ -n "$FAKE_STATUS" ]; then
    STATUS="🟠 假忙（$FAKE_STATUS）"
  elif [ "$UNCOMMITTED" -gt 5 ]; then
    STATUS="🟠 ${UNCOMMITTED}文件未提交"
    FAKE_SUGGESTION="立即 git add -A && git commit"
  elif [ "$COMMIT_IDLE" -lt "$NUDGE_MIN" ]; then
    STATUS="🟡 ${COMMIT_IDLE}m前"
  elif [ "$COMMIT_IDLE" -lt "$RESET_MIN" ]; then
    STATUS="🟠 ${COMMIT_IDLE}m未commit"
  else
    STATUS="🔴 停滞$(( COMMIT_IDLE / 60 ))h"
  fi
  REPORT_LINES="$REPORT_LINES\n- $agent: $STATUS"

  # --- 催促逻辑 ---
  NEED_NUDGE=false
  ACTION="nudge"
  if [ "$COMMIT_IDLE" -ge "$RESET_MIN" ]; then
    NEED_NUDGE=true; ACTION="reset"
  elif [ "$COMMIT_IDLE" -ge "$NUDGE_MIN" ] || [ -n "$FAKE_SUGGESTION" ]; then
    NEED_NUDGE=true
  fi

  if [ "$NEED_NUDGE" = true ]; then
    # 冷却检查
    CD_FILE="$STATE_DIR/nudge-cooldown/$agent"
    if [ -f "$CD_FILE" ]; then
      CD_AGE=$(( (NOW - $(cat "$CD_FILE")) / 60 ))
      [ "$CD_AGE" -lt "$COOLDOWN_MIN" ] && continue
    fi

    TASKS=$(python3 "$HELPERS" get_remaining_tasks "$agent" 2>/dev/null)

    if [ "$ACTION" = "reset" ]; then
      # 用 openclaw 命令 reset（不直接操作文件）
      openclaw agent --agent "$agent" --session-id "reset-$(date +%s)" \
        -m "🔧 新 Session。你的工作目录：$ADIR（$ABRANCH 分支）。剩余任务：
$TASKS
完成后在工作目录创建 .done 文件，或 commit message 包含 [DONE]。每完成一步 git commit。" \
        > "$STATE_DIR/nudge-${agent}.log" 2>&1 &
    elif [ -n "$FAKE_SUGGESTION" ]; then
      openclaw agent --agent "$agent" \
        -m "⚠️ $FAKE_SUGGESTION
工作目录：$ADIR。剩余任务：
$TASKS" \
        >> "$STATE_DIR/nudge-${agent}.log" 2>&1 &
    else
      openclaw agent --agent "$agent" \
        -m "⚠️ 已停滞 ${COMMIT_IDLE} 分钟。继续做：
$TASKS
每完成一步 git commit。完成后创建 .done 文件或 commit [DONE]。" \
        >> "$STATE_DIR/nudge-${agent}.log" 2>&1 &
    fi

    date +%s > "$CD_FILE"
    NUDGE_LOG="$NUDGE_LOG $ACTION:$agent"
    log "AUTO $ACTION: $agent"
    slog "$ACTION" "$agent" "commit_idle=${COMMIT_IDLE}m"
  fi

  # --- Session 轮换检查 ---
  if [ "${SESSION_LINES:-0}" -gt "$SESSION_MAX" ]; then
    TOTAL_C=$(git -C "$PROJECT_DIR" rev-list "$MAIN_BRANCH".."$ABRANCH" --count 2>/dev/null || echo "0")
    TASKS=$(python3 "$HELPERS" get_remaining_tasks "$agent" 2>/dev/null)

    openclaw agent --agent "$agent" --session-id "rotate-$(date +%s)" \
      -m "🔄 Session 轮换。工作目录：$ADIR（$ABRANCH）。已有 $TOTAL_C commits。剩余任务：
$TASKS
继续工作，每完成一步 git commit。完成后创建 .done 文件或 commit [DONE]。" \
      > "$STATE_DIR/nudge-${agent}.log" 2>&1 &
    log "SESSION_ROTATE: $agent (${SESSION_LINES} lines)"
    slog "session_rotate" "$agent" "${SESSION_LINES}lines"
  fi
done

#=== 全部完成检测 ===
COMPLETED_COUNT=$(sort -u "$STATE_DIR/completed-agents" | wc -l | tr -d ' ')
TOTAL_AGENTS=${#AGENTS[@]}
if [ "$COMPLETED_COUNT" -ge "$TOTAL_AGENTS" ] && [ "$TOTAL_AGENTS" -gt 0 ]; then
  NEED_COMMANDER=true
  COMMANDER_REASON="🎉 所有 Agent 已完成！需要最终验收。"
fi

#=== 唤醒总管 ===
if [ "$NEED_COMMANDER" = true ]; then
  if [ "$COMPLETED_COUNT" -ge "$TOTAL_AGENTS" ]; then
    CMD_MSG="🔔 所有 Agent 已完成！请做最终验收，验收后通知 Boss。
$COMMANDER_REASON"
  else
    CMD_MSG="🔔 有 Agent 完成了当前任务，立即验收并派下一阶段任务。
$COMMANDER_REASON"
  fi
  openclaw agent --agent main -m "$CMD_MSG" --deliver --channel telegram \
    > "$STATE_DIR/commander-wake.log" 2>&1 &
  log "COMMANDER_WAKE: $COMMANDER_REASON"
  slog "commander_wake" "main" "$COMMANDER_REASON"
fi

#=== 写 checks 文件 ===
ROUND=$(grep -c "^## 第" "$CHECKS_FILE" 2>/dev/null || echo "0")
ROUND=$((ROUND + 1))
{
  echo ""
  echo "## 第${ROUND}轮检查（$(date '+%H:%M')）"
  echo -e "$REPORT_LINES"
  [ -n "$(echo "$NUDGE_LOG" | xargs)" ] && echo "- 自动操作:$NUDGE_LOG"
  [ "$NEED_COMMANDER" = true ] && echo "- 🔔 已唤醒总管"
} >> "$CHECKS_FILE"

python3 "$HELPERS" trim_checks "$CHECKS_FILE" 50 2>/dev/null

#=== 写汇报文本（管道格式：name|status|commits）===
REPORT_INPUT=""
for agent in "${AGENTS[@]}"; do
  ABRANCH=$(_acfg "$agent" branch)
  COMMITS=$(git -C "$PROJECT_DIR" rev-list "$MAIN_BRANCH".."$ABRANCH" --count 2>/dev/null || echo "0")
  ASTATUS=$(echo -e "$REPORT_LINES" | grep "^- $agent:" | sed "s/^- $agent: //")
  REPORT_INPUT="$REPORT_INPUT${agent}|${ASTATUS}|${COMMITS}
"
done

REPORT_TEXT=$(echo "$REPORT_INPUT" | python3 "$HELPERS" build_report 2>/dev/null)
echo "$REPORT_TEXT" > "$STATE_DIR/latest-report.txt"

# 汇报去重：内容无变化不发（macOS 兼容）
REPORT_HASH=$(echo "$REPORT_TEXT" | shasum -a 256 2>/dev/null | awk '{print $1}')
LAST_HASH=$(cat "$STATE_DIR/last-report-hash" 2>/dev/null || echo "")
if [ "$REPORT_HASH" != "$LAST_HASH" ]; then
  tg_send "$REPORT_TEXT"
  echo "$REPORT_HASH" > "$STATE_DIR/last-report-hash"
  slog "report_sent" "" "hash=$REPORT_HASH"
fi

#=== 心跳时间戳 ===
echo "$NOW" > "$STATE_DIR/last-heartbeat-ts"

#=== 日志轮换 ===
[ -f "$LOG" ] && [ "$(wc -l < "$LOG" | tr -d ' ')" -gt 500 ] && tail -300 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"

log "HEARTBEAT_DONE: round=$ROUND nudge='$NUDGE_LOG' commander=$NEED_COMMANDER"
slog "heartbeat" "" "round=$ROUND"
