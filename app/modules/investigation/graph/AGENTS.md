# AGENTS.md — investigation graph

Read [`README.md`](../../../../README.md), root [`AGENTS.md`](../../../../AGENTS.md), accepted ADRs in [`docs/adr/`](../../../../docs/adr/), [`../tools/AGENTS.md`](../tools/AGENTS.md), and [`../../evidence/AGENTS.md`](../../evidence/AGENTS.md) before editing.

LangGraph workflow: intake → supervisor loop → writer → verifier → finalize. Specialists are short-lived subgraphs. They do not talk to each other; they return `AgentResult` into shared `RunState`.

## Agent rules

- Keep `single`, `rules`, and `llm` sharing tools, budgets, and claim schema. Changing one means changing `evals/agents/` in the same change.
- Follow-ups are typed variants. Dedup by structural equality. Do not use free-text as follow-up identity.
- Guardrails (min comps, dispatch budget, duplicate follow-up) are code, not LLM judgment.
- Never phrase renewal comparisons as causal. Use `CompareAroundEvent` and correlation language.
- Graph nodes must not import repositories, providers, or `valuation`. SQL and external fetches stay behind tools.
- Nodes must tolerate re-entry (`thread_id` = job id).
- Do not expand city coverage or add a fourth specialist without being asked.
- Do not claim multi-agent is better; that is an eval result.
- If adaptive behavior changes, update the matching `tests/trajectory/` test in the same change.

## What belongs here

- `state.py`, `followups.py` (typed requests only).
- `builder.py` — `build_graph(variant: Literal["single","rules","llm"])`.
- `specialist.py` — shared bounded tool loop. Config key `SHAMAI_MAX_TOOL_CALLS` default **8** per dispatch.
- `agents/market.py` and `agents/development.py` — prompt, tool list, guardrails only.
- `supervisor_rules.py` — question queue, budgets, duplicate suppression.
- `supervisor_llm.py` — prioritizes the **same** queue; cannot invent new action types.
- `single_agent.py` — evaluation baseline: all tools, **no follow-up protocol**. Budget = `SHAMAI_MAX_TOOL_CALLS` (8), not the supervisor dispatch cap. Do not give `single` 6×8 tool calls.
- `writer.py`, `verify.py`, `finalize.py`.
- `prompts/` — the only long-form natural language for models.

## Supervisor

Allowed actions: dispatch Market, dispatch Development, finish. Hard budget `SHAMAI_MAX_DISPATCHES` default **6**. After intake, the first Market and Development tasks are emitted together with LangGraph `Send` (fan-out). Follow-ups after merge may be sequential. `RunState.profile` is `homebuyer` | `investor` and is passed to reporting.

Unanswered required questions at finish become the report's missing-information section. Do not drop them.

Use the LLM supervisor only to order remaining questions or decide "answered well enough." Routing that is obvious from open question types stays in `supervisor_rules.py`.

## Follow-ups

Closed set, for example: `ExplainPricePremium`, `CompareAroundEvent`, `ResolvePlanConflict`.

## Guardrails vs judgment

| Situation | Implementation |
| --- | --- |
| Comp count < N | Deterministic widen order (radius, time, size) then lower confidence |
| Duplicate dispatch | Supervisor rule |
| Outlier keep/drop with a reason | Market LLM after a tool flags the outlier |
| Two plan sources disagree | Development agent + `ResolvePlanConflict` |
| "Did renewal cause the premium?" | Forbidden; use `CompareAroundEvent` and correlation language |

Required trajectory tests: `thin_comps`, `outlier_comp`, `plan_conflict`, `renewal_followup`.

## Writer and verifier

Not agents. The writer emits typed claims with evidence ids. The verifier uses `app.modules.evidence`. Max 2 rewrite loops. After that, qualify or drop; still emit uncertainty, missing, and conflicts sections. A coverage limitation is missing information, not a zero count.
