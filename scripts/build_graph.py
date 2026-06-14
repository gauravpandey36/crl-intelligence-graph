#!/usr/bin/env python3
"""L3 — entity resolution + the typed knowledge graph.

Unifies CRL sponsors with FDA enforcement firms (recalls, Import Alert 66-40 red
list, debarment) via canonical-name resolution (confidence-scored, never auto-
asserted), and builds a typed NetworkX graph:

  nodes : Company, Drug, CRL, DeficiencyType, TherapeuticArea, Firm(enforcement)
  edges : filed, for_drug, cited, in_area, has_recall, on_import_alert, debarred,
          cross_enforcement (the load-bearing CRL<->enforcement bridge, scored)

Emits graph/graph.json. Public FDA data; educational, not regulatory advice.
"""
from __future__ import annotations
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRL = ROOT / "data" / "crl_entities.json"
ENF = ROOT / "enforcement"
OUT = ROOT / "graph" / "graph.json"

SUFFIXES = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|co|company|plc|"
    r"pharmaceuticals?|pharma|therapeutics?|laboratories|labs?|gmbh|ag|sa|s\.a|nv|n\.v|"
    r"pvt|private|holdings?|group|usa|us|international|biosciences?|biologics?|sciences?)\b",
    re.IGNORECASE)


def canon(name: str) -> str:
    if not name:
        return ""
    s = name.lower()
    s = re.sub(r"\(.*?\)", " ", s)            # drop parentheticals
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = SUFFIXES.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def split_deficiencies(types: list[str]) -> list[str]:
    out = []
    for t in types:
        for part in re.split(r"\s*&\s*|/", t):
            p = part.strip()
            if p:
                out.append(p)
    # dedupe preserve order
    seen, res = set(), []
    for p in out:
        if p.lower() not in seen:
            seen.add(p.lower()); res.append(p)
    return res


def fuzzy(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def main() -> None:
    import networkx as nx
    crls = json.loads(CRL.read_text())
    recalls = json.loads((ENF / "recalls.json").read_text())
    import_alert = json.loads((ENF / "import_alert_6640.json").read_text())
    debarment = json.loads((ENF / "debarment.json").read_text())

    G = nx.MultiDiGraph()

    def add(nid, ntype, label, **kw):
        if not G.has_node(nid):
            G.add_node(nid, type=ntype, label=label, **kw)

    # ---- CRL core ----------------------------------------------------------
    crl_company_canon = {}     # canon -> company node id
    for c in crls:
        crl_id = c["crl_id"]
        comp = c["company"]
        ck = canon(comp)
        comp_id = f"company:{ck}" if ck else f"company:{crl_id}"
        add(comp_id, "Company", comp, canon=ck)
        crl_company_canon.setdefault(ck, comp_id)
        add(crl_id, "CRL", f'{c.get("drug") or comp} CRL ({c.get("year")})',
            year=c.get("year"), app_type=c.get("app_type"), outcome=c.get("outcome"))
        G.add_edge(comp_id, crl_id, type="filed")
        if c.get("drug"):
            did = f"drug:{canon(c['drug'])}"
            add(did, "Drug", c["drug"])
            G.add_edge(crl_id, did, type="for_drug")
        for d in split_deficiencies(c.get("deficiency_types") or []):
            nid = f"deficiency:{d.lower()}"
            add(nid, "DeficiencyType", d)
            G.add_edge(crl_id, nid, type="cited")
        if c.get("therapeutic_area"):
            tid = f"area:{c['therapeutic_area'].lower()}"
            add(tid, "TherapeuticArea", c["therapeutic_area"])
            G.add_edge(crl_id, tid, type="in_area")

    # ---- enforcement firms (bounded: matched-to-CRL or repeat offenders) ---
    # recalls: keep firms appearing >=3 times (repeat recallers) or matching a CRL co.
    recall_firm_counts = Counter(canon(r.get("firm", "")) for r in recalls if r.get("firm"))
    recall_by_canon = defaultdict(list)
    for r in recalls:
        recall_by_canon[canon(r.get("firm", ""))].append(r)

    cross_links = 0
    repeat_nodes = 0

    def link_enforcement(firm_canon: str, firm_label: str, etype: str, ev: dict, conf: float):
        nonlocal cross_links
        fid = f"firm:{firm_canon}"
        add(fid, "Firm", firm_label)
        G.add_edge(fid, fid, type="_self")  # ensure present
        # if this firm matches a CRL company, bridge them
        if firm_canon in crl_company_canon:
            comp_id = crl_company_canon[firm_canon]
            G.add_edge(comp_id, fid, type="cross_enforcement", via=etype, confidence=round(conf, 2))
            cross_links += 1
        return fid

    # recalls -> repeat recallers + CRL matches
    for fc, n in recall_firm_counts.items():
        if not fc:
            continue
        matched = fc in crl_company_canon
        if n >= 3 or matched:
            sample = recall_by_canon[fc][0]
            fid = f"firm:{fc}"
            add(fid, "Firm", sample.get("firm"), recalls=n)
            repeat_nodes += 1 if n >= 3 else 0
            ev = {"recalls": n, "reason": (sample.get("reason") or "")[:120]}
            rid = f"enf:recall:{fc}"
            add(rid, "Enforcement", f'{n} recalls — {sample.get("firm")}', kind="recall",
                count=n, reason=(sample.get("reason") or "")[:160])
            G.add_edge(fid, rid, type="has_recall")
            if matched:
                G.add_edge(crl_company_canon[fc], fid, type="cross_enforcement",
                           via="recall", confidence=0.95)
                cross_links += 1

    # import alert red list -> CRL matches (exact + high fuzzy)
    crl_keys = list(crl_company_canon.keys())
    ia_matches = 0
    for ia in import_alert:
        fc = canon(ia.get("firm", ""))
        if not fc:
            continue
        fid = f"firm:{fc}"
        add(fid, "Firm", ia.get("firm"), country=ia.get("country"))
        aid = f"watch:importalert:{fc}"
        add(aid, "WatchList", f'Import Alert 66-40 — {ia.get("firm")}', kind="import_alert",
            country=ia.get("country"))
        G.add_edge(fid, aid, type="on_import_alert")
        if fc in crl_company_canon:
            G.add_edge(crl_company_canon[fc], fid, type="cross_enforcement",
                       via="import_alert", confidence=0.95)
            cross_links += 1; ia_matches += 1

    # debarment -> CRL matches
    for db in debarment:
        fc = canon(db.get("name", ""))
        if not fc or len(fc) < 4:
            continue
        if fc in crl_company_canon:
            did = f"watch:debarment:{fc}"
            add(did, "WatchList", f'Debarment — {db.get("name")}', kind="debarment")
            G.add_edge(crl_company_canon[fc], did, type="debarred", confidence=0.9)
            cross_links += 1

    # remove the helper self-edges
    G.remove_edges_from([(u, v, k) for u, v, k, d in G.edges(keys=True, data=True)
                         if d.get("type") == "_self"])

    # ---- export ------------------------------------------------------------
    nodes = [{"id": n, **G.nodes[n]} for n in G.nodes]
    edges = [{"source": u, "target": v, **{k2: v2 for k2, v2 in d.items()}}
             for u, v, k, d in G.edges(keys=True, data=True)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"nodes": nodes, "edges": edges,
                               "disclaimer": "Educational, built on public FDA records. "
                               "Not regulatory advice. Matches are confidence-scored, not "
                               "definitive."}, indent=2))

    type_counts = Counter(d["type"] for _, d in G.nodes(data=True))
    edge_counts = Counter(d.get("type") for _, _, d in G.edges(data=True))
    print(f"[L3] wrote {OUT}")
    print(f"  nodes: {G.number_of_nodes()}  edges: {G.number_of_edges()}")
    print(f"  node types: {dict(type_counts)}")
    print(f"  edge types: {dict(edge_counts)}")
    print(f"  CRL<->enforcement cross-links (sponsor also recalled / on a watch list): {cross_links}")
    print(f"  import-alert direct CRL-sponsor matches: {ia_matches}")

    # shared-firm cluster check: a firm node linking >=2 events/CRLs
    clusters = []
    for n, d in G.nodes(data=True):
        if d["type"] in ("Firm", "Company"):
            deg = G.degree(n)
            cross = sum(1 for _, _, e in G.edges(n, data=True)
                        if e.get("type") in ("cross_enforcement", "has_recall",
                                             "on_import_alert", "filed", "debarred"))
            if cross >= 2:
                clusters.append((d["label"], cross))
    clusters.sort(key=lambda x: -x[1])
    print(f"  shared/multi-event clusters (>=2 linked events): {len(clusters)}")
    for lbl, c in clusters[:5]:
        print(f"    - {lbl}: {c} linked events")

    ok = (G.number_of_nodes() > 300 and len(clusters) >= 1 and cross_links >= 1)
    print(f"\n[L3 EXIT] nodes>300:{G.number_of_nodes()>300} cross_links>=1:{cross_links>=1} "
          f"clusters>=1:{len(clusters)>=1} -> {'PASS' if ok else 'FAIL'}")
    import sys
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
