"""Write the gallery page of the 398 minimal forbidden unit-distance graphs from gallery_embed.py's output.

usage: python write_gallery.py GALLERY.json CERT_TYPES.json OUT.html

Refuses unless every drawing is genuine (every solid edge unit to 1e-35 after 50-digit refinement, points apart) and
the list is exactly 74 + 324 graphs. The page carries its data inline and draws the SVGs in the browser.
"""
import sys, json, collections

GAL, CT, OUT = sys.argv[1:4]
gal = json.load(open(GAL))["graphs"]
ctype = json.load(open(CT))
by_src = collections.Counter(g["source"] for g in gal)
if by_src != {"GP": 74, "L10": 324}:
    sys.exit(f"refusing: expected 74 GP + 324 L10 drawings, got {dict(by_src)}")
bad = [g["g6"] for g in gal if not g.get("genuine")]
if bad:
    sys.exit(f"refusing: {len(bad)} drawings are not genuine: {bad[:5]}")
missing = [g["g6"] for g in gal if g["g6"] not in ctype]
if missing:
    sys.exit(f"refusing: no certificate type for {missing[:5]}")

rows = []
for g in gal:
    rows.append({"g": g["g6"], "n": g["n"], "m": g["m"], "s": g["source"], "e": g["removed_edge"],
                 "p": [[round(x, 5), round(y, 5)] for x, y in g["coords"]], "l": g["dashed_length"],
                 "gap": g["min_gap"], "d": g["degrees"], "c": ctype[g["g6"]],
                 "E": None})
# edges from graph6, so the page needs no decoder
def edges(g6):
    n = ord(g6[0]) - 63
    bits = []
    for ch in g6[1:]:
        v = ord(ch) - 63
        bits += [(v >> (5 - i)) & 1 for i in range(6)]
    out, k = [], 0
    for j in range(1, n):
        for i in range(j):
            if bits[k]:
                out.append([i, j])
            k += 1
    return out
for r in rows:
    r["E"] = edges(r["g"])
    assert len(r["E"]) == r["m"]
counts = collections.Counter(r["n"] for r in rows)
data = json.dumps(rows, separators=(",", ":"))

PAGE = r"""<title>The 398 Forbidden Graphs</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=STIX+Two+Text:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --ground:#F3F4EF; --card:#FBFBF8; --ink:#1B1E23; --soft:#555C66; --rule:#D8DBD2; --edge:#22262D;
  --dash:#B26D00; --accent:#2D5B86; --chip:#E7E9E2; --chip-on:#1B1E23; --chip-on-ink:#F3F4EF; --shadow:0 1px 0 rgba(27,30,35,.06);
  --serif:"STIX Two Text","STIX Two","Times New Roman",Georgia,serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#13161A; --card:#1A1E23; --ink:#E7E9E4; --soft:#A2A8B0; --rule:#2B3137; --edge:#D8DCE1;
    --dash:#F0B040; --accent:#8FB6DE; --chip:#22272D; --chip-on:#E7E9E4; --chip-on-ink:#13161A; --shadow:none; color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --ground:#13161A; --card:#1A1E23; --ink:#E7E9E4; --soft:#A2A8B0; --rule:#2B3137; --edge:#D8DCE1;
  --dash:#F0B040; --accent:#8FB6DE; --chip:#22272D; --chip-on:#E7E9E4; --chip-on-ink:#13161A; --shadow:none; color-scheme:dark;
}
body{background:var(--ground);color:var(--ink);font-family:var(--serif);font-size:17px;line-height:1.5}
.wrap{max-width:1180px;margin:0 auto;padding-inline:clamp(16px,4vw,40px);padding-block:clamp(20px,5vw,48px) 56px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--soft)}
h1{font-weight:600;font-size:clamp(28px,4.6vw,46px);line-height:1.1;margin:.35em 0 .4em;text-wrap:balance;max-width:22ch}
.lede{max-width:64ch;color:var(--ink);margin:0 0 1.1em}
.head{display:grid;gap:8px 48px;align-items:center}
@media (min-width:920px){.head{grid-template-columns:minmax(0,1fr) 300px}}
.hero{margin:0;display:grid;gap:8px;justify-items:center;max-width:300px}
.hero svg{width:100%;max-width:300px;aspect-ratio:1/1;display:block}
.hero figcaption{font-size:14.5px;color:var(--soft);text-align:center;max-width:32ch}
.lede em{font-style:italic}
.legend{display:flex;flex-wrap:wrap;gap:10px 28px;align-items:center;font-size:15px;color:var(--soft);margin:0 0 26px}
.legend span{display:inline-flex;align-items:center;gap:10px}
.legend svg{width:46px;height:12px;overflow:visible}
.bar{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:center;justify-content:space-between;
  z-index:3;background:var(--ground);padding-block:12px;border-bottom:1px solid var(--rule)}
@media (min-width:760px){.bar{position:sticky;top:env(safe-area-inset-top,0px)}}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-family:var(--mono);font-size:13px;border:0;border-radius:999px;background:var(--chip);color:var(--ink);padding:6px 11px;cursor:pointer;font-variant-numeric:tabular-nums}
.chip b{font-weight:500;color:var(--soft);margin-left:6px}
.chip[aria-pressed="true"]{background:var(--chip-on);color:var(--chip-on-ink)}
.chip[aria-pressed="true"] b{color:var(--chip-on-ink);opacity:.75}
.chip:focus-visible,.card:focus-visible,.tools input:focus-visible,.tools select:focus-visible,.x:focus-visible,.copy:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tools{display:flex;gap:8px;flex-wrap:wrap}
.tools input,.tools select{font-family:var(--mono);font-size:13px;background:var(--card);color:var(--ink);border:1px solid var(--rule);border-radius:8px;padding:7px 10px}
.tools input{width:min(210px,52vw)}
.note{font-size:14px;color:var(--soft);margin:14px 0 18px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.card{all:unset;box-sizing:border-box;display:flex;flex-direction:column;gap:6px;background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:10px 10px 9px;cursor:pointer;box-shadow:var(--shadow)}
.card:hover{border-color:var(--soft)}
.card svg{width:100%;aspect-ratio:1/1;display:block}
.cap{display:flex;justify-content:space-between;gap:6px;font-family:var(--mono);font-size:11.5px;color:var(--soft);font-variant-numeric:tabular-nums}
.cap .g6{color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.new{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--dash)}
.empty{padding:40px 0;color:var(--soft)}
.sheet{position:fixed;inset:0;z-index:10;background:rgba(10,12,14,.55);display:flex;align-items:center;justify-content:center;padding:16px}
.panel{background:var(--card);color:var(--ink);border-radius:14px;max-width:880px;width:100%;max-height:calc(100% - 32px);overflow:auto;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:0}
.panel .big{padding:18px;border-right:1px solid var(--rule)}
.panel .big svg{width:100%;aspect-ratio:1/1;display:block}
.panel .info{padding:20px 22px;display:flex;flex-direction:column;gap:14px}
.panel h2{font-size:24px;font-weight:600;margin:0;font-family:var(--mono);word-break:break-all}
.panel dl{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;margin:0;font-size:15px}
.panel dt{color:var(--soft)}
.panel dd{margin:0;font-variant-numeric:tabular-nums}
.panel dd.m{font-family:var(--mono);font-size:13.5px}
.row{display:flex;gap:8px;align-items:center;justify-content:space-between}
.x,.copy{font-family:var(--mono);font-size:13px;background:var(--chip);color:var(--ink);border:0;border-radius:8px;padding:7px 11px;cursor:pointer}
.panel p{margin:0;font-size:15px;color:var(--soft)}
footer{margin-top:42px;padding-top:18px;border-top:1px solid var(--rule);font-size:14.5px;color:var(--soft);display:grid;gap:10px;max-width:78ch}
footer b{color:var(--ink);font-weight:600}
@media (max-width:700px){.panel{grid-template-columns:1fr}.panel .big{border-right:0;border-bottom:1px solid var(--rule)}}
@media (prefers-reduced-motion:no-preference){.card{transition:border-color .15s}}
</style>
<div class="wrap">
  <div class="head"><div>
  <div class="eyebrow">Minimal forbidden unit-distance graphs &middot; up to ten vertices</div>
  <h1>398 graphs that cannot be drawn with every edge of length&nbsp;1</h1>
  <p class="lede">A graph is a <em>unit-distance graph</em> if its vertices can be placed at distinct points of the plane with every edge exactly one unit long; other pairs may be any distance apart. None of the graphs below is one, yet each becomes one the moment any single edge is removed: they are the <em>minimal</em> forbidden graphs, and this is all of them up to ten vertices. So each is drawn with every edge at length 1 but one. The dashed edge is the one that cannot be.</p>
  <div class="legend">
    <span><svg viewBox="0 0 46 12" aria-hidden="true"><line x1="2" y1="6" x2="44" y2="6" stroke="var(--edge)" stroke-width="1.6"/></svg>length 1</span>
    <span><svg viewBox="0 0 46 12" aria-hidden="true"><line x1="2" y1="6" x2="44" y2="6" stroke="var(--dash)" stroke-width="2.2" stroke-dasharray="6 4"/></svg>the edge that cannot be length 1, with its length &#8467;</span>
  </div>
  </div>
  <figure class="hero" id="hero"><div id="heroart"></div><figcaption>K<sub>4</sub>, the smallest. Five of its six edges can be length 1 at once, as two equilateral triangles; the sixth is then &radic;3 &asymp; 1.732.</figcaption></figure>
  </div>
  <div class="bar">
    <div class="chips" id="chips" role="group" aria-label="Filter by number of vertices"></div>
    <div class="tools">
      <input id="q" type="search" placeholder="find a graph6 string" aria-label="Find a graph by its graph6 string" autocomplete="off" spellcheck="false">
      <select id="sort" aria-label="Sort">
        <option value="order">sort: vertices, edges</option>
        <option value="long">sort: longest dashed edge</option>
        <option value="short">sort: dashed edge nearest 1</option>
      </select>
    </div>
  </div>
  <p class="note" id="note"></p>
  <div class="grid" id="grid"></div>
  <footer>
    <div><b>Where the list comes from.</b> The 74 graphs on four to nine vertices are Globus and Parshall's (2019). The 324 on ten vertices were determined in September 2026 by the Artificial Wasteland: every one of the 33,162 candidate graphs carries a checkable certificate, either an exact embedding or a proof that none exists, all accepted by an independent checker, and the 324 refutations were accepted again by a second verifier written separately from the specification.</div>
    <div><b>How the drawings were made.</b> For each graph and each edge, many unit-distance drawings of the graph without that edge were found numerically and the most legible kept (points and edges well apart), then refined at 50 digits: every solid edge has length 1 to within 10<sup>&minus;35</sup>. The dashed length is that drawing's; where the drawing can flex, other drawings give other lengths, never exactly 1.</div>
  </footer>
</div>
<div class="sheet" id="sheet" hidden>
  <div class="panel" role="dialog" aria-modal="true" aria-labelledby="dt">
    <div class="big" id="big"></div>
    <div class="info">
      <div class="row"><span class="eyebrow" id="dsrc"></span><button class="x" id="close">Close</button></div>
      <h2 id="dt"></h2>
      <dl id="dl"></dl>
      <div class="row"><p id="dnote"></p></div>
      <button class="copy" id="copy">Copy graph6</button>
    </div>
  </div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
  var ROWS = JSON.parse(document.getElementById('data').textContent);
  var CERT = {tree:'proof tree (the AMP calculus)', tu:'a rigid gadget forces a unit distance the graph lacks',
    'null':'Nullstellensatz identity', 'null-dag':'Nullstellensatz identity, derived in rows',
    real:'real-algebraic certificate (Sturm or sum of squares)', 'real-dag':'real-algebraic certificate, derived in rows'};
  var state = {n:'all', q:'', sort:'order'};
  try { var s = JSON.parse(localStorage.getItem('fg398') || '{}'); if (s.n) state.n = s.n; if (s.sort) state.sort = s.sort; } catch(e) {}
  var grid = document.getElementById('grid'), note = document.getElementById('note');
  function svg(r, big){
    var xs = r.p.map(function(p){return p[0]}), ys = r.p.map(function(p){return -p[1]});
    var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs), miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
    var span = Math.max(maxx - minx, maxy - miny, 1), pad = span * (big ? .16 : .1), side = span + 2 * pad;
    var cx = (minx + maxx) / 2, cy = (miny + maxy) / 2, x0 = cx - side / 2, y0 = cy - side / 2;
    var rad = side * (big ? .018 : .026), dash = side * (big ? .03 : .045);
    var out = ['<svg viewBox="' + [x0, y0, side, side].map(function(v){return v.toFixed(4)}).join(' ') + '" role="img" aria-label="Drawing of ' + r.g + '">'];
    var ru = r.e[0], rv = r.e[1];
    r.E.forEach(function(e){
      if ((e[0] === ru && e[1] === rv) || (e[0] === rv && e[1] === ru)) return;
      out.push('<line x1="' + xs[e[0]] + '" y1="' + ys[e[0]] + '" x2="' + xs[e[1]] + '" y2="' + ys[e[1]] + '" stroke="var(--edge)" stroke-width="' + (big ? 1.5 : 1.3) + '" vector-effect="non-scaling-stroke" stroke-linecap="round"/>');
    });
    out.push('<line x1="' + xs[ru] + '" y1="' + ys[ru] + '" x2="' + xs[rv] + '" y2="' + ys[rv] + '" stroke="var(--dash)" stroke-width="' + (big ? 2.4 : 2) + '" vector-effect="non-scaling-stroke" stroke-dasharray="' + (dash * 1.2).toFixed(4) + ' ' + dash.toFixed(4) + '" stroke-linecap="butt"/>');
    r.p.forEach(function(p, i){
      out.push('<circle cx="' + xs[i] + '" cy="' + ys[i] + '" r="' + rad.toFixed(4) + '" fill="var(--edge)"/>');
      if (big) out.push('<text x="' + (xs[i] + rad * 1.4).toFixed(4) + '" y="' + (ys[i] - rad * 1.4).toFixed(4) + '" font-size="' + (side * .032).toFixed(4) + '" fill="var(--soft)" font-family="IBM Plex Mono, monospace">' + i + '</text>');
    });
    if (big) {
      var mx = (xs[ru] + xs[rv]) / 2, my = (ys[ru] + ys[rv]) / 2;
      out.push('<text x="' + (mx + rad * 1.5).toFixed(4) + '" y="' + (my + rad * 3.5).toFixed(4) + '" font-size="' + (side * .04).toFixed(4) + '" fill="var(--dash)" font-family="IBM Plex Mono, monospace">ℓ = ' + r.l.toFixed(4) + '</text>');
    }
    out.push('</svg>');
    return out.join('');
  }
  function chips(){
    var counts = {}; ROWS.forEach(function(r){ counts[r.n] = (counts[r.n] || 0) + 1; });
    var keys = ['all'].concat(Object.keys(counts).sort(function(a, b){return a - b}));
    document.getElementById('chips').innerHTML = keys.map(function(k){
      var label = k === 'all' ? 'all' : k + ' vertices', num = k === 'all' ? ROWS.length : counts[k];
      return '<button class="chip" data-n="' + k + '" aria-pressed="' + (String(state.n) === k) + '">' + label + '<b>' + num + '</b></button>';
    }).join('');
  }
  function render(){
    var q = state.q.trim();
    var rows = ROWS.filter(function(r){ return (state.n === 'all' || String(r.n) === String(state.n)) && (!q || r.g.indexOf(q) !== -1); });
    rows.sort(function(a, b){
      if (state.sort === 'long') return b.l - a.l;
      if (state.sort === 'short') return Math.abs(a.l - 1) - Math.abs(b.l - 1);
      return a.n - b.n || a.m - b.m || (a.g < b.g ? -1 : 1);
    });
    note.textContent = rows.length === ROWS.length ? 'All 398, the 74 on four to nine vertices first. Tap a drawing for its details.' :
      rows.length + ' of 398 shown.' + (q && !rows.length ? ' No graph6 string contains “' + q + '”.' : '');
    grid.innerHTML = rows.length ? rows.map(function(r){
      return '<button class="card" data-g="' + r.g.replace(/"/g, '&quot;') + '" aria-label="' + r.n + ' vertices, ' + r.m + ' edges, graph6 ' + r.g.replace(/"/g, '&quot;') + '">' + svg(r, false) +
        '<span class="cap"><span class="g6">' + r.g.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</span><span>' + r.n + '·' + r.m + '</span></span>' +
        '<span class="cap"><span>ℓ = ' + r.l.toFixed(3) + '</span>' + (r.s === 'L10' ? '<span class="new">new</span>' : '<span>GP</span>') + '</span></button>';
    }).join('') : '<div class="empty">Nothing matches. Clear the search box or pick another vertex count.</div>';
  }
  var BYG = {}; ROWS.forEach(function(r){ BYG[r.g] = r; });
  var sheet = document.getElementById('sheet'), current = null, lastFocus = null;
  function open(g){
    var r = BYG[g]; if (!r) return; current = r; lastFocus = document.activeElement;
    document.getElementById('big').innerHTML = svg(r, true);
    document.getElementById('dt').textContent = r.g;
    document.getElementById('dsrc').textContent = r.s === 'L10' ? 'ten vertices · new in 2026' : 'Globus & Parshall, 2019';
    var rows = [['vertices', r.n], ['edges', r.m], ['degrees', r.d.join(' ')], ['dashed edge', r.e[0] + '–' + r.e[1]],
      ['its length', r.l.toFixed(10)], ['closest points', r.gap.toFixed(4)], ['why it is forbidden', CERT[r.c] || r.c]];
    document.getElementById('dl').innerHTML = rows.map(function(x, i){ return '<dt>' + x[0] + '</dt><dd' + (i < 5 ? ' class="m"' : '') + '>' + String(x[1]).replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</dd>'; }).join('');
    document.getElementById('dnote').textContent = 'Remove any one edge and the rest can be drawn with every edge of length 1; this drawing removes ' + r.e[0] + '–' + r.e[1] + '.';
    document.getElementById('copy').textContent = 'Copy graph6';
    sheet.hidden = false; document.getElementById('close').focus();
  }
  function close(){ sheet.hidden = true; current = null; if (lastFocus) lastFocus.focus(); }
  document.getElementById('chips').addEventListener('click', function(ev){
    var b = ev.target.closest('.chip'); if (!b) return; state.n = b.getAttribute('data-n'); save(); chips(); render();
  });
  document.getElementById('q').addEventListener('input', function(ev){ state.q = ev.target.value; render(); });
  document.getElementById('sort').addEventListener('change', function(ev){ state.sort = ev.target.value; save(); render(); });
  grid.addEventListener('click', function(ev){ var c = ev.target.closest('.card'); if (c) open(c.getAttribute('data-g')); });
  document.getElementById('close').addEventListener('click', close);
  sheet.addEventListener('click', function(ev){ if (ev.target === sheet) close(); });
  document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape' && !sheet.hidden) close(); });
  document.getElementById('copy').addEventListener('click', function(ev){
    if (!current) return; var btn = ev.currentTarget, text = current.g;
    function fallback(){ btn.textContent = text; var r = document.createRange(); r.selectNodeContents(btn); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); }
    try { navigator.clipboard.writeText(text).then(function(){ btn.textContent = 'Copied'; }, fallback); } catch(e) { fallback(); }
  });
  function save(){ try { localStorage.setItem('fg398', JSON.stringify({n: state.n, sort: state.sort})); } catch(e) {} }
  document.getElementById('sort').value = state.sort;
  var k4 = ROWS.filter(function(r){ return r.n === 4; })[0];
  if (k4) document.getElementById('heroart').innerHTML = svg(k4, true).replace(/\u2113 = [0-9.]+/, '\u2113 = \u221a3');
  chips(); render();
})();
</script>
"""
html = PAGE.replace("__DATA__", data.replace("</", "<\\/"))
open(OUT, "w").write(html)
print("wrote", OUT, len(html), "bytes;", dict(sorted(counts.items())))
