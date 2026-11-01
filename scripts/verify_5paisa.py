#!/usr/bin/env python3
"""Script to verify 5paisa broker connectivity and read-only API access."""

import sys

from nifty_trading.broker.auth import FivePaisaAuthManager


def main() -> int:
    auth_manager = FivePaisaAuthManager()
    result = auth_manager.verify_connection()

    print("5PAISA CONNECTION VERIFICATION\n")
    print(f"SDK: {result.sdk_version}")
    print(f"Authentication: {'SUCCESS' if result.auth_success else 'FAILED'}")
    print(f"Read-only broker API: {'SUCCESS' if result.readonly_api_success else 'FAILED'}")
    print(f"Timestamp: {result.timestamp_ist}")
    print(f"Operational mode: {result.operational_mode}")
    print(f"Live orders: {'ENABLED' if result.live_orders_enabled else 'DISABLED'}")

    if result.account_summary:
        print(f"Account check: {result.account_summary}")

    if result.error_message:
        print(f"\n[NOTE / DIAGNOSTIC]: {result.error_message}")

    return 0 if (result.auth_success and result.readonly_api_success) else 1


if __name__ == "__main__":
    sys.exit(main())
