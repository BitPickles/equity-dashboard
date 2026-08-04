# JustLend — 协议口径判定书（内部文档）

> **内部资料，不对外展示**。本文件是接管 Agent 的快速上手手册：理解 JustLend 协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
> 最近更新：2026-08-04

---

## 一、协议档案

| 项 | 值 |
|---|---|
| 名称 / Ticker | JustLend / JST |
| 实体类型 | `application`（lending） |
| 市值（as_of 2026-08-04） | ~$851.6M |
| 股东回报率 | ~0%（股息 0% + 回购 0%） |
| 置信度 | low |
| 数据源优先级 | 链上（TRONGrid 核实）> 治理提案 > DefiLlama |

## 二、收入判定（核心）

**Boss 定稿口径：TEV = 0 —— 宣称 100% 净收入回购销毁，但链上核实为 pocket-to-pocket 做账式（金库转 Black Hole，无市场买入证据）**

```
净收入（365d）= DefiLlama interest spread ≈ $500k（照算）
股东回报 = 0（做账式销毁：孙宇晨金库 → executor → TRON Black Hole，无 USDT 市场买入证据）
```

| 计入项 | 说明 | 数据源 |
|---|---|---|
| 净收入（借贷利差 interest spread） | DefiLlama justlend slug 报 ~$500k/年，净收入照算 | DefiLlama |

| 不计入 | 原因 |
|---|---|
| 宣称的"100% 净收入回购销毁" | 链上核实为 pocket-to-pocket 做账式（金库转 Black Hole），非真市场 buyback，不计入股东回报 |

## 三、股东回报拆分

| 机制 | 类型 | 占比 |
|---|---|---|
| 宣称 100% 净收入回购销毁（链上核实做账式） | `buyback`（回购） | 0%（做账式销毁，确凿为 0） |

## 四、关键计算逻辑（adapter.py）

`data/protocols/justlend/adapter.py` → `build_snapshot(proto_dir)`：

1. 净收入照算：`revenue = $500,000`（DefiLlama interest spread，estimate）；毛利 = 收入（借贷利差无 LP 分润）
2. 读 `burn-history.json` / `all-protocols.json` 的 validation：累计 burn **1,604,586,131 JST**（2025-10 / 2026-01 / 2026-04 / 2026-07 共 4 次）
3. 链上核实 burn 源头：全部来自孙宇晨生态中央金库 `TFTWNgDBkQ5wQoP8RXpRznnHvAVV8x5jLu`（持 HTX 2623B + WIN 484M + TUSD + BTC 等），经 executor `TZJVQuU3CJqBScwoxhRtkxQ7JjsNNrpEag` → TRON Black Hole
4. 反向验证：无对应 USDT/USDD 流出换取 JST 的链上痕迹（真 buyback 特征缺失）→ 做账式销毁不创造市场买压、不减少实际流通量（销毁的 JST 本不在流通）
5. 股东回报确凿为 0（非 null）：by_mechanism `usd_365d=0`；burn 数据仅作供给侧记录，非 TEV 来源

## 五、数据管道（data_pipeline）

| 数据 | 频率 | 脚本 |
|---|---|---|
| 链上金库 → Black Hole 转账核验 | 季度 | （无脚本，手工 TRONGrid 核验） |

## 六、历史验证与注意点

- **⚠️ pocket-to-pocket 做账式销毁**：burn 的 JST 全部来自孙宇晨金库（TFTWNgDB...，持 HTX/WIN/TUSD 等孙宇晨生态代币），不是从市场用协议收入买入——对流通量和价格无实际支撑
- **⚠️ 无市场买入证据**：真 buyback 链上特征是 executor 拿 USDT/USDD → 去 DEX 换 JST → burn；观察到的是项目方金库直接转 JST → executor → Black Hole，无 USDT 对应流出
- **DefiLlama 侧面佐证**：justlend slug 只报 ~$500k/年 revenue（interest spread），远远撑不起官方声称的 $41.42M 储备 + 后续季度收入
- **TRON 生态透明度低**：JST staking 机制缺透明文档，无 Dune 等独立分析工具；DefiLlama 无 tokenRights 数据；与 Justin Sun 团队关联，中心化程度高
- **未来重新评估条件**：若链上观察到 executor 真正从市场买 JST（USDT 流出 + JST 流入配对），可重新评估
- tevStatus = `none`，tevRatio = null，各周期 TEV/Earning Yield 均 0%

## 七、判定书出处

- 判定书总表：`docs/protocol-revenue-recognition.md` §18
- 配置文件：`data/protocols/justlend/config.json`（revenue_recognition 字段）
- 数据维护说明：`data/protocols/justlend/README.md`（如有）
