from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.infrastructure.gis.constants import USER_AGENT


def default_http_client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        timeout=httpx.Timeout(
            settings.http_timeout_seconds,
            connect=settings.http_connect_timeout_seconds,
        ),
        follow_redirects=True,
    )
