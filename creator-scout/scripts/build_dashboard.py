#!/usr/bin/env python3
"""
Stage 4: render a self-contained dashboard from enriched.json.

    python3 build_dashboard.py --enriched output/enriched.json \\
        --meta output/run-meta.json --out output/creator-pool.html \\
        --title "Creator Pool" --platform instagram --niche "your niche"

One HTML file, everything inlined, no network calls, no CDN, dark-mode aware.
Design notes if you restyle this: engagement is the number that earns top
billing (not follower count), the mean/median toggle exists because a small
post sample is routinely skewed by one outlier, and a "found by 2+ methods"
badge matters because that's the strongest discovery signal the pipeline has.
"""
import argparse
import json
import os
import sys

CSS = """
:root{
  --paper:#F6F4EE; --ink:#171A21;
  --bg:var(--paper); --panel:#FFFFFF; --line:#DDD8CB; --line-soft:#EAE6D9;
  --text:#171A21; --text-dim:#5D6270; --text-faint:#8D8F97;
  --accent:#3454D1; --accent-soft:#DCE3F7; --accent-ink:#1F3599;
  --warn:#9A6314; --warn-bg:#F4E7D2;
  --m-search:#8A5A2E; --m-search-bg:#F2E4D3;
  --m-tag:#2B6E8C; --m-tag-bg:#DCEAF0;
  --m-native:#6B4E8E; --m-native-bg:#E7E0F0;
  --shadow:0 1px 3px rgba(23,26,33,.08); --radius:6px;
  --display:"Iowan Old Style","Georgia",ui-serif,serif;
  --body:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
  --mono:"SF Mono",ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#14161C; --panel:#1D2028; --line:#31353F; --line-soft:#282C35;
    --text:#E7E5DD; --text-dim:#9A9DA8; --text-faint:#6E7180;
    --accent:#7C93F0; --accent-soft:#232A47; --accent-ink:#B7C4F7;
    --warn:#E0B267; --warn-bg:#32271A;
    --m-search:#D9A876; --m-search-bg:#332619;
    --m-tag:#7FBCDA; --m-tag-bg:#1C2E36;
    --m-native:#B69BD6; --m-native-bg:#28213A;
    --shadow:0 1px 3px rgba(0,0,0,.4);
  }
}
:root[data-theme="dark"]{
  --bg:#14161C; --panel:#1D2028; --line:#31353F; --line-soft:#282C35;
  --text:#E7E5DD; --text-dim:#9A9DA8; --text-faint:#6E7180;
  --accent:#7C93F0; --accent-soft:#232A47; --accent-ink:#B7C4F7;
  --warn:#E0B267; --warn-bg:#32271A;
  --m-search:#D9A876; --m-search-bg:#332619;
  --m-tag:#7FBCDA; --m-tag-bg:#1C2E36;
  --m-native:#B69BD6; --m-native-bg:#28213A;
  --shadow:0 1px 3px rgba(0,0,0,.4);
}
:root[data-theme="light"]{
  --bg:var(--paper); --panel:#FFFFFF; --line:#DDD8CB; --line-soft:#EAE6D9;
  --text:#171A21; --text-dim:#5D6270; --text-faint:#8D8F97;
  --accent:#3454D1; --accent-soft:#DCE3F7; --accent-ink:#1F3599;
  --warn:#9A6314; --warn-bg:#F4E7D2;
  --m-search:#8A5A2E; --m-search-bg:#F2E4D3;
  --m-tag:#2B6E8C; --m-tag-bg:#DCEAF0;
  --m-native:#6B4E8E; --m-native-bg:#E7E0F0;
  --shadow:0 1px 3px rgba(23,26,33,.08);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--body);font-size:15px;line-height:1.5}
.wrap{max-width:1220px;margin:0 auto;padding:30px 22px 64px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;flex-wrap:wrap;
  border-bottom:2px solid var(--text);padding-bottom:12px;margin-bottom:22px}
.kicker{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--text-dim);margin:0 0 4px}
h1{font-family:var(--display);font-weight:600;font-size:clamp(26px,4vw,38px);margin:0;text-wrap:balance}
.count{font-family:var(--mono);font-size:30px;line-height:1;text-align:right}
.count span{display:block;font-family:var(--body);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--text-dim);margin-top:4px}
.themebtn{font-size:10px;letter-spacing:.08em;text-transform:uppercase;background:transparent;
  color:var(--text-dim);border:1px solid var(--line);border-radius:var(--radius);padding:6px 10px;cursor:pointer}
.themebtn:hover{color:var(--accent);border-color:var(--accent)}
.panels{display:grid;grid-template-columns:1.2fr 1fr;gap:24px;padding-bottom:20px;
  border-bottom:1px solid var(--line-soft)}
@media (max-width:800px){.panels{grid-template-columns:1fr}}
.panel-label{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-faint);
  display:flex;justify-content:space-between;gap:10px;margin:0 0 8px}
.meter{display:flex;height:22px;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
.meter div+div{border-left:1px solid var(--bg)}
.meterkey{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:8px}
.meterkey button{display:flex;align-items:center;gap:6px;background:none;border:none;padding:2px 0;
  cursor:pointer;color:var(--text-dim);font-size:12px}
.meterkey button[aria-pressed="false"]{opacity:.35}
.dot{width:9px;height:9px;border-radius:2px}
.meterkey b{font-family:var(--mono);color:var(--text)}
.health{display:flex;flex-direction:column;gap:8px;font-size:13px}
.health-row{display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:baseline;color:var(--text-dim)}
.health-row b{font-family:var(--mono);color:var(--text)}
.health-note{font-size:11px;color:var(--text-faint);margin:0}
.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:14px 0;
  border-bottom:1px solid var(--line-soft);position:sticky;top:0;background:var(--bg);z-index:5}
.search{flex:1 1 200px;min-width:160px}
.search input{width:100%;font-size:14px;color:var(--text);background:var(--panel);
  border:1px solid var(--line);border-radius:var(--radius);padding:8px 11px}
.toggle{display:flex;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
.toggle button{font-size:10px;letter-spacing:.08em;text-transform:uppercase;background:var(--panel);
  color:var(--text-dim);border:none;padding:7px 10px;cursor:pointer}
.toggle button[aria-pressed="true"]{background:var(--accent);color:#fff}
.chip{font-size:10px;letter-spacing:.06em;text-transform:uppercase;background:var(--panel);
  color:var(--text-dim);border:1px solid var(--line);border-radius:var(--radius);padding:7px 9px;cursor:pointer}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
select{font-size:13px;color:var(--text);background:var(--panel);border:1px solid var(--line);
  border-radius:var(--radius);padding:7px 9px}
.resultline{display:flex;justify-content:space-between;gap:16px;padding:12px 0 2px;font-size:12px;
  color:var(--text-dim);flex-wrap:wrap}
.resultline b{font-family:var(--mono);color:var(--text)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px;margin-top:12px}
.card{display:flex;flex-direction:column;gap:9px;background:var(--panel);border:1px solid var(--line-soft);
  border-radius:var(--radius);padding:14px;box-shadow:var(--shadow)}
.card:hover{border-color:var(--accent)}
.card-top{display:flex;justify-content:space-between;gap:10px}
.handle{font-family:var(--mono);font-size:14px;color:var(--text);text-decoration:none}
.handle:hover{color:var(--accent)}
.handle::before{content:"@";color:var(--text-faint)}
.followers{text-align:right}
.followers b{display:block;font-family:var(--mono);font-size:15px}
.followers span{display:block;font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-faint)}
.metrics{display:flex;gap:14px;align-items:center;padding:8px 0;border-top:1px solid var(--line-soft);
  border-bottom:1px solid var(--line-soft)}
.er b{font-family:var(--mono);font-size:20px}
.er i{font-style:normal;font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--text-faint)}
.submetrics{display:flex;flex-wrap:wrap;gap:2px 12px;font-size:11px;color:var(--text-dim)}
.submetrics span{font-family:var(--mono);color:var(--text)}
.bio{font-size:12px;line-height:1.5;color:var(--text-dim);margin:0;white-space:pre-line;overflow-wrap:anywhere}
.cardfoot{display:flex;flex-wrap:wrap;gap:5px;align-items:center}
.src{font-size:10px;padding:3px 6px;border-radius:var(--radius);white-space:nowrap}
.src-profile_search{color:var(--m-search);background:var(--m-search-bg)}
.src-hashtag{color:var(--m-tag);background:var(--m-tag-bg)}
.src-native{color:var(--m-native);background:var(--m-native-bg)}
.tag{font-size:9px;letter-spacing:.08em;text-transform:uppercase;border-radius:var(--radius);padding:3px 6px}
.tag-cross{color:var(--accent-ink);background:var(--accent-soft);border:1px solid var(--accent)}
.tag-skew,.tag-managed{color:var(--warn);background:var(--warn-bg);border:1px solid var(--warn)}
.recency{font-family:var(--mono);font-size:10px;color:var(--text-faint);margin-right:auto}
.recency.fresh{color:var(--accent)}
.contact{border-top:1px dashed var(--line);padding-top:8px;margin-top:auto;display:flex;
  flex-direction:column;gap:4px}
.contact-label{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-faint)}
.contact-row{display:flex;gap:4px 9px;flex-wrap:wrap;font-size:11px}
.contact a{color:var(--accent);text-decoration:none;overflow-wrap:anywhere}
.contact a:hover{text-decoration:underline}
.cmail{font-family:var(--mono);font-size:11px}
.cnone{color:var(--text-faint);font-style:italic;font-size:11px}
.empty{padding:50px 0;text-align:center;color:var(--text-dim)}
.linkbtn{background:none;border:none;font:inherit;color:var(--accent);cursor:pointer;text-decoration:underline}
footer{margin-top:30px;padding-top:14px;border-top:1px solid var(--line-soft);font-size:11.5px;
  color:var(--text-faint);line-height:1.7}
footer b{color:var(--text-dim)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
"""

JS = r"""
const POOL = __DATA__;
const META = __META__;

const BANDS = [
  {k:'b0', label:'Under 1%', lo:0, hi:1, c:'#DAD3C1', d:'#3A3F31'},
  {k:'b1', label:'1-3%',     lo:1, hi:3, c:'#A9BCE6', d:'#2C3B6B'},
  {k:'b2', label:'3-6%',     lo:3, hi:6, c:'#6E86D6', d:'#3F53A6'},
  {k:'b3', label:'6%+',      lo:6, hi:Infinity, c:'#3454D1', d:'#7C93F0'},
  {k:'bx', label:'No data',  lo:null, hi:null, c:'#C7C2B3', d:'#454A57'}
];
const METHODS = [{k:'profile_search', label:'Bio search'}, {k:'hashtag', label:'Hashtag'},
                  {k:'native', label:'Native search'}];
const state = {q:'', bands:new Set(), methods:new Set(), cross:false, clean:false,
               email:false, metric:'mean', sort:'er-desc'};

const erOf = r => state.metric === 'mean' ? r.engagement_rate : r.engagement_rate_median;
const likeOf = r => state.metric === 'median' ? r.median_likes : r.avg_likes;
const cmtOf = r => state.metric === 'median' ? r.median_comments : r.avg_comments;
const bandOf = r => { const v = erOf(r); if (v === null || v === undefined) return 'bx';
  return BANDS.find(b => b.lo !== null && v >= b.lo && v < b.hi).k; };
const fmt = n => n >= 1e6 ? (n/1e6).toFixed(n>=1e7?0:2).replace(/\.?0+$/,'')+'M'
              : n >= 1e3 ? (n/1e3).toFixed(n>=1e5?0:1).replace(/\.0$/,'')+'K' : String(Math.round(n));
const methodOf = s => s.split(':')[0];
function esc(s){ return String(s).replace(/[&<>"']/g, m =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
function host(u){ try { return new URL(u).hostname.replace(/^www\./,''); } catch(e){ return u; } }

POOL.forEach(r => {
  r.methods = [...new Set((r.sources||[]).map(methodOf))];
  r._hay = (r.handle + ' ' + (r.bio||'') + ' ' + (r.sources||[]).join(' ') + ' ' +
            ((r.contact && r.contact.emails) ? r.contact.emails.join(' ') : '')).toLowerCase();
  r._skewed = (r.top_post_vs_median || 0) >= 5;
});

function isDark(){
  const a = document.documentElement.getAttribute('data-theme');
  return a ? a === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
}
const bandColor = b => isDark() ? b.d : b.c;

function paintSummary(){
  const counts = {};
  BANDS.forEach(b => counts[b.k] = POOL.filter(r => bandOf(r) === b.k).length);
  document.getElementById('meter').innerHTML = BANDS.filter(b => counts[b.k] > 0)
    .map(b => `<div style="flex:${counts[b.k]};background:${bandColor(b)}" title="${b.label}: ${counts[b.k]}"></div>`).join('');
  document.getElementById('meterkey').innerHTML = BANDS.map(b =>
    `<button type="button" data-band="${b.k}" aria-pressed="${state.bands.size===0||state.bands.has(b.k)}">
       <span class="dot" style="background:${bandColor(b)}"></span>${b.label} <b>${counts[b.k]}</b>
     </button>`).join('');
}

function visible(){
  let rows = POOL.filter(r =>
    (!state.q || r._hay.includes(state.q)) &&
    (state.bands.size === 0 || state.bands.has(bandOf(r))) &&
    (state.methods.size === 0 || r.methods.some(m => state.methods.has(m))) &&
    (!state.cross || r.methods.length > 1) &&
    (!state.clean || !r._skewed) &&
    (!state.email || !!(r.contact && r.contact.emails.length)));
  const nn = v => (v === null || v === undefined) ? -1 : v;
  const cmp = {
    'er-desc': (a,b) => nn(erOf(b)) - nn(erOf(a)),
    'er-asc': (a,b) => nn(erOf(a)) - nn(erOf(b)),
    'followers-desc': (a,b) => b.follower_count - a.follower_count,
    'followers-asc': (a,b) => a.follower_count - b.follower_count,
    'recent-desc': (a,b) => a.days_since_last_post - b.days_since_last_post,
    'handle-asc': (a,b) => a.handle.localeCompare(b.handle),
  }[state.sort];
  return rows.sort(cmp);
}

function contactBlock(r){
  const c = r.contact;
  if (!c) return `<div class="contact"><span class="contact-label">Contact</span>
      <span class="cnone">Outside contact scope</span></div>`;
  const bits = [];
  c.emails.forEach(e => {
    const idx = (c.management_emails||[]).indexOf(e);
    const name = idx > -1 ? (c.management_names||[])[idx] : null;
    bits.push(`<span><a class="cmail" href="mailto:${esc(e)}">${esc(e)}</a>${
      name ? ` <span class="tag tag-managed">${esc(name)}</span>` : ''}</span>`);
  });
  if (c.business_contact) bits.push(`<span>${esc(c.business_contact_label||'contact')} <a href="${esc(c.business_contact)}" target="_blank" rel="noopener noreferrer">link</a></span>`);
  if (c.website) bits.push(`<span>site <a href="${esc(c.website)}" target="_blank" rel="noopener noreferrer">${esc(host(c.website))}</a></span>`);
  return `<div class="contact"><span class="contact-label">Contact</span>
    ${bits.length ? `<div class="contact-row">${bits.join('')}</div>` : `<span class="cnone">No public contact path found</span>`}</div>`;
}

function render(){
  const rows = visible();
  document.getElementById('shown').textContent = rows.length;
  document.getElementById('grid').innerHTML = rows.length ? rows.map(r => {
    const er = erOf(r), l = likeOf(r), c = cmtOf(r);
    const chips = (r.sources||[]).map(s => {
      const m = methodOf(s);
      const lab = m === 'profile_search' ? 'search' : m === 'hashtag' ? '#' : 'native';
      return `<span class="src src-${m}">${lab}</span>`;
    }).join('');
    return `<article class="card">
      <div class="card-top">
        <a class="handle" href="${esc(r.profile_url)}" target="_blank" rel="noopener noreferrer">${esc(r.handle)}</a>
        <div class="followers"><b>${fmt(r.follower_count)}</b><span>followers</span></div>
      </div>
      <div class="metrics">
        <div class="er"><b>${er===null||er===undefined?'-':er.toFixed(2)+'%'}</b><i>engagement</i></div>
        <div class="submetrics">
          <span>likes <span>${l===null||l===undefined?'-':fmt(l)}</span></span>
          <span>comments <span>${c===null||c===undefined?'-':fmt(c)}</span></span>
        </div>
      </div>
      <p class="bio">${esc(r.bio||'')}</p>
      <div class="cardfoot">
        <span class="recency${r.days_since_last_post<=7?' fresh':''}">${r.days_since_last_post}d ago</span>
        ${r._skewed ? `<span class="tag tag-skew">top post ${r.top_post_vs_median}x</span>` : ''}
        ${r.methods.length>1 ? `<span class="tag tag-cross">${r.methods.length} methods</span>` : ''}
        ${chips}
      </div>
      ${contactBlock(r)}
    </article>`;
  }).join('') : `<div class="empty" style="grid-column:1/-1">No creators match those filters.
      <button class="linkbtn" type="button" id="clearall">Clear filters</button></div>`;
  const cl = document.getElementById('clearall');
  if (cl) cl.onclick = clearAll;
}

function clearAll(){
  state.q=''; state.bands.clear(); state.methods.clear();
  state.cross=false; state.clean=false; state.email=false;
  document.getElementById('q').value=''; syncChips(); paintSummary(); render();
}
function syncChips(){
  document.querySelectorAll('[data-method]').forEach(b =>
    b.setAttribute('aria-pressed', state.methods.size===0 || state.methods.has(b.dataset.method)));
  document.getElementById('crossbtn').setAttribute('aria-pressed', state.cross);
  document.getElementById('cleanbtn').setAttribute('aria-pressed', state.clean);
  document.getElementById('emailbtn').setAttribute('aria-pressed', state.email);
  document.querySelectorAll('[data-metric]').forEach(b =>
    b.setAttribute('aria-pressed', b.dataset.metric === state.metric));
}

(function health(){
  const stale = META.stale||[], un = META.unavailable||[], oor = META.out_of_range||[];
  let html = `<div class="health-row"><span></span><span>Ranked below</span><b>${POOL.length}</b></div>`;
  if (oor.length) html += `<div class="health-row"><span></span><span>Outside follower range</span><b>${oor.length}</b></div>`;
  if (stale.length) html += `<div class="health-row"><span></span><span>Dropped, silent ${META.max_age_days}+ days</span><b>${stale.length}</b></div>`;
  if (un.length) html += `<div class="health-row"><span></span><span>No usable data</span><b>${un.length}</b></div>`;
  if (META.truncated_by_limit) html += `<div class="health-row"><span></span><span>Below the requested cutoff</span><b>${META.truncated_by_limit}</b></div>`;
  document.getElementById('health').innerHTML = html;
})();

document.getElementById('q').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); render(); });
document.getElementById('sort').addEventListener('change', e => { state.sort = e.target.value; render(); });
document.getElementById('meterkey').addEventListener('click', e => {
  const b = e.target.closest('[data-band]'); if (!b) return;
  const k = b.dataset.band;
  state.bands.has(k) ? state.bands.delete(k) : state.bands.add(k);
  if (state.bands.size === BANDS.length) state.bands.clear();
  paintSummary(); render();
});
document.querySelectorAll('[data-method]').forEach(b => b.addEventListener('click', () => {
  const k = b.dataset.method;
  state.methods.has(k) ? state.methods.delete(k) : state.methods.add(k);
  if (state.methods.size === METHODS.length) state.methods.clear();
  syncChips(); render();
}));
document.getElementById('crossbtn').addEventListener('click', () => { state.cross=!state.cross; syncChips(); render(); });
document.getElementById('cleanbtn').addEventListener('click', () => { state.clean=!state.clean; syncChips(); render(); });
document.getElementById('emailbtn').addEventListener('click', () => { state.email=!state.email; syncChips(); render(); });
document.querySelectorAll('[data-metric]').forEach(b => b.addEventListener('click', () => {
  state.metric = b.dataset.metric; syncChips(); render();
}));
document.getElementById('themebtn').addEventListener('click', () => {
  document.documentElement.setAttribute('data-theme', isDark() ? 'light' : 'dark');
  paintSummary(); render();
});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (!document.documentElement.getAttribute('data-theme')) { paintSummary(); render(); }
});
paintSummary(); syncChips(); render();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enriched", required=True)
    ap.add_argument("--meta")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Creator Pool")
    ap.add_argument("--platform", default="instagram")
    ap.add_argument("--niche", default="")
    ap.add_argument("--captured", default="")
    args = ap.parse_args()

    with open(args.enriched) as fh:
        rows = json.load(fh)
    meta = {}
    if args.meta and os.path.exists(args.meta):
        with open(args.meta) as fh:
            meta = json.load(fh)

    max_posts = max([r.get("posts_analyzed") or 0 for r in rows], default=10) or 10
    skewed = [r for r in rows if (r.get("top_post_vs_median") or 0) >= 5]
    hidden = [r for r in rows if r.get("likes_hidden_posts")]
    pinned = [r for r in rows if r.get("pinned_in_sample")]
    denom = "views" if args.platform == "tiktok" else "followers"
    rng = meta.get("follower_range") or [0, None]
    rng_txt = f"{rng[0]:,}-{rng[1]:,}" if rng[1] else f"{rng[0]:,}+"

    eyebrow = " . ".join(x for x in [args.platform, args.niche, "ranked by engagement"] if x)
    payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    metajson = json.dumps(meta, ensure_ascii=False).replace("</", "<\\/")

    notes = []
    if skewed:
        worst = max(skewed, key=lambda r: r["top_post_vs_median"])
        notes.append(f"Switch to median to see typical performance: {len(skewed)} of {len(rows)} "
                      f"creators here have a top post at least 5x their median. {worst['handle']} "
                      f"reads {worst['engagement_rate']}% on the mean and {worst['engagement_rate_median']}% "
                      f"on the median.")
    if hidden:
        notes.append(f"{len(hidden)} creators hide like counts on some posts, where a preview count was used.")
    if pinned:
        notes.append(f"Pinned posts appear in {len(pinned)} creators' samples; recency uses the newest "
                      f"post, not the first item in the grid.")

    body = f"""
<div class="wrap">
  <header>
    <div><p class="kicker">{eyebrow}</p><h1>{args.title}</h1></div>
    <div style="display:flex;align-items:center;gap:14px">
      <div class="count">{len(rows)}<span>creators</span></div>
      <button class="themebtn" id="themebtn" type="button">Theme</button>
    </div>
  </header>
  <section class="panels">
    <div>
      <p class="panel-label"><span>Engagement, click a band to filter</span></p>
      <div class="meter" id="meter"></div>
      <div class="meterkey" id="meterkey"></div>
    </div>
    <div>
      <p class="panel-label">Pool health - {meta.get('sourced', len(rows))} sourced . {rng_txt} followers</p>
      <div class="health" id="health"></div>
    </div>
  </section>
  <div class="controls">
    <label class="search"><input id="q" type="search" placeholder="Search handles, bios, emails..." aria-label="Search"></label>
    <div class="toggle" role="group" aria-label="Metric basis">
      <button type="button" data-metric="mean" aria-pressed="true">Mean</button>
      <button type="button" data-metric="median" aria-pressed="false">Median</button>
    </div>
    <div class="chips" style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="chip" type="button" data-method="profile_search">Bio search</button>
      <button class="chip" type="button" data-method="hashtag">Hashtag</button>
      <button class="chip" type="button" data-method="native">Native search</button>
      <button class="chip" type="button" id="crossbtn" aria-pressed="false">Found 2+ ways</button>
      <button class="chip" type="button" id="cleanbtn" aria-pressed="false">Hide spikes</button>
      <button class="chip" type="button" id="emailbtn" aria-pressed="false">Has email</button>
    </div>
    <select id="sort" aria-label="Sort">
      <option value="er-desc">Engagement, high to low</option>
      <option value="er-asc">Engagement, low to high</option>
      <option value="followers-desc">Followers, high to low</option>
      <option value="followers-asc">Followers, low to high</option>
      <option value="recent-desc">Most recently posted</option>
      <option value="handle-asc">Handle, A to Z</option>
    </select>
  </div>
  <div class="resultline"><span>Showing <b id="shown">{len(rows)}</b> of <b>{len(rows)}</b></span></div>
  <main class="grid" id="grid"></main>
  <footer>
    <b>Engagement = (avg likes + avg comments) / {denom}</b>, over each creator's last {max_posts} posts.
    {' '.join(notes)}<br>
    {'Captured ' + args.captured + '. ' if args.captured else ''}Ranked by engagement only, not vetted
    for brand fit, so off-topic and brand accounts matched by caption text may still appear.
  </footer>
</div>
"""

    doc = (f"<title>{args.title}</title>\n"
           '<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           f"<style>{CSS}</style>\n{body}\n"
           f"<script>{JS.replace('__DATA__', payload).replace('__META__', metajson)}</script>\n")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(doc)
    print(f"wrote {args.out} ({len(doc):,} bytes, {len(rows)} creators)")


if __name__ == "__main__":
    sys.exit(main())
