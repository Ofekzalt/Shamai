# AGENTS.md — infrastructure/llm

Read [`README.md`](../../../README.md), root [`AGENTS.md`](../../../AGENTS.md), and accepted ADRs in [`docs/adr/`](../../../docs/adr/) before editing.

Model client and usage recording. Graph nodes do not open the client or the `llm_calls` table themselves.

## Agent rules

- The jobs runner attaches the cost callback. Nodes call the client the runner injected.
- Record token usage and cost in `llm_calls`. Do not rely on LangSmith for evaluation metrics.
- Do not import `app.modules` or `app.jobs`.
- Do not choose investigation policy, follow-ups, or which claims to keep.
- Eval and production share this client. A prompt change for an eval needs an explicit flag, not a second client.

## What belongs here

- `client.py` — chat completion used by graph nodes and the injected evidence judge.
- `usage.py` — the callback that writes one `llm_calls` row per model call. The `llm_calls` model lives here.
