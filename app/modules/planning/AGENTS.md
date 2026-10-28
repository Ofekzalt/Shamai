# AGENTS.md — planning

Read [`README.md`](../../../README.md), root [`AGENTS.md`](../../../AGENTS.md), [`docs/data-sources.md`](../../../docs/data-sources.md), accepted ADRs in [`docs/adr/`](../../../docs/adr/), [`app/core/AGENTS.md`](../../core/AGENTS.md), and [`app/modules/property_data/AGENTS.md`](../property_data/AGENTS.md) before editing.

Urban plans, status events, renewal and Pinui-Binui polygons, and planning documents. Area sync follows the same coverage rules as `property_data`. A single document or current status is a separate lookup.

## Agent rules

- No provider ships without a filled `go` row in `docs/data-sources.md`. Area sync also requires geographic retrieval and permission to store the polygons. A document-only source does not get area coverage.
- Agents, graph nodes, and tools never import `providers/`. Only `service.py` does.
- Plan status is append-only events. Never overwrite a single status column.
- Snapshot layers set `history_available=false`. Do not backfill a fake `published_at` or use today's polygon for a historical replay.
- Fetching one plan document or one current status never marks an area cell `complete`.
- Incomplete area coverage returns a typed limitation. Do not report "no plan" because the cache is empty.
- Compute `available_at` on write, using the lag in `data-sources.md` when `published_at` is missing.
- Idempotent upserts on a natural key. Raw files stay in gitignored `data/`.
- Do not import `investigation`, `evidence`, `valuation`, or `property_data`.
- Do not copy a municipal GIS HTTP client into this package and into `property_data`. Extract `app/infrastructure/gis/` when a second module needs the same client.

## What belongs here

- `service.py` — area coverage check, then provider; plus `get_document(plan_id)` and current status by plan id.
- `repository.py` — plans, events, polygons, document cache, coverage cells for planning sources.
- `models.py` — those tables. Polygons in EPSG:4326.
- `dto.py` — records returned to tools.
- `providers/` — one module per `go` source (for example plan boundaries, renewal polygons, urban renewal). Add the file only after the row exists.

## Tests

The December 2024 approval published in January 2025 is invisible at `as_of=2024-11-01` and visible at `as_of=2025-02-01`. A document fetch leaves area coverage unchanged. Incomplete coverage does not become "no plans."
