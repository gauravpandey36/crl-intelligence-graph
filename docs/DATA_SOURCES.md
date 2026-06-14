# Data sources (all public FDA)

| Source | What | Access | Join key |
|---|---|---|---|
| 333 structured CRLs | [gauravpandey36/fda-crl-intelligence](https://github.com/gauravpandey36/fda-crl-intelligence) (AI-structured from public FDA CRLs) | JSON | sponsor/drug; facility mostly redacted |
| openFDA CRLs | newly-public CRLs | `api.fda.gov` transparency endpoint | letter_date, center |
| Inspection Classification DB | OAI/VAI/NAI by facility | `datadashboard.fda.gov/oii/cd/inspections.htm` (XLSX export) | **FEI** (cleanest) |
| Compliance Actions / Warning Letters | WLs, seizures | `datadashboard.fda.gov/oii/cd/complianceactions.htm` + FDA WL DB | FEI / firm name |
| Import Alert 66-40 | red list, detention w/o exam | `accessdata.fda.gov/cms_ia/importalert_189.html` (HTML scrape) | firm name + address (no FEI) |
| Debarment List | barred persons/firms | FDA Debarment page (XLSX) | name |
| CI Disqualification | restricted clinical investigators | OpenSanctions mirror `us_fda_restricted` | person name |
| openFDA drug enforcement/recalls | recall records | `api.fda.gov/drug/enforcement.json` (keyless) | recalling-firm name (no FEI) |
| Drug Shortages | current/resolved | `api.fda.gov/drug/shortages.json` (keyless) | drug-level |
| FEI Portal | name/address/DUNS → FEI resolver | `feiportal.fda.gov` (interactive) | the Rosetta Stone |

**Honesty rule:** no universal key in a user's uploaded vendor list → fuzzy match with confidence scores; Import-Alert/recall matches are name-only (lower confidence) vs FEI matches. Absence of a hit ≠ clean.
