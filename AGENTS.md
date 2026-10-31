# AGENTS.md — repository

Read [`README.md`](README.md), this file, [`docs/data-sources.md`](docs/data-sources.md), and accepted ADRs in [`docs/adr/`](docs/adr/) before editing. Module rules live in each package's `AGENTS.md` (`app/core`, `app/modules/*`, `app/jobs`, `app/infrastructure/llm`, `evals`, `tests`, `docs`, `scripts/spike`). Those files win on conflict for files inside their directory.

## Agent rules

- **Modular monolith.** One package, one database, two long-running processes (`api`, `worker`). Reference loads and backfill call the same module services as the worker. Do not add a separate ingestion package, microservices, Redis, RabbitMQ, Kafka, or a frontend unless the human asks.
- **Import direction is one-way.** `app.main` imports controllers. `investigation.controller` → `jobs`. `jobs` → `investigation.graph` and `infrastructure.llm`. `graph` → `investigation.tools` + `evidence` + `reporting`. `tools` → `property_data.service` + `planning.service` + `valuation` + `evidence`. A service → its own repository and providers. Repositories → `core`. `evidence` → `core`; `evidence.calculations` may import `valuation`. `reporting` uses its own DTOs and never imports repositories. `app` never imports `evals` or `scripts`. Nothing imports a controller except `app.main`. `valuation` imports nothing from `app`. `graph` and `tools` must not import repositories or providers.
- **No invented numbers.** Tools write evidence. Claims cite evidence IDs. The verifier rejects or qualifies material claims that fail their check. Incomplete coverage is a limitation, not a count of zero.
- **No future data.** Time-sensitive reads filter `available_at <= as_of`. Filtering on deal/effective date alone is a bug.
- **Rules vs LLM.** If an `if` statement can decide it (min comps, dispatch budget, duplicate follow-up), it is a guardrail. Do not ask the model.
- **Follow-ups are typed.** Add a variant to `app/modules/investigation/graph/followups.py`. Do not pass free-text questions between agents except as an optional human-readable `reason` field.
- **Correlation is not causation.** Renewal vs non-renewal price gaps are exploratory and index-adjusted. Never phrase them as "the plan caused appreciation."
- **Licensing before fetch.** Do not scrape a source whose terms are undocumented. Record the decision in `docs/data-sources.md`. Never commit raw data.
- **Guarantees we actually test:** at-least-once jobs, reaping expired leases, timeouts → incomplete reports, p50/p95 measured not promised, material claims validated or qualified.
- **Production variant.** The public API has no `variant` field. The worker default is `rules`. `single` and `llm` are eval-only unless config overrides.
- Never rewrite an accepted ADR; add a superseding ADR in `docs/adr/`.

## Coding

- Python 3.12, Ruff, pytest. Prefer typed Pydantic models at process boundaries.
- Valuation and calculated-claim functions stay pure and unit-tested without a database.
- Tools are adapters: call module services, call `valuation`, upsert evidence. No investigation policy in tools. Services own coverage checks and provider fallback.
- Idempotent writes: evidence keyed by hash(run, tool, params); jobs keyed by `idempotency_key`.
- Record LLM cost in `llm_calls`. Published eval metrics come from `llm_calls` and `evals.valuation.run`, not LangSmith. LangSmith tracing may be enabled later for debugging agent runs; it must not replace those numbers.
- Do not add comments that restate the code. Do not add docstrings that duplicate type names.

## Variants

`build_graph(variant)` must keep `single`, `rules`, and `llm` sharing tools, budgets, and claim schema. If you change one, change the eval harness in `evals/agents/` in the same change.

## When stuck on data

Stop and update `docs/data-sources.md` (license, history available, lag). Do not paper over missing history by claiming full as-of replay.

## Out of scope until asked

SSE, `/compare`, HTML maps, Deep Agents, LightGBM, MAPIE, Kubernetes, user accounts.
