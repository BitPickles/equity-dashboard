#!/bin/bash
# 每日数据更新（Mac Mini cron 用）
# 每日主链：同步 main → update-prices → update-aster → rebuild-daily → build-snapshot → sync → validate → push main
# 用法: bash scripts/daily-run.sh
set -e
cd "$(dirname "$0")/.."
PY=python3

echo "=== $(date) 每日更新开始 ==="

# 以远端 main 为唯一发布基线；拉取失败或有非快进冲突时安全退出，避免覆盖他人上线。
if [ "$(git branch --show-current)" != "main" ]; then
  echo "❌ daily-run 必须在 main 分支执行"
  exit 1
fi
git fetch origin main
git merge --ff-only origin/main

# 1. 更新价格/市值（CoinGecko，约1分钟；网络抖动时部分协议失败 → 不阻断主流程，validate 会兜底）
$PY scripts/update-prices.py || echo "⚠️ update-prices 部分失败（网络），继续主流程（下次同步补齐）"

# 1.5 Aster 链上回购采集（Moralis，2026-08-06 接入；失败不阻断主流程）
$PY scripts/update-aster.py || echo "⚠️ update-aster 失败（网络/key），继续主流程"

# 2. 刷新 daily 数据（防僵尸）
$PY scripts/rebuild-daily.py

# 3. 刷新 27 个财务 snapshot，避免 validate 因 snapshot 过期拒绝发布。
#    适配器从已更新的 daily / 协议配置生成派生估值与历史序列。
$PY scripts/build-snapshot.py

# 4. 从刚生成的 snapshot 同步财务字段到主表
$PY scripts/sync-all-protocols-from-snapshots.py

# 5. 校验（必须 0 errors，否则终止不推送）
if ! $PY scripts/validate.py 2>&1 | tee /tmp/validate-out.txt | grep -q "0 errors"; then
  echo "❌ validate 失败，终止不推送"
  tail -20 /tmp/validate-out.txt
  exit 1
fi

# 6. 提交推送 main（线上站点每日自动更新）
git add -A
if git diff --cached --quiet; then
  echo "无数据变更，跳过提交"
else
  git commit -m "chore(daily): 每日数据同步 $(date +%Y-%m-%d)"
  git push origin main
fi

echo "=== $(date) 每日更新完成 ==="
