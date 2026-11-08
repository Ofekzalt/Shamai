# ADR 0002 — Point-in-time reads on `available_at`

Status: Accepted

## Context

Government transaction and planning data may be effective before it is public. Historical investigations must not see facts that were not yet available.

## Decision

Time-sensitive rows store `effective_at`, `published_at`, `retrieved_at`, and `available_at = coalesce(published_at, effective_at + documented_lag)`. All visibility queries filter `available_at <= as_of`. Filtering on deal date or status effective date alone is rejected in review.

## Alternatives

- Filter on `effective_at` only: leaks future publications into past runs.
- Store only `published_at`: many sources omit it; lag fallback is required.

## Consequences

- Loaders set `available_at_estimated` when lag is used.
- Tools and valuation must use the same visibility rule; comparables and event windows included.
