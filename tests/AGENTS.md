# AGENTS.md — tests

Read [`README.md`](../README.md), root [`AGENTS.md`](../AGENTS.md), accepted ADRs in [`docs/adr/`](../docs/adr/), and the module `AGENTS.md` for the code under test before editing.

If a behavior is in an `AGENTS.md` as a guarantee, it has a test here or the guarantee is a lie. Prefer fixtures over live network.

## Agent rules

- Assert on tool names, params, and follow-up types, not on prose, in trajectory tests.
- Do not hit nadlan.gov.il or other live sources in CI.
- Do not delete a failing test to make CI green; fix the code or the fixture.
- Integration spatial and PIT geometry tests use PostGIS only (no sqlite).
- Keep seed data tiny (one neighborhood, tens of rows), not a city dump.
- Graph tests may use `build_graph("rules")` with fake LLMs; still compile the `llm` variant so imports do not rot.
- State whether a scenario is planned, implemented, or verified in CI.

## Folders

| Path | Purpose |
| --- | --- |
| `unit/` | Valuation, verifier, follow-up equality, `visible_as_of` helpers without geometry |
| `integration/` | Tools + PostGIS, queue claim, API. Partial coverage returns a limitation, not zero comparables or zero plans |
| `reliability/` | Worker kill, reaper, idempotent evidence, job complete twice |
| `trajectory/` | Adaptive agent paths with seeded DB states |
| `fixtures/` | Shared seed data; one fixture pack per trajectory scenario |

## Trajectory tests (required)

These fail if the agent takes the same tool path regardless of data:

1. **`thin_comps`** — fewer than N comps → widen radius, then time, then size; confidence down.
2. **`outlier_comp`** — one deviant sale → inspect `transaction_detail`; keep or drop with a reason in findings.
3. **`plan_conflict`** — municipal vs iplan disagree → `ResolvePlanConflict` / conflicts section.
4. **`renewal_followup`** — approved renewal nearby → Market `CompareAroundEvent`; language is correlation.

Stub the LLM when you need a deterministic path; use a real model only in optional nightly evals.

## Point-in-time fixture

A plan approved Dec 2024, `published_at` Jan 2025, must be invisible at `as_of=2024-11-01` and visible at `as_of=2025-02-01`.
