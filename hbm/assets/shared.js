/* =====================================================================
   存储三巨头估值看板 · 共享脚本  shared.js   (vanilla ES module, 无框架)
   ---------------------------------------------------------------------
   引入（放在页面末尾即可，模块内部会自行等待 DOM / ECharts）：
     <script type="module">
       import * as SK from './assets/shared.js';
       // 或按需： import { echartsReady, loadJSON, COMPANY_COLORS, ... } from './assets/shared.js';
     </script>

   —— 导出速览（下方每个都有详细注释）——
     echartsReady               Promise<echarts>  —— 从 CDN 加载 ECharts，resolve 出全局 echarts
     loadJSON(path)             Promise<any>      —— fetch + json，失败抛错（前端只读数据）
     COMPANY_COLORS             {ticker: hex}     —— MU / SK Hynix / Samsung 主色
     COMPANY_NAMES              {ticker: 名称}
     TIER_COLORS                {S..D: hex}       —— 信源档位色
     TIER_DEFS                  {S..D: 释义}      —— 徽章 tooltip 文案
     C                          {loss,peak,link,...} —— 常用语义色（读 CSS 变量兜底）
     FONT_SANS / FONT_MONO      字体名字符串（供 ECharts textStyle 用）
     baseOption({dark})         object            —— 统一 ECharts 基础 option（浅/深色主题）
     lineSeries(opts)           object            —— 一条折线 series（含亏损断点 connectNulls:false）
     initChart(el, option)      echarts 实例      —— init + setOption + 注册自适应 resize
     autoResize(charts)         () => void        —— 批量 resize（window resize 已自动挂）
     disposeChart(el)           void              —— dispose 容器上的实例并移出集合（innerHTML 替换前调）
     tierBadgeHTML(tier, size)  string            —— 信源徽章 HTML 片段
     srcPillHTML({...})         string            —— 信源 pill（徽章+来源+图标）HTML 片段
     injectTopNav(el, active)   void              —— 可选：注入统一顶栏导航
     NAV_LINKS                  [{href,label,key}]—— 导航映射（看板 / 公司 / 电话会）
   ===================================================================== */

/* ------------------------------------------------------------------ *
 * 1) 常量：公司色 / 档位色 / 语义色 / 字体
 *    与 shared.css 的 CSS 变量保持同一套确切值。
 * ------------------------------------------------------------------ */
export const COMPANY_COLORS = {
  'MU':        '#2E6FE6',   // Micron
  '000660.KS': '#F5822A',   // SK Hynix
  '005930.KS': '#7B61FF',   // Samsung
};

export const COMPANY_NAMES = {
  'MU':        'Micron',
  '000660.KS': 'SK Hynix',
  '005930.KS': 'Samsung',
};

export const TIER_COLORS = {
  S: '#1A7F4E',  // 监管原文
  A: '#0E8C8C',  // 第三方硬数据 / 官方 IR
  B: '#5B6B8C',  // 产业链
  C: '#8A8F98',  // 媒体
  D: '#B8790E',  // AI / 估算
};

export const TIER_DEFS = {
  S: '监管原文（SEC/DART/8-K）',
  A: '公司官方 IR，非监管归档',
  B: '产业链数据',
  C: '媒体',
  D: 'AI/估算',
};

/* 语义色：优先读 CSS 变量（单一真源），拿不到就用硬编码兜底 */
function cssVar(name, fallback) {
  try {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  } catch (e) { return fallback; }
}
export const C = {
  ink:      cssVar('--ink',   '#1A1D23'),
  muted:    cssVar('--muted', '#5C6470'),
  faint:    cssVar('--faint', '#8A909B'),
  loss:     cssVar('--loss',  '#E5484D'),   // 亏损 / 负值 / NM 红
  peak:     cssVar('--peak',  '#F0B429'),   // 峰值黄
  link:     cssVar('--link',  '#2E6FE6'),
  softLine: cssVar('--border-soft', '#EDEFF2'),
  darkCanvas: cssVar('--dark-canvas', '#0D1117'),
};

export const FONT_SANS = 'Noto Sans SC';
export const FONT_MONO = 'IBM Plex Mono';

/* 导航映射：全站统一顶栏 看板 · 公司 · 电话会（阅读页/跨季对比/数据与来源不进导航） */
export const NAV_LINKS = [
  { key: 'board',     href: 'index.html',   label: '看板' },
  { key: 'companies', href: '公司.html',     label: '公司' },
  { key: 'fabs',      href: '扩产.html',     label: '扩产' },
  { key: 'calls',     href: '电话会.html',   label: '电话会' },
];

/* ------------------------------------------------------------------ *
 * 2) echartsReady —— 动态加载 ECharts，暴露 ready Promise
 *    - 主源 jsDelivr，失败自动回退 unpkg。
 *    - 若页面已用 <script> 手动引了 echarts，直接复用 window.echarts。
 *    用法：const echarts = await echartsReady; ...
 * ------------------------------------------------------------------ */
const ECHARTS_SRCS = [
  'https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js',
  'https://unpkg.com/echarts@5/dist/echarts.min.js',
];

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('load failed: ' + src));
    document.head.appendChild(s);
  });
}

export const echartsReady = (async () => {
  if (window.echarts) return window.echarts;
  for (const src of ECHARTS_SRCS) {
    try {
      await loadScript(src);
      if (window.echarts) return window.echarts;
    } catch (e) { /* 尝试下一个源 */ }
  }
  throw new Error('ECharts 加载失败（jsDelivr / unpkg 均不可达）');
})();

/* ------------------------------------------------------------------ *
 * 3) loadJSON(path) —— 只读数据帮手
 *    用法：const data = await loadJSON('data/valuation.json');
 * ------------------------------------------------------------------ */
export async function loadJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error('loadJSON ' + path + ' → HTTP ' + res.status);
  return res.json();
}

/* ------------------------------------------------------------------ *
 * 4) ECharts 主题 / 基础 option 工厂
 *    baseOption({dark}) 返回浅色（页内）或深色（导出帧）主题的骨架：
 *    背景、字体、坐标轴、网格线、tooltip 已按设计语言设好。
 *    页面再往里塞 series / yAxis 覆盖即可。
 * ------------------------------------------------------------------ */
function axisText(dark)  { return dark ? '#9AA3B2' : '#8A909B'; }
function splitLine(dark) { return dark ? '#232936' : C.softLine; }

export function baseOption({ dark = false, categories = null } = {}) {
  const fs = dark ? 14 : 11.5;
  const opt = {
    animation: !dark,
    backgroundColor: dark ? C.darkCanvas : 'transparent',
    textStyle: { fontFamily: FONT_SANS },
    grid: { left: 58, right: 30, top: 34, bottom: 30 },
    tooltip: { trigger: 'axis', confine: true, textStyle: { fontSize: 12 } },
    xAxis: {
      type: 'category',
      data: categories || undefined,
      boundaryGap: true,
      axisLine: { lineStyle: { color: splitLine(dark) } },
      axisTick: { show: false },
      axisLabel: { color: axisText(dark), fontSize: fs, fontFamily: FONT_MONO },
    },
    yAxis: {
      type: 'value',
      nameTextStyle: { color: axisText(dark), fontSize: fs - 1 },
      axisLabel: { color: axisText(dark), fontSize: fs, fontFamily: FONT_MONO },
      splitLine: { lineStyle: { color: splitLine(dark) } },
    },
    series: [],
  };
  return opt;
}

/* 一条公司折线：默认 connectNulls:false —— 亏损期（如 P/E 的 NM）自然断开，不插值。
   opts: { name, data, color, dark, dashed, yAxisIndex, symbol, symbolSize } */
export function lineSeries(opts = {}) {
  const { name, data, color, dark = false, dashed = false,
          yAxisIndex = 0, symbol = 'circle', symbolSize } = opts;
  return {
    name, type: 'line', data, color, yAxisIndex,
    connectNulls: false,                 // 亏损期断点：不连线、不插值
    symbol,
    symbolSize: symbolSize != null ? symbolSize : (dark ? 9 : 7),
    lineStyle: {
      width: dashed ? (dark ? 2.2 : 1.5) : (dark ? 3.5 : 2.5),
      type: dashed ? 'dashed' : 'solid',
    },
  };
}

/* ------------------------------------------------------------------ *
 * 5) 图表实例帮手
 *    initChart：init + setOption(...,true) + 记入内部集合，随窗口自适应。
 *    autoResize：手动触发批量 resize（一般不用手调，window.resize 已挂）。
 * ------------------------------------------------------------------ */
const _charts = new Set();
let _resizeHooked = false;

export function initChart(el, option) {
  if (!window.echarts || !el) return null;
  let inst = window.echarts.getInstanceByDom(el);
  if (!inst) inst = window.echarts.init(el);
  inst.setOption(option, true);
  inst.resize();
  _charts.add(inst);
  if (!_resizeHooked) {
    _resizeHooked = true;
    window.addEventListener('resize', () => autoResize());
  }
  return inst;
}

export function autoResize() {
  _charts.forEach((c) => { try { c.resize(); } catch (e) {} });
}

/* disposeChart(el)：按容器元素释放图表实例 —— dispose 并从 _charts 集合移除。
   页面用 innerHTML 整体替换含图容器（如 Tab 切换）前必须调用，
   否则旧实例被 _charts 与 resize 监听器引用，连同脱离文档的 canvas 永不释放。 */
export function disposeChart(el) {
  if (!window.echarts || !el) return;
  const inst = window.echarts.getInstanceByDom(el);
  if (!inst) return;
  _charts.delete(inst);
  try { inst.dispose(); } catch (e) { /* 已释放等边界情况静默 */ }
}

/* ------------------------------------------------------------------ *
 * 6) 信源徽章 / pill 渲染帮手（返回 HTML 字符串，前端 innerHTML 用）
 * ------------------------------------------------------------------ */
/* tierBadgeHTML('S', 'md') → 带对应档位色的方块徽章。
   size ∈ 'lg'(22) | 'md'(17) | 'sm'(15) | 'xs'(13)，默认 'md'。 */
export function tierBadgeHTML(tier, size = 'md') {
  const t = String(tier || 'C').toUpperCase();
  return `<span class="tier tier--${t.toLowerCase()} tier--${size}">${t}</span>`;
}

/* srcPillHTML({tier, source, icon, tip, size}) → 徽章 + 来源名 + 方式图标 的 pill。
   例：srcPillHTML({tier:'S', source:'SEC EDGAR', icon:'⚙️', tip:'…'}) */
export function srcPillHTML({ tier, source = '', icon = '', tip = '', size = 'sm' } = {}) {
  const cls = size === 'sm' ? 'src-pill src-pill--sm' : 'src-pill';
  const badge = tierBadgeHTML(tier, size === 'sm' ? 'xs' : 'sm');
  const t = tip ? ` title="${tip.replace(/"/g, '&quot;')}"` : '';
  return `<span class="${cls}"${t}>${badge}${source}${icon ? ' ' + icon : ''}</span>`;
}

/* ------------------------------------------------------------------ *
 * 7) injectTopNav(el, activeKey) —— 可选顶栏导航注入
 *    el: 容器 <nav class="top-nav">；activeKey: NAV_LINKS 里的 key，高亮当前页。
 *    不想显示到自身页时可传 exclude 数组。
 * ------------------------------------------------------------------ */
export function injectTopNav(el, activeKey = '', { exclude = [] } = {}) {
  if (!el) return;
  el.innerHTML = NAV_LINKS
    .filter((l) => !exclude.includes(l.key))
    .map((l) => `<a href="${l.href}"${l.key === activeKey ? ' class="is-active"' : ''}>${l.label}</a>`)
    .join('');
}
