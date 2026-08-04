# BNB — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 BNB 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | BNB Chain / BNB |
| 实体类型 | `platform_token`（平台币） |
| 市值（as_of 2026-08-04） | ~$76.9B |
| 股东回报率 | ~12.46%（股息 6.87% + 回购 5.59%） |
| 置信度 | high |
| 数据源优先级 | 链上（0xdead / StakeHub）> 官方公告 > 估算 |

## 二、收入判定（核心）

**Boss 定稿口径：平台币赋能即收入**（2026-08-02）

```
收入 = aBNB APY × 市值 + (Auto-Burn + BEP-95) USD
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 打新（Launchpad/Launchpool） | 公链天然属性；用 aBNB APY 推算（含打新+质押合计） | StakeHub 链上 |
| 质押奖励（aBNB） | APY 6.87%（Aster 官方披露，Boss 确认含打新+质押） | 链上 |
| 销毁（Auto-Burn） | 季度自动销毁，近 4 季 USD 重估 | 链上 0xdead |
| 销毁（BEP-95） | 每区块按比例销毁 gas fee 的一部分 | 链上 0xdead |

| 不计入 | 原因 |
|---|---|
| gas 手续费 | BEP-95 销毁部分已含于销毁科目，避免重复计算 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| aBNB 打新+质押 | `yield`（股息） | 6.87% |
| Auto-Burn + BEP-95 销毁 | `destroy`（回购） | 5.59% |

## 四、关键计算逻辑（adapter.py）

`data/protocols/bnb/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `burn-history.json`（quarterly_burns + asbnb_apy_percent）+ `bep95-history.json`（506 天序列）
2. `burn_4q_usd = validation.recent_4q_burn_usd_current`（Auto-Burn 近 4 季 USD 当前价重估）
3. `bep95_usd = bep95_365d_bnb × bnb_price`（BEP-95 365 天累计 × 当前价）
4. `staking_usd = aBNB_APY × mcap`
5. `total_rev = burn_usd + staking_usd`

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| Auto-Burn 公告 | 事件驱动（季度） | ai-watch-official.py（AI 抓公告） |
| BEP-95 链上 | 日频 | update-bnb-tev.py |
| aBNB APY | 日频 | 链上 StakeHub |

## 六、历史验证与注意点

- **⚠️ BEP-95 时间序列**：BEP-95 从 2021-11 启动，序列有 506 天
- **Auto-Burn 双口径**：7d/30d/90d 用历史 USD 累加，365d 用 BNB 量 × 当前价（重估）
- **asBNB APY 固定 6.87%**：含打新+质押合计（Boss 2026-08-02 确认），不是纯质押
- **Earning Yield = BEP-95 + aBNB APY**（不含 Auto-Burn，因为 Auto-Burn 是公式销毁不是"收入"）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §1
- 配置文件：`data/protocols/bnb/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/bnb/README.md`（TEV 公式详解）
