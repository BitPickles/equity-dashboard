#!/bin/bash
# task-stop.sh — 一键停止持续任务系统
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPERS="$SCRIPT_DIR/helpers.py"
export TASK_CONFIG="${TASK_CONFIG:-$SCRIPT_DIR/config.json}"

[ -f "$HOME/.openclaw/.env" ] && source "$HOME/.openclaw/.env"

_cfg() { python3 "$HELPERS" read_config "$1" 2>/dev/null; }
_expand() { echo "$1" | sed "s|~|$HOME|g"; }
_acfg() { python3 "$HELPERS" agent_config "$1" "$2" 2>/dev/null; }

PROJECT_NAME=$(_cfg project.name)
PROJECT_DIR=$(_expand "$(_cfg project.dir)")
MAIN_BRANCH=$(_cfg project.branch)
STATE_DIR=$(_expand "$(_cfg paths.state_dir)")
LOGS_DIR=$(_expand "$(_cfg paths.logs_dir)")
AGENTS=($(python3 "$HELPERS" list_agents))
SLOG="$LOGS_DIR/task-events.jsonl"

echo "🛑 停止 ${PROJECT_NAME} 持续任务系统"

# 1. 通知 Agent 收尾
echo ""
echo "=== 1. 通知 Agent 收尾 ==="
for agent in "${AGENTS[@]}"; do
  ADIR=$(_expand "$(_acfg "$agent" worktree)")
  echo "  通知 $agent 收尾..."
  openclaw agent --agent "$agent" \
    -m "⏹️ 任务结束。请在 3 分钟内：
1. 提交所有未保存的改动 (git add -A && git commit)
2. 在 $ADIR 写一个 WRAP-UP.md（做了什么/未完成/遗留/建议）
不要开始新任务。" \
    > "$STATE_DIR/nudge-${agent}.log" 2>&1 &
done

echo "  等待 3 分钟让 Agent 收尾..."
sleep 180

# 2. 备份 WRAP-UP + 兜底 commit
echo ""
echo "=== 2. 收尾归档 ==="
for agent in "${AGENTS[@]}"; do
  ADIR=$(_expand "$(_acfg "$agent" worktree)")
  if [ -d "$ADIR" ]; then
    # 复制 WRAP-UP
    if [ -f "$ADIR/WRAP-UP.md" ]; then
      cp "$ADIR/WRAP-UP.md" "$HOME/clawd/memory/wrapup-${agent}-$(date +%Y%m%d-%H%M).md"
      echo "  ✅ $agent WRAP-UP 已归档"
    else
      echo "  ⚠️ $agent 没写 WRAP-UP"
    fi
    # 兜底: 自动提交未保存改动
    UNCOMMITTED=$(git -C "$ADIR" status --short 2>/dev/null | wc -l | tr -d ' ')
    if [ "$UNCOMMITTED" -gt 0 ]; then
      git -C "$ADIR" add -A 2>/dev/null
      git -C "$ADIR" commit -m "[AUTO] 任务停止时自动提交未保存改动" 2>/dev/null
      echo "  ✅ $agent 自动提交 $UNCOMMITTED 文件"
    fi
  fi
done

# 3. 卸载 launchd
echo ""
echo "=== 3. 卸载 launchd ==="
for p in ai.openclaw.task-monitor ai.openclaw.task-watchdog; do
  PLIST="$HOME/Library/LaunchAgents/${p}.plist"
  if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null
    rm -f "$PLIST"
    echo "  ✅ 卸载 $p"
  fi
done

# 4. 清理 HEARTBEAT.md
echo ""
echo "=== 4. 清理 HEARTBEAT ==="
cat > "$HOME/clawd/HEARTBEAT.md" << 'EOF'
# HEARTBEAT.md

无活跃持续任务。
EOF
echo "  ✅"

# 5. 合并分支
echo ""
echo "=== 5. 合并分支到 $MAIN_BRANCH ==="
cd "$PROJECT_DIR" 2>/dev/null || true
for agent in "${AGENTS[@]}"; do
  ABRANCH=$(_acfg "$agent" branch)
  COMMITS=$(git rev-list "$MAIN_BRANCH".."$ABRANCH" --count 2>/dev/null || echo "0")
  if [ "$COMMITS" -gt 0 ]; then
    git checkout "$MAIN_BRANCH" 2>/dev/null
    if git merge "$ABRANCH" --no-edit 2>/dev/null; then
      echo "  ✅ $ABRANCH ($COMMITS commits) → $MAIN_BRANCH"
    else
      echo "  ⚠️ $ABRANCH 合并冲突，需手动处理"
      git merge --abort 2>/dev/null
    fi
  else
    echo "  - $ABRANCH 无新 commits"
  fi
done

# 6. 记录事件
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"event\":\"task_stop\",\"agent\":\"\",\"detail\":\"project=${PROJECT_NAME}\"}" >> "$SLOG"

echo ""
echo "=== 🛑 已停止 ==="
echo "WRAP-UP: ~/clawd/memory/wrapup-*"
echo "日志: $LOGS_DIR/"
