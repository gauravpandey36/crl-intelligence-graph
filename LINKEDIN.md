# LinkedIn draft — CRL Intelligence Graph

> Draft for Gourav to review/edit before posting. Plain language, no hype. Public FDA data only.

---

**Why did FDA say no — and is it *your* risk?**

Every paid regulatory-intelligence tool can hand you a searchable list of FDA Complete Response
Letters. None of them answers the question a Head of Reg Intel actually asks on a Monday morning:

*"A company in my supply chain got a CRL. Does that same company also show up in FDA's enforcement
record — recalls, Import Alerts, debarments? And is anyone on MY vendor list exposed?"*

So I built an open one that does. Free, MIT-licensed, runs with zero install.

**The CRL Intelligence Graph** — 333 structured CRLs fused with the public enforcement record into
a 2,360-node graph at the sponsor and facility level:

→ 15 sponsors carry **both** a CRL and an enforcement footprint — the cross-enforcement
intersection a searchable database can't compute.
→ CMC (manufacturing) deficiencies dominate where drugs die — 188 citations, ahead of clinical.
→ Teva, Mylan, and Celltrion each appear across 5 CRLs.

And the part the incumbents can't give you: **bring your own data.** Paste your CDMO/vendor list
and it flags any name on an FDA watch list — with a confidence score and the source record — and
returns a fully traceable exposure index. (A Veeva Vault RIM connector is a documented next step.)

It's built entirely on public FDA records. It's deliberately precise — it would rather miss a
match than assert a wrong one — and every limitation is written down.

Fork it, run it in an afternoon, point it at your own data:
🔗 github.com/gauravpandey36/crl-intelligence-graph

Educational tool, not regulatory advice. Feedback from reg-affairs and supply-quality folks
especially welcome — tell me what would make this useful in your actual workflow.

#RegulatoryAffairs #PharmaQuality #FDA #DrugDevelopment #OpenSource #SupplyChain
