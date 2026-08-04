# LayerZero — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 LayerZero 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | LayerZero / ZRO |
| 实体类型 | `application`（跨链基础设施） |
| 市值（as_of 2026-08-04） | ~$261.5M |
| 股东回报率 | ~0.30%（股息 0% + 回购 0.30%） |
| 置信度 | medium |
| 数据源优先级 | 链上（Stargate 回购）> 官方 > tokenomics.com > DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：协议本体消息费 0% take rate → 收入 = Stargate 收入（协议本体 0，标注 fee switch 未开启）**

```
收入（365d）= Stargate 收入 ≈ $3.07M（协议本体 0，fee switch OFF）
毛利 ≈ $0.78M（Stargate 收入中 $2.28M 流向 supply-side DVN/Executor 外包成本）
净利 ≈ $0.78M（极薄）
股东回报 = Stargate 回购 ZRO $0.78M（100% Stargate 收入）≈ 0.30%
稀释注记 ⚠️：每月解锁 ~$48M（2027 年中前持续）
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| Stargate 收入 | 2026-03 起 100% Stargate 收入回购 ZRO（累计 149.5 万 ZRO / $3.14M），链上可验证 | Etherscan（链上） |

| 不计入 | 原因 |
|---|---|
| 协议本体消息费 | 消息费 0% take rate（$3.59M 费用流向 DVN/Executor 外部节点，外包成本）；fee switch 未开启（半年公投多次未过） |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| Stargate 收入回购 ZRO（100%） | `buyback`（回购） | 0.30% |

## 四、关键计算逻辑（adapter.py）

`data/protocols/layerzero/adapter.py` → `build_snapshot(proto_dir)`：

1. 读 `all-protocols.json` 的 `metrics.trailing_365d_revenue_usd`（Stargate 收入 ≈ $3.07M）；协议本体 `protocol_fees_usd_365d = 0`（fee switch 未开启）
2. 优先复用 `financial_snapshot` 已验证毛利（2026-08-02 定稿）：`gross_profit ≈ $0.78M`；无值时按 `revenue × 0.2557` 估算；supply-side 外包成本（DVN/Executor）≈ $2.28M
3. 增发成本 treatment = `dilution_note`（无对价解锁，不算成本不扣减净利，但财报页强制展示）：每月解锁 ~$48M（2027 年中前持续），回购月 ~$150K 远不足以对冲
4. 净利 = 毛利 − 增发成本 0 − 运营成本（数据不可得）≈ $0.78M
5. 股东回报 = Stargate 回购 `trailing_365d_tev_usd ≈ $784,539`；`yield = 回购 / 市值 ≈ 0.30%`；verified: partial
6. 派生：毛利率 ~25.6%（supply-side 外包成本占比高）；P/E ≈ 333、P/S ≈ 85

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| Stargate 回购 ZRO 链上追踪 | 日频 | update-layerzero-tev.py |
| AI 监控费用开关公投（开启后收入端打开） | 事件驱动 | ai-watch-governance.py |

## 六、历史验证与注意点

- **🔍 AI 哨兵观察点**：**费用开关半年公投**——开启后收入端打开（$150B+ 年化跨链量 × bps），届时协议本体收入从 0 变为有值，需重新判定
- **⚠️ 稀释注记（treatment=dilution_note）**：每月解锁 ~$48M（2027 年中前持续）——无对价解锁，不算成本但**必须标注**（财报页强制展示）；回购月 ~$150K 远不足以对冲
- **协议本体收入 = 0 的原因**：TVL $7.5B、月跨链量 ~$140 亿（年化 $150B+），但消息费 0% take rate；$3.59M 费用流向 DVN/Executor 外部节点（外包成本）
- **毛利/净利极薄**：2026 gross $1.2M 中 $1.1M 给 supply-side，归协议 ≈ $0.1-0.5M
- **本质是"期权价值"标的**：当前股东回报率 ≈ 0.3-2%（极低），主要看未来费用开关开启后的潜在收入
- **DefiLlama 口径**：DefiLlama 的 "LayerZero V2" = 整个协议（协议版本号，非某个产品）；跨链量不产生收入
- Stargate 回购：2025-08 $110M 收购 Stargate；2026-03 起 100% Stargate 收入回购 ZRO

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §26
- 配置文件：`data/protocols/layerzero/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/layerzero/README.md`（如有）
