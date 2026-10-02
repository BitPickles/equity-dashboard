# TOOLS.md - Local Notes

## API Keys

⚠️ **所有 API Key 已迁移至 `~/.openclaw/.env`（权限 600），此处仅保留说明。**

### FRED API
- **用途**: 宏观原始数据（原 BMRI 指标输入；BMRI 已下线，现由 `scripts/fetch-indicators.py` 走免费 CSV 抓取，不再需要 key）
- **环境变量**: `FRED_API_KEY`

### Etherscan/BscScan API
- **邮箱**: zhengzhi2233@proton.me
- **支持网络**: BSC, ETH, Polygon, Arbitrum 等所有 EVM 网络
- **环境变量**: `ETHERSCAN_API_KEY`

### 飞书 API
- **Bot Name**: AI助手
- **Bot 日历 ID**: `feishu.cn_wOoFF5TmeeP8JUzmYGbQTh@group.calendar.feishu.cn`
- **Bot 日历名称**: 3D 小助理
- **共享日历 ID**: `feishu.cn_ZMyhp7l3djLaMxDPDoEy4a@group.calendar.feishu.cn`
- **共享日历名称**: Boss 日程（⚠️ 以后用这个创建日程）
- **环境变量**: `FEISHU_APP_ID`, `FEISHU_APP_SECRET`

### MiniMax API
- **用途**: MiniMax AI 模型调用
- **环境变量**: `MINIMAX_API_KEY`

## 日程管理

⚠️ **使用前先加载环境变量**: `source ~/.openclaw/.env`

### 获取 Token
```bash
source ~/.openclaw/.env
curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d "{\"app_id\": \"$FEISHU_APP_ID\", \"app_secret\": \"$FEISHU_APP_SECRET\"}"
```

### 查询日程
```bash
curl -s -X GET "https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events?start_time={unix}&end_time={unix}" \
  -H "Authorization: Bearer {token}"
```

### 创建日程
```bash
curl -s -X POST "https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"summary": "标题", "start_time": {"timestamp": "unix"}, "end_time": {"timestamp": "unix"}}'
```

### ⚠️ 重要：创建日程后必须添加 Boss 为参与者
```bash
curl -s -X POST "https://open.feishu.cn/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}/attendees?user_id_type=open_id" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"attendees": [{"type": "user", "user_id": "ou_028dcc071d235bbca2b2cf3fd75d44ba"}], "need_notification": true}'
```

## Boss 信息
- **飞书 Open ID**: `ou_028dcc071d235bbca2b2cf3fd75d44ba`
- **显示名称**: 郑植

## 工作记录存储

- **Boss 工作日志**: `~/clawd/memory/work-logs/YYYY-MM-DD.md`
- **员工汇报**: `~/clawd/memory/employee-reports/YYYY-MM-DD.md`

## 员工信息

| 姓名 | 职位 | 汇报频率 | 备注 |
|-----|-----|---------|-----|
| 李芳 | - | 工作日 | 汇报 Boss 日程完成情况 |

### 李芳
- **飞书 Open ID**: `ou_b1e4bd6c059774bf1f52fe6c19a0a9e8`
- **权限级别**: reporter（只能汇报，不能下指令）
- **汇报内容**: Boss 当日/昨日日程完成情况
- **汇报时间**: 工作日
