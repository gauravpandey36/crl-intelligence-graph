# CRL Intelligence Graph

**Why did FDA say no — and is it *your* risk?**

An open, free knowledge graph of **FDA Complete Response Letters (CRLs)** — the rejection
letters FDA sends when it won't approve a drug — *fused with* the enforcement record (recalls,
Import Alert 66-40 detentions, debarments) at the **sponsor and facility level**.

The paid tools (FDAzilla/Redica and friends) give you a searchable list of letters. They can't
answer the question a Head of Regulatory Intelligence actually asks: **"a company in my supply
chain got a CRL — does that company *also* show up in FDA's enforcement data, and is anyone on
*my* vendor list exposed?"** This tool answers that, for free, and lets you point it at your own
data to make it about *you*.

Built entirely on **public FDA records**. MIT licensed. Runs with **zero `pip install`**
(Python standard library only).

> **Disclaimer.** This is an educational tool built on public FDA records. It is **not**
> regulatory, legal, or investment advice. Every fuzzy match is confidence-scored and is **not**
> a definitive identification. Absence of a signal is **not** a clean bill of health. Discuss any
> judgment call with qualified regulatory counsel.

---

## What's in the box

A **2,360-node graph** built from 333 structured CRLs joined to the public enforcement record:

| Node type | Count |
|---|---:|
| CRLs | 333 |
| Companies (sponsors) | 260 |
| Drugs | 320 |
| Deficiency types | 50 |
| Therapeutic areas | 22 |
| Manufacturing firms | 681 |
| Enforcement records | 263 |
| Watch-list entries | 431 |

Screened against **443** Import Alert 66-40 firms, **272** debarment-list entries, and **3,000**
recall records.

Four surfaces, all included:

1. **Graph explorer** (`portal/explorer.html`) — an interactive Cytoscape.js view of the
   cross-enforcement subgraph: click a sponsor, expand to its CRLs, drugs, deficiency types, and
   enforcement footprint. Filter by node type.
2. **648-page wiki** (`portal/wiki/`) — a cross-linked page per company, drug, deficiency type,
   and therapeutic area, so every node is a readable, linkable record.
3. **Vendor screener** — paste your CDMO / vendor list and get any name that appears on an FDA
   watch list, **with a confidence score and the source record**. Plus a transparent, fully
   traceable *exposure index* (descriptive, not predictive).
4. **A grounded companion** — a chat guide that answers questions about the graph by citing the
   real nodes and numbers (never invents a figure) and walks you to the screener. Bring your own
   Anthropic key; the rest of the portal works without it.

## The findings it surfaces (all from public data)

- **15 sponsors carry both a CRL *and* an enforcement footprint** (a recall, an Import Alert
  detention, or a debarment) — the cross-enforcement intersection the searchable databases don't
  compute.
- **Repeat-rejected sponsors**: Teva, Mylan, and Celltrion each appear across **5** CRLs.
- **Where drugs die**: **CMC** (chemistry/manufacturing/controls) deficiencies dominate at **188**
  citations, ahead of Clinical (150) and Facility (46). The full per-therapeutic-area failure
  fingerprint is in [`docs/FINDING_cascade.md`](docs/FINDING_cascade.md).

## Quickstart (under a minute, zero dependencies)

```bash
git clone https://github.com/gauravpandey36/crl-intelligence-graph
cd crl-intelligence-graph
python3 portal/server.py 8791
# open http://localhost:8791
```

That serves the dashboard, the graph explorer, the wiki, and the vendor screener — all from the
Python standard library. To enable the chat companion, bring your own key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # only the companion needs this
python3 portal/server.py 8791
```

## Bring your own data — make it about *you*

This is the part the incumbents can't give you: fuse your internal lists with the public record.

- **Vendor / CDMO screen (works today).** `POST /api/screen {"vendors": ["...","..."]}` or paste
  into the portal. Returns each name's watch-list hits with confidence + source + date, and a
  traceable exposure index. CLI: `python3 screener/screen.py`.
- **Your CSV.** `screener/screen.py` reads a vendor CSV directly (`screen_csv`).
- **Veeva Vault RIM (documented upgrade).** The screener takes a list of names; wiring it to a
  Veeva VQL query (`SELECT name__v FROM ...`) over OAuth2 is a thin adapter — your admin enables
  API access, you map the name field, and the same screen runs over your live RIM data. This is a
  v2 connector, intentionally not bundled (it needs per-customer credentials).

## How it's built (the pipeline, all re-runnable)

```
scripts/normalize_crls.py     # CRLs -> canonical sponsor/drug/deficiency entities
scripts/ingest_enforcement.py # openFDA recalls + Import Alert 66-40 + debarment (keyless)
scripts/build_graph.py        # NetworkX graph: typed nodes + edges, entity resolution
scripts/analytics.py          # centrality, cross-enforcement, repeat-rejected, fingerprints
scripts/build_portal.py       # the 648-page wiki + Cytoscape explorer + dashboard
```

The pre-built `data/`, `enforcement/`, and `graph/` JSON are included, so you can explore
immediately. Re-run the pipeline to refresh from updated FDA data (the CRL source is the companion
repo [gauravpandey36/fda-crl-intelligence](https://github.com/gauravpandey36/fda-crl-intelligence)).

No graph database required — the graph is plain NetworkX → JSON → Cytoscape.js. No vendor lock-in,
no subscription, no Neo4j.

## Honest limitations

Read [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) before you trust a result. The
short version: matching is **company-level** (CRLs redact the facility); recalls are recorded
under the **US distributor**, not the foreign manufacturer (an FEI-based join is the v2 fix); the
exposure index is **descriptive, not predictive**; and fuzzy matches are confidence-scored, never
definitive. The tool is built to **miss a match rather than assert a wrong one.**

## Fork it and prove it in an afternoon

1. Clone, run `python3 portal/server.py 8791`, open the explorer.
2. Paste a few of your real CDMOs into the screener — see what's already public.
3. Re-run `scripts/` against the latest FDA pull to confirm the numbers.
4. Plug your own list (CSV today, Veeva VQL with the documented adapter).

If it's useful, bring it in-house and point it at your data. That's the whole idea.

## License

MIT — see [LICENSE](LICENSE). Public FDA data. Educational, not regulatory advice.
