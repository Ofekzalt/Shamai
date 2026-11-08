from __future__ import annotations

import argparse
import logging
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session_factory
from app.core.logging import configure_logging, log_extra
from app.infrastructure.llm.client import LlmClient
from app.infrastructure.llm.models import LlmCall
from app.infrastructure.llm.usage import record_llm_call
from app.modules.investigation.graph.builder import build_graph
from app.modules.investigation.graph.runtime import RUNTIME_KEY, GraphRuntime
from evals.agents.expected import expected_for_case
from evals.agents.score import VariantScore, format_variant_summary, summary_to_markdown

logger = logging.getLogger(__name__)

_GOLDEN_SET = Path(__file__).resolve().parent / "golden_set.yaml"
_DEFAULT_RESULTS = Path(__file__).resolve().parents[1] / "results"
Variant = Literal["single", "rules", "llm"]


def _offline_client() -> httpx.Client:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "offline"})

    return httpx.Client(transport=httpx.MockTransport(handler))


def load_golden_set(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or _GOLDEN_SET
    payload = yaml.safe_load(target.read_text(encoding="utf-8"))
    properties = payload.get("properties") or []
    if not isinstance(properties, list):
        raise ValueError("golden_set.yaml must contain a properties list")
    return properties


def _request_from_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "address": case["address"],
        "asking_price_agorot": int(case["asking_price_agorot"]),
        "size_sqm": float(case["size_sqm"]),
        "profile": case["profile"],
        "as_of": case["as_of"],
    }


def _followup_types(state: dict[str, Any]) -> list[str]:
    types: list[str] = []
    for item in state.get("followup_queue") or []:
        if isinstance(item, dict):
            kind = item.get("type")
            if kind:
                types.append(str(kind))
    for call in state.get("tool_calls") or []:
        if isinstance(call, dict) and call.get("tool") == "compare_around_event":
            types.append("CompareAroundEvent")
    return types


def _llm_cost(session: Session, run_id: uuid.UUID) -> Decimal:
    total = session.scalar(
        select(func.coalesce(func.sum(LlmCall.cost_usd), 0)).where(LlmCall.run_id == run_id)
    )
    return Decimal(str(total or 0))


def run_property(
    session: Session,
    *,
    case: dict[str, Any],
    variant: Variant,
    settings: Settings,
) -> tuple[dict[str, Any] | None, dict[str, Any], int, str | None, uuid.UUID | None]:
    expected = expected_for_case(session, case)
    if not expected.geocoded:
        return None, {}, 0, "address not in geocode cache", None

    if variant == "llm" and not settings.llm_api_key:
        return None, {}, 0, "SHAMAI_LLM_API_KEY not set for llm variant", None

    run_id = uuid.uuid4()
    started = time.perf_counter()

    def on_usage(model: str, prompt_tokens: int, completion_tokens: int, cost_usd: Decimal) -> None:
        record_llm_call(
            session,
            run_id=run_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
        )
        session.flush()

    llm = (
        LlmClient(settings, on_usage=on_usage)
        if variant == "llm" and settings.llm_api_key
        else None
    )
    runtime = GraphRuntime(
        session_factory=lambda: session,
        http=_offline_client(),
        settings=settings,
        llm=llm,
        owns_sessions=False,
        variant=variant,
    )
    graph = build_graph(variant, checkpointer=MemorySaver())
    config = {
        "configurable": {"thread_id": str(run_id), RUNTIME_KEY: runtime},
        "max_concurrency": 1,
    }
    request = _request_from_case(case)
    final = graph.invoke({"job_id": str(run_id), "request": request}, config=config)
    latency_ms = int((time.perf_counter() - started) * 1000)
    report = final.get("result_json")
    if not isinstance(report, dict):
        return None, final, latency_ms, "graph finished without result_json", run_id
    return report, final, latency_ms, None, run_id


def run_variant(
    session: Session,
    *,
    cases: list[dict[str, Any]],
    variant: Variant,
    settings: Settings,
) -> VariantScore:
    from evals.agents.score import score_property

    aggregate = VariantScore(variant=variant)
    total_cost = Decimal(0)
    for case in cases:
        property_id = str(case["id"])
        report, final, latency_ms, skip_reason, run_id = run_property(
            session,
            case=case,
            variant=variant,
            settings=settings,
        )
        expected = expected_for_case(session, case)
        if skip_reason:
            aggregate.properties.append(
                score_property(
                    property_id=property_id,
                    expected=expected,
                    report=report,
                    followups=[],
                    latency_ms=latency_ms,
                    skip_reason=skip_reason,
                )
            )
            continue
        if run_id is not None:
            total_cost += _llm_cost(session, run_id)
        aggregate.properties.append(
            score_property(
                property_id=property_id,
                expected=expected,
                report=report,
                followups=_followup_types(final),
                latency_ms=latency_ms,
            )
        )
    aggregate.cost_usd = float(total_cost)
    return aggregate


def run(
    *,
    variants: list[Variant] | None = None,
    golden_path: Path | None = None,
    write_results: Path | None = None,
    session: Session | None = None,
) -> int:
    if session is None:
        session_factory = get_session_factory()
        with session_factory() as owned:
            return run(
                variants=variants,
                golden_path=golden_path,
                write_results=write_results,
                session=owned,
            )

    settings = get_settings()
    variants = variants or ["single", "rules", "llm"]
    cases = load_golden_set(golden_path)
    notes: list[str] = []
    geocoded = sum(1 for case in cases if expected_for_case(session, case).geocoded)
    if geocoded == 0:
        notes.append(
            "No golden-set addresses found in geocode cache; all properties skipped. "
            "Load municipal geocode cache before expecting non-zero accuracy."
        )

    scores: list[VariantScore] = []
    for variant in variants:
        logger.info(
            "agent eval variant started",
            extra=log_extra(event="eval.agents.variant", variant=variant),
        )
        scores.append(run_variant(session, cases=cases, variant=variant, settings=settings))
        print(format_variant_summary(scores[-1]))

    skipped_properties = {
        row.property_id for score in scores for row in score.properties if row.skipped
    }
    if skipped_properties:
        notes.append(f"Skipped properties: {', '.join(sorted(skipped_properties))}")

    output_dir = write_results or _DEFAULT_RESULTS
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown = summary_to_markdown(scores, notes=notes)
    (output_dir / "agents_latest.md").write_text(markdown, encoding="utf-8")

    logger.info(
        "agent eval completed",
        extra=log_extra(event="eval.agents.completed", variant_count=len(scores)),
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Shamai agent golden-set eval")
    parser.add_argument(
        "--variant",
        action="append",
        choices=["single", "rules", "llm"],
        dest="variants",
        help="Variant to run (repeatable; default all three)",
    )
    parser.add_argument(
        "--golden-set",
        type=Path,
        default=None,
        help="Path to golden_set.yaml",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Directory for committed summaries",
    )
    args = parser.parse_args(argv)
    configure_logging(get_settings().log_level)
    try:
        return run(
            variants=args.variants,
            golden_path=args.golden_set,
            write_results=args.results_dir,
        )
    except Exception:
        logger.exception("agent eval failed", extra=log_extra(event="eval.agents.failed"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
