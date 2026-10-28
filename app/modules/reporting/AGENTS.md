# AGENTS.md — reporting

Read [`README.md`](../../../README.md), root [`AGENTS.md`](../../../AGENTS.md), and accepted ADRs in [`docs/adr/`](../../../docs/adr/) before editing.

Owns the report DTO stored in `jobs.result_json` and renders it to Markdown. Does not investigate, query PostGIS, or call LLMs.

## Agent rules

- Rendering must not add numbers. Material claims in the DTO are already verified or qualified.
- Correlation language for `CompareAroundEvent` is required in the investor template.
- JSON for `GET /analyses/{id}/report` is `jobs.result_json`, not a second structure invented here.
- Investor template may include historical growth **scenarios** and the exploratory renewal comparison. It must not print a predicted future price.
- A coverage limitation renders in the missing-information section. It must not render as zero transactions or zero plans.
- Do not import repositories, graph nodes, or tools.
- Do not fetch evidence payloads. Deep audit is `GET /evidence/{id}`.

## What belongs here

- `dto.py` — report JSON, the same shape as `jobs.result_json`.
- `service.py` — profile selection and render entrypoint.
- `renderer.py` — `render(report, profile) -> str`.
- `templates/homebuyer.md.j2` and `templates/investor.md.j2`, added with the first template. Profile selects the template.

The writer and finalize nodes build the DTO. This module only types and formats it.
