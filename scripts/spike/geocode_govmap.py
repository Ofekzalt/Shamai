"""Probe GovMap geocode (fallback)."""

from __future__ import annotations

from scripts.spike._common import client, print_summary, save

GOVMAP_SEARCH = "https://www.govmap.gov.il/api/search-service/search"
GOVMAP_DOCS = "https://api.govmap.gov.il/"
_DIZENGOFF_50_TLV = (
    "\u05d3\u05d9\u05d6\u05e0\u05d2\u05d5\u05e3 50, "
    "\u05ea\u05dc \u05d0\u05d1\u05d9\u05d1-\u05d9\u05e4\u05d5"
)

SAMPLE_BODY = {
    "language": "he",
    "limit": 5,
    "type": 1,
    "address": _DIZENGOFF_50_TLV,
}


def main() -> None:
    result_count = 0
    notes: list[str] = []

    with client() as http:
        try:
            resp = http.post(GOVMAP_SEARCH, json=SAMPLE_BODY)
            save("geocode_govmap", "search_raw", resp.content, suffix=".txt")
            notes.append(f"POST search HTTP {resp.status_code}")
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith(
                "application/json"
            ):
                payload = resp.json()
                results = payload.get("results") or []
                result_count = len(results) if isinstance(results, list) else 0
        except Exception as exc:  # noqa: BLE001
            notes.append(f"search failed: {exc}")

        try:
            home = http.get("https://www.govmap.gov.il/")
            save("geocode_govmap", "home", home.text[:15000], suffix=".html")
            notes.append(f"www HTTP {home.status_code}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"home failed: {exc}")

        try:
            docs = http.get(GOVMAP_DOCS)
            save("geocode_govmap", "api_docs", docs.text[:15000], suffix=".html")
            notes.append(f"api docs HTTP {docs.status_code}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"docs failed: {exc}")

    if result_count > 0:
        proposed = "go"
        access = "JSON search-service POST"
    else:
        proposed = "pending"
        access = (
            "Documented GovMap search API exists (api.govmap.gov.il); spike blocked by "
            "CloudFront/403 from this environment — re-verify from app network before fallback use"
        )

    print_summary(
        source="Geocode: GovMap",
        url=GOVMAP_SEARCH,
        license_note="Government mapping service; confirm cache/redistribution on GovMap terms",
        access=access,
        published_at="n/a",
        lag="n/a",
        history="n/a",
        proposed=proposed,
        notes="; ".join(notes),
    )


if __name__ == "__main__":
    main()
