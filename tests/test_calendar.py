"""Unit tests for NSE calendar, holiday classification, and trading session hours."""

from datetime import date

from nifty_trading.data.calendar import NSECalendar


def test_calendar_weekends():
    """Verify Saturday and Sunday are marked as weekends and non-trading."""
    cal = NSECalendar()
    # 2025-09-06 is Saturday, 2025-09-07 is Sunday
    assert cal.is_weekend(date(2025, 9, 6)) is True
    assert cal.is_weekend(date(2025, 9, 7)) is True
    assert cal.is_trading_day(date(2025, 9, 6)) is False
    assert cal.is_trading_day(date(2025, 9, 7)) is False


def test_calendar_official_holidays():
    """Verify official NSE holidays are classified correctly."""
    cal = NSECalendar()
    # Gandhi Jayanti: 2025-10-02
    assert cal.is_holiday(date(2025, 10, 2)) is True
    assert cal.is_trading_day(date(2025, 10, 2)) is False
    assert "NSE Holiday" in cal.classify_date_status(date(2025, 10, 2))

    # Republic Day: 2026-01-26
    assert cal.is_holiday(date(2026, 1, 26)) is True
    assert cal.is_trading_day(date(2026, 1, 26)) is False


def test_calendar_special_session():
    """Verify Diwali Muhurat trading special session is recognized as active trading."""
    cal = NSECalendar()
    assert cal.is_trading_day(date(2025, 10, 21)) is True
    assert "Muhurat Trading" in cal.classify_date_status(date(2025, 10, 21))
