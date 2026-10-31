from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.modules.property_data.providers import cbs
from app.modules.property_data.repository import upsert_statistical_area


def load_statistical_areas_from_zip(session: Session, path: Path) -> int:
    count = 0
    for code, wkt in cbs.iter_shapes_from_archive(path):
        upsert_statistical_area(session, cbs_code=code, wkt=wkt)
        count += 1
    session.flush()
    return count
