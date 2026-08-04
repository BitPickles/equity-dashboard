# JustLend TEV 数据维护说明

## 一、定性：TEV = 0（pocket-to-pocket 做账销毁）

JustLend DAO 2025-10 宣布 JST Buyback & Burn 机制，3 次执行累计销毁 1.356B JST (13.70% 供应)。

**但 2026-04-25 链上核实发现**：

- 所有 burn 的 JST 全部来自同一个上游地址 `TFTWNgDBkQ5wQoP8RXpRznnHvAVV8x5jLu`
- 该地址持仓：**HTX 2,623B（火币代币）+ WIN 484M（WINkLink）+ TUSD 15k** 等孙宇晨生态代币
- 这是**孙宇晨生态的中央金库**，不是协议的 SBM buyback 合约
- 没有观察到对应 USDT / USDD 流出（市场买入）的链上证据

**结论**：做账式销毁（pocket-to-pocket 转账），不是真 buyback。对流通量和价格无实际支撑。

所以 Shareholder Yield 各周期归零（`tevStatus=none`, `confidence=low`）。

---

## 二、数据保留策略

- **sync-tev-data.js justlend 分支**：Shareholder Yield = 0，但 `validation` 字段保留 7d/30d/90d/365d 的 burn 数量作为"供给侧事实"记录
- **update-justlend-tev.py**：仍然每日跑（监控新 burn 事件），数据写到 `burn-history.json`
- **tev-records.json**：保留（详情页历史图可展示 burn 事件存在这一事实）
- 如果未来链上观察到 executor 真正从市场买 JST（USDT 流出 + JST 流入配对），可重新评估

---

## 三、关键地址（TronScan 可查）

| 角色 | 地址 |
|---|---|
| JST (TRC-20) | `TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9` |
| TRON Black Hole（burn 目的地）| `T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb` |
| Burn Executor | `TZJVQuU3CJqBScwoxhRtkxQ7JjsNNrpEag` |
| **孙宇晨生态金库（JST 真实来源）** | `TFTWNgDBkQ5wQoP8RXpRznnHvAVV8x5jLu` |

---

## 四、3 次 burn 事件（链上已验证）

| Burn | 日期 | JST | 官方公告 USD |
|------|------|-----|--------------|
| #1 | 2025-10-19 | 559.89M | ~17.7M USD |
| #2 | 2026-01-14 | 525.00M | ~21.0M USD |
| #3 | 2026-04-15 | 271.34M | ~21.3M USD |

累计 **1,356,228,332 JST = 13.70%** of 9.9B supply。Black Hole 当前持仓精确吻合。

---

## 五、历史变更

- **2026-04-25**（Boss 决策）：链上复核发现 pocket-to-pocket 做账销毁 → TEV 归零
- **2026-04-24**：初版按 A 口径算出 365d Shareholder Yield = 15.88%（后被推翻）
- **2025-10-22**：JustLend DAO 治理通过 JST Buyback & Burn Program

---

## 六、为什么还保留监控脚本

即使 TEV = 0，我们仍然：
1. 保留 `update-justlend-tev.py` 每日跑——监控新 burn 事件 + 持续观察上游地址
2. `tev-records.json` 保留 3 次 burn 记录——详情页可展示事实
3. 将来如果链上出现真实 USDT → JST 市场买入证据（例如 executor 开始从 SunSwap 等 DEX 买入），立即重新评估

**对孙宇晨生态的项目，链上监控比白皮书可信。**
