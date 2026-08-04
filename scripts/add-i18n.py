#!/usr/bin/env python3
"""Batch add data-zh/data-en attributes to all HTML files"""
import re, os, glob

# Master translation dictionary
TRANSLATIONS = {
    # Common
    "详情": "Details",
    "7日": "7D",
    "返回": "Back",
    "加载中": "Loading",
    "更新时间": "Updated",
    "数据来源": "Data Source",
    "关于": "About",
    "指标说明": "About This Indicator",
    "计算公式": "Formula",
    "区间说明": "Zone Guide",
    "数据源": "Data Source",
    "历史走势": "Historical Trend",
    "当前值": "Current Value",
    "最新数据": "Latest Data",
    "日期范围": "Date Range",
    "全部": "All",
    "近一年": "1 Year",
    "近半年": "6 Months",
    "近三月": "3 Months",
    "近一月": "1 Month",
    
    # Navigation
    "首页": "Home",
    "BTC 周期": "BTC Cycle",
    "宏观风险": "Macro Risk",
    "切换主题": "Toggle Theme",
    
    # Hero
    "总市值": "Total Market Cap",
    "24h 成交量": "24h Volume",
    "BTC 占比": "BTC Dominance",
    
    # TEV Section
    "协议估值": "Protocol Valuation",
    "覆盖协议": "Protocols",
    "治理监控": "Governance",
    "查看完整排名 →": "View Full Rankings →",
    "治理动态": "Governance Feed",
    "进行中": "Active",
    "已通过": "Passed",
    "已结束": "Ended",
    "投票中": "Voting",
    "讨论中": "Discussion",
    "投票截止": "Vote Ends",
    "支持率": "Approval",
    "阶段": "Phase",
    "温度检查": "Temp Check",
    "论坛回复": "Forum Replies",
    "通过日期": "Pass Date",
    "投票率": "Turnout",
    
    # BTC Cycle
    "抄底区": "Buy Zone",
    "定投区": "DCA Zone",
    "过热区": "Overheat",
    "合理区": "Fair Zone",
    "低估区": "Undervalued",
    "平衡": "Balanced",
    "BTC主导": "BTC Dominant",
    "山寨季": "Alt Season",
    
    # Macro Risk
    "中性": "Neutral",
    "低风险": "Low Risk",
    "高风险": "High Risk",
    "10Y 美债": "10Y Treasury",
    "全球 M2": "Global M2",
    
    # Stats
    "市场周期指标": "Cycle Indicators",
    "链上数据驱动": "On-chain Driven",
    
    # AHR999
    "九神指标": "AHR999 Index",
    "定投时机参考": "DCA Timing Reference",
    "当 AHR999": "When AHR999",
    "时，适合抄底": ", buy zone",
    "时，适合定投": ", DCA zone",
    "时，等待时机": ", wait zone",
    
    # MVRV
    "链上估值指标": "On-chain Valuation",
    "市场价值与实现价值比率": "Market Value to Realized Value Ratio",
    
    # BMRI
    "宏观风险指数": "Macro Risk Index",
    "综合评分": "Composite Score",
    "利率因子": "Rate Factor",
    "流动性因子": "Liquidity Factor",
    "风险因子": "Risk Factor",
    "子指标": "Sub-indicators",
    "版本": "Version",
    "版本说明": "Version Notes",
    "计算方法": "Methodology",
    "权重": "Weight",
    "得分": "Score",
    "标准化": "Normalized",
    "原始值": "Raw Value",
    "美债利率": "Treasury Rate",
    "全球流动性": "Global Liquidity",
    "风险偏好": "Risk Appetite",
    "美元指数": "Dollar Index",
    "信用利差": "Credit Spread",
    "波动率指数": "Volatility Index",
    
    # BTC.D
    "BTC 市值占比": "BTC Market Dominance",
    "资金流向": "Capital Flow",
    "资金流向指标": "Capital Flow Indicator",
    
    # TEV pages
    "协议": "Protocol",
    "代币": "Token",
    "市值": "Market Cap",
    "年收入": "Annual Revenue",
    "年 TEV": "Annual TEV",
    "分配比例": "Distribution Ratio",
    "收益率": "Earning Yield",
    "机制": "Mechanism",
    "回购": "Buyback",
    "销毁": "Burn",
    "分红": "Dividend",
    "质押奖励": "Staking Reward",
    "置信度": "Confidence",
    "高": "High",
    "中": "Medium",
    "低": "Low",
    "无": "None",
    "数据说明": "Data Notes",
    "TEV 机制说明": "TEV Mechanism",
    "历史记录": "History",
    "排名": "Rank",
    "类别": "Category",
    "借贷": "Lending",
    "永续合约": "Perpetuals",
    "去中心化交易所": "DEX",
    "收益聚合": "Yield",
    "流动性质押": "Liquid Staking",
    "再质押": "Restaking",
    "稳定币": "Stablecoin",
    "全部协议": "All Protocols",
    "仅 Active": "Active Only",
    "按 Yield 排序": "Sort by Yield",
    "按市值排序": "Sort by Market Cap",
    "治理提案": "Governance Proposals",
    "治理概况": "Governance Overview",
    "活跃提案": "Active Proposals",
    "TEV 相关": "TEV Related",
    "最新提案": "Latest Proposals",
    "提案详情": "Proposal Details",
    "投票结果": "Voting Results",
    "赞成": "For",
    "反对": "Against",
    "弃权": "Abstain",
    
    # Footer
    "数据仅供参考，不构成投资建议": "Data for reference only, not investment advice",
    "由": "by",
}

def add_i18n(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    count = 0
    
    # Sort by length descending to match longer phrases first
    sorted_items = sorted(TRANSLATIONS.items(), key=lambda x: -len(x[0]))
    
    for zh, en in sorted_items:
        # Pattern: >Chinese text< (inside HTML tags, not already translated)
        # Avoid matching inside attributes or already-translated elements
        pattern = r'(?<!data-zh=")(?<!data-en=")>' + re.escape(zh) + r'<'
        
        def replacer(m):
            # Check if this element already has data-zh
            # Look backwards to find the opening tag
            pos = m.start()
            before = content[max(0, pos-200):pos]
            if 'data-zh=' in before.split('>')[-1] if '>' in before else before:
                return m.group()
            return f' data-zh="{zh}" data-en="{en}">{zh}<'
        
        new_content = re.sub(pattern, replacer, content)
        if new_content != content:
            diff = len(re.findall(pattern, content)) - len(re.findall(pattern, new_content))
            count += max(0, diff) or (1 if new_content != content else 0)
            content = new_content
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
    
    # Count final data-zh
    final_count = len(re.findall(r'data-zh=', content))
    return final_count

# Process all HTML files
files = [
    'index.html',
    'ahr999/index.html',
    'mvrv/index.html', 
    'bmri/index.html',
    'btc-dominance/index.html',
    'equity/index.html',
    'equity/protocol.html',
    'governance/index.html',
    'governance/proposals.html',
    'governance/protocol.html',
]

for f in files:
    if os.path.exists(f):
        count = add_i18n(f)
        print(f'{f}: {count} data-zh attributes')
    else:
        print(f'{f}: NOT FOUND')
