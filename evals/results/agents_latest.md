# Agent eval summary

- variant=rules evaluated=15 skipped=0 accuracy=75.6% claim_support=100.0% completeness=63.3% followups=7 cost_usd=0.0000 latency_p50_ms=161 latency_p95_ms=255
- variant=single evaluated=15 skipped=0 accuracy=75.6% claim_support=100.0% completeness=63.3% followups=0 cost_usd=0.0000 latency_p50_ms=114 latency_p95_ms=208
- variant=llm skipped (SHAMAI_LLM_API_KEY not set in this run)

## Notes

- Reference DB loaded via municipal geocode + odata TLV transactions (street centroids; `dealnature` size field).
- Planning providers (iplan TLS, renewal geometry page size) often return incomplete coverage; completeness penalizes missing plan/renewal sections accordingly.
- Use `python -m evals.valuation.run --as-of 2025-07-01` when the latest transaction `available_at` is before “now”.
