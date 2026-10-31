from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from app.core.database import get_session_factory
from app.infrastructure.gis.http import default_http_client
from app.modules.planning.dto import PlansAtPointQuery, RenewalAtPointQuery
from app.modules.planning.service import plans_at_point, renewal_at_point


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="planning")
    sub = parser.add_subparsers(dest="command", required=True)

    plans = sub.add_parser("plans")
    plans.add_argument("--lon", type=float, required=True)
    plans.add_argument("--lat", type=float, required=True)
    plans.add_argument("--as-of", dest="as_of", default=None)

    renewal = sub.add_parser("renewal")
    renewal.add_argument("--lon", type=float, required=True)
    renewal.add_argument("--lat", type=float, required=True)
    renewal.add_argument("--as-of", dest="as_of", default=None)

    args = parser.parse_args(argv)
    as_of = _parse_as_of(args.as_of)
    session_factory = get_session_factory()
    with default_http_client() as client, session_factory() as session:
        if args.command == "plans":
            result = plans_at_point(
                session,
                client,
                PlansAtPointQuery(lon=args.lon, lat=args.lat, as_of=as_of),
            )
            session.commit()
            print(result.model_dump_json())
            return 0
        if args.command == "renewal":
            result = renewal_at_point(
                session,
                client,
                RenewalAtPointQuery(lon=args.lon, lat=args.lat, as_of=as_of),
            )
            session.commit()
            print(result.model_dump_json())
            return 0
    return 1


def _parse_as_of(value: str | None) -> datetime:
    if value is None:
        return datetime.now(tz=UTC)
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
