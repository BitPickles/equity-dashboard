#!/usr/bin/env node
/**
 * Fetch historical data from DefiLlama and CoinGecko
 * Updates daily JSON files with fees, revenue (TEV proxy), prices
 */

const fs = require('fs');
const path = require('path');

const PROTOCOLS = [
  { id: 'uniswap', coingecko: 'uniswap', ticker: 'UNI' },
  { id: 'aave', coingecko: 'aave', ticker: 'AAVE' },
  { id: 'pendle', coingecko: 'pendle', ticker: 'PENDLE' },
  { id: 'sky', coingecko: 'maker', ticker: 'MKR' },
  { id: 'maple', coingecko: 'maple', ticker: 'SYRUP' },
  { id: 'gmx', coingecko: 'gmx', ticker: 'GMX' },
  { id: 'dydx', coingecko: 'dydx-chain', ticker: 'DYDX' },
  { id: 'ether.fi', coingecko: 'ether-fi', ticker: 'ETHFI' },
  { id: 'curve-dex', coingecko: 'curve-dao-token', ticker: 'CRV' },
  { id: 'hyperliquid', coingecko: 'hyperliquid', ticker: 'HYPE' },
];

const DATA_DIR = path.join(__dirname, '../data/daily');

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
  return res.json();
}

async function fetchDefiLlamaFees(protocolId) {
  console.log(`  Fetching DefiLlama fees for ${protocolId}...`);
  const [feesData, revenueData, holdersRevenueData] = await Promise.all([
    fetchJSON(`https://api.llama.fi/summary/fees/${protocolId}?dataType=dailyFees`),
    fetchJSON(`https://api.llama.fi/summary/fees/${protocolId}?dataType=dailyRevenue`),
    fetchJSON(`https://api.llama.fi/summary/fees/${protocolId}?dataType=dailyHoldersRevenue`).catch(() => ({ totalDataChart: [] })),
  ]);
  
  const fees = new Map();
  const revenue = new Map();
  const holdersRevenue = new Map();
  
  for (const [ts, val] of feesData.totalDataChart || []) {
    const date = new Date(ts * 1000).toISOString().split('T')[0];
    fees.set(date, val);
  }
  
  for (const [ts, val] of revenueData.totalDataChart || []) {
    const date = new Date(ts * 1000).toISOString().split('T')[0];
    revenue.set(date, val);
  }
  
  // holdersRevenue 是真正的 TEV（分给代币持有者的部分）
  for (const [ts, val] of holdersRevenueData.totalDataChart || []) {
    const date = new Date(ts * 1000).toISOString().split('T')[0];
    holdersRevenue.set(date, val);
  }
  
  console.log(`    Fees: ${fees.size} days, Revenue: ${revenue.size} days, HoldersRevenue: ${holdersRevenue.size} days`);
  return { fees, revenue, holdersRevenue };
}

async function fetchCoinGeckoPrices(coingeckoId, startDate) {
  console.log(`  Fetching CoinGecko prices for ${coingeckoId}...`);
  
  // CoinGecko market_chart/range needs unix timestamps
  const from = Math.floor(new Date(startDate).getTime() / 1000);
  const to = Math.floor(Date.now() / 1000);
  
  const url = `https://api.coingecko.com/api/v3/coins/${coingeckoId}/market_chart/range?vs_currency=usd&from=${from}&to=${to}`;
  const data = await fetchJSON(url);
  
  const prices = new Map();
  const marketCaps = new Map();
  
  for (const [ts, price] of data.prices || []) {
    const date = new Date(ts).toISOString().split('T')[0];
    prices.set(date, price);
  }
  
  for (const [ts, mcap] of data.market_caps || []) {
    const date = new Date(ts).toISOString().split('T')[0];
    marketCaps.set(date, mcap);
  }
  
  console.log(`    Prices: ${prices.size} days`);
  return { prices, marketCaps };
}

function groupByMonth(records) {
  const months = new Map();
  for (const rec of records) {
    const month = rec.date.slice(0, 7); // YYYY-MM
    if (!months.has(month)) months.set(month, []);
    months.get(month).push(rec);
  }
  return months;
}

async function processProtocol(protocol) {
  console.log(`\n=== Processing ${protocol.id} ===`);
  
  const protocolDir = path.join(DATA_DIR, protocol.id);
  if (!fs.existsSync(protocolDir)) {
    fs.mkdirSync(protocolDir, { recursive: true });
  }
  
  // Fetch data
  const { fees, revenue, holdersRevenue } = await fetchDefiLlamaFees(protocol.id);
  await sleep(500); // Rate limit
  
  // Get date range from fees
  const allDates = Array.from(fees.keys()).sort();
  if (allDates.length === 0) {
    console.log('  No fee data found, skipping');
    return;
  }
  
  const startDate = allDates[0];
  console.log(`  Date range: ${startDate} to ${allDates[allDates.length - 1]}`);
  
  // Fetch prices (may fail due to rate limits)
  let prices = new Map();
  let marketCaps = new Map();
  try {
    const priceData = await fetchCoinGeckoPrices(protocol.coingecko, startDate);
    prices = priceData.prices;
    marketCaps = priceData.marketCaps;
  } catch (err) {
    console.log(`  CoinGecko error: ${err.message} (will use existing price data)`);
  }
  await sleep(1000); // CoinGecko rate limit
  
  // Build records
  const records = [];
  for (const date of allDates) {
    // TEV = holdersRevenue（分给代币持有者的部分），如果没有则用 revenue
    const tevValue = holdersRevenue.get(date) ?? revenue.get(date) ?? 0;
    records.push({
      date,
      price_usd: prices.get(date) || null,
      market_cap_usd: marketCaps.get(date) || null,
      daily_fees_usd: fees.get(date) || 0,
      daily_revenue_usd: revenue.get(date) || 0,
      daily_holders_revenue_usd: holdersRevenue.get(date) || 0,
      // TEV = holdersRevenue（真正分给持有者的收入）
      daily_tev_usd: tevValue,
      tev_source: holdersRevenue.has(date) ? 'defillama_holdersRevenue' : 'defillama_revenue',
    });
  }
  
  // Group by month and write files
  const months = groupByMonth(records);
  let filesWritten = 0;
  
  for (const [month, monthRecords] of months) {
    const filePath = path.join(protocolDir, `${month}.json`);
    
    // Merge with existing data if present
    let existing = { records: [] };
    if (fs.existsSync(filePath)) {
      try {
        existing = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      } catch {}
    }
    
    // Merge records (new data overwrites)
    const existingMap = new Map(existing.records?.map(r => [r.date, r]) || []);
    for (const rec of monthRecords) {
      const old = existingMap.get(rec.date) || {};
      existingMap.set(rec.date, {
        ...old,
        ...rec,
        // Keep existing price if new is null
        price_usd: rec.price_usd ?? old.price_usd ?? null,
        market_cap_usd: rec.market_cap_usd ?? old.market_cap_usd ?? null,
      });
    }
    
    const merged = Array.from(existingMap.values()).sort((a, b) => a.date.localeCompare(b.date));
    
    const output = {
      protocol: protocol.id,
      period: month,
      source: 'defillama+coingecko',
      fetched_at: new Date().toISOString(),
      record_count: merged.length,
      records: merged,
    };
    
    fs.writeFileSync(filePath, JSON.stringify(output, null, 2));
    filesWritten++;
  }
  
  // Write latest.json
  const latestRecord = records[records.length - 1];
  const trailing30dTev = records.slice(-30).reduce((sum, r) => sum + (r.daily_tev_usd || 0), 0);
  const trailing30dRevenue = records.slice(-30).reduce((sum, r) => sum + (r.daily_revenue_usd || 0), 0);
  const trailing365dTev = records.slice(-365).reduce((sum, r) => sum + (r.daily_tev_usd || 0), 0);
  const trailing365dFees = records.slice(-365).reduce((sum, r) => sum + (r.daily_fees_usd || 0), 0);
  const trailing365dRevenue = records.slice(-365).reduce((sum, r) => sum + (r.daily_revenue_usd || 0), 0);
  const annualizedTev = trailing30dTev * 12;
  const marketCap = latestRecord.market_cap_usd || 0;
  const tevYield = marketCap > 0 ? annualizedTev / marketCap : 0;
  
  const latest = {
    protocol: protocol.id,
    updated_at: new Date().toISOString(),
    latest_record: latestRecord,
    metrics: {
      trailing_30d_shareholder_returns_usd: trailing30dTev,
      trailing_30d_fees_usd: records.slice(-30).reduce((sum, r) => sum + (r.daily_fees_usd || 0), 0),
      trailing_30d_revenue_usd: trailing30dRevenue,
      trailing_365d_shareholder_returns_usd: trailing365dTev,
      trailing_365d_fees_usd: trailing365dFees,
      trailing_365d_revenue_usd: trailing365dRevenue,
      annualized_returns_usd: annualizedTev,
      current_market_cap_usd: marketCap,
      tev_yield: (tevYield * 100).toFixed(2) + '%',
      return_yield_decimal: tevYield,
      calculated_at: new Date().toISOString(),
    },
    data_range: {
      start: allDates[0],
      end: allDates[allDates.length - 1],
      total_days: allDates.length,
    },
  };
  
  fs.writeFileSync(path.join(protocolDir, 'latest.json'), JSON.stringify(latest, null, 2));
  
  console.log(`  Written ${filesWritten} monthly files + latest.json`);
}

async function main() {
  console.log('=== DefiLlama Data Fetcher ===');
  console.log(`Output: ${DATA_DIR}`);
  
  for (const protocol of PROTOCOLS) {
    try {
      await processProtocol(protocol);
    } catch (err) {
      console.error(`Error processing ${protocol.id}:`, err.message);
    }
    await sleep(1000);
  }
  
  console.log('\n=== Done ===');
}

main().catch(console.error);
