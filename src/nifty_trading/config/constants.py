"""Global constants and exchange parameters for NIFTY trading automation."""

from zoneinfo import ZoneInfo

# Timezone
IST = ZoneInfo("Asia/Kolkata")

# Market Session Timings (IST)
MARKET_OPEN_TIME = "09:15:00"
MARKET_CLOSE_TIME = "15:30:00"

# 5paisa Exchange Segment Definitions
EXCHANGE_NSE = "N"
EXCHANGE_BSE = "B"
EXCHANGE_MCX = "M"

EXCHANGE_SEGMENT_CASH = "C"
EXCHANGE_SEGMENT_DERIVATIVE = "D"
EXCHANGE_SEGMENT_CURRENCY = "U"

# Target Instrument Defaults
NIFTY_50_INDEX_SYMBOL = "NIFTY 50"
NIFTY_50_INDEX_EXCH = "N"
NIFTY_50_INDEX_SEGMENT = "C"

# 5paisa URLs
FIVEPAISA_SCRIP_MASTER_URL = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/ScripMaster/segment/All"
FIVEPAISA_HISTORICAL_DATA_ROUTE = "https://openapi.5paisa.com/V2/historical/"

