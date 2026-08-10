# Mac Mini 每日数据更新部署文档

> 用途：替代本机（Windows/WorkBuddy automation）的每日数据更新任务，
> 在 Mac Mini 上定时自动跑：价格同步 → 数据重建 → validate → git push dev。
> 创建：2026-08-06

## 1. 部署前置（一次性）

### 1.1 环境
- macOS（Apple Silicon 或 Intel 均可），需联网
- Python 3.10+（建议 Homebrew 安装：`brew install python@3.11`）
- git（`xcode-select --install` 自带）

### 1.2 克隆仓库
```bash
cd ~
git clone https://github.com/BitPickles/equity-dashboard.git tev-dashboard
cd tev-dashboard
git checkout dev          # 每日更新只推 dev，不要动 main
```

### 1.3 依赖安装（仅 1 个第三方包）
```bash
python3 -m pip install requests   # 仅 fetch-aster-onchain.py 需要，其余全标准库
```

### 1.4 配置环境变量（.env）
```bash
cd ~/tev-dashboard
cat > .env << 'EOF'
CMC_API_KEY=你的CMCkey
MORALIS_API_KEY=你的Moraliskey（Boss 2026-08-06 确认：只读查询 key，暴露风险低，直接复用现有 key 即可）
GLM_API_KEY=你的GLMkey（用于AI审计，可选）
EOF
chmod 600 .env   # 权限收紧，防他人读取
```
> ⚠️ .env 已在 .gitignore 中，不会被提交。

### 1.5 git push 权限
Mac Mini 需要能 push dev 分支：
```bash
gh auth login   # 或手动配置 SSH key（https://github.com/settings/keys）
git config --global user.name "BitPickles"
git config --global user.email "BitPickles@users.noreply.github.com"
```

## 2. 每日更新脚本

创建 `~/tev-dashboard/scripts/daily-run.sh`：

```bash
#!/bin/bash
# 每日数据更新（Mac Mini cron）
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

# 4. 校验（必须 0 errors）
if ! $PY scripts/validate.py | grep -q "0 errors"; then
  echo "❌ validate 失败，终止不推送"
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
```

```bash
chmod +x ~/tev-dashboard/scripts/daily-run.sh
```

## 3. 定时任务（cron）

```bash
crontab -e
# 添加一行（每天 08:05 执行，避开整点）
5 8 * * * /bin/bash ~/tev-dashboard/scripts/daily-run.sh >> ~/tev-dashboard/logs/daily.log 2>&1
```

```bash
mkdir -p ~/tev-dashboard/logs
```

> macOS 定时也可用 launchd（更规范），但 cron 已足够。若 Mac Mini 会睡眠，
> 建议在「系统设置 → 电池 → 计划」开启定时唤醒，或用 `pmset repeat wakeorpoweron`。

## 4. 验证

```bash
# 手动跑一次确认无报错
bash ~/tev-dashboard/scripts/daily-run.sh

# 看日志
tail -20 ~/tev-dashboard/logs/daily.log

# 确认推上去了
git log --oneline -3
```

## 5. 与本机 automation 的关系

- **迁移后**：本机 WorkBuddy 的每日 automation（早 8:00）应 **暂停**，避免与 Mac Mini 双跑冲突（两个进程同时 update-prices 可能互相覆盖）
- 迁移前：先在 Mac Mini 手动跑通 1 次，确认无报错、git push 成功，再停本机 automation

## 6. 注意事项

1. **update-prices.py 的 CoinGecko 免费额度**：约 10 req/min，脚本已内置 6s 间隔，正常
2. **网络**：Mac Mini 需能访问 CoinGecko / DefiLlama / GitHub，国内网络可能需要代理
3. **首次同步**：git clone 后仓库含全部历史数据（~50MB），无需额外初始化
4. **失败处理**：validate 失败不会推送（脚本已加保护），日志见 daily.log
5. **GLM key**：AI 审计功能（scripts/ai-audit/）尚未接入 daily-run，如需可后续加
