# 指标 / 模块下线清单（Indicator Retirement Checklist）

当一个指标口径不合格、被取代、或 Boss 决定不再提供时，按本清单**彻底**下线，避免残留造成
「死链 404 / 僵尸数据 / 页面文案与功能不符」。

> 首次适用：**BMRI**（2026-10-03 下线，口径不合格）。commit `d7d1d101`（dev）。

## 0. 前置确认（问 Boss）
- 首页整块（含仪表盘/走势图/分桶）是否一起删？→ 默认删
- 页面 / 数据文件 / 脚本是否彻底删除？→ 默认彻底删
- 原始数据源（如 FRED）是否保留？→ 若别处复用则保留文件、仅删指标逻辑

## 1. 页面与数据（删除）
- [ ] 指标页面目录：`<indicator>/index.html`（`git rm -r`）
- [ ] 数据文件：`indicators/data/<indicator>.json`（及其 `.bak-*` 备份）
- [ ] 专用脚本：`scripts/*-<indicator>*.py`（recalc / update 等）
- [ ] 指标文档：`docs/skill/indicators/<indicator>.md`

## 2. 首页 `index.html`
- [ ] 删除指标所在 `<section>` 整块 HTML
- [ ] 删除该 section 专属 CSS（`.xxx-section/.xxx-gradient/.xxx-content/...` 及 `@media`）
- [ ] 删除顶部导航 `<a href="#xxx">`（**易漏**：删了 section 却留了锚点 → 死链）
- [ ] 删除旧共用选择器里的孤儿类（如 `.bento-card,.gov-card,.xxx-viz{...}` 去掉 `.xxx-viz`）
- [ ] 删除对应数据同步 JS（IIFE / chart 初始化）
- [ ] meta description / og:description / twitter:description / JSON-LD 中的指标名（**易漏**）

## 3. 站点其余出口
- [ ] `homepage/index.html` 卡片 `<a href="../xxx/">`
- [ ] `daily-report/index.html` 卡片 + 相关函数（含函数签名/调用/Promise.all 项数）
- [ ] 各页导航：`btc-dominance`、`ahr999`、`mvrv` 等子页的 `<a href="../xxx/">`
- [ ] 文案：`about.html`、`terms.html`、`disclaimer.html`
- [ ] `sitemap.xml` 条目
- [ ] `_redirects`：`/xxx`、`/xxx/*`、`/indicators/xxx.html` → `301 /`（Cloudflare 生效；GitHub Pages 不认，测试站会 404，属正常）
- [ ] `indicators/css/common.css` 中指标专属类（保留跨页共用类）

## 4. 脚本与生成器
- [ ] 数据抓取脚本：移除指标逻辑；若原始数据保留则改注释说明
- [ ] `scripts/daily-run.sh`：去掉该指标的步骤 / 警告块
- [ ] `scripts/add-i18n.py`：移除导航词条与指标专属词条（**通用词条要保留**——先 grep 别处是否复用）
- [ ] 日报生成器：`daily-poster/template.html`（卡片 HTML/CSS）、`daily-poster/gen-daily.py`（采集/填充/子因子/历史段/prompt/视角轮换项）
- [ ] 重置 `daily-poster/comment.json` 等「最近一次输出」样例，避免残留旧指标文案

## 5. 文档
- [ ] `README.md`、`TOOLS.md`、`VERSIONING.md`（下线记录）
- [ ] `docs/skill/*.md`（架构/组件/数据规范/页面模板/推文结构）
- [ ] `docs/mac-mini-handoff-prompt.md`

## 6. 残留扫描 + 收尾
- [ ] `grep -rin "<indicator>" . --exclude-dir=.git --exclude-dir=tmp --exclude-dir=node_modules`
  - 允许保留：`memory/`（历史）、`archive/`（归档）、`daily-poster/output/*`（历史海报）、以及「已下线」说明文字
- [ ] 根目录 legacy `all-protocols.json`（由 `sync-protocols.js` 生成，聚合所有 `data/*.json`）
      若含 `<indicator>` 键，手动删除该键（文件 8MB 且被 git 跟踪，勿整体重排）
- [ ] `python scripts/validate.py` → 0 errors / 0 warnings
- [ ] 校验无孤儿引用：`grep -rn "id=\"xxx\"\|\.xxx-\|<removed-class>" *.html */index.html`
- [ ] 提交 dev → push → GitHub Actions `Deploy to GitHub Pages` success
- [ ] 线上验证（测试站 `https://bitpickles.github.io/equity-dashboard/`，带 `?cb=<ts>` 破缓存）：
      - 首页 200 且无指标残留字样；旧路径 404（GH Pages）
      - 子页导航无旧入口

## 陷阱备忘
- 「删 section 忘删导航锚点」「meta 描述漏改」是最常见的两处遗漏。
- i18n 词条看似专属，实则可能被 hbm/equity/membership 复用 —— 删前必 grep。
- `daily-poster/output/*.html` 是历史归档，**不要**动。
- 根 `all-protocols.json` 与 `data/all-protocols.json` 是两个文件，前者是 legacy 僵尸。
