#!/bin/bash
# task-start.sh — 一键启动持续任务系统（通用版）
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPERS="$SCRIPT_DIR/helpers.py"
export TASK_CONFIG="${TASK_CONFIG:-$SCRIPT_DIR/config.json}"

[ -f "$HOME/.openclaw/.env" ] && source "$HOME/.openclaw/.env"

# DRY RUN 模式
DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true && echo "🔍 DRY RUN 模式 — 只展示，不执行"

# 验证配置
echo "=== 0. 验证配置 ==="
python3 "$HELPERS" validate_config || exit 1

_cfg() { python3 "$HELPERS" read_config "$1" 2>/dev/null; }
_expand() { echo "$1" | sed "s|~|$HOME|g"; }
_acfg() { python3 "$HELPERS" agent_config "$1" "$2" 2>/dev/null; }

PROJECT_NAME=$(_cfg project.name)
PROJECT_DIR=$(_expand "$(_cfg project.dir)")
MAIN_BRANCH=$(_cfg project.branch)
STATE_DIR=$(_expand "$(_cfg paths.state_dir)")
LOGS_DIR=$(_expand "$(_cfg paths.logs_dir)")
CHECKS_FILE=$(_expand "$(_cfg paths.checks_file)")
TASK_REGISTRY=$(_expand "$(_cfg paths.task_registry)")
CHAT_ID=$(_cfg telegram.chat_id)

AGENTS=($(python3 "$HELPERS" list_agents))
SLOG="$LOGS_DIR/task-events.jsonl"

echo ""
echo "🚀 启动 ${PROJECT_NAME} 持续任务系统"

# 1. Worktree
echo ""
echo "=== 1. Git Worktree ==="
if [ "$DRY_RUN" = false ]; then
  cd "$PROJECT_DIR" || { echo "❌ 项目目录不存在: $PROJECT_DIR"; exit 1; }
fi
for agent in "${AGENTS[@]}"; do
  ADIR=$(_expand "$(_acfg "$agent" worktree)")
  ABRANCH=$(_acfg "$agent" branch)
  if [ "$DRY_RUN" = true ]; then
    echo "  [DRY] git worktree add $ADIR $ABRANCH"
  else
    if [ ! -d "$ADIR" ]; then
      git worktree add "$ADIR" "$ABRANCH" 2>&1 || echo "  ⚠️ worktree 已存在或分支问题"
    fi
    [ ! -d "$ADIR/node_modules" ] && [ -f "$ADIR/package.json" ] && (cd "$ADIR" && npm install --silent 2>/dev/null)
  fi
  echo "  ✅ $agent → $ADIR ($ABRANCH)"
done

# 2. 状态清理
echo ""
echo "=== 2. 清理状态 ==="
if [ "$DRY_RUN" = false ]; then
  mkdir -p "$STATE_DIR/nudge-cooldown" "$LOGS_DIR"
  rm -f "$STATE_DIR/completed-agents" "$STATE_DIR/last-report-hash" "$STATE_DIR/nudge-cooldown"/*
  touch "$STATE_DIR/completed-agents"
fi
echo "  ✅ $STATE_DIR"

# 3. HEARTBEAT.md
echo ""
echo "=== 3. HEARTBEAT.md ==="
if [ "$DRY_RUN" = false ]; then
  cat > "$HOME/clawd/HEARTBEAT.md" << EOF
# HEARTBEAT.md

## 活跃持续任务

项目: ${PROJECT_NAME}
脚本自动监控中。不需要 Agent 执行任何检查。
回复 HEARTBEAT_OK 即可。
EOF
fi
echo "  ✅"

# 4. 安装 launchd
echo ""
echo "=== 4. 安装 launchd ==="
MONITOR_PLIST="$HOME/Library/LaunchAgents/ai.openclaw.task-monitor.plist"
WATCHDOG_PLIST="$HOME/Library/LaunchAgents/ai.openclaw.task-watchdog.plist"

if [ "$DRY_RUN" = false ]; then
  cat > "$MONITOR_PLIST" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>ai.openclaw.task-monitor</string>
    <key>ProgramArguments</key><array>
        <string>/bin/bash</string>
        <string>$SCRIPT_DIR/task-monitor.sh</string>
    </array>
    <key>StartInterval</key><integer>300</integer>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>$LOGS_DIR/launchd-monitor.log</string>
    <key>StandardErrorPath</key><string>$LOGS_DIR/launchd-monitor-err.log</string>
    <key>EnvironmentVariables</key><dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>TASK_CONFIG</key><string>$TASK_CONFIG</string>
    </dict>
</dict>
</plist>
PLIST

  cat > "$WATCHDOG_PLIST" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>ai.openclaw.task-watchdog</string>
    <key>ProgramArguments</key><array>
        <string>/bin/bash</string>
        <string>$SCRIPT_DIR/system-watchdog.sh</string>
    </array>
    <key>StartInterval</key><integer>1800</integer>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>$LOGS_DIR/launchd-watchdog.log</string>
    <key>StandardErrorPath</key><string>$LOGS_DIR/launchd-watchdog-err.log</string>
    <key>EnvironmentVariables</key><dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>TASK_CONFIG</key><string>$TASK_CONFIG</string>
    </dict>
</dict>
</plist>
PLIST

  for p in ai.openclaw.task-monitor ai.openclaw.task-watchdog; do
    launchctl unload "$HOME/Library/LaunchAgents/${p}.plist" 2>/dev/null
    launchctl load "$HOME/Library/LaunchAgents/${p}.plist" 2>&1
    echo "  ✅ $p"
  done
else
  echo "  [DRY] 安装 task-monitor (5min) + watchdog (30min)"
fi

# 5. 派发任务
echo ""
echo "=== 5. 派发任务 ==="
for agent in "${AGENTS[@]}"; do
  ADIR=$(_expand "$(_acfg "$agent" worktree)")
  ABRANCH=$(_acfg "$agent" branch)
  AROLE=$(_acfg "$agent" role)
  TASKS=$(python3 "$HELPERS" get_remaining_tasks "$agent" 2>/dev/null)

  MSG="🔧 任务指令
角色：$AROLE | 工作目录：$ADIR（$ABRANCH 分支，不需要 checkout）
任务：
$TASKS
规则：在 $ADIR 目录工作，每完成一步 git commit。全部完成后在工作目录创建 .done 文件，或最后一条 commit message 包含 [DONE]。"

  if [ "$DRY_RUN" = true ]; then
    echo "  [DRY] openclaw agent --agent $agent -m '...(${#TASKS} chars tasks)'"
  else
    nohup openclaw agent --agent "$agent" -m "$MSG" > "$STATE_DIR/nudge-${agent}.log" 2>&1 &
    echo "  ✅ $agent (pid=$!)"
  fi
done

# 6. 记录启动事件
if [ "$DRY_RUN" = false ]; then
  mkdir -p "$(dirname "$SLOG")"
  echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"event\":\"task_start\",\"agent\":\"\",\"detail\":\"project=${PROJECT_NAME} agents=${#AGENTS[@]}\"}" >> "$SLOG"
fi

echo ""
echo "=== 🎉 启动完成 ==="
echo "项目: $PROJECT_NAME"
echo "Agent: ${AGENTS[*]}"
echo "监控: launchd 每5分钟 | 看门狗: launchd 每30分钟"
echo "汇报: 直接 Telegram（内容变化时发送）"
echo "完成信号: .done 文件 或 commit [DONE] tag"
