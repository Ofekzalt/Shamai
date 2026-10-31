# AGENTS.md — investigation

Read [`README.md`](../../../README.md), root [`AGENTS.md`](../../../AGENTS.md), accepted ADRs in [`docs/adr/`](../../../docs/adr/), [`graph/AGENTS.md`](graph/AGENTS.md), and [`tools/AGENTS.md`](tools/AGENTS.md) before editing.

FastAPI analysis routes, request and status models, and the investigation lifecycle. LangGraph rules live in `graph/`. Tool rules live in `tools/`. This package does not run the graph inside a request.

## Agent rules

- Preserve the v1 analysis routes, status names, and idempotency contract until an ADR changes them.
- Do not accept `prompt` or `variant`. Variant is worker and eval config.
- Reject addresses that do not geocode through the Tel Aviv–Yafo municipal address layer.
- `controller.py` imports `jobs` and local DTOs. It does not import graph nodes, tools, repositories, or providers.
- Do not open a database engine in the controller. Use the session dependency from `app.core`.
- Never return raw LLM traces as the user-facing report.
- Do not grow a frontend. Swagger is enough.
- `app.main` is the only module that imports `controller.py`.

## Endpoints owned here

| Method | Path | Role |
| --- | --- | --- |
| POST | `/analyses` | Header `Idempotency-Key` required. First create **202**; repeats return the same `{id, status}` with **200** |
| GET | `/analyses/{id}` | `queued` \| `running` \| `verifying` \| `done` \| `failed` \| `incomplete` |
| GET | `/analyses/{id}/report` | JSON from `result_json`; Markdown if `Accept: text/markdown` |

`GET /evidence/{id}` belongs to `app.modules.evidence`. No SSE, no `/compare`, no auth (v1 is local/demo).

## Request and response

- Require address (or structured location), asking price, size (m²), and `profile` in `{homebuyer, investor}`. Optional rooms, floor, year built.
- Optional `as_of` (calendar date, Asia/Jerusalem; default today in that timezone).
- Money in the API is integer agorot (or a documented `ILS` decimal field converted once at the edge).
- Same `Idempotency-Key` and same body → same job id. Same key and a different body → **409**.
- Reports include claim types, evidence ids, uncertainty, missing data, and conflicts. Markdown rendering is `app.modules.reporting`.

## What belongs here

- `controller.py` — the three analysis routes.
- `dto.py` — create-analysis body and status payload. No `variant`, no `prompt`.
- `service.py` — enqueue and status reads. It does not investigate.
- `graph/` — see `graph/AGENTS.md`.
- `tools/` — see `tools/AGENTS.md`.

## Tests

API tests hit the app with a stub queue if needed: validation errors, idempotent POST, status payload, missing analysis 404.
