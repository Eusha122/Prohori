// Collect the full public debarment list ("All" tab = ongoing + past) from e-GP by
// clicking through the report like a visitor. Writes data/raw/debarment/debarment.jsonl.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const URL = 'https://www.eprocure.gov.bd/resources/common/DebarmentRpt.jsp';
const OUT_DIR = path.join(__dirname, '..', 'data', 'raw', 'debarment');
const OUT_FILE = path.join(OUT_DIR, 'debarment.jsonl');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function readRows(page) {
  return page.evaluate(() => {
    const rows = [...document.querySelectorAll('#resultTable tr')].slice(1);
    return rows.map(tr => [...tr.querySelectorAll('td')].map(td => td.innerText.replace(/\s+/g, ' ').trim()))
      .filter(c => c.length >= 8)
      .map(c => ({
        sNo: c[0], company: c[1], country: c[2], address: c[3], area: c[4],
        period: c[5], debarredBy: c[6], reason: c[7],
      }));
  });
}

async function pager(page) {
  return page.evaluate(() => ({
    pageNo: Number(document.querySelector('#pageNo')?.value),
    total: Number(document.querySelector('#totalPages')?.value),
  }));
}

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch(
    process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  const page = await browser.newPage();
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 120000 });
  await page.waitForTimeout(2000);
  await page.click('#dArchive');           // "All" tab
  await page.waitForTimeout(8000);

  const out = fs.createWriteStream(OUT_FILE, { flags: 'w' });
  let seen = 0;
  for (let guard = 0; guard < 500; guard++) {
    const { pageNo, total } = await pager(page);
    const rows = await readRows(page);
    rows.forEach(r => out.write(JSON.stringify({ page: pageNo, ...r }) + '\n'));
    seen += rows.length;
    if (pageNo % 10 === 0 || pageNo === total) console.log(`page ${pageNo}/${total}, rows so far ${seen}`);
    if (!total || pageNo >= total) break;
    await page.click('#btnNext');
    await sleep(2500 + Math.random() * 1000);
    await page.waitForFunction(prev => Number(document.querySelector('#pageNo')?.value) > prev,
      pageNo, { timeout: 60000 });
  }
  out.end();
  console.log(`done: ${seen} rows -> ${OUT_FILE}`);
  await browser.close();
})();
