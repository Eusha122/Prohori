// Collect public "awarded contract" detail pages for a list of contracts (data/raw/detail/targets.csv).
// Pages are fetched as plain HTML from inside one browser session (no rendering), parsed into
// label -> value fields plus the beneficial-ownership table, and appended to JSONL. Resumable.
//
// Usage: node collect_detail.js --worker 1 --workers 8 [--delay-ms 800] [--targets targets_b.csv --tag b]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };
const WORKER = Number(arg('--worker', 1));
const WORKERS = Number(arg('--workers', 1));
const DELAY = Number(arg('--delay-ms', 800));
const TARGETS = arg('--targets', 'targets.csv');
const TAG = arg('--tag', '') ? `${arg('--tag', '')}_` : '';
const DIR = path.join(__dirname, '..', 'data', 'raw', 'detail');
const OUT = path.join(DIR, `detail_${TAG}w${WORKER}.jsonl`);
const DONE = path.join(DIR, `done_${TAG}w${WORKER}.txt`);
const LOG = path.join(DIR, `collect_${TAG}w${WORKER}.log`);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log = m => { const l = `${new Date().toISOString()} ${m}`; console.log(l); fs.appendFileSync(LOG, l + '\n'); };

function targets() {
  const lines = fs.readFileSync(path.join(DIR, TARGETS), 'utf8').trim().split(/\r?\n/).slice(1);
  return lines.map(l => l.split(',')).filter((_, i) => i % WORKERS === WORKER - 1)
    .map(([tender_id, pkg_lot_id]) => ({ tender_id, pkg_lot_id }));
}

// Runs in the browser: fetch one detail page and parse it.
async function fetchDetail(page, t) {
  return page.evaluate(async ({ tender_id, pkg_lot_id }) => {
    const url = `/resources/common/ViewAwardedContracts.jsp?pkgLotId=${encodeURIComponent(pkg_lot_id)}&tenderid=${encodeURIComponent(tender_id)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const doc = new DOMParser().parseFromString(await res.text(), 'text/html');
    const clean = s => (s || '').replace(/\s+/g, ' ').trim();
    const fields = {};
    for (const tr of doc.querySelectorAll('tr')) {
      const cells = [...tr.children].filter(c => /^(TD|TH)$/.test(c.tagName));
      if (cells.length >= 2) {
        const k = clean(cells[0].textContent).replace(/:$/, '');
        if (k && k.length < 120 && !(k in fields)) fields[k] = clean(cells[1].textContent);
      }
    }
    // Beneficial ownership rows: tables with a "Beneficial Ownership (%)" header.
    const owners = [];
    for (const table of doc.querySelectorAll('table')) {
      const head = clean(table.querySelector('tr')?.textContent);
      if (/Beneficial Ownership \(%\)/i.test(head)) {
        for (const tr of [...table.querySelectorAll('tr')].slice(1)) {
          const c = [...tr.querySelectorAll('td')].map(td => clean(td.textContent));
          if (c.length >= 4) owners.push({ name: c[1], designation: c[2], percent: c[3], country: c[4] || '' });
        }
      }
    }
    return { fields, owners, n_fields: Object.keys(fields).length };
  }, t);
}

async function openSession() {
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  const page = await browser.newPage();
  await page.goto('https://www.eprocure.gov.bd/resources/common/SearchNOA.jsp', { waitUntil: 'domcontentloaded', timeout: 120000 });
  return { browser, page };
}

(async () => {
  fs.mkdirSync(DIR, { recursive: true });
  const done = new Set(fs.existsSync(DONE) ? fs.readFileSync(DONE, 'utf8').split('\n').filter(Boolean) : []);
  const todo = targets().filter(t => !done.has(t.pkg_lot_id));
  log(`worker ${WORKER}/${WORKERS}: ${todo.length} to fetch (${done.size} already done)`);
  let session = await openSession();
  let failures = 0;
  for (let i = 0; i < todo.length; i++) {
    const t = todo[i];
    try {
      const r = await fetchDetail(session.page, t);
      if (r.n_fields < 5) throw new Error('page had too few fields');
      fs.appendFileSync(OUT, JSON.stringify({ ...t, fetchedAt: new Date().toISOString(), ...r }) + '\n');
      fs.appendFileSync(DONE, t.pkg_lot_id + '\n');
      failures = 0;
      if ((i + 1) % 100 === 0) log(`${i + 1}/${todo.length} ok`);
      await sleep(DELAY + Math.random() * 300);
    } catch (e) {
      failures++;
      const wait = Math.min(300000, 5000 * 2 ** Math.min(failures, 6));
      log(`${t.pkg_lot_id} failed (${e.message}); retry #${failures} in ${wait / 1000}s`);
      if (failures >= 8) { log(`${t.pkg_lot_id} skipped after repeated failures`); failures = 0; continue; }
      await sleep(wait);
      i--;
      if (failures % 3 === 0) { try { await session.browser.close(); } catch {} session = await openSession(); }
    }
  }
  log('finished');
  await session.browser.close();
})();
