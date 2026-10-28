# AGENTS.md — investigation tools

Read [`README.md`](../../../../README.md), root [`AGENTS.md`](../../../../AGENTS.md), accepted ADRs in [`docs/adr/`](../../../../docs/adr/), [`../../property_data/AGENTS.md`](../../property_data/AGENTS.md), [`../../planning/AGENTS.md`](../../planning/AGENTS.md), and [`../../valuation/AGENTS.md`](../../valuation/AGENTS.md) before editing.

Tools are the only way agents touch property data, planning data, and valuation. They are not agents and they do not investigate.

## Agent rules

- Every public tool takes `as_of` and the run id, calls a module service, may call `valuation`, upserts evidence, and returns a small typed result plus evidence ids.
- Call `property_data` and `planning` services. Do not import their repositories or providers. Do not call the network.
- Same run + tool + params → same evidence row.
- No job state and no LLM calls. The service may write source rows when coverage is missing. The tool does not write those tables itself.
- No investigation policy. Widening search is a Market-agent or guardrail loop that calls `find_comparables` again with a larger radius or window.
- If the service returns incomplete or failed coverage, write that limitation into the evidence payload. Do not turn it into a count of zero.
- `compare_around_event` must document a correlation-style comparison, not causal uplift, including the index adjustment in the payload.
- Keep signatures stable. Graph prompts depend on them.
- Do not import FastAPI. Do not implement follow-up types.

## What belongs here

- `market.py` — `find_comparables`, `price_index`, `transaction_detail`, `compare_around_event`.
- `development.py` — `plans_at_location`, `plan_status_history`, `renewal_areas`.

Intake geocoding goes through a tool that calls the `property_data` service, so the graph does not import that service itself.

## Tests

Integration tests against PostGIS fixtures: `as_of` hides future rows; evidence upsert is stable across two calls; `compare_around_event` payload includes the non-causal flag or equivalent field; partial coverage is stored as a limitation.
