#!/usr/bin/env python3
"""Build portal/dashboard_data.json — precomputed aggregates that power the orientation
dashboard (rejections by year, deficiency categories, NDA vs BLA, top companies, areas,
enforcement coverage). All from the data the graph already holds. Public FDA data."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
crls = json.loads((ROOT / "data" / "crl_entities.json").read_text())
analytics = json.loads((ROOT / "graph" / "analytics.json").read_text())


def n(p):
    return len(json.loads((ROOT / "enforcement" / p).read_text()))


by_year = Counter()
by_apptype = Counter()
by_area = Counter()
by_company = Counter()
defic = Counter()
for c in crls:
    if c.get("year"):
        by_year[int(c["year"])] += 1
    by_apptype[(c.get("app_type") or "Other").upper()] += 1
    if c.get("therapeutic_area"):
        by_area[c["therapeutic_area"]] += 1
    if c.get("company"):
        by_company[c["company"]] += 1
    for d in (c.get("deficiency_types") or []):
        defic[d] += 1

years = sorted(y for y in by_year if 2005 <= y <= 2026)
data = {
    "totals": {
        "crls": len(crls),
        "companies": len(by_company),
        "drugs": len({c.get("drug") for c in crls if c.get("drug")}),
        "graph_nodes": analytics["totals"]["nodes"],
        "graph_edges": analytics["totals"]["edges"],
        "import_alert_firms": n("import_alert_6640.json"),
        "debarments": n("debarment.json"),
        "recalls": n("recalls.json"),
        "cross_enforcement": len(analytics["cross_enforcement_sponsors"]),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
    },
    "by_year": {str(y): by_year[y] for y in years},
    "by_app_type": dict(by_apptype.most_common()),
    "deficiency_categories": analytics["top_deficiency_types"],
    "top_companies": by_company.most_common(10),
    "therapeutic_areas": by_area.most_common(10),
    "cross_enforcement_sponsors": [
        {"company": r["company"], "events": r["n_events"], "via": r["vias"]}
        for r in analytics["cross_enforcement_sponsors"][:8]
    ],
}
(ROOT / "portal" / "dashboard_data.json").write_text(json.dumps(data, indent=2) + "\n")
t = data["totals"]
print(f"[dashboard] {t['crls']} CRLs, {t['companies']} companies, {t['drugs']} drugs, "
      f"{t['year_min']}–{t['year_max']}")
print(f"  by_app_type: {data['by_app_type']}")
print(f"  years with data: {len(data['by_year'])}  ({min(data['by_year'])}..{max(data['by_year'])})")
print(f"  top company: {data['top_companies'][0]}")
print(f"  deficiency top: {data['deficiency_categories'][0]}")
print(f"  enforcement: IA {t['import_alert_firms']}, debar {t['debarments']}, recalls {t['recalls']}")
