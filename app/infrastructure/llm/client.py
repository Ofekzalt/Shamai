from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.core.config import Settings
from app.core.logging import host_from_url, log_extra

UsageCallback = Callable[[str, int, int, Decimal], None]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LlmResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class LlmClient:
    def __init__(
        self,
        settings: Settings,
        *,
        http: httpx.Client | None = None,
        on_usage: UsageCallback | None = None,
    ) -> None:
        self._settings = settings
        self._http = http
        self._on_usage = on_usage

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
    ) -> LlmResponse:
        if not self._settings.llm_api_key:
            logger.error(
                "llm api key missing",
                extra=log_extra(event="llm.not_configured"),
            )
            raise RuntimeError("SHAMAI_LLM_API_KEY is not set")
        chosen = model or self._settings.llm_model
        url = self._settings.llm_base_url.rstrip("/") + "/chat/completions"
        client = self._http or httpx.Client(timeout=self._settings.http_timeout_seconds)
        owns = self._http is None
        try:
            try:
                response = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self._settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": chosen, "messages": messages},
                )
                response.raise_for_status()
                payload = response.json()
            except Exception:
                logger.exception(
                    "llm request failed",
                    extra=log_extra(
                        event="external.request_failed",
                        host=host_from_url(url),
                    ),
                )
                raise
        finally:
            if owns:
                client.close()
        choice = payload["choices"][0]["message"]["content"] or ""
        usage = payload.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        cost = _estimate_cost(prompt_tokens, completion_tokens, model=chosen)
        if self._on_usage is not None:
            self._on_usage(chosen, prompt_tokens, completion_tokens, cost)
        return LlmResponse(
            text=str(choice),
            model=chosen,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


def _estimate_cost(prompt_tokens: int, completion_tokens: int, *, model: str = "") -> Decimal:
    per_million = {
        "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
        "gpt-4o": (Decimal("2.50"), Decimal("10.00")),
    }
    prompt_rate, completion_rate = per_million.get(model, (Decimal("0.15"), Decimal("0.60")))
    prompt = Decimal(prompt_tokens) * prompt_rate / Decimal(1_000_000)
    completion = Decimal(completion_tokens) * completion_rate / Decimal(1_000_000)
    return prompt + completion
