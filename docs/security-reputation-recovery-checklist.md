# Crypto3D 安全信誉恢复清单

## 已完成修复
- 为正式站补充安全响应头：HSTS、CSP、X-Frame-Options、X-Content-Type-Options、Permissions-Policy、Referrer-Policy
- 收口调试/测试/旧目录页面的公开访问（通过 `_redirects` 重定向）
- GitHub Pages 部署从“整仓库直传”改为“过滤后上传 `_site`”，避免 debug/test/review/poster/web 等目录继续上线

## 本次被排除出正式部署的内容
- `review/`
- `poster/`
- `web/`
- `tmp/`
- `*.bak`
- `debug-report.md`
- `equity/debug.html`
- `equity/final-debug.html`
- `equity/simple-debug.html`
- `equity/simple-test.html`
- `equity/test-proto.html`
- `equity/test-tevratio.html`
- `equity/test_fetch.html`
- `daily-poster/output/comments.html`
- `daily-poster/output/comments.json`

## 上线后验证
1. 打开首页 `https://crypto3d.pro/`，确认可正常访问
2. 验证以下路径已不再暴露原始内容，而是跳转或失效：
   - `/equity/debug`
   - `/equity/test_fetch`
   - `/review/news-radar.html`
   - `/poster/output/2026-03-20.html`
   - `/web/protocol.html`
   - `/daily-poster/output/comments.html`
   - `/daily-poster/output/comments.json`
3. 检查响应头是否生效：
   - `Strict-Transport-Security`
   - `Content-Security-Policy`
   - `X-Frame-Options`
   - `Permissions-Policy`
4. 用无痕窗口、不同网络或手机再次访问，确认“危险网站”提示是否仍出现

## 复审建议
### Google Search Console / Safe Browsing
- 进入站点属性后，检查“安全问题”或相关告警
- 若出现历史命中，提交复审
- 复审说明建议写清：
  - 已清理公开调试/测试页面
  - 已收口历史 review / poster / web 页面
  - 已改造部署流程，避免非正式文件再次上线
  - 已补齐安全响应头

### 其他安全信誉平台
可顺手复查：
- Google Transparency Report
- VirusTotal URL / Domain
- URLVoid
- urlscan

## 后续建议
- 正式站与实验/验收页面彻底分仓或分域名，不再同域部署
- 所有调试页只保留在本地或受限环境
- 以后新增 GitHub Pages 内容时，默认先加入白名单式发布策略，而不是整仓库上传
