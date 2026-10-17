"""Builds frontend/index.html from the design page, which is not changed.

    python3 scripts/build_frontend.py [path/to/company.src.html]   (default: ../company-analysis/company.src.html)
"""
import re
from pathlib import Path

NAME = "Wintender"
SITE = Path(__file__).resolve().parents[1]
import sys
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else SITE.parent / "company-analysis/company.src.html"
src = SOURCE.read_text()
s = src


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:90])
    s = s.replace(old, new)


# 1. the sample-data generator becomes the data loader
start = s.index("/* ---------- sample data, in the shape of")
end = s.index("for (const p of PART) (BY_TENDER[p.tender_id] ||= []).push(p);\n") + len("for (const p of PART) (BY_TENDER[p.tender_id] ||= []).push(p);\n")
s = s[:start] + r"""/* ---------- data from the API: company, buyer_org, tender, participation and contract totals ---------- */
const API = (window.API_BASE || '').replace(/\/$/, '');
let COMPANY = null, PART = [], T = {}, A = {}, C = {}, CT = {}, BY_TENDER = {}, INDIA = [], LIMITED = false;
const END = new Date();
const NO_AUTH = { organisation: 'Unknown authority', ministry: '', department: '', office: '', state: null };
async function getJSON(path) {
  const r = await fetch(API + path, { headers: { Accept: 'application/json' } });
  if (!r.ok) throw new Error(r.status === 429 ? 'Too many requests. Wait a minute and try again.'
    : r.status === 404 ? 'This company was not found.' : 'The server could not answer (' + r.status + '). Try again in a moment.');
  return r.json();
}
async function loadCompany(id) {
  const d = await getJSON('/api/company?id=' + encodeURIComponent(id));
  COMPANY = d.company; PART = d.part; LIMITED = d.limited;
  T = Object.fromEntries(d.tenders.map(t => [t.tender_id, t]));
  A = Object.fromEntries(d.authorities.map(a => [a.buyer_org_id, a]));
  C = Object.fromEntries([COMPANY, ...d.companies].map(c => [c.company_id, c]));
  CT = Object.fromEntries(d.contracts.map(c => [c.tender_id + ':' + c.company_id, c.total]));
  BY_TENDER = {};
  for (const p of PART) if (T[p.tender_id]) (BY_TENDER[p.tender_id] ||= []).push(p);
}
""" + s[end:]

# 2. window.history was shadowed by a function called history(), so the address bar never updated
rep("function history() {", "function bidRows() {")
rep("const H = history();", "const H = bidRows();")
rep("  return PART.filter(p => p.company_id === COMPANY.company_id && inPeriod(T[p.tender_id]))",
    "  return PART.filter(p => p.company_id === COMPANY.company_id && T[p.tender_id] && inPeriod(T[p.tender_id]))")
rep("const t = T[p.tender_id], a = A[t.buyer_org_id];", "const t = T[p.tender_id], a = A[t.buyer_org_id] || NO_AUTH;")
rep("office: a.office, state: a.state }", "office: a.office, state: t.state || a.state }")

# 3. real data has gaps (no state, no authority): skip them instead of showing "null"
rep("buyers: new Set(H.map(h => h.buyer_org_id)).size, states: new Set(H.map(h => h.state)).size,",
    "buyers: new Set(H.map(h => h.buyer_org_id)).size, states: new Set(H.map(h => h.state).filter(Boolean)).size,")
rep("const m = {}; for (const h of H) m[h[key]] = (m[h[key]] || 0) + (won(h) ? value(h) : 0) + 1e-6;",
    "const m = {}; for (const h of H) if (h[key]) m[h[key]] = (m[h[key]] || 0) + (won(h) ? value(h) : 0) + 1e-6;")
rep("g.n++; g.states.add(h.state);\n    const s = (states[h.state] ||= { name: h.state, v: 0, n: 0, orgs: new Set() }); s.v += v; s.n++; s.orgs.add(h.organisation);",
    "g.n++; if (h.state) g.states.add(h.state);\n    if (h.state) { const s = (states[h.state] ||= { name: h.state, v: 0, n: 0, orgs: new Set() }); s.v += v; s.n++; s.orgs.add(h.organisation); }")
rep("allStates: new Set(H.map(h => h.state)).size };", "allStates: new Set(H.map(h => h.state).filter(Boolean)).size };")
rep("const a = (m[h.buyer_org_id] ||= { ...A[h.buyer_org_id], bids: 0, won: 0, value: 0, last: '' });",
    "const a = (m[h.buyer_org_id] ||= { ...(A[h.buyer_org_id] || NO_AUTH), bids: 0, won: 0, value: 0, last: '' });")
rep("[a.organisation, a.office, a.ministry, a.state].some(x => x.toLowerCase().includes(q))",
    "[a.organisation, a.office, a.ministry, a.state].some(x => (x || '').toLowerCase().includes(q))")
rep("<td class=\"hide-sm\">${esc(a.state)}</td>", "<td class=\"hide-sm\">${esc(a.state || '—')}</td>")
rep("<span class=\"sub trunc\">${esc(h.office)}, ${esc(h.state)}</span>",
    "<span class=\"sub trunc\">${esc([h.office, h.state].filter(Boolean).join(', ') || '—')}</span>")
rep("const catChips = Object.entries(cats)", "const catChips = Object.entries(cats).filter(([k]) => k && k !== 'null')")

# 4. the map comes from india.json instead of being pasted into the page
rep('<script id="india" type="application/json">__INDIA__</script>\n', '')
rep("const INDIA = JSON.parse(document.getElementById('india').textContent);\n", "")

# 5. sample-data labels become real ones; "Companies" goes back to the search
rep('<div class="sidefoot"><b>Sample data</b><span>Generated to show the layout. Same shape as the company tables; not connected to the database.</span>',
    '<div class="sidefoot"><b>Live data</b><span>Awarded GeM bids, contracts and bid documents. The company figures are rebuilt every night.</span>')
rep('<span class="badge badge-warn">Sample data</span>', '<span class="badge" id="note" hidden></span>')
rep("<span>Companies</span><span class=\"sepc\">/</span><span class=\"trunc\">${esc(short(COMPANY.display_name))}</span>",
    "<a class=\"crumblink\" href=\"./\">Companies</a><span class=\"sepc\">/</span><span class=\"trunc\">${esc(short(COMPANY.display_name))}</span>")
rep("<title>Bidally Company Profile</title>", f"<title>{NAME}</title>\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<meta name=\"description\" content=\"Bid history, authorities and competitors of GeM sellers.\">")
rep("</style>", """.crumblink{color:inherit;text-decoration:none}.crumblink:hover{color:var(--text);text-decoration:underline}
.tbl a.name{color:inherit;text-decoration:none}.tbl a.name:hover{text-decoration:underline}
</style>""")

# 6. a search page when no company is chosen, and startup that loads the data first
rep("const startAt = location.hash.slice(1);\nif (SECTIONS.some(s => s[0] === startAt)) state.section = startAt;\nconst vsAt = /^vs-(\\d+)$/.exec(startAt);\nif (vsAt) { state.section = 'competitors'; state.comp.id = +vsAt[1]; }\nstate.anim = true;\nrender();\n",
r"""/* ---------- company search (the start page) ---------- */
const HSORTS = [['bids', 'Most bids'], ['won', 'Most wins'], ['value', 'Awarded value'], ['rate', 'Win rate'], ['name', 'Name']];
const startArgs = new URLSearchParams(location.search);
const home = { q: startArgs.get('q') || '', sort: HSORTS.some(x => x[0] === startArgs.get('sort')) ? startArgs.get('sort') : 'bids',
  page: Math.max(0, parseInt(startArgs.get('page'), 10) || 0), rows: null, total: 0, per: 50, rateMin: 10, error: '' };
function homeView() {
  const rows = home.rows, typed = home.q.trim().length >= 2;
  const body = (rows || []).map(c => `<tr class="clickable" data-co="${c.company_id}" tabindex="0">
      <td><span class="row gap10"><span class="av sm">${initials(c.display_name)}</span><a class="name" href="?c=${c.company_id}">${esc(title(c.display_name))}</a></span></td>
      <td class="r">${num(c.total_bids)}</td><td class="r">${num(c.awarded_bids)}</td><td class="r hide-sm">${pct(c.win_rate)}</td>
      <td class="r"><b>${inr(c.awarded_value)}</b></td><td class="go">${icon('arrow', 15)}</td></tr>`).join('');
  const pages = Math.max(1, Math.ceil(home.total / home.per)), from = home.page * home.per;
  const sorts = HSORTS.map(([k, l]) => `<button class="${home.sort === k ? 'on' : ''}" data-hsort="${k}">${l}</button>`).join('');
  const what = home.sort === 'rate' ? `companies with at least ${home.rateMin} bids` : typed ? 'matching companies' : 'companies';
  const list = home.error ? `<div class="empty"><strong>${esc(home.error)}</strong><span>Try again in a moment.</span></div>`
    : rows == null ? `<div class="empty"><strong>Loading…</strong></div>`
    : rows.length ? `<div class="scroll-x"><table class="tbl"><thead><tr><th>Company</th><th class="r">Bids</th><th class="r">Won</th><th class="r hide-sm">Win rate</th><th class="r">Awarded value</th><th></th></tr></thead><tbody>${body}</tbody></table></div>
      <div class="pager"><span>${num(from + 1)}–${num(from + rows.length)} of ${num(home.total)} ${what} · page ${num(home.page + 1)} of ${num(pages)}</span>
        <span class="row gap6"><button class="btn" data-hpage="-1" ${home.page ? '' : 'disabled'}>Previous</button><button class="btn" data-hpage="1" ${home.page < pages - 1 ? '' : 'disabled'}>Next</button></span></div>`
    : `<div class="empty"><strong>No company matches “${esc(home.q)}”</strong><span>Try part of the name.</span></div>`;
  return `<div class="pagehead rise" style="--i:0"><div class="eyebrow">Companies</div><h1 style="margin-top:4px">Find a company</h1></div>
    <section class="card rise" style="--i:1">
      <div class="toolbar"><div class="search" style="width:min(380px,100%)">${icon('search', 15)}<input class="input" id="hq" type="search" placeholder="Company name, at least 2 letters" value="${esc(home.q)}" aria-label="Search companies"></div>
        <div class="seg" role="group" aria-label="Sort companies">${sorts}</div>
        <span class="sub small muted" style="margin-left:auto">${rows ? num(home.total) + ' ' + what : ''}</span></div>
      ${list}</section>`;
}
function renderHome() {
  document.getElementById('sidenav').innerHTML = `<div class="sidegrp">${NAME}</div><button class="sideitem on">${icon('search')}<span>Find a company</span></button>`;
  document.getElementById('mtabs').innerHTML = '';
  document.getElementById('crumbs').innerHTML = '<span>Companies</span>';
  document.getElementById('period').innerHTML = '';
  document.getElementById('view').innerHTML = homeView();
}
async function searchCompanies() {
  const asked = [home.q, home.sort, home.page].join('|');
  const args = new URLSearchParams();  // the list's state goes in the address, so Back returns to the same page
  if (home.q.trim()) args.set('q', home.q.trim());
  if (home.sort !== 'bids') args.set('sort', home.sort);
  if (home.page) args.set('page', home.page);
  try { history.replaceState(null, '', location.pathname + (String(args) ? '?' + args : '')); } catch (e) {}
  try {
    const d = await getJSON('/api/companies?' + new URLSearchParams({ q: home.q.trim(), sort: home.sort, page: home.page }));
    if (asked !== [home.q, home.sort, home.page].join('|')) return;
    Object.assign(home, { rows: d.companies, total: d.total, per: d.per_page, rateMin: d.rate_min_bids, error: '' });
  } catch (e) { home.error = e.message; }
  renderHome();
  const el = document.getElementById('hq'); if (el && home.q && document.activeElement === document.body) { el.focus(); el.setSelectionRange(home.q.length, home.q.length); }
}
let homeTyping;
document.addEventListener('input', e => {
  if (e.target.id !== 'hq') return;
  home.q = e.target.value; home.page = 0; clearTimeout(homeTyping); homeTyping = setTimeout(searchCompanies, 250);
});
document.addEventListener('click', e => {
  const b = e.target.closest('button[data-hsort], button[data-hpage]');
  if (!b || b.disabled) return;
  if (b.dataset.hsort) { home.sort = b.dataset.hsort; home.page = 0; } else { home.page = Math.max(0, home.page + +b.dataset.hpage); window.scrollTo(0, 0); }
  home.rows = home.rows || []; searchCompanies();
});
document.addEventListener('click', e => { const r = e.target.closest('tr[data-co]'); if (r && !e.target.closest('a')) location.href = '?c=' + r.dataset.co; });
document.addEventListener('keydown', e => { const r = e.target.closest && e.target.closest('tr[data-co]'); if (r && e.key === 'Enter') location.href = '?c=' + r.dataset.co; });

/* ---------- start ---------- */
(async () => {
  const id = new URLSearchParams(location.search).get('c');
  const view = document.getElementById('view');
  fetch('india.json').then(r => r.json()).then(paths => { INDIA = paths; if (COMPANY) render(); }).catch(() => {});
  if (!id) { renderHome(); return searchCompanies(); }
  view.innerHTML = '<div class="empty"><strong>Loading company…</strong><span>Bids, authorities and competitors.</span></div>';
  try { await loadCompany(id); }
  catch (e) { view.innerHTML = `<div class="empty"><strong>${esc(e.message)}</strong><a class="btn" href="./">Find a company</a></div>`; return; }
  document.title = title(COMPANY.display_name) + ' · ' + NAME;
  if (LIMITED) { const n = document.getElementById('note'); n.hidden = false; n.textContent = 'Latest bids only'; n.title = 'This company has more bids than the page loads; the oldest are left out.'; }
  const startAt = location.hash.slice(1);
  if (SECTIONS.some(s => s[0] === startAt)) state.section = startAt;
  const vsAt = /^vs-(\d+)$/.exec(startAt);
  if (vsAt) { state.section = 'competitors'; state.comp.id = +vsAt[1]; }
  state.anim = true;
  render();
})();
""")
rep("addEventListener('hashchange', () => { const h = location.hash.slice(1); if (SECTIONS.some(s => s[0] === h) && h !== state.section) go(h); });",
    "addEventListener('hashchange', () => { const h = location.hash.slice(1), vs = /^vs-(\\d+)$/.exec(h); if (!COMPANY) return;\n  if (vs) { if (+vs[1] !== state.comp.id) openRival(+vs[1]); } else if (SECTIONS.some(s => s[0] === h) && h !== state.section) go(h); });")

# 7. competitors are counted by the server for each period; a competitor's own bids load when its head to head opens
rep("let COMPANY = null, PART = [], T = {}, A = {}, C = {}, CT = {}, BY_TENDER = {}, INDIA = [], LIMITED = false;",
    "let COMPANY = null, PART = [], T = {}, A = {}, C = {}, CT = {}, BY_TENDER = {}, INDIA = [], LIMITED = false, RIVALS = {};\nconst LOADED = new Set();")
rep("COMPANY = d.company; PART = d.part; LIMITED = d.limited;", "COMPANY = d.company; PART = d.part; LIMITED = d.limited; RIVALS = d.rivals;")
rep("""  for (const p of PART) if (T[p.tender_id]) (BY_TENDER[p.tender_id] ||= []).push(p);
}
""", """  for (const p of PART) if (T[p.tender_id]) (BY_TENDER[p.tender_id] ||= []).push(p);
}
async function loadRival(id) {
  if (LOADED.has(id)) return;
  const d = await getJSON('/api/rival?id=' + COMPANY.company_id + '&rival=' + id);
  for (const p of d.part) if (T[p.tender_id]) { PART.push(p); (BY_TENDER[p.tender_id] ||= []).push(p); }
  LOADED.add(id);
}
""")
i = s.index("function rivals(H) {")
j = s.index("\n}\n", i) + 3
s = s[:i] + "function rivals(H) {\n  return (RIVALS[state.period] || []).map(r => ({ ...r, c: C[r.id] })).filter(r => r.c);\n}\n" + s[j:]
rep("function openRival(id) { state.section = 'competitors'; state.comp.id = id; state.anim = true; setHash('vs-' + id); render(); window.scrollTo(0, 0); }",
    """async function openRival(id) {
  state.section = 'competitors'; state.comp.id = id; state.anim = true; setHash('vs-' + id);
  if (!LOADED.has(id)) {
    document.getElementById('view').innerHTML = '<div class="empty"><strong>Loading the head to head…</strong></div>';
    try { await loadRival(id); } catch (e) { state.comp.id = null; render(); return; }
  }
  render(); window.scrollTo(0, 0);
}""")
rep("  if (vsAt) { state.section = 'competitors'; state.comp.id = +vsAt[1]; }\n  state.anim = true;\n  render();\n})();",
    "  if (vsAt) { state.section = 'competitors'; state.comp.id = +vsAt[1]; try { await loadRival(+vsAt[1]); } catch (e) { state.comp.id = null; } }\n  state.anim = true;\n  render();\n})();")

# 8. real counts need a grid step that grows with the data; masked offices ("*****") are left out; [hidden] really hides
rep("const step = max <= 6 ? 1 : max <= 12 ? 2 : max <= 30 ? 5 : 10, top = Math.ceil(max / step) * step;",
    "const step = niceStep(max), top = Math.ceil(max / step) * step;")
rep("step = max <= 4 ? 1 : max <= 10 ? 2 : 5, top = Math.ceil(max / step) * step;",
    "step = niceStep(max, 4), top = Math.ceil(max / step) * step;")
rep("const bar = (w, c) =>", """const niceStep = (max, lines = 6) => { const raw = Math.max(1, max / lines), p = 10 ** Math.floor(Math.log10(raw)), f = raw / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; };
const bar = (w, c) =>""")
rep("office: a.office, state: t.state || a.state }", "office: /^\\*+$/.test(a.office || '') ? '' : a.office, state: t.state || a.state }")
rep("<span class=\"sub trunc\">${esc(a.office)} · ${esc(a.ministry)}</span>",
    "<span class=\"sub trunc\">${esc([/^\\*+$/.test(a.office || '') ? '' : a.office, a.ministry].filter(Boolean).join(' · '))}</span>")
rep(".crumblink{", "[hidden]{display:none!important}\n.crumblink{")

# 9. the product name; the page's API is on the same site, so no address to configure
rep("/* Bidally app shell scoped to one seller", f"/* {NAME} app shell scoped to one seller")
rep("tokens from the Bidally design */", "tokens from the design */")
rep('<div class="brand"><div class="mark">B</div><div><span class="name">Bidally</span><span class="sub">Bidder Intelligence</span></div></div>',
    f'<div class="brand"><div class="mark">{NAME[0]}</div><div><span class="name">{NAME}</span><span class="sub">GeM bid history</span></div></div>')
rep("const API = (window.API_BASE || '').replace(/\\/$/, '');", f"const API = (window.API_BASE || '').replace(/\\/$/, ''), NAME = '{NAME}';")

assert "mulberry32" not in s
assert "Bidally" not in s, "the old name is still in the page" and "TENDERS" not in s and "__INDIA__" not in s
# keep the company's name in the tab title; Next's router puts the default title back when the hash changes
rep("  const H = bidRows();\n  renderShell(H);", "  const H = bidRows();\n  document.title = title(COMPANY.display_name) + ' · ' + NAME;\n  renderShell(H);")

# 11. outcome_source 3 is a tied L1 counted as won until a contract names the winner
rep("by_contract: w.filter(h => h.outcome_source === 1).length, pending:",
    "by_contract: w.filter(h => h.outcome_source === 1).length, tied: w.filter(h => h.outcome_source === 3).length, pending:")
rep("${num(s.by_contract)} by contract, ${num(s.won - s.by_contract)} as sole L1",
    "${num(s.by_contract)} by contract, ${num(s.won - s.by_contract - s.tied)} sole L1${s.tied ? ', ' + num(s.tied) + ' tied L1' : ''}")
rep("${h.outcome_source === 1 ? 'Contract' : 'Sole L1'}",
    "${h.outcome_source === 1 ? 'Contract' : h.outcome_source === 3 ? 'L1 tie' : 'Sole L1'}")

# 10. split into the Next.js app: the CSS, the HTML shell (rendered by app/page.js) and the page script (public/app.js)
import json
style = s[s.index("<style>\n") + 8:s.index("</style>")]
shell = s[s.index("</style>") + len("</style>"):s.index("<script>")].strip()
script = s[s.index("<script>\n") + 9:s.rindex("</script>")]
(SITE / "app/design.css").write_text(style)
(SITE / "app/shell.js").write_text("// generated by scripts/build_frontend.py from the design page; do not edit\nexport default " + json.dumps(shell) + ";\n")
(SITE / "public/app.js").write_text("// generated by scripts/build_frontend.py from the design page; do not edit\n" + script)
# public/india.json (the map) does not change
print("built: css", len(style), "shell", len(shell), "script", len(script), "bytes; source unchanged:", SOURCE.read_text() == src)
