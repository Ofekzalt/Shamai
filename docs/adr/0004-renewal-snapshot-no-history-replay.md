# ADR 0004 — Renewal polygons are snapshots without history replay

Status: Accepted

## Context

Tel Aviv urban-renewal GIS layers are municipal snapshots, not append-only event feeds. iplan status similarly lacks a verified native event stream for all history.

## Decision

Renewal and related planning layers are loaded with `history_available=false` in `docs/data-sources.md`. Shamai synthesizes `plan_status_events` at ingest where needed but does not claim full historical polygon replay from snapshots alone.

## Alternatives

- Backfill synthetic `published_at` on snapshots: would fake point-in-time correctness.
- Omit renewal entirely: loses material investor due-diligence signal.

## Consequences

- Reports qualify renewal and plan history when coverage is snapshot-only.
- `CompareAroundEvent` uses correlation language and index adjustment, never causal uplift.
