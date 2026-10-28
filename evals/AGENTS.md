# AGENTS.md — evals

Read [`README.md`](../README.md), root [`AGENTS.md`](../AGENTS.md), accepted ADRs in [`docs/adr/`](../docs/adr/), [`app/modules/valuation/AGENTS.md`](../app/modules/valuation/AGENTS.md), and [`app/modules/investigation/graph/AGENTS.md`](../app/modules/investigation/graph/AGENTS.md) before editing.

This package is allowed to import `app`. `app` must never import `evals`.

## Agent rules

- Temporal splits use `available_at`, never `effective_at`.
- Always print the baseline next to the comps engine, even if the baseline wins.
- Do not tune the golden set to make multi-agent win.
- Do not drop failing properties from the committed summary without a written reason in `evals/results/`.
- `compare_around_event` success means the comparison ran and was labeled non-causal, not that uplift was proved.
- Commit summaries (Markdown/JSON), not raw traces or downloaded source data.
- Do not change production prompts "just for the eval" without a flag.
- Do not depend on LangSmith; read `llm_calls`.
- Keep backtest and agent evals independent so backtest can run before agents exist.

## Two programs

1. **`evals/valuation`** — leakage-free temporal split on `available_at`. Train/fit any index **only** on rows available before each test sale's `as_of`. Metrics: MAE, MAPE, share within 10%, overall and by segment (neighborhood, size band). Baseline is neighborhood median ₪/m² × size.

2. **`evals/agents`** — ~15 properties in `evals/agents/golden_set.yaml` with explicit `as_of`. Expected findings derived from the DB where possible. Run variants `single`, `rules`, `llm` with the same model and tools. Budget: `single` uses `SHAMAI_MAX_TOOL_CALLS`; `rules`/`llm` use that cap **per dispatch** plus `SHAMAI_MAX_DISPATCHES`. Do not equalize by giving `single` the product of both caps.

Manual rubric: `evals/agents/manual_review.md`. Score: factual accuracy, claim-support rate, completeness, follow-ups triggered, cost (from `llm_calls`), latency.

## Manual review

Five cases in `manual_review.md` scored on: correct interpretation, missed caveats, overclaiming. Database checks measure retrieval; this measures judgment. Do not replace the five with more automated rows and call eval done.

## Running (planned)

`python -m evals.valuation.run` and `python -m evals.agents.run`.
