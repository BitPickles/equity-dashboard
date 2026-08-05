"""审计6：daily 历史时间序列连续性

检查项：
- 26 协议 daily 文件完整性
- 月份文件连续性（断档检测）
- latest 数据有效性

注：详情页历史图读 data/history/（与 daily 月份文件不同），
本审计只检查 daily 是否有数据可用。
"""
import json
import os
from pathlib import Path
from datetime import datetime

print("=" * 78)
print("审计 6：daily 历史时间序列连续性")
print("=" * 78)
ap = json.load(open('data/all-protocols.json', encoding='utf-8'))
issues = []

for pid in sorted(ap['protocols']):
    dp = Path(f'data/daily/{pid}')
    if not dp.exists():
        issues.append((pid, '无 daily 目录'))
        continue
    months = sorted([f for f in os.listdir(dp) if f.endswith('.json')])
    if not months:
        issues.append((pid, 'daily 空'))
        continue
    latest_ok = 'latest.json' in months
    hist_months = [m.replace('.json', '') for m in months if m != 'latest.json']
    if not hist_months:
        issues.append((pid, f'只有 latest，无历史月份'))
        continue
    try:
        dates = [datetime.strptime(m, '%Y-%m') for m in hist_months]
        gaps = []
        for i in range(1, len(dates)):
            diff = (dates[i].year - dates[i-1].year) * 12 + (dates[i].month - dates[i-1].month)
            if diff > 1:
                gaps.append((hist_months[i-1], hist_months[i], diff - 1))
        if gaps:
            issues.append((pid, f'断档: {gaps[:3]}'))
    except Exception as e:
        issues.append((pid, f'解析失败: {str(e)[:40]}'))

    if latest_ok:
        try:
            d = json.load(open(dp / 'latest.json', encoding='utf-8'))
            lr = d.get('latest_record', {})
            if not lr.get('daily_fees_usd') and not lr.get('price_usd'):
                issues.append((pid, 'latest 无有效记录'))
        except Exception as e:
            issues.append((pid, f'latest 损坏: {str(e)[:30]}'))

for pid, msg in issues:
    print(f'⚠️ {pid}: {msg}')
print(f"\n共 {len(issues)} 个 daily 问题" if issues else "\n✅ 全部 daily 连续完整")