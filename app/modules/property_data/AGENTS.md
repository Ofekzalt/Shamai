# AGENTS.md — property_data

Read [`README.md`](../../../README.md), root [`AGENTS.md`](../../../AGENTS.md), [`docs/data-sources.md`](../../../docs/data-sources.md), accepted ADRs in [`docs/adr/`](../../../docs/adr/), and [`app/core/AGENTS.md`](../../core/AGENTS.md) before editing.

Addresses, the geocode cache, residential transactions, statistical areas, and transaction-area coverage. The service checks PostgreSQL first. A provider runs only when coverage is missing or stale.

## Agent rules

- No provider ships without a filled `go` row in `docs/data-sources.md`. The row must allow geographic or date-range retrieval and local storage. Throttling is not permission.
- Agents, graph nodes, and tools never import `providers/`. Only `service.py` does.
- The caller chooses the radius and date range. This module does not decide investigation policy (minimum comps, widen order).
- Existing transaction rows never mean an area is complete. Coverage is its own table.
- On failure or incomplete coverage, return the rows that were stored plus a typed limitation. An empty list is not "zero sales" unless coverage for that query is `complete`.
- Time-sensitive reads take `as_of` and use `visible_as_of`. Compute `available_at` when writing. If `published_at` is missing, apply the lag from `data-sources.md` and set `available_at_estimated=true`.
- Idempotent upserts on a natural key. Re-running a fetch must not duplicate facts.
- Raw files and HTTP caches go under gitignored `data/`.
- Do not import `investigation`, `evidence`, `valuation`, or `planning`.
- Do not compute weighted medians, index adjustments, or claim verification.
- Comparable candidates come from PostGIS (`<->` / KNN), not from a Python loop over the city.

## Coverage

A request maps to grid cells in EPSG:2039 (250 m cells via `app/infrastructure/gis/coverage_grid.py`). A cell satisfies the request only when its status is `complete`, its stored window covers the requested dates, and the open end of that window is still within the source lag documented in `data-sources.md`. A closed historical window does not need another fetch for an earlier `as_of`.

Fetch only cells that fail that check. Group them into as few bounding boxes as the provider allows, follow pagination, validate, normalize, and upsert. Mark those cells `complete` only after the provider proves the last page. If it cannot, leave them `incomplete` even when some rows were stored.

A coverage-row lease stops two jobs from fetching the same cell. Transactions themselves stay in EPSG:4326.

## What belongs here

- `service.py` — coverage check, provider fallback, upsert, typed result including limitation.
- `repository.py` — coverage, KNN candidates, geocode cache, statistical areas.
- `models.py` — transactions, geocode cache, statistical areas, coverage.
- `dto.py` — records returned to tools.
- `providers/` — one module per source that has a `go` row (`transactions`, `geocoding`). Do not add the file before that row exists.
- Hebrew addresses: Tel Aviv municipal address layer first, then GovMap if that row is `go`. Always cache. Geocoding is an address cache, not a cell grid.

Statistical areas are a reference dataset for the price index. Use cell coverage only if that source supports geographic retrieval and local storage. Otherwise load them in bulk through this service.

Do not transform geometry in Python beyond shapely validation. Load with PostGIS.

## Tests

A fixture with rows and no complete coverage cell returns a limitation, not a confident empty market. A future-dated transaction is invisible at an earlier `as_of`. A second fetch of the same cell does not insert a second fact.
