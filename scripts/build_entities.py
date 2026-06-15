#!/usr/bin/env python3
"""Build the answer-first data layer: per-company Knowledge-Card intelligence + the landing verdict.
Reuses the validated screener + exposure logic so every enforcement hit is sourced & confidence-scored.
Outputs portal/data/companies.json (keyed by slug) and portal/data/landing.json. Public FDA data."""
from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "screener"))
from screen import screen_vendor, _load          # noqa: E402
from exposure import exposure                      # noqa: E402

crls = json.loads((ROOT / "data" / "crl_entities.json").read_text())
analytics = json.loads((ROOT / "graph" / "analytics.json").read_text())
ia, db, rc = _load()


def slug(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")[:80]


by_co = defaultdict(list)
for c in crls:
    if c.get("company"):
        by_co[c["company"]].append(c)

companies = {}
search = []
for name, items in by_co.items():
    sr = screen_vendor(name, ia, db, rc)
    ex = exposure([sr])
    defic, areas, apptypes, years, drugs = Counter(), Counter(), Counter(), [], set()
    crl_list = []
    for c in sorted(items, key=lambda x: x.get("year") or 0, reverse=True):
        for d in (c.get("deficiency_types") or []):
            defic[d] += 1
        if c.get("therapeutic_area"):
            areas[c["therapeutic_area"]] += 1
        if c.get("app_type"):
            apptypes[c["app_type"].upper()] += 1
        if c.get("year"):
            years.append(int(c["year"]))
        if c.get("drug"):
            drugs.add(c["drug"])
        src = c.get("sources")
        if isinstance(src, dict):
            src = [v for v in src.values() if isinstance(v, str) and v.startswith("http")][:3]
        elif isinstance(src, list):
            src = [v for v in src if v][:3]
        else:
            src = [src] if src else []
        crl_list.append({
            "drug": c.get("drug"), "year": c.get("year"), "app_type": c.get("app_type"),
            "area": c.get("therapeutic_area"), "deficiencies": c.get("deficiency_types") or [],
            "reason": (c.get("reason") or "")[:240], "sources": src,
        })
    hits = sr.get("hits", [])
    enf_kinds = sorted({h.get("list", "").split(" (")[0] for h in hits})
    sl = slug(name)
    companies[sl] = {
        "name": name, "slug": sl,
        "crl_count": len(items),
        "years": [min(years), max(years)] if years else None,
        "crls": crl_list,
        "deficiencies": defic.most_common(),
        "areas": areas.most_common(),
        "app_types": apptypes.most_common(),
        "drugs": sorted(drugs),
        "enforcement": {"status": sr.get("status"), "n_events": len(hits),
                        "kinds": enf_kinds, "hits": hits},
        "risk": {"exposure_index": ex["exposure_index"], "band": ex["band"],
                 "breakdown": ex["breakdown"]},
        "cross_enforcement": len(hits) > 0,
    }
    search.append({"slug": sl, "name": name, "crls": len(items),
                   "enf": len(hits), "exp": ex["exposure_index"]})

(ROOT / "portal" / "data").mkdir(parents=True, exist_ok=True)
(ROOT / "portal" / "data" / "companies.json").write_text(json.dumps(companies, indent=1))
(ROOT / "portal" / "data" / "search.json").write_text(
    json.dumps(sorted(search, key=lambda x: (-x["enf"], -x["crls"])), indent=1))

# ---- landing verdict ----
defic_all = Counter()
by_year = Counter()
app_all = Counter()
for c in crls:
    for d in (c.get("deficiency_types") or []):
        defic_all[d] += 1
    if c.get("year"):
        by_year[int(c["year"])] += 1
    if c.get("app_type"):
        app_all[c["app_type"].upper()] += 1

# marquee = the cross-enforcement firms (the "is it your risk" wow) with their slugs
marquee = []
for r in analytics["cross_enforcement_sponsors"][:6]:
    sl = slug(r["company"])
    if sl in companies:
        marquee.append({"slug": sl, "name": r["company"], "events": r["n_events"],
                        "via": r["vias"], "crls": companies[sl]["crl_count"]})
cross_n = sum(1 for c in companies.values() if c["cross_enforcement"])
repeat_n = sum(1 for c in companies.values() if c["crl_count"] >= 3)
top_def = defic_all.most_common(1)[0]
landing = {
    "totals": {"crls": len(crls), "companies": len(companies),
               "drugs": len({c.get("drug") for c in crls if c.get("drug")}),
               "cross_enforcement_firms": cross_n, "repeat_rejected_firms": repeat_n,
               "year_min": min(by_year), "year_max": max(by_year),
               "top_deficiency": top_def[0], "top_deficiency_n": top_def[1],
               "ia_firms": len(ia), "debarments": len(db), "recalls": len(rc)},
    "marquee": marquee,
    "deficiency_categories": defic_all.most_common(10),
    "by_year": {str(y): by_year[y] for y in sorted(by_year)},
    "by_app_type": app_all.most_common(),
    "most_exposed": sorted(
        [{"slug": c["slug"], "name": c["name"], "crls": c["crl_count"],
          "events": c["enforcement"]["n_events"], "exp": c["risk"]["exposure_index"],
          "band": c["risk"]["band"], "kinds": c["enforcement"]["kinds"]}
         for c in companies.values() if c["cross_enforcement"]],
        key=lambda x: (-x["exp"], -x["events"], -x["crls"]))[:12],
    "most_rejected": sorted(
        [{"slug": c["slug"], "name": c["name"], "crls": c["crl_count"]}
         for c in companies.values()], key=lambda x: -x["crls"])[:12],
}
(ROOT / "portal" / "data" / "landing.json").write_text(json.dumps(landing, indent=1))

print(f"[entities] {len(companies)} company cards; {cross_n} cross-enforcement; "
      f"{repeat_n} repeat-rejected; top deficiency {top_def[0]} ({top_def[1]})")
print(f"  marquee: {[m['name'] for m in marquee]}")
print(f"  most-exposed[0]: {landing['most_exposed'][0] if landing['most_exposed'] else 'none'}")
