#!/usr/bin/env node
/**
 * Fetch TEV (HoldersRevenue) history from DefiLlama for all Active protocols.
 * Aggregates daily data into monthly records and writes tev-records.json files.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const PROTOCOLS = [
  { id: 'aave', slug: 'aave', mechanism: 'buyback_burn', name: 'AAVE Buyback', startDate: '2025-04-09' },
  { id: 'sky', slug: 'sky', mechanism: 'buyback_burn', name: 'Smart Burn Engine', startDate: '2023-10-01' },
  { id: 'pendle', slug: 'pendle', mechanism: 've_reward', name: 'vePENDLE Revenue Share', startDate: '2023-07-01' },
  { id: 'curve', slug: 'curve-finance', mechanism: 've_reward', name: 'veCRV Fee Distribution', startDate: '2020-09-01' },
  { id: 'gmx', slug: 'gmx', mechanism: 'staking_reward', name: 'GMX Staking Rewards', startDate: '2021-09-01' },
  { id: 'dydx', slug: 'dydx', mechanism: 'staking_reward', name: 'DYDX Staker Fee Distribution', startDate: '2023-10-01' },
  { id: 'maple', slug: 'maple', mechanism: 'staking_reward', name: 'SYRUP Staking Fee Share', startDate: '2024-01-01' },
  { id: 'pancakeswap', slug: 'pancakeswap', mechanism: 'buyback_burn', name: 'CAKE Buyback & Burn', startDate: '2021-04-01' },
  { id: 'radiant', slug: 'radiant-capital', mechanism: 'direct_distribution', name: 'dLP Fee Distribution', startDate: '2023-01-01' },
  { id: 'etherfi', slug: 'ether.fi', mechanism: 'buyback_accumulate', name: 'ETHFI Buyback', startDate: '2025-04-25' },
  { id: 'ethena', slug: 'ethena', mechanism: 'staking_reward', name: 'sENA Revenue Share', startDate: '2024-04-01' },
];

const DATA_DIR = path.join(__dirname, '..', 'data', 'protocols');

function fetch(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'TEV-Dashboard/1.0' } }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error(`JSON parse error for ${url}: ${e.message}`)); }
      });
      res.on('error', reject);
    }).on('error', reject);
  });
}

function toYYYYMM(ts) {
  const d = new Date(ts * 1000);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
}

function toQuarter(ts) {
  const d = new Date(ts * 1000);
  const q = Math.ceil((d.getUTCMonth() + 1) / 3);
  return `${d.getUTCFullYear()}-Q${q}`;
}

function toDate(ts) {
  return new Date(ts * 1000).toISOString().split('T')[0];
}

async function fetchProtocol(proto) {
  console.log(`\nFetching ${proto.id}...`);

  // Try holdersRevenue first
  let url = `https://api.llama.fi/summary/fees/${proto.slug}?dataType=dailyHoldersRevenue`;
  let data;
  try {
    data = await fetch(url);
  } catch (e) {
    console.log(`  holdersRevenue failed, trying revenue: ${e.message}`);
    url = `https://api.llama.fi/summary/fees/${proto.slug}?dataType=dailyRevenue`;
    try {
      data = await fetch(url);
    } catch (e2) {
      console.log(`  revenue also failed: ${e2.message}`);
      return null;
    }
  }

  const chart = data.totalDataChart;
  if (!chart || !Array.isArray(chart)) {
    console.log(`  No chart data found`);
    return null;
  }

  // Filter non-zero entries
  const nonZero = chart.filter(([ts, val]) => val > 0);
  console.log(`  Total data points: ${chart.length}, non-zero: ${nonZero.length}`);
  console.log(`  All-time total: $${(data.totalAllTime || 0).toLocaleString()}`);
  console.log(`  30d total: $${(data.total30d || 0).toLocaleString()}`);

  // Aggregate by month
  const monthly = {};
  for (const [ts, val] of nonZero) {
    const month = toYYYYMM(ts);
    if (!monthly[month]) monthly[month] = { total: 0, days: 0, firstTs: ts, lastTs: ts };
    monthly[month].total += val;
    monthly[month].days++;
    monthly[month].lastTs = ts;
  }

  // Build records
  const records = [];
  for (const [month, agg] of Object.entries(monthly).sort()) {
    records.push({
      id: `${proto.id}-${proto.mechanism.replace(/_/g, '-')}-${month}`,
      date: `${month}-01`,
      type: 'aggregate',
      mechanism: proto.mechanism === 'buyback_burn' ? proto.name :
                 proto.mechanism === 'buyback_accumulate' ? proto.name :
                 proto.mechanism === 've_reward' ? proto.name :
                 proto.mechanism === 'staking_reward' ? proto.name :
                 proto.mechanism === 'direct_distribution' ? proto.name : proto.name,
      amount_usd: Math.round(agg.total),
      period: month,
      days_with_data: agg.days,
      source: {
        type: 'api',
        provider: 'DefiLlama',
        endpoint: url,
        data_type: 'dailyHoldersRevenue',
        methodology: data.methodology?.HoldersRevenue || data.childProtocols?.[0]?.methodology?.HoldersRevenue || 'See DefiLlama methodology'
      },
      notes: `Monthly aggregate from ${agg.days} days of data`
    });
  }

  // Quarterly summary
  const quarterly = {};
  for (const [ts, val] of nonZero) {
    const q = toQuarter(ts);
    if (!quarterly[q]) quarterly[q] = 0;
    quarterly[q] += val;
  }

  // Build mechanism summary
  const byMechanism = {};
  byMechanism[proto.mechanism] = Math.round(nonZero.reduce((s, [_, v]) => s + v, 0));

  const result = {
    protocol: proto.id,
    updated_at: new Date().toISOString(),
    data_source: 'DefiLlama API (dailyHoldersRevenue)',
    data_source_url: url,
    records: records,
    summary: {
      total_returns_usd: Math.round(nonZero.reduce((s, [_, v]) => s + v, 0)),
      total_30d_usd: data.total30d || 0,
      by_mechanism: byMechanism,
      by_period: Object.fromEntries(
        Object.entries(quarterly).sort().map(([k, v]) => [k, Math.round(v)])
      )
    }
  };

  console.log(`  Generated ${records.length} monthly records`);
  console.log(`  Total TEV: $${result.summary.total_returns_usd.toLocaleString()}`);

  return result;
}

async function main() {
  console.log('=== TEV History Fetcher ===');
  console.log(`Fetching data for ${PROTOCOLS.length} protocols...\n`);

  const results = {};
  const errors = [];

  for (const proto of PROTOCOLS) {
    try {
      const result = await fetchProtocol(proto);
      if (result) {
        results[proto.id] = result;

        // Write tev-records.json
        const dir = path.join(DATA_DIR, proto.id);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        const filePath = path.join(dir, 'tev-records.json');
        fs.writeFileSync(filePath, JSON.stringify(result, null, 2));
        console.log(`  ✅ Written to ${filePath}`);
      } else {
        errors.push({ id: proto.id, error: 'No data' });
      }
    } catch (e) {
      console.error(`  ❌ Error: ${e.message}`);
      errors.push({ id: proto.id, error: e.message });
    }

    // Rate limit
    await new Promise(r => setTimeout(r, 1500));
  }

  // Summary
  console.log('\n=== Summary ===');
  console.log(`Successfully processed: ${Object.keys(results).length}/${PROTOCOLS.length}`);
  if (errors.length > 0) {
    console.log('Errors:');
    for (const e of errors) console.log(`  ${e.id}: ${e.error}`);
  }

  // Print total TEV by protocol
  console.log('\nTEV by Protocol:');
  for (const [id, data] of Object.entries(results).sort((a, b) => b[1].summary.total_returns_usd - a[1].summary.total_returns_usd)) {
    console.log(`  ${id}: $${data.summary.total_returns_usd.toLocaleString()} (${data.records.length} months)`);
  }
}

main().catch(console.error);
