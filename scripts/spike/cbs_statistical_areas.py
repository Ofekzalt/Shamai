"""Probe CBS statistical areas (mesh / statistical area geometry)."""

from __future__ import annotations

from scripts.spike._common import client, print_summary, save, save_json

PACKAGE_ID = "6b729165-dc9c-49b3-afc6-eceabd8fef70"
RESOURCE_ID = "3b88cb58-62cd-43ea-9156-7b81ead557b1"
PACKAGE_URL = f"https://data.gov.il/dataset/{PACKAGE_ID}"
DOWNLOAD_URL = (
    f"https://e.data.gov.il/dataset/{PACKAGE_ID}/resource/{RESOURCE_ID}/download/50400-2008.7z"
)


def main() -> None:
    notes: list[str] = []
    proposed = "pending"
    license_note = "See data.gov.il package page"

    with client() as http:
        try:
            pkg = http.get(f"https://data.gov.il/api/3/action/package_show?id={PACKAGE_ID}")
            save("cbs", "package_show", pkg.content, suffix=".json")
            if pkg.status_code == 200:
                payload = pkg.json().get("result", {})
                save_json("cbs", "package_parsed", payload)
                license_note = payload.get("license_title") or license_note
                title = payload.get("title", "")
                notes.append(f"package: {title[:80]}")
                proposed = "go"
        except Exception as exc:  # noqa: BLE001
            notes.append(f"package_show failed: {exc}")

        try:
            head = http.head(DOWNLOAD_URL)
            notes.append(f"bulk HEAD HTTP {head.status_code}")
            if head.status_code == 200:
                proposed = "go"
        except Exception as exc:  # noqa: BLE001
            notes.append(f"bulk HEAD failed: {exc}")

    print_summary(
        source="Statistical areas (CBS)",
        url=DOWNLOAD_URL,
        license_note=license_note,
        access="National ZIP shapefile on data.gov.il/e.data.gov.il; bulk load (reference dataset)",
        published_at="n/a",
        lag="n/a",
        history="n/a",
        proposed=proposed,
        notes="; ".join(notes) or f"Package landing: {PACKAGE_URL}",
    )


if __name__ == "__main__":
    main()
