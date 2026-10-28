# AGENTS.md — jobs

Read [`README.md`](../../README.md), root [`AGENTS.md`](../../AGENTS.md), accepted ADRs in [`docs/adr/`](../../docs/adr/), [`app/modules/investigation/graph/AGENTS.md`](../modules/investigation/graph/AGENTS.md), and [`app/infrastructure/llm/AGENTS.md`](../infrastructure/llm/AGENTS.md) before editing.

This layer decides **which run happens**, on which process, and how many times. LangGraph's checkpointer decides **where inside a run** to resume. Do not collapse those two ideas.

## Agent rules

- Keep statuses `queued` | `running` | `verifying` | `done` | `failed` | `incomplete` consistent with the API.
- Delivery is at-least-once. Completing a job twice must be a no-op.
- Timeouts store whatever `result_json` exists and set `incomplete`, not `failed`.
- Record elapsed time for p50/p95; do not encode "under 5 minutes" as a product promise.
- Do not implement valuation or claim verification here.
- Call LLM APIs only through `runner` → graph. Cost rows go through `app.infrastructure.llm`, not from a graph node.
- Do not add Redis or RabbitMQ.
- Link to `tests/reliability/` once those tests exist.

## What belongs here

- `queue.py` — enqueue, `SELECT ... FOR UPDATE SKIP LOCKED` claim, heartbeat, complete, fail.
- `worker.py` — `python -m app.jobs.worker` loop.
- `reaper.py` — jobs whose `lease_expires_at` passed return to runnable (if attempts remain).
- `runner.py` — invoke `build_graph` with `thread_id=job.id` and the Postgres checkpointer.

Job row fields that must exist: `status`, `attempts`, `max_attempts` (default 3), `lease_expires_at`, heartbeat, unique `idempotency_key`, `error`/`reason`, `result_json`.

`verifying` is set while the writer/verifier loop runs. `failed` is for enqueue/validation/crash with nothing to show.

## Delivery semantics

Duplicate execution of a graph node is expected if the process dies before checkpoint commit. Tools/evidence upserts must be idempotent. `POST /analyses` with the same idempotency key returns the existing job.

Terminal failures (max attempts, unrecoverable error, run timeout) store a reason and a status the API can show. Do not leave jobs in `running` forever.

## Timeouts

Defaults: lease 15 minutes with heartbeat every 60s; run timeout 10 minutes; step timeout 120s.

`runner.py` attaches the `app.infrastructure.llm` cost callback that writes `llm_calls`. Graph nodes do not open that table directly.

## Tests

`tests/reliability/`: kill worker mid-run → reaper claims → job reaches a terminal state; lease expiry; idempotent enqueue. A dummy job (graph stub) is enough until the real graph exists.
