# Sky（MakerDAO）— 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Sky 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Sky (MakerDAO) / MKR |
| 实体类型 | `application`（cdp / 稳定币） |
| 市值（as_of 2026-08-04） | ~$1.81B |
| 股东回报率 | ~4.30%（股息 0% + 回购销毁 4.30%） |
| 置信度 | high |
| 数据源优先级 | 链上（SBE/Elixir 地址）> DefiLlama dailyHoldersRevenue > 官方治理 |

## 二、收入判定（核心）

**Boss 定稿口径：盈余先进 Surplus Buffer 国库（≤5000 万 DAI）；超额 SBE 买入 MKR + 等量 DAI 组 LP 做市；Elixir 真燃烧 = 发股息（回购性质 🟢）**

```
协议盈余 = dailyRevenue 365d = $234,377,977（已扣 DSR/SSR）
股东回报 = dailyHoldersRevenue 365d（Splitter burn = SBE 真实支出）= $77,998,812
回报率 = $77,998,812 ÷ 市值 $1.81B = 4.30%
留存 vs 分配：留存 66.7% / 分配 33.3%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| Elixir 真燃烧 | Splitter burn 部分（SBE/Elixir 真燃烧实际支出），销毁 = 发股息 🟢 | DefiLlama dailyHoldersRevenue |

| 不计入 | 原因 |
|---|---|
| Surplus Buffer 留存 | 国库留存（上限 5000 万 DAI），非流向持币人 |
| SBE 买 MKR 做市 | 买 MKR + 等量 DAI 组 LP 做市，LP 归协议锁定，标注「回购做市」，非直接流向持币人 |
| Splitter farm 部分 | 新铸造 SKY + USDS yield 给 SKY stakers，为协议支出而非市场回购 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| Elixir / SBE 真燃烧（Splitter burn → MKR LP 销毁） | `destroy`（销毁=股息） | 4.30%（分配 33.3%） |
| Surplus Buffer 留存 + SBE 回购做市（LP 锁定） | `buyback`（回购做市） | 0%（不计入，留存 66.7%） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/sky/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 all-protocols.json → `validation.burn_365d_usd`（dailyHoldersRevenue = Splitter burn 365d = $77,998,812）+ `metrics.trailing_365d_revenue_usd`（dailyRevenue 365d = $234,377,977）
2. `retained = revenue − burn = $156,379,165`（留存）；`dist_ratio = burn/revenue = 33.3%`；`retain_ratio = 66.7%`
3. 毛利 = 协议盈余（cdp 已扣 DSR/SSR 用户利息，无 LP 分润成本）
4. 净利 = 协议盈余，calculation_note 写明「留存 vs 分配」比例
5. 股东回报 by_mechanism = [{mechanism: "Elixir/SBE 真燃烧", type: "destroy", usd: $77,998,812, yield: 4.30%}, {mechanism: "留存+SBE 回购做市", type: "buyback", 不计入}]
6. 派生估值：pe = mcap/burn = 23.27，payout_ratio = dist_ratio = 0.3328

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| DefiLlama dailyHoldersRevenue | 日频 | fetch-defillama.js |
| 链上：SBE/Elixir 地址 | 日频 | update-sky.py |

## 六、历史验证与注意点

- **⚠️ 2026-03 治理减速**：Splitter burn 参数大幅下调（日均从 ~$300k 降至 ~$37.6k，-87.5%），365d 窗口含下调前高峰 → 短周期 yield < 365d（不是价值损失，是 burn 速度放缓）
- **SBE 销毁的是 LP token 不是 MKR 本身**：链上 MKR @ 0xdead 365d 只有 0.0001 MKR；SKY @ 0xdead 4.82 SKY，0xdead 余额不反映真实 burn
- **数据源选择**：SBE 链上数据分散（新 Flapper 地址未公开 + LP token burn 复杂），DefiLlama dailyHoldersRevenue 已精准对应 SBE 支出（与 2026-03 治理公告 $37,600/天 吻合）→ 采用 DefiLlama 是合理权衡
- **Earning vs TEV 差值**：Earning Yield 12.92%（dailyRevenue）与 TEV 4.30% 的差值 = Splitter farm 部分（协议支出）
- **MKR vs SKY**：市值/ticker 用 SKY（活跃现行 token），burn 目标仍为 MKR（经 LP 机制间接），Dashboard 显示 MKR 保持历史连续性

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §7（Boss 2026-08-02 定稿）
- 配置文件：`data/protocols/sky/config.json`（revenue_recognition 字段，payout_ratio≈0.3336）
- 数据维护说明：`data/protocols/sky/README.md`（如有）
