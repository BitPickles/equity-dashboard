#!/usr/bin/env node
/**
 * DeFi TEV Dashboard - Data Collection Script
 * 
 * Fetches:
 * - Fee/Revenue data from DefiLlama
 * - Price/Market cap data from CoinGecko
 * 
 * Usage:
 *   node collect-data.js              # Collect all protocols
 *   node collect-data.js aave pendle  # Collect specific protocols
 */

const fs = require('fs');
const path = require('path');

// Protocol configurations
const PROTOCOLS = {
  aave: {
    name: 'Aave',
    defillama_slug: 'aave',
    coingecko_id: 'aave',
    payout_ratio: 0.318, // Default TEV distribution ratio (from manual data)
  },
  pendle: {
    name: 'Pendle',
    defillama_slug: 'pendle',
    coingecko_id: 'pendle',
    payout_ratio: 0.80, // 80% to vePENDLE holders
  },
  sky: {
    name: 'Sky (MakerDAO)',
    defillama_slug: 'makerdao',
    coingecko_id: 'maker', // Still MKR on CoinGecko
    payout_ratio: 0.70, // ~70% to buybacks
  },
  uniswap: {
    name: 'Uniswap',
    defillama_slug: 'uniswap',
    coingecko_id: 'uniswap',
    payout_ratio: 0.0, // Currently 0% fee switch
  },
  hype: {
    name: 'Hyperliquid',
    defillama_slug: 'hyperliquid',
    coingecko_id: 'hyperliquid',
    payout_ratio: 0.99, // 99% to Assistance Fund buyback
  },
};

const DATA_DIR = path.join(__dirname, '..', 'data');
const DAILY_DIR = path.join(DATA_DIR, 'daily');

// Rate limiting - CoinGecko free tier is strict (~10-30 req/min)
const DELAY_MS = 2000; // 2s between API calls
const COINGECKO_DELAY_MS = 8000; // 8s between CoinGecko calls (to avoid 429)
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Fetch with error handling and retries
 */
async function fetchWithRetry(url, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, {
        headers: {
          'User-Agent': 'DeFi-TEV-Dashboard/1.0',
          'Accept': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`  Attempt ${i + 1}/${retries} failed: ${error.message}`);
      if (i < retries - 1) {
        await sleep(2000 * (i + 1)); // Exponential backoff
      } else {
        throw error;
      }
    }
  }
}

/**
 * Fetch fee data from DefiLlama
 */
async function fetchDefiLlamaFees(slug) {
  const url = `https://api.llama.fi/summary/fees/${slug}`;
  console.log(`  Fetching DefiLlama fees: ${url}`);
  
  const data = await fetchWithRetry(url);
  
  return {
    total24h: data.total24h,
    total7d: data.total7d,
    total30d: data.total30d,
    totalAllTime: data.totalAllTime,
    change1d: data.change_1d,
    // Historical daily data
    dailyChart: data.totalDataChart || [],
    // Chain breakdown (if available)
    chainBreakdown: data.totalDataChartBreakdown || [],
  };
}

/**
 * Fetch price and market data from CoinGecko
 */
async function fetchCoinGeckoData(coinId, days = 90, retries = 5) {
  // First get current price and market cap
  const priceUrl = `https://api.coingecko.com/api/v3/simple/price?ids=${coinId}&vs_currencies=usd&include_market_cap=true&include_24hr_change=true`;
  console.log(`  Fetching CoinGecko price...`);
  
  let priceData;
  for (let i = 0; i < retries; i++) {
    try {
      priceData = await fetchWithRetry(priceUrl, 1); // Single attempt, we handle retries here
      break;
    } catch (error) {
      console.log(`  CoinGecko rate limited, waiting ${COINGECKO_DELAY_MS * (i + 1)}ms...`);
      await sleep(COINGECKO_DELAY_MS * (i + 1));
      if (i === retries - 1) throw error;
    }
  }
  
  await sleep(COINGECKO_DELAY_MS);
  
  // Then get historical data
  const historyUrl = `https://api.coingecko.com/api/v3/coins/${coinId}/market_chart?vs_currency=usd&days=${days}`;
  console.log(`  Fetching CoinGecko history (${days} days)...`);
  
  let historyData;
  for (let i = 0; i < retries; i++) {
    try {
      historyData = await fetchWithRetry(historyUrl, 1);
      break;
    } catch (error) {
      console.log(`  CoinGecko rate limited, waiting ${COINGECKO_DELAY_MS * (i + 1)}ms...`);
      await sleep(COINGECKO_DELAY_MS * (i + 1));
      if (i === retries - 1) throw error;
    }
  }
  
  return {
    current: {
      price_usd: priceData[coinId]?.usd,
      market_cap_usd: priceData[coinId]?.usd_market_cap,
      change_24h: priceData[coinId]?.usd_24h_change,
    },
    history: {
      prices: historyData.prices || [], // [[timestamp, price], ...]
      market_caps: historyData.market_caps || [],
    },
  };
}

/**
 * Process and merge data for a protocol
 */
function processProtocolData(protocol, fees, prices) {
  const records = [];
  
  // Build a map of prices by date
  const priceByDate = {};
  const mcapByDate = {};
  
  for (const [timestamp, price] of prices.history.prices) {
    const date = new Date(timestamp).toISOString().split('T')[0];
    priceByDate[date] = price;
  }
  
  for (const [timestamp, mcap] of prices.history.market_caps) {
    const date = new Date(timestamp).toISOString().split('T')[0];
    mcapByDate[date] = mcap;
  }
  
  // Process fee data
  for (const [timestamp, feeValue] of fees.dailyChart) {
    const date = new Date(timestamp * 1000).toISOString().split('T')[0];
    
    // Handle different fee data formats
    let dailyFee = 0;
    if (typeof feeValue === 'number') {
      dailyFee = feeValue;
    } else if (typeof feeValue === 'object') {
      // Sum all chain/version fees
      dailyFee = Object.values(feeValue).reduce((sum, chainFees) => {
        if (typeof chainFees === 'number') return sum + chainFees;
        if (typeof chainFees === 'object') {
          return sum + Object.values(chainFees).reduce((s, v) => s + (typeof v === 'number' ? v : 0), 0);
        }
        return sum;
      }, 0);
    }
    
    // Calculate TEV (estimated based on protocol's distribution ratio)
    const config = PROTOCOLS[protocol];
    const dailyTev = dailyFee * config.payout_ratio;
    
    records.push({
      date,
      price_usd: priceByDate[date] || null,
      market_cap_usd: mcapByDate[date] || null,
      daily_fees_usd: Math.round(dailyFee),
      daily_tev_usd: Math.round(dailyTev),
      tev_ratio_used: config.payout_ratio,
    });
  }
  
  // Sort by date
  records.sort((a, b) => a.date.localeCompare(b.date));
  
  return records;
}

/**
 * Calculate TEV Yield metrics
 */
function calculateMetrics(records) {
  if (records.length < 30) {
    return null;
  }
  
  const last30 = records.slice(-30);
  const trailing30dTev = last30.reduce((sum, r) => sum + (r.daily_tev_usd || 0), 0);
  const annualizedTev = trailing30dTev * 12;
  const currentMcap = records[records.length - 1]?.market_cap_usd;
  
  if (!currentMcap) return null;
  
  return {
    trailing_30d_shareholder_returns_usd: Math.round(trailing30dTev),
    annualized_tev_usd: Math.round(annualizedTev),
    current_market_cap_usd: Math.round(currentMcap),
    tev_yield: (annualizedTev / currentMcap * 100).toFixed(2) + '%',
    tev_yield_decimal: annualizedTev / currentMcap,
    calculated_at: new Date().toISOString(),
  };
}

/**
 * Group records by month
 */
function groupByMonth(records) {
  const months = {};
  
  for (const record of records) {
    const month = record.date.slice(0, 7); // YYYY-MM
    if (!months[month]) {
      months[month] = [];
    }
    months[month].push(record);
  }
  
  return months;
}

/**
 * Save data to files
 */
function saveData(protocol, records, metrics) {
  const protocolDir = path.join(DAILY_DIR, protocol);
  
  // Ensure directory exists
  if (!fs.existsSync(protocolDir)) {
    fs.mkdirSync(protocolDir, { recursive: true });
  }
  
  // Group by month and save
  const byMonth = groupByMonth(records);
  
  for (const [month, monthRecords] of Object.entries(byMonth)) {
    const filePath = path.join(protocolDir, `${month}.json`);
    const data = {
      protocol,
      period: month,
      source: 'auto',
      fetched_at: new Date().toISOString(),
      record_count: monthRecords.length,
      records: monthRecords,
    };
    
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
    console.log(`  Saved ${monthRecords.length} records to ${filePath}`);
  }
  
  // Save latest metrics summary
  const summaryPath = path.join(protocolDir, 'latest.json');
  const summary = {
    protocol,
    updated_at: new Date().toISOString(),
    latest_record: records[records.length - 1],
    metrics,
    data_range: {
      start: records[0]?.date,
      end: records[records.length - 1]?.date,
      total_days: records.length,
    },
  };
  
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
  console.log(`  Saved summary to ${summaryPath}`);
}

/**
 * Main collection function
 */
async function collectProtocol(protocolKey) {
  const config = PROTOCOLS[protocolKey];
  if (!config) {
    console.error(`Unknown protocol: ${protocolKey}`);
    return null;
  }
  
  console.log(`\n📊 Collecting data for ${config.name}...`);
  
  try {
    // Fetch fees from DefiLlama
    const fees = await fetchDefiLlamaFees(config.defillama_slug);
    console.log(`  ✓ DefiLlama: ${fees.dailyChart.length} daily records, $${(fees.total30d / 1e6).toFixed(2)}M 30d fees`);
    
    await sleep(DELAY_MS);
    
    // Fetch prices from CoinGecko
    const prices = await fetchCoinGeckoData(config.coingecko_id);
    console.log(`  ✓ CoinGecko: $${prices.current.price_usd?.toFixed(2)} price, $${(prices.current.market_cap_usd / 1e9).toFixed(2)}B mcap`);
    
    // Process and merge
    const records = processProtocolData(protocolKey, fees, prices);
    console.log(`  ✓ Processed ${records.length} daily records`);
    
    // Calculate metrics
    const metrics = calculateMetrics(records);
    if (metrics) {
      console.log(`  ✓ TEV Yield: ${metrics.tev_yield} (30d rolling annualized)`);
    }
    
    // Save
    saveData(protocolKey, records, metrics);
    
    return { records, metrics };
  } catch (error) {
    console.error(`  ✗ Failed to collect ${config.name}: ${error.message}`);
    return null;
  }
}

/**
 * Main entry point
 */
async function main() {
  console.log('═══════════════════════════════════════════════════');
  console.log('  DeFi TEV Dashboard - Data Collection');
  console.log('  ' + new Date().toISOString());
  console.log('═══════════════════════════════════════════════════');
  
  // Parse command line args
  const args = process.argv.slice(2);
  const protocolsToCollect = args.length > 0 
    ? args.filter(p => PROTOCOLS[p])
    : Object.keys(PROTOCOLS);
  
  if (args.length > 0 && protocolsToCollect.length === 0) {
    console.error(`Unknown protocols: ${args.join(', ')}`);
    console.log(`Available: ${Object.keys(PROTOCOLS).join(', ')}`);
    process.exit(1);
  }
  
  console.log(`\nProtocols: ${protocolsToCollect.join(', ')}`);
  
  const results = {};
  
  for (const protocol of protocolsToCollect) {
    results[protocol] = await collectProtocol(protocol);
    await sleep(COINGECKO_DELAY_MS * 2); // Extra delay between protocols for CoinGecko rate limit
  }
  
  // Summary
  console.log('\n═══════════════════════════════════════════════════');
  console.log('  Summary');
  console.log('═══════════════════════════════════════════════════');
  
  for (const [protocol, data] of Object.entries(results)) {
    if (data?.metrics) {
      console.log(`  ${PROTOCOLS[protocol].name.padEnd(20)} TEV Yield: ${data.metrics.tev_yield}`);
    } else {
      console.log(`  ${PROTOCOLS[protocol].name.padEnd(20)} ✗ Failed or insufficient data`);
    }
  }
  
  console.log('\n✓ Collection complete\n');
}

main().catch(console.error);
