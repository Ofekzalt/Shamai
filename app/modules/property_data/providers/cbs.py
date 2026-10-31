from __future__ import annotations

import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

import py7zr
import shapefile
from pyproj import Transformer

_ITM_TO_WGS84 = Transformer.from_crs("EPSG:2039", "EPSG:4326", always_xy=True)


def iter_shapes_from_archive(path: Path) -> Iterator[tuple[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".7z":
        yield from _iter_from_7z(path)
    elif suffix == ".zip":
        yield from _iter_from_zip(path)
    else:
        raise ValueError(f"Unsupported archive type: {suffix}")


def _iter_from_zip(path: Path) -> Iterator[tuple[str, str]]:
    with zipfile.ZipFile(path, "r") as archive:
        shp_name = next((n for n in archive.namelist() if n.lower().endswith(".shp")), None)
        if shp_name is None:
            raise FileNotFoundError("No .shp in archive")
        base = shp_name[:-4]
        shx = next(n for n in archive.namelist() if n.lower() == f"{base.lower()}.shx")
        dbf = next(n for n in archive.namelist() if n.lower() == f"{base.lower()}.dbf")
        with (
            archive.open(shp_name) as shp_io,
            archive.open(shx) as shx_io,
            archive.open(dbf) as dbf_io,
        ):
            yield from _iter_reader(shapefile.Reader(shp=shp_io, shx=shx_io, dbf=dbf_io))


def _iter_from_7z(path: Path) -> Iterator[tuple[str, str]]:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        with py7zr.SevenZipFile(path, mode="r") as archive:
            archive.extractall(path=out)
        shp = next(out.rglob("*.shp"), None)
        if shp is None:
            raise FileNotFoundError("No .shp in 7z archive")
        reader = shapefile.Reader(str(shp))
        yield from _iter_reader(reader)


def _iter_reader(reader: shapefile.Reader) -> Iterator[tuple[str, str]]:
    field_names = [f[0] for f in reader.fields[1:]]
    code_names = {"stat11", "cbs_code", "smlt"}
    code_idx = next(
        (i for i, name in enumerate(field_names) if name.lower() in code_names),
        0,
    )
    for shape_rec in reader.iterShapeRecords():
        code = str(shape_rec.record[code_idx])
        wkt = _shape_to_wkt(shape_rec.shape)
        if wkt:
            yield code, wkt


def _shape_to_wkt(shape: shapefile.Shape) -> str | None:
    if shape.shapeType not in {shapefile.POLYGON, shapefile.POLYGONZ, shapefile.POLYGONM}:
        return None
    parts = list(shape.parts) + [len(shape.points)]
    rings: list[str] = []
    for start, end in zip(parts, parts[1:], strict=False):
        ring = shape.points[start:end]
        if len(ring) < 3:
            continue
        coords = ", ".join(_project_xy(x, y) for x, y in ring)
        rings.append(f"({coords})")
    if not rings:
        return None
    return f"MULTIPOLYGON(({','.join(rings)}))"


def _project_xy(x: float, y: float) -> str:
    lon, lat = _ITM_TO_WGS84.transform(x, y)
    return f"{lon} {lat}"
