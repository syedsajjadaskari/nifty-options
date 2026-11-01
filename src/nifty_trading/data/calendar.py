"""NSE Trading Calendar, Holiday Schedule, and Market Hours validation."""

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from nifty_trading.config.constants import IST

# Standard NSE Trading Session Hours (Cash & Index)
MARKET_OPEN = time(9, 15, 0)
MARKET_CLOSE = time(15, 30, 0)

# Expected trading minutes in a normal day (09:15 to 15:30 inclusive in 5paisa is 376 candles)
NORMAL_DAY_CANDLE_COUNT = 376

# Recognized NSE Trading Holidays (Cash Market) for 2025 and 2026
# Source: NSE Official Trading Holiday Circulars
NSE_HOLIDAYS: set[str] = {
    # 2025
    "2025-01-26",  # Republic Day (Sunday)
    "2025-02-26",  # Maha Shivratri
    "2025-03-14",  # Holi
    "2025-03-31",  # Id-Ul-Fitr
    "2025-04-10",  # Mahavir Jayanti
    "2025-04-14",  # Dr. Baba Saheb Ambedkar Jayanti
    "2025-04-18",  # Good Friday
    "2025-05-01",  # Maharashtra Day
    "2025-06-07",  # Bakri Id (Saturday)
    "2025-07-06",  # Moharram (Sunday)
    "2025-08-15",  # Independence Day
    "2025-10-02",  # Mahatma Gandhi Jayanti
    "2025-10-21",  # Diwali Laxmi Pujan (Muhurat trading evening session)
    "2025-10-22",  # Diwali Balipratipada
    "2025-11-05",  # Prakash Gurpurb / Guru Nanak Jayanti
    "2025-12-25",  # Christmas
    # 2026
    "2026-01-26",  # Republic Day
    "2026-02-17",  # Maha Shivratri
    "2026-03-03",  # Holi
    "2026-03-20",  # Id-Ul-Fitr
    "2026-03-27",  # Ram Navami
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. Baba Saheb Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-05-27",  # Bakri Id / Eid-ul-Adha
    "2026-06-26",  # Muharram
    "2026-08-15",  # Independence Day (Saturday)
}

# Special Trading Sessions (e.g. Diwali Muhurat Trading: 1 hour special evening session)
SPECIAL_SESSIONS: dict[str, dict[str, Any]] = {
    "2025-10-21": {"type": "Muhurat Trading", "expected_candles": 61},
}


class NSECalendar:
    """NSE Trading calendar utility for session verification and holiday classification."""

    def __init__(
        self,
        holidays: set[str] | None = None,
        tz: ZoneInfo = IST,
    ):
        self.holidays = holidays if holidays is not None else NSE_HOLIDAYS
        self.tz = tz

    def is_weekend(self, dt: date | datetime) -> bool:
        """Check if date falls on Saturday (5) or Sunday (6)."""
        d = dt.date() if isinstance(dt, datetime) else dt
        return d.weekday() in (5, 6)

    def is_holiday(self, dt: date | datetime) -> bool:
        """Check if date is an official NSE market holiday."""
        d_str = (dt.date() if isinstance(dt, datetime) else dt).strftime("%Y-%m-%d")
        return d_str in self.holidays

    def is_trading_day(self, dt: date | datetime) -> bool:
        """Check whether date is an active trading session."""
        d = dt.date() if isinstance(dt, datetime) else dt
        d_str = d.strftime("%Y-%m-%d")

        # Special session override (even if on weekend or holiday date)
        if d_str in SPECIAL_SESSIONS:
            return True

        if self.is_weekend(d):
            return False

        if self.is_holiday(d):
            return False

        return True

    def get_trading_days(self, start_date: date, end_date: date) -> list[date]:
        """Generate list of expected trading dates between start and end date inclusive."""
        current = start_date
        trading_days = []
        while current <= end_date:
            if self.is_trading_day(current):
                trading_days.append(current)
            current += timedelta(days=1)
        return trading_days

    def classify_date_status(self, d: date) -> str:
        """Classify date into closure reason or trading session."""
        d_str = d.strftime("%Y-%m-%d")
        if d_str in SPECIAL_SESSIONS:
            return f"Special Session ({SPECIAL_SESSIONS[d_str]['type']})"
        if self.is_weekend(d):
            return "Expected market closure (Weekend)"
        if self.is_holiday(d):
            return "Expected market closure (NSE Holiday)"
        return "Trading Day"
