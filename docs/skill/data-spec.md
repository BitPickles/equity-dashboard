# 数据规范

## 目录结构

```
indicators/data/
├── shared/                    # 共享数据
│   ├── btc-price.json        # BTC 价格历史
│   └── fred-macro.json       # FRED 宏观数据
├── ahr999.json               # AHR999 指标数据
├── mvrv.json                 # MVRV 指标数据
└── btc-dominance.json        # BTC 市值占比数据
```

## 共享数据

### btc-price.json
所有指标共用的 BTC 价格数据源。

```json
{
  "updated_at": "2026-02-12",
  "source": "coingecko/glassnode",
  "history": [
    {"date": "2010-07-18", "price": 0.09},
    {"date": "2010-07-19", "price": 0.08},
    ...
  ]
}
```

**规则：**
- 单一数据源，其他指标引用此文件获取 BTC 价格
- 历史数据从 2010-07-18 开始
- 每日更新，追加新数据

### fred-macro.json
FRED 宏观经济原始数据。原为 BMRI 指标的输入；BMRI 已于 2026-10-03 下线，此文件目前无页面消费，仅作原始数据保留。

```json
{
  "updated_at": "2026-02-12",
  "series": {
    "DGS10": {"2013-01-02": 1.86, "2013-01-03": 1.91, ...},
    "VIXCLS": {"2013-01-02": 14.68, ...},
    ...
  }
}
```

## 指标数据格式

### 通用结构
```json
{
  "updated_at": "2026-02-12",
  "current": { ... },          // 当前值
  "history": [ ... ]           // 历史数据
}
```

### AHR999
```json
{
  "updated_at": "2026-02-12",
  "current": {
    "date": "2026-02-12",
    "value": 0.82,
    "price": 68500,
    "cost_200d": 72000,
    "fitted_price": 85000,
    "status": "定投区"
  },
  "history": [
    {
      "date": "2011-02-03",
      "close": 0.89,
      "ahr999": 0.42,
      "cost_200d": 0.85,
      "fitted_price": 0.12
    },
    ...
  ]
}
```

**状态判断：**
- `value < 0.45` → "抄底区"
- `0.45 <= value <= 1.2` → "定投区"
- `value > 1.2` → "观望区"

### MVRV
```json
{
  "updated_at": "2026-02-12",
  "current": {
    "date": "2026-02-10",
    "value": 2.15,
    "btc_price": 68688
  },
  "history": [
    {"date": "2010-07-18", "value": 146.04, "btc_price": 0.09},
    ...
  ]
}
```

### BTC Dominance
```json
{
  "updated_at": "2026-02-12",
  "current": {
    "date": "2026-02-08",
    "value": 54.2
  },
  "history": [
    {"date": "2014-01-01", "value": 95.2},
    ...
  ]
}
```

## 数据更新规则

### 更新频率
| 数据 | 频率 | 来源 |
|------|------|------|
| BTC 价格 | 每日 | CoinGecko/Binance |
| FRED 宏观 | 每日 | FRED API |
| AHR999 | 每日 | 计算 (依赖 BTC 价格) |
| MVRV | 每日 | Glassnode/计算 |

### 增量更新
- **不要**每次重新获取全部历史
- 只获取新数据，追加到 history 数组末尾
- 更新 `updated_at` 和 `current`

### 数据脚本
位于 `scripts/` 目录：
- `fetch-indicators.py` - 指标板块统一更新（btc-price / fred-macro / ahr999 / marketcap / btc-dominance / mvrv）
- ⚠️ BMRI 指标已于 2026-10-03 下线（口径不合格）：页面、导航、`indicators/data/bmri.json` 与全部相关脚本均已移除，原 /bmri 链接 301 到首页
- 其他...

## 日期格式

统一使用 ISO 格式：`YYYY-MM-DD`

```json
"date": "2026-02-12"
```

## 数值精度

| 类型 | 精度 |
|------|------|
| 价格 (USD) | 2 位小数 |
| 百分比 | 1-2 位小数 |
| 指标值 | 2-4 位小数 |
