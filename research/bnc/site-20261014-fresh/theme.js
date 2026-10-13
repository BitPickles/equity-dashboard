/**
 * Crypto3D Theme System
 * Single source of truth for theme toggle across all pages.
 */
(function() {
  var STORAGE_KEY = 'theme';
  var root = document.documentElement;

  function applyTheme(theme) {
    if (theme === 'light') {
      root.setAttribute('data-theme', 'light');
    } else {
      root.removeAttribute('data-theme');
    }
    syncLogo(theme);
  }

  // 同步 logo：白天模式用深色版 logo-dark.svg（白底可见），黑夜模式用白色版 logo.svg
  function syncLogo(theme) {
    // 同步 logo：白天模式用深色版 logo-dark.svg（白底可见），黑夜模式用白色版 logo.svg
    // ⚠️ 必须保留原 src 的路径前缀（如 '../'），否则相对路径解析失败（2026-08-04 bug）
    var newFile = theme === 'light' ? 'logo-dark.svg' : 'logo.svg';
    document.querySelectorAll('img.logo-icon').forEach(function(img) {
      var raw = img.getAttribute('src') || '';
      if (!raw) return;
      var curFile = raw.split('/').pop();
      if (curFile !== 'logo.svg' && curFile !== 'logo-dark.svg') return; // 非站点 logo（协议头像等）不动
      if (curFile === newFile) return;
      // 保留前缀（'../' 或 'https://cdn/...'），只替换文件名
      var prefix = raw.substring(0, raw.length - curFile.length);
      img.setAttribute('src', prefix + newFile);
    });
  }

  function getTheme() {
    return root.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  }

  function toggleTheme() {
    var next = getTheme() === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem(STORAGE_KEY, next);
  }

  function iconMarkup() {
    return '<svg class="moon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z"/></svg><svg class="sun" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"/></svg>';
  }

  function normalizeButton(btn) {
    if (!btn) return null;
    btn.id = 'tt';
    btn.setAttribute('data-theme-toggle', 'true');
    btn.setAttribute('aria-label', '切换主题');
    btn.classList.add('theme-toggle-btn', 'ib', 'tt');
    if (!btn.querySelector('.moon') || !btn.querySelector('.sun')) {
      btn.innerHTML = iconMarkup();
    }
    if (!btn.dataset.themeBound) {
      btn.addEventListener('click', toggleTheme);
      btn.dataset.themeBound = 'true';
    }
    return btn;
  }

  var saved = localStorage.getItem(STORAGE_KEY);
  applyTheme(saved === 'dark' ? 'dark' : 'light');

  var existingToggle = document.querySelector('[data-theme-toggle]') || document.getElementById('tt');
  if (existingToggle) {
    normalizeButton(existingToggle);
    return;
  }

  var headerRight = document.querySelector('.header-right') || document.querySelector('.hd-r');
  if (!headerRight) {
    var headerContent = document.querySelector('.header-content');
    if (headerContent) {
      headerRight = document.createElement('div');
      headerRight.className = 'theme-toggle-slot';
      headerRight.style.marginLeft = '12px';
      headerRight.style.display = 'flex';
      headerRight.style.alignItems = 'center';
      headerContent.appendChild(headerRight);
    }
  }
  if (!headerRight) return;

  var btn = document.createElement('button');
  btn.innerHTML = iconMarkup();
  headerRight.appendChild(btn);
  normalizeButton(btn);
})();
