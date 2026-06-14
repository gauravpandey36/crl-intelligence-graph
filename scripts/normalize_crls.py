#!/usr/bin/env python3
"""Normalize the structured CRLs into graph-ready entities.

Reads a CRL source database (a JSON array of CRL records) and emits
data/crl_entities.json: each CRL becomes a record with a canonical sponsor, drug,
year, app type/number, therapeutic area, a SPLIT list of deficiency types (from
`classification`), the reason/narrative, outcome, and any source links. Also
attempts a light facility/CDMO mention extraction (most CRLs redact this —
facility linkage is done properly via the enforcement data, not the CRL text).

The pre-built data/crl_entities.json is already included, so you only need to run
this to rebuild from an updated source. Point it at your source file with:
    CRL_SOURCE=/path/to/crl_full_database.json python3 scripts/normalize_crls.py
The default source is the companion repo github.com/gauravpandey36/fda-crl-intelligence.

Public FDA data. Educational, not regulatory advice.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path

SRC = Path(os.environ.get("CRL_SOURCE",
           Path(__file__).resolve().parent.parent / "data" / "crl_full_database.json"))
OUT = Path(__file__).resolve().parent.parent / "data" / "crl_entities.json"

# light facility/CDMO mention cues (honest: sparse, due to redaction)
FACILITY_CUES = re.compile(
    r"(manufactur\w+ (?:site|facilit\w+|plant)|contract manufactur\w+|\bCDMO\b|\bCMO\b|"
    r"fill[- ]finish|drug substance (?:site|manufactur\w+)|third[- ]party manufactur\w+)",
    re.IGNORECASE)


def clean_company(raw: str) -> tuple[str, str | None]:
    """Strip a parenthetical note (e.g. 'Proximagen, LLC (later UCB)') -> (canonical, note)."""
    raw = (raw or "").strip()
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", raw)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return raw, None


def split_deficiencies(classification: str) -> list[str]:
    if not classification:
        return []
    parts = re.split(r"[/,;]| and ", classification)
    seen, out = set(), []
    for p in parts:
        t = p.strip().rstrip(".")
        key = t.lower()
        if t and key not in seen:
            seen.add(key)
            out.append(t)
    return out


def facility_mentions(*texts: str) -> list[str]:
    found = []
    for t in texts:
        if not t:
            continue
        for m in FACILITY_CUES.finditer(t):
            found.append(m.group(0).strip())
    # dedupe, keep short
    seen, out = set(), []
    for f in found:
        k = f.lower()
        if k not in seen:
            seen.add(k); out.append(f)
    return out[:5]


def main() -> None:
    raw = json.loads(SRC.read_text())
    entities = []
    for i, r in enumerate(raw):
        company, company_note = clean_company(r.get("company", ""))
        deficiencies = split_deficiencies(r.get("classification", ""))
        fac = facility_mentions(r.get("details", ""), r.get("narrative", ""),
                                r.get("reason", ""))
        entities.append({
            "crl_id": f"CRL-{i+1:03d}",
            "company": company,
            "company_note": company_note,
            "drug": (r.get("drug_name") or "").strip() or None,
            "year": r.get("year_int") or r.get("year"),
            "app_type": (r.get("app_type") or "").strip() or None,   # NDA/BLA/ANDA/505(b)(2)
            "app_number": (r.get("app_number") or "").strip() or None,
            "therapeutic_area": (r.get("therapeutic_area") or "").strip() or None,
            "deficiency_types": deficiencies,
            "reason": (r.get("reason") or "").strip() or None,
            "narrative": (r.get("narrative") or r.get("details") or "").strip()[:1500] or None,
            "outcome": (r.get("outcome") or "").strip() or None,
            "facility_mentions": fac,
            "sources": {
                "news": r.get("news_results") or [],
                "sec": r.get("sec_results") or [],
                "pubmed": r.get("pubmed_results") or [],
            },
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(entities, indent=2))

    # ---- counts (EXIT evidence) ----
    companies = {e["company"] for e in entities if e["company"]}
    drugs = {e["drug"] for e in entities if e["drug"]}
    areas = {e["therapeutic_area"] for e in entities if e["therapeutic_area"]}
    app_types = {}
    deficiency_counter = {}
    facilities_found = sum(1 for e in entities if e["facility_mentions"])
    for e in entities:
        if e["app_type"]:
            app_types[e["app_type"]] = app_types.get(e["app_type"], 0) + 1
        for d in e["deficiency_types"]:
            deficiency_counter[d] = deficiency_counter.get(d, 0) + 1

    print(f"[L1] wrote {OUT}")
    print(f"  CRL records: {len(entities)}")
    print(f"  unique companies: {len(companies)}")
    print(f"  unique drugs: {len(drugs)}")
    print(f"  therapeutic areas: {len(areas)}")
    print(f"  app types: {dict(sorted(app_types.items(), key=lambda x: -x[1]))}")
    print(f"  CRLs with a facility/CDMO mention: {facilities_found}/{len(entities)} "
          f"(most redacted — facility linkage happens in L3 via enforcement data)")
    top_def = sorted(deficiency_counter.items(), key=lambda x: -x[1])[:10]
    print(f"  top deficiency types: {top_def}")

    ok = (len(entities) == 333 and len(companies) > 50 and len(deficiency_counter) > 3)
    print(f"\n[L1 EXIT] records=333:{len(entities)==333} companies>50:{len(companies)>50} "
          f"deficiency_types>3:{len(deficiency_counter)>3} -> {'PASS' if ok else 'FAIL'}")
    import sys
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
