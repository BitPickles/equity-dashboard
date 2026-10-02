# 每日数据播报推文规则

## 发布时间

- 早：09:30（数据自检后）
- 晚：21:30（数据自检后）

## 推文结构

```
📊 Crypto3D 加密数据站 | 每日复盘 YYYY-MM-DD

**AHR999: X.XX**
[数据解读 + 历史对比]

**MVRV: X.XX**
[数据解读 + 历史对比]

**BTC.D: XX.X%**
[数据解读]

💡 **周期视角**：[基于 BTC 价格波动 + 多指标联动的周期分析]

📈 crypto3d.pro

🤖 本条由 AI 运营助手自动生成，仅供参考，不构成投资建议。
```

> **注意**：BTC 价格不写入推文，但编辑时需根据价格波动分析市场周期。

## 内容规则

### 必须包含

| 项目 | 说明 |
|-----|------|
| 三大指标 | AHR999 → MVRV → BTC.D |
| 历史对比 | 引用历史相似时期的数据 |
| 周期视角 | 基于 BTC 价格波动 + 多指标交叉解读 |
| 网站链接 | crypto3d.pro |
| AI 声明 | 自动生成 + 非投资建议 |

> **BTC 价格**：不写入推文，但编辑时需参考价格波动来分析周期

### 情绪共情

- 下跌时：承认恐惧，不说"抄底机会"
- 上涨时：提醒风险，不说"牛市来了"
- 震荡时：保持客观，不强行解读

### 数据真实性（最高优先级）

- ⚠️ **所有陈述必须有数据支持，不能瞎编**
- ⚠️ 只能使用本站实际拥有的指标数据
- ⚠️ 不能编造"链上数据显示..."等无法验证的说法
- ⚠️ 历史对比必须基于真实历史数据

### 禁止用词

- ❌ 抄底、满仓、暴涨、牛市确认
- ❌ 绝对底部、不会再跌、最后机会
- ❌ 财富密码、百倍币、一定要买
- ❌ 编造没有数据支持的市场描述

### 鼓励用词

- ✅ 历史数据显示、统计上看
- ✅ 分批布局、保持纪律
- ✅ 仅供参考、不构成建议
- ✅ 低估可以持续、不猜拐点

## 指标解读参考

### AHR999

| 区间 | 含义 |
|-----|------|
| < 0.45 | 定投区间（历史约 10%） |
| 0.45 - 1.2 | 正常波动 |
| > 1.2 | 偏贵，谨慎 |

### MVRV

| 区间 | 含义 |
|-----|------|
| < 1.0 | 低于全网成本，深度低估 |
| 1.0 - 2.0 | 合理区间 |
| > 3.0 | 过热，历史顶部区域 |

### BTC.D

| 区间 | 含义 |
|-----|------|
| > 60% | BTC 主导，山寨弱势 |
| 50-60% | 均衡 |
| < 50% | 山寨季，风险加大 |

## 数据获取

```python
# AHR999 + BTC价格
indicators/data/ahr999.json → history[-1]
  - close: BTC价格
  - ahr999: 指标值
  - cost_200d: 200日成本
  - fitted_price: 拟合价格

# MVRV
indicators/data/mvrv.json → history[-1]
  - mvrv: 指标值

# BTC.D
indicators/data/btc-dominance.json → history[-1]
  - value: 占比
```

## 发布工具

### bird CLI（推荐）

```bash
# 检查登录状态
bird --chrome-profile "Default" whoami
# 输出示例：🙋 @22333D (3D 加密频道)

# 发送推文
bird --chrome-profile "Default" tweet '推文内容'

# 发送带图片的推文
bird --chrome-profile "Default" --media /path/to/image.png tweet '推文内容'
```

### 发推流程

1. **获取数据**
   ```bash
   cd ~/.openclaw/workspace-engineer/tev-dashboard
   cat indicators/data/ahr999.json | jq '.history[-1]'
   cat indicators/data/mvrv.json | jq '.history[-1]'
   cat indicators/data/btc-dominance.json | jq '.history[-1]'
   ```

2. **编写推文**（按模板，基于真实数据）

3. **检查字符数**
   - Twitter 限制：280 字符（中文约 140 字）
   - 如果超长：考虑发 thread（多条推文）或精简

4. **发布**
   ```bash
   bird --chrome-profile "Default" tweet '内容'
   ```

5. **确认发布成功**
   - 检查返回的链接
   - 必要时在浏览器验证

### 发 Thread（长内容）

```bash
# 先发第一条
bird --chrome-profile "Default" tweet '第一条内容'
# 记下返回的 tweet ID

# 回复形成 thread
bird --chrome-profile "Default" reply <tweet-id> '第二条内容'
```

### 常见问题

| 问题 | 解决方案 |
|-----|---------|
| Chrome cookies 找不到 | 确认 Chrome 已登录 x.com，profile 名称用 "Default" |
| 推文太长 | 精简内容或发 thread |
| Safari cookies 权限错误 | 忽略，只要 Chrome 能用就行 |

## 更新日志

- 2026-02-15: 创建规则
- 2026-02-15: 新增数据真实性要求（不能瞎编）
- 2026-02-15: 新增 bird CLI 完整发布流程
