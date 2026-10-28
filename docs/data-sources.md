# Data sources

Fill this during the day-1–2 spike. **No loader ships without a row here.**

| Source | URL | License / terms | Access | `published_at`? | Lag if estimated | `history_available` | Go/no-go | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Transactions (nadlan / alt.) | | | | | | | pending | Throttling ≠ permission |
| Tel Aviv renewal / Pinui-Binui | | | | | | | pending | Snapshot vs events |
| iplan / XPLAN | | | | | | | pending | Status history required for as-of plans |
| Statistical areas (CBS) | | | | | | n/a | pending | |
| Geocode: TLV municipal | | | | n/a | n/a | n/a | pending | First choice |
| Geocode: GovMap | | | | n/a | n/a | n/a | pending | Fallback only |

Conservative lag is per source (days). Timezone for `as_of` defaults: Asia/Jerusalem.
