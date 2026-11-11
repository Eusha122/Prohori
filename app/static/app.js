// Prohori front end. Routes: #/  #/search/<q>  #/company/<key>  #/office/<name>  #/patterns  #/debarred  #/largest
//   #/watchlist[/<overall|size>/<division>]  #/model  #/about  #/pricing  #/probashi  #/districts  #/district/<name>
//   #/check[/<q>]  #/report/<key>  #/numbers (team only)
// Every visible text has an English and a Bangla version: T('English', 'বাংলা'). The language button in the top-right
// corner switches all of it, including numbers, Taka amounts and dates, and is remembered in the browser.
const view = document.getElementById('view');

const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage blocked */ } },
};
let LANG = store.get('lang') === 'bn' ? 'bn' : 'en';
const T = (en, bn) => (LANG === 'bn' ? bn : en);
const isPhone = () => window.matchMedia('(max-width: 760px)').matches;
const LOC = () => (LANG === 'bn' ? 'bn-BD' : 'en-IN');
const DIGITS = '০১২৩৪৫৬৭৮৯';
const dig = s => (LANG === 'bn' ? String(s).replace(/[0-9]/g, d => DIGITS[d]) : String(s));
const bnNote = s => (LANG === 'en' ? `<span class="bn">${s}</span>` : '');   // small Bangla line under English text

const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const num = n => (n ?? 0).toLocaleString(LOC());
const pct = x => dig(`${Math.round((x ?? 0) * 100)}%`);
const pctTxt = x => dig(`${(x * 100).toFixed(0)}%`);
const contracts = n => T(`${num(n)} contract${n === 1 ? '' : 's'}`, `${num(n)}টি চুক্তি`);
const date = d => d ? new Date(d).toLocaleDateString(LANG === 'bn' ? 'bn-BD' : 'en-GB',
  { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

// Taka in the units Bangladeshi readers use: crore / lakh.
function taka(v) {
  if (v == null) return '—';
  const f = (x, d) => x.toLocaleString(LOC(), { maximumFractionDigits: d });
  if (v >= 1e7) return T(`Tk ${f(v / 1e7, v >= 1e9 ? 0 : 2)} crore`, `${f(v / 1e7, v >= 1e9 ? 0 : 2)} কোটি টাকা`);
  if (v >= 1e5) return T(`Tk ${f(v / 1e5, 1)} lakh`, `${f(v / 1e5, 1)} লাখ টাকা`);
  return T(`Tk ${num(Math.round(v))}`, `${num(Math.round(v))} টাকা`);
}

// Place names in Bangla.
const PLACE_BN = {
  Dhaka: 'ঢাকা', Gazipur: 'গাজীপুর', Narayanganj: 'নারায়ণগঞ্জ', Tangail: 'টাঙ্গাইল', Kishoreganj: 'কিশোরগঞ্জ',
  Manikganj: 'মানিকগঞ্জ', Munshiganj: 'মুন্সীগঞ্জ', Narsingdi: 'নরসিংদী', Faridpur: 'ফরিদপুর', Gopalganj: 'গোপালগঞ্জ',
  Madaripur: 'মাদারীপুর', Rajbari: 'রাজবাড়ী', Shariatpur: 'শরীয়তপুর', Mymensingh: 'ময়মনসিংহ', Jamalpur: 'জামালপুর',
  Netrokona: 'নেত্রকোনা', Sherpur: 'শেরপুর', Chattogram: 'চট্টগ্রাম', "Cox's Bazar": 'কক্সবাজার', Cumilla: 'কুমিল্লা',
  Brahmanbaria: 'ব্রাহ্মণবাড়িয়া', Chandpur: 'চাঁদপুর', Noakhali: 'নোয়াখালী', Feni: 'ফেনী', Lakshmipur: 'লক্ষ্মীপুর',
  Rangamati: 'রাঙ্গামাটি', Khagrachari: 'খাগড়াছড়ি', Bandarban: 'বান্দরবান', Rajshahi: 'রাজশাহী', Bogura: 'বগুড়া',
  Pabna: 'পাবনা', Sirajganj: 'সিরাজগঞ্জ', Naogaon: 'নওগাঁ', Natore: 'নাটোর', Joypurhat: 'জয়পুরহাট',
  'Chapai Nawabganj': 'চাঁপাইনবাবগঞ্জ', Khulna: 'খুলনা', Jashore: 'যশোর', Kushtia: 'কুষ্টিয়া', Bagerhat: 'বাগেরহাট',
  Satkhira: 'সাতক্ষীরা', Jhenaidah: 'ঝিনাইদহ', Magura: 'মাগুরা', Narail: 'নড়াইল', Chuadanga: 'চুয়াডাঙ্গা',
  Meherpur: 'মেহেরপুর', Barishal: 'বরিশাল', Patuakhali: 'পটুয়াখালী', Bhola: 'ভোলা', Pirojpur: 'পিরোজপুর',
  Barguna: 'বরগুনা', Jhalokathi: 'ঝালকাঠি', Sylhet: 'সিলেট', Moulvibazar: 'মৌলভীবাজার', Habiganj: 'হবিগঞ্জ',
  Sunamganj: 'সুনামগঞ্জ', Rangpur: 'রংপুর', Dinajpur: 'দিনাজপুর', Kurigram: 'কুড়িগ্রাম', Nilphamari: 'নীলফামারী',
  Gaibandha: 'গাইবান্ধা', Thakurgaon: 'ঠাকুরগাঁও', Lalmonirhat: 'লালমনিরহাট', Panchagarh: 'পঞ্চগড়',
  Jessore: 'যশোর', Bogra: 'বগুড়া', Barisal: 'বরিশাল', Comilla: 'কুমিল্লা', Chittagong: 'চট্টগ্রাম', Other: 'অন্যান্য',
};
const place = n => (LANG === 'bn' && n ? PLACE_BN[n] || n : n || '');

// Small hand-drawn signs (inline SVG) used instead of text symbols/emoji, so they look the same everywhere.
const ICON = {
  ext: '<svg class="ic" viewBox="0 0 12 12" aria-hidden="true"><path d="M5 2.5H2.5v7h7V7" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M7 1.5h3.5V5M10.5 1.5L5.5 6.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
  more: '<svg class="ic" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 2.5L6.5 6 3 9.5M6.5 2.5L10 6 6.5 9.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  up: '<svg class="ic" viewBox="0 0 12 12" aria-hidden="true"><path d="M6 10.5V2M2.5 5.5L6 2l3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  down: '<svg class="ic" viewBox="0 0 12 12" aria-hidden="true"><path d="M6 1.5V10M2.5 6.5L6 10l3.5-3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};
const companyLink = (key, name) => `<a href="#/company/${encodeURIComponent(key)}">${esc(name)}</a>`;
const officeLink = name => `<a href="#/office/${encodeURIComponent(name)}">${esc(name)}</a>`;
const egpLink = (t, p) => p
  ? `<a target="_blank" rel="noopener" href="https://www.eprocure.gov.bd/resources/common/ViewAwardedContracts.jsp?pkgLotId=${encodeURIComponent(p)}&tenderid=${encodeURIComponent(t)}">${T('e-GP', 'ই-জিপি')} ${ICON.ext}</a>`
  : '';
const shareBar = s => `<div class="share"><div class="track"><span style="width:${Math.min(100, s * 100)}%"></span></div>${pct(s)}</div>`;
const debTag = n => n ? ` <span class="tagdeb">${T('[debarred]', '[নিষিদ্ধ]')}</span>` : '';
const facts = rows => `<ul class="facts">${rows.map(([l, v]) =>
  `<li><span class="label">${l}</span><span class="leader"></span><span class="val">${v}</span></li>`).join('')}</ul>`;

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

// ---------- Page frame (menus, footer) in both languages ----------
const CHROME_BN = {
  'Independent public-data watchdog · not a government website': 'স্বাধীন জনতথ্য পর্যবেক্ষক · সরকারি ওয়েবসাইট নয়',
  Menu: 'মেনু', Home: 'প্রথম পাতা', 'AI Watchlist': 'এআই নজরতালিকা', Probashi: 'প্রবাসী', Plans: 'প্ল্যান', About: 'আমাদের কথা',
  'Type a company or office name (e.g. LGED Naogaon)': 'প্রতিষ্ঠান বা অফিসের নাম লিখুন (যেমন: LGED Naogaon)',
  Search: 'খুঁজুন', 'Risk Patterns': 'ঝুঁকির সংকেত', 'Go To': 'যান', 'Debarred Firms': 'নিষিদ্ধ প্রতিষ্ঠান',
  'Largest Contracts': 'সবচেয়ে বড় চুক্তি', 'Government Offices': 'সরকারি অফিস', 'AI Accuracy': 'এআই কতটা সঠিক',
  'How It Works': 'কীভাবে কাজ করে', 'Quick Links': 'দ্রুত লিংক', 'Home / At a glance': 'প্রথম পাতা / এক নজরে',
  'AI watchlist: firms to review first': 'এআই নজরতালিকা: আগে যাচাই করার প্রতিষ্ঠান', 'Unusual for their size': 'আকারের তুলনায় অস্বাভাবিক',
  'Offices where one company wins most': 'যে অফিসে একটি প্রতিষ্ঠান বেশিরভাগ কাজ পায়', 'Debarred firms found in contracts': 'চুক্তিতে পাওয়া নিষিদ্ধ প্রতিষ্ঠান',
  'Largest contracts': 'সবচেয়ে বড় চুক্তি', 'For Bangladeshis Abroad': 'প্রবাসীদের জন্য', 'My home district': 'আমার জেলা',
  'Check a company before you give or invest': 'টাকা দেওয়া বা বিনিয়োগের আগে প্রতিষ্ঠান যাচাই', 'Plans and waitlist': 'প্ল্যান ও অপেক্ষার তালিকা',
  'Contractor Check Report for banks (sample)': 'ব্যাংকের জন্য ঠিকাদার যাচাই রিপোর্ট (নমুনা)', Help: 'সাহায্য',
  'How Prohori works': 'প্রহরী কীভাবে কাজ করে', 'How to read a risk flag': 'ঝুঁকির সংকেত কীভাবে পড়বেন',
  'How accurate is the AI?': 'এআই কতটা সঠিক?', 'Original data: e-GP portal': 'মূল তথ্য: ই-জিপি পোর্টাল',
  TICKER: 'নোটিশ: প্রহরীর সংকেতগুলো যাচাইয়ের জন্য, অভিযোগ নয় — সিদ্ধান্ত সবসময় মানুষ নেয়। · এআই শুধু যাচাইয়ের অগ্রাধিকার ঠিক করে; কোনো প্রতিষ্ঠান সম্পর্কে সিদ্ধান্ত দেয় না।',
  FOOTER: 'তথ্যসূত্র: বাংলাদেশ ই-জিপি পোর্টাল (eprocure.gov.bd)-এর প্রকাশ্য চুক্তি-ঘোষণা ও নিষিদ্ধ তালিকা · প্রহরী একটি স্বাধীন উদ্যোগ; বিপিপিএ বা কোনো সরকারি অফিসের সঙ্গে যুক্ত নয়।',
};
const CHROME_EN = {
  TICKER: 'Notice: Flags shown on Prohori are patterns for review, not accusations — a human always decides. · AI scores rank firms for review; they never decide anything about a firm.',
  FOOTER: 'Data source: Bangladesh e-GP portal (eprocure.gov.bd) public award notices and debarment list · Prohori is an independent project and is not affiliated with BPPA or any government office.',
};
function applyChrome() {
  document.documentElement.lang = LANG;
  document.body.classList.toggle('lang-bn', LANG === 'bn');
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const k = el.dataset.i18n;
    el.textContent = LANG === 'bn' ? CHROME_BN[k] || k : CHROME_EN[k] || k;
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const k = el.dataset.i18nPh;
    el.placeholder = isPhone() ? T('Company or office name', 'প্রতিষ্ঠান বা অফিসের নাম') : LANG === 'bn' ? CHROME_BN[k] || k : k;
  });
  const t = document.getElementById('langToggle');
  t.textContent = LANG === 'bn' ? 'English' : 'বাংলা';
  t.classList.toggle('bn', LANG === 'en');
  tick();
}
function setLang(l) {
  LANG = l;
  store.set('lang', l);
  applyChrome();
  rebuildAI();
  route();
}

// Live date/time line like public portals show ("Tuesday, 03 Nov, 2026 12:05:26 BST").
function tick() {
  const now = new Date();
  const loc = LANG === 'bn' ? 'bn-BD' : 'en-GB';
  const d = now.toLocaleDateString(loc, { timeZone: 'Asia/Dhaka', weekday: 'long', day: '2-digit', month: 'short', year: 'numeric' });
  const t = now.toLocaleTimeString(loc, { timeZone: 'Asia/Dhaka', hour12: false });
  document.getElementById('clock').textContent = `${d} ${t} ${T('BST', 'বাংলাদেশ সময়')}`;
}
setInterval(tick, 1000);

async function home() {
  const [s, pat] = await Promise.all([api('/api/stats'), api('/api/patterns?limit=8')]);
  view.innerHTML = `
    <h1>${T("Who wins Bangladesh's government contracts?", 'বাংলাদেশের সরকারি কাজ কে পায়?')}</h1>
    <p>${T(`Prohori reads the contract awards that government offices publish on the national e-GP portal and
      highlights patterns worth a closer look — for example, one company winning most contracts at one office,
      or contracts going to firms the government has officially debarred.`,
      `সরকারি অফিসগুলো জাতীয় ই-জিপি পোর্টালে যেসব চুক্তি প্রকাশ করে, প্রহরী সেগুলো পড়ে এবং খতিয়ে দেখার মতো সংকেত দেখায় —
      যেমন, একটি অফিসের বেশিরভাগ কাজ একই প্রতিষ্ঠান পাচ্ছে, কিংবা সরকার যাদের নিষিদ্ধ করেছে তারাও কাজ পেয়েছে।`)}
      ${bnNote('সরকারি কাজ কে পায়, কত টাকায় — সহজে দেখুন।')}</p>
    <h2>${T('At a Glance', 'এক নজরে')}</h2>
    ${facts([
      [T('Contracts analysed', 'বিশ্লেষণ করা চুক্তি'), num(s.contracts)],
      [T('Total contract value', 'মোট চুক্তিমূল্য'), taka(s.value_bdt)],
      [T('Companies', 'প্রতিষ্ঠান'), num(s.companies)],
      [T('Government buying offices', 'সরকারি ক্রয়কারী অফিস'), num(s.offices)],
      [T("Companies winning 40%+ of an office's contracts", 'কোনো অফিসের ৪০%-এর বেশি কাজ পাওয়া প্রতিষ্ঠান'), `<a href="#/patterns">${num(s.dominant_companies)}</a>`],
      [T('Officially debarred firms found among winners', 'কাজ পাওয়াদের মধ্যে সরকারিভাবে নিষিদ্ধ প্রতিষ্ঠান'), `<a href="#/debarred">${num(s.debarred_found)}</a>`],
      [T('Active firms scored by the AI', 'এআই যাদের মূল্যায়ন করেছে (সক্রিয় প্রতিষ্ঠান)'), `<a href="#/watchlist">${num(s.risk.scored)}</a>`],
      [T('Firms the AI puts in its top 5% for review', 'এআই-এর শীর্ষ ৫% যাচাই-তালিকায় থাকা প্রতিষ্ঠান'), `<a href="#/watchlist">${num(s.risk.high)}</a>`],
      [T('Contracts signed between', 'চুক্তি সইয়ের সময়কাল'), `${date(s.first_date)} – ${date(s.last_date)}`],
      ...(s.data_updated ? [[T('Data updated (every night from e-GP)', 'তথ্য হালনাগাদ (প্রতি রাতে ই-জিপি থেকে)'), date(s.data_updated)]] : []),
    ])}
    <h2>${T('AI Early Warning', 'এআই আগাম সতর্কতা')}</h2>
    <p>${T(`Prohori's AI looks at each firm's whole contract history and ranks which firms to review first. In a test on past
      data, it put <b>${pctTxt(s.model.caught_share)} of firms that were later debarred</b> in its top 10%, about
      <b>${Math.round(s.model.months_early)} months before</b> the government debarred them.`,
      `প্রহরীর এআই প্রতিটি প্রতিষ্ঠানের পুরো চুক্তির ইতিহাস দেখে ঠিক করে কাদের আগে যাচাই করা দরকার। অতীতের তথ্য দিয়ে পরীক্ষায়,
      <b>পরে নিষিদ্ধ হওয়া প্রতিষ্ঠানগুলোর ${pctTxt(s.model.caught_share)}</b> এআই-এর শীর্ষ ১০%-এ ছিল — সরকার নিষিদ্ধ করার প্রায়
      <b>${dig(Math.round(s.model.months_early))} মাস আগে</b>।`)}
      <a href="#/watchlist">${T('See the AI watchlist', 'এআই নজরতালিকা দেখুন')} ${ICON.more}</a> · <a href="#/model">${T('How accurate is it?', 'এটি কতটা সঠিক?')} ${ICON.more}</a>
      ${bnNote('নিষিদ্ধ হওয়ার আগেই ঝুঁকি চিহ্নিত করা।')}</p>
    <h2>${T('Latest Risk Patterns', 'সাম্প্রতিক ঝুঁকির সংকেত')}</h2>
    <ul class="plain">${pat.map(r => `<li>${officeLink(r.office)} (${esc(place(r.district))}) — ${companyLink(r.winner_key, r.winner)}
      ${T(`won <b>${pct(r.top_share_n)}</b> of ${contracts(r.n_contracts)}`, `${contracts(r.n_contracts)}-এর মধ্যে <b>${pct(r.top_share_n)}</b> পেয়েছে`)}${debTag(r.n_debarments)}</li>`).join('')}</ul>
    <p style="margin-top:8px"><a href="#/patterns">${T('View all risk patterns', 'সব ঝুঁকির সংকেত দেখুন')} ${ICON.more}</a></p>
    <h2>${T('Important Notice', 'জরুরি কথা')}</h2>
    <ul class="plain">
      <li>${T(`Flags are <b>patterns for review, not accusations</b>. A high share can have innocent reasons
        (few local contractors, specialised work).`, `সংকেতগুলো <b>যাচাইয়ের জন্য, অভিযোগ নয়</b>। বেশি অংশ পাওয়ার নির্দোষ কারণও থাকতে পারে
        (এলাকায় ঠিকাদার কম, বিশেষ ধরনের কাজ)।`)} <span class="important">${T('A human always decides.', 'সিদ্ধান্ত সবসময় মানুষ নেয়।')}</span></li>
      <li>${T('Company names are matched by spelling. Different firms can share a name — verify by address on e-GP.',
        'প্রতিষ্ঠানের নাম বানান দিয়ে মেলানো হয়। একই নামে আলাদা প্রতিষ্ঠান থাকতে পারে — ই-জিপিতে ঠিকানা মিলিয়ে নিন।')}</li>
      <li>${T('Covers every contract award published on e-GP from December 2011 to today.',
        'ডিসেম্বর ২০১১ থেকে আজ পর্যন্ত ই-জিপিতে প্রকাশিত সব চুক্তি এখানে আছে।')}</li>
    </ul>`;
}

async function search(q) {
  const r = await api(`/api/search?q=${encodeURIComponent(q)}`);
  trackEvent('search', 'search');
  const comp = r.companies.map(c => `<tr>
      <td>${companyLink(c.key, c.name)}${debTag(c.n_debarments)}
        ${c.n_dominated_offices ? ` <span class="tagdom">${T('[dominant at an office]', '[একটি অফিসে প্রাধান্য]')}</span>` : ''}</td>
      <td class="num">${num(c.n_contracts)}</td><td class="num">${taka(c.value_bdt)}</td>
      <td class="num hide-sm">${num(c.n_districts)}</td></tr>`).join('');
  const offs = r.offices.map(o => `<tr><td>${officeLink(o.name)}</td><td>${esc(place(o.district))}</td>
      <td class="num">${num(o.n_contracts)}</td><td class="num">${taka(o.value_bdt)}</td></tr>`).join('');
  view.innerHTML = `<h1>${T(`Search results for “${esc(q)}”`, `“${esc(q)}”-এর ফলাফল`)}</h1>
    <h2>${T('Companies', 'প্রতিষ্ঠান')}</h2>
    ${comp ? `<table><tr><th>${T('Company', 'প্রতিষ্ঠান')}</th><th class="num">${T('Contracts', 'চুক্তি')}</th><th class="num">${T('Value', 'মূল্য')}</th><th class="num hide-sm">${T('Districts', 'জেলা')}</th></tr>${comp}</table>`
      : `<p class="muted">${T('No companies found.', 'কোনো প্রতিষ্ঠান পাওয়া যায়নি।')}</p>`}
    <h2>${T('Government Offices', 'সরকারি অফিস')}</h2>
    ${offs ? `<table><tr><th>${T('Office', 'অফিস')}</th><th>${T('District', 'জেলা')}</th><th class="num">${T('Contracts', 'চুক্তি')}</th><th class="num">${T('Value', 'মূল্য')}</th></tr>${offs}</table>`
      : `<p class="muted">${T('No offices found.', 'কোনো অফিস পাওয়া যায়নি।')}</p>`}`;
}

function yearList(rows) {
  const max = Math.max(...rows.map(r => r.value_bdt || 0), 1);
  return `<ul class="years">${rows.map(r => `<li><span>${dig(r.year)}</span>
    <span class="b" style="width:${Math.max(1, ((r.value_bdt || 0) / max) * 100)}%"></span>
    <span class="v">${contracts(r.n)} · ${taka(r.value_bdt)}</span></li>`).join('')}</ul>`;
}

// ---------- AI risk score ----------
let MODEL = null;               // cached /api/model (backtest numbers quoted next to scores)
const getModel = async () => MODEL || (MODEL = await api('/api/model'));
const topTxt = t => {
  const v = t < 1 ? t.toFixed(1) : Math.round(t);
  return T(`top ${v}%`, `শীর্ষ ${dig(v)}%`);
};
const BAND_BN = { very_high: 'খুব বেশি', high: 'বেশি', elevated: 'কিছুটা বেশি', typical: 'সাধারণ' };
const bandName = r => T(r.band_label, BAND_BN[r.band] || r.band_label);
const bandPill = r => `<span class="pill ${r.band}">${bandName(r)}</span>`;
const meter = top => `<div class="meter" title="${topTxt(top)}"><span style="left:${Math.min(99.5, 100 - top)}%"></span></div>`;
// A reason's value, formatted in the current language from the raw number the server sends.
function fmtVal(x) {
  const v = x.raw;
  if (v == null) return x.value;
  if (x.kind === 'pct') return pct(v);
  if (x.kind === 'x') return `${dig(v.toFixed(1))}×`;
  if (x.kind === 'tk') return taka(v);
  if (x.kind === 'd') return v >= 365 ? T(`${(v / 365).toFixed(1)} years`, `${dig((v / 365).toFixed(1))} বছর`)
    : T(`${Math.round(v)} days`, `${dig(Math.round(v))} দিন`);
  return num(Math.round(v));
}
const reasonLabel = y => T(y.label, y.label_bn || y.label);
const reasonList = rs => rs.length
  ? `<ul class="reasons">${rs.map(x => `<li><b>${esc(reasonLabel(x))}:</b> ${esc(fmtVal(x))}
      <span class="muted">— ${T(`higher than ${x.higher_than}% of active firms`, `সক্রিয় প্রতিষ্ঠানগুলোর ${dig(x.higher_than)}%-এর চেয়ে বেশি`)}</span></li>`).join('')}</ul>`
  : `<p class="muted">${T('No single signal stands out; the score comes from many small factors.', 'কোনো একক সংকেত আলাদা করে চোখে পড়ে না; অনেক ছোট ছোট বিষয় মিলিয়ে স্কোর।')}</p>`;

function riskSection(r, m, c) {
  const head = `<h2>${T('AI Review Priority', 'এআই যাচাই-অগ্রাধিকার')} ${bnNote('(এআই অগ্রাধিকার)')}</h2>`;
  if (!r.risk.length) {
    return `${head}<p class="muted">${c.n_debarments
      ? T('Not scored: this firm is already on the debarment list.', 'মূল্যায়ন করা হয়নি: প্রতিষ্ঠানটি আগে থেকেই নিষিদ্ধ তালিকায় আছে।')
      : T('Not scored: no contract won in the last 3 years.', 'মূল্যায়ন করা হয়নি: গত ৩ বছরে কোনো চুক্তি পায়নি।')}</p>`;
  }
  const t5 = m.main_test.top_5pct;
  const block = x => `
    <div class="risk">
      <div class="riskhead">${bandPill(x)}
        <span>${T(`<b>${topTxt(x.top_pct)}</b> of ${num(r.scored)} active firms · among firms of similar size: <b>${topTxt(x.top_pct_size)}</b>`,
          `${num(r.scored)}টি সক্রিয় প্রতিষ্ঠানের মধ্যে <b>${topTxt(x.top_pct)}</b> · একই আকারের প্রতিষ্ঠানের মধ্যে: <b>${topTxt(x.top_pct_size)}</b>`)}</span>
        ${r.risk.length > 1 ? `<span class="muted">(${T(`${esc(x.division)} division`, `${esc(place(x.division))} বিভাগ`)})</span>` : ''}</div>
      ${meter(x.top_pct)}
      <div class="why">${T('Main reasons for the score:', 'স্কোরের প্রধান কারণ:')}</div>${reasonList(x.reasons)}
      ${x.behaviour_reasons.length && x.reasons.some(y => y.size_related)
        ? `<div class="why">${T('Not counting size:', 'আকার বাদ দিলে:')}</div>${reasonList(x.behaviour_reasons)}` : ''}
    </div>`;
  const [first, ...others] = r.risk;
  const otherList = others.map(x => `${esc(place(x.division))}: ${bandName(x).toLowerCase()}`).join(', ');
  const blocks = block(first) + (others.length ? `<details class="more"><summary>${T(
    `Show the ${others.length} other division${others.length > 1 ? 's' : ''} (${otherList})`,
    `অন্য ${dig(others.length)}টি বিভাগ দেখুন (${otherList})`)}</summary>
    ${others.map(block).join('')}</details>` : '');
  return `${head}
    ${r.risk.length > 1 ? `<p class="muted">${T(`This name wins contracts in ${r.risk.length} divisions. Each is scored separately because they may be different firms.`,
      `এই নামে ${dig(r.risk.length)}টি বিভাগে কাজ পাওয়া গেছে। এগুলো আলাদা প্রতিষ্ঠান হতে পারে, তাই প্রতিটির আলাদা মূল্যায়ন।`)}</p>` : ''}
    ${blocks}
    <p class="caveat">${T(`This is a statistical estimate from public records, <b>not a finding of wrongdoing</b>.
      In past tests, firms in the AI's top 5% were about ${Math.round(t5.lift)} times more likely than average to be
      debarred within 2 years. Even so, about ${Math.round(100 - t5.precision * 100)} in 100 of them were not.
      Innocent reasons are common: large firms simply win more contracts.`,
      `এটি প্রকাশ্য তথ্য থেকে পরিসংখ্যানগত অনুমান, <b>অন্যায়ের প্রমাণ নয়</b>। অতীতের পরীক্ষায়, এআই-এর শীর্ষ ৫%-এ থাকা প্রতিষ্ঠানগুলো
      ২ বছরের মধ্যে নিষিদ্ধ হওয়ার সম্ভাবনা গড়ের চেয়ে প্রায় ${dig(Math.round(t5.lift))} গুণ বেশি ছিল। তবুও প্রতি ১০০টির মধ্যে প্রায়
      ${dig(Math.round(100 - t5.precision * 100))}টি নিষিদ্ধ হয়নি। নির্দোষ কারণ প্রায়ই থাকে: বড় প্রতিষ্ঠান স্বাভাবিকভাবেই বেশি কাজ পায়।`)}
      <a href="#/model">${T('How accurate is the AI?', 'এআই কতটা সঠিক?')}</a> · <a href="#/about">${T('Think this is wrong?', 'ভুল মনে হচ্ছে?')}</a>
      ${bnNote('এটি একটি পরিসংখ্যানগত অনুমান, অভিযোগ নয়।')}</p>`;
}

// ---------- Floating "Prohori AI" assistant (Amazon Nova 2 Lite) ----------
// A round button in the bottom-right corner of every page. It opens a chat panel that answers
// questions about the page being viewed (a company, an office, or a list), using only that page's facts.
const AI_ICON = {
  ask: '<svg class="aic" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5h16v10H10l-4.5 3.5v-3.5H4z" fill="#eaf4e0" stroke="#2c6e1c" stroke-width="1.8" stroke-linejoin="round"/><path d="M8 9.5h8M8 12.5h5" stroke="#2c6e1c" stroke-width="1.6" stroke-linecap="round"/><circle cx="19.5" cy="5.5" r="2.6" fill="#d62828"/></svg>',
  send: '<svg class="aic" viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 11.5L20 4l-6.5 16-2.6-6.4z" fill="#eaf4e0" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/></svg>',
  close: '<svg class="aic" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
  fab: '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 7h22v14H14l-6 5v-5H5z" fill="#eaf4e0" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/><path d="M10 12h12M10 16h7" stroke="#2c6e1c" stroke-width="2" stroke-linecap="round"/><circle cx="26" cy="7" r="3.6" fill="#d62828" stroke="#fff" stroke-width="1.2"/></svg>',
};
// Example questions per page, in each language.
const AI_EXAMPLES = {
  bn: {
    company: ['এই প্রতিষ্ঠানের ঝুঁকির মাত্রা এমন কেন?', 'কোন অফিস থেকে এটি সবচেয়ে বেশি কাজ পায়?', 'এটা কি দুর্নীতির প্রমাণ?', 'আমি তথ্যগুলো কীভাবে যাচাই করব?'],
    office: ['এই অফিসে কারা সবচেয়ে বেশি কাজ পায়?', 'একটি প্রতিষ্ঠান কি বেশিরভাগ কাজ পাচ্ছে?', 'এই অফিস মোট কত টাকার কাজ দিয়েছে?'],
    page: ['এই পাতায় কী দেখানো হচ্ছে?', 'এআই কতটা সঠিক?', 'প্রহরী কীভাবে কাজ করে?', 'ঝুঁকির সংকেত মানে কি অভিযোগ?'],
    district: ['এই জেলায় কোন বড় প্রকল্প হচ্ছে?', 'এই জেলায় কে সবচেয়ে বেশি কাজ পায়?', 'কোনো নিষিদ্ধ প্রতিষ্ঠান কি এখানে কাজ পেয়েছে?'],
    districts: ['আমার জেলায় কী তৈরি হচ্ছে কীভাবে দেখব?', 'গত বছর কোন জেলায় সবচেয়ে বেশি চুক্তি হয়েছে?'],
    probashi: ['বিদেশ থেকে কীভাবে নিজের জেলার খবর রাখব?', 'বিনিয়োগের আগে প্রতিষ্ঠান কীভাবে যাচাই করব?'],
    check: ['বিনিয়োগের আগে কী কী যাচাই করব?', 'সরকারিভাবে নিষিদ্ধ মানে কী?'],
    pricing: ['প্রহরী কারা টাকা দিয়ে ব্যবহার করবে?', 'টাকা দিলে কি স্কোর বদলানো যায়?', 'ঠিকাদার যাচাই রিপোর্টে কী থাকে?'],
  },
  en: {
    company: ['Why is this firm ranked like this?', 'Which office gives it the most work?', 'Is this proof of corruption?', 'How can I check these facts?'],
    office: ['Who wins the most contracts here?', 'Does one company get most of the work?', 'How much has this office spent in total?'],
    page: ['What does this page show?', 'How accurate is the AI?', 'How does Prohori work?', 'Is a risk flag an accusation?'],
    district: ['What big projects are being built here?', 'Who wins the most contracts in this district?', 'Have any debarred firms worked here?'],
    districts: ['How do I find what is being built in my district?', 'Which district got the most contracts last year?'],
    probashi: ['How can I follow my home district from abroad?', 'How do I check a company before I invest?'],
    check: ['What should I check before I invest in a firm?', 'What does officially debarred mean?'],
    pricing: ['Who pays for Prohori?', 'Can paying change a score?', 'What is in the Contractor Check Report?'],
  },
};
let AICTX = { ctx: 'home', key: '', label: '', kind: 'page' };
const AICHATS = {};                       // conversation per page, kept while the site is open
const aiId = () => `${AICTX.ctx}:${AICTX.key}`;

// Model output is plain text: paragraphs and "- " bullet lines. Escape it, then build simple HTML.
function aiText(t) {
  const out = [];
  let list = [];
  const flush = () => { if (list.length) { out.push(`<ul>${list.join('')}</ul>`); list = []; } };
  for (const line of String(t).split('\n')) {
    const s = line.trim();
    if (!s) { flush(); continue; }
    if (/^[-–]\s+/.test(s)) list.push(`<li>${esc(s.replace(/^[-–]\s+/, ''))}</li>`);
    else { flush(); out.push(`<p>${esc(s)}</p>`); }
  }
  flush();
  return out.join('');
}

async function aiFetch(path, body) {
  const r = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j.detail === 'string' ? j.detail : `Error ${r.status}`);
  return j;
}

let aiKeysBound = false;
function buildAI(openNow = false) {
  document.body.insertAdjacentHTML('beforeend', `
    <button type="button" id="aifab" class="aifab" aria-label="${T('Ask Prohori AI about this page', 'এই পাতা নিয়ে প্রহরী এআই-কে প্রশ্ন করুন')}" title="${T('Prohori AI — ask about this page', 'প্রহরী এআই — এই পাতা নিয়ে প্রশ্ন করুন')}">
      ${AI_ICON.fab}<span class="aifab-tip" id="aitip" hidden>${T('Ask the AI about this page', 'এই পাতা নিয়ে এআই-কে প্রশ্ন করুন')}</span></button>
    <section id="aipanel" class="aipanel" hidden role="dialog" aria-label="Prohori AI">
      <header class="aihead">
        <div class="aititle">${AI_ICON.ask}<div><b>${T('Prohori AI', 'প্রহরী এআই')}</b><span>${T('Ask in English or Bangla', 'বাংলা বা ইংরেজিতে প্রশ্ন করুন')}</span></div></div>
        <button type="button" class="aiclose" id="aiclose" aria-label="${T('Close', 'বন্ধ')}">${AI_ICON.close}</button>
      </header>
      <div class="aictx" id="aictx"></div>
      <div class="aibody" id="aibody"></div>
      <form class="aiask" id="aiform">
        <textarea name="q" rows="1" maxlength="2000" placeholder="${T('Type your question…', 'প্রশ্ন লিখুন…')}"></textarea>
        <button type="submit" class="aisend" aria-label="${T('Send', 'পাঠান')}">${AI_ICON.send}</button>
      </form>
      <p class="aifoot">${T('AI can make mistakes.', 'এআই ভুল করতে পারে।')}</p>
    </section>`);
  const fab = document.getElementById('aifab'), panel = document.getElementById('aipanel');
  const body = document.getElementById('aibody'), form = document.getElementById('aiform');
  const open = on => {
    panel.hidden = !on;
    document.body.classList.toggle('ai-open', on);
    document.getElementById('aitip').hidden = true;
    if (on) { renderAI(); if (window.innerWidth > 760) form.q.focus(); }
  };
  fab.addEventListener('click', () => open(panel.hidden));
  document.getElementById('aiclose').addEventListener('click', () => open(false));
  if (!aiKeysBound) {
    aiKeysBound = true;
    document.addEventListener('keydown', e => {
      const p = document.getElementById('aipanel');
      if (e.key === 'Escape' && p && !p.hidden) { p.hidden = true; document.body.classList.remove('ai-open'); }
    });
  }
  // Text box grows with the text (up to about 6 lines, then scrolls). Enter sends, Shift+Enter adds a new line.
  const box = form.q;
  const fit = () => { box.style.height = 'auto'; box.style.height = `${Math.min(box.scrollHeight, 150)}px`; };
  box.addEventListener('input', fit);
  box.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener('submit', e => { e.preventDefault(); aiSend(box.value); box.value = ''; fit(); });
  body.addEventListener('click', e => {
    const b = e.target.closest('[data-act]');
    if (!b) return;
    if (b.dataset.act === 'explain') aiSend(T('Explain this page in simple words', 'এই পাতা সহজ বাংলায় বুঝিয়ে দিন'), true);
    else aiSend(b.textContent);
  });
  if (openNow) open(true);

  // First visit in this browser tab: a small hint next to the button for a few seconds.
  let seen = false;
  try { seen = sessionStorage.getItem('aiTip') === '1'; sessionStorage.setItem('aiTip', '1'); } catch (e) { /* storage blocked */ }
  if (!seen) {
    const tip = document.getElementById('aitip');
    setTimeout(() => { if (panel.hidden) tip.hidden = false; }, 1200);
    setTimeout(() => { tip.hidden = true; }, 9000);
  }
}
function rebuildAI() {
  const wasOpen = !document.getElementById('aipanel')?.hidden;
  document.getElementById('aifab')?.remove();
  document.getElementById('aipanel')?.remove();
  buildAI(wasOpen);
}

// Called after each page renders, so the assistant knows what the visitor is looking at.
function setAIContext(ctx, key, label) {
  AICTX = { ctx, key: key || '', label: label || '', kind: ctx === 'report' ? 'company' : ctx === 'company' || ctx === 'office' ? ctx : 'page' };
  if (!document.getElementById('aipanel').hidden) renderAI();
}

function renderAI() {
  const { kind, label } = AICTX;
  document.getElementById('aictx').innerHTML = `${T('This page:', 'এই পাতা:')} <b>${esc(label || 'Prohori')}</b>`;
  const msgs = AICHATS[aiId()] || [];
  const intro = kind === 'company'
    ? T(`I am Prohori AI. Ask me about the government contracts of <b>${esc(label)}</b>.`, `আমি প্রহরী এআই। <b>${esc(label)}</b>-এর সরকারি চুক্তির তথ্য নিয়ে প্রশ্ন করুন।`)
    : kind === 'office'
      ? T(`I am Prohori AI. Ask me about the contracts of <b>${esc(label)}</b>.`, `আমি প্রহরী এআই। <b>${esc(label)}</b> অফিসের চুক্তির তথ্য নিয়ে প্রশ্ন করুন।`)
      : T('I am Prohori AI. Ask me about this page or about Prohori.', 'আমি প্রহরী এআই। এই পাতা বা প্রহরী সম্পর্কে প্রশ্ন করুন।');
  const ex = AI_EXAMPLES[LANG][AICTX.ctx] || AI_EXAMPLES[LANG][kind];
  const body = document.getElementById('aibody');
  body.innerHTML = `
    <div class="aimsg bot">${intro}</div>
    ${msgs.map(m => `<div class="aimsg me">${esc(m.q)}</div>
      <div class="aimsg bot${m.err ? ' err' : ''}">${m.a == null ? `<span class="aityping">${T('AI is writing', 'এআই লিখছে')}<i>.</i><i>.</i><i>.</i></span>`
        : m.err ? esc(m.a) : aiText(m.a)}</div>`).join('')}
    ${msgs.some(m => m.explain && !m.err) ? '' : `<button type="button" data-act="explain" class="aibtn">${AI_ICON.ask} ${T('Explain this page in simple words', 'এই পাতা সহজ বাংলায় বুঝিয়ে দিন')}</button>`}
    ${msgs.length ? '' : `<div class="aichips"><span class="muted">${T('For example:', 'উদাহরণ:')}</span>
      ${ex.map(q => `<button type="button" data-act="ask" class="chip">${esc(q)}</button>`).join('')}</div>`}`;
  // Show the newest question at the top, so a long answer can be read from its first line.
  const last = [...body.querySelectorAll('.aimsg.me')].pop();
  body.scrollTop = last ? last.offsetTop - 8 : 0;
}

async function aiSend(question, explain = false) {
  question = String(question || '').trim();
  if (!explain && question.length < 3) return;
  const { ctx, key } = AICTX, id = aiId();
  trackEvent('chat', ctx);
  const m = { q: question, a: null, explain };
  const chat = (AICHATS[id] ||= []);
  // The last few finished turns go along, so the AI understands follow-ups ("I mean this line").
  const history = chat.filter(x => x.a != null && !x.err).slice(-4).map(x => ({ q: x.q, a: x.a }));
  chat.push(m);
  renderAI();
  try {
    const r = explain
      ? await aiFetch(`/api/explain?ctx=${encodeURIComponent(ctx)}&key=${encodeURIComponent(key)}&lang=${LANG}`)
      : await aiFetch('/api/ask', { ctx, key, question, history });
    m.a = r.text;
  } catch (e) {
    m.a = e.message; m.err = true;
  }
  if (aiId() === id && !document.getElementById('aipanel').hidden) renderAI();
}

function bidFacts(b) {
  if (!b || !b.pages) return '';
  return `<h2>${T('From Contract Detail Pages', 'চুক্তির বিস্তারিত পাতা থেকে')}</h2>
    ${facts([
      [T('Detail pages checked', 'যাচাই করা বিস্তারিত পাতা'), T(`${num(b.pages)} of this firm's contracts`, `এই প্রতিষ্ঠানের ${num(b.pages)}টি চুক্তি`)],
      ...(b.with_bids ? [[T('Typical number of tenders received', 'সাধারণত কয়টি দরপত্র জমা পড়ে'), num(Math.round(b.median_received))],
        [T('Contracts with only one tender received', 'মাত্র একটি দরপত্র জমা পড়া চুক্তি'), T(`${num(b.single_bid)} of ${num(b.with_bids)}`, `${num(b.with_bids)}টির মধ্যে ${num(b.single_bid)}টি`)]] : []),
      [T('Contract not signed in time', 'সময়মতো সই না হওয়া চুক্তি'), num(b.sign_late || 0)],
      [T('Performance security not given in time', 'সময়মতো জামানত না দেওয়া'), num(b.ps_late || 0)],
    ])}
    <p class="muted" style="margin-top:6px">${T(`Shown for information. These facts are not used in the AI score: we tested
      them and they did not predict debarment (<a href="#/model">details</a>).`, `শুধু তথ্যের জন্য দেখানো হলো। এগুলো এআই স্কোরে ব্যবহার হয় না:
      পরীক্ষা করে দেখা গেছে এগুলো নিষিদ্ধ হওয়ার পূর্বাভাস দেয় না (<a href="#/model">বিস্তারিত</a>)।`)}</p>`;
}

async function company(key) {
  const [r, m] = await Promise.all([api(`/api/company?key=${encodeURIComponent(key)}`), getModel()]);
  const c = r.company;
  const hasBids = r.recent.some(x => x.received != null);
  const labels = { high: T('High:', 'গুরুতর:'), medium: T('Review:', 'যাচাই করুন:'), info: T('Note:', 'লক্ষ করুন:') };
  const flags = r.flags.length
    ? `<ul class="flags">${r.flags.map(f => `<li class="${f.level}"><span class="lvl">${labels[f.level]}</span>${esc(T(f.en, f.bn))}
        ${f.detail ? `<span class="detail">${T('Reason on record:', 'নথিতে কারণ:')} ${esc(f.detail)}</span>` : ''}</li>`).join('')}</ul>`
    : `<p>${T('No risk patterns found by the current rules.', 'বর্তমান নিয়মে কোনো ঝুঁকির সংকেত পাওয়া যায়নি।')}</p>`;
  view.innerHTML = `
    <h1>${esc(c.name)}</h1>
    ${facts([
      [T('Contracts won', 'জেতা চুক্তি'), num(c.n_contracts)],
      [T('Total value', 'মোট মূল্য'), taka(c.value_bdt)],
      [T('Offices / districts', 'অফিস / জেলা'), T(`${c.n_offices} offices in ${c.n_districts} districts`, `${num(c.n_districts)}টি জেলায় ${num(c.n_offices)}টি অফিস`)],
      [T('Active period', 'কাজের সময়কাল'), `${date(c.first_contract)} – ${date(c.last_contract)}`],
    ])}
    <p class="actions"><a class="btn-line" href="#/report/${encodeURIComponent(key)}">${T('Contractor Check Report (for banks)', 'ঠিকাদার যাচাই রিপোর্ট (ব্যাংকের জন্য)')}</a>
      ${signupBtn('notify', T('Notify me when it wins a contract', 'নতুন কাজ পেলে আমাকে জানান'), c.name)}</p>
    <h2>${T('Risk Patterns', 'ঝুঁকির সংকেত')} ${bnNote('(ঝুঁকির সংকেত)')}</h2>${flags}
    ${riskSection(r, m, c)}
    <h2>${T('Contracts Won per Year', 'বছরভিত্তিক জেতা চুক্তি')}</h2>${yearList(r.by_year)}
    <h2>${T('Where It Wins', 'কোথায় কাজ পায়')}</h2>
    <table><tr><th>${T('Office', 'অফিস')}</th><th class="hide-sm">${T('District', 'জেলা')}</th><th class="num">${T('Won', 'পেয়েছে')}</th><th>${T("Share of office's contracts", 'অফিসের চুক্তিতে অংশ')}</th></tr>
      ${r.top_offices.map(o => `<tr><td>${officeLink(o.procuring_entity)}</td><td class="hide-sm">${esc(place(o.district))}</td>
        <td class="num">${num(o.n)} / ${num(o.office_n)}</td><td>${shareBar(o.share_n)}</td></tr>`).join('')}</table>
    <h2>${T('Recent Contracts', 'সাম্প্রতিক চুক্তি')}</h2>
    <table><tr><th>${T('Signed', 'সইয়ের তারিখ')}</th><th>${T('Work', 'কাজ')}</th><th class="hide-sm">${T('Office', 'অফিস')}</th><th>${T('Method', 'পদ্ধতি')}</th>${hasBids ? `<th class="num">${T('Tenders', 'দরপত্র')}</th>` : ''}<th class="num">${T('Value', 'মূল্য')}</th><th></th></tr>
      ${r.recent.map(x => `<tr><td>${date(x.signed_date)}</td><td class="title">${esc(x.title)}</td>
        <td class="hide-sm">${officeLink(x.procuring_entity)}</td><td>${esc(x.method)}</td>
        ${hasBids ? `<td class="num">${x.received != null ? num(x.received) : '—'}</td>` : ''}
        <td class="num">${taka(x.value_bdt)}</td><td>${egpLink(x.tender_id, x.pkg_lot_id)}</td></tr>`).join('')}</table>
    ${bidFacts(r.bids)}`;
}

async function watchlist(mode = 'overall', division = '') {
  if (mode !== 'size') mode = 'overall';
  const [r, m] = await Promise.all([
    api(`/api/watchlist?view=${mode}&division=${encodeURIComponent(division)}&limit=100`), getModel()]);
  const link = (v, d, label, on) => on ? `<b>${label}</b>` : `<a href="#/watchlist/${v}/${encodeURIComponent(d)}">${label}</a>`;
  const t5 = m.main_test.top_5pct;
  view.innerHTML = `
    <h1>${T('AI Watchlist: Firms to Review First', 'এআই নজরতালিকা: আগে যাচাই করার প্রতিষ্ঠান')}</h1>
    <p>${T(`The AI ranks every active contractor (${num(r.scored)} firms) by how much its contract record looks like the
      records of firms that were later debarred.`, `এআই প্রতিটি সক্রিয় ঠিকাদারকে (${num(r.scored)}টি প্রতিষ্ঠান) সাজায় — কার চুক্তির ইতিহাস পরে নিষিদ্ধ
      হওয়া প্রতিষ্ঠানগুলোর সঙ্গে কতটা মেলে।`)} <span class="important">${T('This is a review list, not a list of guilty firms.', 'এটি যাচাইয়ের তালিকা, দোষী প্রতিষ্ঠানের তালিকা নয়।')}</span>
      ${T(`In past tests, firms in the top 5% were about ${Math.round(t5.lift)} times more likely than average to be
      debarred within 2 years, but about ${Math.round(100 - t5.precision * 100)} in 100 were not.`,
      `অতীতের পরীক্ষায় শীর্ষ ৫%-এর প্রতিষ্ঠানগুলোর ২ বছরের মধ্যে নিষিদ্ধ হওয়ার সম্ভাবনা গড়ের প্রায় ${dig(Math.round(t5.lift))} গুণ ছিল,
      তবে প্রতি ১০০টির মধ্যে প্রায় ${dig(Math.round(100 - t5.precision * 100))}টি নিষিদ্ধ হয়নি।`)}
      ${bnNote('যাচাইয়ের তালিকা — দোষী প্রতিষ্ঠানের তালিকা নয়।')}</p>
    <p class="tabs">${T('Rank by:', 'সাজানো:')} ${link('overall', division, T('Overall risk', 'সামগ্রিক ঝুঁকি'), mode === 'overall')} ·
      ${link('size', division, T('Unusual for its size', 'আকারের তুলনায় অস্বাভাবিক'), mode === 'size')}
      <span class="muted">${mode === 'size'
        ? T('(compared only with firms that won a similar number of contracts; firms with 10+ contracts)', '(শুধু কাছাকাছি সংখ্যক চুক্তি পাওয়া প্রতিষ্ঠানের সঙ্গে তুলনা; ১০টির বেশি চুক্তি পাওয়া প্রতিষ্ঠান)')
        : T('(big firms rank high: size is the strongest warning sign in past data)', '(বড় প্রতিষ্ঠান উপরে থাকে: অতীতের তথ্যে আকারই সবচেয়ে শক্ত সতর্কসংকেত)')}</span></p>
    <p class="tabs">${T('Division:', 'বিভাগ:')} ${link(mode, '', T('All', 'সব'), !division)} ·
      ${r.divisions.map(d => link(mode, d, esc(place(d)), d === division)).join(' · ')}</p>
    <table><tr><th class="num">#</th><th>${T('Company', 'প্রতিষ্ঠান')}</th><th>${T('Priority', 'অগ্রাধিকার')}</th><th class="num">${T('Overall', 'সামগ্রিক')}</th><th class="num">${T('Vs. similar size', 'একই আকারের তুলনায়')}</th>
      <th class="hide-sm">${T('Main reasons', 'প্রধান কারণ')}</th><th class="num">${T('Contracts', 'চুক্তি')}</th></tr>
      ${r.rows.map((x, i) => `<tr><td class="num">${num(i + 1)}</td><td>${companyLink(x.winner_key, x.name)} <span class="muted">(${esc(place(x.division))})</span>
          ${x.debarred_elsewhere ? ` <span class="tagdeb">${T('[name on debarment list]', '[নাম নিষিদ্ধ তালিকায়]')}</span>` : ''}</td>
        <td>${bandPill(x)}</td><td class="num">${topTxt(x.top_pct)}</td><td class="num">${topTxt(x.top_pct_size)}</td>
        <td class="hide-sm">${esc((mode === 'size' ? x.behaviour_reasons : x.reasons).map(reasonLabel).join('; ') || '—')}</td>
        <td class="num">${num(x.n_contracts)}</td></tr>`).join('')}</table>
    <p class="muted" style="margin-top:8px">${T('“[name on debarment list]”: a firm with this name was debarred, possibly in another division. Firms already debarred in the same division are not scored.',
      '“[নাম নিষিদ্ধ তালিকায়]”: এই নামের কোনো প্রতিষ্ঠান নিষিদ্ধ হয়েছে, হয়তো অন্য বিভাগে। একই বিভাগে আগে থেকে নিষিদ্ধ প্রতিষ্ঠানের মূল্যায়ন করা হয় না।')}</p>`;
}

const WEIGHT_BN = {
  'total contract value': 'মোট চুক্তিমূল্য', 'share won as a joint venture': 'যৌথ উদ্যোগে জেতা চুক্তির অংশ',
  'share of open-tendering contracts': 'উন্মুক্ত দরপত্রের চুক্তির অংশ', 'largest contract': 'সবচেয়ে বড় চুক্তি',
  'share of contracts from local-government engineering (LGED)': 'এলজিইডি থেকে পাওয়া চুক্তির অংশ',
  'contracts won in the last 12 months': 'গত ১২ মাসে জেতা চুক্তি', 'share of road contracts': 'সড়কের কাজের অংশ',
  'contracts won (all time)': 'মোট জেতা চুক্তি', 'average contract size': 'গড় চুক্তির আকার', 'number of ministries': 'মন্ত্রণালয়ের সংখ্যা',
  'share of its own contracts from one office': 'নিজের কাজের কত অংশ একটি অফিস থেকে',
  'typical days from advertisement to contract': 'বিজ্ঞাপন থেকে চুক্তি পর্যন্ত সাধারণ সময়',
  'share of contracts from roads & highways': 'সড়ক ও জনপথ থেকে পাওয়া চুক্তির অংশ', 'time since first contract': 'প্রথম চুক্তির পর থেকে সময়',
  'growth in contracts vs the year before': 'আগের বছরের তুলনায় চুক্তি বৃদ্ধি', "share of last year's offices that were new to it": 'গত বছরের নতুন অফিসের অংশ',
  'contract value in the last 12 months': 'গত ১২ মাসের চুক্তিমূল্য', 'share of contracts signed under 21 days after advertisement': 'বিজ্ঞাপনের ২১ দিনের মধ্যে সই হওয়া চুক্তির অংশ',
  'share of water contracts': 'পানির কাজের অংশ', 'share of supply contracts': 'সরবরাহ চুক্তির অংশ', 'share of bridge contracts': 'সেতুর কাজের অংশ',
  'share of request-for-quotation contracts': 'দরপ্রস্তাব (আরএফকিউ) চুক্তির অংশ', 'recent contract size vs its usual size': 'সাম্প্রতিক চুক্তির আকার বনাম সাধারণ আকার',
  'time since last contract': 'শেষ চুক্তির পর থেকে সময়', 'share of building contracts': 'ভবনের কাজের অংশ',
  "highest share of a single office's contracts": 'একটি অফিসের চুক্তিতে সর্বোচ্চ অংশ', 'share of limited-tendering contracts': 'সীমিত দরপত্রের চুক্তির অংশ',
  'buying offices in the last 12 months': 'গত ১২ মাসে ক্রয়কারী অফিসের সংখ্যা', 'offices where it wins 40%+ of contracts': 'যেসব অফিসে ৪০%+ চুক্তি পায়',
  'share of repair contracts': 'মেরামতের কাজের অংশ', 'number of districts': 'জেলার সংখ্যা', 'share of service contracts': 'সেবা চুক্তির অংশ',
  'number of buying offices': 'ক্রয়কারী অফিসের সংখ্যা', 'share of electric contracts': 'বৈদ্যুতিক কাজের অংশ',
  'share of direct / single-source contracts': 'সরাসরি / একক উৎসের চুক্তির অংশ',
};
const f2 = (x, d) => dig(x.toFixed(d));
async function model() {
  const m = await getModel();
  const a = m.main_test, b = m.stability_fold;
  const cap = a.caught_in_advance;
  const tops = [[T('Top 1%', 'শীর্ষ ১%'), a.top_1pct], [T('Top 5%', 'শীর্ষ ৫%'), a.top_5pct], [T('Top 10%', 'শীর্ষ ১০%'), a.top_10pct]];
  const snap = Object.entries(a.auc_per_snapshot);
  const de = m.detail_eval && m.detail_eval.main_test;
  const w = Object.entries(m.weights || {});
  view.innerHTML = `
    <h1>${T('How Accurate Is the AI?', 'এআই কতটা সঠিক?')}</h1>
    <p>${T(`We tested the AI the way you would test a weather forecast. We went back to past dates, let the AI rank every
      active firm using <b>only what was known on that date</b>, and then checked which firms the government actually
      debarred in the next ${m.horizon_months / 12} years. The AI never saw those later debarments while learning.`,
      `আবহাওয়ার পূর্বাভাস যেভাবে যাচাই করা হয়, এআই-কেও সেভাবে পরীক্ষা করা হয়েছে। অতীতের কিছু তারিখে ফিরে গিয়ে এআই-কে
      <b>শুধু সেই তারিখ পর্যন্ত জানা তথ্য</b> দিয়ে সব সক্রিয় প্রতিষ্ঠান সাজাতে দেওয়া হয়েছে, তারপর দেখা হয়েছে পরের
      ${dig(m.horizon_months / 12)} বছরে সরকার আসলে কাদের নিষিদ্ধ করেছে। শেখার সময় এআই সেই পরের নিষেধাজ্ঞাগুলো দেখেনি।`)}
      ${bnNote('অতীতের তথ্য দিয়ে পরীক্ষা: এআই আগে থেকেই কতটা ধরতে পেরেছে।')}</p>

    <h2>${T('Main Test (July 2023 – July 2024)', 'প্রধান পরীক্ষা (জুলাই ২০২৩ – জুলাই ২০২৪)')}</h2>
    ${facts([
      [T('Test dates', 'পরীক্ষার তারিখ'), T(`${snap.length} dates, every 3 months (${date(snap[0][0])} – ${date(snap[snap.length - 1][0])})`,
        `${dig(snap.length)}টি তারিখ, প্রতি ৩ মাস পরপর (${date(snap[0][0])} – ${date(snap[snap.length - 1][0])})`)],
      [T('Firm records tested', 'পরীক্ষিত প্রতিষ্ঠান-রেকর্ড'), num(a.test_rows)],
      [T('Firms debarred within 2 years of a test date', 'পরীক্ষার তারিখের ২ বছরের মধ্যে নিষিদ্ধ প্রতিষ্ঠান'), T(`${num(cap.banned_entities_in_test)} firms`, `${num(cap.banned_entities_in_test)}টি`)],
      [T("Firms caught early (in the AI's top 10% before the ban)", 'আগেই ধরা পড়েছে (নিষেধাজ্ঞার আগে এআই-এর শীর্ষ ১০%-এ)'),
        `<b>${T(`${num(cap.flagged_top10pct_before_ban)} of ${num(cap.banned_entities_in_test)}`, `${num(cap.banned_entities_in_test)}টির মধ্যে ${num(cap.flagged_top10pct_before_ban)}টি`)} (${pctTxt(cap.share)})</b>`],
      [T('How early (median)', 'কত আগে (মধ্যমা)'), T(`about ${Math.round(cap.median_months_before_ban)} months before the ban`, `নিষেধাজ্ঞার প্রায় ${dig(Math.round(cap.median_months_before_ban))} মাস আগে`)],
      [T('Ranking score (AUC)', 'সাজানোর স্কোর (AUC)'), T(`${a.roc_auc.toFixed(2)} (95% range ${a.roc_auc_95ci[0].toFixed(2)}–${a.roc_auc_95ci[1].toFixed(2)})`,
        `${f2(a.roc_auc, 2)} (৯৫% সীমা ${f2(a.roc_auc_95ci[0], 2)}–${f2(a.roc_auc_95ci[1], 2)})`)],
    ])}
    <p class="muted" style="margin-top:6px">${T(`AUC means: pick one firm that was later debarred and one that was not. The AI
      ranks the debarred one higher ${pctTxt(a.roc_auc)} of the time. A coin flip scores 50%.`,
      `AUC মানে: পরে নিষিদ্ধ হওয়া একটি এবং নিষিদ্ধ না হওয়া একটি প্রতিষ্ঠান নিলে, এআই ${pctTxt(a.roc_auc)} ক্ষেত্রে নিষিদ্ধটিকে উপরে রাখে। টস করলে ৫০% হয়।`)}</p>

    <h2>${T("If You Check the AI's Top List", 'এআই-এর শীর্ষ তালিকা যাচাই করলে')}</h2>
    <table><tr><th>${T('Firms checked', 'যাচাই করা প্রতিষ্ঠান')}</th><th class="num">${T('Share of all later-debarred firms found', 'পরে নিষিদ্ধ হওয়াদের কত অংশ পাওয়া গেল')}</th>
      <th class="num">${T('Times more likely than average', 'গড়ের চেয়ে কত গুণ বেশি')}</th><th class="num">${T('Later debarred, per 100 checked', 'প্রতি ১০০টিতে পরে নিষিদ্ধ')}</th></tr>
      ${tops.map(([l, t]) => `<tr><td>${l}</td><td class="num">${pctTxt(t.recall)}</td>
        <td class="num">${f2(t.lift, 1)}×</td><td class="num">${f2(t.precision * 100, 1)}</td></tr>`).join('')}</table>
    <p class="muted" style="margin-top:6px">${T(`Debarment is rare (${(a.base_rate * 100).toFixed(2)}% of firms in 2 years), so even a
      good list contains mostly firms that will not be debarred. That is why every flag needs a human check.`,
      `নিষেধাজ্ঞা বিরল (২ বছরে ${f2(a.base_rate * 100, 2)}% প্রতিষ্ঠান), তাই ভালো তালিকাতেও বেশিরভাগ প্রতিষ্ঠান নিষিদ্ধ হবে না। এজন্যই প্রতিটি সংকেত মানুষের যাচাই দরকার।`)}</p>

    <h2>${T('Compared With a Simple Rule', 'একটি সহজ নিয়মের সঙ্গে তুলনা')}</h2>
    <p>${T('A simple rule, “firms that win more contracts are riskier”, is surprisingly strong. We compare against it honestly:',
      'একটি সহজ নিয়ম — “যারা বেশি কাজ পায় তারা বেশি ঝুঁকিপূর্ণ” — আশ্চর্যজনকভাবে শক্তিশালী। আমরা সৎভাবে এর সঙ্গে তুলনা করি:')}</p>
    <table><tr><th>${T('Test', 'পরীক্ষা')}</th><th class="num">${T('AI', 'এআই')}</th><th class="num">${T('Size rule', 'আকারের নিয়ম')}</th></tr>
      <tr><td>${T('Main test: ranking score (AUC)', 'প্রধান পরীক্ষা: সাজানোর স্কোর (AUC)')}</td><td class="num"><b>${f2(a.roc_auc, 3)}</b></td><td class="num">${f2(a.size_only_baseline.roc_auc, 3)}</td></tr>
      <tr><td>${T('Main test: ranking among firms of similar size', 'প্রধান পরীক্ষা: একই আকারের প্রতিষ্ঠানের মধ্যে সাজানো')}</td><td class="num"><b>${f2(a.auc_within_size_deciles, 3)}</b></td><td class="num">${f2(a.size_only_baseline.auc_within_size_deciles, 3)}</td></tr>
      <tr><td>${T('Earlier period (July 2020 – July 2021): AUC', 'আগের সময় (জুলাই ২০২০ – জুলাই ২০২১): AUC')}</td><td class="num">${f2(b.roc_auc, 3)}</td><td class="num"><b>${f2(b.size_only_baseline.roc_auc, 3)}</b></td></tr>
      <tr><td>${T('Earlier period: firms caught early', 'আগের সময়: আগেই ধরা পড়েছে')}</td><td class="num">${T(`${pctTxt(b.caught_in_advance.share)}, ~${Math.round(b.caught_in_advance.median_months_before_ban)} months ahead`,
        `${pctTxt(b.caught_in_advance.share)}, প্রায় ${dig(Math.round(b.caught_in_advance.median_months_before_ban))} মাস আগে`)}</td><td class="num">—</td></tr>
    </table>
    <p style="margin-top:8px">${T(`What this means: much of the AI's power comes from size. Its extra value is in telling apart
      <b>firms of similar size</b>, which the size rule cannot do. In the earlier period the AI was no better than the
      size rule overall. We show that openly.`, `এর মানে: এআই-এর শক্তির বড় অংশ আসে আকার থেকে। এর বাড়তি মূল্য হলো <b>একই আকারের প্রতিষ্ঠানগুলোকে
      আলাদা করা</b>, যা আকারের নিয়ম পারে না। আগের সময়ে সামগ্রিকভাবে এআই আকারের নিয়মের চেয়ে ভালো ছিল না। আমরা তা খোলাখুলি দেখাই।`)}</p>

    <h2>${T('Main Test, Date by Date', 'প্রধান পরীক্ষা, তারিখ অনুযায়ী')}</h2>
    <table><tr><th>${T('Test date', 'পরীক্ষার তারিখ')}</th><th class="num">AUC</th></tr>
      ${snap.map(([d, v]) => `<tr><td>${date(d)}</td><td class="num">${f2(v, 3)}</td></tr>`).join('')}</table>

    <h2>${T('Signals the AI Weighs Most', 'এআই যেসব সংকেতকে সবচেয়ে বেশি গুরুত্ব দেয়')}</h2>
    <ul class="plain">${w.slice(0, 10).map(([k, v]) => `<li>${esc(T(k[0].toUpperCase() + k.slice(1), WEIGHT_BN[k] || k))}:
      <b class="${v > 0 ? 'up' : 'down'}">${v > 0 ? `${ICON.up} ${T('higher means more risk', 'বেশি হলে ঝুঁকি বেশি')}` : `${ICON.down} ${T('higher means less risk', 'বেশি হলে ঝুঁকি কম')}`}</b></li>`).join('')}</ul>
    <p class="muted" style="margin-top:6px">${T('Signals overlap (for example, total value and number of contracts), so a single weight should not be read on its own.',
      'সংকেতগুলো একে অপরের সঙ্গে জড়িত (যেমন মোট মূল্য ও চুক্তির সংখ্যা), তাই একটি গুরুত্বকে আলাদাভাবে পড়া ঠিক নয়।')}</p>

    ${de ? `<h2>${T('What We Tried That Did Not Work', 'যা চেষ্টা করেও কাজে লাগেনি')}</h2>
    <p>${T(`We downloaded about 28,000 contract detail pages to test bidding signals: how many firms bid, contracts with only one
      bidder, late signing, late performance security, aid funding, and addresses shared with banned firms. On the same
      firms and test dates, adding them changed the AUC from ${de.base_auc.toFixed(3)} to ${de.detail_auc.toFixed(3)}, so
      <b>no improvement</b>. Debarred firms had single-bidder contracts about as often as other firms. We kept these
      facts on company pages but left them out of the score.`,
      `দরপত্রের সংকেত পরীক্ষার জন্য প্রায় ২৮,০০০ চুক্তির বিস্তারিত পাতা নামানো হয়েছিল: কতজন দরপত্র দেয়, একক দরদাতার চুক্তি,
      দেরিতে সই, দেরিতে জামানত, বিদেশি সাহায্য, এবং নিষিদ্ধ প্রতিষ্ঠানের সঙ্গে একই ঠিকানা। একই প্রতিষ্ঠান ও তারিখে এগুলো যোগ করলে
      AUC ${f2(de.base_auc, 3)} থেকে ${f2(de.detail_auc, 3)} হয়, অর্থাৎ <b>কোনো উন্নতি নেই</b>। নিষিদ্ধ প্রতিষ্ঠানগুলোর একক-দরদাতার চুক্তি
      অন্যদের মতোই ছিল। তথ্যগুলো প্রতিষ্ঠানের পাতায় রাখা হয়েছে, কিন্তু স্কোরে নয়।`)}</p>
    <p>${T('One early version seemed to improve accuracy. We found it was “peeking at the future” through the way pages were sampled, removed it, and the gain disappeared.',
      'প্রথম দিকের একটি সংস্করণে নির্ভুলতা বেড়েছে মনে হয়েছিল। পরে দেখা গেল পাতা বাছাইয়ের ধরনের কারণে সেটি “ভবিষ্যৎ দেখে ফেলছিল”; তা সরানোর পর বাড়তি লাভ চলে যায়।')}</p>` : ''}

    <h2>${T('Limits You Should Know', 'যে সীমাবদ্ধতাগুলো জানা দরকার')}</h2>
    <ul class="plain">
      <li>${T('The AI learns from <b>past debarments</b>. Firms that broke rules but were never debarred look “normal” to it.',
        'এআই <b>অতীতের নিষেধাজ্ঞা</b> থেকে শেখে। যারা নিয়ম ভেঙেছে কিন্তু নিষিদ্ধ হয়নি, তাদের এটি “স্বাভাবিক” মনে করে।')}</li>
      <li>${T('Some agencies debar firms more often than others, for example local-government engineering (LGED). The AI partly learns <b>where enforcement happens</b>, not only where problems happen.',
        'কিছু সংস্থা অন্যদের চেয়ে বেশি নিষিদ্ধ করে, যেমন এলজিইডি। তাই এআই আংশিকভাবে শেখে <b>কোথায় ব্যবস্থা নেওয়া হয়</b>, শুধু কোথায় সমস্যা হয় তা নয়।')}</li>
      <li>${T('Company names are matched by spelling within each division; different firms can share a name.',
        'প্রতিটি বিভাগে প্রতিষ্ঠানের নাম বানান দিয়ে মেলানো হয়; একই নামে আলাদা প্রতিষ্ঠান থাকতে পারে।')}</li>
      <li>${T('Scores rank firms for review. They never decide anything about a firm.', 'স্কোর শুধু যাচাইয়ের ক্রম ঠিক করে। কোনো প্রতিষ্ঠান সম্পর্কে সিদ্ধান্ত দেয় না।')}</li>
    </ul>`;
}

async function office(name) {
  const r = await api(`/api/office?name=${encodeURIComponent(name)}`);
  const o = r.office;
  const top = r.winners[0];
  const warn = o.top_share_n >= 0.4 && o.n_contracts >= 20
    ? `<ul class="flags"><li class="medium"><span class="lvl">${T('Review:', 'যাচাই করুন:')}</span>${T(`One company — ${esc(top?.name)} — won ${pct(o.top_share_n)} of this office's contracts.`,
      `এই অফিসের চুক্তির ${pct(o.top_share_n)} একটি প্রতিষ্ঠান — ${esc(top?.name)} — পেয়েছে।`)}</li></ul>` : '';
  view.innerHTML = `
    <h1>${esc(o.procuring_entity)}</h1>
    ${facts([
      [T('Ministry', 'মন্ত্রণালয়'), esc(o.ministry)],
      [T('District', 'জেলা'), esc(place(o.district))],
      [T('Contracts awarded', 'দেওয়া চুক্তি'), num(o.n_contracts)],
      [T('Total value', 'মোট মূল্য'), taka(o.value_bdt)],
      [T('Different winning companies', 'আলাদা বিজয়ী প্রতিষ্ঠান'), num(o.n_winners)],
    ])}
    <p class="actions">${signupBtn('alerts', T('Get alerts for new contracts here', 'এই অফিসের নতুন চুক্তির খবর পান'), o.procuring_entity)}</p>
    ${warn}
    <h2>${T('Who Wins Here', 'এখানে কে কাজ পায়')}</h2>
    <table><tr><th>${T('Company', 'প্রতিষ্ঠান')}</th><th class="num">${T('Contracts', 'চুক্তি')}</th><th class="num">${T('Value', 'মূল্য')}</th><th>${T('Share', 'অংশ')}</th></tr>
      ${r.winners.map(w => `<tr><td>${companyLink(w.key, w.name)}${debTag(w.n_debarments)}</td>
        <td class="num">${num(w.n)}</td><td class="num">${taka(w.value_bdt)}</td><td>${shareBar(w.share_n)}</td></tr>`).join('')}</table>
    <h2>${T('Recent Contracts', 'সাম্প্রতিক চুক্তি')}</h2>
    <table><tr><th>${T('Signed', 'সইয়ের তারিখ')}</th><th>${T('Work', 'কাজ')}</th><th>${T('Winner', 'বিজয়ী')}</th><th>${T('Method', 'পদ্ধতি')}</th><th class="num">${T('Value', 'মূল্য')}</th></tr>
      ${r.recent.map(x => `<tr><td>${date(x.signed_date)}</td><td class="title">${esc(x.title)}</td>
        <td>${companyLink(x.winner_key, x.winner)}</td><td>${esc(x.method)}</td><td class="num">${taka(x.value_bdt)}</td></tr>`).join('')}</table>`;
}

async function patterns() {
  const rows = await api('/api/patterns');
  view.innerHTML = `
    <h1>${T('Offices Where One Company Wins Most Contracts', 'যে অফিসে একটি প্রতিষ্ঠান বেশিরভাগ কাজ পায়')}</h1>
    <p>${T('Offices with 30 or more contracts where a single company won at least 40%. A high share can have innocent reasons — it is a signal to look closer, not proof.',
      '৩০ বা তার বেশি চুক্তি হয়েছে এমন অফিস, যেখানে একটি প্রতিষ্ঠান অন্তত ৪০% কাজ পেয়েছে। বেশি অংশ পাওয়ার নির্দোষ কারণ থাকতে পারে — এটি খতিয়ে দেখার সংকেত, প্রমাণ নয়।')}
      ${bnNote('একটি প্রতিষ্ঠান বেশিরভাগ কাজ পাচ্ছে — যাচাই করা দরকার।')}</p>
    <table><tr><th>${T('Office', 'অফিস')}</th><th class="hide-sm">${T('District', 'জেলা')}</th><th>${T('Top winner', 'শীর্ষ বিজয়ী')}</th><th class="num">${T('Contracts', 'চুক্তি')}</th><th>${T("Top winner's share", 'শীর্ষ বিজয়ীর অংশ')}</th></tr>
      ${rows.map(r => `<tr><td>${officeLink(r.office)}</td><td class="hide-sm">${esc(place(r.district))}</td>
        <td>${companyLink(r.winner_key, r.winner)}${debTag(r.n_debarments)}</td>
        <td class="num">${num(r.n_contracts)}</td><td>${shareBar(r.top_share_n)}</td></tr>`).join('')}</table>`;
}

async function debarred() {
  const rows = await api('/api/debarred');
  view.innerHTML = `
    <h1>${T('Debarred Firms Found Among Contract Winners', 'কাজ পাওয়াদের মধ্যে নিষিদ্ধ প্রতিষ্ঠান')}</h1>
    <p>${T('Companies on the government\'s own e-GP debarment list that also appear as contract winners. Debarment is an official government decision.',
      'সরকারের নিজস্ব ই-জিপি নিষিদ্ধ তালিকায় থাকা যেসব প্রতিষ্ঠান চুক্তিও পেয়েছে। নিষেধাজ্ঞা একটি সরকারি সিদ্ধান্ত।')}
      <span class="important">${T('Names are matched by spelling', 'নাম বানান দিয়ে মেলানো হয়')}</span> —
      ${T('where a name appears in many districts it may belong to several firms.', 'কোনো নাম অনেক জেলায় থাকলে তা একাধিক প্রতিষ্ঠানের হতে পারে।')}</p>
    <table><tr><th>${T('Company', 'প্রতিষ্ঠান')}</th><th class="num">${T('Contracts', 'চুক্তি')}</th><th class="num">${T('Value', 'মূল্য')}</th><th>${T('Debarred', 'নিষিদ্ধ')}</th><th class="hide-sm">${T('By', 'যে সংস্থা')}</th></tr>
      ${rows.map(r => `<tr><td>${companyLink(r.key, r.name)}${r.name_may_be_shared ? ` <span class="muted">${T(`(name in ${r.n_districts} districts)`, `(${dig(r.n_districts)}টি জেলায় এই নাম)`)}</span>` : ''}</td>
        <td class="num">${num(r.n_contracts)}</td><td class="num">${taka(r.value_bdt)}</td>
        <td>${date(r.first_debar_from)} – ${date(r.last_debar_to)}</td>
        <td class="hide-sm">${esc((r.debarred_by || '').split(',')[0])}</td></tr>`).join('')}</table>`;
}

async function largest() {
  const rows = await api('/api/largest');
  view.innerHTML = `
    <h1>${T('Largest Contracts', 'সবচেয়ে বড় চুক্তি')}</h1>
    <table><tr><th>${T('Signed', 'সইয়ের তারিখ')}</th><th>${T('Work', 'কাজ')}</th><th>${T('Winner', 'বিজয়ী')}</th><th class="hide-sm">${T('Office', 'অফিস')}</th><th class="num">${T('Value', 'মূল্য')}</th><th></th></tr>
      ${rows.map(x => `<tr><td>${date(x.signed_date)}</td><td class="title">${esc(x.title)}</td>
        <td>${companyLink(x.winner_key, x.winner)}</td><td class="hide-sm">${officeLink(x.procuring_entity)}</td>
        <td class="num">${taka(x.value_bdt)}</td><td>${egpLink(x.tender_id, x.pkg_lot_id)}</td></tr>`).join('')}</table>`;
}

function about() {
  view.innerHTML = `
    <h1>${T('How Prohori Works', 'প্রহরী কীভাবে কাজ করে')}</h1>
    <p>${T(`By law, every government office publishes its tenders and contract awards on the national e-GP portal
      (eprocure.gov.bd). There are almost 9 lakh of them — too many for anyone to check by hand.
      Prohori collects these public records automatically and checks them for patterns.`,
      `আইন অনুযায়ী প্রতিটি সরকারি অফিস তাদের দরপত্র ও চুক্তি জাতীয় ই-জিপি পোর্টালে (eprocure.gov.bd) প্রকাশ করে। এমন চুক্তি প্রায় ৯ লাখ —
      হাতে হাতে যাচাই করা অসম্ভব। প্রহরী এই প্রকাশ্য তথ্য স্বয়ংক্রিয়ভাবে সংগ্রহ করে এবং সংকেত খোঁজে।`)}</p>
    <h2 id="sec-flags">${T('How to Read a Risk Flag', 'ঝুঁকির সংকেত কীভাবে পড়বেন')}</h2>
    <ul class="flags">
      <li class="high"><span class="lvl">${T('High:', 'গুরুতর:')}</span>${T('An official government decision, such as a debarment.', 'সরকারি সিদ্ধান্ত, যেমন নিষেধাজ্ঞা।')}</li>
      <li class="medium"><span class="lvl">${T('Review:', 'যাচাই করুন:')}</span>${T('An unusual pattern, such as one company winning most contracts at an office, or many contracts given without open competition.',
        'অস্বাভাবিক ধরন, যেমন একটি অফিসের বেশিরভাগ কাজ একটি প্রতিষ্ঠানের পাওয়া, বা অনেক কাজ উন্মুক্ত প্রতিযোগিতা ছাড়া দেওয়া।')}</li>
      <li class="info"><span class="lvl">${T('Note:', 'লক্ষ করুন:')}</span>${T('Something to keep in mind, such as a company name used by several different firms.',
        'মনে রাখার মতো বিষয়, যেমন একই নাম কয়েকটি আলাদা প্রতিষ্ঠানের।')}</li>
    </ul>
    <h2>${T('The AI Review Priority', 'এআই যাচাই-অগ্রাধিকার')}</h2>
    <p>${T(`Besides the simple rules above, an AI model ranks every active firm by how much its contract history looks like
      the histories of firms that were later debarred. It uses 35 signals, such as growth, the number of offices and
      districts, buying methods, and types of work. Each company page shows its rank and the main reasons in plain words.
      The model was tested on past data it had never seen.`, `উপরের সহজ নিয়মের পাশাপাশি একটি এআই মডেল প্রতিটি সক্রিয় প্রতিষ্ঠানকে সাজায় —
      কার চুক্তির ইতিহাস পরে নিষিদ্ধ হওয়া প্রতিষ্ঠানগুলোর সঙ্গে কতটা মেলে। এটি ৩৫টি সংকেত ব্যবহার করে, যেমন বৃদ্ধি, অফিস ও জেলার সংখ্যা,
      ক্রয় পদ্ধতি ও কাজের ধরন। প্রতিটি প্রতিষ্ঠানের পাতায় তার অবস্থান ও প্রধান কারণ সহজ ভাষায় দেখানো হয়।
      মডেলটি এমন অতীত তথ্যে পরীক্ষা করা হয়েছে যা এটি আগে দেখেনি।`)} <a href="#/model">${T('See the full test results', 'পরীক্ষার পূর্ণ ফলাফল দেখুন')}</a>.</p>
    <ul class="plain">
      <li><span class="pill very_high">${T('Very high', 'খুব বেশি')}</span> ${T('top 1%', 'শীর্ষ ১%')} · <span class="pill high">${T('High', 'বেশি')}</span> ${T('top 5%', 'শীর্ষ ৫%')} ·
        <span class="pill elevated">${T('Elevated', 'কিছুটা বেশি')}</span> ${T('top 15%', 'শীর্ষ ১৫%')} · <span class="pill typical">${T('Typical', 'সাধারণ')}</span> ${T('the rest', 'বাকি সব')}</li>
    </ul>
    <h2>${T('If You Think a Flag Is Wrong', 'কোনো সংকেত ভুল মনে হলে')}</h2>
    <ul class="plain">
      <li>${T('Every number links back to the original public record on e-GP, so anyone can check it.', 'প্রতিটি সংখ্যা ই-জিপির মূল প্রকাশ্য নথির সঙ্গে যুক্ত, তাই যে কেউ যাচাই করতে পারেন।')}</li>
      <li>${T('Common innocent reasons: a firm is large, works in a remote area with few contractors, or does specialised work.', 'সাধারণ নির্দোষ কারণ: প্রতিষ্ঠানটি বড়, ঠিকাদার কম এমন দূরের এলাকায় কাজ করে, বা বিশেষ ধরনের কাজ করে।')}</li>
      <li>${T('Firms and offices can ask for a correction or add an explanation. Corrections to the data are applied and shown on the page.', 'প্রতিষ্ঠান ও অফিস সংশোধন চাইতে বা ব্যাখ্যা যোগ করতে পারে। তথ্যের সংশোধন করা হয় এবং পাতায় দেখানো হয়।')}</li>
    </ul>
    <h2>${T('What Prohori Does Not Do', 'প্রহরী যা করে না')}</h2>
    <ul class="plain">
      <li>${T('It does not call anyone corrupt. Flags are signals for review; a human — an auditor, bank officer or journalist — always decides.', 'কাউকে দুর্নীতিবাজ বলে না। সংকেত শুধু যাচাইয়ের জন্য; সিদ্ধান্ত সবসময় মানুষ নেন — নিরীক্ষক, ব্যাংক কর্মকর্তা বা সাংবাদিক।')}</li>
      <li>${T('It does not use any private data. Everything comes from public government records.', 'কোনো ব্যক্তিগত তথ্য ব্যবহার করে না। সবকিছু সরকারের প্রকাশ্য নথি থেকে।')}</li>
    </ul>`;
}

// ---------- Usage counter (no cookies, no IP stored) + waitlist sign-ups ----------
const VID = store.get('pvid') || (() => { const v = Math.random().toString(36).slice(2, 14); store.set('pvid', v); return v; })();
const TZ = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) { return ''; } })();
const ABROAD = !!TZ && TZ !== 'Asia/Dhaka';   // browser time zone outside Bangladesh
// Price test for Contractor Pro: each visitor always sees the same one of two planned prices.
const PRICE = store.get('pv') || (() => { const v = Math.random() < 0.5 ? '6000' : '9000'; store.set('pv', v); return v; })();
function trackEvent(event, page = '') {
  fetch('/api/track', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event, page, vid: VID, abroad: ABROAD }), keepalive: true }).catch(() => {});
}

const PLAN_INFO = {
  pro: { en: 'Contractor Pro — join the waitlist', bn: 'কন্ট্রাক্টর প্রো — অপেক্ষার তালিকায় যোগ দিন', role: 'contractor' },
  lender: { en: 'Lender Check — request Contractor Check Reports', bn: 'লেন্ডার চেক — ঠিকাদার যাচাই রিপোর্টের অনুরোধ', role: 'bank' },
  institution: { en: 'Institution licence — register interest', bn: 'প্রতিষ্ঠানের লাইসেন্স — আগ্রহ জানান', role: 'ngo' },
  digest: { en: 'Free district digest (English / Bangla)', bn: 'বিনামূল্যে জেলার মাসিক সারাংশ (বাংলা / ইংরেজি)', role: 'nrb' },
  alerts: { en: 'Get alerts for new contracts at this office', bn: 'এই অফিসের নতুন চুক্তির খবর পান', role: 'contractor' },
  notify: { en: 'Notify me when this company wins a new contract', bn: 'এই প্রতিষ্ঠান নতুন কাজ পেলে জানান', role: 'journalist' },
};
const ROLES = [['contractor', 'Contractor / supplier', 'ঠিকাদার / সরবরাহকারী'], ['bank', 'Bank or finance company', 'ব্যাংক বা আর্থিক প্রতিষ্ঠান'],
  ['journalist', 'Journalist', 'সাংবাদিক'], ['nrb', 'Bangladeshi living abroad', 'প্রবাসী বাংলাদেশি'], ['citizen', 'Citizen', 'নাগরিক'],
  ['student', 'Student / researcher', 'শিক্ষার্থী / গবেষক'], ['government', 'Government / audit', 'সরকারি / নিরীক্ষা'],
  ['ngo', 'NGO / donor project', 'এনজিও / দাতা প্রকল্প'], ['other', 'Other', 'অন্যান্য']];
const roleName = r => { const x = ROLES.find(y => y[0] === r); return x ? T(x[1], x[2]) : r; };

function openSignup(plan, target = '') {
  const info = PLAN_INFO[plan];
  const title = T(info.en, info.bn);
  trackEvent('signup_open', plan === 'pro' ? `pro_${PRICE}` : plan);
  document.getElementById('signup')?.remove();
  document.body.insertAdjacentHTML('beforeend', `
    <div class="modal" id="signup" role="dialog" aria-label="${esc(title)}">
      <form class="modal-box" id="signup-form">
        <div class="modal-head"><b>${esc(title)}</b>
          <button type="button" class="aiclose" data-close aria-label="${T('Close', 'বন্ধ')}">${AI_ICON.close}</button></div>
        ${target ? `<p class="muted">${T('For:', 'যার জন্য:')} <b>${esc(target)}</b></p>` : ''}
        ${plan === 'pro' ? `<p>${T(`Planned price: <b>Tk ${num(+PRICE)} a year</b> (about Tk ${num(Math.round(PRICE / 10))} a month).`,
          `পরিকল্পিত দাম: <b>বছরে ${num(+PRICE)} টাকা</b> (মাসে প্রায় ${num(Math.round(PRICE / 10))} টাকা)।`)}</p>` : ''}
        <p class="notice">${T('Nothing is sold yet and no payment is taken. We will contact you once, when this is ready.',
          'এখনো কিছু বিক্রি হচ্ছে না, কোনো টাকা নেওয়া হচ্ছে না। প্রস্তুত হলে আমরা একবার যোগাযোগ করব।')}</p>
        <label>${T('I am a', 'আমি')}<select name="role">${ROLES.map(([v, en, bn]) => `<option value="${v}"${v === info.role ? ' selected' : ''}>${T(en, bn)}</option>`).join('')}</select></label>
        <label>${T('Email or mobile number', 'ইমেইল বা মোবাইল নম্বর')}<input name="contact" required maxlength="120" autocomplete="email" placeholder="you@example.com / 01XXXXXXXXX"></label>
        <label>${T('Name or organisation (optional)', 'নাম বা প্রতিষ্ঠান (ঐচ্ছিক)')}<input name="name" maxlength="80"></label>
        <label>${T('District, or country if abroad', 'জেলা, বা বিদেশে থাকলে দেশ')}<input name="place" maxlength="80" placeholder="${T('e.g. Natore / London', 'যেমন: নাটোর / লন্ডন')}"></label>
        <label class="check"><input type="checkbox" name="abroad"${ABROAD ? ' checked' : ''}> ${T('I live outside Bangladesh', 'আমি বাংলাদেশের বাইরে থাকি')}</label>
        <label>${T('Anything you want from Prohori? (optional)', 'প্রহরী থেকে কী চান? (ঐচ্ছিক)')}<textarea name="note" maxlength="500" rows="2"></textarea></label>
        <p class="aierr" id="signup-err" hidden></p>
        <button class="btn-main">${T('Join', 'যোগ দিন')}</button>
        <p class="muted small">${T('We store only what you type here, to tell you when it is ready. We never share or sell it.',
          'আপনি যা লিখবেন শুধু তা-ই রাখা হয়, প্রস্তুত হলে জানানোর জন্য। আমরা কখনো তা শেয়ার বা বিক্রি করি না।')}</p>
      </form>
    </div>`);
  const box = document.getElementById('signup'), f = document.getElementById('signup-form');
  const close = () => box.remove();
  box.addEventListener('click', e => { if (e.target === box || e.target.closest('[data-close]')) close(); });
  f.addEventListener('submit', async e => {
    e.preventDefault();
    const err = document.getElementById('signup-err');
    err.hidden = true;
    try {
      const r = await aiFetch('/api/signup', { plan, target, role: f.role.value, contact: f.contact.value.trim(),
        name: f.name.value, place: f.place.value, abroad: f.abroad.checked, note: f.note.value,
        price_variant: plan === 'pro' ? PRICE : '' });
      f.innerHTML = `<div class="modal-head"><b>${T('Thank you.', 'ধন্যবাদ!')}</b><button type="button" class="aiclose" data-close aria-label="${T('Close', 'বন্ধ')}">${AI_ICON.close}</button></div>
        <p>${r.already ? T('You were already on this list.', 'আপনি আগে থেকেই এই তালিকায় আছেন।') : T('You are on the list.', 'আপনি তালিকায় যুক্ত হয়েছেন।')}
        ${T('We will contact you once, when it is ready.', 'প্রস্তুত হলে আমরা একবার জানাব।')}</p>`;
    } catch (x) {
      err.textContent = LANG === 'bn' && /valid email/.test(x.message) ? 'সঠিক ইমেইল বা মোবাইল নম্বর দিন।' : x.message;
      err.hidden = false;
    }
  });
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-signup]');
  if (b) { e.preventDefault(); openSignup(b.dataset.signup, b.dataset.target || ''); }
  const l = e.target.closest('#langToggle');
  if (l) { e.preventDefault(); setLang(LANG === 'bn' ? 'en' : 'bn'); }
});
const signupBtn = (plan, label, target = '') =>
  `<button type="button" class="btn-line" data-signup="${plan}" data-target="${esc(target)}">${label}</button>`;

// ---------- Plans ----------
function pricing() {
  const pro = +PRICE;
  view.innerHTML = `
    <h1>${T('Plans', 'প্ল্যান')}</h1>
    <p>${T(`Prohori is <b>free for citizens, journalists, students and Bangladeshis abroad</b>. Paid plans for businesses are
      coming soon. Join the waitlist and we will tell you when they open.`, `প্রহরী <b>নাগরিক, সাংবাদিক, শিক্ষার্থী ও প্রবাসীদের জন্য বিনামূল্যে</b>।
      ব্যবসার জন্য পেইড প্ল্যান শীঘ্রই আসছে। অপেক্ষার তালিকায় যোগ দিন, চালু হলে জানাব।`)}</p>
    <table class="plans">
      <tr><th>${T('Plan', 'প্ল্যান')}</th><th>${T('For', 'যাদের জন্য')}</th><th>${T('What you get', 'যা পাবেন')}</th><th class="num">${T('Price', 'দাম')}</th><th></th></tr>
      <tr><td><b>${T('Free', 'ফ্রি')}</b></td><td>${T('Citizens, journalists, students, Bangladeshis abroad', 'নাগরিক, সাংবাদিক, শিক্ষার্থী, প্রবাসী')}</td>
        <td>${T('Search every contract since 2011, company, office and district pages, risk signals with reasons, AI watchlist, Bangla/English AI assistant',
          '২০১১ থেকে সব চুক্তি খোঁজা, প্রতিষ্ঠান-অফিস-জেলার পাতা, কারণসহ ঝুঁকির সংকেত, এআই নজরতালিকা, বাংলা/ইংরেজি এআই সহকারী')}</td>
        <td class="num"><b>${T('Tk 0', '০ টাকা')}</b></td><td><a href="#/probashi">${T('Start', 'শুরু করুন')}</a></td></tr>
      <tr><td><b>${T('Contractor Pro', 'কন্ট্রাক্টর প্রো')}</b></td><td>${T('Contractors and suppliers', 'ঠিকাদার ও সরবরাহকারী')}</td>
        <td>${T('Alerts for chosen offices and districts, winner and price history per office, competitor history, check and reply to your own profile',
          'পছন্দের অফিস ও জেলার নতুন কাজের খবর, প্রতিটি অফিসে কে কত দামে জেতে, প্রতিযোগীর ইতিহাস, নিজের প্রোফাইল দেখা ও জবাব দেওয়া')}</td>
        <td class="num"><b>${T(`Tk ${num(pro)}/year`, `বছরে ${num(pro)} টাকা`)}</b></td><td>${signupBtn('pro', T('Join waitlist', 'অপেক্ষার তালিকায় যোগ দিন'))}</td></tr>
      <tr><td><b>${T('Lender Check', 'লেন্ডার চেক')}</b></td><td>${T('Banks and finance companies', 'ব্যাংক ও আর্থিক প্রতিষ্ঠান')}</td>
        <td>${T('Contractor Check Report before a work-order loan or bank guarantee.', 'কার্যাদেশ ঋণ বা ব্যাংক গ্যারান্টির আগে ঠিকাদার যাচাই রিপোর্ট।')}
          <a href="#/report/${encodeURIComponent(SAMPLE_REPORT)}">${T('See a sample', 'নমুনা দেখুন')}</a></td>
        <td class="num"><b>${T('Per report', 'প্রতি রিপোর্ট')}</b></td><td>${signupBtn('lender', T('Request access', 'অনুরোধ করুন'))}</td></tr>
      <tr><td><b>${T('Institution', 'প্রতিষ্ঠান')}</b></td><td>${T('Audit bodies, donor projects, NGOs, newsrooms', 'নিরীক্ষা সংস্থা, দাতা প্রকল্প, এনজিও, সংবাদমাধ্যম')}</td>
        <td>${T('Bulk watchlists, data exports, training', 'বড় পরিসরের নজরতালিকা, তথ্য ডাউনলোড, প্রশিক্ষণ')}</td>
        <td class="num"><b>${T('Contact us', 'যোগাযোগ করুন')}</b></td><td>${signupBtn('institution', T('Register interest', 'আগ্রহ জানান'))}</td></tr>
    </table>
    <p class="caveat"><b>${T('Paying never changes, hides or lowers a risk score.', 'টাকা দিয়ে কখনো ঝুঁকির মাত্রা বদলানো, লুকানো বা কমানো যায় না।')}</b>
      ${T('Every score comes from the same public data for everyone. Any firm can reply or ask for a correction for free.',
        'সবার জন্য একই প্রকাশ্য তথ্য থেকে স্কোর আসে। যেকোনো প্রতিষ্ঠান বিনামূল্যে জবাব দিতে বা সংশোধন চাইতে পারে।')}</p>`;
}

// ---------- Probashi: welcome page for Bangladeshis abroad ----------
function probashi() {
  const home = store.get('homeDistrict');
  view.innerHTML = `
    <h1>${T('Probashi: Prohori for Bangladeshis Abroad', 'প্রবাসী: প্রবাসী বাংলাদেশিদের জন্য প্রহরী')}</h1>
    <p class="lead">${T('Your remittance keeps the country running. See how public money is spent at home — from abroad.',
      'প্রবাসী ভাই-বোনেরা: আপনার পাঠানো রেমিট্যান্সে দেশ চলে। দেশের সরকারি টাকা কোথায় খরচ হচ্ছে — বিদেশ থেকেই দেখুন।')}</p>
    <p>${T(`Bangladeshis abroad sent home about <b>US$35.6 billion</b> in FY2025-26, a record. Many also fund schools, mosques, roads and
      family businesses at home. Prohori lets you follow public money at home from anywhere in the world, in English or Bangla.`,
      `২০২৫-২৬ অর্থবছরে প্রবাসীরা প্রায় <b>৩,৫৬০ কোটি মার্কিন ডলার</b> দেশে পাঠিয়েছেন — যা রেকর্ড। অনেকে গ্রামের স্কুল, মসজিদ, রাস্তা ও
      পারিবারিক ব্যবসায়ও টাকা দেন। প্রহরী দিয়ে বিশ্বের যেকোনো জায়গা থেকে বাংলা বা ইংরেজিতে দেশের সরকারি টাকার খবর রাখুন।`)}</p>
    <h2>${T('What You Can Do Here', 'এখানে যা করতে পারেন')}</h2>
    <ul class="choices">
      <li><a href="#/districts"><b>${T('My home district', 'আমার জেলা')}</b>
        <span>${home ? T(`Your district: ${esc(home)}. See what the government is building there.`, `আপনার জেলা: ${esc(place(home))}। সেখানে সরকার কী বানাচ্ছে দেখুন।`)
          : T('Pick your district once. See what the government is building there, who wins the contracts, and for how much.', 'একবার জেলা বেছে নিন। সেখানে সরকার কী বানাচ্ছে, কে কাজ পাচ্ছে, কত টাকায় — দেখুন।')}</span></a></li>
      <li><a href="#/check"><b>${T('Check a company', 'প্রতিষ্ঠান যাচাই')}</b>
        <span>${T('Before you send money to, invest in or lend to a firm at home, check its government record.', 'দেশে কোনো প্রতিষ্ঠানে টাকা পাঠানো, বিনিয়োগ বা ঋণ দেওয়ার আগে তার সরকারি রেকর্ড দেখুন।')}</span></a></li>
      <li><a href="#" data-signup="digest" data-target="${esc(home || '')}"><b>${T('Free monthly digest', 'বিনামূল্যে মাসিক সারাংশ')}</b>
        <span>${T('A short English or Bangla summary of new contracts in your district, by email, once a month.', 'আপনার জেলার নতুন চুক্তির ছোট সারাংশ, বাংলা বা ইংরেজিতে, মাসে একবার ইমেইলে।')}</span></a></li>
      <li><a target="_blank" rel="noopener" href="https://github.com/Eusha122/Prohori"><b>${T('Help build Prohori', 'প্রহরী গড়ায় অংশ নিন')}</b>
        <span>${T('Engineers, data scientists and journalists abroad: improve maps, translate, test the AI. Open source.', 'বিদেশে থাকা প্রকৌশলী, ডেটা বিজ্ঞানী ও সাংবাদিকেরা: মানচিত্র উন্নত করুন, অনুবাদ করুন, এআই পরীক্ষা করুন। ওপেন সোর্স।')}</span></a></li>
    </ul>
    <p class="muted">${T('Tip: ask the AI assistant (bottom right) in English or Bangla.', 'পরামর্শ: নিচে ডান কোণের এআই সহকারীকে বাংলা বা ইংরেজিতে প্রশ্ন করুন।')}</p>`;
}

// ---------- My home district: pick once, remembered in this browser ----------
async function districtsPage() {
  const ds = await api('/api/districts');
  const home = store.get('homeDistrict');
  const byDiv = {};
  ds.forEach(d => (byDiv[d.division || 'Other'] ||= []).push(d));
  view.innerHTML = `
    <h1>${T('My Home District', 'আমার জেলা')}</h1>
    ${home ? `<p class="caveat">${T('Your home district:', 'আপনার জেলা:')} <b>${esc(place(home))}</b> · <a href="#/district/${encodeURIComponent(home)}">${T(`Open ${esc(home)}`, `${esc(place(home))} দেখুন`)} ${ICON.more}</a>
      <span class="small muted">${T('(remembered in this browser only)', '(শুধু এই ব্রাউজারে মনে রাখা হয়েছে)')}</span></p>`
      : `<p>${T('Pick your district. We will remember it in this browser, so next time you can open it in one click.', 'আপনার জেলা বেছে নিন। এই ব্রাউজারে মনে রাখা হবে, পরের বার এক ক্লিকেই খুলবে।')}</p>`}
    <form class="inline-search" onsubmit="return false"><input id="dfilter" placeholder="${T('Type to find your district, e.g. Sylhet', 'জেলার নাম লিখে খুঁজুন, যেমন: সিলেট')}" autocomplete="off"></form>
    <div class="districts" id="dlist">${Object.keys(byDiv).sort().map(div => `
      <div data-div><h3>${esc(place(div))}</h3><ul class="plain">${byDiv[div].map(d => `<li data-name="${esc(`${d.district} ${PLACE_BN[d.district] || ''}`.toLowerCase())}">
        <a href="#/district/${encodeURIComponent(d.district)}" data-home="${esc(d.district)}">${esc(place(d.district))}</a>
        <span class="muted">${T(`${num(d.n_12m)} contracts last year`, `গত বছর ${num(d.n_12m)}টি চুক্তি`)}</span></li>`).join('')}</ul></div>`).join('')}</div>`;
  const f = document.getElementById('dfilter');
  f.addEventListener('input', () => {
    const q = f.value.trim().toLowerCase();
    document.querySelectorAll('#dlist li').forEach(li => { li.hidden = q && !li.dataset.name.includes(q); });
    document.querySelectorAll('#dlist [data-div]').forEach(g => { g.hidden = !g.querySelector('li:not([hidden])'); });
  });
  document.getElementById('dlist').addEventListener('click', e => {
    const a = e.target.closest('[data-home]');
    if (a) store.set('homeDistrict', a.dataset.home);
  });
  if (window.innerWidth > 760) f.focus();
}

async function districtPage(name) {
  const d = await api(`/api/district?name=${encodeURIComponent(name)}`);
  const s = d.summary;
  const dn = esc(place(d.district));
  view.innerHTML = `
    <h1>${T(`${dn} District: What Is Being Built`, `${dn} জেলা: কী তৈরি হচ্ছে`)}</h1>
    ${bnNote(`${esc(PLACE_BN[d.district] || d.district)} জেলায় সরকারি কাজ: কে পাচ্ছে, কত টাকায়।`)}
    ${facts([
      [T('Division', 'বিভাগ'), esc(place(d.division))],
      [T('Government contracts', 'সরকারি চুক্তি'), `${num(s.n)} (${date(s.first_date)} – ${date(s.last_date)})`],
      [T('Total value', 'মোট মূল্য'), taka(s.value_bdt)],
      [T('Last 12 months', 'গত ১২ মাস'), `${contracts(s.n_12m)} · ${taka(s.value_12m)}`],
      [T('Government buying offices', 'সরকারি ক্রয়কারী অফিস'), num(s.offices)],
      [T('Different winning companies', 'আলাদা বিজয়ী প্রতিষ্ঠান'), num(s.winners)],
    ])}
    <p class="actions">${signupBtn('digest', T(`Get a free monthly digest for ${dn}`, `${dn} জেলার বিনামূল্যে মাসিক সারাংশ পান`), d.district)}
      <button type="button" class="btn-line" data-saved="${T('Saved as my home district', 'আমার জেলা হিসেবে রাখা হয়েছে')}" onclick="store.set('homeDistrict', ${esc(JSON.stringify(d.district))}); this.textContent = this.dataset.saved">${T('Set as my home district', 'আমার জেলা হিসেবে রাখুন')}</button></p>
    <h2>${T('Money Spent per Year', 'বছরভিত্তিক খরচ')}</h2>${yearList(d.by_year)}
    <h2>${T('Biggest Contracts in the Last 3 Years', 'গত ৩ বছরের সবচেয়ে বড় চুক্তি')}</h2>
    <table><tr><th>${T('Signed', 'সইয়ের তারিখ')}</th><th>${T('Work', 'কাজ')}</th><th>${T('Winner', 'বিজয়ী')}</th><th class="hide-sm">${T('Office', 'অফিস')}</th><th class="num">${T('Value', 'মূল্য')}</th><th></th></tr>
      ${d.biggest.map(x => `<tr><td>${date(x.signed_date)}</td><td class="title">${esc(x.title)}</td><td>${companyLink(x.winner_key, x.winner)}</td>
        <td class="hide-sm">${officeLink(x.procuring_entity)}</td><td class="num">${taka(x.value_bdt)}</td><td>${egpLink(x.tender_id, x.pkg_lot_id)}</td></tr>`).join('')}</table>
    <h2>${T('Who Wins Here', 'এখানে কে কাজ পায়')}</h2>
    <table><tr><th>${T('Company', 'প্রতিষ্ঠান')}</th><th class="num">${T('Contracts here', 'এখানে চুক্তি')}</th><th class="num">${T('Value here', 'এখানে মূল্য')}</th><th>${T('AI review priority', 'এআই যাচাই-অগ্রাধিকার')}</th></tr>
      ${d.winners.map(w => `<tr><td>${companyLink(w.key, w.name)}${debTag(w.n_debarments)}</td><td class="num">${num(w.n)}</td>
        <td class="num">${taka(w.value_bdt)}</td><td>${w.band ? bandPill(w) : '<span class="muted">—</span>'}</td></tr>`).join('')}</table>
    ${d.dominated.length ? `<h2>${T('Offices Where One Company Wins Most', 'যে অফিসে একটি প্রতিষ্ঠান বেশিরভাগ কাজ পায়')}</h2>
    <ul class="flags">${d.dominated.map(o => `<li class="medium"><span class="lvl">${T('Review:', 'যাচাই করুন:')}</span>${officeLink(o.name)} —
      ${companyLink(o.top_key, o.top_winner)} ${T(`won <b>${pct(o.top_share_n)}</b> of ${contracts(o.n_contracts)}`, `${contracts(o.n_contracts)}-এর মধ্যে <b>${pct(o.top_share_n)}</b> পেয়েছে`)}${debTag(o.n_debarments)}</li>`).join('')}</ul>` : ''}
    ${d.debarred.length ? `<h2>${T('Officially Debarred Firms That Won Work Here', 'এখানে কাজ পাওয়া সরকারিভাবে নিষিদ্ধ প্রতিষ্ঠান')}</h2>
    <table><tr><th>${T('Company', 'প্রতিষ্ঠান')}</th><th class="num">${T('Contracts here', 'এখানে চুক্তি')}</th><th class="num">${T('Value here', 'এখানে মূল্য')}</th><th>${T('Debarred', 'নিষিদ্ধ')}</th></tr>
      ${d.debarred.map(x => `<tr><td>${companyLink(x.key, x.name)}${x.name_may_be_shared ? ` <span class="muted">${T('(name used in many districts)', '(নামটি অনেক জেলায় আছে)')}</span>` : ''}</td>
        <td class="num">${num(x.n)}</td><td class="num">${taka(x.value_bdt)}</td><td>${date(x.first_debar_from)} – ${date(x.last_debar_to)}</td></tr>`).join('')}</table>` : ''}
    <h2>${T('Main Buying Offices', 'প্রধান ক্রয়কারী অফিস')}</h2>
    <table><tr><th>${T('Office', 'অফিস')}</th><th class="num">${T('Contracts', 'চুক্তি')}</th><th class="num">${T('Value', 'মূল্য')}</th><th>${T("Top winner's share", 'শীর্ষ বিজয়ীর অংশ')}</th></tr>
      ${d.offices.map(o => `<tr><td>${officeLink(o.name)}</td><td class="num">${num(o.n_contracts)}</td><td class="num">${taka(o.value_bdt)}</td>
        <td>${shareBar(o.top_share_n || 0)}</td></tr>`).join('')}</table>
    <h2>${T('Latest Contracts', 'সর্বশেষ চুক্তি')}</h2>
    <table><tr><th>${T('Signed', 'সইয়ের তারিখ')}</th><th>${T('Work', 'কাজ')}</th><th>${T('Winner', 'বিজয়ী')}</th><th class="num">${T('Value', 'মূল্য')}</th><th></th></tr>
      ${d.recent.map(x => `<tr><td>${date(x.signed_date)}</td><td class="title">${esc(x.title)}</td><td>${companyLink(x.winner_key, x.winner)}</td>
        <td class="num">${taka(x.value_bdt)}</td><td>${egpLink(x.tender_id, x.pkg_lot_id)}</td></tr>`).join('')}</table>
    <p class="caveat">${T('Flags are patterns for review, not accusations. Company names are matched by spelling; check the original record on e-GP.',
      'সংকেতগুলো যাচাইয়ের জন্য, অভিযোগ নয়। প্রতিষ্ঠানের নাম বানান দিয়ে মেলানো; ই-জিপিতে মূল নথি দেখে নিন।')}</p>`;
}

// ---------- Company check: before you give, invest or lend ----------
async function checkPage(q = '') {
  q = q.trim();
  const r = q.length >= 2 ? await api(`/api/search?q=${encodeURIComponent(q)}`) : null;
  if (r) trackEvent('search', 'check');
  const verdict = c => c.n_debarments
    ? `<b class="bad">${T('Yes — officially debarred', 'হ্যাঁ — সরকারিভাবে নিষিদ্ধ')}</b>`
    : `<b class="good">${T('No', 'না')}</b> <span class="muted">${T('(by name)', '(নাম অনুযায়ী)')}</span>`;
  const notes = c => [c.n_dominated_offices ? T("Wins 40%+ of an office's contracts", 'একটি অফিসের ৪০%+ কাজ পায়') : '',
    c.n_districts >= 9 ? T(`Name used in ${c.n_districts} districts — confirm the address`, `নামটি ${dig(c.n_districts)}টি জেলায় আছে — ঠিকানা মিলিয়ে নিন`) : '']
    .filter(Boolean).join('; ') || '—';
  view.innerHTML = `
    <h1>${T('Check a Company Before You Give or Invest', 'টাকা দেওয়া বা বিনিয়োগের আগে প্রতিষ্ঠান যাচাই করুন')}</h1>
    <p>${T(`Sending money to a contractor, a supplier or a family business at home? Type its name. You will see its government
      contract record, whether the government officially debarred it, and patterns worth a closer look.`,
      `দেশে কোনো ঠিকাদার, সরবরাহকারী বা পারিবারিক ব্যবসায় টাকা পাঠাচ্ছেন? নাম লিখুন। তার সরকারি চুক্তির রেকর্ড, সরকার তাকে নিষিদ্ধ করেছে কি না,
      এবং খতিয়ে দেখার মতো সংকেত — সব দেখতে পাবেন।`)}</p>
    <form class="inline-search" onsubmit="location.hash='#/check/'+encodeURIComponent(this.q.value.trim());return false">
      <input name="q" value="${esc(q)}" placeholder="${T('Company name, e.g. Barendra Construction', 'প্রতিষ্ঠানের নাম, যেমন: Barendra Construction')}" autocomplete="off" required minlength="2">
      <button class="btn-main">${T('Check', 'যাচাই')}</button></form>
    ${!r ? '' : r.companies.length ? `
      <h2>${T(`Results for “${esc(q)}”`, `“${esc(q)}”-এর ফলাফল`)}</h2>
      <table><tr><th>${T('Company', 'প্রতিষ্ঠান')}</th><th class="num">${T('Government contracts', 'সরকারি চুক্তি')}</th><th class="num">${T('Total value', 'মোট মূল্য')}</th>
        <th>${T('Officially debarred?', 'সরকারিভাবে নিষিদ্ধ?')}</th><th class="hide-sm">${T('Worth a closer look', 'খতিয়ে দেখার মতো')}</th><th></th></tr>
        ${r.companies.map(c => `<tr><td>${companyLink(c.key, c.name)}</td><td class="num">${num(c.n_contracts)}</td>
          <td class="num">${taka(c.value_bdt)}</td><td>${verdict(c)}</td><td class="hide-sm">${esc(notes(c))}</td>
          <td><a href="#/report/${encodeURIComponent(c.key)}">${T('Full check report', 'পূর্ণ যাচাই রিপোর্ট')}</a></td></tr>`).join('')}</table>`
      : `<h2>${T(`No government contracts found for “${esc(q)}”`, `“${esc(q)}” নামে কোনো সরকারি চুক্তি পাওয়া যায়নি`)}</h2>
      <p>${T('That is not good or bad by itself: many honest firms never work for the government. Try a shorter part of the name.',
        'এটি নিজে ভালো বা খারাপ কিছু নয়: অনেক সৎ প্রতিষ্ঠান কখনো সরকারি কাজ করে না। নামের ছোট অংশ দিয়ে আবার খুঁজুন।')}</p>`}
    <h2>${T('Also Check These Yourself', 'নিজেও এগুলো যাচাই করুন')}</h2>
    <ul class="plain">
      <li>${T("The firm's <b>trade licence</b> and <b>TIN/BIN</b> numbers, and that the name and address match.", 'প্রতিষ্ঠানের <b>ট্রেড লাইসেন্স</b> ও <b>টিআইএন/বিআইএন</b> নম্বর, এবং নাম-ঠিকানা মেলে কি না।')}</li>
      <li>${T('If it says it works for the government, ask for its <b>e-GP tenderer ID</b> and look up its contracts here.', 'সরকারি কাজ করে বললে তার <b>ই-জিপি টেন্ডারার আইডি</b> চেয়ে নিন এবং এখানে চুক্তি দেখুন।')}</li>
      <li>${T('Visit the office or site, and speak to past clients.', 'অফিস বা কাজের জায়গা ঘুরে দেখুন, আগের গ্রাহকদের সঙ্গে কথা বলুন।')}</li>
      <li>${T('Prohori shows public records only. A clean record is not a guarantee, and a flag is not proof of wrongdoing.', 'প্রহরী শুধু প্রকাশ্য নথি দেখায়। পরিষ্কার রেকর্ড নিশ্চয়তা নয়, আর সংকেত অন্যায়ের প্রমাণ নয়।')}</li>
    </ul>`;
}

// ---------- Contractor Check Report (the Lender Check product) ----------
const SAMPLE_REPORT = 'jakaullah and brothers';
const METHOD_NAMES = {
  OTM: ['Open tendering', 'উন্মুক্ত দরপত্র'], LTM: ['Limited tendering', 'সীমিত দরপত্র'],
  OSTETM: ['Open tendering, two envelopes', 'উন্মুক্ত দরপত্র, দুই খামে'], RFQ: ['Request for quotation', 'দরপ্রস্তাব আহ্বান'],
  RFQU: ['Request for quotation', 'দরপ্রস্তাব আহ্বান'], RFQL: ['Request for quotation', 'দরপ্রস্তাব আহ্বান'],
  DPM: ['Direct purchase, no competition', 'সরাসরি ক্রয়, প্রতিযোগিতা ছাড়া'], SSS: ['Single-source selection, no competition', 'একক উৎস, প্রতিযোগিতা ছাড়া'],
  QCBS: ['Quality and cost based selection', 'মান ও খরচভিত্তিক বাছাই'], SFB: ['Selection under fixed budget', 'নির্দিষ্ট বাজেটে বাছাই'],
  IC: ['Individual consultant', 'একক পরামর্শক'],
};
const methodName = m => (METHOD_NAMES[m] ? `${T(...METHOD_NAMES[m])} (${m})` : m);
async function report(key) {
  const r = await api(`/api/report?key=${encodeURIComponent(key)}`);
  trackEvent('report', 'report');
  const c = r.company, today = new Date();
  const rid = `PR-${today.toISOString().slice(0, 10).replace(/-/g, '')}-${(c.winner_key || '').replace(/[^a-z]/g, '').slice(0, 6).toUpperCase()}`;
  const by = esc((c.debarred_by || '').split(',')[0]);
  const debar = c.n_debarments
    ? `<b class="bad">${T('Yes', 'হ্যাঁ')}</b> — ${T(`by ${by}`, `${by} দ্বারা`)}, ${date(c.first_debar_from)} – ${date(c.last_debar_to)}`
    : `<b class="good">${T('Not on the e-GP debarment list', 'ই-জিপি নিষিদ্ধ তালিকায় নেই')}</b> ${T('(by name)', '(নাম অনুযায়ী)')}`;
  const risk = r.risk[0];
  const years = Math.max(0, Math.round((new Date(c.last_contract) - new Date(c.first_contract)) / 3.156e10 * 10) / 10);
  view.innerHTML = `
    <div class="report">
      <div class="report-head">
        <div><b>${T('Prohori Contractor Check Report', 'প্রহরী ঠিকাদার যাচাই রিপোর্ট')}</b></div>
        <div class="muted">${T('Report', 'রিপোর্ট')} ${rid}<br>${T('Made', 'তৈরি')} ${date(today)} · ${T('data up to', 'তথ্য পর্যন্ত')} ${date(r.data_through)}</div>
      </div>
      <p class="report-actions"><button class="btn-main" onclick="window.print()">${T('Print / save as PDF', 'প্রিন্ট / পিডিএফ হিসেবে রাখুন')}</button>
        ${signupBtn('lender', T('Get reports for your bank', 'আপনার ব্যাংকের জন্য রিপোর্ট নিন'))}
        <span class="muted">${T('Sample of the planned Lender Check product.', 'পরিকল্পিত লেন্ডার চেক সেবার নমুনা।')}</span></p>
      <h1>${esc(c.name)}</h1>
      <h2>${T('1. Official Checks', '১. সরকারি যাচাই')}</h2>
      ${facts([
        [T('Government debarment list (e-GP)', 'সরকারি নিষিদ্ধ তালিকা (ই-জিপি)'), debar],
        [T('Name used by other firms?', 'অন্য প্রতিষ্ঠানও কি এই নাম ব্যবহার করে?'), c.name_may_be_shared
          ? `<b class="bad">${T('Possibly', 'হতে পারে')}</b> — ${T(`this name appears in ${c.n_districts} districts; confirm address and trade licence`, `এই নাম ${dig(c.n_districts)}টি জেলায় আছে; ঠিকানা ও ট্রেড লাইসেন্স মিলিয়ে নিন`)}`
          : T('No sign of that', 'এমন কিছু দেখা যায়নি')],
      ])}
      <h2>${T('2. Track Record With Government', '২. সরকারি কাজের রেকর্ড')}</h2>
      ${facts([
        [T('Contracts won (all time)', 'জেতা চুক্তি (সব সময়)'), `${num(c.n_contracts)} · ${taka(c.value_bdt)}`],
        [T('Contracts won (last 3 years)', 'জেতা চুক্তি (গত ৩ বছর)'), `${num(r.last3.n)} · ${taka(r.last3.value_bdt)} · ${T(`from ${num(r.last3.offices)} offices`, `${num(r.last3.offices)}টি অফিস থেকে`)}`],
        [T('Active period', 'কাজের সময়কাল'), `${date(c.first_contract)} – ${date(c.last_contract)} (${T(`${years} years`, `${dig(years)} বছর`)})`],
        [T('Where', 'কোথায়'), T(`${c.n_offices} offices in ${c.n_districts} districts`, `${num(c.n_districts)}টি জেলায় ${num(c.n_offices)}টি অফিস`)],
        [T('Main ministries', 'প্রধান মন্ত্রণালয়'), r.ministries.map(m => `${esc(m.ministry)} (${num(m.n)})`).join('; ')],
      ])}
      <h3>${T('Contracts per year', 'বছরভিত্তিক চুক্তি')}</h3>${yearList(r.by_year)}
      <h3>${T('How it won its contracts', 'কোন পদ্ধতিতে কাজ পেয়েছে')}</h3>
      <table><tr><th>${T('Buying method', 'ক্রয় পদ্ধতি')}</th><th class="num">${T('Contracts', 'চুক্তি')}</th><th class="num">${T('Value', 'মূল্য')}</th></tr>
        ${r.methods.map(m => `<tr><td>${esc(methodName(m.method))}</td><td class="num">${num(m.n)}</td><td class="num">${taka(m.value_bdt)}</td></tr>`).join('')}</table>
      <h2>${T('3. Concentration and Risk Signals', '৩. কেন্দ্রীকরণ ও ঝুঁকির সংকেত')}</h2>
      ${r.flags.length ? `<ul class="flags">${r.flags.map(f => `<li class="${f.level}">${esc(T(f.en, f.bn))}</li>`).join('')}</ul>`
        : `<p>${T('No rule-based risk patterns found.', 'নিয়মভিত্তিক কোনো ঝুঁকির সংকেত পাওয়া যায়নি।')}</p>`}
      ${risk ? `<p><b>${T('AI review priority:', 'এআই যাচাই-অগ্রাধিকার:')}</b> ${bandPill(risk)} ${T(`${topTxt(risk.top_pct)} of ${num(r.scored)} active firms (${esc(risk.division)} division).`,
        `${num(r.scored)}টি সক্রিয় প্রতিষ্ঠানের মধ্যে ${topTxt(risk.top_pct)} (${esc(place(risk.division))} বিভাগ)।`)}
        ${T('Main reasons:', 'প্রধান কারণ:')} ${esc(risk.reasons.map(y => `${reasonLabel(y)} ${fmtVal(y)}`).join('; ') || T('many small factors', 'অনেক ছোট বিষয়'))}.</p>` : ''}
      ${r.bids && r.bids.pages ? `<p><b>${T(`From ${num(r.bids.pages)} contract detail pages:`, `${num(r.bids.pages)}টি চুক্তির বিস্তারিত পাতা থেকে:`)}</b>
        ${r.bids.with_bids ? T(`typical tenders received ${num(Math.round(r.bids.median_received))}; single-tender contracts ${num(r.bids.single_bid)} of ${num(r.bids.with_bids)}; `,
          `সাধারণত দরপত্র জমা পড়ে ${num(Math.round(r.bids.median_received))}টি; একক দরপত্রের চুক্তি ${num(r.bids.with_bids)}টির মধ্যে ${num(r.bids.single_bid)}টি; `) : ''}
        ${T(`not signed in time ${num(r.bids.sign_late || 0)}; performance security late ${num(r.bids.ps_late || 0)}.`,
          `সময়মতো সই হয়নি ${num(r.bids.sign_late || 0)}টি; জামানত দেরিতে ${num(r.bids.ps_late || 0)}টি।`)}</p>` : ''}
      <h2>${T('4. Biggest Offices for This Firm', '৪. এই প্রতিষ্ঠানের প্রধান অফিস')}</h2>
      <table><tr><th>${T('Office', 'অফিস')}</th><th class="num">${T('Won', 'পেয়েছে')}</th><th>${T("Share of office's contracts", 'অফিসের চুক্তিতে অংশ')}</th></tr>
        ${r.top_offices.slice(0, 6).map(o => `<tr><td>${esc(o.procuring_entity)}</td><td class="num">${num(o.n)} / ${num(o.office_n)}</td><td>${shareBar(o.share_n)}</td></tr>`).join('')}</table>
      <h2>${T('5. How to Use This Report', '৫. এই রিপোর্ট কীভাবে ব্যবহার করবেন')}</h2>
      <ul class="plain small">
        <li>${T('This report is built only from public records on the national e-GP portal (eprocure.gov.bd) and its debarment list.', 'এই রিপোর্ট শুধু জাতীয় ই-জিপি পোর্টাল (eprocure.gov.bd)-এর প্রকাশ্য নথি ও নিষিদ্ধ তালিকা থেকে তৈরি।')}</li>
        <li>${T('It is <b>not a credit rating</b> and <b>not evidence of wrongdoing</b>. Risk signals are patterns for human review.', 'এটি <b>ক্রেডিট রেটিং নয়</b> এবং <b>অন্যায়ের প্রমাণ নয়</b>। ঝুঁকির সংকেত মানুষের যাচাইয়ের জন্য।')}</li>
        <li>${T('Names are matched by spelling. Confirm identity with the trade licence, TIN and e-GP tenderer ID before any decision.', 'নাম বানান দিয়ে মেলানো। সিদ্ধান্তের আগে ট্রেড লাইসেন্স, টিআইএন ও ই-জিপি টেন্ডারার আইডি দিয়ে পরিচয় নিশ্চিত করুন।')}</li>
        <li>${T('The firm can reply to or correct anything in this report for free. Paying customers can never change a score.', 'প্রতিষ্ঠানটি বিনামূল্যে এই রিপোর্টের যেকোনো কিছুর জবাব বা সংশোধন দিতে পারে। টাকা দেওয়া গ্রাহক কখনো স্কোর বদলাতে পারে না।')}</li>
      </ul>
    </div>`;
}

// ---------- Usage numbers (team only) ----------
const PLAN_NAMES = { pro: ['Contractor Pro', 'কন্ট্রাক্টর প্রো'], lender: ['Lender Check (banks)', 'লেন্ডার চেক (ব্যাংক)'],
  institution: ['Institution licence', 'প্রতিষ্ঠানের লাইসেন্স'], digest: ['Free district digest', 'জেলার মাসিক সারাংশ'],
  alerts: ['Office alerts', 'অফিসের খবর'], notify: ['Company alerts', 'প্রতিষ্ঠানের খবর'] };
async function numbers() {
  // Private team page: the password is the PROHORI_ADMIN_KEY in .env (kept only in this browser).
  let key = store.get('pkey');
  if (!key) { key = prompt(T('Team password for the private numbers page:', 'দলের পাসওয়ার্ড:')) || ''; store.set('pkey', key); }
  const res = await fetch('/api/numbers', { headers: { 'x-admin-key': key } });
  if (!res.ok) {
    store.set('pkey', '');
    view.innerHTML = `<h1>${T('Private page', 'ব্যক্তিগত পাতা')}</h1><p class="muted">${T('This page is for the Prohori team only.', 'এই পাতা শুধু প্রহরী দলের জন্য।')}</p>`;
    return;
  }
  const n = await res.json();
  const roles = Object.entries(n.signups_by_role).sort((a, b) => b[1] - a[1]);
  const plans = Object.entries(n.signups_by_plan).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...n.daily_visitors.map(d => d.visitors));
  const none = `<tr><td colspan="2" class="muted">${T('None yet', 'এখনো নেই')}</td></tr>`;
  view.innerHTML = `
    <h1>${T('Usage Numbers (team only)', 'ব্যবহারের হিসাব (শুধু দলের জন্য)')}</h1>
    <p>${T(`Counted with <b>no cookies and no IP addresses</b>. No advertising has been done. Real numbers since ${n.since ? date(n.since) : 'launch'}.`,
      `<b>কুকি ও আইপি ঠিকানা ছাড়া</b> গোনা। কোনো বিজ্ঞাপন দেওয়া হয়নি। ${n.since ? date(n.since) : 'শুরু'} থেকে আসল সংখ্যা।`)}</p>
    ${facts([
      [T('Different visitors', 'আলাদা দর্শক'), num(n.visitors)],
      [T('Visitors from outside Bangladesh', 'বিদেশ থেকে দর্শক'), num(n.visitors_abroad)],
      [T('Pages viewed', 'দেখা পাতা'), num(n.page_views)],
      [T('Searches', 'খোঁজা'), num(n.searches)],
      [T('Questions asked to the AI', 'এআই-কে প্রশ্ন'), num(n.chat_questions)],
      [T('Contractor Check Reports opened', 'খোলা যাচাই রিপোর্ট'), num(n.reports_opened)],
      [T('Waitlist sign-ups', 'অপেক্ষার তালিকায় নাম'), num(n.signups)],
      [T('Sign-ups from abroad', 'বিদেশ থেকে নাম'), num(n.signups_abroad)],
    ])}
    <h2>${T('Sign-ups by Plan and Role', 'প্ল্যান ও পরিচয় অনুযায়ী নাম')}</h2>
    <table><tr><th>${T('Plan', 'প্ল্যান')}</th><th class="num">${T('Sign-ups', 'নাম')}</th></tr>${plans.map(([p, k]) => `<tr><td>${esc(PLAN_NAMES[p] ? T(...PLAN_NAMES[p]) : p)}</td><td class="num">${num(k)}</td></tr>`).join('') || none}</table>
    <table style="margin-top:8px"><tr><th>${T('Who', 'কে')}</th><th class="num">${T('Sign-ups', 'নাম')}</th></tr>${roles.map(([r, k]) => `<tr><td>${esc(roleName(r))}</td><td class="num">${num(k)}</td></tr>`).join('') || none}</table>
    <h2>${T('Price Test for Contractor Pro', 'কন্ট্রাক্টর প্রো-এর দাম পরীক্ষা')}</h2>
    <table><tr><th>${T('Planned price', 'পরিকল্পিত দাম')}</th><th class="num">${T('Opened the form', 'ফর্ম খুলেছে')}</th><th class="num">${T('Joined', 'যোগ দিয়েছে')}</th></tr>
      ${['6000', '9000'].map(p => `<tr><td>${T(`Tk ${num(+p)} a year`, `বছরে ${num(+p)} টাকা`)}</td><td class="num">${num(n.pro_form_opens[`pro_${p}`] || 0)}</td><td class="num">${num(n.pro_price_test[p] || 0)}</td></tr>`).join('')}</table>
    <h2>${T('Visitors per Day (last 30 days)', 'দৈনিক দর্শক (গত ৩০ দিন)')}</h2>
    <ul class="years">${n.daily_visitors.map(d => `<li><span>${dig(esc(d.day.slice(5)))}</span><span class="b" style="width:${Math.max(1, d.visitors / max * 100)}%"></span><span class="v">${num(d.visitors)}</span></li>`).join('')}</ul>`;
}

// Copy each table's header text onto its cells, so on phones every row can stack as
// "Label ..... value" blocks (see .rtable in style.css).
function labelTables() {
  view.querySelectorAll('table').forEach(t => {
    const heads = [...t.querySelectorAll('tr:first-child th')].map(th => th.textContent.trim());
    t.querySelectorAll('tr').forEach(tr =>
      [...tr.children].forEach((cell, i) => {
        if (cell.tagName === 'TD') cell.dataset.label = heads[i] || '';
      }));
    t.classList.add('rtable');
    // long values (office names, reasons) take a full line in the phone summary rows
    t.querySelectorAll('td:not(.title)').forEach(td => { if (td.textContent.trim().length > 34) td.classList.add('wide'); });
    // On phones, long tables show their first rows and a "Show more" button, so pages stay short.
    const rows = [...t.querySelectorAll('tr')].filter(tr => !tr.querySelector('th'));
    if (isPhone() && rows.length > 10) {
      rows.slice(6).forEach(tr => tr.classList.add('clip'));
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'more-rows';
      const label = () => {
        const left = t.querySelectorAll('tr.clip').length;
        btn.textContent = T(`Show ${Math.min(20, left)} more (${left} left)`, `আরও ${dig(Math.min(20, left))}টি দেখুন (বাকি ${dig(left)}টি)`);
      };
      btn.addEventListener('click', () => {
        [...t.querySelectorAll('tr.clip')].slice(0, 20).forEach(tr => tr.classList.remove('clip'));
        if (!t.querySelector('tr.clip')) btn.remove(); else label();
      });
      label();
      t.after(btn);
    }
  });
  // Fact tiles on phones: long values take the full width.
  view.querySelectorAll('.facts li').forEach(li => {
    const v = li.querySelector('.val'), l = li.querySelector('.label');
    if ((v && v.textContent.trim().length > 16) || (l && l.textContent.trim().length > 42)) li.classList.add('wide');
  });
}

// ---------- Phone menu (the side menu slides in as a drawer) ----------
function setMenu(open) {
  document.body.classList.toggle('nav-open', open);
  document.getElementById('menuBtn').setAttribute('aria-expanded', open ? 'true' : 'false');
}
document.getElementById('menuBtn').addEventListener('click', () => setMenu(!document.body.classList.contains('nav-open')));
document.getElementById('menuClose').addEventListener('click', () => setMenu(false));
document.getElementById('navshade').addEventListener('click', () => setMenu(false));
document.getElementById('sidenav').addEventListener('click', e => { if (e.target.closest('a[href^="#/"]')) setMenu(false); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') setMenu(false); });

async function route() {
  const [, page, ...rest] = location.hash.split('/');
  const arg = decodeURIComponent(rest.join('/'));
  view.innerHTML = `<p class="muted">${T('Loading…', 'লোড হচ্ছে…')}</p>`;
  try {
    if (page === 'search' && arg) await search(arg);
    else if (page === 'company') await company(arg);
    else if (page === 'office') await office(arg);
    else if (page === 'patterns') await patterns();
    else if (page === 'debarred') await debarred();
    else if (page === 'largest') await largest();
    else if (page === 'watchlist') await watchlist(rest[0], decodeURIComponent(rest[1] || ''));
    else if (page === 'model') await model();
    else if (page === 'about') about();
    else if (page === 'pricing') pricing();
    else if (page === 'probashi') probashi();
    else if (page === 'districts') await districtsPage();
    else if (page === 'check') await checkPage(arg);
    else if (page === 'district') await districtPage(arg);
    else if (page === 'report') await report(arg);
    else if (page === 'numbers') await numbers();
    else await home();
    labelTables();
    // Tell the AI assistant what is on screen: a company, an office, or one of the list pages.
    const PAGES = ['search', 'patterns', 'debarred', 'largest', 'watchlist', 'model', 'about', 'pricing', 'probashi', 'check', 'districts'];
    const KEYED = ['company', 'office', 'district', 'report'];
    const ctx = KEYED.includes(page) ? page : PAGES.includes(page) ? page : 'home';
    const h1 = view.querySelector('h1');
    setAIContext(ctx, KEYED.includes(ctx) ? arg : '', h1 ? h1.textContent.trim() : 'Home');
    trackEvent('view', ctx);
    // Highlight the current page in the Go To row; on phones scroll it into view.
    document.querySelectorAll('.gonav a').forEach(x => {
      const on = (x.getAttribute('href').split('/')[1] || '') === (page || '');
      x.classList.toggle('active', on);
      if (on && isPhone()) x.scrollIntoView({ block: 'nearest', inline: 'center' });
    });
  } catch (e) {
    view.innerHTML = `<p class="muted">${T('Could not load this page', 'পাতাটি লোড করা যায়নি')} (${esc(e.message)}).</p>`;
  }
  const sec = (page === 'probashi' || page === 'about') && arg && document.getElementById(`sec-${arg}`);
  if (sec) sec.scrollIntoView(); else window.scrollTo(0, 0);
}
window.addEventListener('hashchange', () => { document.getElementById('signup')?.remove(); route(); });
// When the screen switches between phone and desktop size (rotating, resizing), redraw for the new size.
window.matchMedia('(max-width: 760px)').addEventListener('change', e => {
  if (!e.matches) setMenu(false);
  applyChrome();
  route();
});
// Phone menu: the "Go To" row (hidden on phones) is copied, with its icons, to the top of the menu drawer.
(function copyGoToIntoMenu() {
  const head = document.querySelector('#sidenav .drawer-head');
  const items = [...document.querySelectorAll('.gonav a')].map(a => `<li>${a.outerHTML}</li>`).join('');
  head.insertAdjacentHTML('afterend', `<h3 class="m-only" data-i18n="Go To">Go To</h3><ul class="links golinks m-only">${items}</ul>`);
})();
applyChrome();
buildAI();
route();
