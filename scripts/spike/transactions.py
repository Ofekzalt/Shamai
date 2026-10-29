"""Probe residential transaction sources (Nadlan vs odata.org.il open mirror)."""

from __future__ import annotations

from scripts.spike._common import client, print_summary, save, save_json

NADLAN_HOME = "https://www.nadlan.gov.il/"
ODATA_PACKAGE = "84f2bc2d-87a0-474e-a3ea-63d7bb9b5447"
ODATA_DATASTORE_RESOURCE = "24eabceb-faea-4f92-9e94-df710c29cae7"
ODATA_DATASTORE_URL = (
    "https://www.odata.org.il/api/3/action/datastore_search"
    f"?resource_id={ODATA_DATASTORE_RESOURCE}&limit=3"
)
TLV_FILTER = (
    "https://www.odata.org.il/api/3/action/datastore_search"
    f"?resource_id={ODATA_DATASTORE_RESOURCE}"
    "&filters=%7B%22city_name%22%3A%22%D7%AA%D7%9C%20%D7%90%D7%91%D7%99%D7%91%20-%D7%99%D7%A4%D7%95%22%7D&limit=2"
)


def main() -> None:
    nadlan_note = ""
    api_ok = False
    api_note = ""
    tlv_total = 0
    license_note = ""

    with client() as http:
        try:
            nadlan_resp = http.get(NADLAN_HOME)
            save("transactions", "nadlan_home", nadlan_resp.text[:20000], suffix=".html")
            nadlan_note = (
                f"nadlan.gov.il HTTP {nadlan_resp.status_code}; public search UI only — "
                "no bulk API or storage permission verified."
            )
        except Exception as exc:  # noqa: BLE001 — spike
            nadlan_note = f"Nadlan home unreachable: {exc}"

        try:
            pkg = http.get(f"https://www.odata.org.il/api/3/action/package_show?id={ODATA_PACKAGE}")
            save("transactions", "odata_package", pkg.content, suffix=".json")
            if pkg.status_code == 200:
                payload = pkg.json().get("result", {})
                license_note = payload.get("license_title") or "See odata.org.il package page"
                save_json("transactions", "odata_package_parsed", payload)
        except Exception as exc:  # noqa: BLE001
            license_note = f"Could not read package license: {exc}"

        try:
            api_resp = http.get(ODATA_DATASTORE_URL)
            save("transactions", "odata_datastore_sample", api_resp.content, suffix=".json")
            if api_resp.status_code == 200:
                payload = api_resp.json()
                records = payload.get("result", {}).get("records", [])
                api_ok = len(records) > 0
                if api_ok:
                    save_json("transactions", "odata_datastore_parsed", payload)
                    keys = sorted(records[0].keys())
                    api_note = f"datastore_search ok; fields include {keys[:14]}"
        except Exception as exc:  # noqa: BLE001
            api_note = f"odata datastore probe failed: {exc}"

        try:
            tlv_resp = http.get(TLV_FILTER)
            save("transactions", "odata_tlv_filter", tlv_resp.content, suffix=".json")
            if tlv_resp.status_code == 200:
                tlv_total = tlv_resp.json().get("result", {}).get("total", 0)
        except Exception as exc:  # noqa: BLE001
            api_note = f"{api_note}; TLV filter failed: {exc}"

    if api_ok:
        proposed = "go"
        url = (
            f"https://www.odata.org.il/dataset/{ODATA_PACKAGE}/resource/{ODATA_DATASTORE_RESOURCE}"
        )
        access = (
            "CKAN datastore_search on odata.org.il (CSV mirror of tax nadlan dump); "
            "filter city_name, dealdatetime; optional 71MB ZIP bulk"
        )
        published_at = "no"
        lag = "90"
        history = "yes (historical deals in open dump; not live Nadlan UI)"
        notes = (
            f"{nadlan_note} Alternate mirror only — not live nadlan.gov.il scrape. "
            f"TLV rows in dump (filter): {tlv_total}. {api_note}"
        )
    else:
        proposed = "no-go"
        url = NADLAN_HOME
        access = "No verified licensed bulk endpoint"
        published_at = "unknown"
        lag = "90"
        history = "unknown"
        notes = f"{nadlan_note}. {api_note}"

    print_summary(
        source="Transactions (nadlan / alt.)",
        url=url,
        license_note=license_note or "Creative Commons Attribution (odata package when reachable)",
        access=access,
        published_at=published_at,
        lag=lag,
        history=history,
        proposed=proposed,
        notes=notes,
    )


if __name__ == "__main__":
    main()
