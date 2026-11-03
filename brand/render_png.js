// Render the Prohori logo SVG to PNG sizes, plus a horizontal lockup (icon + name).
// Usage (from prohori/brand):  NODE_PATH=../collector/node_modules node render_png.js
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const DIR = __dirname;
const OUT = path.join(DIR, 'png');
const uri = file => 'data:image/svg+xml;base64,' +
  Buffer.from(fs.readFileSync(path.join(DIR, file), 'utf8')).toString('base64');
const iconUri = uri('prohori-icon.svg');        // white pages
const plainUri = uri('prohori-icon-plain.svg'); // green / dark backgrounds
const tileUri = uri('prohori-icon-tile.svg');   // phone home-screen icons (no transparency)

const lockup = (bg, logo, nameColor, tagColor) => `<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@700&display=swap" rel="stylesheet">
<style>body{margin:0;background:${bg}}#l{display:inline-flex;align-items:center;gap:22px;padding:28px 40px 28px 28px}
img{width:150px;height:150px}.n{font:700 76px/1 "Hind Siliguri",Arial;color:${nameColor}}
.t{display:block;font:400 26px/1.3 Arial;color:${tagColor};margin-top:8px}</style></head>
<body><div id="l"><img src="${logo}"><div><span class="n">প্রহরী</span>
<span class="t">Public Procurement Watch · সরকারি ক্রয় পর্যবেক্ষণ</span></div></div></body></html>`;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch(
    process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  // A fresh page per image: reusing one page across viewport resizes can stall screenshots.
  for (const size of [16, 32, 48, 180, 192, 512, 1024]) {
    const page = await browser.newPage({ viewport: { width: Math.max(size, 64), height: Math.max(size, 64) } });
    const src = size === 180 || size === 192 ? tileUri : iconUri;
    await page.setContent(`<body style="margin:0;background:transparent"><img src="${src}" style="width:${size}px;height:${size}px;display:block"></body>`);
    await page.locator('img').screenshot({ path: path.join(OUT, `prohori-icon-${size}.png`), omitBackground: true });
    await page.close();
  }

  for (const [name, html] of [
    ['prohori-logo-light.png', lockup('transparent', iconUri, '#2a5f16', '#555')],
    ['prohori-logo-dark.png', lockup('transparent', plainUri, '#ffffff', '#e8f3dc')],
  ]) {
    const page = await browser.newPage({ viewport: { width: 1400, height: 400 } });
    await page.setContent(html, { waitUntil: 'networkidle' });
    await page.locator('#l').screenshot({ path: path.join(OUT, name), omitBackground: true });
    await page.close();
  }
  await browser.close();
  console.log('wrote', fs.readdirSync(OUT).join(', '));
})();
