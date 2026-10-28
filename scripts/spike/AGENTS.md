# AGENTS.md — scripts/spike

Read [`README.md`](../../README.md), root [`AGENTS.md`](../../AGENTS.md), and [`docs/data-sources.md`](../../docs/data-sources.md) before editing.

Throwaway probes for one external source. They answer whether a loader is allowed to exist. They are not production ingestion.

## Agent rules

- A probe checks license, geographic or date-range filter, pagination, history, and lag. Write the result into `docs/data-sources.md`.
- Do not promote a probe into `app/modules/*/providers/` until that row is `go`.
- `app` does not import `scripts`.
- Raw responses stay in gitignored `data/`. Do not commit them.
- Throttling, an API key, or a public URL is not permission to store the data.

## What belongs here

One short script per source under question. Delete or replace it once the `data-sources.md` row is filled.
