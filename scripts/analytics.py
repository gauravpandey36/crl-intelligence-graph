#!/usr/bin/env python3
"""L4 — cascade + centrality analytics over the knowledge graph.

Produces graph/analytics.json and docs/FINDING_cascade.md:
  - top risk-hub nodes (degree centrality on companies/firms)
  - repeat-rejected sponsors (multiple CRLs)
  - cross-enforcement sponsors (a CRL AND recalls/watch-list footprint) -- the headline
  - dominant deficiency types + per-therapeutic-area deficiency fingerprint

Public FDA data; educational, not regulatory advice.
"""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "graph" / "graph.json"
OUT = ROOT / "graph" / "analytics.json"
FINDING = ROOT / "docs" / "FINDING_cascade.md"


def main() -> None:
    import networkx as nx
    g = json.loads(GRAPH.read_text())
    G = nx.MultiDiGraph()
    for n in g["nodes"]:
        G.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
    for e in g["edges"]:
        G.add_edge(e["source"], e["target"], **{k: v for k, v in e.items()
                                                 if k not in ("source", "target")})

    def label(nid):
        return G.nodes[nid].get("label", nid)

    # --- repeat-rejected sponsors (companies with >1 CRL) ---
    crl_by_company = defaultdict(list)
    for u, v, d in G.edges(data=True):
        if d.get("type") == "filed":
            crl_by_company[u].append(v)
    repeat_rejected = sorted(
        [(label(c), len(v)) for c, v in crl_by_company.items() if len(v) > 1],
        key=lambda x: -x[1])[:15]

    # --- cross-enforcement sponsors (CRL + recalls/watchlist) — the headline ---
    cross = []
    for u, v, d in G.edges(data=True):
        if d.get("type") in ("cross_enforcement", "debarred"):
            cross.append((label(u), d.get("via", d.get("type")), d.get("confidence")))
    cross_by_company = defaultdict(list)
    for comp, via, conf in cross:
        cross_by_company[comp].append((via, conf))
    cross_enforcement = sorted(
        [{"company": c, "n_events": len(v), "vias": sorted({x[0] for x in v})}
         for c, v in cross_by_company.items()],
        key=lambda x: -x["n_events"])[:15]

    # --- dominant deficiency types ---
    defc = Counter()
    for u, v, d in G.edges(data=True):
        if d.get("type") == "cited":
            defc[label(v)] += 1
    top_deficiencies = defc.most_common(12)

    # --- per-therapeutic-area deficiency fingerprint ---
    # CRL -> area, CRL -> deficiency
    crl_area = {}
    crl_def = defaultdict(list)
    for u, v, d in G.edges(data=True):
        if d.get("type") == "in_area":
            crl_area[u] = label(v)
        if d.get("type") == "cited":
            crl_def[u].append(label(v))
    area_def = defaultdict(Counter)
    for crl, area in crl_area.items():
        for dd in crl_def.get(crl, []):
            area_def[area][dd] += 1
    fingerprint = {area: c.most_common(3) for area, c in
                   sorted(area_def.items(), key=lambda x: -sum(x[1].values()))[:8]}

    # --- degree-centrality risk hubs (company/firm nodes) ---
    deg = nx.degree_centrality(G)
    hubs = sorted(
        [(label(n), round(deg[n], 4), G.degree(n)) for n, d in G.nodes(data=True)
         if d.get("type") in ("Company", "Firm")],
        key=lambda x: -x[2])[:12]

    analytics = {
        "totals": {"nodes": G.number_of_nodes(), "edges": G.number_of_edges()},
        "repeat_rejected_sponsors": repeat_rejected,
        "cross_enforcement_sponsors": cross_enforcement,
        "top_deficiency_types": top_deficiencies,
        "therapeutic_area_fingerprint": fingerprint,
        "risk_hubs": hubs,
        "disclaimer": "Educational, public FDA records. Not regulatory advice. "
                      "Cross-enforcement matches are confidence-scored, not definitive.",
    }
    OUT.write_text(json.dumps(analytics, indent=2))

    # --- the finding writeup ---
    md = ["# Finding: cross-enforcement and shared-risk patterns in FDA CRLs",
          "",
          "*Educational, built on public FDA records (CRLs + recalls + Import Alert 66-40 + "
          "debarment). Not regulatory advice. Company-level matches are confidence-scored.*",
          "",
          f"Graph: **{G.number_of_nodes()} nodes, {G.number_of_edges()} edges**.",
          "",
          "## The headline a search box can't give: sponsors whose rejection sits next to an enforcement footprint",
          "These companies received a Complete Response Letter AND independently appear in FDA "
          "recalls / the Import Alert 66-40 red list / the debarment list. A document-by-document "
          "search shows you one or the other; the graph shows the overlap.",
          "",
          "| Sponsor | Linked enforcement events | Via |",
          "|---|---:|---|"]
    for r in cross_enforcement[:10]:
        md.append(f"| {r['company']} | {r['n_events']} | {', '.join(r['vias'])} |")
    md += ["",
           "## Repeat-rejected sponsors (more than one CRL)",
           "| Sponsor | CRLs |", "|---|---:|"]
    for name, n in repeat_rejected[:10]:
        md.append(f"| {name} | {n} |")
    md += ["",
           "## What FDA says no for (deficiency dominance)",
           "| Deficiency type | CRLs citing it |", "|---|---:|"]
    for name, n in top_deficiencies[:10]:
        md.append(f"| {name} | {n} |")
    md += ["",
           "## Therapeutic-area failure fingerprints",
           "The dominant rejection reasons differ by area:"]
    for area, items in fingerprint.items():
        md.append(f"- **{area}**: " + ", ".join(f"{d} ({n})" for d, n in items))
    md += ["",
           "## Risk hubs (most-connected company/firm nodes)",
           "| Node | Degree |", "|---|---:|"]
    for name, _c, deg_n in hubs[:10]:
        md.append(f"| {name} | {deg_n} |")
    md += ["",
           "*Limits: most CRLs redact the manufacturing facility, so company-level matching is "
           "the honest resolution; absence of a match is not a clean bill. Import-Alert/recall "
           "matches are name-based (lower confidence than an FEI join). This is lead-generation "
           "for due diligence, not a compliance determination.*"]
    FINDING.write_text("\n".join(md) + "\n")

    print(f"[L4] wrote {OUT} and {FINDING}")
    print(f"  cross-enforcement sponsors: {len(cross_enforcement)} "
          f"(top: {cross_enforcement[0]['company']} / {cross_enforcement[0]['n_events']} events)"
          if cross_enforcement else "  (none)")
    print(f"  repeat-rejected sponsors: {len(repeat_rejected)} "
          f"(top: {repeat_rejected[0]})" if repeat_rejected else "")
    print(f"  top deficiency: {top_deficiencies[0] if top_deficiencies else '-'}")
    print(f"  risk hubs: {hubs[0][0]} (deg {hubs[0][2]})" if hubs else "")

    ok = (len(cross_enforcement) >= 1 and len(top_deficiencies) >= 3
          and FINDING.exists() and OUT.exists())
    print(f"\n[L4 EXIT] cross_enforcement>=1:{len(cross_enforcement)>=1} "
          f"deficiencies>=3:{len(top_deficiencies)>=3} finding_written:{FINDING.exists()} "
          f"-> {'PASS' if ok else 'FAIL'}")
    import sys
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
