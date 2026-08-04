# Uniswap — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 Uniswap 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | Uniswap / UNI |
| 实体类型 | `application`（dex） |
| 市值（as_of 2026-08-04） | ~$2.54B |
| 股东回报率 | ~0.72%（股息 0% + 回购销毁 0.72%） |
| 置信度 | high |
| 数据源优先级 | 链上（Etherscan 直查 0xdead / Firepit）> DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：收入 = 抽成手续费（容易计算）；收入基本全部用于回购（Firepit 销毁 UNI 🟢）**

```
收入 = 365d 链上 0xdead 累计 UNI × 当前价
    = 4,580,003 UNI × $4.01 = $18,365,812
回报率 = $18,365,812 ÷ 市值 $2.54B = 0.72%
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 抽成手续费（365d 0xdead 累计） | v2 协议费 0.05% 全池统一 / v3 1/4~1/6 of LP fee；fee switch 2025-12-28 开启后协议费 → TokenJar → Firepit → 0xdead 销毁 | 链上 Etherscan |

| 不计入 | 原因 |
|---|---|
| 一次性 1 亿 UNI 国库销毁 | 2025-12-27 Timelock 执行的 retroactive burn，属存量模拟操作（模拟 fee switch 从 genesis 开启），不计入 365d 股东回报 |
| Unichain Firepit 销毁 | 脚本只覆盖 Ethereum mainnet，Unichain 上 burn 未计入（M1 扩展） |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| Firepit 销毁 UNI（fee switch → TokenJar → 0xdead） | `destroy`（回购性质） | 0.72% |

## 四、关键计算逻辑（adapter.py）

`data/protocols/uniswap/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 all-protocols.json → `validation.burn_365d_uni`（365d UNI 转入 0xdead 累计 = 4,580,003 UNI，排除 ≥10M 一次性事件）
2. `burn_365d = burn_365d_uni × uni_price_usd`（$4.01）= $18,365,812
3. `burn_yield = burn_365d / mcap × 100% = 0.72%`
4. 毛利 = 收入（抽成手续费为协议净得，LP 分润已由各池自行结算）；无持续增发（UNI 总供应封顶 10 亿）
5. 净利 = 收入 = 股东回报（收入基本 100% 用于 Firepit 回购销毁）
6. 股东回报 by_mechanism = [{mechanism: "Firepit 销毁 UNI", type: "destroy", usd: $18,365,812, yield: 0.72%}]
7. 派生估值：pe = ps = mcap/burn = 138.4，payout_ratio = 1.0

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 链上：Etherscan 直查 0xdead / Firepit 合约地址 | 日频 | update-uniswap.py |
| DefiLlama dailyRevenue | 日频 | fetch-defillama.js |

## 六、历史验证与注意点

- **⚠️ Fee switch 开启史**：2025-12-28 UNIfication 提案生效，fee switch 开启 → TEV 从 0 变有值；2025-06 之前无 burn 数据（365d 窗口前半段实际为 0）
- **⚠️ 一次性 1 亿 UNI 销毁排除**：2025-12-27 Timelock（0x1a9c...35bc）执行，脚本自动识别单笔 ≥10M UNI 事件并排除
- **M0/M1 任务**：去链上找实际回购地址（Firepit 合约 / 0xdead 转账），核对 Firepit 合约地址与协议费流向；Unichain Firepit 销毁待扩展
- **from 地址分布复杂**：63 个不同地址（L2 桥代理、EOA 等），并非全部是 Firepit 合约；A 口径按「到 0xdead 即算 supply 收缩」处理
- **销毁路径**：协议费用 → TokenJar → Firepit 合约 → 0xdead，每次 release 阈值 2,000 UNI
- **短周期加速**：7d 年化 0.87% > 30d 0.69% > 365d 0.72%（近期销毁加速）

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §8（Boss 2026-08-02 定稿）
- 配置文件：`data/protocols/uniswap/config.json`（revenue_recognition 字段，tevRatio=1）
- 数据维护说明：`data/protocols/uniswap/README.md`（如有）
