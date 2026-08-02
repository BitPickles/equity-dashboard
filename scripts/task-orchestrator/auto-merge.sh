#!/bin/bash
# auto-merge.sh — 合并各 Agent 分支到主开发分支（通用版）
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPERS="$SCRIPT_DIR/helpers.py"
export TASK_CONFIG="${TASK_CONFIG:-$SCRIPT_DIR/config.json}"

_cfg() { python3 "$HELPERS" read_config "$1" 2>/dev/null; }
_expand() { echo "$1" | sed "s|~|$HOME|g"; }
_acfg() { python3 "$HELPERS" agent_config "$1" "$2" 2>/dev/null; }

PROJECT_DIR=$(_expand "$(_cfg project.dir)")
MAIN_BRANCH=$(_cfg project.branch)
LOGS_DIR=$(_expand "$(_cfg paths.logs_dir)")
AGENTS=($(python3 "$HELPERS" list_agents))

LOG="$LOGS_DIR/auto-merge.log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

cd "$PROJECT_DIR" || { echo "❌ 项目目录不存在"; exit 1; }
git checkout "$MAIN_BRANCH" 2>/dev/null

MERGED=0
CONFLICTS=0

for agent in "${AGENTS[@]}"; do
  ABRANCH=$(_acfg "$agent" branch)
  COMMITS=$(git rev-list "$MAIN_BRANCH".."$ABRANCH" --count 2>/dev/null || echo "0")
  
  if [ "$COMMITS" -gt 0 ]; then
    if git merge "$ABRANCH" --no-edit 2>/dev/null; then
      echo "✅ $ABRANCH → $MAIN_BRANCH ($COMMITS commits)"
      log "MERGED: $ABRANCH ($COMMITS commits)"
      MERGED=$((MERGED + 1))
    else
      echo "⚠️ $ABRANCH 冲突"
      git merge --abort 2>/dev/null
      log "CONFLICT: $ABRANCH"
      CONFLICTS=$((CONFLICTS + 1))
    fi
  fi
done

echo "合并: $MERGED | 冲突: $CONFLICTS"

# 可选: 构建检查
if [ -f "package.json" ] && [ "$MERGED" -gt 0 ]; then
  echo "运行构建检查..."
  if npm run build --silent 2>/dev/null; then
    echo "✅ 构建通过"
    log "BUILD: OK"
  else
    echo "❌ 构建失败"
    log "BUILD: FAILED"
  fi
fi
