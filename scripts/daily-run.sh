#!/bin/bash
# 每日数据更新（Mac Mini cron 用）
# 与 WorkBuddy automation 相同流程：update-prices → rebuild-daily → sync → validate → push dev
# 用法: bash scripts/daily-run.sh
set -e
cd "$(dirname "$0")/.."
PY=python3

echo "=== $(date) 每日更新开始 ==="

# 1. 更新价格/市值（CoinGecko，约1分钟）
$PY scripts/update-prices.py

# 2. 刷新 daily 数据（防僵尸）
$PY scripts/rebuild-daily.py

# 3. 从 snapshot 同步财务字段（snapshot 由 adapter 离线维护，不在每日流程重建）
$PY scripts/sync-all-protocols-from-snapshots.py

# 4. 校验（必须 0 errors，否则终止不推送）
if ! $PY scripts/validate.py 2>&1 | tee /tmp/validate-out.txt | grep -q "0 errors"; then
  echo "❌ validate 失败，终止不推送"
  tail -20 /tmp/validate-out.txt
  exit 1
fi

# 5. 提交推送（仅 dev）
git add -A
if git diff --cached --quiet; then
  echo "无数据变更，跳过提交"
else
  git commit -m "chore(daily): 每日数据同步 $(date +%Y-%m-%d)"
  git push origin dev
fi

echo "=== $(date) 每日更新完成 ==="
