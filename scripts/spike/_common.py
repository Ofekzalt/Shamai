from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import httpx

USER_AGENT = "ShamaiSpike/0.1 (+https://github.com/Ofekzalt/Shamai; research only)"
TIMEOUT = httpx.Timeout(30.0, connect=15.0)
DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "spike"


def client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        timeout=TIMEOUT,
        follow_redirects=True,
    )


def save(source: str, name: str, content: bytes | str, *, suffix: str = ".txt") -> Path:
    out_dir = DATA_ROOT / source
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}{suffix}"
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)
    return path


def save_json(source: str, name: str, payload: Any) -> Path:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    return save(source, name, text, suffix=".json")


def curl_get(url: str) -> tuple[int, bytes]:
    proc = subprocess.run(
        ["curl", "-sS", "-A", USER_AGENT, "-w", "\n%{http_code}", url],
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace") or "curl failed")
    body, _, status_line = proc.stdout.rpartition(b"\n")
    status = int(status_line.decode("ascii", errors="replace") or "0")
    return status, body


def print_summary(
    *,
    source: str,
    url: str,
    license_note: str,
    access: str,
    published_at: str,
    lag: str,
    history: str,
    proposed: str,
    notes: str = "",
) -> None:
    print(f"\n=== {source} ===")
    print(f"URL: {url}")
    print(f"License/terms: {license_note}")
    print(f"Access: {access}")
    print(f"published_at: {published_at}")
    print(f"Lag (days, if estimated): {lag}")
    print(f"history_available: {history}")
    print(f"Proposed go/no-go: {proposed}")
    if notes:
        print(f"Notes: {notes}")
