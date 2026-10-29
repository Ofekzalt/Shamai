"""Probe Tel Aviv-Yafo municipal address / geocode layer."""

from __future__ import annotations

from scripts.spike._common import client, print_summary, save, save_json

TLV_GIS = "https://gisn.tel-aviv.gov.il/arcgis/rest/services"
ADDRESS_LAYER = (
    "https://gisn.tel-aviv.gov.il/arcgis/rest/services/IView2/MapServer/527/query"
    "?where=t_rechov%20LIKE%20%27%25%D7%93%D7%99%D7%96%D7%A0%D7%92%25%27"
    "&outFields=t_ktovet_melea,lon,lat,ms_gush,ms_chelka&returnGeometry=false"
    "&resultRecordCount=5&f=json"
)


def main() -> None:
    features = 0
    notes: list[str] = []

    with client() as http:
        try:
            meta = http.get(f"{TLV_GIS}/IView2/MapServer/527?f=pjson")
            save("geocode_tlv", "layer527_meta", meta.content, suffix=".json")
            notes.append(f"layer527 meta HTTP {meta.status_code}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"meta failed: {exc}")

        try:
            resp = http.get(ADDRESS_LAYER)
            save("geocode_tlv", "address_sample", resp.content, suffix=".json")
            if resp.status_code == 200:
                payload = resp.json()
                save_json("geocode_tlv", "address_sample_parsed", payload)
                features = len(payload.get("features", []))
                notes.append(f"Dizengoff sample features={features}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"query failed: {exc}")

    proposed = "go" if features else "pending"
    access = (
        "ArcGIS REST IView2/MapServer/527 (כתובות); filter t_rechov, ms_bayit; lon/lat WGS84"
        if features
        else "Layer 527 reachable but sample query returned 0 rows"
    )

    print_summary(
        source="Geocode: TLV municipal",
        url=f"{TLV_GIS}/IView2/MapServer/527",
        license_note=(
            "Tel Aviv municipal GIS (viewer disclaimer: informational only). "
            "Confirm storage/cache with city open-data terms before production scale."
        ),
        access=access,
        published_at="n/a",
        lag="n/a",
        history="n/a",
        proposed=proposed,
        notes="; ".join(notes),
    )


if __name__ == "__main__":
    main()
