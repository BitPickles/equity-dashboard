#!/usr/bin/env node
/**
 * Fix Radiant (wrong slug) and Ethena (needs revenue data instead of holdersRevenue)
 */
const fs = require('fs');
const path = require('path');
const https = require('https');

const DATA_DIR = path.join(__dirname, '..', 'data', 'protocols');

function fetch(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'TEV-Dashboard/1.0' } }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error(`JSON parse: ${e.message}`)); }
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

async function processProtocol(id, slug, dataType, mechanism, mechName) {
  const url = `https://api.llama.fi/summary/fees/${slug}?dataType=${dataType}`;
  console.log(`Fetching ${id} from ${url}`);
  
  const data = await fetch(url);
  const chart = data.totalDataChart;
  const nonZero = chart.filter(([ts, val]) => val > 0);
  
  console.log(`  Total: ${chart.length}, non-zero: ${nonZero.length}`);
  console.log(`  All-time: $${(data.totalAllTime || 0).toLocaleString()}`);

  // Monthly aggregation
  const monthly = {};
  for (const [ts, val] of nonZero) {
    const month = toYYYYMM(ts);
    if (!monthly[month]) monthly[month] = { total: 0, days: 0 };
    monthly[month].total += val;
    monthly[month].days++;
  }

  const records = Object.entries(monthly).sort().map(([month, agg]) => ({
    id: `${id}-${mechanism.replace(/_/g, '-')}-${month}`,
    date: `${month}-01`,
    type: 'aggregate',
    mechanism: mechName,
    amount_usd: Math.round(agg.total),
    period: month,
    days_with_data: agg.days,
    source: {
      type: 'api',
      provider: 'DefiLlama',
      endpoint: url,
      data_type: dataType,
      methodology: data.childProtocols?.[0]?.methodology?.HoldersRevenue || data.childProtocols?.[0]?.methodology?.Revenue || 'See DefiLlama'
    }
  }));

  const quarterly = {};
  for (const [ts, val] of nonZero) {
    const q = toQuarter(ts);
    if (!quarterly[q]) quarterly[q] = 0;
    quarterly[q] += val;
  }

  const result = {
    protocol: id,
    updated_at: new Date().toISOString(),
    data_source: `DefiLlama API (${dataType})`,
    data_source_url: url,
    records,
    summary: {
      total_returns_usd: Math.round(nonZero.reduce((s, [_, v]) => s + v, 0)),
      total_30d_usd: data.total30d || 0,
      by_mechanism: { [mechanism]: Math.round(nonZero.reduce((s, [_, v]) => s + v, 0)) },
      by_period: Object.fromEntries(Object.entries(quarterly).sort().map(([k, v]) => [k, Math.round(v)]))
    }
  };

  const dir = path.join(DATA_DIR, id);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'tev-records.json'), JSON.stringify(result, null, 2));
  console.log(`  ✅ Written ${records.length} records, total: $${result.summary.total_returns_usd.toLocaleString()}`);
}

async function main() {
  // Fix Radiant - correct slug is "radiant"
  await processProtocol('radiant', 'radiant', 'dailyHoldersRevenue', 'direct_distribution', 'dLP Fee Distribution');

  await new Promise(r => setTimeout(r, 1500));

  // Fix Ethena - use dailyRevenue since holdersRevenue shows $0
  // (sENA revenue is tracked differently in DefiLlama)
  await processProtocol('ethena', 'ethena', 'dailyRevenue', 'staking_reward', 'sENA Revenue Share');
}

main().catch(console.error);
