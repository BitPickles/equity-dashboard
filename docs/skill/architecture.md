# 架构说明

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | 纯静态 HTML/CSS/JS（无框架） |
| 图表 | LightweightCharts v4 |
| 托管 | GitHub Pages |
| 数据 | JSON 文件（静态） |
| 更新 | Python/Node 脚本 + Cron |

## 为什么选择纯静态？
- **简单可靠** - 无服务器依赖，GitHub Pages 免费托管
- **快速加载** - 无 JS 框架开销
- **易于维护** - AI 可直接编辑 HTML/CSS
- **成本为零** - 无服务器费用

## 数据流

```
外部 API (CoinGecko/FRED/DefiLlama)
         ↓
   数据脚本 (scripts/)
         ↓
   JSON 文件 (indicators/data/)
         ↓
   前端页面 (fetch + 渲染)
```

## 共享数据层

所有指标共用的基础数据存放在 `indicators/data/shared/`：

| 文件 | 说明 | 更新频率 |
|------|------|----------|
| btc-price.json | BTC 历史价格 | 每日 |
| fred-macro.json | FRED 宏观数据 | 每日 |

### 原则
- **单一数据源** - BTC 价格只在一处维护
- **增量更新** - 历史数据持久化，只追加新数据
- **不重复获取** - 避免 API 调用浪费

## 页面类型与导航结构

### 页面层级
```
首页 (/)
├── 指标页面（独立工具）
│   ├── /mvrv/
│   ├── /ahr999/
│   ├── /bmri/
│   └── /btc-dominance/
└── TEV 专题（独立项目）
    ├── /tev/ (列表页)
    └── /equity/protocol.html (详情页)
```

### 1. 指标页面 (Indicator Pages)
- 路径: `/{indicator}/index.html`
- 结构统一，参见 [page-template.md](./page-template.md)
- 例: `/ahr999/`, `/bmri/`, `/mvrv/`
- **导航**: 只有「首页」

### 2. 首页 (Landing)
- 路径: `/index.html`
- 展示所有指标概览
- 导航入口

### 3. TEV 专题页
- 路径: `/tev/`
- 独立设计，不在通用模板范围内
- 有自己的数据和样式
- **导航规则**:
  - `/equity/index.html` (列表页): 只有「首页」
  - `/equity/protocol.html` (详情页): 「首页」+「TEV」

## 响应式设计

| 断点 | 说明 |
|------|------|
| > 1024px | 桌面端 |
| 768-1024px | 平板 |
| < 768px | 手机端 |

图表和卡片在移动端自动调整布局。

## 国际化 (i18n)

使用 `data-zh` / `data-en` 属性实现中英文切换：

```html
<span data-zh="抄底区" data-en="Bottom Zone">抄底区</span>
```

JS 通过 `LangUtils` 工具切换语言，存储在 localStorage。

## 性能考虑

- **图表懒加载** - 数据加载完成后才渲染
- **默认显示范围** - 不加载全部历史，默认从 2013/2014 开始
- **CSS 合并** - 共享样式在 common.css
- **JS 合并** - 共享工具在 chart-utils.js
