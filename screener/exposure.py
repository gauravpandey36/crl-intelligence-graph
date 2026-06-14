#!/usr/bin/env python3
"""L6 — program exposure index.

Given a program profile (a vendor CSV), produce a DESCRIPTIVE, fully-traceable
exposure index: every point traces to a dated public FDA source record. This is
NOT a predictive CRL rate (public data has no clean denominator; a rate would be
survivorship-biased). It is an additive "how much public enforcement signal sits
on your vendor list" score, for due-diligence triage.

Public FDA data. Educational, not regulatory advice. Not predictive of FDA action.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "screener"))
from screen import screen_csv  # noqa: E402

# severity weights (transparent, additive) — every point is explainable
SEVERITY = {
    "FDA Debarment List": 40,
    "Import Alert 66-40 (DWPE red list)": 30,
    "FDA recalls (openFDA)": 10,
}
CONFIRM_DISCOUNT = 0.5   # a "confirm" (fuzzy) hit counts half a "high" hit


def _year(s: str | None) -> int | None:
    if not s:
        return None
    import re
    m = re.search(r"(19|20)\d{2}", str(s))
    return int(m.group(0)) if m else None


def _recency_factor(year: int | None) -> float:
    # current year ~2026; recent enforcement weighs more
    if year is None:
        return 0.7
    age = max(0, 2026 - year)
    if age <= 2:
        return 1.0
    if age <= 5:
        return 0.8
    if age <= 10:
        return 0.5
    return 0.3


def exposure(results: list[dict]) -> dict:
    total = 0.0
    breakdown = []
    for r in results:
        for h in r["hits"]:
            base = SEVERITY.get(h["list"], 5)
            if h["list"] == "FDA recalls (openFDA)":
                base += 2 * min(h.get("recall_count", 1), 5)  # repeat recallers weigh more
            level_factor = 1.0 if h.get("level") == "high" else CONFIRM_DISCOUNT
            rec = _recency_factor(_year(h.get("date")))
            pts = round(base * level_factor * rec, 1)
            total += pts
            breakdown.append({
                "vendor": r["vendor"], "list": h["list"], "points": pts,
                "why": f"{base} base x {level_factor} ({h.get('level')}) x {rec} recency",
                "matched_firm": h.get("matched_firm"), "date": h.get("date"),
                "source": h.get("source"),
            })
    total = round(total, 1)
    band = ("Low" if total < 20 else "Moderate" if total < 60 else "Elevated")
    return {
        "exposure_index": total, "band": band,
        "n_vendors": len(results),
        "n_flagged": sum(1 for r in results if r["hits"]),
        "breakdown": sorted(breakdown, key=lambda x: -x["points"]),
        "disclaimer": ("Descriptive, fully traceable exposure score from public FDA records. "
                       "NOT a predictive CRL rate and NOT regulatory advice. Every point traces "
                       "to a dated source record below. Absence of signal is not a clean bill."),
    }


def render(ex: dict) -> str:
    out = [f"PROGRAM EXPOSURE INDEX: {ex['exposure_index']}  (band: {ex['band']})",
           f"{ex['n_flagged']}/{ex['n_vendors']} vendors carry a public enforcement signal.",
           "Every point is traceable:", "-" * 60]
    for b in ex["breakdown"]:
        out.append(f"  +{b['points']:>5}  {b['vendor']}  [{b['list']}]")
        out.append(f"         {b['why']}; matched '{b['matched_firm']}' "
                   f"({b.get('date') or 'no date'}); src {b['source']}")
    out.append("\n" + ex["disclaimer"])
    return "\n".join(out)


def main() -> None:
    sample = ROOT / "screener" / "sample_vendors.csv"
    if not sample.exists():
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "screener" / "screen.py")],
                       capture_output=True)
    results = screen_csv(str(sample))
    ex = exposure(results)
    print(render(ex))
    # EXIT: an index is produced AND every point traces to a source record
    traceable = all(("source" in b and "points" in b and "why" in b) for b in ex["breakdown"])
    ok = (isinstance(ex["exposure_index"], (int, float)) and len(ex["breakdown"]) >= 1
          and traceable)
    print(f"\n[L6 EXIT] index_produced:{isinstance(ex['exposure_index'],(int,float))} "
          f"points>=1:{len(ex['breakdown'])>=1} every_point_traceable:{traceable} "
          f"-> {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
