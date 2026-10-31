from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.logging import configure_logging
from app.infrastructure.gis.http import default_http_client
from app.modules.property_data.dto import NearbyTransactionsQuery
from app.modules.property_data.service import geocode_address, nearby_transactions
from app.modules.property_data.service_cbs import load_statistical_areas_from_zip
from app.modules.property_data.service_transactions import load_transactions_for_point
from app.modules.property_data.window import transaction_window_start


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="property_data")
    sub = parser.add_subparsers(dest="command", required=True)

    geocode = sub.add_parser("geocode")
    geocode.add_argument("--street", required=True)
    geocode.add_argument("--house", required=True)

    tx = sub.add_parser("transactions")
    tx.add_argument("--lon", type=float, required=True)
    tx.add_argument("--lat", type=float, required=True)
    tx.add_argument("--as-of", dest="as_of", default=None)

    nearby = sub.add_parser("nearby")
    nearby.add_argument("--lon", type=float, required=True)
    nearby.add_argument("--lat", type=float, required=True)
    nearby.add_argument("--radius-m", type=float, default=500.0)
    nearby.add_argument("--as-of", dest="as_of", default=None)

    cbs = sub.add_parser("statistical-areas")
    cbs.add_argument("zip_path", type=Path)

    args = parser.parse_args(argv)
    configure_logging(get_settings().log_level)
    session_factory = get_session_factory()
    with default_http_client() as client, session_factory() as session:
        if args.command == "geocode":
            record = geocode_address(session, client, street=args.street, house_number=args.house)
            session.commit()
            print(f"{record.lat},{record.lon}")
            return 0
        if args.command == "transactions":
            as_of = _parse_as_of(args.as_of)
            window_start = transaction_window_start(as_of)
            result = load_transactions_for_point(
                session,
                client,
                lon=args.lon,
                lat=args.lat,
                window_start=window_start,
                window_end=as_of,
                settings=get_settings(),
            )
            session.commit()
            print(result.model_dump_json())
            return 0
        if args.command == "nearby":
            as_of = _parse_as_of(args.as_of)
            result = nearby_transactions(
                session,
                client,
                NearbyTransactionsQuery(
                    lon=args.lon, lat=args.lat, radius_m=args.radius_m, as_of=as_of
                ),
            )
            session.commit()
            print(result.model_dump_json())
            return 0
        if args.command == "statistical-areas":
            count = load_statistical_areas_from_zip(session, args.zip_path)
            session.commit()
            print(count)
            return 0
    return 1


def _parse_as_of(value: str | None) -> datetime:
    if value is None:
        return datetime.now(tz=UTC)
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
