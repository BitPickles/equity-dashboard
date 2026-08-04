# Crypto3D Dashboard Skill

---
## ⚠️ 核心公式（不可更改）

| 指标 | 公式 | 数据口径 |
|-----|------|---------|
| **TEV** | 项目分配给代币持有者的价值（回购+分润+分代币） | **过去365天累计** |
| **Shareholder Yield** | `TEV ÷ 代币市值` | 年化 |
| **分配比例** | `TEV ÷ 协议利润(Revenue)` | 年化 |
| **收益率** | `协议利润(Revenue) ÷ 市值` | 年化 |

### 关键区分
- **Fees（收入）**: 协议产生的总手续费，含分给LP/存款用户的部分
- **Revenue（利润）**: 协议自己留下的收入，扣除LP分成后

### 数据来源
| 数据 | 来源 | 字段 |
|-----|------|------|
| 协议利润 | DefiLlama | `trailing_365d_revenue_usd` |
| 代币市值 | CMC / 交易所 API | `market_cap_usd` |
| TEV | **每个项目单独计算** | `trailing_365d_tev_usd` |

> **重要**：所有数据口径统一为「过去365天」，每个协议必须输出 `trailing_365d_tev_usd` 值。

---

## 概述
Crypto3D 数据看板网站的架构规范和开发指南。包含设计系统、页面模板、数据规范等。

## 触发场景
- 开发/修改 Crypto3D 网站页面
- 添加新指标页面
- 调整布局或样式
- 处理数据更新脚本

## 文件结构
```
skills/crypto3d-dashboard/
├── SKILL.md           # 本文件 - 入口
├── architecture.md    # 整体架构
├── design-system.md   # 设计规范
├── page-template.md   # 页面结构模板
├── data-spec.md       # 数据格式规范
└── components.md      # 通用组件
```

## 快速参考

### 代码仓库
- **工作目录**: `~/.openclaw/workspace-engineer/tev-dashboard/`
- **GitHub**: `https://github.com/BitPickles/tev-dashboard`
- **测试站**: `https://bitpickles.github.io/tev-dashboard`
- **正式站**: `https://crypto3d.pro`

### 分支策略
- `dev` - 开发分支，所有修改先提交到这里
- `main` - 生产分支，**需 Boss 批准才能合并**

### 目录结构
```
tev-dashboard/
├── index.html              # 首页
├── indicators/
│   ├── css/common.css      # 共享样式
│   ├── js/chart-utils.js   # 共享图表工具
│   └── data/
│       ├── shared/         # 共享数据（BTC价格、FRED宏观）
│       ├── ahr999.json
│       ├── bmri.json
│       ├── mvrv.json
│       └── btc-dominance.json
├── ahr999/index.html       # AHR999 指标页
├── bmri/index.html         # BMRI 指标页
├── mvrv/index.html         # MVRV 指标页
├── btc-dominance/index.html
├── tev/                    # TEV 页面（独立，不在重构范围）
└── scripts/                # 数据更新脚本
```

## 开发流程

1. **读取相关规范** - 先看 design-system.md 和 page-template.md
2. **在 dev 分支开发** - `git checkout dev`
3. **本地测试** - `python3 -m http.server 8765`
4. **提交推送** - 到 dev 分支
5. **验收** - 在测试站验证
6. **报告 Boss** - 等待批准后合并到 main

## 相关文档

### 通用规范
- [架构说明](./architecture.md)
- [设计系统](./design-system.md)
- [页面模板](./page-template.md)
- [数据规范](./data-spec.md)
- [TEV 数据层](./tev-data-layer.md) ← **回报口径合并逻辑**
- [组件说明](./components.md)
- [运营手册](./operations.md) ← **日常工作流程**
- [每日推文](./daily-tweet.md) ← **日常推特发布规范**

### 指标专属设计
- [AHR999](./indicators/ahr999.md) - 九神指标，定投时机判断
- [BMRI](./indicators/bmri.md) - 宏观风险指数，多版本切换
- [MVRV](./indicators/mvrv.md) - 链上估值，市值/已实现市值
- [BTC.D](./indicators/btc-dominance.md) - 市值占比，资金流向
