// Collect every public Notification of Award row from e-GP, page by page, the same way
// the SearchNOA page loads them (10 rows per request). Resumable: each page is appended
// to a JSONL file as soon as it arrives, and finished page numbers are recorded, so a
// restart after a power cut continues where it stopped.
//
// Usage: node collect_noa.js [--from N] [--to N] [--delay-ms 1500] [--worker NAME]
// Several workers can run at once on different page ranges; each --worker NAME gets
// its own output, bookmark and log files. Without --worker the original filenames are used.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  return i > 0 ? Number(process.argv[i + 1]) : fallback;
}
function strArg(name, fallback) {
  const i = process.argv.indexOf(name);
  return i > 0 ? process.argv[i + 1] : fallback;
}

const NOA_URL = 'https://www.eprocure.gov.bd/resources/common/SearchNOA.jsp';
const OUT_DIR = path.join(__dirname, '..', 'data', 'raw', 'noa');
const WORKER = strArg('--worker', '');
const SUFFIX = WORKER ? `_${WORKER}` : '';
const DONE_FILE = path.join(OUT_DIR, `pages_done${SUFFIX}.txt`);
const LOG_FILE = path.join(OUT_DIR, `collect${SUFFIX}.log`);
const PAGES_PER_FILE = 1000;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log = msg => {
  const line = `${new Date().toISOString()} ${msg}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n');
};

function loadDone() {
  if (!fs.existsSync(DONE_FILE)) return new Set();
  return new Set(fs.readFileSync(DONE_FILE, 'utf8').split('\n').filter(Boolean).map(Number));
}

// Runs inside the browser page: request one list page and parse its rows.
async function fetchPage(page, pageNo) {
  return page.evaluate(async pageNo => {
    const body = new URLSearchParams({ keyword: '', pageNo: String(pageNo), size: '10' });
    const res = await fetch('/SearchNoaServlet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
      body,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    const doc = new DOMParser().parseFromString(`<table>${html}</table>`, 'text/html');
    const totalPages = doc.querySelector('#totalPages')?.value || null;
    const rows = [...doc.querySelectorAll('tr')].map(tr => {
      const td = [...tr.querySelectorAll('td')];
      if (td.length < 8) return null;
      const link = td[2].querySelector('a');
      const href = link?.getAttribute('href') || '';
      const params = new URLSearchParams(href.split('?')[1] || '');
      const more = td[2].querySelector('.more');
      let title = '';
      if (more) {
        const clone = more.cloneNode(true);
        clone.querySelectorAll('.moreellipses, .morelink').forEach(e => e.remove());
        title = clone.textContent.replace(/\s+/g, ' ').trim();
      }
      const cell2 = td[2].cloneNode(true);
      cell2.querySelectorAll('a, .more').forEach(e => e.remove());
      const peParts = td[3].innerHTML.split(/<br\s*\/?>/i).map(s =>
        s.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim());
      return {
        sNo: td[0].textContent.trim(),
        ministry: td[1].textContent.replace(/\s+/g, ' ').trim(),
        tenderId: params.get('tenderid'),
        pkgLotId: params.get('pkgLotId'),
        idAndRef: link?.textContent.replace(/\s+/g, ' ').trim() || '',
        title,
        advertised: cell2.textContent.replace(/\s+/g, ' ').trim(),
        procuringEntity: peParts[0] || '',
        method: peParts[1] || '',
        district: td[4].textContent.replace(/\s+/g, ' ').trim(),
        contractSigned: td[5].textContent.trim(),
        winner: td[6].textContent.replace(/\s+/g, ' ').trim(),
        value: td[7].textContent.replace(/\s+/g, ' ').trim(),
      };
    }).filter(Boolean);
    return { totalPages, rows, rawLength: html.length };
  }, pageNo);
}

async function openSession() {
  const browser = await chromium.launch(
    process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  const page = await browser.newPage();
  await page.goto(NOA_URL, { waitUntil: 'networkidle', timeout: 120000 });
  return { browser, page };
}

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const done = loadDone();
  const delayMs = arg('--delay-ms', 1500);
  let session = await openSession();

  const first = await fetchPage(session.page, 1);
  const totalPages = Number(first.totalPages) || arg('--to', 0);
  const from = arg('--from', 1);
  const to = arg('--to', totalPages);
  log(`total pages on site: ${first.totalPages}; collecting ${from}..${to}; already done: ${done.size}`);

  let failures = 0;
  for (let p = from; p <= to; p++) {
    if (done.has(p)) continue;
    try {
      const { rows, totalPages: liveTotal } = await fetchPage(session.page, p);
      if (rows.length === 0) {
        // Past the last page (the oldest records): nothing more to collect.
        if (liveTotal && p > Number(liveTotal)) { log(`page ${p} is past the last page (${liveTotal}); stopping`); break; }
        throw new Error('empty page');
      }
      const file = path.join(OUT_DIR, `noa${SUFFIX}_${String(Math.floor((p - 1) / PAGES_PER_FILE)).padStart(3, '0')}.jsonl`);
      const fetchedAt = new Date().toISOString();
      fs.appendFileSync(file, rows.map(r => JSON.stringify({ page: p, fetchedAt, ...r })).join('\n') + '\n');
      fs.appendFileSync(DONE_FILE, p + '\n');
      done.add(p);
      failures = 0;
      if (p % 100 === 0) log(`page ${p}/${to} ok (${done.size} done)`);
      await sleep(delayMs + Math.random() * 500);
    } catch (err) {
      failures++;
      const wait = Math.min(300000, 5000 * 2 ** Math.min(failures, 6));
      log(`page ${p} failed (${err.message}); retry #${failures} in ${wait / 1000}s`);
      await sleep(wait);
      p--; // retry the same page
      if (failures % 3 === 0) {
        try { await session.browser.close(); } catch {}
        session = await openSession();
      }
    }
  }
  log('finished');
  await session.browser.close();
})();
