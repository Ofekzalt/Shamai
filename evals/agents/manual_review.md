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
