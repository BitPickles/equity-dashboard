# MNT — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 MNT 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Mantle / MNT |
| 实体类型 | `platform_token`（平台币，L2 链代币，交易所生态孵化） |
| 市值（as_of 2026-08-04） | ~$1.98B |
| 股东回报率 | ~5.0%（股息 5.0% + 回购 0%） |
| 置信度 | low |
| 数据源优先级 | 官方（APY 实测） > 估算 > 链上（质押收益采集待补） |

## 二、收入判定（核心）

**Boss 定稿口径：平台币赋能即收入，同 BNB；质押收益按 BNB asBNB 同口径计入**（2026-08-04 拍板）

```
收入 = MNT 原生质押 APY × 市值 ≈ 5.0% × $1.98B ≈ $99M/年
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| MNT 原生质押收益 | 原生质押已上线，stacky.fi 实测 ~5.0% APY（30% 供应质押 ≈ $647M），按 BNB asBNB 同口径计入 | stacky.fi / stakingcrypto.info 实测 |

| 不计入 | 原因 |
|---|---|
| sequencer fees | 进 BaseFeeVault 不自动 burn 给 MNT（与 BNB BEP-95 不同） |
| mETH 收益 | 归 mETH stakers + LSP + 节点运营商，与 MNT 持有人无关 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| MNT 原生质押收益（~5.0% APY） | `yield`（股息） | 5.0% |

- 股东回报合计 $99,061,566/年 ÷ 市值 ≈ **5.0%**（snapshot `shareholder_returns_usd_365d = $99.06M`，`shareholder_yield_percent = 5.0`，`payout_ratio = 1.0`）

## 四、关键计算逻辑（adapter.py）

`data/protocols/mnt/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `config.json` + `data/all-protocols.json`，取 `market_cap_usd`（≈ $1.98B）
2. `STAKING_APY = 0.05`（2026-08-04 stacky.fi 实测 ~5.0%，常量写死）
3. `staking_usd = STAKING_APY × mcap`（≈ $99.06M）；`total_rev = staking_usd`
4. 收入拆分：`burn_usd_365d = 0`、`staking_rewards_usd_365d = staking_usd`、launchpad 为 null
5. 毛利/净利 = 收入（平台币无 LP 成本模型，毛利率/净利率 = 100%，标注为非经营性利润）
6. `by_mechanism` 单条 yield 机制（$99.06M / 5.0%）
7. 派生估值：`pe = ps = mcap / staking_usd`（20.0）、`payout_ratio = 1.0`
8. verification：口径 = 质押收益（Boss 2026-08-04 拍板），status = estimated

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| MNT 原生质押 APY（stacky.fi 实测） | 季度复核（静态） | 无（静态维护） |
| 质押收益链上采集 | 上线后补 | 待补（补链上采集） |

## 六、历史验证与注意点

- **⚠️ 质押收益 = 持币人质押利息，非协议利润**：详情页须注记口径（赋能口径，非经营性收入）
- **sequencer fees 不流向 MNT**：Mantle v2 EIP-1559 风格 fee 进 BaseFeeVault，由 DAO 投票决定用途，与 BNB BEP-95 实时 burn 不同
- **mETH 收益独立**：Mantle LST 收益分给 mETH stakers + LSP + 节点运营商，不计入 MNT
- **Treasury Burn 提案未执行**：论坛讨论 3-8% 供应在 12-24 个月销毁的提案存在，未投票通过，当前 0 影响；若通过执行需重新评估
- **⚠️ 潜在稀释**：MNT 供应未锁定（总供应 62.2 亿 vs 流通 32.5 亿）；此前 staking 4-8% APY 来自新币发行（inflation）不算真 TEV，2026-08-04 改为按原生质押收益口径计入
- APY 为第三方实测估算，需季度复核（config 标 low confidence）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §2（MNT，Boss 2026-08-02 选 B + 2026-08-04 补质押收益）
- 配置文件：`data/protocols/mnt/config.json`（revenue_recognition 字段）
