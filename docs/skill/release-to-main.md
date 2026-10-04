# 发布到主站手册（dev → main）

生产站 `crypto3d.pro` 由 **main** 分支经 Cloudflare Pages 部署；测试站由 **dev** 经 GitHub Pages 部署。
代码/页面改动**只在 dev 开发**，Boss 批准后按本手册发布到 main。

## 关键前提：dev 与 main 是「并行分支」
- 每日自动化（`daily-run.sh`）**只推 main**（`data/` + `indicators/data/`），因此 **dev 会持续落后 main**。
- 所以**不能**直接 `git merge dev` 到 main（会把 dev 缺失的每日同步一起卷进来、且极易在数据文件上冲突）。
- 正确做法：**cherry-pick** dev 上的功能提交到 main。

## 发布步骤

### 1. 摸清分叉
```bash
git fetch origin
git log --oneline origin/main..dev      # dev 独有（要发布的）
git log --oneline dev..origin/main      # main 独有（每日同步，勿动）
git merge-base dev origin/main | xargs git log --oneline -1
```
确认 dev 独有提交里**哪些是功能、哪些是重复**（例：hbm 若已 cherry-pick 过就跳过）。

### 2. 切 main 对齐远端
```bash
git checkout main && git reset --hard origin/main
```

### 3. cherry-pick（按时间顺序）
```bash
git cherry-pick <sha1> <sha2> ...
```
- 逐个确认输出无 conflict。
- 若冲突：多为「双方都改了同一数据文件」。**不要**手动乱合数据 —— `git cherry-pick --abort`，改为只 cherry-pick 与数据无重叠的提交，或先让自动化刷新数据后再试。

### 4. 发布前验证（main 工作树）
```bash
python scripts/validate.py            # 期望 0 errors / 0 warnings
# 抽查关键数据日期 / 删文件是否真的没了
```
> ⚠️ 发布前务必确认「**要修的问题在 main 上确实是坏的**」。例：2026-10-04 发现 `indicators/data/` 在 main 上停 08-10、`btc-price` 停 02-12 —— 说明 10-02 的修复**从没进过生产**，差点漏发。

### 5. 推 main
```bash
git push origin main
```

### 6. 等部署 + 生产验证
```bash
gh run list --limit 3                                  # 找 Deploy to Cloudflare Pages
gh run watch <run-id> --exit-status
```
**生产验证必须带缓存穿透**（Cloudflare `Cache-Control: max-age=300`）：
```bash
TS=$(date +%s)
curl -s "https://crypto3d.pro/?cb=$TS" | grep -o "旧字样"      # 应为空
curl -s -o /dev/null -w "%{http_code} → %{redirect_url}\n" https://crypto3d.pro/旧路径/
curl -s "https://crypto3d.pro/indicators/data/ahr999.json?cb=$TS"   # 看 updated_at
```
> `/bmri`、`/bmri/*` 这类 `_redirects` 301 **只在 Cloudflare 生效**；GitHub Pages（测试站）不认，会 404 —— 属正常。

### 7. 收尾：把 main 合回 dev，避免 dev 持续落后
```bash
git checkout dev && git merge origin/main --no-edit && git push origin dev
git diff --stat dev origin/main        # 期望为空（树内容一致）
```
- cherry-pick 后两边提交 hash 不同但**内容应完全一致**；`git diff --stat` 为空即验证通过。
- 合并会把 main 的每日同步补进 dev，且 cherry-pick 的内容已存在 → 不产生重复改动。

## 易踩坑
| 坑 | 现象 | 对策 |
|---|---|---|
| 直接 merge dev→main | 数据文件大冲突 | 用 cherry-pick |
| 漏发「只在 dev 的修复」 | 生产长期不生效 | 先列 `origin/main..dev` 全部提交，逐个判断 |
| CDN 缓存 | 推完 curl 到旧数据 | 加 `?cb=<ts>` 或等 5 分钟 |
| （本机）git 写操作 | `.git/refs` 偶发消失 / index 损坏 | 提交后 `ls .git/refs/heads/` 验证 |
| 自动化只推 main | dev 天天落后 | 每次发布后执行第 7 步 merge |
