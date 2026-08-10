# Mac Mini Agent 接管提示词（交付版 2026-08-11）

> 给另一台设备（Mac Mini，prod-m1-2）上负责**整站运营**的 Agent 的交接说明。
> 由主开发机 Agent（2026-08-11）编写，Boss 确认后生效。

---

## 0. 你的身份与职责边界（先读这里）

你负责 **crypto3d.pro 整个网站的日常运营**（含全部板块：equity 估值、ahr999、mvrv、bmri、btc-dominance、hbm 等指标 + 每日数据更新 + 部署）。

**本次改版边界（重要）**：2026-07-31 至 2026-08-11 期间，主开发机完成了 **equity 板块（原 tev 板块）的全面改版**——从"股东回报率"升级为"DeFi 协议美股化估值体系"（损益表 + P/S/P/E + 财报页 + 27 协议 adapter 体系）。**本次只改了 equity 这一个板块**，其他板块（ahr999/mvrv 等指标）逻辑未变，按你原有流程维护即可。

**本次交接你要做的**：
1. 自检你设备上留存的历史脚本（可能很多旧版），清理/停用与新版冲突的
2. 用仓库最新脚本替换旧脚本（仓库 scripts/ 是权威）
3. 配置 .env（3 个 key）
4. 建立每日定时任务（cron / launchd）跑 daily-run.sh
5. 验证正式站 equity 板块正常

---

## 1. 仓库状态（重要）

- **仓库**：`https://github.com/BitPickles/equity-dashboard`（public）
- **分支**：每日更新只 push **dev**；**main 已包含 equity 改版（558e2e77，2026-08-11 上线）**
- **发版铁律**：不要在 main 上直接开发；main 只接受 merge（由 Boss 批准）
- 部署链路：dev/main → GitHub Actions `Deploy to Cloudflare Pages` → crypto3d.pro

**2026-08-11 已上线 main（558e2e77）包含**：
- `equity/` 板块（index.html / protocol.html + logos）
- `data/protocols/<id>/adapter.py`（27 协议适配器体系）+ `data/snapshots/`
- 全部数据修复（aster PE 17.8x、sky/spark 价格 id、短周期数据、i18n 键清洗）
- 部署脚本 `scripts/daily-run.sh`、`scripts/update-aster.py`、审计脚本 `scripts/audit*.py`

---

## 2. 第一步：自检你设备上的历史脚本（关键！）

你设备上应该存有**多轮迭代的旧脚本**。请逐一检查并处理：

### 🔴 必须停用/删除的旧脚本（会破坏新版数据）

| 旧脚本 | 原因 | 处理 |
|---|---|---|
| `sync-tev-data.js` | 旧 TEV 同步，会**覆盖短周期 yield 为 0**（aster/bgb 等）| 停用，勿运行 |
| `fetch-defillama.js` | 旧数据抓取，与新版 rebuild-daily 冲突 | 停用 |
| `fetch-tev-history.js` | 旧历史生成 | 停用 |
| 任何 `update-aster*.py` 的**旧模拟版**（含假数据）| 旧版是模拟数据 | 用新版 `update-aster.py` 替换 |

### ✅ 保留并确保使用新版（仓库 scripts/ 为准）

每日更新只用这些（`daily-run.sh` 已串好，见第 4 节）：
- `update-prices.py`（价格/市值，CoinGecko + CMC 兜底）
- `update-aster.py`（Aster 链上回购，Moralis）
- `rebuild-daily.py`（daily 数据，DefiLlama + CoinGecko）
- `sync-all-protocols-from-snapshots.py`（snapshot → 主表）
- `validate.py`（校验）
- `build-snapshot.py`（27 adapter → snapshot，离线维护时用）
- `fetch-cmc-supply.py`（流通量，每日）
- `audit5-derivations.py` / `audit6-daily-continuity.py`（审计，可选每日跑）

**自检命令**（在仓库根目录）：
```bash
git status                     # 确认工作区干净
git log --oneline -3           # 确认 HEAD 是最新
ls scripts/ | grep -E "sync-tev|fetch-defillama|fetch-tev-history"  # 应确认停用
```

---

## 3. 第二步：clone / 更新 + 配置 .env

```bash
# 若已有旧 clone：直接更新
cd ~/tev-dashboard && git fetch origin && git checkout dev && git pull origin dev

# 若新设备：全新 clone
git clone https://github.com/BitPickles/equity-dashboard.git ~/tev-dashboard
cd ~/tev-dashboard && git checkout dev

# 依赖（仅 1 个第三方包）
python3 -m pip install requests

# .env（3 个 key，Boss 2026-08-06 确认直接复用现有 key）
cat > .env << 'EOF'
CMC_API_KEY=你的CMCkey
MORALIS_API_KEY=你的Moraliskey
GLM_API_KEY=你的GLMkey（AI 审计用，可选）
EOF
chmod 600 .env
```

---

## 4. 第三步：每日定时任务

**推荐 cron**（也可以 launchd，cron 已够用）：
```bash
crontab -e
# 每天 08:05 执行（避开整点）
5 8 * * * /bin/bash ~/tev-dashboard/scripts/daily-run.sh >> ~/tev-dashboard/logs/daily.log 2>&1
mkdir -p ~/tev-dashboard/logs
```

`daily-run.sh` 内部流程（已串好，无需改动）：
```
update-prices → update-aster → rebuild-daily → sync-all-protocols → validate → push dev
```
- 网络抖动时 update-prices/update-aster 失败**不阻断**主流程
- validate 必须 0 errors 才会 push
- 若 Mac Mini 会睡眠，用「系统设置→电池→计划」定时唤醒

---

## 5. 第四步：上线验证

```bash
# 手动跑一次每日流程
bash scripts/daily-run.sh

# 验证正式站（Cloudflare 部署约 1-2 分钟）
curl -sI https://crypto3d.pro/equity/          # 应 200
curl -sI https://crypto3d.pro/tev/             # 应 200（重定向到 equity）
curl -sI https://crypto3d.pro/                 # 首页

# 验证 equity 数据
# 打开 https://crypto3d.pro/equity/ 检查：
# - 主表 26 协议、周期切换 7D/30D/90D/1Y 有数据
# - BNB 12%+ / aster PE ~17.8x / sky 5.9%
# - 详情页损益表瀑布正常
```

---

## 6. 已知注意事项（踩坑记录）

1. **`.workbuddy/` 目录不入仓库**（.gitignore 已排除）——你本地的 automation 配置属于设备本地
2. **CoinGecko 免费限速 ~10 req/min**：脚本已内置 6s 间隔 + 429 重试，Mac Mini 网络稳定即可
3. **sky 的 CoinGecko id 是 `sky`**（不是 maker）；**spark 是 `spark-2`**（不是 spark）——已修复在脚本里，勿改回
4. **Aster 6-17 新机制**：官方公布的回购钱包（0xa0ed...）链上执行量仅 25 ASTER，实际执行地址待官方披露——`update-aster.py` 已采集 S4 钱包（0x573c...），365d 用链上年化（PE 17.8x）。**若官方披露新地址，在 `update-aster.py` 的 WALLETS 里加即可**
5. **`data/aster-onchain.json` 是 Aster 链上数据权威源**（update-aster.py 维护），勿手改
6. **git 偶发 `.git/refs` 损坏**（本机 Windows 遇过）：Mac Mini（macOS）一般没有此问题；若遇到 `not a git repository`，检查 `.git/refs/heads` 是否存在
7. **不要 push 到 main**：每日更新只 push dev；main 由 Boss 批准 merge（参考 2026-08-11 上线流程）

---

## 7. 审计（可选，建议每周）

```bash
python3 scripts/audit5-derivations.py   # 派生关系（P/S、市值、yield 公式）
python3 scripts/audit6-daily-continuity.py  # daily 时间序列断档
```

---

## 附：本次改版核心成果（2026-07-31 ~ 08-11）

| 项 | 说明 |
|---|---|
| 板块路径 | `/tev/` → `/equity/`（旧路径自动重定向）|
| 术语 | TEV 全面废弃 → 收入/毛利/净利/股东回报/留存（美股五段式）|
| 数据体系 | 27 协议 adapter.py → snapshot → all-protocols（判定书口径）|
| 主表 | 收入/毛利/净利/净利率/P/S/P/E/股息率/回购率/股东回报率/派息率 + 周期切换 |
| 详情页 | 估值概览 + 损益表瀑布 + 历史图 + 流通量曲线 + 计算口径 |
| 关键修复 | aster PE 69→17.8x、sky/spark 价格 id、短周期数据、MORALIS key 环境变量化 |
