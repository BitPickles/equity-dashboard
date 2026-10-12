/* Crypto3D — 法律 / 说明页交互
 * 1) 由正文 h2 自动生成侧栏目录（无需手写维护）
 * 2) 滚动高亮当前章节
 * 3) 回到顶部按钮
 * 4) 页脚年份动态化
 * 语言/主题切换按钮由 lang.js / theme.js 负责注入与绑定。
 */
(function () {
  'use strict';

  var STRIP_NUM = /^\s*\d+\s*[.、．]\s*/;

  /* ── 目录 ── */
  function buildTOC() {
    var content = document.querySelector('.legal-content');
    var nav = document.querySelector('.toc-nav');
    if (!content || !nav) return;

    var heads = content.querySelectorAll('section > h2');
    if (!heads.length) return;

    // 记住每节 id（首次生成后固定，重排语言时复用）
    var ids = [];
    for (var i = 0; i < heads.length; i++) {
      var h = heads[i];
      if (!h.id) h.id = 'sec-' + (i + 1);
      ids.push(h.id);
    }

    nav.textContent = '';
    var frag = document.createDocumentFragment();
    for (var j = 0; j < heads.length; j++) {
      var t = (heads[j].textContent || '').trim();
      var label = t.replace(STRIP_NUM, '') || t;

      var a = document.createElement('a');
      a.href = '#' + ids[j];
      a.setAttribute('data-target', ids[j]);

      var num = document.createElement('span');
      num.className = 'n';
      num.textContent = (j + 1 < 10 ? '0' : '') + (j + 1);

      a.appendChild(num);
      a.appendChild(document.createTextNode(label));
      frag.appendChild(a);
    }
    nav.appendChild(frag);
    spy();
  }

  /* ── 滚动高亮 ── */
  var tocLinks = [];
  function collectLinks() {
    tocLinks = Array.prototype.slice.call(document.querySelectorAll('.toc-nav a'));
  }
  function spy() {
    if (!tocLinks.length) return;
    var fromTop = window.pageYOffset + 120;
    var current = tocLinks[0];
    for (var i = 0; i < tocLinks.length; i++) {
      var id = tocLinks[i].getAttribute('data-target');
      var el = id ? document.getElementById(id) : null;
      if (el && el.offsetTop <= fromTop) current = tocLinks[i];
    }
    for (var k = 0; k < tocLinks.length; k++) {
      tocLinks[k].classList.toggle('active', tocLinks[k] === current);
    }
  }

  /* ── 回到顶部 ── */
  function initTop() {
    var btn = document.createElement('button');
    btn.className = 'totop';
    btn.type = 'button';
    btn.setAttribute('aria-label', '回到顶部 / Back to top');
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    document.body.appendChild(btn);
    return btn;
  }

  /* ── 页脚年份 ── */
  function initYear() {
    var el = document.getElementById('ft-year');
    if (el) el.textContent = String(new Date().getFullYear());
  }

  function onScroll() {
    var y = window.pageYOffset;
    if (topBtn) topBtn.classList.toggle('show', y > 420);
    spy();
  }

  var topBtn = null;
  var ticking = false;

  function init() {
    buildTOC();
    collectLinks();
    topBtn = initTop();
    initYear();
    onScroll();

    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () { onScroll(); ticking = false; });
    }, { passive: true });

    window.addEventListener('resize', function () { spy(); }, { passive: true });

    // 语言切换后重建目录
    window.addEventListener('langchange', function () { buildTOC(); collectLinks(); onScroll(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
