# Finding: cross-enforcement and shared-risk patterns in FDA CRLs

*Educational, built on public FDA records (CRLs + recalls + Import Alert 66-40 + debarment). Not regulatory advice. Company-level matches are confidence-scored.*

Graph: **2360 nodes, 2066 edges**.

## The headline a search box can't give: sponsors whose rejection sits next to an enforcement footprint
These companies received a Complete Response Letter AND independently appear in FDA recalls / the Import Alert 66-40 red list / the debarment list. A document-by-document search shows you one or the other; the graph shows the overlap.

| Sponsor | Linked enforcement events | Via |
|---|---:|---|
| Sun Pharmaceutical Industries Ltd. | 3 | import_alert, recall |
| Glenmark Pharmaceuticals, Inc. | 2 | import_alert, recall |
| Mylan GmbH | 2 | import_alert, recall |
| Baxter Healthcare Corp. | 2 | import_alert, recall |
| Teva Pharmaceuticals USA, Inc. | 1 | recall |
| Hospira, Inc. | 1 | recall |
| AuroMedics Pharma LLC | 1 | recall |
| Valeant Pharmaceuticals | 1 | recall |
| Dr. Reddy’s Laboratories | 1 | recall |
| Regeneron Pharmaceuticals, Inc. | 1 | recall |

## Repeat-rejected sponsors (more than one CRL)
| Sponsor | CRLs |
|---|---:|
| Teva Pharmaceuticals USA, Inc. | 5 |
| Mylan GmbH | 5 |
| Celltrion, Inc. | 5 |
| Dr. Reddy’s Laboratories | 4 |
| Eli Lilly and Company | 4 |
| Astellas Pharma US, Inc. | 4 |
| CMP Development LLC | 4 |
| Amgen Inc. | 4 |
| HQ Specialty Pharma Corp. | 3 |
| Glenmark Pharmaceuticals, Inc. | 3 |

## What FDA says no for (deficiency dominance)
| Deficiency type | CRLs citing it |
|---|---:|
| CMC | 188 |
| Clinical | 150 |
| Facility | 46 |
| Nonclinical | 23 |
| Labeling | 20 |
| Device | 17 |
| Regulatory | 13 |
| HF | 9 |
| Microbiology | 8 |
| Clinical Pharmacology | 7 |

## Therapeutic-area failure fingerprints
The dominant rejection reasons differ by area:
- **Metabolic**: Clinical (6), CMC (5), Nonclinical (2)
- **Infectious Disease**: Clinical (8), CMC (3), Clinical+CMC (1)
- **Oncology**: Clinical (9), CMC (4)
- **CNS**: CMC (5), Clinical (4), Facility (1)
- **Pain**: Clinical (4), CMC (2), Facility (2)
- **Immunology**: Clinical (4), CMC (3), Labeling (1)
- **Rare Disease**: Clinical (5), CMC (2), Facility (1)
- **Respiratory**: Clinical (3), Facility (2)

## Risk hubs (most-connected company/firm nodes)
| Node | Degree |
|---|---:|
| Mylan GmbH | 7 |
| Teva Pharmaceuticals USA, Inc. | 6 |
| Sun Pharmaceutical Industries, Inc. | 6 |
| Glenmark Pharmaceuticals, Inc. | 5 |
| Dr. Reddy’s Laboratories | 5 |
| Celltrion, Inc. | 5 |
| Astellas Pharma US, Inc. | 5 |
| Amgen Inc. | 5 |
| Hospira, Inc. | 4 |
| Regeneron Pharmaceuticals, Inc. | 4 |

*Limits: most CRLs redact the manufacturing facility, so company-level matching is the honest resolution; absence of a match is not a clean bill. Import-Alert/recall matches are name-based (lower confidence than an FEI join). This is lead-generation for due diligence, not a compliance determination.*
