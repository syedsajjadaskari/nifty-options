#!/usr/bin/env python3
"""Script to validate downloaded historical candle dataset and generate audit reports."""

import sys

from nifty_trading.data.validator import DataQualityValidator


def main() -> int:
    print("==================================================")
    print("NIFTY 50 DATA QUALITY AUDIT & VALIDATION")
    print("==================================================")

    validator = DataQualityValidator()
    report = validator.run_audit()

    print(f"\nInstrument:                    {report.instrument}")
    print(f"Timeframe:                     {report.timeframe}")
    print(f"Total Candles:                 {report.total_candle_count:,}")
    print(f"First Available Timestamp:     {report.first_timestamp}")
    print(f"Last Available Timestamp:      {report.last_timestamp}")
    print(f"Trading Dates Covered:         {report.trading_dates_count} / {report.expected_trading_days_count} expected")
    print(f"Missing Trading Days:          {report.missing_trading_days_count}")
    print(f"Duplicate Timestamps:          {report.duplicate_timestamps_count}")
    print(f"Null / Invalid OHLC Rows:      {report.null_or_invalid_ohlc_count}")
    print(f"Price Inconsistencies:         {report.price_inconsistency_count}")
    print(f"Strictly Monotonic Ordering:   {report.timestamp_order_strictly_monotonic}")
    print(f"Session Boundary Violations:   {report.session_boundary_violations_count}")
    print(f"Incomplete Days (< 376 bars):  {report.incomplete_days_count}")
    print(f"Missing Minute Bars:           {report.missing_minute_bars_count}")
    print(f"Storage Size on Disk:          {report.total_storage_size_mb} MB ({report.total_storage_size_bytes:,} bytes)")
    print(f"DuckDB Query Access:           {'SUCCESS' if report.duckdb_read_success else 'FAILED'}")

    print("\nMonthly Coverage:")
    for m in report.monthly_coverage:
        print(f"  {m['month']}: {m['actual_trading_days']}/{m['expected_trading_days']} days | {m['candle_count']:,} candles | {m['coverage_pct']}%")

    print("\n--------------------------------------------------")
    print("REPORTS GENERATED:")
    print("  - reports/data_quality/nifty50_1m_audit.json")
    print("  - reports/data_quality/nifty50_1m_summary.md")
    print("--------------------------------------------------")

    return 0 if (report.total_candle_count > 0 and report.duplicate_timestamps_count == 0 and report.price_inconsistency_count == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
