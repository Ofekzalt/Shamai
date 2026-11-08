from __future__ import annotations


def parse_address(address: str) -> tuple[str, str]:
    cleaned = address.replace(",", " ").strip()
    parts = [part for part in cleaned.split() if part]
    if not parts:
        return address.strip(), "1"
    if len(parts) == 1:
        return parts[0], "1"
    return " ".join(parts[:-1]), parts[-1]
