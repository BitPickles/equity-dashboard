#!/usr/bin/env node
/**
 * sync-tev-data.js - TEV 数据自动同步脚本
 * 
 * 功能：
 * 1. 从 DefiLlama 获取 Revenue 数据
 * 2. 从 CMC 获取市值数据（CoinGecko 备用）
 * 3. 根据 payout_ratio 计算 TEV
 * 4. 更新 all-protocols.json
 * 
 * 用法：
 *   node scripts/sync-tev-data.js           # 更新所有协议
 *   node scripts/sync-tev-data.js aave gmx  # 只更新指定协议
 *   node scripts/sync-tev-data.js --dry-run # 预览不写入
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// CMC 数据更新脚本路径
const CMC_UPDATE_SCRIPT = '/Users/aibot/.openclaw/workspace-researcher/scripts/update_cmc_daily.py';
const BTCD_SYNC_SCRIPT = path.join(__dirname, 'sync-btcd.py');

// 协议配置：DefiLlama slug, CoinGecko id, CMC slug, payout_ratio
const PROTOCOL_CONFIG = {
  aave: { 
    defillamaSlug: 'aave', 
    coingeckoId: 'aave',
    cmcSlug: 'aave',
    payout_ratio: null,  // 特殊：固定年度回购预算
    fixedTevUsd: 30000000,
    note: '年度回购 $30M (2026-03 治理投票从 $50M 下调, 99.37% 通过)'
  },
  curve: {
    defillamaSlug: 'curve-dex',
    coingeckoId: 'curve-dao-token',
    cmcSlug: 'curve-dao-token',
    defillamaDataType: 'dailyHoldersRevenue',
    payout_ratio: 1.0,
    note: 'DefiLlama dailyHoldersRevenue 已映射 FeeAllocator 90%→veCRV (2025-06-27 起). 注意：仅 veCRV 持有人捕获，裸 CRV ≈ 0，前端 Caveat 必须标注'
  },
  dydx: {
    defillamaSlug: 'dydx',
    coingeckoId: 'dydx-chain',
    cmcSlug: 'dydx-chain',
    defillamaDataType: 'dailyHoldersRevenue',
    payout_ratio: 1.0,
    note: 'DefiLlama dailyHoldersRevenue 已是 holders 部分; 分母用 DYDX Chain native mcap (排除 ethDYDX bridge 关闭后的孤儿). 75% buyback 治理通过但 Cosmos 链 Treasury SubDAO 账户链上无公开 tracker, medium confidence'
  },
  etherfi: {
    defillamaSlug: 'ether.fi',
    coingeckoId: 'ether-fi',
    cmcSlug: 'ether-fi',
    payout_ratio: 0.25,
    note: '25% 协议收入回购 ETHFI → sETHFI (DAO Proposal #11, 正式治理通过)'
  },
  fluid: {
    defillamaSlug: 'fluid',
    coingeckoId: 'instadapp',
    cmcSlug: 'instadapp',
    defillamaDataType: 'dailyHoldersRevenue',
    payout_ratio: 1.0,
    note: '35% revenue → Treasury 回购. DefiLlama dailyHoldersRevenue 365d $4.75M (实测与官方 35% 一致). 链上 2 个 reserve 钱包: 0x3e6F.../0x9Afb..., 但回购后 FLUID 终极用途未公开 (caveat)'
  },
  gmx: {
    defillamaSlug: 'gmx',
    coingeckoId: 'gmx',
    cmcSlug: 'gmx',
    payout_ratio: 0,
    note: '⚠️ TEV PAUSED: 2026-03-04 起 ETH/AVAX 实时分红停, 改为 Treasury 累积 GMX 等待 GMX 价格 ≥ $90 触发分配. 当前 GMX ~$7, 触发条件远未达, staker 实际现金收益 = 0. yield 标 0% + caveat 说明暂停状态'
  },
  maple: {
    defillamaSlug: 'maple',
    coingeckoId: 'syrup',
    cmcSlug: 'maple-finance',
    defillamaDataType: 'dailyHoldersRevenue',
    payout_ratio: 1.0,
    note: 'MIP-019/020 25% revenue → SSF 回购 SYRUP. DefiLlama dailyHoldersRevenue 365d $1.81M (6 个月外推). 风险: SSF 国库钱包未公开, burn vs reserve 比例未披露'
  },
  pancakeswap: {
    defillamaSlug: 'pancakeswap',
    coingeckoId: 'pancakeswap-token',
    cmcSlug: 'pancakeswap',
    defillamaDataType: 'dailyHoldersRevenue',
    payout_ratio: 1.0,
    note: 'CAKE 销毁: veCAKE 已 2025-04-23 sunset, Tokenomics 3.0 转 100% burn → 0xdead. DefiLlama holdersRevenue 已是 burn 部分, 但仅覆盖 AMM/StableSwap, 漏 Perpetual/Prediction/Lottery (前端 Caveat 标注)'
  },
  pendle: {
    defillamaSlug: 'pendle',
    coingeckoId: 'pendle',
    cmcSlug: 'pendle',
    defillamaDataType: 'dailyHoldersRevenue',
    payout_ratio: 1.0,
    note: 'DefiLlama dailyHoldersRevenue 已是 sPENDLE 持有人份额(实测 365d $22M, 占 revenue $26M 的 85%, 与官方 80% 比例吻合). 但多链 buyback executor 未公开, sPENDLE 入金混杂用户 stake 无法链上分离, medium confidence'
  },
  sky: {
    defillamaSlug: 'sky',
    coingeckoId: 'maker',
    cmcSlug: 'sky',
    payout_ratio: null,
    fixedTevUsd: 13724000,  // $37,600/天 × 365 = $13.724M (2026-03 治理大幅下调, 原 $30万/天)
    note: 'Smart Burn Engine 日回购 $37,600 (2026-03 治理投票下调 87.5%)'
  },
  // 以下协议无 TEV (tevStatus=none)，仅获取市值
  compound: {
    defillamaSlug: 'compound-v3',
    coingeckoId: 'compound-governance-token',
    cmcSlug: 'compound',
    payout_ratio: 0,
    note: '纯治理代币'
  },
  eigenlayer: {
    defillamaSlug: 'eigenlayer',
    coingeckoId: 'eigenlayer',
    cmcSlug: 'eigenlayer',
    payout_ratio: 0,
    note: '纯治理代币'
  },
  ethena: {
    defillamaSlug: 'ethena',
    coingeckoId: 'ethena',
    cmcSlug: 'ethena',
    payout_ratio: 0,
    note: '纯治理代币'
  },
  justlend: {
    defillamaSlug: 'justlend',
    coingeckoId: 'just',
    cmcSlug: 'justlend',
    payout_ratio: 0.30,
    note: '30% 平台收入回购烧毁 JST (2025-10 治理通过, $41.42M 储备至 Q4 2026)'
  },
  jito: {
    defillamaSlug: 'jito',
    coingeckoId: 'jito-governance-token',
    cmcSlug: 'jito',
    payout_ratio: 0,
    note: 'MEV 收益归 JitoSOL, JTO 纯治理'
  },
  kamino: {
    defillamaSlug: 'kamino',
    coingeckoId: 'kamino',
    cmcSlug: 'kamino-finance',
    payout_ratio: 0,
    note: '纯治理代币'
  },
  lido: {
    defillamaSlug: 'lido',
    coingeckoId: 'lido-dao',
    cmcSlug: 'lido-dao',
    payout_ratio: 0,
    note: '纯治理代币'
  },
  morpho: {
    defillamaSlug: 'morpho',
    coingeckoId: 'morpho',
    cmcSlug: 'morpho',
    payout_ratio: 0,
    note: '纯治理代币'
  },
  spark: {
    defillamaSlug: 'spark',
    coingeckoId: 'spark',
    cmcSlug: 'spark',
    payout_ratio: 0,
    note: '收入归 Sky DAO'
  },
  mnt: {
    defillamaSlug: null,  // 无 mantle-mnt 协议级 fees
    coingeckoId: 'mantle',
    cmcSlug: 'mantle',
    payout_ratio: 0,
    note: 'governance-only (类 LDO). Mantle L2 sequencer fees 不流向 MNT 持有人, mETH 收益给 mETH 持有人, Treasury Burn 提案讨论中未执行'
  },
  bgb: {
    defillamaSlug: null,
    coingeckoId: 'bitget-token',
    cmcSlug: 'bitget-token',
    payout_ratio: 0,
    note: '⚠️ BGB 销毁源头不可链上验证 (类 JustLend pocket-to-pocket 嫌疑). 官方称 20% 收入回购, 但销毁来源无市场对手方证据. yield 标 0% + low confidence'
  },
  okb: {
    defillamaSlug: null,
    coingeckoId: 'okb',
    cmcSlug: 'okb',
    payout_ratio: 0,
    note: '2025-08 永久锁定 21M 供应, 移除 mint/burn. 官方治理决议永久停止所有 TEV 机制. yield 0% high confidence (明确停止, 非 paused)'
  },
  // SKIP_PROTOCOLS: 市值/年度TEV由独立脚本维护，但 DefiLlama 收入用于多维度 yield 计算
  aster: {
    defillamaSlug: null,  // DefiLlama 无可用数据
    coingeckoId: 'aster-2',
    cmcSlug: 'aster',
    payout_ratio: 0.7,
    note: '70% 交易费回购销毁 (独立链上追踪)'
  },
  bnb: {
    defillamaSlug: 'bsc',
    coingeckoId: 'binancecoin',
    cmcSlug: 'bnb',
    payout_ratio: 0,
    note: 'Auto-Burn + BEP-95 + StakeHub (独立链上追踪)'
  },
  hype: {
    defillamaSlug: 'hyperliquid',
    coingeckoId: 'hyperliquid',
    cmcSlug: 'hyperliquid',
    payout_ratio: 1.0,
    note: '100% Assistance Fund 回购烧毁 (独立追踪)'
  },
  uniswap: {
    defillamaSlug: 'uniswap',
    coingeckoId: 'uniswap',
    cmcSlug: 'uniswap',
    payout_ratio: 1.0,
    note: '100% 协议费 Firepit 烧毁 + Unichain (独立链上追踪)'
  },
  layerzero: {
    defillamaSlug: 'layerzero-v2',
    coingeckoId: 'layerzero',
    cmcSlug: 'layerzero',
    payout_ratio: null,
    note: 'Stargate 回购小额；协议本体 fee switch 关闭收入=0（期权价值标的）'
  },
};

// 不更新市值/年度TEV的协议（有独立数据源），但仍拉 DefiLlama 收入算多维度 yield
// 2026-04-26: pancakeswap/etherfi/curve 改链上口径，不再走 generic DefiLlama
const SKIP_PROTOCOLS = ['aster', 'hype', 'bnb', 'uniswap', 'bgb', 'okb', 'pancakeswap', 'etherfi', 'curve'];

// 股东回报拆分：把每协议的「股东回报率」归为 dividend(分配给持有人/质押者) 或 buyback(回购销毁)
//   'dividend'：fee 分配给 ve/staker（持有人拿到现金/代币流）
//   'buyback' ：协议回购销毁（减少流通 → 全体持有人通过稀缺性受益）
//   'mixed'   ：两者皆有，由专属分支预存 protocol._divYld（分红部分 yield），post-pass 用 buyback = tev - dividend
// 后处理 pass 据此输出 dividend_yield/buyback_yield；不变量：两者和 ≡ 股东回报率（每周期）
const VALUE_RETURN = {
  aave: 'mixed',   bnb: 'mixed',
  curve: 'dividend', dydx: 'dividend', pendle: 'dividend', gmx: 'dividend',
  aster: 'buyback', hype: 'buyback', uniswap: 'buyback', pancakeswap: 'buyback',
  fluid: 'buyback', maple: 'buyback', sky: 'buyback', justlend: 'buyback',
  etherfi: 'buyback', ethena: 'buyback',
};

const DATA_FILE = path.join(__dirname, '../data/all-protocols.json');

// API 请求封装
async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// 获取 DefiLlama Revenue
// dataType: 'dailyRevenue' (默认, 协议总收入) | 'dailyHoldersRevenue' (已是持有人捕获的部分)
// 选 'dailyHoldersRevenue' 时，PROTOCOL_CONFIG 的 payout_ratio 应设为 1.0（数据本身就是 TEV）
async function getDefillamaRevenue(slug, dataType = 'dailyRevenue') {
  try {
    const data = await fetchJson(`https://api.llama.fi/summary/fees/${slug}?dataType=${dataType}`);
    const chart = data.totalDataChart || [];
    const sumSlice = (n) => chart.slice(-n).reduce((s, d) => s + (d[1] || 0), 0);
    return {
      revenue7d:   chart.length >= 7   ? sumSlice(7)   : null,
      revenue30d:  chart.length >= 7   ? sumSlice(30)  : null,
      revenue90d:  chart.length >= 30  ? sumSlice(90)  : null,
      revenue365d: sumSlice(365),
      chartLength: chart.length,
      dataType,
    };
  } catch (e) {
    console.warn(`  ⚠️ DefiLlama ${slug}/${dataType}: ${e.message}`);
    return null;
  }
}

// 通用 DefiLlama fees/revenue/holdersRevenue 拉取
async function getDefillamaFees(slug, dataType) {
  try {
    const data = await fetchJson(`https://api.llama.fi/summary/fees/${slug}?dataType=${dataType}`);
    const chart = data.totalDataChart || [];
    const sumSlice = (n) => chart.slice(-n).reduce((s, d) => s + (d[1] || 0), 0);
    return {
      sum7d:   sumSlice(7),
      sum30d:  sumSlice(30),
      sum90d:  sumSlice(90),
      sum365d: sumSlice(365),
      chartLength: chart.length,
    };
  } catch (e) {
    console.warn(`  ⚠️ DefiLlama ${slug}/${dataType}: ${e.message}`);
    return null;
  }
}

// 获取 CoinGecko 市值（带重试）
async function getCoingeckoMarketCap(id, retries = 2) {
  for (let i = 0; i < retries; i++) {
    try {
      if (i > 0) {
        console.log(`  ⏳ CoinGecko 重试 ${i + 1}/${retries}...`);
        await new Promise(r => setTimeout(r, 3000 * i));
      }
      const data = await fetchJson(`https://api.coingecko.com/api/v3/simple/price?ids=${id}&vs_currencies=usd&include_market_cap=true`);
      const mcap = data[id]?.usd_market_cap || 0;
      if (mcap > 0) return mcap;
    } catch (e) {
      if (i === retries - 1) {
        console.warn(`  ⚠️ CoinGecko ${id}: ${e.message}`);
      }
    }
  }
  return null;
}

// 获取 CMC 市值（主数据源）
async function getCmcMarketCap(slug) {
  try {
    // 使用 CMC 公开 API
    const data = await fetchJson(`https://api.coinmarketcap.com/data-api/v3/cryptocurrency/detail?slug=${slug}`);
    const mcap = data?.data?.statistics?.marketCap || 0;
    if (mcap > 0) {
      return mcap;
    }
  } catch (e) {
    console.warn(`  ⚠️ CMC ${slug}: ${e.message}`);
  }
  return null;
}

// 获取市值（CMC 优先，CoinGecko 备用）
async function getMarketCap(coingeckoId, cmcSlug) {
  // 先尝试 CMC
  if (cmcSlug) {
    let mcap = await getCmcMarketCap(cmcSlug);
    if (mcap && mcap > 0) return mcap;
  }
  
  // CMC 失败，尝试 CoinGecko
  console.log(`  → 切换到 CoinGecko...`);
  let mcap = await getCoingeckoMarketCap(coingeckoId);
  if (mcap && mcap > 0) return mcap;
  
  return null;
}

// 更新 CMC 数据并同步 BTC.D
function updateCmcAndBtcd() {
  console.log('📈 更新 CMC 市值数据...');
  try {
    // 更新 CMC CSV
    if (fs.existsSync(CMC_UPDATE_SCRIPT)) {
      const output = execSync(`python3 "${CMC_UPDATE_SCRIPT}"`, {
        encoding: 'utf8',
        timeout: 60000
      });
      const match = output.match(/Added (\d+) new records/);
      if (match && match[1] !== '0') {
        console.log(`  ✅ CMC: +${match[1]} 条数据`);
      } else {
        console.log(`  ✅ CMC: 已是最新`);
      }
    }
    
    // 同步 BTC.D
    if (fs.existsSync(BTCD_SYNC_SCRIPT)) {
      const output = execSync(`python3 "${BTCD_SYNC_SCRIPT}"`, {
        encoding: 'utf8',
        timeout: 30000,
        cwd: __dirname
      });
      const match = output.match(/最新: ([\d-]+), BTC\.D: ([\d.]+)%/);
      if (match) {
        console.log(`  ✅ BTC.D: ${match[1]} ${match[2]}%`);
      } else if (output.includes('没有新数据')) {
        console.log(`  ✅ BTC.D: 已是最新`);
      }
    }
  } catch (e) {
    console.log(`  ⚠️ CMC/BTC.D 更新失败: ${e.message}`);
  }
  console.log('');
}

// 主函数
async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const targetProtocols = args.filter(a => !a.startsWith('--'));
  
  console.log('=== TEV 数据同步 ===\n');
  if (dryRun) console.log('🔍 预览模式（不写入）\n');
  
  // 先更新 CMC/BTC.D（如果是完整同步）
  if (!dryRun && targetProtocols.length === 0) {
    updateCmcAndBtcd();
  }
  
  // 读取现有数据
  const allData = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  const protocols = allData.protocols;

  // 同步所有协议的静态字段（confidence/tevStatus/return_mechanisms 等）从 config.json → all-protocols.json
  // 否则在 config.json 改了 confidence 但 sync 不会拉过来, 主表会显示旧值
  const STATIC_FIELDS_FROM_CONFIG = ['confidence', 'confidence_reason', 'tevStatus',
                                     'return_mechanisms', 'tev_summary', 'analyst_notes', 'notes',
                                     'last_updated'];
  for (const [pid, protocol] of Object.entries(protocols)) {
    const configPath = path.join(__dirname, `../data/protocols/${pid}/config.json`);
    if (!fs.existsSync(configPath)) continue;
    try {
      const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      for (const field of STATIC_FIELDS_FROM_CONFIG) {
        if (cfg[field] !== undefined) protocol[field] = cfg[field];
      }
    } catch (e) {
      console.warn(`  ⚠️ 读 ${pid}/config.json 失败: ${e.message}`);
    }
  }

  let updated = 0;
  let errors = 0;
  
  for (const [key, config] of Object.entries(PROTOCOL_CONFIG)) {
    // 跳过未指定的协议
    if (targetProtocols.length > 0 && !targetProtocols.includes(key)) continue;
    
    // BNB 专属计算：Auto-Burn（按窗口年化）+ asBNB 固定 APY
    if (key === 'bnb') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 bnb... (专属 TEV 计算)`);
      if (!protocol.metrics) protocol.metrics = {};
      const marketCap = protocol.market_cap_usd || 0;
      const bnbPrice = marketCap / 136357344;  // circulating supply ~136.36M

      // 读取烧毁历史
      const burnHistPath = path.join(__dirname, '../data/protocols/bnb/burn-history.json');
      let burnHist = { quarterly_burns: [], asbnb_apy_percent: 6.87, bep95_weekly_bnb: 720.64 };
      try { burnHist = JSON.parse(fs.readFileSync(burnHistPath, 'utf8')); } catch {}

      // 读取 BEP-95 日时间序列（Dune seed + 后续累积）
      const bep95HistPath = path.join(__dirname, '../data/protocols/bnb/bep95-history.json');
      let bep95Hist = { daily: [] };
      try { bep95Hist = JSON.parse(fs.readFileSync(bep95HistPath, 'utf8')); } catch {}
      const bep95Daily = bep95Hist.daily || [];

      const asbnbApy = burnHist.asbnb_apy_percent || 6.87;
      const burns = burnHist.quarterly_burns || [];

      // BEP-95 按窗口从日时间序列求和（单位：BNB）
      const sumBep95 = (days) => bep95Daily.slice(-days).reduce((s, r) => s + (r.bnb || 0), 0);
      const bep95_7d_bnb   = sumBep95(7);
      const bep95_30d_bnb  = sumBep95(30);
      const bep95_90d_bnb  = sumBep95(90);
      const bep95_365d_bnb = sumBep95(365);
      // 年化 USD（用当前价）
      const bep95_7d_usd   = bep95_7d_bnb   * (365 / 7)   * bnbPrice;
      const bep95_30d_usd  = bep95_30d_bnb  * (365 / 30)  * bnbPrice;
      const bep95_90d_usd  = bep95_90d_bnb  * (365 / 90)  * bnbPrice;
      const bep95_365d_usd = bep95_365d_bnb * bnbPrice;  // 已是 365 天累计

      // Auto-Burn 口径：
      //   - 7d/30d/90d：近 4 季 burn 的 usd_value 累加（每次 burn 公告时的历史 USD）
      //   - 365d：近 4 季 burn BNB 合计 × 当前价（按当前市价重估）
      const recent4Burns = burns.slice(-4);
      const recent4BurnBnb = recent4Burns.reduce((s, b) => s + (b.bnb_burned || 0), 0);
      const recent4BurnUsdHistorical = recent4Burns.reduce((s, b) => s + (b.usd_value || 0), 0);
      const recent4BurnUsdCurrent = recent4BurnBnb * bnbPrice;
      const lastBurn = burns[burns.length - 1] || { bnb_burned: 0, date: null };

      // 各周期 TEV Yield = (Auto-Burn USD + BEP-95 年化 USD) / 市值 + asBNB APY
      const calcYield = (autoBurnUsd, bep95Usd) => marketCap > 0
        ? Math.round((autoBurnUsd + bep95Usd) / marketCap * 10000) / 100
        : 0;

      const burnYield_7d   = calcYield(recent4BurnUsdHistorical, bep95_7d_usd);
      const burnYield_30d  = calcYield(recent4BurnUsdHistorical, bep95_30d_usd);
      const burnYield_90d  = calcYield(recent4BurnUsdHistorical, bep95_90d_usd);
      const burnYield_365d = calcYield(recent4BurnUsdCurrent,    bep95_365d_usd);

      const tevYield_7d   = Math.round((burnYield_7d   + asbnbApy) * 100) / 100;
      const tevYield_30d  = Math.round((burnYield_30d  + asbnbApy) * 100) / 100;
      const tevYield_90d  = Math.round((burnYield_90d  + asbnbApy) * 100) / 100;
      const tevYield_365d = Math.round((burnYield_365d + asbnbApy) * 100) / 100;

      protocol.metrics.tev_yield_7d_ann  = tevYield_7d;
      protocol.metrics.tev_yield_30d_ann = tevYield_30d;
      protocol.metrics.tev_yield_90d_ann = tevYield_90d;
      protocol.shareholder_yield_percent         = tevYield_365d;
      // BNB 无 fee 分润机制，payout_ratio 不适用（前端渲染会显示 '—'）
      protocol.payout_ratio = null;

      // 股东回报拆分（mixed）：分红 = asBNB 质押收益（各周期恒定）；回购 = Auto-Burn + BEP-95（post-pass 取 tev - dividend）
      protocol._divYld = { '7': asbnbApy, '30': asbnbApy, '90': asbnbApy, '365': asbnbApy };

      // Earning Yield = BEP-95（按窗口年化）+ asBNB APY
      // 各周期用对应窗口的 BEP-95 值，与 TEV Yield 的周期口径保持一致
      const bep95Yield = (usd) => marketCap > 0 ? usd / marketCap * 100 : 0;
      const ey_7d   = Math.round((bep95Yield(bep95_7d_usd)   + asbnbApy) * 100) / 100;
      const ey_30d  = Math.round((bep95Yield(bep95_30d_usd)  + asbnbApy) * 100) / 100;
      const ey_90d  = Math.round((bep95Yield(bep95_90d_usd)  + asbnbApy) * 100) / 100;
      const ey_365d = Math.round((bep95Yield(bep95_365d_usd) + asbnbApy) * 100) / 100;
      protocol.total_yield_percent        = ey_365d;
      protocol.metrics.earning_yield_7d_ann  = ey_7d;
      protocol.metrics.earning_yield_30d_ann = ey_30d;
      protocol.metrics.earning_yield_90d_ann = ey_90d;

      // BNB 的 BEP-95 占 yield 比例极小 (~0.02%)，需用 3 位小数才能看出周期差异
      protocol.display_precision = 3;

      // 同步 validation 字段（各周期独立，反映 BEP-95 波动）
      if (!protocol.validation) protocol.validation = {};
      protocol.validation.method = 'Auto-Burn（短周期=近4季USD累加；365d=近4季BNB×当前价）+ BEP-95（按窗口从日时间序列计算）+ asBNB APY (Aster)';
      protocol.validation.asbnb_apy_percent = asbnbApy;
      protocol.validation.tev_yield_7d_percent   = tevYield_7d;
      protocol.validation.tev_yield_30d_percent  = tevYield_30d;
      protocol.validation.tev_yield_90d_percent  = tevYield_90d;
      protocol.validation.tev_yield_365d_percent = tevYield_365d;
      protocol.validation.bep95_7d_bnb   = Math.round(bep95_7d_bnb   * 100) / 100;
      protocol.validation.bep95_30d_bnb  = Math.round(bep95_30d_bnb  * 100) / 100;
      protocol.validation.bep95_90d_bnb  = Math.round(bep95_90d_bnb  * 100) / 100;
      protocol.validation.bep95_365d_bnb = Math.round(bep95_365d_bnb * 100) / 100;
      protocol.validation.bep95_data_days = bep95Daily.length;
      protocol.validation.bep95_data_range = bep95Daily.length
        ? { start: bep95Daily[0].date, end: bep95Daily[bep95Daily.length - 1].date }
        : null;
      protocol.validation.last_burn_bnb = lastBurn.bnb_burned || 0;
      protocol.validation.last_burn_date = lastBurn.date || null;
      protocol.validation.recent_4q_burn_bnb = Math.round(recent4BurnBnb);
      protocol.validation.recent_4q_burn_usd_historical = Math.round(recent4BurnUsdHistorical);
      protocol.validation.recent_4q_burn_usd_current = Math.round(recent4BurnUsdCurrent);
      protocol.validation.bnb_price_usd = Math.round(bnbPrice * 100) / 100;
      protocol.validation.market_cap_usd = marketCap;
      protocol.validation.burn_source = `Auto-Burn 近4季 ${Math.round(recent4BurnBnb).toLocaleString()} BNB (历史$${(recent4BurnUsdHistorical/1e9).toFixed(2)}B / 当前价$${(recent4BurnUsdCurrent/1e9).toFixed(2)}B); BEP-95 ${bep95Daily.length}天数据, 7/30/90/365d = ${Math.round(bep95_7d_bnb)}/${Math.round(bep95_30d_bnb)}/${Math.round(bep95_90d_bnb)}/${Math.round(bep95_365d_bnb)} BNB`;

      console.log(`  BNB price: $${bnbPrice.toFixed(0)}`);
      console.log(`  BEP-95 series: ${bep95Daily.length} days (${bep95Daily[0]?.date} → ${bep95Daily[bep95Daily.length-1]?.date})`);
      console.log(`  BEP-95 窗口 BNB: 7d=${Math.round(bep95_7d_bnb)} / 30d=${Math.round(bep95_30d_bnb)} / 90d=${Math.round(bep95_90d_bnb)} / 365d=${Math.round(bep95_365d_bnb)}`);
      console.log(`  Auto-Burn USD: 近4季历史累加=$${(recent4BurnUsdHistorical/1e9).toFixed(2)}B / 当前价重估=$${(recent4BurnUsdCurrent/1e9).toFixed(2)}B`);
      console.log(`  asBNB APY: ${asbnbApy}%`);
      console.log(`  TEV Yield: 7d=${tevYield_7d}% 30d=${tevYield_30d}% 90d=${tevYield_90d}% 365d=${tevYield_365d}%`);
      updated++;
      continue;
    }

    // Aave 专属：TEV = 固定年度 Buyback 预算 + Safety Module holders revenue（动态，按窗口）
    // 决策（Boss 2026-04-22 定）：
    //   1. Buyback $30M/年（2026-03 治理从 $50M 下调）——算 TEV，但是 treasury-accumulated 非真 burn
    //   2. Safety Module（Umbrella）按 DefiLlama dailyHoldersRevenue 窗口累加年化（方案 A）
    //   3. 最近 50+ 天 SM = $0 可能是 Umbrella 迁移期，暂信 DefiLlama
    if (key === 'aave') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 aave... (双源：固定 Buyback $30M + 动态 Safety Module holdersRevenue)`);
      const marketCap = protocol.market_cap_usd || 0;
      const fixedBuybackUsd = config.fixedTevUsd || 30_000_000;  // 2026-03 治理后 $30M

      const [holdersData, revenueData] = await Promise.all([
        getDefillamaFees('aave', 'dailyHoldersRevenue'),
        getDefillamaRevenue('aave'),
      ]);

      if (!protocol.metrics) protocol.metrics = {};

      // TEV = buyback + SM annualized，各周期独立
      const calcTev = (smSum, days) => {
        if (!marketCap) return 0;
        const ann = days >= 365 ? 1 : (365 / days);
        const smUsd = (smSum || 0) * ann;
        return Math.round((fixedBuybackUsd + smUsd) / marketCap * 10000) / 100;
      };
      const calcEarn = (revSum, days) => {
        if (!marketCap) return 0;
        const ann = days >= 365 ? 1 : (365 / days);
        return Math.round((revSum || 0) * ann / marketCap * 10000) / 100;
      };

      if (holdersData && revenueData) {
        const tev_7d   = calcTev(holdersData.sum7d,   7);
        const tev_30d  = calcTev(holdersData.sum30d,  30);
        const tev_90d  = calcTev(holdersData.sum90d,  90);
        const tev_365d = calcTev(holdersData.sum365d, 365);
        const ey_7d   = calcEarn(revenueData.revenue7d,   7);
        const ey_30d  = calcEarn(revenueData.revenue30d,  30);
        const ey_90d  = calcEarn(revenueData.revenue90d,  90);
        const ey_365d = calcEarn(revenueData.revenue365d, 365);

        protocol.metrics.tev_yield_7d_ann  = tev_7d;
        protocol.metrics.tev_yield_30d_ann = tev_30d;
        protocol.metrics.tev_yield_90d_ann = tev_90d;
        protocol.shareholder_yield_percent         = tev_365d;
        protocol.metrics.earning_yield_7d_ann  = ey_7d;
        protocol.metrics.earning_yield_30d_ann = ey_30d;
        protocol.metrics.earning_yield_90d_ann = ey_90d;
        protocol.total_yield_percent         = ey_365d;
        protocol.metrics.trailing_7d_revenue_usd   = revenueData.revenue7d;
        protocol.metrics.trailing_30d_revenue_usd  = revenueData.revenue30d;
        protocol.metrics.trailing_90d_revenue_usd  = revenueData.revenue90d;
        protocol.metrics.trailing_365d_revenue_usd = revenueData.revenue365d;

        // payout_ratio 按周期
        const calcRatio = (t, e) => (e > 0 ? Math.round(t / e * 10000) / 10000 : null);
        protocol.tevRatio_7d   = calcRatio(tev_7d,   ey_7d);
        protocol.tevRatio_30d  = calcRatio(tev_30d,  ey_30d);
        protocol.tevRatio_90d  = calcRatio(tev_90d,  ey_90d);
        protocol.tevRatio_365d = calcRatio(tev_365d, ey_365d);
        protocol.payout_ratio = protocol.tevRatio_365d;

        // 股东回报拆分（mixed）：分红 = Safety Module holdersRevenue（年化）；回购 = 固定 Buyback（post-pass 取 tev - dividend）
        const divYld = (smSum, days) => {
          if (!marketCap) return 0;
          const ann = days >= 365 ? 1 : (365 / days);
          return Math.round((smSum || 0) * ann / marketCap * 10000) / 100;
        };
        protocol._divYld = {
          '7':   divYld(holdersData.sum7d,   7),
          '30':  divYld(holdersData.sum30d,  30),
          '90':  divYld(holdersData.sum90d,  90),
          '365': divYld(holdersData.sum365d, 365),
        };

        protocol.validation = protocol.validation || {};
        protocol.validation.method = 'TEV = 固定 Buyback $30M/年（2026-03 治理）+ Safety Module (Umbrella) DefiLlama dailyHoldersRevenue 按窗口年化';
        protocol.validation.fixed_buyback_usd_annual = fixedBuybackUsd;
        protocol.validation.sm_7d_usd   = Math.round(holdersData.sum7d);
        protocol.validation.sm_30d_usd  = Math.round(holdersData.sum30d);
        protocol.validation.sm_90d_usd  = Math.round(holdersData.sum90d);
        protocol.validation.sm_365d_usd = Math.round(holdersData.sum365d);
        protocol.validation.caveats = [
          'Buyback 是 treasury-accumulated，不是真 burn（买入 AAVE → Ecosystem Reserve，治理可 redistribute）',
          'Safety Module 分发是脉冲式（每 1-2 周一次大包），短周期窗口可能为 0',
          '最近 50+ 天 SM = $0，可能 Umbrella 新合约 DefiLlama 追踪滞后，或真的暂停分发',
          '链上 AAVE @ 0xdead 365d = 0.0001 AAVE（没有真销毁，符合 treasury buyback 模式）',
        ];

        console.log(`  marketCap: $${(marketCap/1e9).toFixed(2)}B, 固定 Buyback: $${fixedBuybackUsd/1e6}M`);
        console.log(`  SM holdersRevenue: 7d=$${(holdersData.sum7d/1e6).toFixed(2)}M 30d=$${(holdersData.sum30d/1e6).toFixed(2)}M 90d=$${(holdersData.sum90d/1e6).toFixed(2)}M 365d=$${(holdersData.sum365d/1e6).toFixed(2)}M`);
        console.log(`  Revenue:           7d=$${(revenueData.revenue7d/1e6).toFixed(2)}M 30d=$${(revenueData.revenue30d/1e6).toFixed(2)}M 90d=$${(revenueData.revenue90d/1e6).toFixed(2)}M 365d=$${(revenueData.revenue365d/1e6).toFixed(2)}M`);
        console.log(`  TEV Yield:     7d=${tev_7d}% 30d=${tev_30d}% 90d=${tev_90d}% 365d=${tev_365d}%`);
        console.log(`  Earning:       7d=${ey_7d}% 30d=${ey_30d}% 90d=${ey_90d}% 365d=${ey_365d}%`);
        console.log(`  payout_ratio (各周期): 7d=${protocol.tevRatio_7d} 30d=${protocol.tevRatio_30d} 90d=${protocol.tevRatio_90d} 365d=${protocol.tevRatio_365d}`);
      }
      updated++;
      continue;
    }

    // Sky 专属：TEV 用 DefiLlama dailyHoldersRevenue（Splitter 的 burn 部分，即 SBE 真实支出）
    // 原代码使用 fixedTevUsd: $13.724M（治理公告值），但实际每日波动，应动态拉取
    // Splitter 的 farm 部分（给 SKY stakers）不算 TEV（新铸造的 SKY + USDS yield，非市场回购）
    if (key === 'sky') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 sky... (DefiLlama dailyHoldersRevenue 口径)`);
      const marketCap = protocol.market_cap_usd || 0;
      if (!protocol.metrics) protocol.metrics = {};

      // 拉 holdersRevenue（TEV）和 revenue（Earning）两个口径
      const [holdersData, revenueData] = await Promise.all([
        getDefillamaFees('sky', 'dailyHoldersRevenue'),
        getDefillamaRevenue('sky'),
      ]);

      const calcY = (sum, days) => {
        if (sum == null || !marketCap) return null;
        const ann = days >= 365 ? 1 : (365 / days);
        return Math.round(sum * ann / marketCap * 10000) / 100;
      };

      if (holdersData) {
        protocol.metrics.tev_yield_7d_ann  = calcY(holdersData.sum7d,   7);
        protocol.metrics.tev_yield_30d_ann = calcY(holdersData.sum30d,  30);
        protocol.metrics.tev_yield_90d_ann = calcY(holdersData.sum90d,  90);
        protocol.shareholder_yield_percent         = calcY(holdersData.sum365d, 365);
      }
      if (revenueData) {
        protocol.metrics.trailing_7d_revenue_usd   = revenueData.revenue7d;
        protocol.metrics.trailing_30d_revenue_usd  = revenueData.revenue30d;
        protocol.metrics.trailing_90d_revenue_usd  = revenueData.revenue90d;
        protocol.metrics.trailing_365d_revenue_usd = revenueData.revenue365d;
        protocol.metrics.earning_yield_7d_ann  = calcY(revenueData.revenue7d,  7);
        protocol.metrics.earning_yield_30d_ann = calcY(revenueData.revenue30d, 30);
        protocol.metrics.earning_yield_90d_ann = calcY(revenueData.revenue90d, 90);
        protocol.total_yield_percent         = calcY(revenueData.revenue365d, 365);
      }

      // payout_ratio 动态反映 Splitter 的 burn 比例 —— 按各周期独立算
      if (holdersData && revenueData) {
        const calcRatio = (h, r) => (r > 0 && h != null ? Math.round(h / r * 10000) / 10000 : null);
        protocol.tevRatio_7d   = calcRatio(holdersData.sum7d,   revenueData.revenue7d);
        protocol.tevRatio_30d  = calcRatio(holdersData.sum30d,  revenueData.revenue30d);
        protocol.tevRatio_90d  = calcRatio(holdersData.sum90d,  revenueData.revenue90d);
        protocol.tevRatio_365d = calcRatio(holdersData.sum365d, revenueData.revenue365d);
        protocol.payout_ratio = protocol.tevRatio_365d;  // 顶层保持 365d
      }

      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'DefiLlama dailyHoldersRevenue = Splitter burn (SBE 真实支出) / dailyRevenue = 协议总归属';
      protocol.validation.tev_source = 'DefiLlama dailyHoldersRevenue (slug=sky)';
      protocol.validation.earning_source = 'DefiLlama dailyRevenue (slug=sky)';
      if (holdersData) {
        protocol.validation.burn_7d_usd   = Math.round(holdersData.sum7d);
        protocol.validation.burn_30d_usd  = Math.round(holdersData.sum30d);
        protocol.validation.burn_90d_usd  = Math.round(holdersData.sum90d);
        protocol.validation.burn_365d_usd = Math.round(holdersData.sum365d);
      }
      if (holdersData && holdersData.sum30d) {
        protocol.validation.burn_daily_avg_30d_usd = Math.round(holdersData.sum30d / 30);
      }
      protocol.validation.note = '2026-03 Splitter burn 参数大幅下调（日均从 ~$300k 降至 ~$37.6k，-87.5%）。365d 窗口包含下调前高峰，所以短周期 < 365d。';

      console.log(`  marketCap: $${(marketCap/1e9).toFixed(2)}B`);
      if (holdersData) console.log(`  HoldersRevenue: 7d=$${(holdersData.sum7d/1e6).toFixed(2)}M 30d=$${(holdersData.sum30d/1e6).toFixed(2)}M 90d=$${(holdersData.sum90d/1e6).toFixed(2)}M 365d=$${(holdersData.sum365d/1e6).toFixed(2)}M`);
      if (revenueData) console.log(`  Revenue:        7d=$${(revenueData.revenue7d/1e6).toFixed(2)}M 30d=$${(revenueData.revenue30d/1e6).toFixed(2)}M 90d=$${(revenueData.revenue90d/1e6).toFixed(2)}M 365d=$${(revenueData.revenue365d/1e6).toFixed(2)}M`);
      console.log(`  TEV Yield: 7d=${protocol.metrics.tev_yield_7d_ann}% 30d=${protocol.metrics.tev_yield_30d_ann}% 90d=${protocol.metrics.tev_yield_90d_ann}% 365d=${protocol.shareholder_yield_percent}%`);
      console.log(`  Earning:   7d=${protocol.metrics.earning_yield_7d_ann}% 30d=${protocol.metrics.earning_yield_30d_ann}% 90d=${protocol.metrics.earning_yield_90d_ann}% 365d=${protocol.total_yield_percent}%`);
      console.log(`  payout_ratio (dynamic): ${protocol.payout_ratio}`);
      updated++;
      continue;
    }

    // JustLend 专属：TEV 归零（2026-04-25 链上核实 + Boss 决策）
    // 链上发现 burn 的 JST 全部来自孙宇晨生态金库 TFTWNgDB...（持有 HTX/WIN/TUSD 系他的代币），
    // 属 pocket-to-pocket 做账式销毁（从项目方自持里拿出来转 Black Hole），不是市场 buyback，
    // 对流通量和价格无实际支撑。按方法论不算真 TEV。
    if (key === 'justlend') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 justlend... (pocket-to-pocket 做账销毁，TEV 归零)`);
      const burnHistPath = path.join(__dirname, '../data/protocols/justlend/burn-history.json');
      let burnHist = { burns: [] };
      try { burnHist = JSON.parse(fs.readFileSync(burnHistPath, 'utf8')); } catch {}
      const burns = burnHist.burns || [];
      const marketCap = protocol.market_cap_usd || 0;
      const circulatingSupply = 8_540_000_000;
      const jstPrice = marketCap > 0 ? marketCap / circulatingSupply : 0;

      if (!protocol.metrics) protocol.metrics = {};
      // TEV 全部归零
      protocol.metrics.tev_yield_7d_ann  = 0;
      protocol.metrics.tev_yield_30d_ann = 0;
      protocol.metrics.tev_yield_90d_ann = 0;
      protocol.shareholder_yield_percent         = 0;
      protocol.metrics.earning_yield_7d_ann  = 0;
      protocol.metrics.earning_yield_30d_ann = 0;
      protocol.metrics.earning_yield_90d_ann = 0;
      protocol.total_yield_percent         = 0;
      protocol.metrics.trailing_7d_revenue_usd   = 0;
      protocol.metrics.trailing_30d_revenue_usd  = 0;
      protocol.metrics.trailing_90d_revenue_usd  = 0;
      protocol.metrics.trailing_365d_revenue_usd = 0;

      protocol.tevStatus = 'none';
      protocol.confidence = 'low';
      protocol.payout_ratio = null;

      // 保留 burn 事件数据作为"供给侧事实"证据，不作为 TEV 来源
      const today = new Date();
      const sumJst = (days) => {
        const cutoff = new Date(today.getTime() - days * 86400000).toISOString().slice(0, 10);
        return burns.filter(b => b.date > cutoff).reduce((s, b) => s + (b.jst || 0), 0);
      };
      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'TEV 归零（pocket-to-pocket 做账销毁，非真市场 buyback）';
      protocol.validation.burn_7d_jst   = Math.round(sumJst(7));
      protocol.validation.burn_30d_jst  = Math.round(sumJst(30));
      protocol.validation.burn_90d_jst  = Math.round(sumJst(90));
      protocol.validation.burn_365d_jst = Math.round(sumJst(365));
      protocol.validation.jst_price_usd = Math.round(jstPrice * 1e6) / 1e6;
      protocol.validation.total_burned_jst = burnHist.total_burned_jst;
      protocol.validation.burn_events = burns.length;
      protocol.validation.tev_zero_reason = 'burn JST 源头是孙宇晨生态金库（TFTWNgDB... 持 HTX/WIN/TUSD 等），非协议收入买入，不构成真 TEV';
      protocol.validation.caveats = [
        '所有 burn 的 JST 来自同一地址 TFTWNgDBkQ5wQoP8RXpRznnHvAVV8x5jLu，该地址持仓包含 HTX/WIN/TUSD 等孙宇晨生态代币，基本可认定为项目方金库',
        '没有观察到对应 USDT/USDD 流出（协议收入换 JST）的证据，不是真市场 buyback',
        '对流通量和价格无实际支撑（本来就不在流通），不符合 TEV = token 持有人真实价值捕获 的定义',
        'DefiLlama justlend slug 只报 ~$500k/年 revenue（interest spread），侧面佐证协议真实对外分发收入很少',
        '如果未来发现 executor 真正从市场买 JST（看到 USDT/USDD 流出换取 JST 的链上证据），可重新评估',
      ];

      console.log(`  JST price: $${jstPrice.toFixed(6)} (mcap $${(marketCap/1e6).toFixed(1)}M)`);
      console.log(`  链上 burn 事件数: ${burns.length} (仅作供给侧事实记录)`);
      console.log(`  TEV Yield: 0% (pocket-to-pocket 做账销毁，不计入)`);
      updated++;
      continue;
    }

    // Aster 专属：TEV = Stage5/6 buyback wallet 的 ASTER 累积 × 当前价（类似 Hyperliquid AF）
    // 数据源：data/aster-onchain.json（由 update-aster-tev.py 每日维护，Moralis API）
    if (key === 'aster') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 aster... (Stage5/6 buyback treasury 口径)`);
      const onchainPath = path.join(__dirname, '../data/aster-onchain.json');
      let onchain = [];
      try { onchain = JSON.parse(fs.readFileSync(onchainPath, 'utf8')); } catch (e) {
        console.warn(`  ⚠️ aster-onchain.json 读取失败: ${e.message}`);
      }
      const marketCap = protocol.market_cap_usd || 0;
      const circulatingSupply = 2_460_000_000;  // Aster 流通量近似
      const asterPrice = marketCap > 0 ? marketCap / circulatingSupply : 0;

      // 按 N 天窗口汇总 ASTER inflow
      const today = new Date();
      const sumAster = (days) => {
        const cutoff = new Date(today.getTime() - days * 86400000).toISOString().slice(0, 10);
        return (onchain || []).filter(r => r.date > cutoff).reduce((s, r) => s + (r.aster || 0), 0);
      };
      const buy7d_aster   = sumAster(7);
      const buy30d_aster  = sumAster(30);
      const buy90d_aster  = sumAster(90);
      const buy365d_aster = sumAster(365);

      const calcYield = (aster_sum, days) => {
        if (!marketCap || !asterPrice) return 0;
        const usd = aster_sum * asterPrice;
        const ann = days >= 365 ? 1 : (365 / days);
        return Math.round(usd * ann / marketCap * 10000) / 100;
      };
      const tev_7d   = calcYield(buy7d_aster,   7);
      const tev_30d  = calcYield(buy30d_aster,  30);
      const tev_90d  = calcYield(buy90d_aster,  90);
      const tev_365d = calcYield(buy365d_aster, 365);

      if (!protocol.metrics) protocol.metrics = {};
      protocol.metrics.tev_yield_7d_ann  = tev_7d;
      protocol.metrics.tev_yield_30d_ann = tev_30d;
      protocol.metrics.tev_yield_90d_ann = tev_90d;
      protocol.shareholder_yield_percent         = tev_365d;
      // Aster 的 TEV = Earning（100% 买回 → stage 合约，用 treasury buyback 口径，等同 100% 分润）
      protocol.metrics.earning_yield_7d_ann  = tev_7d;
      protocol.metrics.earning_yield_30d_ann = tev_30d;
      protocol.metrics.earning_yield_90d_ann = tev_90d;
      protocol.total_yield_percent         = tev_365d;
      protocol.metrics.trailing_7d_revenue_usd   = Math.round(buy7d_aster * asterPrice);
      protocol.metrics.trailing_30d_revenue_usd  = Math.round(buy30d_aster * asterPrice);
      protocol.metrics.trailing_90d_revenue_usd  = Math.round(buy90d_aster * asterPrice);
      protocol.metrics.trailing_365d_revenue_usd = Math.round(buy365d_aster * asterPrice);

      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'A 口径：Stage5/6 buyback wallet 累积 ASTER × 当前价（treasury buyback，非真 burn）';
      protocol.validation.buy_7d_aster   = Math.round(buy7d_aster);
      protocol.validation.buy_30d_aster  = Math.round(buy30d_aster);
      protocol.validation.buy_90d_aster  = Math.round(buy90d_aster);
      protocol.validation.buy_365d_aster = Math.round(buy365d_aster);
      protocol.validation.aster_price_usd = Math.round(asterPrice * 10000) / 10000;
      protocol.validation.data_days = (onchain || []).length;
      protocol.validation.data_range = onchain && onchain.length
        ? { start: onchain[0].date, end: onchain[onchain.length - 1].date }
        : null;
      protocol.validation.caveats = [
        'Stage5/6 是 treasury buyback（wallet 持仓），部分 burn 部分给 community rewards，不全是真销毁',
        '2026-03-30 tokenomics 改革后新增 staking rewards（暂不计入 TEV）',
        'Moralis 免费 tier 可能滞后几天',
      ];

      console.log(`  ASTER price: $${asterPrice.toFixed(4)} (marketCap $${(marketCap/1e9).toFixed(2)}B ÷ ${(circulatingSupply/1e9).toFixed(2)}B supply)`);
      console.log(`  Buyback ASTER: 7d=${Math.round(buy7d_aster).toLocaleString()} / 30d=${Math.round(buy30d_aster).toLocaleString()} / 90d=${Math.round(buy90d_aster).toLocaleString()} / 365d=${Math.round(buy365d_aster).toLocaleString()}`);
      console.log(`  TEV Yield: 7d=${tev_7d}% 30d=${tev_30d}% 90d=${tev_90d}% 365d=${tev_365d}%`);
      updated++;
      continue;
    }

    // Uniswap 专属：TEV 只看链上 UNI 转入 0xdead（A 口径，Boss 2026-04-22 定）
    // 排除 >=10M UNI 的一次性治理事件（如 2025-12-27 Timelock 100M retroactive burn）
    if (key === 'uniswap') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 uniswap... (链上 0xdead burn 口径)`);
      const burnHistPath = path.join(__dirname, '../data/protocols/uniswap/burn-history.json');
      let burnHist = { daily: [], retro_events: [] };
      try { burnHist = JSON.parse(fs.readFileSync(burnHistPath, 'utf8')); } catch (e) {
        console.warn(`  ⚠️ burn-history.json 读取失败: ${e.message}`);
      }
      const marketCap = protocol.market_cap_usd || 0;
      const circulatingSupply = 633561603;  // CoinGecko circulating，近似值，可后续改为动态
      const uniPrice = marketCap > 0 && circulatingSupply > 0 ? marketCap / circulatingSupply : 0;

      // 按 N 天窗口求和持续 burn（排除 retro）
      const today = new Date();
      const sumBurn = (days) => {
        const cutoff = new Date(today.getTime() - days * 86400000).toISOString().slice(0, 10);
        return (burnHist.daily || []).filter(r => r.date > cutoff).reduce((s, r) => s + (r.uni || 0), 0);
      };
      const burn7d_uni   = sumBurn(7);
      const burn30d_uni  = sumBurn(30);
      const burn90d_uni  = sumBurn(90);
      const burn365d_uni = sumBurn(365);

      const usd = (uni) => uni * uniPrice;
      const calcY = (usdVal, days) => {
        if (!marketCap) return 0;
        const ann = days >= 365 ? 1 : (365 / days);
        return Math.round(usdVal * ann / marketCap * 10000) / 100;
      };
      const tev_7d   = calcY(usd(burn7d_uni),   7);
      const tev_30d  = calcY(usd(burn30d_uni),  30);
      const tev_90d  = calcY(usd(burn90d_uni),  90);
      const tev_365d = calcY(usd(burn365d_uni), 365);

      if (!protocol.metrics) protocol.metrics = {};
      protocol.metrics.tev_yield_7d_ann  = tev_7d;
      protocol.metrics.tev_yield_30d_ann = tev_30d;
      protocol.metrics.tev_yield_90d_ann = tev_90d;
      protocol.shareholder_yield_percent         = tev_365d;
      // Earning = TEV for uniswap (payout_ratio=1.0，所有 burn 归 token holder)
      protocol.metrics.earning_yield_7d_ann  = tev_7d;
      protocol.metrics.earning_yield_30d_ann = tev_30d;
      protocol.metrics.earning_yield_90d_ann = tev_90d;
      protocol.total_yield_percent         = tev_365d;
      // revenue 字段用 burn USD 填（反映 token holder 实得）
      protocol.metrics.trailing_7d_revenue_usd   = Math.round(usd(burn7d_uni));
      protocol.metrics.trailing_30d_revenue_usd  = Math.round(usd(burn30d_uni));
      protocol.metrics.trailing_90d_revenue_usd  = Math.round(usd(burn90d_uni));
      protocol.metrics.trailing_365d_revenue_usd = Math.round(usd(burn365d_uni));

      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'A 口径：365d UNI 转入 0xdead（链上）减去 >=10M UNI 一次性事件';
      protocol.validation.burn_7d_uni   = Math.round(burn7d_uni);
      protocol.validation.burn_30d_uni  = Math.round(burn30d_uni);
      protocol.validation.burn_90d_uni  = Math.round(burn90d_uni);
      protocol.validation.burn_365d_uni = Math.round(burn365d_uni);
      protocol.validation.retro_events_count = (burnHist.retro_events || []).length;
      protocol.validation.retro_total_uni = Math.round((burnHist.retro_events || []).reduce((s, r) => s + (r.amount || 0), 0));
      protocol.validation.uni_price_usd = Math.round(uniPrice * 100) / 100;
      protocol.validation.data_days = (burnHist.daily || []).length;
      protocol.validation.data_range = burnHist.daily && burnHist.daily.length
        ? { start: burnHist.daily[0].date, end: burnHist.daily[burnHist.daily.length-1].date }
        : null;

      console.log(`  UNI price: $${uniPrice.toFixed(2)} (marketCap $${(marketCap/1e9).toFixed(2)}B ÷ ${(circulatingSupply/1e6).toFixed(0)}M supply)`);
      console.log(`  Burn UNI: 7d=${Math.round(burn7d_uni).toLocaleString()} / 30d=${Math.round(burn30d_uni).toLocaleString()} / 90d=${Math.round(burn90d_uni).toLocaleString()} / 365d=${Math.round(burn365d_uni).toLocaleString()}`);
      console.log(`  Retro 排除: ${(burnHist.retro_events || []).length} 次, 共 ${Math.round((burnHist.retro_events || []).reduce((s, r) => s + (r.amount || 0), 0)/1e6)}M UNI`);
      console.log(`  TEV Yield: 7d=${tev_7d}% 30d=${tev_30d}% 90d=${tev_90d}% 365d=${tev_365d}%`);
      updated++;
      continue;
    }

    // PancakeSwap 专属：DefiLlama buyback&burn 口径 (dailyHoldersRevenue)
    // 数据源：data/protocols/pancakeswap/burn-history.json (update-pancakeswap-tev.py 维护)
    // 注：原链上 net deflation 口径因公共 BSC RPC 取消 archive 支持已失效，2026-06-14 改 DefiLlama
    if (key === 'pancakeswap') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 pancakeswap... (DefiLlama buyback&burn 口径)`);
      const histPath = path.join(__dirname, '../data/protocols/pancakeswap/burn-history.json');
      let hist = null;
      try { hist = JSON.parse(fs.readFileSync(histPath, 'utf8')); } catch (e) {
        console.warn(`  ⚠️ burn-history.json 读取失败: ${e.message}`); continue;
      }
      // net_burns key 用字符串 "7","30","90","365"，每项 {burn_usd, annualized_usd, yield_pct}
      const sm = hist.net_burns || {};
      const mcap = hist.market_cap_usd || protocol.market_cap_usd || 0;
      if (!protocol.metrics) protocol.metrics = {};
      protocol.market_cap_usd = mcap;
      protocol.metrics.current_market_cap_usd = mcap;
      protocol.metrics.tev_yield_7d_ann   = sm['7']?.yield_pct ?? 0;
      protocol.metrics.tev_yield_30d_ann  = sm['30']?.yield_pct ?? 0;
      protocol.metrics.tev_yield_90d_ann  = sm['90']?.yield_pct ?? 0;
      protocol.shareholder_yield_percent          = sm['365']?.yield_pct ?? 0;
      protocol.total_yield_percent      = protocol.shareholder_yield_percent;
      protocol.metrics.earning_yield_7d_ann  = protocol.metrics.tev_yield_7d_ann;
      protocol.metrics.earning_yield_30d_ann = protocol.metrics.tev_yield_30d_ann;
      protocol.metrics.earning_yield_90d_ann = protocol.metrics.tev_yield_90d_ann;
      protocol.metrics.trailing_7d_revenue_usd   = sm['7']?.burn_usd ?? 0;
      protocol.metrics.trailing_30d_revenue_usd  = sm['30']?.burn_usd ?? 0;
      protocol.metrics.trailing_90d_revenue_usd  = sm['90']?.burn_usd ?? 0;
      protocol.metrics.trailing_365d_revenue_usd = sm['365']?.burn_usd ?? 0;
      protocol.metrics.trailing_365d_tev_usd     = sm['365']?.burn_usd ?? 0;
      protocol.tevStatus = 'active';
      protocol.payout_ratio = 1.0;
      protocol.confidence = 'high';
      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'DefiLlama dailyHoldersRevenue (CAKE buyback&burn, gross)';
      protocol.validation.burn_7d_usd   = sm['7']?.burn_usd;
      protocol.validation.burn_30d_usd  = sm['30']?.burn_usd;
      protocol.validation.burn_90d_usd  = sm['90']?.burn_usd;
      protocol.validation.burn_365d_usd = sm['365']?.burn_usd;
      protocol.validation.cake_price_usd = hist.cake_price_usd;
      console.log(`  buyback&burn 365d: $${((sm['365']?.burn_usd||0)/1e6).toFixed(1)}M  (gross)`);
      console.log(`  TEV Yield: 7d=${sm['7']?.yield_pct}% 30d=${sm['30']?.yield_pct}% 90d=${sm['90']?.yield_pct}% 365d=${sm['365']?.yield_pct}%`);
      updated++;
      continue;
    }

    // ether.fi 专属：链上 buyback 路径无法识别 → TEV 归零（unverified）
    // Boss 2026-04-26 决策：类似 JustLend，链上看不到协议宣传的 buyback
    // 链上事实：Foundation Multisig 0x7A6A 365d 0 inflow，sETHFI 入金混入用户 stake，
    //           Uni V3 主池没有大单 buyback 模式，多 Gnosis Safe 间内部腾挪非市场买入
    if (key === 'etherfi') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 etherfi... (链上 buyback 路径不可识别 → TEV unverified)`);
      const histPath = path.join(__dirname, '../data/protocols/etherfi/buyback-history.json');
      let hist = null;
      try { hist = JSON.parse(fs.readFileSync(histPath, 'utf8')); } catch (e) {
        console.warn(`  ⚠️ buyback-history.json 读取失败: ${e.message}`); continue;
      }
      const sm = hist.summary || {};
      const mcap = hist.market_cap_usd || protocol.market_cap_usd || 0;
      if (!protocol.metrics) protocol.metrics = {};
      protocol.market_cap_usd = mcap;
      protocol.metrics.current_market_cap_usd = mcap;
      // TEV 全部归零（unverified）
      protocol.metrics.tev_yield_7d_ann   = 0;
      protocol.metrics.tev_yield_30d_ann  = 0;
      protocol.metrics.tev_yield_90d_ann  = 0;
      protocol.shareholder_yield_percent          = 0;
      protocol.total_yield_percent      = 0;
      protocol.metrics.earning_yield_7d_ann  = 0;
      protocol.metrics.earning_yield_30d_ann = 0;
      protocol.metrics.earning_yield_90d_ann = 0;
      protocol.metrics.trailing_7d_revenue_usd   = 0;
      protocol.metrics.trailing_30d_revenue_usd  = 0;
      protocol.metrics.trailing_90d_revenue_usd  = 0;
      protocol.metrics.trailing_365d_revenue_usd = 0;
      protocol.metrics.trailing_365d_tev_usd     = 0;
      protocol.tevStatus = 'none';
      protocol.payout_ratio = null;
      protocol.confidence = 'low';
      // 保留全部链上调研事实作为"供给侧记录"，未来如发现真实 executor 可恢复
      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'TEV unverified (链上 buyback 路径不可识别)';
      protocol.validation.sethfi_inflow_365d_ethfi_upper = sm['365d']?.ethfi;
      protocol.validation.sethfi_inflow_365d_usd_upper   = sm['365d']?.usd;
      protocol.validation.foundation_multisig_365d_inflow = hist.foundation_multisig_365d_inflow_ethfi;
      protocol.validation.foundation_multisig_status = hist.foundation_multisig_status;
      protocol.validation.ethfi_price_usd = hist.ethfi_price_usd;
      protocol.validation.tev_unverified_reason = 'DAO Proposal #11 宣称的 Withdrawal Revenue Buyback 链上不可识别：Foundation Multisig 0x7A6A41F353B3002751d94118aA7f4935dA39bB53 365d 入金=0；sETHFI 合约 365d 入金 128M ETHFI 含用户 stake 无法分离；Uni V3 主池无大单 buyback 模式；Foundation 出账只见 Gnosis Safe 间内部腾挪（非市场买入）';
      protocol.validation.caveats = [
        'Foundation Multisig 0x7A6A41F353B3002751d94118aA7f4935dA39bB53 过去 365 天 ETHFI 入金 = 0（链上确证）',
        'sETHFI 合约 0x86B5780b606940Eb59A062aA85a07959518c0161 365d 入金 128M ETHFI from 420 unique senders，包含 (a) 用户自主 stake (b) 协议侧 distribution (c) LayerZero 跨链 bridge - 无法分离三者',
        'ETHFI/WETH Uni V3 池 (0x06f00544...) 30d top 买家是 routing bot (0xbdb3ba9f, 745 笔小单, 持仓 ~2k ETHFI), 不是 buyback executor',
        'Foundation Multisig → 0x5ec5e6b4... → 0xa000244b... → 0x8f08b704... 多个 Gnosis Safe 间转账 = 内部 treasury 腾挪, 非协议市场 buyback',
        '可能解释: (a) buyback 实际未执行; (b) 在 Arbitrum/Base L2 执行; (c) 路径混入 sETHFI 入金中无法识别. 我们倾向 (a) 或 (c)',
        '如果未来发现真实 buyback executor 地址 (协议团队公开 / 链上模式变化), 可立即恢复 TEV 计算',
      ];
      console.log(`  Foundation Multisig 365d 入金: 0 ETHFI ← 与研究指向不符`);
      console.log(`  sETHFI 上界 (含用户 stake) 365d: ${(sm['365d']?.ethfi || 0).toLocaleString()} ETHFI = $${((sm['365d']?.usd||0)/1e6).toFixed(1)}M`);
      console.log(`  TEV Yield: 0% (unverified, 链上 buyback 路径不可识别)`);
      updated++;
      continue;
    }

    // Curve 专属：链上 Community Fund Treasury × 9 推算 + veCRV TVL
    // 数据源：data/protocols/curve/fee-history.json (update-curve-tev.py 维护)
    if (key === 'curve') {
      const protocol = protocols[key];
      if (!protocol) continue;
      console.log(`📊 curve... (链上 FeeAllocator × 9 推算口径)`);
      const histPath = path.join(__dirname, '../data/protocols/curve/fee-history.json');
      let hist = null;
      try { hist = JSON.parse(fs.readFileSync(histPath, 'utf8')); } catch (e) {
        console.warn(`  ⚠️ fee-history.json 读取失败: ${e.message}`); continue;
      }
      const sm = hist.summary || {};
      const mcap = hist.crv_market_cap_usd || protocol.market_cap_usd || 0;
      if (!protocol.metrics) protocol.metrics = {};
      protocol.market_cap_usd = mcap;
      protocol.metrics.current_market_cap_usd = mcap;
      // 默认主表显示 nominal yield (CRV 全市值分母)
      protocol.metrics.tev_yield_7d_ann   = sm['7d']?.yield_pct_nominal ?? 0;
      protocol.metrics.tev_yield_30d_ann  = sm['30d']?.yield_pct_nominal ?? 0;
      protocol.metrics.tev_yield_90d_ann  = sm['90d']?.yield_pct_nominal ?? 0;
      protocol.shareholder_yield_percent          = sm['365d']?.yield_pct_nominal ?? 0;
      protocol.total_yield_percent      = protocol.shareholder_yield_percent;
      protocol.metrics.earning_yield_7d_ann  = protocol.metrics.tev_yield_7d_ann;
      protocol.metrics.earning_yield_30d_ann = protocol.metrics.tev_yield_30d_ann;
      protocol.metrics.earning_yield_90d_ann = protocol.metrics.tev_yield_90d_ann;
      protocol.metrics.trailing_7d_revenue_usd   = sm['7d']?.vecrv_tev_usd ?? 0;
      protocol.metrics.trailing_30d_revenue_usd  = sm['30d']?.vecrv_tev_usd ?? 0;
      protocol.metrics.trailing_90d_revenue_usd  = sm['90d']?.vecrv_tev_usd ?? 0;
      protocol.metrics.trailing_365d_revenue_usd = sm['365d']?.vecrv_tev_usd ?? 0;
      protocol.metrics.trailing_365d_tev_usd     = sm['365d']?.vecrv_tev_usd ?? 0;
      protocol.tevStatus = 'active';
      protocol.payout_ratio = 0.9;  // FeeAllocator 90% to veCRV
      protocol.confidence = 'high';
      protocol.validation = protocol.validation || {};
      protocol.validation.method = 'Community Fund Treasury crvUSD inflow × 9 (FeeAllocator 90/10)';
      protocol.validation.crv_locked_in_vecrv = hist.crv_locked_in_vecrv;
      protocol.validation.vecrv_tvl_usd = hist.vecrv_tvl_usd;
      protocol.validation.lock_ratio_pct = hist.lock_ratio_pct;
      // 双口径：nominal vs veCRV-only
      protocol.validation.yield_vecrv_only_7d  = sm['7d']?.yield_pct_vecrv_only;
      protocol.validation.yield_vecrv_only_30d = sm['30d']?.yield_pct_vecrv_only;
      protocol.validation.yield_vecrv_only_90d = sm['90d']?.yield_pct_vecrv_only;
      protocol.validation.yield_vecrv_only_365d = sm['365d']?.yield_pct_vecrv_only;
      protocol.validation.caveats = hist.caveats || [];
      console.log(`  veCRV TEV 365d: $${((sm['365d']?.vecrv_tev_usd||0)/1e6).toFixed(2)}M (Treasury × 9)`);
      console.log(`  CRV 锁仓: ${(hist.crv_locked_in_vecrv||0).toLocaleString()} (${hist.lock_ratio_pct}% of circulating)`);
      console.log(`  TEV Yield: nominal 365d=${sm['365d']?.yield_pct_nominal}% / veCRV-only=${sm['365d']?.yield_pct_vecrv_only}%`);
      updated++;
      continue;
    }

    // 其他特殊协议：不更新市值和年度TEV，但拉 DefiLlama 收入计算多维度 yield
    if (SKIP_PROTOCOLS.includes(key)) {
      const protocol = protocols[key];
      if (!protocol) continue;
      if (!config.defillamaSlug) { console.log(`⏭️  ${key}: 跳过（无 DefiLlama slug）`); continue; }
      console.log(`📊 ${key}... (多维度 yield only)`);
      const revenueData = await getDefillamaRevenue(config.defillamaSlug);
      if (revenueData) {
        const marketCap = protocol.market_cap_usd || 0;
        if (!protocol.metrics) protocol.metrics = {};
        protocol.metrics.trailing_7d_revenue_usd = revenueData.revenue7d;
        protocol.metrics.trailing_30d_revenue_usd = revenueData.revenue30d;
        protocol.metrics.trailing_90d_revenue_usd = revenueData.revenue90d;
        protocol.metrics.trailing_365d_revenue_usd = revenueData.revenue365d;
        // 多维度年化 TEV Yield（用现有 payout_ratio 或从现有 yield 反推）
        const payout_ratio = config.payout_ratio || (marketCap > 0 && revenueData.revenue365d > 0 ? (protocol.shareholder_yield_percent / 100 * marketCap) / (revenueData.revenue365d * 365 / 365) / 1 : 0);
        const calcY = (rev, days) => {
          if (rev == null || !marketCap || !payout_ratio) return null;
          // 365d 不需要年化（已是 365 天累计）
          const annFactor = days >= 365 ? 1 : (365 / days);
          return Math.round(rev * annFactor * payout_ratio / marketCap * 10000) / 100;
        };
        const calcEY = (rev, days) => {
          if (rev == null || !marketCap) return null;
          const annFactor = days >= 365 ? 1 : (365 / days);
          return Math.round(rev * annFactor / marketCap * 10000) / 100;
        };
        protocol.metrics.tev_yield_7d_ann = calcY(revenueData.revenue7d, 7);
        protocol.metrics.tev_yield_30d_ann = calcY(revenueData.revenue30d, 30);
        protocol.metrics.tev_yield_90d_ann = calcY(revenueData.revenue90d, 90);
        protocol.metrics.earning_yield_7d_ann = calcEY(revenueData.revenue7d, 7);
        protocol.metrics.earning_yield_30d_ann = calcEY(revenueData.revenue30d, 30);
        protocol.metrics.earning_yield_90d_ann = calcEY(revenueData.revenue90d, 90);
        // 新增：365d 顶层字段（之前 SKIP 分支漏算，导致 365d yield 停留在手写值）
        const tev365 = calcY(revenueData.revenue365d, 365);
        const earning365 = calcEY(revenueData.revenue365d, 365);
        if (tev365 != null) protocol.shareholder_yield_percent = tev365;
        if (earning365 != null) protocol.total_yield_percent = earning365;
        updated++;
        console.log(`  rev 7d=$${((revenueData.revenue7d||0)/1e6).toFixed(2)}M, 365d=$${((revenueData.revenue365d||0)/1e6).toFixed(2)}M`);
        console.log(`  yield 7d=${protocol.metrics.tev_yield_7d_ann}% 30d=${protocol.metrics.tev_yield_30d_ann}% 90d=${protocol.metrics.tev_yield_90d_ann}% 365d=${protocol.shareholder_yield_percent}%`);
      }
      await new Promise(r => setTimeout(r, 2000));
      continue;
    }
    
    console.log(`📊 ${key}...`);
    
    const protocol = protocols[key];
    if (!protocol) {
      console.log(`  ❌ 协议不存在`);
      errors++;
      continue;
    }
    
    // 获取 Revenue（部分协议指定 dailyHoldersRevenue，搭配 payout_ratio: 1.0）
    const revenueData = await getDefillamaRevenue(config.defillamaSlug, config.defillamaDataType || 'dailyRevenue');
    if (!revenueData) {
      errors++;
      continue;
    }
    
    // 获取市值（CoinGecko + CMC 双源）
    const marketCap = await getMarketCap(config.coingeckoId, config.cmcSlug);
    if (!marketCap) {
      errors++;
      continue;
    }
    
    // 计算 TEV
    let tev365d;
    if (config.fixedTevUsd) {
      // 固定 TEV（如 Aave）
      tev365d = config.fixedTevUsd;
    } else if (config.payout_ratio !== undefined && config.payout_ratio !== null) {
      // 按比例计算（含 payout_ratio=0 的明确归零，不再反推）
      tev365d = revenueData.revenue365d * config.payout_ratio;
    } else {
      // 从现有 TEV Yield 反推（仅 payout_ratio 完全未定义时）
      const tevYield = protocol.shareholder_yield_percent || 0;
      tev365d = tevYield * marketCap / 100;
    }
    
    // 计算多维度年化 TEV Yield
    const calcYield = (revenue, days) => {
      if (revenue == null || !marketCap) return null;
      const annualized = revenue * (365 / days);
      const tev = config.fixedTevUsd ? config.fixedTevUsd : annualized * (config.payout_ratio || 0);
      return Math.round(tev / marketCap * 10000) / 100;
    };

    const tevYield = marketCap > 0 ? (tev365d / marketCap * 100) : 0;
    // fixedTevUsd 协议：TEV Yield 各周期相同（预算固定），但 Earning Yield 仍反映收入波动
    const tevYield7d  = config.fixedTevUsd ? tevYield : calcYield(revenueData.revenue7d, 7);
    const tevYield30d = config.fixedTevUsd ? tevYield : calcYield(revenueData.revenue30d, 30);
    const tevYield90d = config.fixedTevUsd ? tevYield : calcYield(revenueData.revenue90d, 90);

    // 更新数据
    if (!protocol.metrics) protocol.metrics = {};

    const oldMcap = protocol.market_cap_usd;
    const oldRevenue = protocol.metrics.trailing_365d_revenue_usd;
    const oldTevYield = protocol.shareholder_yield_percent;

    protocol.market_cap_usd = marketCap;
    protocol.metrics.current_market_cap_usd = marketCap;
    protocol.metrics.trailing_7d_revenue_usd = revenueData.revenue7d;
    protocol.metrics.trailing_30d_revenue_usd = revenueData.revenue30d;
    protocol.metrics.trailing_90d_revenue_usd = revenueData.revenue90d;
    protocol.metrics.trailing_365d_revenue_usd = revenueData.revenue365d;
    protocol.metrics.trailing_365d_tev_usd = tev365d;
    protocol.metrics.trailing_30d_tev_usd = tev365d / 12;
    protocol.metrics.tev_yield_7d_ann = tevYield7d;
    protocol.metrics.tev_yield_30d_ann = tevYield30d;
    protocol.metrics.tev_yield_90d_ann = tevYield90d;
    protocol.shareholder_yield_percent = Math.round(tevYield * 100) / 100;

    // 多维度年化 Earning Yield = annualized revenue / market_cap
    const calcEarningYield = (revenue, days) => {
      if (revenue == null || !marketCap) return null;
      return Math.round(revenue * (365 / days) / marketCap * 10000) / 100;
    };
    protocol.metrics.earning_yield_7d_ann = calcEarningYield(revenueData.revenue7d, 7);
    protocol.metrics.earning_yield_30d_ann = calcEarningYield(revenueData.revenue30d, 30);
    protocol.metrics.earning_yield_90d_ann = calcEarningYield(revenueData.revenue90d, 90);
    protocol.total_yield_percent = calcEarningYield(revenueData.revenue365d, 365) || protocol.total_yield_percent;
    
    // 输出变化
    console.log(`  市值: $${(oldMcap/1e6).toFixed(1)}M → $${(marketCap/1e6).toFixed(1)}M`);
    console.log(`  Revenue: $${((oldRevenue||0)/1e6).toFixed(1)}M → $${(revenueData.revenue365d/1e6).toFixed(1)}M`);
    console.log(`  TEV Yield: ${oldTevYield||0}% → ${tevYield.toFixed(2)}%`);
    
    updated++;
    
    // CoinGecko 限流 - 增加间隔
    await new Promise(r => setTimeout(r, 3000));
  }
  
  // === 股东回报拆分（dividend vs buyback）+ 风格分类 ===
  // 不变量：dividend_yield + buyback_yield ≡ tev_yield（每周期）。回购 = tev - dividend，强制自洽。
  for (const [pid, protocol] of Object.entries(allData.protocols)) {
    const m = protocol.metrics || (protocol.metrics = {});
    const vr = VALUE_RETURN[pid] || 'buyback';
    const div = protocol._divYld || null;  // mixed 分支预存的分红 yield（按周期）
    const splitOne = (tev, key) => {
      tev = tev || 0;
      let d;
      if (!tev) d = 0;
      else if (vr === 'dividend') d = tev;
      else if (vr === 'mixed' && div) d = Math.min(div[key] || 0, tev);
      else d = 0;  // buyback
      d = Math.round(d * 100) / 100;
      return { d, b: Math.round((tev - d) * 100) / 100 };
    };
    const s365 = splitOne(protocol.shareholder_yield_percent, '365');
    protocol.dividend_yield_percent = s365.d;
    protocol.buyback_yield_percent  = s365.b;
    for (const [n, field] of [['7', 'tev_yield_7d_ann'], ['30', 'tev_yield_30d_ann'], ['90', 'tev_yield_90d_ann']]) {
      const s = splitOne(m[field], n);
      m['dividend_yield_' + n + 'd_ann'] = s.d;
      m['buyback_yield_'  + n + 'd_ann'] = s.b;
    }
    // 风格：现金牛（在实际向持有人还钱）vs 成长（基本不还钱，按 P/S + 增速估）
    // 阈值 1%：把 Uniswap(~0.66%, fee switch 基本关) / Lido(0) 等近零回报归成长；
    // Curve/Aster/Maple 等虽然 yield 不高但有真实资本返还 → 现金牛（风格是性质不是量级）
    protocol.style = (protocol.shareholder_yield_percent >= 1 && protocol.tevStatus === 'active') ? 'cash_cow' : 'growth';
    delete protocol._divYld;
  }

  // === Snapshot 合并 post-pass（M1：PRD 5.4 消费 Financial Snapshot）===
  // 从 data/snapshots/<pid>.json 读取损益表/估值字段，写入 all-protocols.json
  // 前端主表/详情页据此渲染 收入/毛利/净利/净利率/增速 列
  const SNAPSHOTS_DIR = path.join(__dirname, '../data/snapshots');
  for (const [pid, protocol] of Object.entries(allData.protocols)) {
    const snapPath = path.join(SNAPSHOTS_DIR, `${pid}.json`);
    if (!fs.existsSync(snapPath)) continue;
    try {
      const snap = JSON.parse(fs.readFileSync(snapPath, 'utf8'));
      const inc = snap.income_statement || {};
      const rev = inc.revenue?.revenue_included || {};
      const val = snap.valuation || {};
      const hr = snap.holder_returns?.summary || {};
      const bs = snap.balance_sheet || {};
      // 损益表（365d 口径）
      protocol.financial_snapshot = {
        entity_type: inc.revenue?.entity_type || null,
        revenue_usd_365d: rev.total_usd_365d ?? null,
        revenue_included: rev,
        gross_profit_usd_365d: inc.gross_profit?.gross_profit_usd_365d ?? null,
        lp_share_cost_usd_365d: inc.gross_profit?.lp_share_cost_usd_365d ?? null,
        emission_cost_usd_365d: inc.token_emission_cost?.usd_365d ?? null,
        emission_treatment: inc.token_emission_cost?.treatment || 'none',
        net_income_usd_365d: inc.net_income?.net_income_usd_365d ?? null,
        gross_margin_percent: inc.margins?.gross_margin_percent ?? null,
        net_margin_percent: inc.margins?.net_margin_percent ?? null,
        growth_yoy_percent: inc.revenue?.growth_yoy_percent ?? null,
        // 估值（派生）
        pe: val.pe ?? null,
        ps: val.ps ?? null,
        pb: val.pb ?? null,
        ev_revenue: val.ev_revenue ?? null,
        payout_ratio: val.payout_ratio ?? null,
        // 股东回报 summary
        shareholder_returns_usd_365d: hr.shareholder_returns_usd_365d ?? null,
        // 验证状态
        verification_status: snap.verification?.status || 'partial',
        as_of: snap.as_of || null,
      };
      // 顶层便捷字段（主表列直接用）
      protocol.revenue_usd_365d = rev.total_usd_365d ?? null;
      protocol.gross_profit_usd_365d = inc.gross_profit?.gross_profit_usd_365d ?? null;
      protocol.net_income_usd_365d = inc.net_income?.net_income_usd_365d ?? null;
      protocol.net_margin_percent = inc.margins?.net_margin_percent ?? null;
      protocol.growth_yoy_percent = inc.revenue?.growth_yoy_percent ?? null;
      protocol.entity_type = inc.revenue?.entity_type || null;
      // 平台币口径（方案 A）：P/S == P/E，tooltip 标注收入=赋能口径
      if (protocol.entity_type === 'platform_token' && val.ps != null && val.pe == null) {
        protocol.financial_snapshot.pe = protocol.financial_snapshot.ps;
        protocol.financial_snapshot.ps = protocol.financial_snapshot.pe;
      }
    } catch (e) {
      console.warn(`  ⚠️ 合并 snapshot ${pid} 失败: ${e.message}`);
    }
  }

  // 写入文件
  if (!dryRun && updated > 0) {
    allData.generated_at = new Date().toISOString();
    fs.writeFileSync(DATA_FILE, JSON.stringify(allData, null, 2));
    console.log(`\n✅ 已更新 ${updated} 个协议`);

    // 同步回写每个协议的 config.json，保持首页与详情页数据一致
    for (const [pid, protocol] of Object.entries(allData.protocols)) {
      const configPath = path.join(__dirname, `../data/protocols/${pid}/config.json`);
      if (!fs.existsSync(configPath)) continue;
      try {
        const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        // 同步动态计算字段
        cfg.market_cap_usd = protocol.market_cap_usd;
        cfg.shareholder_yield_percent = protocol.shareholder_yield_percent;
        cfg.total_yield_percent = protocol.total_yield_percent;
        cfg.payout_ratio = protocol.payout_ratio;
        cfg.dividend_yield_percent = protocol.dividend_yield_percent;
        cfg.buyback_yield_percent = protocol.buyback_yield_percent;
        cfg.style = protocol.style;
        if (!cfg.tev_data) cfg.tev_data = {};
        cfg.tev_data.shareholder_yield_percent = protocol.shareholder_yield_percent;
        cfg.tev_data.market_cap_usd = protocol.market_cap_usd;
        cfg.tev_data.annual_tev_usd = (protocol.metrics || {}).trailing_365d_tev_usd;
        cfg.tev_data.calculation_date = new Date().toISOString().split('T')[0];
        // 同步 validation 到 tev_data.validation，避免详情页显示旧值
        if (protocol.validation) {
          cfg.tev_data.validation = { ...(cfg.tev_data.validation || {}), ...protocol.validation };
        }
        if (protocol.metrics) {
          cfg.metrics = { ...cfg.metrics, ...protocol.metrics };
        }
        fs.writeFileSync(configPath, JSON.stringify(cfg, null, 2));
      } catch (e) {
        console.warn(`  ⚠️ 回写 ${pid}/config.json 失败: ${e.message}`);
      }
    }
    console.log(`📋 已同步 config.json`);
  } else if (dryRun) {
    console.log(`\n🔍 预览完成，${updated} 个协议将被更新`);
  }
  
  if (errors > 0) {
    console.log(`⚠️ ${errors} 个错误`);
  }
}

main().catch(console.error);
