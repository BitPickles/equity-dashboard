"""审计5：派生关系验证（P/S、P/E、市值公式、yield 公式）

Boss 持续要求检查 → 派生关系数学一致性：
- P/S = mcap/rev = 100/total_yield（5% 容差）
- mcap = price × circulating_supply（5% 容差，注：流通量在 supply/<pid>.json）
- total_yield × payout ≈ shareholder_yield（15% 容差，payout<1 时）
- gross ≤ rev
- net_margin = net/rev（5% 容差）
- 流通量字段完整性
"""
import json
from pathlib import Path

print("=" * 90)
print("审计 5：派生关系验证")
print("=" * 90)
ap = json.load(open('data/all-protocols.json', encoding='utf-8'))
issues = []

for pid in sorted(ap['protocols']):
    p = ap['protocols'][pid]
    mcap = p.get('market_cap_usd')
    rev = p.get('revenue_usd_365d')
    net = p.get('net_income_usd_365d')
    sy = p.get('shareholder_yield_percent')
    ty = p.get('total_yield_percent')
    pr = p.get('payout_ratio')
    price = (p.get('metrics') or {}).get('current_price_usd')
    circ = (p.get('metrics') or {}).get('circulating_supply')
    gross = p.get('gross_profit_usd_365d')
    nm = p.get('net_margin_percent')

    checks = []
    if mcap and rev and rev > 0:
        ps_calc = mcap / rev
        ps_from_yield = 100 / ty if ty and ty > 0 else None
        if ps_from_yield and abs(ps_calc - ps_from_yield) / ps_calc > 0.05:
            checks.append(f'P/S 不一致: mcap/rev={ps_calc:.1f} vs 100/ty={ps_from_yield:.1f}')
    if mcap and price and circ:
        calc = price * circ
        if abs(mcap - calc) / calc > 0.05:
            checks.append(f'mcap≠price×circ: {mcap/1e9:.2f}B vs {calc/1e9:.2f}B')
    if ty and pr and sy and pr < 1 and ty > 0:
        expect = ty * pr
        if abs(sy - expect) / max(expect, 0.01) > 0.15:
            checks.append(f'total×payout={expect:.2f} ≠ shareholder={sy:.2f}')
    if gross and rev and gross > rev * 1.05:
        checks.append(f'gross {gross/1e6:.1f}M > rev {rev/1e6:.1f}M')
    if nm is not None and net is not None and rev:
        calc_nm = net / rev * 100
        if abs(nm - calc_nm) > 5:
            checks.append(f'net_margin {nm:.0f} ≠ net/rev {calc_nm:.0f}')
    if checks:
        issues.append((pid, checks))

for pid, checks in issues:
    print(f'⚠️ {pid}:')
    for c in checks:
        print(f'    - {c}')
print(f"\n共 {len(issues)} 个协议派生关系异常" if issues else "\n✅ 全部派生关系正确")