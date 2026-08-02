#!/usr/bin/env python3
"""
update-sky.py - Sky HoldersRevenue 数据更新脚本

数据源：DefiLlama dailyHoldersRevenue
用途：更新 tev-records.json
"""

import json
import datetime
import urllib.request
import sys

PROTOCOL_DIR = 'data/protocols/sky'
RECORDS_FILE = f'{PROTOCOL_DIR}/tev-records.json'

API_URL = 'https://api.llama.fi/summary/fees/sky?dataType=dailyHoldersRevenue'

def fetch_holders_revenue():
    """获取 DefiLlama HoldersRevenue 数据"""
    try:
        response = urllib.request.urlopen(API_URL)
        data = json.loads(response.read())
        chart = data.get('totalDataChart', [])
        return chart
    except Exception as e:
        print(f"  ✗ API 请求失败: {e}")
        return []

def update_records():
    """更新 tev-records.json"""
    chart = fetch_holders_revenue()
    if not chart:
        print("✗ 无数据，退出")
        return False
    
    # 获取最近 365 天
    last_365 = chart[-365:] if len(chart) >= 365 else chart
    
    # 按月分组聚合
    monthly = {}
    for ts, val in last_365:
        dt = datetime.datetime.utcfromtimestamp(ts)
        month_key = dt.strftime('%Y-%m')
        if month_key not in monthly:
            monthly[month_key] = []
        monthly[month_key].append((dt.day, val))
    
    # 生成月度记录
    records = []
    for month in sorted(monthly.keys()):
        days, values = zip(*monthly[month])
        total_usd = sum(values)
        num_days = len(days)
        record = {
            'id': f'sky-holders-{month}',
            'date': f'{month}-01',
            'type': 'holders_revenue',
            'mechanism': 'Smart Burn Engine + Staking Rewards',
            'amount_usd': total_usd,
            'period': month,
            'days_with_data': num_days,
            'source': {
                'type': 'api',
                'provider': 'DefiLlama',
                'endpoint': API_URL,
                'data_type': 'dailyHoldersRevenue',
                'methodology': 'SKY token buybacks + staking rewards (自动适配 burn 比例变化)'
            },
            'notes': f'Monthly aggregate from {num_days} days'
        }
        records.append(record)
    
    # 计算汇总
    total_tev = sum(r['amount_usd'] for r in records)
    total_30d = sum(v for ts, v in chart[-30:] if v)
    
    # 加载现有记录保留 metadata
    try:
        with open(RECORDS_FILE) as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = {'protocol': 'sky', 'records': []}
    
    # 更新
    existing['updated_at'] = datetime.datetime.utcnow().isoformat() + 'Z'
    existing['records'] = records
    existing['data_source'] = 'DefiLlama API (dailyHoldersRevenue)'
    existing['data_source_url'] = API_URL
    existing['protocol'] = 'sky'
    
    existing['summary'] = {
        'total_tev_usd': total_tev,
        'total_30d_usd': total_30d,
        'by_mechanism': {
            'holders_revenue': total_tev
        },
        'by_period': {
            f'{k[:4]}-Q{str(int(k[5:7])-1)}': sum(r['amount_usd'] for r in records if r['date'].startswith(k))
            for k in set([r['date'][:7] for r in records])
        }
    }
    
    # 保存
    with open(RECORDS_FILE, 'w') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    
    return True

def main():
    print('🔄 Sky HoldersRevenue 更新中...')
    
    if update_records():
        # 读取最新统计
        with open(RECORDS_FILE) as f:
            data = json.load(f)
        
        summary = data.get('summary', {})
        total_tev = summary.get('total_tev_usd', 0)
        total_30d = summary.get('total_30d_usd', 0)
        
        print(f'  ✅ TEV 365d: ${total_tev/1e6:.2f}M')
        print(f'  ✅ TEV 30d:  ${total_30d/1e6:.2f}M')
    else:
        print('  ✗ 更新失败')

if __name__ == '__main__':
    main()
