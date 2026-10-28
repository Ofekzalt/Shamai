# AGENTS.md — evidence

Read [`README.md`](../../../README.md), root [`AGENTS.md`](../../../AGENTS.md), accepted ADRs in [`docs/adr/`](../../../docs/adr/), and [`../valuation/AGENTS.md`](../valuation/AGENTS.md) before editing.

The audit trail. If a number is in the report, it is here first. This module also serves `GET /evidence/{id}`.

## Agent rules

- Keep claim types `observed`, `calculated`, and `interpretation` and their checks consistent with README and the writer/verifier.
- Material claims (numbers, plan or status ids, containment, asking vs estimate) must cite evidence ids or fail verification.
- A material claim that the area has no transactions or no plans fails verification unless the cited evidence shows coverage status `complete` for that query.
- Do not let the writer invent evidence IDs.
- The interpretation judge is injected. This package must not import LangGraph. Only `controller.py` imports FastAPI.
- Calculated-claim registry entries must call `app.modules.valuation` (or other named pure functions). The evidence → valuation import is allowed only inside `calculations.py`.
- `verify.py` does not fetch the web and does not call tools or providers.
- Do not run the investigation graph or decide which comps to keep.
- Treat the LLM judge as a separate metric from deterministic pass rate.
- `app.main` is the only module that imports `controller.py`.

## What belongs here

- `store.py` — upsert evidence. Internal unique key = SHA-256 of `run_id`, `tool_name`, and canonical JSON params. Public `id` is a UUID.
- `claims.py` — `ObservedClaim`, `CalculatedClaim`, `InterpretationClaim`.
- `calculations.py` — named functions used to recompute calculated claims.
- `verifier.py` — `observed`, `calculated`, `interpretation`, and the verify entrypoint.
- `controller.py` — `GET /evidence/{id}`.
- `dto.py` — evidence GET payload.
- `repository.py` — evidence rows. Domain source tables stay in their modules. `llm_calls` is written by `app.infrastructure.llm`.

## Claim types and checks

| Type | Meaning | Check |
| --- | --- | --- |
| `observed` | Copied from a source payload | Evidence id exists; cited fields match payload |
| `calculated` | Output of a named function | Re-run the function on cited inputs |
| `interpretation` | LLM judgment over other claims | LLM judge callable; failure → status `qualified` |

Every evidence row stores: tool, params, JSON payload, source or dataset, `retrieved_at`, and coverage status when the tool fetched an area.

Observed numeric tolerance: money in agorot (integers); counts exact; floats only for ratios (1e-6 relative or an explicit field tolerance).

## Verifier policy

Material claims that fail observed or calculated checks are rejected (writer retry) or dropped after max 2 writer loops. Interpretations that fail the judge are qualified in the report.

## Tests

Deterministic tests for observed mismatch, calculated recompute, missing evidence id, idempotent upsert, and a "no transactions" claim whose evidence coverage is not `complete`. The judge can be a fake callable in unit tests.
