// Prohori front end. Routes: #/  #/search/<q>  #/company/<key>  #/office/<name>
//                           #/patterns  #/debarred  #/largest  #/about
const view = document.getElementById('view');

const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const num = n => (n ?? 0).toLocaleString('en-IN');
const pct = x => `${Math.round((x ?? 0) * 100)}%`;
const date = d => d ? new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

// Taka in the units Bangladeshi readers use: crore / lakh.
function taka(v) {
  if (v == null) return '—';
  if (v >= 1e7) return `Tk ${(v / 1e7).toLocaleString('en-IN', { maximumFractionDigits: v >= 1e9 ? 0 : 2 })} crore`;
  if (v >= 1e5) return `Tk ${(v / 1e5).toLocaleString('en-IN', { maximumFractionDigits: 1 })} lakh`;
  return `Tk ${num(Math.round(v))}`;
}
const companyLink = (key, name) => `<a href="#/company/${encodeURIComponent(key)}">${esc(name)}</a>`;
const officeLink = name => `<a href="#/office/${encodeURIComponent(name)}">${esc(name)}</a>`;
const egpLink = (t, p) => p
  ? `<a target="_blank" rel="noopener" href="https://www.eprocure.gov.bd/resources/common/ViewAwardedContracts.jsp?pkgLotId=${encodeURIComponent(p)}&tenderid=${encodeURIComponent(t)}">e-GP ↗</a>`
  : '';
const shareBar = s => `<div class="share"><div class="track"><span style="width:${Math.min(100, s * 100)}%"></span></div>${pct(s)}</div>`;
const debTag = n => n ? ' <span class="tagdeb">[debarred]</span>' : '';
const facts = rows => `<ul class="facts">${rows.map(([l, v]) =>
  `<li><span class="label">${l}</span><span class="leader"></span><span class="val">${v}</span></li>`).join('')}</ul>`;

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

// Live date/time line like public portals show ("Tuesday, 03 Nov, 2026 12:05:26 BST").
function tick() {
  const now = new Date();
  const d = now.toLocaleDateString('en-GB', { timeZone: 'Asia/Dhaka', weekday: 'long', day: '2-digit', month: 'short', year: 'numeric' });
  const t = now.toLocaleTimeString('en-GB', { timeZone: 'Asia/Dhaka', hour12: false });
  document.getElementById('clock').textContent = `${d} ${t} BST`;
}
tick(); setInterval(tick, 1000);

async function home() {
  const [s, pat] = await Promise.all([api('/api/stats'), api('/api/patterns?limit=8')]);
  view.innerHTML = `
    <h1>Who wins Bangladesh's government contracts?</h1>
    <p>Prohori reads the contract awards that government offices publish on the national e-GP portal and
      highlights patterns worth a closer look — for example, one company winning most contracts at one office,
      or contracts going to firms the government has officially debarred.
      <span class="bn">সরকারি কাজ কে পায়, কত টাকায় — সহজে দেখুন।</span></p>
    <h2>At a Glance</h2>
    ${facts([
      ['Contracts analysed', num(s.contracts)],
      ['Total contract value', taka(s.value_bdt)],
      ['Companies', num(s.companies)],
      ['Government buying offices', num(s.offices)],
      ['Companies winning 40%+ of an office\'s contracts', `<a href="#/patterns">${num(s.dominant_companies)}</a>`],
      ['Officially debarred firms found among winners', `<a href="#/debarred">${num(s.debarred_found)}</a>`],
      ['Contracts signed between', `${date(s.first_date)} – ${date(s.last_date)}`],
    ])}
    <h2>Latest Risk Patterns</h2>
    <ul class="plain">${pat.map(r => `<li>${officeLink(r.office)} (${esc(r.district)}) — ${companyLink(r.winner_key, r.winner)}
      won <b>${pct(r.top_share_n)}</b> of ${num(r.n_contracts)} contracts${debTag(r.n_debarments)}</li>`).join('')}</ul>
    <p style="margin-top:8px"><a href="#/patterns">View all risk patterns »</a></p>
    <h2>Important Notice</h2>
    <ul class="plain">
      <li>Flags are <b>patterns for review, not accusations</b>. A high share can have innocent reasons
        (few local contractors, specialised work). <span class="important">A human always decides.</span></li>
      <li>Company names are matched by spelling. Different firms can share a name — verify by address on e-GP.</li>
      <li>Data collection is in progress; figures will grow as older years are added.</li>
    </ul>`;
}

async function search(q) {
  const r = await api(`/api/search?q=${encodeURIComponent(q)}`);
  const comp = r.companies.map(c => `<tr>
      <td>${companyLink(c.key, c.name)}${debTag(c.n_debarments)}
        ${c.n_dominated_offices ? ' <span class="tagdom">[dominant at an office]</span>' : ''}</td>
      <td class="num">${num(c.n_contracts)}</td><td class="num">${taka(c.value_bdt)}</td>
      <td class="num hide-sm">${c.n_districts}</td></tr>`).join('');
  const offs = r.offices.map(o => `<tr><td>${officeLink(o.name)}</td><td>${esc(o.district)}</td>
      <td class="num">${num(o.n_contracts)}</td><td class="num">${taka(o.value_bdt)}</td></tr>`).join('');
  view.innerHTML = `<h1>Search results for “${esc(q)}”</h1>
    <h2>Companies</h2>
    ${comp ? `<table><tr><th>Company</th><th class="num">Contracts</th><th class="num">Value</th><th class="num hide-sm">Districts</th></tr>${comp}</table>` : '<p class="muted">No companies found.</p>'}
    <h2>Government Offices</h2>
    ${offs ? `<table><tr><th>Office</th><th>District</th><th class="num">Contracts</th><th class="num">Value</th></tr>${offs}</table>` : '<p class="muted">No offices found.</p>'}`;
}

function yearList(rows) {
  const max = Math.max(...rows.map(r => r.value_bdt || 0), 1);
  return `<ul class="years">${rows.map(r => `<li><span>${r.year}</span>
    <span class="b" style="width:${Math.max(1, ((r.value_bdt || 0) / max) * 100)}%"></span>
    <span class="v">${num(r.n)} contracts · ${taka(r.value_bdt)}</span></li>`).join('')}</ul>`;
}

async function company(key) {
  const r = await api(`/api/company?key=${encodeURIComponent(key)}`);
  const c = r.company;
  const labels = { high: 'High:', medium: 'Review:', info: 'Note:' };
  const flags = r.flags.length
    ? `<ul class="flags">${r.flags.map(f => `<li class="${f.level}"><span class="lvl">${labels[f.level]}</span>${esc(f.en)}
        <span class="bn">${esc(f.bn)}</span>${f.detail ? `<span class="detail">Reason on record: ${esc(f.detail)}</span>` : ''}</li>`).join('')}</ul>`
    : `<p>No risk patterns found by the current rules. <span class="bn">বর্তমান নিয়মে কোনো সংকেত পাওয়া যায়নি।</span></p>`;
  view.innerHTML = `
    <h1>${esc(c.name)}</h1>
    ${facts([
      ['Contracts won', num(c.n_contracts)],
      ['Total value', taka(c.value_bdt)],
      ['Offices / districts', `${c.n_offices} offices in ${c.n_districts} districts`],
      ['Active period', `${date(c.first_contract)} – ${date(c.last_contract)}`],
    ])}
    <h2>Risk Patterns <span class="bn">(ঝুঁকির সংকেত)</span></h2>${flags}
    <h2>Contracts Won per Year</h2>${yearList(r.by_year)}
    <h2>Where It Wins</h2>
    <table><tr><th>Office</th><th class="hide-sm">District</th><th class="num">Won</th><th>Share of office's contracts</th></tr>
      ${r.top_offices.map(o => `<tr><td>${officeLink(o.procuring_entity)}</td><td class="hide-sm">${esc(o.district)}</td>
        <td class="num">${o.n} / ${o.office_n}</td><td>${shareBar(o.share_n)}</td></tr>`).join('')}</table>
    <h2>Recent Contracts</h2>
    <table><tr><th>Signed</th><th>Work</th><th class="hide-sm">Office</th><th>Method</th><th class="num">Value</th><th></th></tr>
      ${r.recent.map(x => `<tr><td>${date(x.signed_date)}</td><td class="title">${esc(x.title)}</td>
        <td class="hide-sm">${officeLink(x.procuring_entity)}</td><td>${esc(x.method)}</td>
        <td class="num">${taka(x.value_bdt)}</td><td>${egpLink(x.tender_id, x.pkg_lot_id)}</td></tr>`).join('')}</table>`;
}

async function office(name) {
  const r = await api(`/api/office?name=${encodeURIComponent(name)}`);
  const o = r.office;
  const top = r.winners[0];
  const warn = o.top_share_n >= 0.4 && o.n_contracts >= 20
    ? `<ul class="flags"><li class="medium"><span class="lvl">Review:</span>One company — ${esc(top?.name)} — won
        ${pct(o.top_share_n)} of this office's contracts.<span class="bn">এই অফিসের বেশিরভাগ কাজ একটি প্রতিষ্ঠান পেয়েছে।</span></li></ul>` : '';
  view.innerHTML = `
    <h1>${esc(o.procuring_entity)}</h1>
    ${facts([
      ['Ministry', esc(o.ministry)],
      ['District', esc(o.district)],
      ['Contracts awarded', num(o.n_contracts)],
      ['Total value', taka(o.value_bdt)],
      ['Different winning companies', num(o.n_winners)],
    ])}
    ${warn}
    <h2>Who Wins Here</h2>
    <table><tr><th>Company</th><th class="num">Contracts</th><th class="num">Value</th><th>Share</th></tr>
      ${r.winners.map(w => `<tr><td>${companyLink(w.key, w.name)}${debTag(w.n_debarments)}</td>
        <td class="num">${w.n}</td><td class="num">${taka(w.value_bdt)}</td><td>${shareBar(w.share_n)}</td></tr>`).join('')}</table>
    <h2>Recent Contracts</h2>
    <table><tr><th>Signed</th><th>Work</th><th>Winner</th><th>Method</th><th class="num">Value</th></tr>
      ${r.recent.map(x => `<tr><td>${date(x.signed_date)}</td><td class="title">${esc(x.title)}</td>
        <td>${companyLink(x.winner_key, x.winner)}</td><td>${esc(x.method)}</td><td class="num">${taka(x.value_bdt)}</td></tr>`).join('')}</table>`;
}

async function patterns() {
  const rows = await api('/api/patterns');
  view.innerHTML = `
    <h1>Offices Where One Company Wins Most Contracts</h1>
    <p>Offices with 30 or more contracts where a single company won at least 40%. A high share can have innocent
      reasons — it is a signal to look closer, not proof. <span class="bn">একটি প্রতিষ্ঠান বেশিরভাগ কাজ পাচ্ছে — যাচাই করা দরকার।</span></p>
    <table><tr><th>Office</th><th class="hide-sm">District</th><th>Top winner</th><th class="num">Contracts</th><th>Top winner's share</th></tr>
      ${rows.map(r => `<tr><td>${officeLink(r.office)}</td><td class="hide-sm">${esc(r.district)}</td>
        <td>${companyLink(r.winner_key, r.winner)}${debTag(r.n_debarments)}</td>
        <td class="num">${num(r.n_contracts)}</td><td>${shareBar(r.top_share_n)}</td></tr>`).join('')}</table>`;
}

async function debarred() {
  const rows = await api('/api/debarred');
  view.innerHTML = `
    <h1>Debarred Firms Found Among Contract Winners</h1>
    <p>Companies on the government's own e-GP debarment list that also appear as contract winners.
      Debarment is an official government decision. <span class="important">Names are matched by spelling</span> —
      where a name appears in many districts it may belong to several firms.</p>
    <table><tr><th>Company</th><th class="num">Contracts</th><th class="num">Value</th><th>Debarred</th><th class="hide-sm">By</th></tr>
      ${rows.map(r => `<tr><td>${companyLink(r.key, r.name)}${r.name_may_be_shared ? ' <span class="muted">(name in ' + r.n_districts + ' districts)</span>' : ''}</td>
        <td class="num">${num(r.n_contracts)}</td><td class="num">${taka(r.value_bdt)}</td>
        <td>${date(r.first_debar_from)} – ${date(r.last_debar_to)}</td>
        <td class="hide-sm">${esc((r.debarred_by || '').split(',')[0])}</td></tr>`).join('')}</table>`;
}

async function largest() {
  const rows = await api('/api/largest');
  view.innerHTML = `
    <h1>Largest Contracts</h1>
    <table><tr><th>Signed</th><th>Work</th><th>Winner</th><th class="hide-sm">Office</th><th class="num">Value</th><th></th></tr>
      ${rows.map(x => `<tr><td>${date(x.signed_date)}</td><td class="title">${esc(x.title)}</td>
        <td>${companyLink(x.winner_key, x.winner)}</td><td class="hide-sm">${officeLink(x.procuring_entity)}</td>
        <td class="num">${taka(x.value_bdt)}</td><td>${egpLink(x.tender_id, x.pkg_lot_id)}</td></tr>`).join('')}</table>`;
}

function about() {
  view.innerHTML = `
    <h1>How Prohori Works</h1>
    <p>By law, every government office publishes its tenders and contract awards on the national e-GP portal
      (eprocure.gov.bd). There are almost 9 lakh of them — too many for anyone to check by hand.
      Prohori collects these public records automatically and checks them for patterns.</p>
    <h2>How to Read a Risk Flag</h2>
    <ul class="flags">
      <li class="high"><span class="lvl">High:</span>An official government decision, such as a debarment.</li>
      <li class="medium"><span class="lvl">Review:</span>An unusual pattern, such as one company winning most contracts at an office, or many contracts given without open competition.</li>
      <li class="info"><span class="lvl">Note:</span>Something to keep in mind, such as a company name used by several different firms.</li>
    </ul>
    <h2>What Prohori Does Not Do</h2>
    <ul class="plain">
      <li>It does not call anyone corrupt. Flags are signals for review; a human — an auditor, bank officer or journalist — always decides.</li>
      <li>It does not use any private data. Everything comes from public government records.</li>
    </ul>`;
}

async function route() {
  const [, page, ...rest] = location.hash.split('/');
  const arg = decodeURIComponent(rest.join('/'));
  view.innerHTML = '<p class="muted">Loading…</p>';
  try {
    if (page === 'search' && arg) await search(arg);
    else if (page === 'company') await company(arg);
    else if (page === 'office') await office(arg);
    else if (page === 'patterns') await patterns();
    else if (page === 'debarred') await debarred();
    else if (page === 'largest') await largest();
    else if (page === 'about') about();
    else await home();
  } catch (e) {
    view.innerHTML = `<p class="muted">Could not load this page (${esc(e.message)}).</p>`;
  }
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', route);
route();
