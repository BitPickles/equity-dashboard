#!/usr/bin/env python3
"""
M0 一次性脚本：为 26 个协议 config.json 补齐 revenue_recognition + data_pipeline
（按 docs/protocol-revenue-recognition.md 判定书总表，2026-08-02 定稿）

用法: python3 scripts/backfill-data-pipeline.py [--dry-run]
"""
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data" / "protocols"
DRY = "--dry-run" in sys.argv

# 判定书总表 → (entity_type, revenue_recognition, data_pipeline)
# 实体类型: platform_token=平台币 / app=应用型
PLAN = {
    "aave": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "所有计算用净利润：收入 ≠ 总协议费，扣除给 LP 的部分才是协议净利润",
            "revenue_included": {"protocol_fees": {"note": "DefiLlama dailyRevenue（协议归属/净），非 dailyFees"}},
            "revenue_excluded": {},
            "calculation": {"revenue_usd_365d": "DefiLlama dailyRevenue 365d 累加"},
            "source_type": "official",
            "source_url": "https://app.aave.com/governance",
        },
        "dp": {
            "sources": [
                {"type": "official", "method": "AI 抓治理提案/月报（回购金额变化）", "frequency": "event", "script": "ai-watch-governance.py"},
                {"type": "defillama", "method": "dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "cross-validation", "freshness"],
        },
    },
    "aster": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "只计流向流通持币人的价值流；1:1 储备销毁（未流通）不计入股东回报",
            "revenue_included": {"platform_fees": {"note": "平台手续费（DefiLlama dailyRevenue）"}},
            "revenue_excluded": {"reserve_burn": {"note": "1:1 储备销毁烧的是未流通储备币，只减少未来潜在稀释，不作股东回报（198% 为营销话术）"}},
            "calculation": {"tev_ratio": 0.99, "note": "99% 手续费回购给质押者（TWAP 回购 ASTER → veASTER）"},
            "source_type": "chain",
            "source_url": "https://www.asterdex.com",
        },
        "dp": {
            "sources": [
                {"type": "chain", "method": "新回购钱包 + 1:1 销毁记录（2026-06-17 后机制）", "frequency": "daily", "script": "update-aster.py"},
                {"type": "official", "method": "AI 抓公告（机制升级检测）", "frequency": "event", "script": "ai-watch-official.py"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "freshness"],
        },
    },
    "bgb": {
        "entity_type": "platform_token",
        "rr": {
            "entity_type": "platform_token",
            "principle": "平台币赋能即收入；已与 Bitget 平台切割",
            "revenue_included": {"buyback_burn": {"note": "季度回购销毁：交易所+钱包业务利润的 20%（现货/合约/杠杆手续费 + Wallet 收入）"}},
            "revenue_excluded": {"launchpad": {"note": "Bitget 基本没有打新，不计入"}},
            "calculation": {"revenue_usd_365d": "季度利润 20% 回购销毁（官方公告 + 链上验证）"},
            "source_type": "official",
            "source_url": "https://www.bitget.com",
        },
        "dp": {
            "sources": [
                {"type": "official", "method": "AI 抓季度销毁公告（数量 + 日期）", "frequency": "quarterly", "script": "ai-watch-official.py"},
                {"type": "chain", "method": "链上销毁地址复核", "frequency": "daily", "script": "update-bgb-tev.py"},
            ],
            "ai_self_check": ["mechanism-change", "freshness"],
        },
    },
    "mnt": {
        "entity_type": "platform_token",
        "rr": {
            "entity_type": "platform_token",
            "principle": "同 BNB（赋能即收入），但当前无赋能机制（sequencer fees 进 BaseFeeVault 不 burn、mETH 收益归 mETH 持有人、Staking planned）",
            "revenue_included": {},
            "revenue_excluded": {"staking": {"note": "Staking 未上线，上线后按质押收益 🟡 补进收入"}},
            "calculation": {"revenue_usd_365d": 0, "note": "当前显示 0% + 治理代币标注（时间性状态，非本质无赋能）"},
            "source_type": "estimate",
            "source_url": None,
        },
        "dp": {
            "sources": [
                {"type": "estimate", "method": "静态（TEV=0，季度复核）；Staking 上线后补链上采集", "frequency": "quarterly", "script": None},
            ],
            "ai_self_check": ["mechanism-change", "freshness"],
        },
    },
    "okb": {
        "entity_type": "platform_token",
        "rr": {
            "entity_type": "platform_token",
            "principle": "空气币：2025-08 永久停止回购/销毁（一次性销毁 65.26M OKB，合约移除机制）",
            "revenue_included": {},
            "revenue_excluded": {"jumpstart": {"note": "Jumpstart 打新忽略"}},
            "calculation": {"revenue_usd_365d": 0, "note": "TEV=0，标注「回购销毁已于 2025-08 终止，无赋能机制」"},
            "source_type": "estimate",
            "source_url": None,
        },
        "dp": {
            "sources": [
                {"type": "estimate", "method": "静态（TEV=0，季度复核）", "frequency": "quarterly", "script": None},
            ],
            "ai_self_check": ["mechanism-change", "freshness"],
        },
    },
    "hype": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "只计流向流通持币人的价值流；AF 余额（可被动用）不计入",
            "revenue_included": {"trading_fees": {"note": "手续费直接销毁 ≈ 回购，基本 99%（spot 手续费真销毁计入）"}},
            "revenue_excluded": {"assistance_fund": {"note": "AF 用交易费回购 HYPE 留在 AF 地址（可被动用），仅作注记"}},
            "calculation": {"tev_ratio": 0.99, "note": "以链上实际销毁为准（spot 销毁地址）"},
            "source_type": "chain",
            "source_url": "https://app.hyperliquid.xyz",
        },
        "dp": {
            "sources": [
                {"type": "chain", "method": "spot 销毁地址 + AF 地址", "frequency": "daily", "script": "update-hype.py"},
            ],
            "ai_self_check": ["data-plausibility", "freshness"],
        },
    },
    "uniswap": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "收入 = 抽成手续费（容易计算）；收入基本全部用于回购（Firepit 销毁 UNI）",
            "revenue_included": {"fees": {"note": "fee switch 2025-12-28 已开启；抽成手续费"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 1.0, "note": "Firepit 销毁 = 回购性质；365d 0xdead 累计口径"},
            "source_type": "chain",
            "source_url": "https://etherscan.io/address/0x000000000000000000000000000000000000dEaD",
        },
        "dp": {
            "sources": [
                {"type": "chain", "method": "Etherscan 直查 0xdead / Firepit 合约地址", "frequency": "daily", "script": "update-uniswap.py"},
                {"type": "defillama", "method": "dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "freshness"],
        },
    },
    "sky": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "净利留存国库要讲清楚；留存 vs 分配比例在财报页展示",
            "revenue_included": {"protocol_surplus": {"note": "协议盈余（扣 DSR 利息）；Elixir 真燃烧计入股东回报 🟢"}},
            "revenue_excluded": {"surplus_buffer": {"note": "Surplus Buffer 留存国库（≤5000 万 DAI）；SBE 买 MKR 做市部分 LP 锁定不计"}},
            "calculation": {"tev_ratio": 0.3336, "note": "Elixir 燃烧/留存口径"},
            "source_type": "defillama",
            "source_url": "https://defillama.com/protocol/makerdao",
        },
        "dp": {
            "sources": [
                {"type": "defillama", "method": "dailyHoldersRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
                {"type": "chain", "method": "SBE/Elixir 地址链上", "frequency": "daily", "script": "update-sky.py"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "freshness"],
        },
    },
    "pendle": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "80% 确定（Boss 拍板）：80% 协议收入回购 PENDLE → 分给 sPENDLE 质押者",
            "revenue_included": {"protocol_fees": {"note": "协议收入；80% 回购分给 sPENDLE"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.80, "note": "sPENDLE 时代 2026-01-29 起链上可验证"},
            "source_type": "chain",
            "source_url": "https://www.pendle.finance",
        },
        "dp": {
            "sources": [
                {"type": "chain", "method": "sPENDLE 回购 executor（多链）", "frequency": "daily", "script": "update-pendle-tev.py"},
                {"type": "defillama", "method": "dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "freshness"],
        },
    },
    "curve": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "增发按成本计算（美股 SBC 类比）：收入 − LP 分润 = 毛利；毛利 − 增发成本 = 净利为负（净稀释）",
            "revenue_included": {"admin_fee": {"note": "admin fee（交易费 50% LP / 50% admin fee → veCRV；crvUSD 利息 FeeSplitter 动态 50/50）"}},
            "revenue_excluded": {},
            "calculation": {
                "revenue_usd_365d": "admin fee 口径（DefiLlama dailyRevenue）",
                "emission_cost_usd_365d": 26000000,
                "emission_tokens_annual": 115500000,
                "inflation_rate_percent": 4.8,
                "note": "CRV 年增发 ~1.155 亿（约 $26M/年）全流给 LP 挖矿 → 增发作为成本扣除 → 净利为负",
            },
            "source_type": "official",
            "source_url": "https://news.curve.finance",
        },
        "dp": {
            "sources": [
                {"type": "official", "method": "官方周报 news.curve.finance / docs / gov.curve.fi 提案 + crvhub", "frequency": "weekly", "script": "ai-watch-official.py"},
                {"type": "defillama", "method": "dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
                {"type": "chain", "method": "增发量链上验证", "frequency": "daily", "script": "update-curve-tev.py"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "cross-validation", "freshness"],
        },
    },
    "dydx": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "收入 = 净协议费（含 affiliate/rebate 前、外部不可精确复算，需标注）；回购 = 市价买入后质押（非销毁）",
            "revenue_included": {"net_fees": {"note": "75% 回购、15% 质押、5% MegaVault、5% 金库（提案 #313）；大量前置补贴归交易者"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.75, "note": "回购(质押非销毁)，存 Treasury 专用账户；质押奖励 ~0.01% APY 极低；交易所已更名 Arcus，DYDX 代币未更名"},
            "source_type": "official",
            "source_url": "https://www.dydx.foundation",
        },
        "dp": {
            "sources": [
                {"type": "official", "method": "dYdX Foundation 月度报告 + Buyback Dashboard", "frequency": "monthly", "script": "ai-watch-governance.py"},
                {"type": "chain", "method": "链上回购账户", "frequency": "daily", "script": "update-dydx-tev.py"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "freshness"],
        },
    },
    "gmx": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "锁定期内实质为 0：27% 协议费用全额转国库（回购但不向质押者分发，回购-留存模式）",
            "revenue_included": {"platform_fees": {"note": "平台费（V2 交易费可算）"}},
            "revenue_excluded": {"staking_dividends": {"note": "质押分红已暂停（2026-03-04 Restore Price Discovery）"}},
            "calculation": {"revenue_usd_365d": "扣 LP → 净利 → 留存 27%", "tev_ratio": 0.0,
                            "note": "恢复条件：价格阈值 $90（对应市值 ~$9 亿），当前 $6-7 远未触发；股东回报 = 0，标注「锁定至 $90」"},
            "source_type": "official",
            "source_url": "https://gov.gmx.io/t/5042",
        },
        "dp": {
            "sources": [
                {"type": "official", "method": "gov.gmx.io 提案 #5042 监控（价格阈值恢复条件）", "frequency": "event", "script": "ai-watch-governance.py"},
                {"type": "defillama", "method": "V2 交易费日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "freshness"],
        },
    },
    "pancakeswap": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "增发按成本计算：增发 ~$1170 万 < 回购销毁 ~$1800 万 → 净利为正（净通缩，连续 34 个月）",
            "revenue_included": {"protocol_fees": {"note": "协议费；回购销毁 ≈ 总费用 22% / 协议收入 60-65%"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.625, "note": "按 60-65% 计入 🟢（现有 tevRatio 0.15 低估已更新）；现货 15-23%、永续 20%、CAKE.PAD 100%"},
            "source_type": "official",
            "source_url": "https://docs.pancakeswap.finance/cake-tokenomics",
        },
        "dp": {
            "sources": [
                {"type": "official", "method": "docs.pancakeswap.finance/cake-tokenomics + Burn Dashboard", "frequency": "weekly", "script": "ai-watch-official.py"},
                {"type": "defillama", "method": "dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
                {"type": "chain", "method": "日增发 2.25 万 CAKE + 回购销毁链上", "frequency": "daily", "script": "update-pancake-tev.py"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "cross-validation", "freshness"],
        },
    },
    "maple": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "MIP-021 阶梯回购（2026-07-17 通过）：月收入 <$1.5M → 10%；$1.5-2M → 20%；>$2M → 30%",
            "revenue_included": {"protocol_fees": {"note": "协议费收入（月收入 ~$1.29M → 落在 10% 档）"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.10, "note": "动态阶梯：2026-07 起按 MIP-021；MIP-019/020 固定 25% 已于 2026-Q2 结束"},
            "source_type": "official",
            "source_url": "https://maple.finance/transparency",
        },
        "dp": {
            "sources": [
                {"type": "official", "method": "maple.finance/transparency 官方仪表盘 + MIP 提案", "frequency": "monthly", "script": "ai-watch-governance.py"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "freshness"],
        },
    },
    "ethena": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "费用开关生效前 ENA 股东回报 = 0；DAT 回购是金库/储备出资的资本运作，非经营利润分配",
            "revenue_included": {"susde_yield": {"note": "sUSDe yield ~3.5-4% APY 全归 sUSDe 持有人（不计入 ENA 股东回报）"}},
            "revenue_excluded": {"dat_buyback": {"note": "DAT 回购（~$890M）确认为资本运作，不计入持续股东回报"}, "fee_switch": {"note": "费用开关 2026Q3 待激活，激活后 sENA 预期 >5%（届时更新）"}},
            "calculation": {"tev_ratio": 0.0, "note": "近 12 月收入 ~$310M 但净利仅 ~$0.6M；费用开关是 AI 哨兵观察点"},
            "source_type": "official",
            "source_url": "https://www.ethena.fi/governance",
        },
        "dp": {
            "sources": [
                {"type": "official", "method": "Ethena 官方治理/dashboard（费用开关激活状态监控）", "frequency": "event", "script": "ai-watch-governance.py"},
                {"type": "defillama", "method": "dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "freshness"],
        },
    },
    "justlend": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "宣称 100% 净收入回购销毁，但链上核实为 pocket-to-pocket 做账式（金库转 Black Hole，无市场买入证据）",
            "revenue_included": {"net_revenue": {"note": "净收入照算"}},
            "revenue_excluded": {"buyback_burn": {"note": "做账式销毁不计入股东回报"}},
            "calculation": {"tev_ratio": 0.0, "note": "TEV=0"},
            "source_type": "estimate",
            "source_url": None,
        },
        "dp": {
            "sources": [
                {"type": "chain", "method": "链上金库→Black Hole 转账核验", "frequency": "quarterly", "script": None},
            ],
            "ai_self_check": ["mechanism-change", "freshness"],
        },
    },
    "lido": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "只统计利润：收入 → 毛利（扣 LP/成本）→ 净利照算并展示；股东回报 = 0（不回购）",
            "revenue_included": {"protocol_fees": {"note": "DefiLlama dailyRevenue（协议归属部分）"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.0, "note": "LDO 仅治理；不回购的钱进国库/支出 → 损益表留存行"},
            "source_type": "defillama",
            "source_url": "https://defillama.com/protocol/lido",
        },
        "dp": {
            "sources": [
                {"type": "defillama", "method": "dailyFees/dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["data-plausibility", "freshness"],
        },
    },
    "eigenlayer": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "只统计利润；股东回报 = 0（不回购）",
            "revenue_included": {"protocol_fees": {"note": "DefiLlama dailyRevenue（协议归属部分）"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.0, "note": "EIGEN 无收益权；不回购的钱进国库/支出 → 留存行"},
            "source_type": "defillama",
            "source_url": "https://defillama.com/protocol/eigenlayer",
        },
        "dp": {
            "sources": [
                {"type": "defillama", "method": "dailyFees/dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["data-plausibility", "freshness"],
        },
    },
    "compound": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "只统计利润；股东回报 = 0（COMP 纯治理，fee switch OFF）",
            "revenue_included": {"protocol_fees": {"note": "DefiLlama dailyRevenue（协议归属部分）"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.0, "note": "不回购的钱进国库/支出 → 留存行"},
            "source_type": "defillama",
            "source_url": "https://defillama.com/protocol/compound-v2",
        },
        "dp": {
            "sources": [
                {"type": "defillama", "method": "dailyFees/dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["data-plausibility", "freshness"],
        },
    },
    "morpho": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "只统计利润；股东回报 = 0（MORPHO 纯治理）",
            "revenue_included": {"protocol_fees": {"note": "DefiLlama dailyRevenue（协议归属部分）"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.0, "note": "不回购的钱进国库/支出 → 留存行"},
            "source_type": "defillama",
            "source_url": "https://defillama.com/protocol/morpho",
        },
        "dp": {
            "sources": [
                {"type": "defillama", "method": "dailyFees/dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["data-plausibility", "freshness"],
        },
    },
    "spark": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "只统计利润；股东回报 = 0（SPK 收入流向 Sky DAO）",
            "revenue_included": {"protocol_fees": {"note": "DefiLlama dailyRevenue（协议归属部分）"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.0, "note": "收入流向 Sky DAO，SPK 本身无股东回报"},
            "source_type": "defillama",
            "source_url": "https://defillama.com/protocol/spark",
        },
        "dp": {
            "sources": [
                {"type": "defillama", "method": "dailyFees/dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["data-plausibility", "freshness"],
        },
    },
    "kamino": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "只统计利润；股东回报 = 0（KMNO 不回购）",
            "revenue_included": {"protocol_fees": {"note": "DefiLlama dailyRevenue（协议归属部分）"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.0, "note": "不回购的钱进国库/支出 → 留存行"},
            "source_type": "defillama",
            "source_url": "https://defillama.com/protocol/kamino",
        },
        "dp": {
            "sources": [
                {"type": "defillama", "method": "dailyFees/dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["data-plausibility", "freshness"],
        },
    },
    "jito": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "只统计利润；股东回报 = 0（JTO 纯治理，MEV 归 JitoSOL）",
            "revenue_included": {"protocol_fees": {"note": "DefiLlama dailyRevenue（协议归属部分）"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.0, "note": "不回购的钱进国库/支出 → 留存行"},
            "source_type": "defillama",
            "source_url": "https://defillama.com/protocol/jito",
        },
        "dp": {
            "sources": [
                {"type": "defillama", "method": "dailyFees/dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["data-plausibility", "freshness"],
        },
    },
    "fluid": {
        "entity_type": "app",
        "rr": {
            "entity_type": "app",
            "principle": "35% revenue → Treasury 回购（链上 2 个 reserve 钱包；回购后 FLUID 终极用途未公开）",
            "revenue_included": {"protocol_fees": {"note": "DefiLlama dailyRevenue（协议归属部分）"}},
            "revenue_excluded": {},
            "calculation": {"tev_ratio": 0.35, "note": "35% 回购口径（DefiLlama dailyHoldersRevenue 365d $4.75M 与官方 35% 一致）"},
            "source_type": "defillama",
            "source_url": "https://defillama.com/protocol/fluid",
        },
        "dp": {
            "sources": [
                {"type": "chain", "method": "2 个 reserve 钱包链上追踪（0x3e6F.../0x9Afb...）", "frequency": "daily", "script": "track-fluid-buybacks-v3.py"},
                {"type": "defillama", "method": "dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
            ],
            "ai_self_check": ["mechanism-change", "data-plausibility", "freshness"],
        },
    },
}

DEFAULTS = {
    "dp": {
        "sources": [
            {"type": "defillama", "method": "dailyFees/dailyRevenue 日频", "frequency": "daily", "script": "fetch-defillama.js"},
        ],
        "ai_self_check": ["data-plausibility", "freshness"],
    },
}


def main():
    updated, skipped = [], []
    for name in sorted(os.listdir(BASE)):
        p = BASE / name
        if not p.is_dir():
            continue
        cf = p / "config.json"
        if not cf.exists():
            continue
        plan = PLAN.get(name)
        if plan is None:
            skipped.append((name, "无判定书配置，跳过"))
            continue

        d = json.loads(cf.read_text(encoding="utf-8"))
        d["revenue_recognition"] = plan["rr"]
        d["data_pipeline"] = plan["dp"]
        d["last_updated"] = "2026-08-02"
        if DRY:
            updated.append((name, "DRY-RUN 未写入"))
            continue
        cf.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        updated.append((name, "ok"))

    for name, st in updated:
        print(f"  {'[DRY]' if DRY else '   '} {name:14s} {st}")
    for name, st in skipped:
        print(f"  SKIP {name:14s} {st}")
    print(f"\n{'DRY-RUN' if DRY else '写入'}完成: {len(updated)} 更新, {len(skipped)} 跳过")


if __name__ == "__main__":
    main()
