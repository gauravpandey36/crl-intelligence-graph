#!/usr/bin/env python3
"""L2 — ingest public FDA enforcement / watch-list data.

Keyless / public sources first; degrade gracefully and LOG anything that needs
auth we don't have. Writes enforcement/<source>.json + docs/INGEST_LOG.md.

Sources attempted:
  - openFDA drug enforcement (recalls)         api.fda.gov  [keyless]
  - openFDA drug shortages                     api.fda.gov  [keyless]
  - Import Alert 66-40 (DWPE red list)         accessdata.fda.gov HTML scrape
  - FDA Debarment List                         fda.gov (attempt)
  - Inspection Classification (OAI/VAI/NAI)     Data Dashboard (attempt; may need auth)
  - Warning Letters                            Data Dashboard (attempt; may need auth)

Public FDA data. Educational, not regulatory advice.
"""
from __future__ import annotations
import json
import re
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "enforcement"
LOG = ROOT / "docs" / "INGEST_LOG.md"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")
_log: list[str] = []


def fetch(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def openfda_paginated(endpoint: str, search: str, cap: int = 2000) -> list[dict]:
    """Pull up to `cap` records from an openFDA endpoint (keyless, 1000/page)."""
    out, skip = [], 0
    while len(out) < cap:
        q = {"limit": 1000, "skip": skip}
        if search:
            q["search"] = search
        url = f"https://api.fda.gov/{endpoint}.json?" + urllib.parse.urlencode(q)
        try:
            d = json.loads(fetch(url))
        except Exception as e:  # noqa: BLE001
            if skip == 0:
                raise
            break
        res = d.get("results", [])
        if not res:
            break
        out.extend(res)
        skip += len(res)
        if len(res) < 1000:
            break
    return out[:cap]


# --------------------------------------------------------------------------- #
def src_recalls() -> int:
    rows = openfda_paginated("drug/enforcement", "", cap=3000)
    keep = [{
        "firm": r.get("recalling_firm"),
        "city": r.get("city"), "state": r.get("state"), "country": r.get("country"),
        "reason": r.get("reason_for_recall"),
        "classification": r.get("classification"),
        "date": r.get("recall_initiation_date"),
        "product": (r.get("product_description") or "")[:200],
        "status": r.get("status"),
    } for r in rows]
    (OUT / "recalls.json").write_text(json.dumps(keep, indent=2))
    cgmp = sum(1 for r in keep if "cgmp" in (r["reason"] or "").lower()
               or "manufactur" in (r["reason"] or "").lower())
    _log.append(f"| openFDA drug enforcement (recalls) | keyless API | **{len(keep)}** "
                f"({cgmp} CGMP/manufacturing-related) | recalls.json |")
    return len(keep)


def src_shortages() -> int:
    rows = openfda_paginated("drug/shortages", "", cap=3000)
    keep = [{
        "drug": r.get("generic_name") or r.get("proprietary_name"),
        "company": r.get("company_name"),
        "status": r.get("status"),
        "reason": r.get("shortage_reason"),
        "therapeutic_category": r.get("therapeutic_category"),
        "date": r.get("update_date") or r.get("initial_posting_date"),
    } for r in rows]
    (OUT / "shortages.json").write_text(json.dumps(keep, indent=2))
    _log.append(f"| openFDA drug shortages | keyless API | **{len(keep)}** | shortages.json |")
    return len(keep)


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;?", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def src_import_alert_6640() -> int:
    """Import Alert 66-40 — DWPE red list. Firms are in <div class='div-info'> blocks,
    grouped under <h4>COUNTRY</h4>. Firm name = div-name floatleft; date = floatright;
    address = the following 'clear' div. (No FEI on this page.)"""
    html = fetch("https://www.accessdata.fda.gov/cms_ia/importalert_189.html").decode(
        "utf-8", errors="replace")
    # walk the page, tracking the current country from <h4> headers
    recs = []
    cur_country = None
    # split on country headers and div-info blocks, in document order
    tokens = re.split(r'(<h4>.*?</h4>|<div class="div-info">.*?</div>\s*</div>)', html,
                      flags=re.DOTALL | re.IGNORECASE)
    for tok in tokens:
        h = re.match(r"<h4>(.*?)</h4>", tok, re.DOTALL | re.IGNORECASE)
        if h:
            cur_country = _clean(h.group(1))
            continue
        if 'class="div-info"' in tok:
            name = re.search(r'div-name floatleft">(.*?)</div>', tok, re.DOTALL | re.IGNORECASE)
            date = re.search(r'Date Published\s*:\s*([\d/]+)', tok)
            addr = re.search(r'class="clear">(.*?)</div>', tok, re.DOTALL | re.IGNORECASE)
            if name:
                recs.append({
                    "firm": _clean(name.group(1)),
                    "country": cur_country,
                    "address": _clean(addr.group(1)) if addr else None,
                    "date_published": date.group(1) if date else None,
                    "fei": None,  # not present on this page
                })
    seen, uniq = set(), []
    for r in recs:
        k = (r["firm"] or "").lower()
        if k and len(k) > 1 and k not in seen:
            seen.add(k); uniq.append(r)
    (OUT / "import_alert_6640.json").write_text(json.dumps(uniq, indent=2))
    _log.append(f"| Import Alert 66-40 (DWPE red list) | HTML scrape (div-info blocks) | "
                f"**{len(uniq)}** firms | import_alert_6640.json |")
    return len(uniq)


def src_debarment() -> int:
    """FDA Debarment List — try to locate the data on the FDA page."""
    page = fetch("https://www.fda.gov/inspections-compliance-enforcement-and-criminal-"
                 "investigations/compliance-actions-and-activities/fda-debarment-list-drug-"
                 "product-applications").decode("utf-8", errors="replace")
    # names usually appear in a table of debarred persons/firms
    names = re.findall(r"<td[^>]*>([A-Z][A-Za-z.,'\-\s]{3,60})</td>", page)
    names = [n.strip() for n in names if len(n.strip()) > 3][:500]
    seen, uniq = set(), []
    for n in names:
        if n.lower() not in seen:
            seen.add(n.lower()); uniq.append({"name": n})
    if uniq:
        (OUT / "debarment.json").write_text(json.dumps(uniq, indent=2))
        _log.append(f"| FDA Debarment List | HTML scrape | **{len(uniq)}** entries | debarment.json |")
        return len(uniq)
    _log.append("| FDA Debarment List | HTML scrape | 0 parsed (page layout) | skipped |")
    return 0


def try_src(label: str, fn) -> int:
    try:
        n = fn()
        print(f"  [{label}] {n} records")
        return n
    except Exception as e:  # noqa: BLE001
        print(f"  [{label}] SKIPPED: {type(e).__name__}: {str(e)[:80]}")
        _log.append(f"| {label} | FAILED/needs-auth | 0 | skipped: {type(e).__name__} |")
        return 0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("[L2] ingesting public FDA enforcement data...")
    counts = {
        "recalls": try_src("openFDA recalls", src_recalls),
        "shortages": try_src("openFDA shortages", src_shortages),
        "import_alert_6640": try_src("Import Alert 66-40", src_import_alert_6640),
        "debarment": try_src("Debarment List", src_debarment),
    }
    # Inspection Classification + Warning Letters via Data Dashboard need the OII
    # Unified Logon API key (not held). Log honestly rather than fake it.
    _log.append("| Inspection Classification (OAI/VAI/NAI) | Data Dashboard — needs OII Unified "
                "Logon API key (not held) | deferred | see INGEST_LOG note |")
    _log.append("| Warning Letters (structured) | Data Dashboard — needs OII logon; WL full-text "
                "scrape is a v2 enhancement | deferred | — |")

    header = ("# L2 ingest log\n\n*Public FDA data. Educational, not regulatory advice.*\n\n"
              "| Source | Access | Records | File |\n|---|---|---:|---|\n")
    LOG.write_text(header + "\n".join(_log) + "\n\n"
                   "**Note:** the FDA Data Dashboard's Inspection Classification and structured "
                   "Compliance-Actions feeds require an OII Unified Logon API key we do not hold. "
                   "v1 uses the keyless watch lists (Import Alert 66-40 = the strongest red flag, "
                   "recalls, shortages, debarment). Adding the OAI/WL feeds (with a logon key) is a "
                   "documented v2 upgrade.\n")

    nonzero = sum(1 for v in counts.values() if v > 0)
    print(f"\n[L2 EXIT] sources with data: {nonzero} ({[k for k,v in counts.items() if v>0]}) "
          f"-> {'PASS' if nonzero >= 3 else 'FAIL'}")
    import sys
    sys.exit(0 if nonzero >= 3 else 1)


if __name__ == "__main__":
    main()
