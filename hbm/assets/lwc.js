// assets/lwc.js —— TradingView Lightweight Charts 估值时间序列组件（P/E / P/B 日频）
// 首页 Hero 与 周期证据 页共用。原生可拖动/缩放时间轴 + 十字准星 + 公司开关 + 指标切换。
// 设计对齐 shared.css：浅色、公司固定色、IBM Plex Mono 轴标签。

let _lwcPromise = null;

/** 从 CDN 懒加载 Lightweight Charts（standalone），resolve 出 window.LightweightCharts。 */
export function lwcReady() {
  if (_lwcPromise) return _lwcPromise;
  _lwcPromise = new Promise((resolve, reject) => {
    if (window.LightweightCharts) return resolve(window.LightweightCharts);
    const cdns = [
      'https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js',
      'https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js',
    ];
    let i = 0;
    const tryLoad = () => {
      const s = document.createElement('script');
      s.src = cdns[i];
      s.async = true;
      s.onload = () => resolve(window.LightweightCharts);
      s.onerror = () => { i++; (i < cdns.length) ? tryLoad() : reject(new Error('Lightweight Charts 加载失败')); };
      document.head.appendChild(s);
    };
    tryLoad();
  });
  return _lwcPromise;
}

const PALETTE = {
  text: '#5C6470', axisLine: '#E4E7EB', grid: '#EDEFF2', mono: "'IBM Plex Mono', ui-monospace, monospace",
};

/** 极简 HTML 转义（浮框/图例注入公司名与颜色值用；含引号——颜色值会进双引号
    style 属性，不转义引号则数据文件里的异常值可提前闭合属性注入） */
function escText(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/**
 * 在 container 里建一张估值曲线图。
 * @param {HTMLElement} container 须有确定尺寸（或用 autoSize + 有高度的父容器）
 * @param {Object} opts
 *   - companies: [{ ticker, name, color, dates:[YYYY-MM-DD], pe:[num|null], pb:[num|null] }]
 *   - metric: 'pe' | 'pb'（默认 'pe'）
 *   - logForPE: 是否 P/E 用对数轴（默认 true；P/B 恒线性）
 * @returns { chart, setMetric(m), setVisible(ticker,bool), fit(), remove(), isLog() }
 */
export async function createValuationChart(container, opts) {
  const LWC = await lwcReady();
  const logForPE = opts.logForPE !== false;

  const chart = LWC.createChart(container, {
    autoSize: true,
    layout: { background: { type: 'solid', color: 'transparent' }, textColor: PALETTE.text, fontFamily: PALETTE.mono, fontSize: 11 },
    grid: { vertLines: { color: PALETTE.grid }, horzLines: { color: PALETTE.grid } },
    rightPriceScale: { borderColor: PALETTE.axisLine, entireTextOnly: true },
    timeScale: { borderColor: PALETTE.axisLine, timeVisible: false, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true },
    crosshair: {
      mode: LWC.CrosshairMode.Normal,
      vertLine: { color: '#9AA3B2', width: 1, style: 2, labelBackgroundColor: '#3A404B' },
      horzLine: { color: '#9AA3B2', width: 1, style: 2, labelBackgroundColor: '#3A404B' },
    },
    localization: {
      locale: 'zh-CN',
      priceFormatter: (v) => (v == null ? '—' : (v >= 100 ? v.toFixed(0) : v.toFixed(2))),
    },
    handleScroll: true, handleScale: true,   // 原生拖动 + 缩放时间轴
  });

  // 每家一个条目，持有该家当前 metric 下的一组「段」series。
  // ⚠️ LWC v4 line series 的 whitespace（{time} 无 value）不产生视觉断口——它只做
  //    多序列时间轴对齐，折线会直接跨过缺口画直线（已实测）。NM/缺数据要真正
  //    「断开不插值」，必须把每条线按连续非空段拆成多条 series（同色；价签与
  //    名字只挂最后一段，避免重复标签）。
  const seriesMap = {};
  (opts.companies || []).forEach((c) => {
    seriesMap[c.ticker] = { c, segs: [], visible: true };
  });

  let metric = opts.metric || 'pe';

  function toSegments(c) {
    const vals = c[metric] || [];
    const dates = c.dates || [];
    const segs = [];
    let cur = null;
    for (let i = 0; i < dates.length; i++) {
      const v = vals[i];
      if (v == null) { cur = null; continue; }   // 缺口：结束当前段
      if (!cur) { cur = []; segs.push(cur); }
      cur.push({ time: dates[i], value: v });
    }
    return segs;
  }

  function apply() {
    Object.values(seriesMap).forEach((e) => {
      e.segs.forEach((s) => { try { chart.removeSeries(s); } catch (err) {} });
      e.segs = [];
      const segData = toSegments(e.c);
      segData.forEach((data, i) => {
        const isLast = i === segData.length - 1;
        const s = chart.addLineSeries({
          color: e.c.color, lineWidth: 2, priceLineVisible: false,
          lastValueVisible: isLast,          // 价签只在最后一段
          title: isLast ? e.c.name : '',     // 名字只在最后一段
          crosshairMarkerVisible: true,
          // 孤立单点段（前后都是缺口）线画不出来，用点标记兜底可见
          pointMarkersVisible: data.length === 1,
          visible: e.visible,
        });
        s.setData(data);
        e.segs.push(s);
      });
    });
    const isLog = (metric === 'pe') && logForPE;
    chart.priceScale('right').applyOptions({ mode: isLog ? 1 : 0 }); // 1=Logarithmic 0=Normal
    chart.timeScale().fitContent();
  }
  apply();

  return {
    chart,
    setMetric(m) { if (m !== metric) { metric = m; apply(); } },
    getMetric() { return metric; },
    setVisible(ticker, vis) {
      const e = seriesMap[ticker];
      if (e) { e.visible = vis; e.segs.forEach((s) => s.applyOptions({ visible: vis })); }
    },
    fit() { chart.timeScale().fitContent(); },
    remove() { try { chart.remove(); } catch (e) {} },
    isLog() { return (metric === 'pe') && logForPE; },
  };
}

/**
 * createSeriesChart —— 通用多序列折线图（纯增量新增，单图工作台 price/pe/pb 用）。
 * 与 createValuationChart 同一套「分段断开」策略：null=缺口，连续非空段拆成
 * 多条 line series（同色），价签与名字只挂最后一段；不修改 createValuationChart。
 *
 * @param {HTMLElement} container 须有确定尺寸（autoSize + 有高度的父容器）
 * @param {Object} opts
 *   - series: [{ name, color, dates:[YYYY-MM-DD], values:[num|null], visible? }]
 *   - log: 价格轴对数（默认 false）
 *   - dark: 深色主题（导出帧用，默认 false 浅色）
 *   - fontSize: 轴字号（默认 11）
 *   - priceFormatter: 自定义价签格式化（可选）
 *   - hoverTip: 悬停浮框（默认 true；日期 + 各可见序列「色点+名称+值」，跟随鼠标防溢出翻转）
 * @returns { chart, setVisible(name, bool), fit(), remove() }
 *
 * 价签与序列名不再挂在图上（lastValueVisible:false / title:''——多家同显时右侧
 * 价签+名字遮图，读数由悬停浮框提供）；series>1 时容器左上角有静态小图例。
 */
export async function createSeriesChart(container, opts = {}) {
  const LWC = await lwcReady();
  const dark = !!opts.dark;
  const pal = dark
    ? { text: '#9AA3B2', axisLine: '#232936', grid: '#232936', bg: { type: 'solid', color: '#0D1117' } }
    : { text: PALETTE.text, axisLine: PALETTE.axisLine, grid: PALETTE.grid, bg: { type: 'solid', color: 'transparent' } };
  const fmt = opts.priceFormatter || ((v) => {
    if (v == null || !isFinite(v)) return '—';
    const a = Math.abs(v);
    if (a >= 10000) return Math.round(v).toLocaleString('en-US');
    if (a >= 100) return v.toFixed(0);
    return v.toFixed(2);
  });

  const chart = LWC.createChart(container, {
    autoSize: true,
    layout: { background: pal.bg, textColor: pal.text, fontFamily: PALETTE.mono, fontSize: opts.fontSize || 11 },
    grid: { vertLines: { color: pal.grid }, horzLines: { color: pal.grid } },
    rightPriceScale: { borderColor: pal.axisLine, entireTextOnly: true, mode: opts.log ? 1 : 0 },
    timeScale: { borderColor: pal.axisLine, timeVisible: false, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true },
    crosshair: {
      mode: LWC.CrosshairMode.Normal,
      vertLine: { color: '#9AA3B2', width: 1, style: 2, labelBackgroundColor: '#3A404B' },
      horzLine: { color: '#9AA3B2', width: 1, style: 2, labelBackgroundColor: '#3A404B' },
    },
    localization: { locale: 'zh-CN', priceFormatter: fmt },
    handleScroll: true, handleScale: true,   // 原生拖动 + 缩放时间轴
  });

  // 分段断开（与 createValuationChart 的 toSegments 同一策略，通用化到任意 values）：
  // null=缺口 → 结束当前段；连续非空段各自成一条 series，折线不跨缺口插值。
  function toSegments(dates, values) {
    const segs = [];
    let cur = null;
    const n = Math.min(dates.length, values.length);
    for (let i = 0; i < n; i++) {
      const v = values[i];
      if (v == null) { cur = null; continue; }
      if (!cur) { cur = []; segs.push(cur); }
      cur.push({ time: dates[i], value: v });
    }
    return segs;
  }

  const entries = [];
  (opts.series || []).forEach((def) => {
    const visible = def.visible !== false;
    const segData = toSegments(def.dates || [], def.values || []);
    const segs = segData.map((data) => {
      const s = chart.addLineSeries({
        color: def.color, lineWidth: dark ? 2.5 : 2, priceLineVisible: false,
        lastValueVisible: false,   // 价签一律隐藏（多家同显遮图），读数走悬停浮框
        title: '',                 // 序列名同理不上图，静态图例/浮框里给
        crosshairMarkerVisible: true,
        // 孤立单点段（前后都是缺口）线画不出来，用点标记兜底可见
        pointMarkersVisible: data.length === 1,
        visible,
      });
      s.setData(data);
      return s;
    });
    entries.push({ name: def.name, color: def.color, segs, visible });
  });
  chart.timeScale().fitContent();

  // ---- 浮框 / 图例是容器内绝对定位的覆盖层：容器无定位上下文时补 relative ----
  const hoverTip = opts.hoverTip !== false;
  if ((hoverTip || entries.length > 1) && getComputedStyle(container).position === 'static') {
    container.style.position = 'relative';
  }

  // ---- 静态小图例（左上角一行小字，色点+名称；只在 series>1 时显示，不带数值） ----
  const legendItems = {};
  let legendEl = null;
  if (entries.length > 1) {
    legendEl = document.createElement('div');
    legendEl.style.cssText = 'position:absolute;left:8px;top:6px;z-index:3;display:flex;gap:10px;'
      + 'flex-wrap:wrap;pointer-events:none;font:500 11px ' + PALETTE.mono + ';color:' + pal.text + ';';
    entries.forEach((e) => {
      const it = document.createElement('span');
      it.style.cssText = 'display:' + (e.visible ? 'inline-flex' : 'none') + ';align-items:center;gap:4px;';
      it.innerHTML = '<span style="width:8px;height:8px;border-radius:50%;flex:none;background:'
        + escText(e.color) + '"></span>' + escText(e.name);
      legendEl.appendChild(it);
      legendItems[e.name] = it;
    });
    container.appendChild(legendEl);
  }

  // ---- 悬停浮框：subscribeCrosshairMove → 日期 + 各可见序列「色点+名称+值」 ----
  let tipEl = null;
  let onCrosshair = null;
  if (hoverTip) {
    tipEl = document.createElement('div');
    tipEl.style.cssText = 'position:absolute;left:0;top:0;z-index:4;display:none;pointer-events:none;'
      + 'padding:6px 9px;border-radius:6px;white-space:nowrap;line-height:1.7;'
      + (dark
        ? 'background:rgba(13,17,23,.92);border:1px solid #232936;color:#D5DAE2;'
        : 'background:rgba(255,255,255,.96);border:1px solid #E4E7EB;color:#3A404B;box-shadow:0 2px 10px rgba(20,24,31,.10);')
      + 'font:500 11px ' + PALETTE.mono + ';';
    container.appendChild(tipEl);

    // param.time 可能是 'YYYY-MM-DD' 字符串 / BusinessDay 对象 / UTC 秒，统一成 ISO 日期
    const fmtTime = (t) => {
      if (typeof t === 'string') return t;
      if (t && typeof t === 'object' && t.year) {
        const p2 = (x) => (x < 10 ? '0' + x : '' + x);
        return t.year + '-' + p2(t.month) + '-' + p2(t.day);
      }
      if (typeof t === 'number' && isFinite(t)) return new Date(t * 1000).toISOString().slice(0, 10);
      return '';
    };

    onCrosshair = (param) => {
      // 指针不在图内（离开 / 越界）→ 隐藏
      if (!param || !param.point || param.time == null
          || param.point.x < 0 || param.point.y < 0
          || param.point.x > container.clientWidth || param.point.y > container.clientHeight) {
        tipEl.style.display = 'none';
        return;
      }
      const rows = [];
      entries.forEach((e) => {
        if (!e.visible) return;                              // 只列当前可见序列
        let val = null;
        for (let i = 0; i < e.segs.length; i++) {            // 命中该时点的分段取值
          const d = param.seriesData && param.seriesData.get(e.segs[i]);
          if (d && d.value != null) { val = d.value; break; }
        }
        rows.push('<div style="display:flex;align-items:center;gap:5px">'
          + '<span style="width:7px;height:7px;border-radius:50%;flex:none;background:' + escText(e.color) + '"></span>'
          + escText(e.name) + '&nbsp;<b>' + (val == null ? '—' : escText(fmt(val))) + '</b></div>');
      });
      if (!rows.length) { tipEl.style.display = 'none'; return; }
      tipEl.innerHTML = '<div style="color:' + (dark ? '#8A96A8' : '#8A94A6') + '">'
        + escText(fmtTime(param.time)) + '</div>' + rows.join('');
      tipEl.style.display = 'block';
      // 跟随鼠标；贴近右/下边界时向左/上翻转防溢出
      const pad = 14;
      let x = param.point.x + pad;
      let y = param.point.y + pad;
      if (x + tipEl.offsetWidth > container.clientWidth - 4) x = param.point.x - pad - tipEl.offsetWidth;
      if (y + tipEl.offsetHeight > container.clientHeight - 4) y = param.point.y - pad - tipEl.offsetHeight;
      tipEl.style.left = Math.max(0, x) + 'px';
      tipEl.style.top = Math.max(0, y) + 'px';
    };
    chart.subscribeCrosshairMove(onCrosshair);
  }

  // ---- W10 区间测量:纯增量坐标代理（不改 createValuationChart）----
  // LWC v4 中,一条线只有"参与当前价格轴换算"的段（通常是延伸到可视右缘的
  // 最后一段)才对 coordinateToPrice 返回有效值,更早的段返回 null。故按
  // 「可见序列的最后一段 → 其余段」顺序逐一尝试,取到首个有效换算即止。
  // 所有段共享同一右价格轴（含 log),换算结果与选哪条无关。
  function priceCandidates() {
    const out = [];
    entries.forEach((e) => { if (e.visible && e.segs.length) out.push(e.segs[e.segs.length - 1]); });
    entries.forEach((e) => { if (!e.visible && e.segs.length) out.push(e.segs[e.segs.length - 1]); });
    // 兜底:再补上所有段（个别数据形态下最后一段也可能不参与换算）
    entries.forEach((e) => e.segs.forEach((s) => { if (out.indexOf(s) < 0) out.push(s); }));
    return out;
  }

  return {
    chart,
    // W10:y 像素 → 价格（log 轴由 LWC 内部处理;无有效换算时 null）
    priceAt(y) {
      const cands = priceCandidates();
      for (let i = 0; i < cands.length; i++) {
        try {
          const v = cands[i].coordinateToPrice(y);
          if (v != null && isFinite(v)) return v;
        } catch (e) {}
      }
      return null;
    },
    // W10:x 像素 → 时间（LWC 原生:'YYYY-MM-DD' 字符串 / BusinessDay / UTC 秒 / null）
    timeAt(x) {
      try { return chart.timeScale().coordinateToTime(x); }
      catch (e) { return null; }
    },
    setVisible(name, vis) {
      const e = entries.find((x) => x.name === name);
      if (e) {
        e.visible = vis;
        e.segs.forEach((s) => s.applyOptions({ visible: vis }));
        if (legendItems[name]) legendItems[name].style.display = vis ? 'inline-flex' : 'none';
      }
    },
    fit() { chart.timeScale().fitContent(); },
    remove() {
      // 先退订并清理覆盖层 DOM，再销毁 chart（防订阅/节点泄漏）
      if (onCrosshair) { try { chart.unsubscribeCrosshairMove(onCrosshair); } catch (e) {} onCrosshair = null; }
      if (tipEl) { tipEl.remove(); tipEl = null; }
      if (legendEl) { legendEl.remove(); legendEl = null; }
      try { chart.remove(); } catch (e) {}
    },
  };
}
