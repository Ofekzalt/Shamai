"""Probe Tel Aviv urban renewal / Pinui-Binui polygons."""

from __future__ import annotations

from scripts.spike._common import client, print_summary, save, save_json

TLV_GIS = "https://gisn.tel-aviv.gov.il/arcgis/rest/services/IView2/MapServer"
TABA_RENEWAL = (
    f"{TLV_GIS}/528/query"
    "?where=sw_hitchadshut_ironit%3D1"
    "&outFields=taba,t_status,tr_shinuy_status,sw_hitchadshut_ironit"
    "&returnGeometry=true&resultRecordCount=3&f=json"
)
HOUSING_PROJECTS = (
    f"{TLV_GIS}/746/query"
    "?where=1%3D1&outFields=Project_Name,Status,Address,Taba_Link"
    "&returnGeometry=true&resultRecordCount=2&f=json"
)


def main() -> None:
    taba_features = 0
    housing_features = 0
    notes: list[str] = []

    with client() as http:
        try:
            resp = http.get(TABA_RENEWAL)
            save("tlv_renewal", "taba_renewal", resp.content, suffix=".json")
            if resp.status_code == 200:
                payload = resp.json()
                save_json("tlv_renewal", "taba_renewal_parsed", payload)
                taba_features = len(payload.get("features", []))
                notes.append(f"TABA sw_hitchadshut_ironit features={taba_features}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"TABA query: {exc}")

        try:
            resp = http.get(HOUSING_PROJECTS)
            save("tlv_renewal", "housing_projects", resp.content, suffix=".json")
            if resp.status_code == 200:
                housing_features = len(resp.json().get("features", []))
                notes.append(f"housing projects layer 746 features={housing_features}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"housing query: {exc}")

    if taba_features > 0:
        proposed = "go"
        access = (
            "ArcGIS MapServer/528 (תוכניות בניין עיר) polygons; filter sw_hitchadshut_ironit=1; "
            "supplement layer 746 (פרויקטים דיור בהישג יד) points"
        )
        published_at = "partial (tr_shinuy_status on polygon snapshot)"
        history = "false"
    else:
        proposed = "pending"
        access = "Expected TABA renewal filter on layer 528"
        published_at = "unknown"
        history = "unknown"

    print_summary(
        source="Tel Aviv renewal / Pinui-Binui",
        url=f"{TLV_GIS}/528",
        license_note="Tel Aviv municipal GIS — same terms as other IView2 layers",
        access=access,
        published_at=published_at,
        lag="7",
        history=history,
        proposed=proposed,
        notes=(
            "No layer named Pinui-Binui in catalog; urban renewal via TABA flag + status dates. "
            + "; ".join(notes)
        ),
    )


if __name__ == "__main__":
    main()
