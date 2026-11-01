#!/usr/bin/env python3
"""Script to download historical NIFTY 50 index 1-minute OHLCV candles."""

import argparse
import sys

from nifty_trading.data.downloader import HistoricalDataDownloader


def main() -> int:
    parser = argparse.ArgumentParser(description="Download NIFTY 50 1-minute historical data")
    parser.add_argument("--start", type=str, default="2025-09-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2026-08-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Force redownload of completed batches")
    args = parser.parse_args()

    print("==================================================")
    print("NIFTY 50 1-MINUTE HISTORICAL DATA DOWNLOADER")
    print("==================================================")
    print(f"Target Period: {args.start} to {args.end}")
    print(f"Force Redownload: {args.force}\n")

    downloader = HistoricalDataDownloader()
    stats = downloader.download_range(start_date=args.start, end_date=args.end, force=args.force)

    print("\n--------------------------------------------------")
    print("DOWNLOAD SUMMARY")
    print("--------------------------------------------------")
    print(f"Total Monthly Batches: {stats['total_batches']}")
    print(f"Completed Batches:     {stats['completed_batches']}")
    print(f"Skipped (Cached):      {stats['skipped_batches']}")
    print(f"Failed Batches:       {stats['failed_batches']}")
    print(f"Total Candles Saved:  {stats['total_candles']:,}")
    print(f"Total Rejected Rows:  {stats['total_rejected']}")
    print("--------------------------------------------------")

    return 0 if stats["failed_batches"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
