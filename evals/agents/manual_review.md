# Agent eval — manual review (five cases)

Score each case 1–5 on: correct interpretation, missed caveats, overclaiming. Database checks measure retrieval; this measures judgment.

## 1. Thin comps with incomplete transaction coverage

**Setup:** Fewer than five comparable sales visible at `as_of`; widen order exhausted.

**Look for:** Report states a limitation or missing information; no fabricated estimate or comp count. Confidence reflects thin coverage.

## 2. Approved renewal nearby (investor profile)

**Setup:** Property near an approved urban-renewal polygon; `CompareAroundEvent` may run.

**Look for:** Correlation language only; no claim that the plan caused appreciation. Index-adjusted framing if a comparison is shown.

## 3. Municipal vs iplan plan disagreement

**Setup:** Two plan sources disagree at the point.

**Look for:** Conflict or missing-information section; no single authoritative status stated without qualification.

## 4. Asking price far above estimate

**Setup:** Asking price materially above comps-based estimate with adequate comp coverage.

**Look for:** Premium discussed with evidence-backed comps; no causal link to planning or renewal unless evidence supports correlation wording only.

## 5. Future-dated or incomplete planning coverage

**Setup:** Planning or renewal coverage incomplete at `as_of`.

**Look for:** `in_renewal` and plan findings omitted or qualified—not `false` or zero counts implying certainty.

---

## Scores (rules variant, reference DB 2026-11-08)

Reviewer: agent (automated spot-check of `rothschild-1-thin`, `rothschild-1-premium`, `dizengoff-50-investor`, `rothschild-1-homebuyer` reports). Rescore after iplan/renewal loads succeed.

| Case | Interpretation (1–5) | Caveats (1–5) | Overclaiming (1–5) | Notes |
| --- | --- | --- | --- | --- |
| 1 Thin comps | 4 | 4 | 5 | Missing-information cites thin comps / limitations; no fabricated estimate. |
| 2 Renewal nearby | 3 | 3 | 5 | Renewal data incomplete (provider); no causal uplift language observed. |
| 3 Plan conflict | 3 | 4 | 5 | Plans incomplete; conflicts section empty, not over-asserted. |
| 4 Asking premium | 4 | 3 | 5 | Premium framing cautious when estimate omitted; limitations listed. |
| 5 Incomplete planning | 4 | 4 | 5 | Plan/renewal gaps surfaced as limitations, not zeros. |
