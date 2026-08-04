// Helper functions for rendering analyst notes

function notesToMarkdown(notes) {
  if (typeof notes === "string") return notes;
  
  // Sky special formatting
  if (notes && notes.overview && notes.burn_ratio) {
    const ov = notes.overview;
    const br = notes.burn_ratio;
    
    let md = `### 📊 概览\n\n`;
    md += `| 指标 | 值 |\n`;
    md += `|------|-----|\n`;
    md += `| 最近 12 个月 TEV | ${ov.tev_12m} |\n`;
    md += `| 最新月度 TEV | ${ov.latest_month} |\n`;
    md += `| 机制 | ${ov.mechanism} |\n`;
    md += `| 收益来源 | ${ov.yield_source} |\n`;
    
    md += `\n### 🔥 Burn 比例\n\n`;
    md += `> 当前比例: **${br.current}** (${br.current * 100}%) · 通过 **${br.governance}** 调整\n\n`;
    md += `| 日期 | 变更 | Burn 比例 |\n`;
    md += `|------|-------|----------|\n`;
    notes.historical_changes.forEach(c => {
      md += `| ${c.date} | ${(c.from * 100).toFixed(0)}% → ${(c.to * 100).toFixed(0)}% | ${c.to} |\n`;
    });
    
    md += `\n### 📜 合约\n\n`;
    md += `| 合约 | 地址 |\n`;
    md += `|------|------|\n`;
    Object.entries(notes.contracts).forEach(([name, addr]) => {
      md += `| ${name} | \`${addr}\` |\n`;
    });
    
    md += `\n### 🔗 相关链接\n\n`;
    md += `- [治理投票](${notes.links.governance}) - Sky Executive Vote\n`;
    md += `- [Burn Engine](${notes.links.burn_engine}) - BlockAnalitica\n`;
    md += `- [API](${notes.links.api}) - DefiLlama HoldersRevenue\n`;
    
    md += `\n### 💡 机制说明\n\n`;
    md += notes.mechanism_note + `\n`;
    
    return md;
  }
  
  // Maple special formatting
  if (notes && notes.overview && notes.ratio_timeline) {
    const ov = notes.overview;
    
    let md = `### 📊 概览\n\n`;
    md += `| 指标 | 值 |\n`;
    md += `|------|-----|\n`;
    md += `| 当前回购比例 | **${ov.current_ratio}** |\n`;
    md += `| 机制 | ${ov.mechanism} |\n`;
    md += `| 执行频率 | ${ov.frequency} |\n`;
    md += `| 收益来源 | ${ov.yield_source} |\n`;
    
    md += `\n### 📈 比例时间线 (20% → 25%)\n\n`;
    md += `| 时段 | 比例 | MIP | 详情 |\n`;
    md += `|------|------|-----|------|\n`;
    notes.ratio_timeline.forEach(t => {
      md += `| ${t.period} | ${(t.ratio * 100).toFixed(0)}% | [${t.mip}](https://maple.finance/governance/proposals) | ${t.details} |\n`;
    });
    
    md += `\n### 💰 历史回购数据\n\n`;
    md += `| 时期 | 回购花费 (USD) | 回购数量 (SYRUP) |\n`;
    md += `|------|-----------------|-------------------|\n`;
    if (notes.buyback_data.q1_2025) {
      const d = notes.buyback_data.q1_2025;
      md += `| Q1 2025 | $${d.usd.toLocaleString()} | ${d.syrup.toLocaleString()} |\n`;
    }
    if (notes.buyback_data.h1_2025) {
      const d = notes.buyback_data.h1_2025;
      md += `| H1 2025 | $${d.usd.toLocaleString()} | ${d.syrup.toLocaleString()} |\n`;
    }
    if (notes.buyback_data.q4_2025) {
      const d = notes.buyback_data.q4_2025;
      md += `| Q4 2025 | — | ${d.syrup.toLocaleString()} (${d.note}) |\n`;
    }
    
    md += `\n### 📜 MIP 提案\n\n`;
    Object.entries(notes.mip_proposals).forEach(([mip, desc]) => {
      md += `- **${mip}**: ${desc}\n`;
    });
    
    md += `\n### 🔗 相关链接\n\n`;
    md += `- [治理投票](${notes.links.governance}) - Maple Governance\n`;
    md += `- [文档](${notes.links.docs}) - Maple Docs\n`;
    md += `- [Transparency](${notes.links.transparency}) - Maple Transparency\n`;
    
    md += `\n### 💡 机制说明\n\n`;
    md += notes.mechanism_note + `\n`;
    
    md += `\n### 📊 数据源\n\n`;
    md += `DefiLlama **Revenue** × **25%** (当前官方口径)\n`;
    md += `> Protocol Revenue ≈ DeFiLlama Revenue（管理费/服务费/策略费/起始费）`;
    
    return md;
  }
  
  // Default for other protocols
  var md = "";
  for (var key in notes) {
    var value = notes[key];
    var label = key.replace(/_/g, " ");
    if (key === "historical_changes" && Array.isArray(value)) {
      md += "\\n### " + label + "\\n";
      value.forEach(function(change) {
        md += "- **" + change.date + "**: " + change.change + " (ratio = " + change.ratio + ") - " + change.exec_vote + "\\n";
      });
    } else if (key === "tevlama_urls" && Array.isArray(value)) {
      md += "\\n### Data Sources\\n";
      value.forEach(function(url) {
        md += "`" + url + "`\\n";
      });
    } else if (key === "contracts" && typeof value === "object") {
      md += "\\n### Contracts\\n";
      for (var cName in value) {
        md += "- **" + cName + "**: `" + value[cName] + "`\\n";
      }
    } else if (key === "note" && typeof value === "string") {
      md += "\\n> " + value + "\\n";
    } else {
      md += "- **" + label + "**: `" + value + "`\\n";
    }
  }
  return md;
}
