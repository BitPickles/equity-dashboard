#!/bin/bash
# 每日数据更新（Mac Mini cron 用）
# 每日主链：同步 main → update-prices → update-aster → rebuild-daily → build-snapshot → sync → 历史 → 指标 → validate → push main
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

# 1.5 Aster 链上回购采集（2026-08-06 接入；失败不阻断主流程）。
#     ⚠️ 2026-10-07 审计教训：MORALIS_API_KEY 为空/失效时本步骤连续静默失败 3 个月
#     无人发现（aster-onchain.json 停在 07-04）。现在：
#     - 失败时显式 ❌ 告警（不再静默 || echo）
#     - ai-self-check freshness 任务把 aster-onchain >30 天无新记录记为告警
#     - 链上事实（2026-10-07 三源核实）：6-17 新机制钱包转入≈0、余额 30 ASTER，
#       即新机制尚未显化执行量，采集无数据是正常现象；但 Moralis key 仍需配置
#       以便机制激活后第一时间捕获。
if $PY scripts/update-aster.py; then
  echo "✓ aster: 采集完成"
else
  echo "❌ update-aster 失败（MORALIS_API_KEY 失效/为空或网络）—— 请检查 Mac Mini .env"
fi

# 2. 刷新 daily 数据（防僵尸）
$PY scripts/rebuild-daily.py

# 3. 刷新 27 个财务 snapshot，避免 validate 因 snapshot 过期拒绝发布。
#    适配器从已更新的 daily / 协议配置生成派生估值与历史序列。
$PY scripts/build-snapshot.py

# 4. 从刚生成的 snapshot 同步财务字段到主表
$PY scripts/sync-all-protocols-from-snapshots.py

# 5. 重建历史图：TTM 折线与单日净收益柱必须来自不同字段。
#    网络源短暂失败时保留旧历史；前端会显示缺失而非把 TTM 冒充日值。
$PY scripts/fetch-protocol-history.py --all || echo "⚠️ 通用日频历史刷新失败，保留上一版历史"
$PY scripts/fetch-bnb-history.py || echo "⚠️ BNB 日频历史刷新失败，保留上一版历史"
$PY scripts/refresh-unavailable-history.py

# 5.6 指标板块（shared/btc-price、shared/fred-macro、ahr999、marketcap、btc-dominance、mvrv）。
#     数据源：CoinMarketCap（需 .env 的 CMC_API_KEY）+ FRED CSV + bitcoin-data.com。
#     失败不阻断主流程：前端会继续显示上一版指标，不会出现空洞。
#     ⚠️ 2026-10-07 审计教训：脚本内置缺日检测 + freshness 汇总 + 失败非零退出；
#     此处若见 ⚠️ 指标新鲜度问题 / ❌ 说明静默冻结复发，需人工排查（CMC key / 网络）。
$PY scripts/fetch-indicators.py || echo "❌ fetch-indicators 非零退出（见上方 freshness 汇总），保留上一版指标数据 —— 连续多日出现须排查"

# 5.7 每日 AI 审计（PRD 5.5.3，2026-10-07 落地）。
#     freshness/regression 纯脚本必跑；LLM 任务（机制变更/合理性/交叉验证）需 GLM_API_KEY，
#     未配置时自动 --no-llm（结果落 data/ai-audit/<date>.json，alert 级打日志）。
if [ -n "$GLM_API_KEY" ] || grep -q "^GLM_API_KEY=..*" .env 2>/dev/null; then
  $PY scripts/ai-self-check.py || echo "❌ AI 审计失败（不阻断数据管道，但连续失败须排查 GLM key）"
else
  $PY scripts/ai-self-check.py --no-llm || echo "❌ AI 审计（no-llm）失败"
fi

# 6. 校验（必须 0 errors，否则终止不推送）
if ! $PY scripts/validate.py 2>&1 | tee /tmp/validate-out.txt | grep -q "0 errors"; then
  echo "❌ validate 失败，终止不推送"
  tail -20 /tmp/validate-out.txt
  exit 1
fi

# 7. 仅提交每日数据产物到 main（线上站点每日自动更新）。
# 不使用 git add -A，避免把运行日志或人工中的非数据改动误发布。
# indicators/data 必须一并提交，否则指标板块（ahr999/mvrv/btc-dominance）会像
# 2026-08-10 → 10-02 那样长期冻结在旧日期。
git add -A -- data indicators/data
if git diff --cached --quiet; then
  echo "无数据变更，跳过提交"
else
  git commit -m "chore(daily): 每日数据同步 $(date +%Y-%m-%d)"
  git push origin main
fi

echo "=== $(date) 每日更新完成 ==="
