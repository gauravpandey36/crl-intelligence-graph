#!/usr/bin/env python3
"""L5 — vendor watch-list screener.

Upload a vendor/CDMO list (CSV with a 'vendor' or 'name' column, optional
'country'); each vendor is fuzzy-matched against the public FDA watch lists
(Import Alert 66-40 red list, debarment, recall firms) and returned with a
CONFIDENCE score + the matched source record + date. Never auto-asserts a hit:
exact-canonical = high confidence; fuzzy = flagged "confirm". Clean vendors are
reported as "no public watch-list match found (not a clean bill — FDA does not
inspect everyone)".

Public FDA data. Educational, not regulatory advice. Lead-generation for due
diligence, NOT a compliance determination.
"""
from __future__ import annotations
import csv
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENF = ROOT / "enforcement"

SUFFIXES = re.compile(
    r"\b(inc|incorporated|llc|ltd|limited|corp|corporation|co|company|plc|pharmaceuticals?|"
    r"pharma|therapeutics?|laboratories|labs?|gmbh|ag|sa|nv|pvt|private|holdings?|group|usa|"
    r"us|international|biosciences?|biologics?|sciences?)\b", re.IGNORECASE)
HIGH = 0.93      # exact-canonical / near-exact -> high confidence
REVIEW = 0.86    # above this but below HIGH -> "confirm" (medium)


def canon(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = SUFFIXES.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _load():
    def j(name):
        p = ENF / name
        return json.loads(p.read_text()) if p.exists() else []
    import_alert = j("import_alert_6640.json")
    debarment = j("debarment.json")
    recalls = j("recalls.json")
    # index by canonical
    ia = [(canon(x.get("firm", "")), x) for x in import_alert if x.get("firm")]
    db = [(canon(x.get("name", "")), x) for x in debarment if x.get("name")]
    # recalls: aggregate by firm
    rc = {}
    for r in recalls:
        c = canon(r.get("firm", ""))
        if not c:
            continue
        rc.setdefault(c, {"firm": r.get("firm"), "count": 0, "sample_reason": r.get("reason"),
                          "last_date": r.get("date"), "country": r.get("country")})
        rc[c]["count"] += 1
    return ia, db, list(rc.items())


def _best(vendor_canon: str, candidates) -> tuple[float, dict] | None:
    best = (0.0, None)
    for ckey, rec in candidates:
        r = ratio(vendor_canon, ckey)
        if r > best[0]:
            best = (r, rec)
    return best if best[1] and best[0] >= REVIEW else None


def screen_vendor(name: str, ia, db, rc) -> dict:
    vc = canon(name)
    hits = []
    # import alert
    m = _best(vc, ia)
    if m:
        conf, rec = m
        hits.append({"list": "Import Alert 66-40 (DWPE red list)", "confidence": round(conf, 2),
                     "level": "high" if conf >= HIGH else "confirm",
                     "matched_firm": rec.get("firm"), "country": rec.get("country"),
                     "date": rec.get("date_published"),
                     "source": "accessdata.fda.gov import alert 66-40"})
    # debarment
    m = _best(vc, db)
    if m:
        conf, rec = m
        hits.append({"list": "FDA Debarment List", "confidence": round(conf, 2),
                     "level": "high" if conf >= HIGH else "confirm",
                     "matched_firm": rec.get("name"), "source": "FDA Debarment List"})
    # recalls
    m = _best(vc, rc)
    if m:
        conf, rec = m
        hits.append({"list": "FDA recalls (openFDA)", "confidence": round(conf, 2),
                     "level": "high" if conf >= HIGH else "confirm",
                     "matched_firm": rec.get("firm"), "recall_count": rec.get("count"),
                     "sample_reason": (rec.get("sample_reason") or "")[:120],
                     "date": rec.get("last_date"), "source": "api.fda.gov/drug/enforcement"})
    return {"vendor": name, "hits": hits,
            "status": "FLAGGED" if hits else "no public watch-list match"}


def screen_csv(path: str) -> list[dict]:
    ia, db, rc = _load()
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("vendor") or row.get("name") or row.get("Vendor")
                    or next(iter(row.values()), "")).strip()
            if name:
                rows.append(screen_vendor(name, ia, db, rc))
    return rows


def render(results: list[dict]) -> str:
    lines = ["VENDOR WATCH-LIST SCREEN (public FDA data — educational, not regulatory advice)",
             "=" * 70]
    for r in results:
        if r["status"] == "FLAGGED":
            lines.append(f"\n[FLAGGED] {r['vendor']}")
            for h in r["hits"]:
                tag = "HIGH" if h["level"] == "high" else "CONFIRM"
                extra = (f" — {h.get('recall_count')} recalls" if h.get("recall_count") else "")
                lines.append(f"   • {h['list']} [{tag} {int(h['confidence']*100)}%]"
                             f" → matched '{h.get('matched_firm')}'{extra}"
                             f"  (source: {h['source']})")
        else:
            lines.append(f"\n[no match] {r['vendor']}  (not a clean bill — FDA does not inspect everyone)")
    return "\n".join(lines)


def main() -> None:
    # EXIT self-test on a sample CSV: include a known watch-listed-style name + a clean one.
    sample = ROOT / "screener" / "sample_vendors.csv"
    if not sample.exists():
        # seed a sample using real names likely present in the data + a clean control
        ia, db, rc = _load()
        seed_hits = [rec.get("firm") for _, rec in rc[:3] if rec.get("firm")]  # real recall firms
        names = (seed_hits or ["Sun Pharmaceutical Industries Ltd."]) + \
                ["Definitely Clean Vendor Co XYZ-999"]
        with open(sample, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["vendor"])
            for n in names:
                w.writerow([n])
    results = screen_csv(str(sample))
    print(render(results))
    flagged = [r for r in results if r["status"] == "FLAGGED"]
    clean = [r for r in results if r["status"] != "FLAGGED"]
    has_source = all(all("source" in h and "confidence" in h for h in r["hits"]) for r in flagged)
    ok = len(flagged) >= 1 and len(clean) >= 1 and has_source
    print(f"\n[L5 EXIT] flagged>=1:{len(flagged)>=1} clean_handled>=1:{len(clean)>=1} "
          f"every_hit_has_source+confidence:{has_source} -> {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
