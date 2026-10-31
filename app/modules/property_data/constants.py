TRANSACTION_LAG_DAYS = 90

TRANSACTION_SOURCE = "odata_nadlan"

ODATA_DATASTORE_RESOURCE = "24eabceb-faea-4f92-9e94-df710c29cae7"
ODATA_SEARCH_URL = "https://www.odata.org.il/api/3/action/datastore_search"
TLV_CITY = "תל אביב - יפו"
SOURCE_ROW_FIELD = "_id"

TLV_ADDRESS_LAYER = "https://gisn.tel-aviv.gov.il/arcgis/rest/services/IView2/MapServer/527/query"
GEOCODE_SOURCE = "tlv_municipal"
CANDIDATE_LIMIT = 50
LOAD_RADIUS_M = 2000.0
# Matches valuation TIME_DAYS[-1] (1095); property_data must not import valuation.
LOAD_LOOKBACK_DAYS = 1095
