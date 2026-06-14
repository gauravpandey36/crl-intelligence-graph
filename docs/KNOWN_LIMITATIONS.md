# Known limitations (read before trusting a result)

This tool is built ONLY on free public FDA data. It is deliberately precise over greedy —
it would rather miss a match than assert a wrong one. The honest gaps:

1. **Foreign manufacturer vs US distributor naming.** openFDA records a recall under the
   `recalling_firm` (often the US distributor / NDA holder), not the foreign API/manufacturer.
   Example: the valsartan nitrosamine recalls are recorded under "Prinston Pharmaceutical Inc"
   (the US distributor), not "Zhejiang Huahai" (the API maker). Screening by the foreign
   manufacturer name will therefore MISS that recall. The fix is an FEI-based join (FDA
   establishment identifier), a documented v2 upgrade — not faked here.

2. **Company-level, not facility-level, CRL matching.** CRLs almost always redact the specific
   facility. So a sponsor's CRL is linked at the company level, which can over- or under-attribute
   when a company runs many sites.

3. **Active-list snapshot.** Import Alert 66-40 is the *current* DWPE red list. A firm that
   remediated and was removed will not appear, even if it had a historical detention.

4. **No clean denominator.** The exposure index is descriptive (how much public enforcement signal
   sits on your list), NOT a predictive CRL rate. Public data has no unbiased denominator.

5. **Fuzzy matches are confidence-scored, never definitive.** A HIGH match (>=0.93) still warrants
   human confirmation against the cited source record before any decision.

Everything is public FDA data. Educational, not regulatory advice. Discuss judgment calls with
qualified regulatory counsel.
