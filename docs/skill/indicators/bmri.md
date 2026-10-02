# BMRI 指标设计

## 指标概述

| 属性 | 值 |
|------|-----|
| 名称 | BMRI (Bitcoin Macro Risk Index) |
| 路径 | `/bmri/index.html` |
| 数据 | `indicators/data/bmri.json` |
| 用途 | 宏观风险评估，判断宏观环境对 BTC 的友好程度 |

## 核心逻辑

BMRI 综合三个宏观维度评估市场环境：
- **低 BMRI** = 宏观友好 (Risk-On)
- **高 BMRI** = 宏观恶化 (Risk-Off)

## 三大组成部分 (Buckets)

### Rates 桶 (利率) - 权重 35%
| 指标 | FRED Code | 说明 | 方向 |
|------|-----------|------|------|
| 10年期国债 | DGS10 | 名义利率 | 高=风险↑ |
| 10年期 TIPS | DFII10 | 实际利率 | 高=风险↑ |

### Liquidity 桶 (流动性) - 权重 35%
| 指标 | FRED Code | 说明 | 方向 |
|------|-----------|------|------|
| Fed 资产负债表 | WALCL | 流动性投放 | 高=风险↓ |
| 美元指数 | DTWEXBGS | 美元强弱 | 高=风险↑ |

### Risk 桶 (风险偏好) - 权重 30%
| 指标 | FRED Code | 说明 | 方向 |
|------|-----------|------|------|
| VIX | VIXCLS | 恐慌指数 | 高=风险↑ |
| 高收益债利差 | BAMLH0A0HYM2 | 信用风险 | 高=风险↑ |

## 版本差异

| 版本 | 阈值 | 数据频率 | 适用场景 |
|------|------|----------|----------|
| **6M 版** | on=20, off=80 | 周数据 | 中周期趋势，1-6月调仓 |
| **1M 版** | on=25, off=75 | 日数据 | 短期冲击，1-4周调仓 |

默认显示 6M 版。

## 状态区间

| BMRI 范围 | 状态 | 颜色 | 含义 |
|-----------|------|------|------|
| < threshold.on | RISK_ON | 🟢 绿色 | 宏观友好，适合持有 |
| threshold.on ~ off | NEUTRAL | 🟡 黄色 | 中性，维持配置 |
| > threshold.off | RISK_OFF | 🔴 红色 | 宏观恶化，考虑减仓 |

## 页面特有元素

### 版本切换 Tab
```
┌──────────────┐ ┌──────────────┐
│ 6M 版        │ │ 1M 版        │
│ 中周期趋势    │ │ 短期冲击      │
└──────────────┘ └──────────────┘
```
点击切换版本，图表和数据同步更新。

### 统计卡片 (图表上方，横向排列)
```
┌────────────────────────────────────────┐ ┌─────────┐ ┌───────────┐ ┌─────────┐
│  BMRI                                  │ │  Rates  │ │ Liquidity │ │  Risk   │
│  59.9                                  │ │  61.40  │ │   75.70   │ │  39.70  │
│  🟡 Neutral：宏观环境中性，维持现有配置  │ │  ▬▬▬▬   │ │   ▬▬▬▬    │ │  ▬▬▬▬   │
└────────────────────────────────────────┘ └─────────┘ └───────────┘ └─────────┘
```

**BMRI 卡片状态显示：**
- 🟢 Risk-On：宏观环境友好，适合持有或加仓
- 🟡 Neutral：宏观环境中性，维持现有配置
- 🔴 Risk-Off：宏观环境恶化，考虑减仓或对冲

**布局原则：**
- 所有数值卡片放在图表上方
- BMRI 卡片直接显示完整状态描述（emoji + 建议）
- 不需要单独的 Zone Legend
- 数据更新时间在图表右下角显示（不单独做卡片）
- 桶数值显示：0-100，进度条（≤50 绿色, >50 红色）

## 图表配置

### 系列
| 名称 | 颜色 | 默认显示 | Y 轴 | 坐标模式 | 数据来源 |
|------|------|----------|------|-------|--------|
| BMRI | #3b82f6 (蓝) | ✅ | 右轴 | 对数 | bmri.json |
| Rates | #06b6d4 (青) | ❌ | 右轴 | 对数 | bmri.json |
| Liquidity | #22c55e (绿) | ❌ | 右轴 | 对数 | bmri.json |
| Risk | #f59e0b (琥珀) | ❌ | 右轴 | 对数 | bmri.json |
| BTC 价格 | #f59e0b (橙) | ❌ | 左轴 | 对数 | shared/btc-price.json |
| 加密总市值 | #8b5cf6 (紫) | ❌ | 左轴 | 对数 | 动态计算 |

**交互：**
- 点击图例可显示/隐藏 Rates / Liquidity / Risk 子指标
- 点击图例可显示/隐藏 BTC 价格
- 点击图例可显示/隐藏 加密总市值
- 子指标显示时，BMRI 区域背景保持不变
- BTC 价格/加密总市值显示时，左 Y 轴自动显示

**计算说明：**
- 加密总市值 = BTC 市值 / (BTC.D 指标 / 100)
- 当 BTC.D = 50% 时，加密总市值 = BTC 市值 / 0.5 = 2 × BTC 市值
- 当 BTC.D = 60% 时，加密总市值 = BTC 市值 / 0.6 ≈ 1.67 × BTC 市值

### 阈值线
- Risk-On 阈值：绿色虚线
- Risk-Off 阈值：红色虚线
- 零线/50线：灰色半透明

### 区域填充
- < threshold.on：绿色半透明
- > threshold.off：红色半透明

## 数据格式

```json
{
  "updated_at": "2026-02-12",
  "1m": {
    "current": {
      "value": 59.9,
      "date": "2026-02-11",
      "rates": 61.4,
      "liq": 75.7,
      "risk": 39.7,
      "regime": "NEUTRAL"
    },
    "thresholds": {"on": 25, "off": 75},
    "history": [...]
  },
  "6m": {
    "current": {...},
    "thresholds": {"on": 20, "off": 80},
    "history": [...]
  }
}
```

## 切换版本 JS 逻辑

```javascript
function switchVersion(version) {
  currentVersion = version;
  // 更新 Tab 激活状态
  // 调用 updateDisplay() 刷新数据和图表
}
```

## 说明文档内容

1. 什么是 BMRI
2. 三大组成部分详解
3. 1M vs 6M 版本对比
4. 使用建议

## 特殊注意

- BMRI 数据范围是 0-100（非 -1 到 +1）
- 进度条中点是 50
- 版本切换时阈值线位置会变化
- FRED 数据非实时，有 1-2 天延迟

## ⚠️ 生成链路现状（2026-10-02 复核）

**线上 `bmri.json` 在仓库内没有可复现的生成器。**

- 线上序列实测：`1m` 4040 条（2015-07-20 ~ 2026-08-10，**日频日历网格** + 前向填充）；`6m` 675 条（**同一条序列**按每 6 天抽样，值完全一致）；两者 `thresholds` 均为 `{on: 30, off: 70}`。
- ⚠️ 与上面「版本差异」表**不一致**：文档写的是 6M `on=20/off=80`、1M `on=25/off=75`（设计稿口径）。前端直接读 JSON 里的 `thresholds`，所以线上实际按 **30/70** 渲染。
- `scripts/recalc-bmri.py` / `recalc-bmri-fast.py` 都**复现不出**线上序列：用 `shared/fred-macro.json` 复算，百分位法 MAE ≈ 15、minmax 法 MAE ≈ 11；再暴力遍历 64 种「方向（invert）」组合、窗口 180~1825 天，最优仍有 MAE ≈ 11 → 原生成器使用了这 6 条 FRED 序列**之外的输入**（很可能还有 M2 / CPI 等）。
- 原生成器位于 **openclaw operator 链路**（`~/.openclaw/workspace-operator/`，走 FRED API key），**不在本仓库**。
- **处置**：恢复该链路前，`bmri.json` 视为**只读**；**禁止**用 `recalc-bmri.py` 覆盖线上文件——那会把 2015 年以来的历史整体换成另一条序列（静默改写 11 年数据）。页面 `updated_at` 目前如实显示 2026-08-10。

## Bug 修复记录 (2026-02)

### 字段名匹配问题
**问题**: btcPrice 数据映射使用 `d.date` 而非 `d.time`，cryptoTotalMcap 使用 `d.btc_mcap` 而非 `d.value`

**修复**: 统一使用正确的字段名
```javascript
// BTC Price - 使用 shared/btc-price.json
const btcPriceChartData = btcPriceData.history.map(d => ({
  time: d.date,
  value: d.price
}))

// Crypto Total MCap - 使用 marketcap.json
const cryptoTotalMcapData = marketcapData
  .filter(d => d.total_mcap)
  .map(d => ({ time: d.date, value: d.total_mcap }))
```

### 日期范围解耦
**问题**: BTC 价格线受限于 BMRI 数据范围，无法显示更早的历史数据

**修复**: BTC 价格数据独立于 BMRI 数据加载和渲染
- BTC 价格使用 `shared/btc-price.json`（数据从 2010-07-18 开始）
- 图表默认范围设为 2014-01-01 起
- 左轴价格轴仅在 btcPrice 或 cryptoTotalMcap 可见时显示

### 数据可用范围
| 数据文件 | 起始日期 |
|----------|----------|
| btc-price.json | 2010-07-18 |
| bmri.json | 2015-07-20 |
| marketcap.json | 2019-10-25 |

⚠️ `marketcap.json` 只有 2019 年后的数据，无法显示更早的加密总市值
