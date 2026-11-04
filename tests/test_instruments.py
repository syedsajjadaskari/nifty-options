"""Unit tests for instrument master parsing and NIFTY 50 spot index resolution."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from nifty_trading.instruments.resolver import InstrumentResolver


def test_resolve_nifty50_index_success(tmp_path):
    """Verify correct extraction of NIFTY 50 spot index from scrip master."""
    mock_master_manager = MagicMock()
    mock_df = pd.DataFrame([
        {
            "Exch": "N",
            "ExchType": "C",
            "ScripCode": 999920000,
            "Name": "NIFTY",
            "FullName": "NIFTY",
            "ScripType": "EQ",
            "Series": "EQ",
            "TickSize": 0.05,
            "LotSize": 1,
        },
        {
            "Exch": "N",
            "ExchType": "C",
            "ScripCode": 10576,
            "Name": "NIFTYBEES",
            "FullName": "NIPPON INDIA ETF NIFTY 50 BEES",
            "ScripType": "XX",
            "Series": "EQ",
            "TickSize": 0.01,
            "LotSize": 1,
        },
    ])
    mock_master_manager.load_master_dataframe.return_value = mock_df

    resolver = InstrumentResolver(master_manager=mock_master_manager)
    resolver.metadata_dir = tmp_path  # never write the real data/metadata/nifty50_instrument.json from a test
    meta = resolver.resolve_nifty50_index(force_refresh=True)

    assert meta.symbol == "NIFTY"
    assert meta.exchange == "N"
    assert meta.exchange_segment == "C"
    assert meta.scrip_code == 999920000
    assert meta.is_index is True
    assert "ETF" not in meta.full_name


def test_resolve_nifty50_index_not_found(tmp_path):
    """Verify that LookupError is raised if NIFTY spot index is missing."""
    mock_master_manager = MagicMock()
    mock_df = pd.DataFrame([
        {"Exch": "B", "ExchType": "C", "ScripCode": 999901, "Name": "SENSEX", "FullName": "SENSEX"}
    ])
    mock_master_manager.load_master_dataframe.return_value = mock_df

    resolver = InstrumentResolver(master_manager=mock_master_manager)
    resolver.metadata_dir = tmp_path  # never write the real data/metadata/nifty50_instrument.json from a test
    with pytest.raises(LookupError, match="NIFTY 50 spot index could not be located"):
        resolver.resolve_nifty50_index(force_refresh=True)
