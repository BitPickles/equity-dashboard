# Crypto3D TEV Dashboard - 开发维护规范

## 部署流程（铁律）

1. **所有开发在 `dev` 分支完成**
2. Push `dev` 后在测试站验证：https://bitpickles.github.io/tev-dashboard
3. **向 Boss 展示测试站效果，等待确认**
4. Boss 确认后才 merge `dev` → `main` 并 push `main`
5. Push `main` 自动触发 GitHub Actions → Cloudflare Pages 部署到正式站
6. **严禁未经验证直接 push main**
7. 唯一例外：安全修复类紧急变更可直接推 main，但必须说明原因

## TEV 数据口径

数据源优先级：**链上 > 官方治理 > 估算 > DefiLlama**

- **每个协议的 TEV 机制独立，不能套通用公式**。BNB / HYPE / Aster / Uniswap 等需要专属分支。详见 `docs/skill/tev-data-layer.md`
- **DefiLlama 口径需逐个协议验证**：`dailyRevenue` 是否等于归属 token 持有人部分，部分协议（如 Hyperliquid）上 `dailyRevenue == dailyHoldersRevenue`，其他协议未必
- **TEV Yield 365d 是主口径**；短周期（7/30/90d）根据机制特性选择算法：
  - 滚动窗口年化（通用 fee 分润协议）
  - 近 4 季度稳定态（BNB 的 Auto-Burn 季度事件）
  - 时间序列窗口求和（BNB 的 BEP-95 日频波动）
  - 历史 USD 累加 vs 当前价重估（BNB 的短周期 vs 365d 双口径）
- **TEV Ratio 变更**必须有治理提案或官方文档支撑
  - `null` = 协议无 fee 分润机制（如 BNB），前端渲染 `—`
  - `0` = 有 fee 但 0% 归持有人（如 Lido / Compound）
  - 数字 = 明确分润比例（如 Pendle 0.8、Curve 0.5）
- **前端两个数据源必须同步**：主表 `/equity/index.html` 读 `data/all-protocols.json`，详情页 `/equity/protocol.html` 读 `data/protocols/<id>/config.json`，改动要两边核对
- **显示精度**：默认 2 位小数；协议 TEV 某部分贡献 <0.1%（如 BNB 的 BEP-95 ~0.02%）时，在 config 里标 `display_precision: 3`
- **核心规范（schema / 新协议工作流 / 已踩坑清单）**见 `docs/skill/tev-data-layer.md`，公式不可擅自更改

## 分支纪律

- `dev`：开发分支，GitHub Pages 测试站
- `main`：正式发布分支，Cloudflare Pages 正式站
- 数据自动更新：commit 到 `dev` → merge `main` → 自动部署

## 定时任务

- 数据更新：LaunchAgent `com.crypto3d.data-updater`（9:03/21:03）
- 治理监控：LaunchAgent `com.crypto3d.governance-monitor`（9:05/21:05）
- 日志目录：`~/scheduled-tasks/logs/` 和 `~/crypto3d-updater/logs/`
