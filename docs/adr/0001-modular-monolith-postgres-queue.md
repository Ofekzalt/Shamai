# ADR 0001 — Modular monolith with Postgres job queue

Status: Accepted

## Context

Shamai runs due-diligence investigations as background jobs. We need at-least-once execution, idempotent analysis creation, and a single deployable unit for v1.

## Decision

One Python package with two long-running processes (`api`, `worker`), one PostgreSQL/PostGIS database, and a jobs table with `FOR UPDATE SKIP LOCKED` claiming. No Redis, RabbitMQ, or Kafka. Reference loads call the same module services as the worker.

## Alternatives

- Message broker plus separate ingestion service: more moving parts without a proven need at v1 scale.
- Synchronous HTTP investigation: exceeds latency budgets and blocks API workers.

## Consequences

- Reliability tests target lease expiry, reaper, and idempotent completion in-process.
- Horizontal scaling is limited to multiple workers competing on the same queue (acceptable for v1).
