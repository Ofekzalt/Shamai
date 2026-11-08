#!/usr/bin/env bash
# Load reference data for evals and manual QA. Requires DATABASE_URL and network.
set -euo pipefail
cd "$(dirname "$0")/.."

CBS_URL="https://e.data.gov.il/dataset/6b729165-dc9c-49b3-afc6-eceabd8fef70/resource/3b88cb58-62cd-43ea-9156-7b81ead557b1/download/50400-2008.7z"
mkdir -p data
if [[ ! -f data/statistical-areas-2008.7z ]]; then
  echo "Downloading CBS statistical areas..."
  curl -fsSL -o data/statistical-areas-2008.7z "$CBS_URL"
fi

echo "Loading statistical areas..."
uv run python -m app.modules.property_data statistical-areas data/statistical-areas-2008.7z

GEOCODES=(
  "רוטשילד:1"
  "דיזנגוף:50"
  "אבן גבירול:30"
  "אלנבי:100"
  "פרישמן:20"
  "בן יהודה:12"
  "מלך ג'ורג':25"
  "ביאליק:8"
  "ארלוזורוב:45"
)

for pair in "${GEOCODES[@]}"; do
  street="${pair%%:*}"
  house="${pair##*:}"
  echo "Geocode ${street} ${house}..."
  uv run python -m app.modules.property_data geocode --street "$street" --house "$house"
done

# Load transactions and planning around the golden-set centroid (Rothschild 1).
LON=34.7815
LAT=32.0642
AS_OF="2025-01-01T00:00:00+00:00"
echo "Loading transactions near ${LON},${LAT}..."
uv run python -m app.modules.property_data transactions --lon "$LON" --lat "$LAT" --as-of "$AS_OF"
echo "Loading iplan at point..."
uv run python -m app.modules.planning plans --lon "$LON" --lat "$LAT" --as-of "$AS_OF" || {
  echo "iplan load failed (see docs/data-sources.md TLS note); continuing"
}
echo "Loading renewal polygons at point..."
uv run python -m app.modules.planning renewal --lon "$LON" --lat "$LAT" --as-of "$AS_OF"

echo "Done. Verify with: psql ... -c \"select count(*) from transactions;\""
