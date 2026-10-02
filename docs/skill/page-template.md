# 页面模板

## 指标页面结构

每个指标页面遵循统一的结构，确保用户体验一致。

### 布局层级（从上到下）

```
1. Header (导航栏)
2. 页面标题 + 副标题
3. 版本切换 (如有多版本)
4. 统计卡片 (主指标 + 子指标，横向排列)
5. Zone Legend (阈值说明)
6. 图表 (右下角显示数据更新时间)
7. 说明文档 (紧跟图表，不留大空白)
8. Footer
```

### 设计原则
- **图表优先**: 用户首屏应能看到图表
- **统计卡片在上**: 所有数值卡片放图表上方，横向排列
- **更新时间在图表内**: 不单独做卡片，放图表右下角
- **紧凑布局**: 图表下方不留大空白

## HTML 结构模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{指标名} — Crypto3D</title>
  <!-- Favicons -->
  <link rel="icon" type="image/x-icon" href="../favicon.ico">
  <!-- Fonts -->
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Noto+Sans+SC:wght@400;500;600;700&display=swap" rel="stylesheet">
  <!-- Styles -->
  <link rel="stylesheet" href="../indicators/css/common.css">
  <!-- Chart Library -->
  <script src="https://unpkg.com/lightweight-charts@4/dist/lightweight-charts.standalone.production.js"></script>
  <script src="../indicators/js/chart-utils.js"></script>
</head>
<body>
  <header>...</header>
  
  <main>
    <div class="container">
      <!-- Loading State -->
      <div id="loading" class="loading">...</div>
      
      <!-- Main Content -->
      <div id="content" style="display: none;">
        
        <!-- 1. 页面标题 -->
        <div class="page-header">
          <h1 class="page-title">{指标名}</h1>
          <p class="page-subtitle">{一句话说明}</p>
        </div>
        
        <!-- 2. 版本切换 (可选) -->
        <div class="version-tabs">...</div>
        
        <!-- 3. 核心指标卡片 -->
        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 12px;">
          <div class="stat-card">
            <div class="stat-label">{指标名}</div>
            <div class="stat-value" id="main-value">—</div>
            <div class="stat-hint" id="status">—</div>
          </div>
          <!-- Zone Legend -->
          <div class="zone-legend">...</div>
        </div>
        
        <!-- 4. 图表 -->
        <div class="chart-container">
          <div class="chart-header">
            <div class="chart-title">{指标名} 历史走势</div>
            <div class="chart-legend">...</div>
          </div>
          <div class="chart-wrapper" id="chart-container"></div>
          <div class="chart-tooltip floating" id="chart-tooltip">...</div>
          <div class="chart-hint">💡 拖动平移 · 滚轮缩放 · 双击重置</div>
        </div>
        
        <!-- 5. 详细数据卡片 (图表下方) -->
        <div style="display: flex; gap: 12px; margin: 16px 0 24px;">
          <div class="stat-card" style="flex: 1;">
            <div class="stat-label">{子指标1}</div>
            <div class="stat-value" id="sub-value-1">—</div>
          </div>
          <!-- 更多子指标... -->
          <div class="stat-card" style="flex: 0.6;">
            <div class="stat-label">数据更新</div>
            <div class="stat-value small" id="update-date">—</div>
          </div>
        </div>
        
        <!-- 6. 说明文档 -->
        <div class="info-section">
          <h2 class="info-title">💡 什么是 {指标名}？</h2>
          <div class="info-text">...</div>
        </div>
        
      </div>
    </div>
  </main>
  
  <footer>...</footer>
  
  <script>
    // Page-specific JavaScript
  </script>
</body>
</html>
```

## 核心指标卡片布局

### 简单指标 (如 AHR999)
```
┌─────────────┐
│ AHR999      │  + Zone Legend 横向排列
│ 0.82        │
│ 定投区      │
└─────────────┘
```

### 复合指标（多分桶）
```
┌─────────────┐
│ 指标名       │  + Zone Legend
│ 59.9        │
│ 🟡 Neutral  │
└─────────────┘

[图表]

┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ Rates  │ │ Liq    │ │ Risk   │ │ 更新   │
│ 61.40  │ │ 75.70  │ │ 39.70  │ │ 02-11  │
│ ▬▬▬▬   │ │ ▬▬▬▬   │ │ ▬▬▬▬   │ │        │
└────────┘ └────────┘ └────────┘ └────────┘
```

## 图表配置

### 默认显示范围
- 起始: 2013-01-01 或数据起始日期
- 结束: 最新日期 + 90天留白

### 交互
- 拖动平移
- 滚轮缩放
- 双击重置
- 悬停显示 Tooltip

## 说明文档区

每个指标页面底部应包含：
1. 指标定义和计算方法
2. 使用场景
3. 注意事项/免责声明

使用 `.info-section` 样式，支持中英文。
