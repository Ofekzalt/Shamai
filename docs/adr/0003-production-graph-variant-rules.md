# ADR 0003 — Production investigation variant is `rules`

Status: Accepted

## Context

The investigation graph supports `single`, `rules`, and `llm` variants for evaluation. The public API must not expose variant or prompt tuning.

## Decision

The worker default variant is `rules` (`SHAMAI_VARIANT`, default `rules` in settings). The supervisor routes with deterministic rules; the LLM supervisor is used only in the `llm` eval variant. Specialists may call the LLM only when `variant == "llm"` for optional ranking paths.

## Alternatives

- Production `llm` supervisor: higher cost and less predictable routing for v1.
- API `variant` parameter: invites untested production configurations.

## Consequences

- Agent eval compares all three variants; production behavior is the `rules` path.
- Guardrails (min comps widen, dispatch budget, duplicate follow-ups) stay in code, not prompts.
