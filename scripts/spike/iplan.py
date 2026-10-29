"""Probe iplan / XPLAN plan boundaries and status."""

from __future__ import annotations

import json

from scripts.spike._common import client, curl_get, print_summary, save, save_json

XPLAN_MAPSERVER = (
    "https://ags.iplan.gov.il/arcgisiplan/rest/services/PlanningPublic/Xplan/MapServer"
)
PLAN_META_QUERY = (
    f"{XPLAN_MAPSERVER}/1/query"
    "?where=1%3D1&outFields=pl_number,pl_name,depositing_date,last_update_date,pl_date_advertise"
    "&returnGeometry=false&resultRecordCount=2&f=json"
)
POLYGON_QUERY = (
    f"{XPLAN_MAPSERVER}/3/query"
    "?where=1%3D1&outFields=pl_number,mp_id,pl_name&returnGeometry=true&resultRecordCount=1&f=json"
)
IPLAN_PORTAL = "https://www.iplan.gov.il/"


def main() -> None:
    meta_rows = 0
    polygon_rows = 0
    notes: list[str] = []

    with client() as http:
        try:
            catalog = http.get(f"{XPLAN_MAPSERVER}?f=pjson")
            save("iplan", "mapserver_catalog", catalog.content, suffix=".json")
            notes.append(f"MapServer catalog HTTP {catalog.status_code}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"catalog: {exc}")

        try:
            resp = http.get(PLAN_META_QUERY)
            save("iplan", "plan_meta", resp.content, suffix=".json")
            if resp.status_code == 200:
                payload = resp.json()
                save_json("iplan", "plan_meta_parsed", payload)
                meta_rows = len(payload.get("features", []))
                notes.append(f"plan metadata rows={meta_rows}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"metadata httpx: {exc}")
            try:
                status, body = curl_get(PLAN_META_QUERY)
                save("iplan", "plan_meta_curl", body, suffix=".json")
                if status == 200:
                    payload = json.loads(body)
                    meta_rows = len(payload.get("features", []))
                    save_json("iplan", "plan_meta_curl_parsed", payload)
                    notes.append(f"plan metadata rows (curl)={meta_rows}")
            except Exception as curl_exc:  # noqa: BLE001
                notes.append(f"metadata curl: {curl_exc}")

        try:
            resp = http.get(POLYGON_QUERY)
            save("iplan", "plan_polygon", resp.content, suffix=".json")
            if resp.status_code == 200:
                polygon_rows = len(resp.json().get("features", []))
                notes.append(f"polygon rows={polygon_rows}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"polygon httpx: {exc}")
            try:
                status, body = curl_get(POLYGON_QUERY)
                save("iplan", "plan_polygon_curl", body, suffix=".json")
                if status == 200:
                    polygon_rows = len(json.loads(body).get("features", []))
                    notes.append(f"polygon rows (curl)={polygon_rows}")
            except Exception as curl_exc:  # noqa: BLE001
                notes.append(f"polygon curl: {curl_exc}")

        try:
            portal = http.get(IPLAN_PORTAL)
            save("iplan", "portal", portal.text[:10000], suffix=".html")
            notes.append(f"portal HTTP {portal.status_code}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"portal: {exc}")

    if meta_rows > 0 and polygon_rows > 0:
        proposed = "go"
        access = (
            "ArcGIS REST Xplan MapServer: layer 1 metadata, layer 3 polygons; "
            "query by pl_number/mp_id"
        )
        published_at = (
            "partial (depositing_date, pl_date_advertise, last_update_date; "
            "not native event stream)"
        )
        history = "false"
    elif meta_rows > 0 or polygon_rows > 0:
        proposed = "go"
        access = "Partial Xplan MapServer response in spike"
        published_at = "partial"
        history = "false"
    else:
        proposed = "pending"
        access = "Xplan MapServer did not return sample rows"
        published_at = "unknown"
        history = "unknown"

    print_summary(
        source="iplan / XPLAN",
        url=XPLAN_MAPSERVER,
        license_note=(
            "Ministry of Construction and Housing / Planning Administration public services"
        ),
        access=access,
        published_at=published_at,
        lag="14",
        history=history,
        proposed=proposed,
        notes=(
            "Online plans from 2011+ per portal; Phase 4 synthesizes plan_status_events from "
            "date columns — no append-only status feed verified. " + "; ".join(notes)
        ),
    )


if __name__ == "__main__":
    main()
