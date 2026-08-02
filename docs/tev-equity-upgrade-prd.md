# DeFi 协议指标美股化升级 PRD（股东回报 2.0）

> **项目**：Crypto3D 数据站（crypto3d.pro）
> **文档状态**：**v2.3 定稿**（新增 4.6 UI 交互规范——Boss 2026-08-03 UI 优化需求：Caveats 折叠/损益表瀑布式/图表拖动缩放/坐标简写/流通量历史曲线）
> **创建日期**：2026-08-02
> **作者**：WorkBuddy（协助 Boss 3D 整理）
> **相关文档**：`docs/skill/tev-data-layer.md`（TEV 数据层规范，本文的权威基础）；`docs/protocol-revenue-recognition.md`（协议口径判定书总表）

---

## 术语约定（Boss 2026-08-02 定稿，全站统一）

> ⛔ **本 PRD 及后续实现废弃「TEV（Token Economic Value）」概念**，统一使用美股损益表语言：

| 废弃术语 | 新术语（损益表语言） | 含义 |
|---|---|---|
| TEV（Token Economic Value） | **股东回报**（Shareholder Returns） | 流向持币人的价值：股息 + 回购 + 销毁 |
| TEV Yield | **股东回报率**（Shareholder Yield） | 股东回报 ÷ 市值 |
| TEV 机制 | 股东回报机制 / 价值分配机制 | 每项机制的损益表归类 |
| （新概念） | **毛利 Gross Profit** | 收入 − 直接成本（LP 分润等） |
| （新概念） | **净利 Net Income** | 毛利 − 运营成本/激励（= 协议可分配盈余） |
| （新概念） | **留存 Retained** | 净利中未分配给持币人、留在国库的部分 |

**损益表五段式**（每个协议财报页的标准呈现）：

```
收入 Revenue
− 直接成本（LP 分润等）＝ 毛利 Gross Profit
− 运营成本 / 激励        ＝ 净利 Net Income
净利分配：
  ├─ 股东回报（股息 + 回购 + 销毁）→ 流向持币人
  └─ 留存（国库 / Surplus Buffer 等）
```

> 例（Sky）：净利高但大量留存国库（Surplus Buffer ≤ 5000 万 DAI）；超额部分 SBE 回购做市（LP 锁定）；Elixir 真燃烧才计入股东回报。损益表必须把「留存 vs 分配」讲清楚。

**增发成本铁律（Boss 2026-08-02 确认，配比原则 Matching Principle）**：
> **增发是否"直接换取当期协议收入"是判定标准：**
> - ✅ **有对价换收入**（DEX 的 LP 挖矿 / gauge / farm——增发就是用来买手续费/流动性的工具）→ **增发作为成本从净利扣除**（美股 SBC 类比）。例：Curve 年增发 ~$2600 万 → 扣后**净利为负**；Pancake 增发 $1170 万 < 回购 $1800 万 → 扣后**净利为正**。
> - ❌ **无对价 / 非换当期收入**（换取 TVL 锁定、治理参与、安全，或无明显对价）→ **不算成本**，但详情页**必须展示年增发率作为「稀释注记」**（美股财报披露 SBC 同款逻辑，投资者自行判断）。
>
> 无论算不算成本，**增发率必须在协议详情页展示**。计算逻辑（收入 − LP 分润 = 毛利；毛利 − 增发成本 = 净利）与详细数据（增发量、通胀率、分润比例）必须写清楚，不能只给结果数字。

> 现有系统字段（`tev_yield_percent`、`tevRatio`、`TEV_COLORS` 等）为技术遗留命名，实现时统一迁移为股东回报体系，**前端展示用新术语**。

**字段名迁移表（数据模型层，Boss 2026-08-02 确认全面替换，不留旧名）**：

| 旧字段（TEV 体系） | 新字段（损益表体系） | 含义 |
|---|---|---|
| `tevRatio` / `tevRatio_7d/30d/90d/365d` | `payout_ratio` / `payout_ratio_7d/30d/90d/365d` | **派息率** = 股东回报 ÷ 收入 |
| `tev_yield_percent` | `shareholder_yield_percent` | **股东回报率** = 股东回报 ÷ 市值 |
| `tev_yield_7d_ann/30d/90d` | `shareholder_yield_7d_ann/30d/90d` | 周期股东回报率 |
| `tev_usd_365d` | `shareholder_returns_usd_365d` | 股东回报金额（股息+回购+销毁） |
| `tev_mechanisms` | `return_mechanisms` | 股东回报机制 |
| `tev_summary` | `return_summary` | 回报摘要（fee_switch/buybacks/dividends/burns） |
| `tevStatus` | `return_status` | 回报状态（active/partial/none） |
| `tev_data` | `snapshot_data` | 财务快照数据 |
| `tev-records.json` | `shareholder-records.json` | 股东回报历史记录文件 |
| `TEV_COLORS`（前端 JS） | `RETURN_COLORS` | 机制颜色表 |
| `tev_yield_vecrv_only_percent` | `shareholder_yield_vecrv_only_percent` | 特殊口径（Curve） |
| `earning_yield_percent` | `earnings_yield_percent` | 盈利收益率（市值 ÷ 收入 的倒数） |

> **EPS（每股收益）** = 股东回报 ÷ 流通代币量（新增，P2）。三者关系：**派息率 × 盈利收益率 = 股东回报率**（payout × earnings yield = shareholder yield）。

---

## 一、背景与问题

### 1.1 现状

Crypto3D 的 /tev/ 板块已经实现了 TEV（Token Economic Value）指标体系：

- **主表**（`tev/index.html`）：26 个协议，列含 市销率 P/S、市盈率 P/E、股息率、回购率、股东回报率、派息率，支持 7D/30D/90D/1Y 周期切换
- **详情页**（`tev/protocol.html`）：估值概览 + 股东回报历史图表 + 销毁/回购记录 + 深度分析（机制/计算/分析师备注）
- **数据层**：`docs/skill/tev-data-layer.md` 定义了完整方法论——每个协议机制独立、数据源优先级「链上 > 官方治理 > 估算 > DefiLlama」、10 条已踩坑清单

### 1.2 问题

TEV 目前的框架虽已具备美股化雏形，但离"像分析一家上市公司一样分析 DeFi 协议"还有明显差距：

1. **基本面维度缺失**：只有"股东回报/估值倍数"，没有美股财报的核心骨架——收入、利润、费用、利润率、收入增速（YoY/QoQ）。投资者无法回答"这个协议赚不赚钱、增长快不快"。
2. **估值倍数不完整**：有 P/S、P/E，缺 P/B、EV/Revenue 等常用倍数；P/E 用的是"股东回报"而非"净利润"，口径与美股不完全一致。
3. **协议覆盖深度不齐**：只有 BNB、Hyperliquid、Aave、Sky、Uniswap 做了深度链上处理，其余协议仍依赖通用公式或 DefiLlama 兜底口径，数据可信度参差。
4. **无"财报"呈现**：数据分散在 config.json 的多个字段里，没有一个统一的、按"损益表 / 股东回报 / 估值"组织的呈现方式。

### 1.3 之前尝试的教训（Boss 反馈）

> **核心卡点：数据口径难搞定。** 每个协议的价值捕获机制、数据源、计算口径都不一样，机械套用通用公式会严重失真；而逐个协议深挖数据源与口径验证，工作量大且容易中途失联。

因此本 PRD 将**数据层设计放在最高优先级**：先定义统一的数据模型与"协议适配器"模式，跑通一个最复杂的标杆协议（BNB），验证模式后再批量复制。

---

## 二、目标与非目标

### 2.1 目标

把 DeFi 协议当作上市公司来分析，提供一套完整、可溯源、口径一致的美股式财务与估值指标体系：

1. **损益表体系（核心）**：收入 → 毛利（扣 LP/直接成本）→ 净利（扣增发成本/运营成本）→ 股东回报（股息+回购+销毁）→ 留存（国库），全链路可展开计算过程
2. **基本面指标体系**：收入、毛利、净利、利润率（毛利率/净利率）、收入增速（YoY/QoQ）、**增发成本**（有对价换收入才计，无对价作稀释注记）
3. **丰富估值倍数**：P/E、P/S、P/B、EV/Revenue、派息率（Payout Ratio）
4. **股东回报体系**（继承并强化现有 TEV）：股息率、回购率、销毁率、股东总回报（Shareholder Yield）
5. **协议财报页**：每个协议一张"上市公司式财报页"，按 公司概览 / 损益表 / 股东回报 / 估值 / 历史图表 / 计算口径 六区块组织
6. **美股对标**：**概念级对标**（不做实时美股数据对比），在方法论与文档中明确每个指标与美股同名的映射口径，并可在页面上以说明文字/注释形式呈现
7. **自动化运维**：数据源明确到每个协议（链上日频脚本 / 官方公告 AI 抓取），服务器无人值守运行，AI（GLM）每日自检口径与数据质量

### 2.2 非目标

- ❌ 不做实时美股行情对比（如 COIN、HOOD 的实时股价/估值同屏对比）
- ❌ 不改变现有 TEV 的核心公式与方法论（`tev-data-layer.md` 仍为权威；术语按头部「术语约定」迁移）
- ❌ 不在本阶段覆盖 27 个协议的全部深度处理（分批进行，见里程碑）
- ❌ 不引入后端服务——保持纯静态站 + 每日构建脚本的架构

### 2.3 成功标准

- [ ] BNB 作为标杆协议，完成"财报页"全流程（数据 → 验证 → 呈现），Boss 在测试站验收通过
- [ ] 主表新增基本面/估值列，且与现有股东回报列口径自洽（可交叉验证）
- [ ] 每个接入协议的指标都可点击溯源到原始数据（链上/官方/API）
- [ ] 数据更新管道（每日自动）在新增指标后仍稳定运行，无僵尸字段

### 2.4 发版纪律（铁律，Boss 2026-08-02 再次强调）

> ⛔ **本项目的所有改造只允许在测试站上进行，严禁直接改动/推送主站。**

1. **一切开发、提交、推送只针对 `dev` 分支**，测试站在 https://bitpickles.github.io/tev-dashboard
2. **`main` 分支与正式站 crypto3d.pro 是禁区**：未经 Boss 明确批准，任何 commit 不得进入 `main`，禁止 `git push origin main`
3. 每一阶段完成 → 推 `dev` → 测试站验证 → **Boss 在测试站确认后**，才由 Boss 决定是否 merge `main`
4. 紧急修复也不例外：先推 `dev` 验证，再请示（对齐仓库 CLAUDE.md 部署铁律与 MEMORY.md「主站发版必须经 Boss 批准」）
5. 违反此纪律 = 项目事故，无论动机如何

---

## 三、核心映射：美股 ↔ DeFi 指标体系

> 设计原则：**不另造新概念**，直接套用美股成熟口径；每个指标必须能回答一个投资者会问的问题。

### 3.1 指标映射总表

| 美股概念 | 美股定义 | DeFi 对应 | 数据源 | 现状 |
|---|---|---|---|---|
| **Revenue 营收** | 销售收入 | **平台币：赋能总额（打新 + 质押 + 销毁）；应用：协议费收入** | 平台币：aBNB APY + 链上销毁；应用：DefiLlama `dailyFees` | 🟡 口径按 3.3 判定框架收齐 |
| **Gross Profit 毛利** | 营收 − 直接成本 | 收入 − LP 分润等直接成本 | DefiLlama `dailyRevenue`（协议归属） | 🟡 现有（Earning Yield 分子） |
| **Token Emission Cost 增发成本** | SBC 股权激励费用 | **有对价换收入的增发（LP 挖矿/gauge/farm）**；无对价 → 稀释注记 | 链上增发量 × 均价 | 🔴 新增（铁律见头部） |
| **Net Income 净利润** | 税后利润 | 毛利 − 增发成本 − 运营成本（**可为负**，如 Curve） | 需逐协议定义 | 🔴 新增 |
| **Shareholder Returns 股东回报** | 股息 + 回购 | 流向持币人的价值：股息 + 回购 + 销毁（原 TEV） | 各协议机制 | 🟢 现有 |
| **EPS 每股收益** | 净利润 ÷ 股本 | 股东回报 ÷ 流通代币量 | 计算 | 🔴 新增 |
| **Dividend Yield 股息率** | 股息 ÷ 股价 | 直接分润（现金/稳定币/质押奖励）÷ 市值 | 各协议 | 🟢 现有 |
| **Buyback Yield 回购率** | 回购 ÷ 市值 | 回购并销毁 ÷ 市值 | 各协议 | 🟢 现有 |
| **Burn Yield 销毁率** | —（类比注销库存股） | 纯销毁（无回购路径）÷ 市值 | 链上 | 🟡 部分 |
| **Shareholder Yield 股东总回报** | 股息率 + 回购率 | 股息 + 回购 + 销毁 ÷ 市值（原 TEV Yield） | 计算 | 🟢 现有 |
| **Payout Ratio 派息率** | 股息 ÷ 净利润 | 股东回报 ÷ 净利 | 计算 | 🟢 现有（tevRatio） |
| **P/E 市盈率** | 市值 ÷ 净利润 | 市值 ÷ 股东回报（当前）；市值 ÷ Net Income（二期） | 计算 | 🟡 现有 |
| **P/S 市销率** | 市值 ÷ 营收 | 市值 ÷ Revenue | 计算 | 🟢 现有 |
| **P/B 市净率** | 市值 ÷ 净资产 | 市值 ÷ 协议 Treasury（金库资产）；**Treasury 数据不可得 → `—`**（P2 实现） | 新增 | 🔴 新增 |
| **EV/Revenue 企业价值倍数** | EV ÷ 营收 | （市值 − 协议 Treasury）÷ Revenue（简化版 EV） | 计算 | 🔴 新增 |
| **Revenue Growth 收入增速** | YoY/QoQ | 收入同比/环比（需 12 个月以上历史序列） | DefiLlama 历史 / 链上 | 🔴 新增 |
| **Gross Margin 毛利率** | 毛利 ÷ 营收 | 毛利 ÷ Revenue | 计算 | 🔴 新增 |
| **Net Margin 净利率** | 净利润 ÷ 营收 | Net Income ÷ Revenue（**可为负**） | 计算 | 🔴 新增 |

**图例**：🟢 已有且稳定 ｜ 🟡 已有但不完整/口径待统一 ｜ 🔴 本次新增

### 3.2 指标分层（L1–L5）

```
L1 市场数据   价格 / 市值 / 流通量            （CoinGecko，现有）
L2 收入数据   收入 / 毛利 / 增发成本 / 净利 / 增速  （DefiLlama + 链上 + 官方，扩展）
L3 股东回报   股息 / 回购 / 销毁 各机制拆解（各协议适配器，现有）
L4 衍生估值   P/E、P/S、P/B、EV/Rev、派息率    （计算层，扩展）
L5 财报组织   损益表 / 股东回报 / 估值 / 计算口径（呈现层，新增）
```

**关键设计**：L2 与 L3 按实体分轨——**平台币（BNB 等）：收入 = 股东回报（赋能总额，重合）**；应用型协议：L2 收入与 L3 股东回报独立可验证。L4 全部由 L1–L3 派生，杜绝手写 stale 值（对齐 `tev-data-layer.md` 踩坑 #5）。

### 3.3 收入口径判定框架（Revenue Recognition，核心方法论）

> Boss 定稿（2026-08-02）：**平台币不像一家公司，但我们要把它的所有赋能都当成是收入来看。** 收入口径按实体类型分轨，每个协议单独判定。

#### 3.3.1 核心逻辑：赋能即收入（平台币视角）

- **平台币的价值捕获模型 ≠ 公司**。公司靠「经营收入 → 利润 → 分配」；平台币直接通过「赋能持币人」捕获价值（打新、质押、销毁），因此**平台币的收入 = 全部赋能给持币人的价值流**。
- 对**应用型协议**（Uniswap / Aave / Pendle 等），仍保持公司式口径（协议费收入），两者分轨。

#### 3.3.2 平台币收入构成（BNB 口径，Boss 定稿）

**✅ 计入收入：**

| 科目 | 判定理由 | 数据源 |
|---|---|---|
| **(a) 打新**（Launchpad + Launchpool） | 平台币的天然属性，本身就是这样子的 | 用 aBNB 质押奖励推算（见下） |
| **(b) 质押奖励**（Staking） | 计入；**用 aBNB 的质押奖励推算 Launchpad + Staking 的合计收益**（Boss 2026-08-02 确认：aBNB APY 实际已含打新收益，无需单独测算） | aBNB / asBNB APY（链上 StakeHub） |
| **(c) 销毁**（Auto-Burn + BEP-95） | 计入收入——**不然的话这个平台币就没有收入了** | 链上 0xdead + 官方公告（现有实现） |

**❌ 不计入收入：**

| 科目 | 判定理由 |
|---|---|
| **手续费**（gas fee） | 可以不计入（BEP-95 销毁的那部分已通过「销毁」科目计入，其余 gas 费归验证者/链） |

**平台币收入公式（BNB）**：

```
平台币收入 = 打新收益 + 质押奖励 + 销毁
           = aBNB APY × 市值          （打新 + 质押，合并推算）
           + Auto-Burn USD + BEP-95 USD（销毁，链上验证）
```

> **重要结论：对平台币，收入 = 股东回报（赋能总额），两者重合是本框架的设计，不是 bug。**

#### 3.3.3 实体分轨制（收入口径按实体类型判定）

| 实体类型 | 收入口径 | 例 | 数据源 |
|---|---|---|---|
| **platform_token 平台币**（交易所/CEX 生态发行） | 收入 = 全部赋能（打新 + 质押 + 销毁）；手续费不计（Boss 定义：平台币赋能即收入） | BNB、BGB、OKB、MNT（含 L2 链代币，归平台币） | aBNB 类 APY + 链上销毁 |
| **public_chain 公链** | 视具体机制判定（无交易所背景的独立公链另行评估） | （当前 27 协议中主要由平台币覆盖） | — |
| **app 应用型协议** | 收入 = 协议费（fees → 协议部分） | Uniswap / Aave / Pendle / Aster | DefiLlama `dailyRevenue`（逐协议验证） |

> **Boss 分类定义（2026-08-02）**：MNT 虽是 L2 公链，但其核心仍是交易所生态发行的代币——**更愿意统称"平台币"**。平台币的收入口径统一按 BNB 定稿规则：赋能即收入。

**判定流程**（每接入一个协议必须回答，这就是"把口径收好"的落地物）：
1. 这个实体是 **平台币 / 应用 / 独立公链**？
2. 它的**赋能机制**是什么（打新 / 质押 / 销毁 / 分红 / 回购 / 分润）？
3. 哪些科目**算收入、哪些不算？为什么？**（记录进判定书）
4. 数据源与**验证方式**？

**判定铁律（Boss 2026-08-02，从 Aster 提炼）**：
> **只计"流向流通持币人的价值流"；未流通储备的内部变动（销毁/划转）不计入股东回报，最多作注记展示。**
> 例：Aster「198% 回购+销毁」模型中，99% 手续费回购给质押者计入股东回报；1:1 储备销毁烧的是未流通储备币，只减少未来潜在稀释，不作股东回报（营销话术不采信）。

**净利润铁律（Boss 2026-08-02，从 Aave 提炼，框架级）**：
> **所有计算都是算净利润，不是总手续费。** 应用型协议收入 ≠ 所有协议费——大部分收入要给 LP 持有者（流动性提供者），**必须扣除给 LP 的部分，剩下的才是协议净利润**，作为收入与股东回报的计算基础。
> 对应 DefiLlama：用 `dailyRevenue`（协议归属/净）而非 `dailyFees`（总手续费）；对 Aave 这类跟踪不到链上地址的协议，数据源以**官方报告/计划**为准。

#### 3.3.4 收入构成拆解（含金量标注，用于展示而非是否计入）

赋能都算收入后，"含金量"不再决定是否计入，而是决定**展示标注**——告诉投资者这笔收入是"真金白银回收"还是"增发/生态资源买单"：

| 属性 | 定义 | BNB 例 | 说明 |
|---|---|---|---|
| **destroy 销毁型** | 真金白银回收（链上可验证） | Auto-Burn、BEP-95 | 🟢 高含金量 |
| **yield 收益型** | 增发/生态资源支付 | 打新、质押（aBNB） | 🟡 含稀释成本，标注 |

财报页按此拆解收入构成，让投资者看到「12% 收入里，X% 来自真销毁 🟢、Y% 来自质押打新 🟡」。

#### 3.3.5 协议收入口径判定书（v2）

```jsonc
{
  "revenue_recognition": {
    "entity_type": "platform_token",
    "principle": "平台币不像一家公司，把它的所有赋能都当成收入",
    "revenue_included": {
      "launchpad_launchpool": { "note": "平台币天然属性，计入；用 aBNB APY 推算（含打新+质押）" },
      "staking_rewards":      { "note": "计入；aBNB APY 已含打新+质押合计" },
      "burn": { "note": "计入，否则平台币无收入", "items": ["auto_burn", "bep95_burn"] }
    },
    "revenue_excluded": {
      "fees": { "note": "gas 手续费不计入（BEP-95 销毁部分已含于 burn）" }
    },
    "calculation": {
      "revenue_usd_365d": "aBNB_APY × mcap + (auto_burn + bep95)_usd_365d",
      "proxy_apy_source": "asBNB APY（StakeHub 链上）"
    }
  }
}
```

#### 3.3.6 BNB 判定示例（Boss 定稿）

| 科目 | 计入收入? | 构成属性 | 处理 |
|---|---|---|---|
| Launchpad / Launchpool 打新 | ✅ 计入（平台币属性） | 收益型 🟡 | 用 aBNB APY 推算（含打新+质押） |
| 质押奖励（aBNB） | ✅ 计入 | 收益型 🟡 | 同上，合并推算 |
| Auto-Burn + BEP-95 销毁 | ✅ 计入（否则无收入） | 销毁型 🟢 | 链上验证（现有实现） |
| gas 手续费 | ❌ 不计入 | — | 标注"不计入口径"及原因 |

**BNB 财报页呈现**：收入 = 赋能总额（打新 + 质押 + 销毁），按「销毁型 🟢 / 收益型 🟡」拆解；tooltip 注明口径判定书与"手续费不计入"的原因。

#### 3.3.7 对估值倍数的影响（决策已定：方案 A）

平台币口径下 收入 = 股东回报，导致：
- **P/S** = 市值 ÷ 收入 = 市值 ÷ 股东回报 = 1 ÷ 股东回报率
- **P/E**（若用股东回报）= 市值 ÷ 股东回报 = **与 P/S 数值相同**

**✅ Boss 拍板（2026-08-02）：方案 A**——平台币型实体 P/S 与 P/E 展示同一数值，tooltip 标注「收入 = 赋能口径（打新+质押+销毁）」。简单直观，不引入二次口径；应用型协议不受影响（收入 ≠ 股东回报）。

#### 3.3.8 相对 v1 的关键设计调整

- ❌ 废除 v1「收入 ≠ 价值分配」——该原则**对平台币不成立**（Boss 定稿：赋能即收入）
- ✅ 平台币：收入 = 全部赋能（打新 + 质押 + 销毁），手续费不计
- ✅ 应用型协议：保持公司式口径（协议费收入）
- ✅ 含金量标注（销毁型 🟢 / 收益型 🟡）保留，定位从"是否计入"改为"展示标注"

---

## 四、产品范围与页面改造

### 4.1 总览

直接改造现有 /tev/ 板块，不新建独立板块。改造分为两层：

1. **主表升级**（`tev/index.html`）：在现有列基础上增加基本面/估值列
2. **协议财报页**（`tev/protocol.html`）：从"估值概览 + 历史图表"升级为"上市公司式财报页"

### 4.2 主表升级

**现有列**：# / 协议 / 类型 / 市值 / P/S / P/E / 股息率 / 回购率 / 股东回报率 / 派息率 / 数据质量

**新增列**（按 Boss 确认优先级排序，可分两期上）：

| 列 | 说明 | 期次 |
|---|---|---|
| 收入 (Revenue) | 年化协议收入（平台币=赋能总额），`$X.XXB` | P1 |
| 毛利 (Gross Profit) | 收入 − LP 分润，`$X.XXB` | P1 |
| 净利 (Net Income) | 毛利 − 增发成本 − 运营成本（可为负，如 Curve） | P1 |
| 收入增速 (YoY) | 年度同比，`+XX%` / `−XX%` | P1 |
| 净利率 (Net Margin) | 净利 ÷ 收入，`XX%`（可为负） | P1 |
| P/B | 市值 ÷ 协议净资产（口径定义后上） | P2 |
| EV/Revenue | 简化企业价值倍数 | P2 |
| EPS | 股东回报 ÷ 流通量（美元/币） | P2 |

**交互**：周期切换（7D/30D/90D/1Y）继续作用于 yield 类列；收入/增速/利润率默认展示 365d 口径，可加独立切换或 tooltip 说明。

**风格标签升级**：现有"现金牛 / 成长股"判定线（股东回报率 1%）保留，可补充第二个维度（收入增速正负）形成四象限：`现金牛 / 成长股 / 困境反转 / 收缩`（P2 可选）。

### 4.3 协议财报页（核心交付）

详情页按"上市公司财报"逻辑重构为 **6 个区块**：

```
1. 公司概览     协议信息 + 核心财务快照（市值/收入/毛利/净利/股东回报率 5 个大数字）+ 数据质量徽章
2. 损益表       收入 → 毛利（扣 LP）→ 增发成本 → 净利 → 留存（7/30/90/365d 多周期）
                ★ 每个科目可展开「计算过程 + 详细数据」（如 Curve：admin fee $X − 增发 $26M = 净利为负）
3. 股东回报表   机制拆解：股息 / 回购 / 销毁（金额 + 收益率），每项可展开溯源
4. 估值表       P/E / P/S / P/B / EV/Rev / 派息率 / 股东总回报
5. 历史图表     股东回报历史（现有 tev-records 图表保留）+ 新增收入趋势图（P2）
6. 计算口径     ★ 详情页最后：把计算口径的所有考虑讲清楚（Boss 2026-08-02）
                ├─ 实体类型判定（平台币 / 应用 / 公链）及理由
                ├─ 收入口径判定书：计入科目 / 不计入科目 / 为什么（revenue_recognition）
                ├─ 增发成本处理（有对价换收入→成本；无对价→稀释注记）
                ├─ 净利润口径（扣 LP、扣增发，配比原则说明）
                ├─ 股东回报机制判定与含金量标注（销毁型🟢 / 收益型🟡）
                ├─ 数据源与验证（data_pipeline：链上/官方/DefiLlama + AI 自检）
                └─ 已知假设 / caveats（如 BNB 手续费不计入的理由、Sky 留存说明）
```

> **计算过程铁律（Boss 2026-08-02）**：详情页不是只给数字——**计算过程和详细数据必须列出来**（增发量、通胀率、LP 分润比例、回购金额、各项来源），每个科目可展开溯源（对齐"每个数字可溯源"站点原则，hbm 看板同款）。
> **计算口径区块（Boss 2026-08-02）**：详情页**最后一个区块**必须完整呈现「计算口径」，把该协议所有口径判断和理由讲清楚（对应 config 的 `revenue_recognition` + `data_pipeline` + `analyst_notes` + `caveats`）——投资者能看懂"为什么这个数这么算"。

**数据溯源铁律**：财报页每个数字必须可点击溯源（tooltip / 折叠面板展示 数据源 + 计算说明 + 验证状态），对齐"每个数字可溯源"的站点原则（hbm 看板同款）。

### 4.5 详情页区块规范（v2.2，Boss 2026-08-02 定稿，全协议统一标准）

> 在 4.3 基础上，Boss 测试站验收后提出一轮详情页改造需求。**以下为标准，后续所有协议详情页统一遵循**（M2 批量接入时按此渲染）。

**8 条规范**：

1. **移除「股东回报 · 活跃/部分/无」状态卡片**——顶部状态条不再展示。理由：关注点是"用美股指标看这个项目"，而非"现在有没有给持币者提供回报"。
2. **损益表横排**——3 个核心数（收入 / 毛利 / 净利）**横排**展示（占空间少、表现更好），每项下方保留 ⓘ 可展开「计算过程 + 数据源」（溯源铁律不废）。
3. **「股东回报历史」→ 历史数据看板**——不再展示单一 TEV 历史图。改为**可切换指标的历史看板**：历史净收益、历史 P/E、历史 P/S、历史股东回报率、历史净利率等，可看任意口径的历史数据（表格 + 可选图表）。
4. **移除「销毁记录」区块**。
5. **移除「代币经济学」区块**（当前无内容）。
6. **新增「代币流通量曲线」**——代币流通量随时间变化曲线（数据源优先 CMC，免费 Basic 层 15K 次/月；标注数据来源 CMC；key 未到位时保留区块位置不阻塞）。
7. **计算口径文案重写**——面向普通用户：**讲清楚"为什么这么算"**（大白话讲逻辑），去除术语堆砌与乱码。结构仍为折叠卡片（实体类型 / 收入判定书 / 增发处理 / 净利口径 / 含金量 / 数据源验证 / caveats）。
8. **通用标准**——以上 7 条对所有协议生效，新增协议页面必须满足本规范才可上线。

**数据层配套**：
- 历史看板数据源：`build-snapshot.py` 每日产出快照 → 按 `as_of` 累积成时间序列 `data/history/<pid>.json`（净收益/PE/PS/股东回报率/净利率逐日记录）
- 流通量曲线数据源：`scripts/fetch-cmc-supply.py`（CMC API，`CMC_API_KEY` 环境变量，不入仓库）每日拉 27 协议 circulating_supply → `data/supply/<pid>.json`

### 4.4 美股对标（概念级）

- 在方法论区（现有 intro-section）补充"美股对标口径表"：说明 股东回报率 ↔ Shareholder Yield、派息率 ↔ Payout Ratio、P/S ↔ 市销率 等映射
- 每个指标 tooltip 中标注美股对应概念（现有 headerTips 已有雏形，扩展即可）
- **不拉取任何实时美股数据**

### 4.6 UI 交互规范（v2.3，Boss 2026-08-03 定稿，全协议统一）

> **完整规范见独立文档 [`docs/ui-design-system.md`](ui-design-system.md)**（全项目标准，未来所有项目复用）。
> 本节为摘要；明细（颜色、代码、验收清单）以独立文档为准。

**① 关键注意事项（Caveats）**：折叠卡片（details/summary），默认收起，点击展开；字体 12px（小一号），避免视觉噪音。

**② 损益表**：瀑布式展示——收入 → 毛利 → 净利 三个节点用 SVG 连接线（箭头）串起流向，每节点卡片含：指标名 + 大数字 + 边际率小字 + ⓘ 可展开计算过程。比平铺 3 卡更优雅、有层次。

**③ 历史数据图表**（TradingView 风格交互）：
- **单图表叠加**：柱状（单日净收益，左轴）+ 折线（TTM 累计总量，右轴），不拆双图
- **TTM 口径**（Boss 2026-08-03 定名）：过去 365 天滚动和——每天加新增一期、减掉超过一年那期；折线最新点必须 = 损益表净收益
- **可拖动/缩放**：chartjs-plugin-zoom 启用 pan（拖动平移）+ wheel（滚轮缩放）+ drag（框选时间范围）+ 双击重置
- **⚠️ 配置结构铁律**：`plugins.zoom = { pan: {...}, zoom: { wheel, pinch, drag, mode } }`（pan 与 zoom.zoom 并列；错误结构不报错但交互全失效）
- **纵坐标简写**：B=十亿 / M=百万 / K=千
- **横坐标**：完整日期（2025-08-03），autoSkip 自动选 tick
- **高度限制**：单日净收益柱状最高点 ≤ 图 1/2（y.max = p90 × 2.2）
- **数据密度**：一天一个点，不稀疏采样
- **指标切换按钮在图表下方**（pill 风格：圆角胶囊，active 绿色高亮）

**④ 代币流通量**：
- Hero 区：当前流通量**大数字**（橙色 #f0b90b，38px）+ 日期/符号/精确枚数
- 下方历史曲线：90 天每日流通量（CMC historical API），同样支持拖动/缩放/坐标简写
- 说明文案：流通量随时间变化反映增发 vs 销毁净效果（如 BNB BEP-95 使流通量下降）

**⑤ 通用**：数字一律 `JetBrains Mono` 等宽字体；负值红色；无数据「—」而非 0。

---

## 五、数据层架构（本 PRD 的重中之重）

> 针对 Boss 反馈的核心卡点：**数据口径难搞定**。本节设计的目标是让"新增一个协议"变成填空题而不是论述题。

### 5.1 协议适配器模式（Protocol Adapter）

**核心思想**：每个协议一个适配器（Python 脚本 + config），对外输出**统一结构的 Financial Snapshot**；上层计算、展示、验证全部消费统一结构，不感知协议差异。

```
                    ┌─────────────────────────────────────────────┐
                    │         data/protocols/<id>/                │
                    │  config.json（机制/口径/源声明，手写维护）     │
                    │  adapter.py （数据采集+口径计算，每协议专属）   │
                    │  verify.py  （链上哨兵校验，可选）             │
                    └──────────────────┬──────────────────────────┘
                                       │ 输出统一 JSON
                    ┌──────────────────▼──────────────────────────┐
                    │  Financial Snapshot（统一 schema，见 5.2）    │
                    └──────────────────┬──────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
  sync-tev-data.js               validate.py                   前端渲染
  （聚合 → all-protocols.json）   （一致性/新鲜度校验）         （主表 + 财报页）
```

**适配器三件事**（对齐现有 `tev-data-layer.md` 的"三件事框架"）：

1. **机制声明**：本协议的 value accrual 机制是什么（fee 分润 / 回购 / 销毁 / 质押 / 组合），写在 config.json
2. **数据采集**：按 链上 > 官方治理 > 估算 > DefiLlama 优先级取数，脚本实现
3. **口径计算**：把原始数据换算成统一 schema 的字段，`analyst_notes` 记录口径选择理由

### 5.2 Financial Snapshot 统一 Schema（v2）

```jsonc
{
  "protocol": "bnb",
  "as_of": "2026-08-02",
  "income_statement": {
    "revenue": {                 // L2 收入（按 3.3 判定框架，实体分轨）
      "entity_type": "public_chain",   // public_chain | app | cex_token
      "revenue_included": {      // 平台币口径（Boss 定稿：赋能即收入）
        "launchpad_launchpool_usd_365d": 300000000,   // 打新（aBNB APY 推算，含质押）
        "staking_rewards_usd_365d": 500000000,        // 质押奖励（aBNB APY 推算）
        "burn_usd_365d": 1500000000,                  // 销毁（Auto-Burn + BEP-95，链上验证）
        "total_usd_365d": 2300000000                  // = 打新 + 质押 + 销毁
      },
      "revenue_excluded": {      // 明确不计入的科目
        "fees": { "note": "gas 手续费不计入（BEP-95 销毁部分已含于 burn）" }
      },
      "growth_yoy_percent": null,
      "source": { "type": "defillama|chain|official|estimate", "url": "..." }
    },
    "gross_profit": {             // 毛利 = 收入 − 直接成本（LP 分润等）
      "lp_share_cost_usd_365d": 1200000000,   // 给 LP/流动性提供者的分润
      "gross_profit_usd_365d": 1100000000,    // 应用型必填；平台币无 LP 成本时 = revenue
      "calculation_note": "收入 − LP 分润（详情页展示计算过程）"
    },
    "token_emission_cost": {      // 增发成本（美股 SBC 类比，Boss 铁律）
      "usd_365d": 26000000,                   // 年增发代币 × 均价（Curve 约 $26M / Pancake 约 $11.7M）
      "annual_emission_tokens": 115000000,    // 年增发量（CRV 示例）
      "inflation_rate_percent": 4.8,
      "calculation_note": "增发激励作为成本扣除（详情页展示增发量/通胀率/换算过程）"
    },
    "net_income": { ... },        // 净利 = 毛利 − 增发成本 − 运营成本（口径在 config 声明）
    "margins": {                  // 计算派生；平台币无成本模型时标注 N/A
      "gross_margin_percent": null,
      "net_margin_percent": null, // 净利可为负（Curve 案例：增发 > 收入）
      "note": "净利为负时详情页必须展示完整计算过程（收入−LP−增发=负）"
    }
  },
  "holder_returns": {             // L3 股东回报（原 TEV 机制拆解）
    "by_mechanism": [             // 每个机制带"含金量属性"（3.3.4 展示标注）
      { "mechanism": "auto_burn",  "type": "destroy", "usd_365d": 1000000000, "yield_percent": 4.42 },
      { "mechanism": "bep95_burn", "type": "destroy", "usd_365d": 500000000,  "yield_percent": 2.21 },
      { "mechanism": "asbnb_staking", "type": "yield",  "usd_365d": 300000000,  "yield_percent": 1.33 }
    ],
    "summary": {
      "destroy_usd_365d": 1500000000,    // 销毁型（真金白银，🟢 高含金量）
      "yield_usd_365d": 300000000,       // 收益型（增发/生态，🟡 标注稀释）
      "destroy_yield_percent": 6.63,
      "yield_yield_percent": 1.33,
      "shareholder_returns_usd_365d": 1800000000,  // 股东回报总额（股息+回购+销毁）
      "shareholder_yield_percent": 7.96            // 股东回报率（原 tev_yield_percent）
    }
  },
  "balance_sheet": {              // L1 + 简化资产负债（P2 完善）
    "market_cap_usd": 76912536768,
    "tvl_usd": 5387604237,
    "treasury_usd": null,         // 协议金库（可选，P2）
    "debt_usd": null              // 协议负债（极少有，默认 null）
  },
  "valuation": {                  // L4 全部由上面派生，禁止手写
    "pe": 8.02,                   // mcap / shareholder_returns_usd_365d
    "ps": null,                   // 无收入时为 null → 前端显示 —
    "pb": null,
    "ev_revenue": null,
    "payout_ratio": null          // 派息率（原 tevRatio 语义）
  },
  "verification": {               // 链上/交叉验证状态
    "method": "Auto-Burn 近4季 5,977,992 BNB + BEP-95 日序列 + asBNB APY",
    "status": "verified|partial|estimated",
    "last_checked": "2026-08-02"
  }
}
```

**铁律**：
- `valuation` 与 `margins` 必须由上层脚本从 L1–L3 派生计算，**禁止在协议 config 里手写**（对齐踩坑 #5、#6）
- 无数据的字段一律 `null`，前端渲染 `—`，**禁止编造 0**（对齐踩坑 #8）
- `holder_returns` 中的 yield 必须与现有 `shareholder_yield_percent / dividend_yield_percent / buyback_yield_percent` 数值一致（数据层 post-pass 校验；字段名按头部迁移表，旧 tev_yield_percent 作废）

### 5.3 BNB 标杆适配器（先行设计）

BNB 是全站机制最复杂的协议（平台币、无 fee 分润、CEX 财务不公开），跑通它 = 定义最难模型：

| 科目 | 数据源 | 现有实现 | 计入收入?（Boss 定稿） |
|---|---|---|---|
| Auto-Burn（季度 4 次） | 链上 0xdead 转账 + 官方公告 | ✅ 现有（短周期=近4季USD累加；365d=近4季BNB×当前价） | ✅ 销毁型 🟢 |
| BEP-95（日频） | 链上 0xdead 日时间序列（`bep95-history.json`） | ✅ 现有（窗口求和） | ✅ 销毁型 🟢 |
| aBNB 质押 + 打新 | 链上 StakeHub 合约 APY | ✅ 现有（asBNB APY） | ✅ 收益型 🟡（aBNB APY 推算打新+质押合计） |
| gas 手续费 | — | — | ❌ 不计入（BEP-95 销毁部分已含于 burn） |

**BNB 适配器任务清单（M1）**：
- [ ] 产出 `data/protocols/bnb/adapter.py`，输出 5.2 完整 schema
- [ ] 产出 **收入口径判定书**（config.json `revenue_recognition`）：entity_type=platform_token；included=打新+质押+销毁；excluded=gas 手续费；calculation=aBNB_APY × mcap + 销毁 USD
- [ ] `holder_returns` 从现有 burn/aBNB 数据组装，按 3.3.4 拆「销毁型 destroy / 收益型 yield」两组，确保合计与 all-protocols.json 数值一致
- [ ] 财报页 BNB 专属展示：收入=赋能总额（打新+质押+销毁）按含金量分组 + 销毁历史图表（现有）+ 手续费不计入口径 tooltip
- [ ] 验证：`validate.py` 通过 + Boss 测试站验收

### 5.4 数据管道改造

在现有更新管道（`~/crypto3d-updater/update.sh`）基础上：

```
Step 3（现有）  fetch-*-tev.py 各协议专属采集
   ↓ 新增
Step 3.5       build-snapshot.py  跑所有已接入协议适配器 → 生成 Financial Snapshots
Step 4（现有）  sync-tev-data.js   聚合 → data/all-protocols.json（消费 snapshot，不再读散字段）
Step 5（现有）  validate.py        校验扩展：snapshot 完整性 / 派生字段自洽 / 新鲜度
```

**新鲜度监控扩展**：现有 `validate-tev-records.py`（>26h 告警）扩展到 snapshot 各字段，避免再次出现"BNB daily/latest.json 停在 2026-02-09"这类僵尸数据（本次调研已发现，需纳入修复）。

### 5.5 数据源矩阵与自动化运维（Boss 2026-08-02 补充，重点）

> Boss 要求：**PRD 必须写明每个项目收入口径的数据从何而来**——是链上每天跑脚本，还是定期看官方公布？**官方公布的信息也要用脚本自动运行**（不能靠人工）。最终目标：**网站可以在服务器上自动运行，部分脚本每天都跑，AI 用来自检。**

#### 5.5.1 数据源五类 + 采集方式

| 数据源类型 | 采集方式 | 频率 | 自动化 |
|---|---|---|---|
| ① **链上**（RPC/区块/合约事件） | 脚本调 RPC 遍历（0xdead、回购钱包、StakeHub 等） | 日频 | 定时脚本（每天跑） |
| ② **官方 API** | 脚本调官方接口 | 日频/周频 | 定时脚本 |
| ③ **官方公告/报告/治理页** | **网页抓取 + AI 阅读解析**（检测新公告/机制变化/新披露） | 日频 + 事件驱动 | 定时脚本 + LLM 解析（AI 自检哨兵） |
| ④ **DefiLlama API** | 脚本调 api.llama.fi（dailyRevenue 等） | 日频 | 定时脚本 |
| ⑤ **手动/估算** | 人工核实，写进 analyst_notes | 季度/事件 | 记录留痕，validate 强制要求 |

#### 5.5.2 每个协议必须声明 `data_pipeline`（数据从哪来）

每个协议 config.json 增加 `data_pipeline` 字段——这就是"前置信息"的落地物：

```jsonc
"data_pipeline": {
  "sources": [
    { "type": "chain",   "method": "RPC 遍历 0xdead 转账",           "frequency": "daily", "script": "update-bnb-tev.py" },
    { "type": "official","method": "AI 抓取 Auto-Burn 公告（变更检测）", "frequency": "event", "script": "ai-watch-official.py" },
    { "type": "defillama","method": "dailyRevenue",                   "frequency": "daily", "script": "fetch-defillama.js" }
  ],
  "ai_self_check": ["机制变更检测", "数据合理性", "交叉验证", "新鲜度"]
}
```

**已定稿协议的数据源归属（登记表）**：

| 协议 | 数据源类型 | 采集方式 | 频率 | 脚本 |
|---|---|---|---|---|
| BNB | 链上 + 官方 | 0xdead 遍历 + StakeHub APY + **AI 抓 burn 公告** | 日频 + 事件 | update-bnb-tev.py + ai-watch-official.py |
| Aster | 链上 + 官方 | 新回购钱包 + 1:1 销毁记录 + **AI 抓公告** | 日频 + 事件 | update-aster-tev.py（改造）+ ai-watch |
| BGB | 官方 + 链上 | **AI 抓季度销毁公告** + 链上销毁地址复核 | 季度 + 日复核 | ai-watch-official.py + 链上校验 |
| OKB | 静态 | 股东回报=0，无需采集 | 季度复核 | 无（config 静态） |
| Aave | 官方 + DefiLlama | **AI 抓治理提案/月报（回购金额变化）** + dailyRevenue 日频 | 日频 + 事件 | ai-watch-governance.py + fetch-defillama.js |
| MNT | 静态 | 当前 0，Staking 上线后补链上 | 季度复核 | 无（config 静态） |
| 其余（待定稿） | — | 定稿时同步补 `data_pipeline` | — | — |

> **铁律**：官方公布的信息（公告/报告/治理提案）一律由**脚本自动抓取 + AI 阅读解析**，禁止人工定期去查（Aave 回购变化、BGB 季度销毁、Aster 机制升级这类事件，AI 哨兵负责发现）。

#### 5.5.3 AI 自检哨兵（AI Self-Check Sentinel）

用户目标"AI 还可以用来自检"——在每日管道中加入 LLM 自检环节（`scripts/ai-self-check.py`）：

| 自检项 | AI 做什么 | 触发 |
|---|---|---|
| **机制变更检测** | 阅读官方公告/治理页新内容，判断 tokenomics/收入口径是否变化（Aster 99% 就是这类漏网之鱼） | 日频 + 事件 |
| **数据合理性** | 数值突变（环比 > 阈值）、负值、Null 异常 | 日频（validate 后） |
| **交叉验证** | 链上 vs DefiLlama 差异 > 阈值告警；快照与 all-protocols.json 自洽 | 日频 |
| **新鲜度** | snapshot 各字段 > 26h 告警（防僵尸数据） | 日频 |
| **口径回归** | 新协议接入后，既有协议 yield 数值保持不变（回归保护） | 协议接入时 |

##### 5.5.3.1 GLM API 集成（Boss 提供 key）

- **模型供应商**：智谱 GLM（Boss 提供 API key）
- **调用方式**：OpenAI 兼容格式，`scripts/ai-self-check.py` 统一封装
- **配置**：`config/ai-sentinel.json`（key 不落库，从环境变量 `GLM_API_KEY` 读取；env 文件放服务器、不入 git）

```jsonc
// config/ai-sentinel.json
{
  "provider": "zhipu-glm",
  "endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
  "model": "glm-4.6",                 // 以 Boss 实际开通为准，可改
  "api_key_env": "GLM_API_KEY",       // key 从环境变量读，禁止写进仓库
  "temperature": 0,                   // 审计必须确定性输出
  "timeout_sec": 60,
  "max_retries": 2,
  "tasks": ["mechanism-change", "data-plausibility", "cross-validation", "freshness", "regression"]
}
```

- **调用链**：`ai-self-check.py` 读 官方公告抓取缓存 + snapshot + config → 按任务拼装 prompt → 调 GLM → **校验 JSON schema**（不合法则重试 1 次，仍失败标 `AI_ERR` 告警，不影响主数据管道）

##### 5.5.3.2 审计提示词模板（设计阶段定稿，直接可复用）

> 以下 5 套提示词是**交付物**，实现时直接抄用，禁止临时改需求。每套都强制输出 JSON，供脚本解析。

**① 机制变更检测 mechanism-change**（日频 + 事件）

```
[SYSTEM]
你是 Crypto3D 数据站的协议口径审计员。你的职责是判断 DeFi 协议的代币经济机制
（tokenomics）是否发生变化，以及变化是否影响我们计算收入/股东回报的口径。
只输出一个 JSON 对象，不要输出任何其他内容。

[USER]
请对比以下两份信息，判断协议机制是否发生变化：

【当前 config 口径判定书】
{config_revenue_recognition}

【最新官方信息（公告/报告/治理页抓取）】
{official_feed}

判断规则：
1. 官方信息是否提到 回购/销毁/打新/质押/分润 比例的变化？
2. 是否出现新的价值分配机制，或旧机制终止？
3. 是否提到供应量、储备、销毁目标的变化？
4. 与 config 口径冲突或需要补充的地方？

输出 JSON（schema）：
{
  "has_change": true 或 false,
  "changed_fields": ["字段名", "..."],
  "summary_zh": "一句话中文摘要",
  "evidence": "引用原文片段",
  "confidence": "high|medium|low",
  "recommendation": "update_config|need_manual_review|no_action"
}
```

**② 数据合理性 data-plausibility**（日频，validate 后）

```
[SYSTEM]
你是数据质量审计员，检查 DeFi 协议财务数据是否存在异常。
只输出一个 JSON 对象。

[USER]
请检查以下时间序列数据是否异常：
{series_json}

检查项：
1. 环比/同比突变超过 50%？
2. 出现负值或不应出现的 0？
3. Null/缺失是否合理（如 CEX 财务本就不公开）？
4. 数值量级是否与市值、历史量级一致？

输出 JSON：
{
  "is_abnormal": true 或 false,
  "flags": [{"field": "字段", "issue": "问题描述", "severity": "high|medium|low"}],
  "summary_zh": "一句话中文摘要"
}
```

**③ 交叉验证 cross-validation**（日频）

```
[SYSTEM]
你是数据交叉验证审计员，比较链上数据与第三方数据源的差异。
只输出一个 JSON 对象。

[USER]
链上数据：{chain_data}
第三方数据（DefiLlama 等）：{third_party_data}
对比字段：{fields}
告警阈值：差异超过 {threshold_percent}%

输出 JSON：
{
  "mismatches": [{"field": "字段", "chain_value": 数值, "third_party_value": 数值,
                  "diff_percent": 数值, "severity": "high|medium|low"}],
  "verdict": "ok|review|alert",
  "summary_zh": "一句话中文摘要"
}
```

**④ 新鲜度 freshness**（日频，纯脚本判断，不需要 LLM）

```
脚本逻辑：遍历 snapshot 各字段的 updated_at / 数据日期，
任一字段 > 26h → 告警。输出结构化告警清单。
（不消耗 GLM 额度，validate.py 内置即可）
```

**⑤ 口径回归 regression**（协议接入时）

```
[SYSTEM]
你是回归测试审计员，确认新协议接入没有破坏既有协议的数据。
只输出一个 JSON 对象。

[USER]
以下既有协议在本次接入前后的数值：
接入前：{before_json}
接入后：{after_json}

规则：任何差异超过 {epsilon} 都是回归错误。

输出 JSON：
{
  "regressed": [{"protocol": "协议", "field": "字段", "before": 数值, "after": 数值}],
  "verdict": "ok|regression",
  "summary_zh": "一句话中文摘要"
}
```

##### 5.5.3.3 输出校验与告警

- **JSON 校验**：每套提示词的输出都按对应 schema 校验（`scripts/prompt-schemas.py`）；不合法 → 重试 1 次 → 仍失败标 `AI_ERR`
- **告警分级**：`alert`（机制变更/高严重度）→ Telegram 通知 Boss；`review`（中等）→ 日志 + 日报；`ok` → 静默
- **审计痕迹**：每次自检结果落 `data/ai-audit/<date>.json`，可回溯（Boss 可随时查"AI 上次审计说了什么"）

输出：告警写日志 + 可投递 Telegram 通知 Boss（对齐现有团队通知体系）。

#### 5.5.4 服务器自动运行目标架构（无人值守）

```
定时调度（cron / LaunchAgent，每日 9:03 / 21:03，扩展现有 update.sh）
  ├─ Step 3.x   各协议 adapter.py 采集（链上 / 官方 / DefiLlama）
  ├─ Step 3.5   build-snapshot.py        → Financial Snapshots
  ├─ Step 4     sync-tev-data.js         → all-protocols.json
  ├─ Step 5     validate.py              → 结构 / 自洽 / 新鲜度
  ├─ Step 5.5   ai-self-check.py ★新增   → AI 自检（公告变更 / 合理性 / 交叉验证）
  ├─ Step 6     git commit + push dev    → 自动部署测试站
  └─ 告警       失败 / AI 检出机制变更 → 日志 + Telegram 通知 Boss
```

**目标**：无人值守自动运行——数据每天自动更新、AI 自动盯官方公告与口径变化、异常自动告警。

#### 5.5.5 对新增协议工作流的影响

新增协议时，除 config/adapter 外，**必须补 `data_pipeline` 声明**并加入 update.sh 对应 step；否则 validate 不通过（对齐 `tev-data-layer.md`「新协议必加维护脚本」铁律，杜绝 tev-records 停更问题）。

### 5.6 新增协议工作流（改造后）

对齐 `tev-data-layer.md` 第八章，新增一步：

1. 调研机制 → 2. 分类（fee 分润 / 独立机制）→ 3. **写 config.json（机制声明 + 收入口径判定书 `revenue_recognition`）** → 4. **写 adapter.py（数据采集 + 计算）** → 5. 链上校验（哨兵脚本）→ 6. **本地跑 build-snapshot.py 输出 snapshot + validate.py 自检** → 7. 推 dev → 测试站验收 → 8. Boss 确认后 merge main

---

## 六、里程碑与验收标准

> 部署纪律全程遵守：dev 开发 → 测试站验证 → **Boss 确认** → merge main → Cloudflare 正式站。

### M0 — 数据地基（本周）
- 定义并落地 5.2 统一 schema（JSON 样例 + 文档）
- 实现 `build-snapshot.py` + 扩展 `validate.py`
- **实现 `ai-self-check.py` 骨架**（5.5.3：公告变更检测 / 合理性 / 交叉验证 / 新鲜度）
- **协议 `data_pipeline` 字段落地**（5.5.2：**27 个协议全量补齐**数据源/频率/脚本声明）
- **僵尸数据全量补全**（Boss 2026-08-02 确认）：
  - `data/daily/` 全部 27 协议 latest.json 停更 5 个月 → 全部重建
  - 重复目录去重：`curve`/`curve-dex`、`ether.fi`/`etherfi`
  - 26 个 config.json last_updated 停在 04 月底 → 按新口径全量更新
- **验收**：schema 评审通过；validate 脚本可在现有数据上跑通；AI 自检可在 BNB 数据上跑出告警样例；僵尸数据清零

### M1 — BNB 标杆（M0 后 1 轮迭代）
- 完成 BNB 适配器 + Financial Snapshot
- 财报页重构（6 区块 + 数据溯源）
- 主表 P1 新增列（收入/毛利/净利/增速/净利率）
- **验收（Boss 测试站验收）**：
  - BNB 财报页 6 区块全部呈现，每个数字可溯源
  - 主表新增列数值与 BNB 快照一致
  - 收入"不可得"的协议正确显示 `—` 而非 `0`
  - 周期切换、tooltip、i18n 无回归

### M2 — Top 10 批量复制（M1 后）
- 按主表默认顺序（有股东回报 > 0 优先 + 市值降序）接入：Aave、Hyperliquid、Sky、Uniswap、Pendle、Curve、dYdX、GMX、Aster、ether.fi
- 每个协议走 5.6 完整工作流，逐个 Boss 验收
- **验收**：每协议财报页可溯源 + 与现有股东回报数值自洽

### M3 — 全量 + 文档（M2 后）
- 剩余 17 个协议接入（含 无回购协议：财报页显示"治理代币，无股东回报"）
- 完成"美股对标口径表"方法论文档（更新 `tev-data-layer.md` 或新增 `docs/equity-mapping.md`）
- **验收**：27 协议全部有 snapshot；文档完备；站点整体回归

---

## 七、风险与避坑（对齐现有踩坑清单）

| 风险 | 应对 |
|---|---|
| 收入口径不统一（fees vs revenue vs holdersRevenue 混用） | 5.1 适配器强制逐协议声明 + 5.2 schema 三字段分离；对齐踩坑 #4 |
| 派生字段手写导致数学不自洽 | 5.2 铁律：valuation/margins 一律脚本派生，validate 校验；对齐踩坑 #5 #6 |
| 周期口径陷阱（BNB 季度 burn 用滚动窗口） | 沿用现有双口径设计，适配器内固化；对齐踩坑 #1 #2 |
| 无股东回报协议被硬算/编造 | `null` 语义贯穿全链路，前端渲染 `—`；对齐踩坑 #8 |
| 僵尸数据/字段停更 | 5.4 新鲜度监控扩展 + 本期清理既有僵尸数据；对齐踩坑 #10 |
| 范围再次铺太大做不完 | 里程碑严格 gate：M1 BNB 不过 Boss 验收不开 M2 |
| 前端两套数据源（主表 vs 详情页）不同步 | 改造后详情页直接消费 snapshot 同源数据，消除双写；对齐踩坑 #9 |
| 增发成本判定错误（有对价/无对价分不清） | 头部「增发成本铁律」配比原则 + 每协议判定书写明 + AI 哨兵检查 |
| 协议机制过时（Aster 99% 案例） | 5.5 AI 哨兵机制变更检测（GLM 读官方公告）+ 稀释注记强制展示 |
| GLM API 不可用/输出异常 | 5.5.3.3 JSON 校验 + 重试 + AI_ERR 告警降级，不影响主数据管道 |

---

## 八、附录

### 8.1 协议清单与适配器接入优先级

按 `data/all-protocols.json` **27 个协议**（原 26 + 新增 LayerZero），接入顺序以"机制复杂度 + 股东回报意义 + 市值"综合排序：

| 批次 | 协议 | 机制类型 | 备注 |
|---|---|---|---|
| M1 | BNB | burn+staking（最复杂） | 标杆 |
| M2 | Aave / Hyperliquid / Sky / Uniswap / Pendle / Curve / dYdX / GMX / Aster / ether.fi | 回购/销毁/分润/质押混合 | 高股东回报意义 |
| M3 | 其余 15 个（Lido、EigenLayer、Compound、Morpho、Spark、Kamino、JustLend、Ethena、Maple、BGB、OKB、MNT、PancakeSwap、Jito、Fluid）+ **LayerZero** | 含无回购协议 + 期权型 | 全量覆盖 |

### 8.2 关键决策记录（Boss 确认）

| 决策点 | 结论 |
|---|---|
| 升级范围 | 损益表体系 + 基本面指标 + 估值倍数 + 概念级美股对标 + 协议财报页（全维度） |
| 范围取舍 | **先做 BNB 标杆协议**，验证模式后批量复制 |
| 历史卡点 | 数据口径难搞定 → 数据层架构为 PRD 重中之重 |
| 美股对标 | **概念级对标，不做实时美股数据对比** |
| 页面形态 | **直接改造 /tev/**，不新建独立板块 |
| 发版纪律 | **只推 dev / 测试站，严禁直接改主站**（2.4 铁律） |
| 收入口径 | **平台币：赋能即收入**（打新 + 质押 + 销毁计入，gas 手续费不计入）；应用型：协议费收入；**所有计算用净利润**（扣 LP，DefiLlama 用 dailyRevenue 非 dailyFees） |
| 术语体系 | **废弃 TEV**，统一用损益表语言：收入 → 毛利 → 净利 → 股东回报 → 留存（头部术语约定） |
| 增发成本 | **有对价换当期收入（LP 挖矿/gauge/farm）→ 算成本；无对价 → 稀释注记**（配比原则，Curve/Pancake 定稿） |
| 只计流通价值 | 未流通储备的内部变动（销毁/划转）不计入股东回报，最多作注记（Aster 198% 案例） |
| 平台币 P/S 与 P/E 重合 | **方案 A**：同值展示，tooltip 标注「收入 = 赋能口径」 |
| 详情页 | 6 区块，**最后一个区块「计算口径」**把口径考虑讲清楚（4.3） |
| 自动化运维 | 数据源逐协议声明（`data_pipeline`），**官方公告 AI 抓取 + GLM 每日自检**（5.5，Boss 提供 GLM key） |
| 新增协议 | **只加 LayerZero**（TVL 排名对比后决策；GT/KCS/CRO/Babylon/SSV 暂缓） |

### 8.3 协议口径判定书摘要（27 协议总表）

> 完整判定书见 `docs/protocol-revenue-recognition.md`；本表为 PRD 附录摘要。含金量：🟢 销毁型/真金白银 ｜ 🟡 收益型/增发 ｜ ⬜ 无股东回报

| # | 协议 | 实体 | 收入口径 | 股东回报 | 关键注记 |
|---|---|---|---|---|---|
| 1 | BNB | 平台币 | 打新+质押+销毁（aBNB APY 推算打新+质押）| 🟢 销毁 / 🟡 打新质押 ≈12% | gas 手续费不计入；收入=股东回报 |
| 2 | MNT | 平台币 | 赋能即收入 | ⬜ 当前 0 | 无赋能（gas 不进币）；标"治理代币"，Staking 上线后补 |
| 3 | Aster | 应用 | 平台手续费 | 🟢 99% 回购给质押者 | 1:1 储备销毁不计（未流通）；198% 是营销话术 |
| 4 | BGB | 平台币 | 季度利润 20% 回购销毁 | 🟢 季度回购 | 已与 Bitget 切割；官方公告+链上验证 |
| 5 | OKB | 平台币 | 无 | ⬜ 0 | 空气币；2025-08 永久停止回购 |
| 6 | Aave | 应用 | 协议净利润（扣 LP）| 🟢 $30M 回购 / 🟡 Safety Module | 数据源=官方报告（跟踪不到地址）|
| 7 | Sky | 应用 | 协议盈余（扣 DSR 利息）| 🟢 Elixir 真燃烧 | 留存国库讲清楚；SBE 做市不计 |
| 8 | Uniswap | 应用 | 抽成手续费 | 🟢 Firepit 销毁 | fee switch 2025-12 开启；回购地址待调研 |
| 9 | Hyperliquid | 应用 | 交易费 | 🟢 spot 销毁 ≈99% | AF 余额不计（treasury 可动用）|
| 10 | Pendle | 应用 | 协议净利润 | 🟢 80% 回购给 sPENDLE | Boss 拍板 80% |
| 11 | Curve | 应用 | admin fee | 🟡 veCRV 分红（admin fee 口径）| **增发 $26M 成本 → 净利为负** |
| 12 | dYdX | 应用 | 净协议费（标注口径不透明）| 🟢 回购（**质押非销毁**，小）| 已改名 **Arcus**（交易所品牌，DYDX 代币未改名）；已非头部；P/F~88x |
| 13 | GMX | 应用 | 平台费 | ⬜ 当前 0 | **锁定至 $90**（价格阈值非市值）；27% 费用转国库留存 |
| 14 | PancakeSwap | 应用 | 协议费 | 🟢 回购销毁 ≈60-65% 收入 | **净通缩**（增发 $11.7M < 回购 $18M）|
| 15 | Maple | 应用 | 协议费 | 🟢 回购 10/20/30% 阶梯 | **MIP-021**（2026-07 起）：月收入 <$1.5M→10% |
| 16 | ether.fi | 应用 | 协议收入 | 🟢 双引擎回购 ≈4-6% | 提现费 100% + 收入 25% 回购给 sETHFI；Cash 业务占 55% |
| 17 | Ethena | 应用 | sUSDe yield | ⬜ ENA 当前 0 | **费用开关 2026Q3 待激活**（激活后 sENA >5%）→ AI 哨兵观察点；DAT 回购是资本运作 |
| 18 | JustLend | 应用 | 净收入 | ⬜ 0 | 做账式销毁（金库→黑洞，无市场买入）|
| 19-25 | Lido/EigenLayer/Compound/Morpho/Spark/Kamino/Jito | 应用 | 净利润照算 | ⬜ 0 | 只统计利润；不回购的钱进国库/支出，损益表"留存"行展示 |
| 26 | LayerZero | 应用 | Stargate 收入；协议本体 0（fee switch 关）| 🟢 Stargate 回购（小额）| **月解锁 $48M 稀释注记**；费用开关公投=AI 哨兵观察点 |
