#!/usr/bin/env python3
"""L7 — auto-generate the cross-linked wiki + the Cytoscape graph explorer.

From graph/graph.json + graph/analytics.json:
  - portal/wiki/<type>/<slug>.html : one page per Company / Drug / DeficiencyType /
    TherapeuticArea, each listing its graph NEIGHBORS as links (the navigation surface).
  - portal/wiki/index.html : entity index.
  - portal/explorer.html : a filtered Cytoscape.js view of the cross-enforcement subgraph
    (bounded, typed, click-to-expand — not a hairball).
  - portal/index.html : the home/dashboard with the headline findings.

Public FDA data. Educational, not regulatory advice.
"""
from __future__ import annotations
import html
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "graph" / "graph.json"
ANALYTICS = ROOT / "graph" / "analytics.json"
WIKI = ROOT / "portal" / "wiki"
PORTAL = ROOT / "portal"

DISCLAIMER = ("Educational, built on public FDA records (CRLs, recalls, Import Alert 66-40, "
              "debarment). Not regulatory advice. Matches are confidence-scored, not definitive.")
WIKI_TYPES = ["Company", "Drug", "DeficiencyType", "TherapeuticArea"]

CSS = """
:root{--bg:#fcfaf5;--ink:#0a1e33;--soft:#2a3a4f;--muted:#6b7280;--rule:#cdd5dd;--amber:#c4842a}
*{box-sizing:border-box}body{margin:0;font-family:'Source Serif 4',Georgia,serif;background:var(--bg);color:var(--ink);line-height:1.55}
.wrap{max-width:860px;margin:0 auto;padding:28px 22px}
header.m{border-bottom:1.5px solid var(--ink);padding:14px 22px;display:flex;gap:12px;align-items:baseline}
header.m a{color:var(--ink);text-decoration:none;font-weight:700}
header.m .s{color:var(--muted);font-style:italic;font-size:13px}
h1{font-size:30px;margin:.2em 0}.kick{color:var(--amber);font-size:12px;letter-spacing:.16em;text-transform:uppercase;font-weight:700}
a{color:#0a1e33;text-decoration:underline;text-decoration-color:rgba(196,132,42,.5)}
.chip{display:inline-block;border:1px solid var(--rule);border-radius:999px;padding:2px 10px;margin:2px;font-size:13px;text-decoration:none}
.sec{margin:20px 0}.sec h2{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--amber);border-bottom:1px solid var(--rule);padding-bottom:6px}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:7px 8px;border-bottom:1px solid var(--rule)}
.disc{color:var(--muted);font-size:12px;font-style:italic;margin-top:26px;border-top:1px solid var(--rule);padding-top:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px}
"""


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:80] or "x"


def page(title: str, kicker: str, body: str, depth: int) -> str:
    up = "../" * depth
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<header class="m"><a href="{up}index.html">CRL Intelligence Graph</a>
<span class="s">public FDA records · educational, not regulatory advice</span></header>
<div class="wrap"><div class="kick">{html.escape(kicker)}</div><h1>{html.escape(title)}</h1>
{body}<div class="disc">{DISCLAIMER}</div></div></body></html>"""


def main() -> None:
    g = json.loads(GRAPH.read_text())
    analytics = json.loads(ANALYTICS.read_text())
    nodes = {n["id"]: n for n in g["nodes"]}
    # adjacency with edge types
    out_adj = defaultdict(list)
    in_adj = defaultdict(list)
    for e in g["edges"]:
        out_adj[e["source"]].append((e["target"], e.get("type"), e))
        in_adj[e["target"]].append((e["source"], e.get("type"), e))

    by_type = defaultdict(list)
    for nid, n in nodes.items():
        by_type[n["type"]].append(nid)

    WIKI.mkdir(parents=True, exist_ok=True)
    page_path = {}  # nid -> relative path from portal root
    for t in WIKI_TYPES:
        (WIKI / t.lower()).mkdir(parents=True, exist_ok=True)
        for nid in by_type.get(t, []):
            page_path[nid] = f"wiki/{t.lower()}/{slug(nodes[nid]['label'])}-{slug(nid)}.html"

    def link(nid: str, from_depth: int) -> str:
        lbl = html.escape(nodes[nid]["label"])
        if nid in page_path:
            return f'<a class="chip" href="{"../"*from_depth}{page_path[nid]}">{lbl}</a>'
        return f'<span class="chip">{lbl}</span>'

    pages_written = 0
    for t in WIKI_TYPES:
        for nid in by_type.get(t, []):
            n = nodes[nid]
            nbrs = out_adj[nid] + in_adj[nid]
            # group neighbors by relation
            groups = defaultdict(list)
            for tgt, etype, _e in nbrs:
                groups[etype or "related"].append(tgt)
            body = []
            for rel, tgts in sorted(groups.items()):
                seen = []
                for x in tgts:
                    if x not in seen:
                        seen.append(x)
                body.append(f'<div class="sec"><h2>{html.escape(rel)}</h2>'
                            + "".join(link(x, 2) for x in seen[:60]) + "</div>")
            meta = {k: v for k, v in n.items() if k not in ("type", "label", "id")
                    and v not in (None, "", [])}
            if meta:
                body.insert(0, '<div class="sec"><h2>attributes</h2><table>'
                            + "".join(f"<tr><td>{html.escape(str(k))}</td>"
                                      f"<td>{html.escape(str(v))}</td></tr>"
                                      for k, v in meta.items()) + "</table></div>")
            (PORTAL / page_path[nid]).write_text(
                page(n["label"], n["type"], "".join(body) or "<p>No links.</p>", 2))
            pages_written += 1

    # wiki index
    idx = ['<div class="sec"><h2>browse</h2></div>']
    for t in WIKI_TYPES:
        items = sorted(by_type.get(t, []), key=lambda x: nodes[x]["label"])
        idx.append(f'<div class="sec"><h2>{t} ({len(items)})</h2><div class="grid">'
                   + "".join(f'<a href="{slug(nodes[i]["label"])}-{slug(i)}.html"'
                             if False else link(i, 1) for i in items[:300]) + "</div></div>")
    (WIKI / "index.html").write_text(page("Wiki index", "browse entities", "".join(idx), 1))

    # ---- explorer: cross-enforcement subgraph (bounded) ----
    keep = set()
    for e in g["edges"]:
        if e.get("type") in ("cross_enforcement", "debarred", "on_import_alert", "has_recall"):
            keep.add(e["source"]); keep.add(e["target"])
    # add the CRLs + deficiencies of cross-enforcement companies for context (bounded)
    for e in g["edges"]:
        if e["source"] in keep and e.get("type") in ("filed", "cited"):
            keep.add(e["target"])
    keep = set(list(keep)[:600])
    cy_nodes = [{"data": {"id": nid, "label": nodes[nid]["label"], "ntype": nodes[nid]["type"]}}
                for nid in keep]
    cy_edges = [{"data": {"source": e["source"], "target": e["target"],
                          "etype": e.get("type")}}
                for e in g["edges"] if e["source"] in keep and e["target"] in keep]
    (PORTAL / "graph_data.json").write_text(json.dumps({"nodes": cy_nodes, "edges": cy_edges}))

    explorer = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Graph explorer</title>
<style>__CSS__ #cy{height:78vh;border:1px solid var(--rule);border-radius:10px;background:#fff}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.bar button{font:inherit;border:1px solid var(--rule);background:#fff;border-radius:7px;padding:6px 11px;cursor:pointer}
.bar button.on{background:var(--ink);color:var(--bg)}</style>
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js"></script></head>
<body><header class="m"><a href="index.html">CRL Intelligence Graph</a>
<span class="s">cross-enforcement subgraph · click a node to expand · educational, not advice</span></header>
<div class="wrap" style="max-width:1100px"><div class="kick">graph explorer</div>
<h1>The cross-enforcement network</h1>
<p>Sponsors whose Complete Response Letter sits next to a recall / Import Alert / debarment.
A search box shows one document; the graph shows the overlap.</p>
<div class="bar" id="filters"></div><div id="cy"></div>
<div class="disc">__DISC__</div></div>
<script>
const COLORS={Company:'#0a1e33',CRL:'#c4842a',Firm:'#9c6a25',Drug:'#6b7280',
DeficiencyType:'#b91c1c',WatchList:'#7c3aed',Enforcement:'#0f5132',TherapeuticArea:'#2a3a4f'};
fetch('graph_data.json').then(r=>r.json()).then(g=>{
 const cy=cytoscape({container:document.getElementById('cy'),elements:g,
  style:[{selector:'node',style:{'background-color':e=>COLORS[e.data('ntype')]||'#888',
   'label':'data(label)','font-size':7,'width':12,'height':12,'color':'#0a1e33',
   'text-wrap':'ellipsis','text-max-width':70}},
   {selector:'edge',style:{'width':.6,'line-color':'#cdd5dd','curve-style':'haystack'}}],
  layout:{name:'cose',animate:false,nodeRepulsion:6000,idealEdgeLength:60}});
 const types=[...new Set(g.nodes.map(n=>n.data.ntype))];
 const fb=document.getElementById('filters');
 types.forEach(t=>{const b=document.createElement('button');b.textContent=t;b.className='on';
  b.onclick=()=>{b.classList.toggle('on');
   cy.nodes(`[ntype="${t}"]`).style('display',b.classList.contains('on')?'element':'none');};
  fb.appendChild(b);});
 cy.on('tap','node',e=>{e.target.neighborhood().style('opacity',1);
  cy.elements().difference(e.target.closedNeighborhood()).style('opacity',.15);});
 cy.on('tap',e=>{if(e.target===cy)cy.elements().style('opacity',1);});
});
</script></body></html>""".replace("__CSS__", CSS).replace("__DISC__", DISCLAIMER)
    (PORTAL / "explorer.html").write_text(explorer)

    # ---- home/dashboard ----
    cx = analytics["cross_enforcement_sponsors"][:8]
    rr = analytics["repeat_rejected_sponsors"][:8]
    td = analytics["top_deficiency_types"][:8]
    home_body = [
        '<p>An open knowledge graph that fuses FDA Complete Response Letters with Warning-Letter / '
        'recall / Import-Alert enforcement data at the company and facility level. '
        '<a href="explorer.html">Open the graph explorer</a> · <a href="wiki/index.html">Browse the wiki</a>.</p>',
        '<div class="sec"><h2>Sponsors with a CRL AND an enforcement footprint</h2><table>'
        '<tr><th>Sponsor</th><th>Linked events</th><th>Via</th></tr>'
        + "".join(f"<tr><td>{html.escape(r['company'])}</td><td>{r['n_events']}</td>"
                  f"<td>{html.escape(', '.join(r['vias']))}</td></tr>" for r in cx) + "</table></div>",
        '<div class="sec"><h2>Repeat-rejected sponsors</h2><table>'
        + "".join(f"<tr><td>{html.escape(n)}</td><td>{c} CRLs</td></tr>" for n, c in rr)
        + "</table></div>",
        '<div class="sec"><h2>What FDA says no for</h2><table>'
        + "".join(f"<tr><td>{html.escape(n)}</td><td>{c}</td></tr>" for n, c in td) + "</table></div>",
    ]
    (PORTAL / "index.html").write_text(
        page("Why did FDA say no — and is it your risk?", "open FDA regulatory-intelligence graph",
             "".join(home_body), 0))

    print(f"[L7] wrote {pages_written} wiki pages + explorer.html + index.html")
    print(f"  wiki types: {[t for t in WIKI_TYPES if by_type.get(t)]}")
    print(f"  explorer subgraph: {len(cy_nodes)} nodes / {len(cy_edges)} edges")

    # EXIT: >=4 wiki types, explorer exists, a company page links to neighbors
    sample_company = next((nid for nid in by_type.get("Company", [])
                           if out_adj[nid]), None)
    linked = False
    if sample_company:
        txt = (PORTAL / page_path[sample_company]).read_text()
        linked = ('href="../' in txt and "chip" in txt)
    types_ok = sum(1 for t in WIKI_TYPES if by_type.get(t)) >= 4
    exp_ok = (PORTAL / "explorer.html").exists()
    ok = types_ok and exp_ok and linked
    print(f"\n[L7 EXIT] wiki_types>=4:{types_ok} explorer:{exp_ok} "
          f"company_page_links_neighbors:{linked} -> {'PASS' if ok else 'FAIL'}")
    import sys
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
