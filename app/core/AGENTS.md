# AGENTS.md — core

Read [`README.md`](../../README.md), root [`AGENTS.md`](../../AGENTS.md), and accepted ADRs in [`docs/adr/`](../../docs/adr/) before editing.

Shared process setup: configuration, the database session, shared exceptions, and the single point-in-time filter. Domain tables and queries live in the module that owns them.

## Agent rules

- `visible_as_of(query, as_of)` is the only implementation of `available_at <= as_of`. Modules call it. They do not reimplement the filter.
- Do not import `app.modules`, `app.jobs`, or `app.infrastructure`.
- Do not compute valuation, verify claims, or call external APIs.
- Schema changes go through Alembic only. This package does not own feature tables.

## Point-in-time contract

| Column | Meaning |
| --- | --- |
| `effective_at` | When the deal or status took effect |
| `published_at` | When it became public (nullable) |
| `retrieved_at` | When Shamai fetched it |
| `available_at` | `coalesce(published_at, effective_at + lag)` — **this is what queries filter on** |
| `available_at_estimated` | True when the lag fallback was used |

A November 2024 run must not see an approval that became public in January 2025 even if `effective_at` is December 2024. There is a unit or integration fixture for that case; do not delete it.

Geometry in stored facts is EPSG:4326 unless a query documents otherwise. Area-coverage cell indices use EPSG:2039 and are defined by the module that owns coverage.

## What belongs here

- `config.py` — settings, neighborhood allowlist, timezone, budgets.
- `database.py` — engine and session dependency. Route modules do not open their own engines.
- `exceptions.py` — shared error types.
- `point_in_time.py` — `visible_as_of`.
