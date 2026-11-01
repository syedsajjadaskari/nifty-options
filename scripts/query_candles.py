#!/usr/bin/env python3
"""Interactive query script demonstrating zero-overhead DuckDB Parquet queries."""

import sys

from nifty_trading.data.duckdb_interface import DuckDBEngine


def main() -> int:
    engine = DuckDBEngine()

    print("==================================================")
    print("DUCKDB HISTORICAL QUERY ENGINE")
    print("==================================================")

    # 1. Total row count & high-level stats
    stats_df = engine.get_summary_stats()
    print("\n[Query 1] High-Level Dataset Aggregates:")
    print(stats_df.to_string(index=False))

    # 2. Sample first 5 candles
    print("\n[Query 2] First 5 Candles (Ascending Timestamp):")
    sample_df = engine.sample_candles(limit=5)
    print(sample_df.to_string(index=False))

    # 3. Monthly candle aggregates
    monthly_sql = """
    SELECT
        strftime(timestamp, '%Y-%m') AS month,
        count(*) AS candle_count,
        round(min(low), 2) AS month_low,
        round(max(high), 2) AS month_high,
        round(avg(close), 2) AS avg_close,
        count(distinct strftime(timestamp, '%Y-%m-%d')) AS trading_days
    FROM nifty50
    GROUP BY strftime(timestamp, '%Y-%m')
    ORDER BY month ASC
    """
    print("\n[Query 3] Monthly Aggregations:")
    monthly_df = engine.query(monthly_sql)
    print(monthly_df.to_string(index=False))

    # 4. Sample intraday session (First day of dataset)
    if not sample_df.empty:
        first_date = str(sample_df["timestamp"].iloc[0])[:10]
        day_sql = f"""
        SELECT
            strftime(timestamp, '%H:%M:%S') AS time_ist,
            open, high, low, close, volume
        FROM nifty50
        WHERE strftime(timestamp, '%Y-%m-%d') = '{first_date}'
        LIMIT 5
        """
        print(f"\n[Query 4] Sample Intraday Candles for {first_date}:")
        day_df = engine.query(day_sql)
        print(day_df.to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
