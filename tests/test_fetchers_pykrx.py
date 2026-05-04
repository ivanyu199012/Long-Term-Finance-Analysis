"""Tests for the pykrx fetcher using mocked data."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.fetchers.pykrx import download_pykrx, get_live_price_pykrx


# ── Helpers ─────────────────────────────────────────────────────────


def _make_mock_ohlcv(n_rows: int = 20) -> pd.DataFrame:
    """Create a synthetic pykrx-style DataFrame with Korean column names."""
    dates = pd.date_range("2024-01-02", periods=n_rows, freq="B")
    return pd.DataFrame(
        {
            "시가": [100 + i for i in range(n_rows)],
            "고가": [105 + i for i in range(n_rows)],
            "저가": [95 + i for i in range(n_rows)],
            "종가": [102 + i for i in range(n_rows)],
            "거래량": [1000 * (i + 1) for i in range(n_rows)],
        },
        index=dates,
    )


# ── download_pykrx tests ───────────────────────────────────────────


class TestDownloadPykrx:
    """Test download_pykrx with mocked pykrx.stock calls."""

    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_returns_dataframe_with_correct_columns(self, mock_get):
        mock_get.return_value = _make_mock_ohlcv()
        df = download_pykrx("133690", period_days=30)

        assert "Close" in df.columns
        assert "Open" in df.columns
        assert "High" in df.columns
        assert "Low" in df.columns
        assert "Volume" in df.columns

    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_has_datetime_index(self, mock_get):
        mock_get.return_value = _make_mock_ohlcv()
        df = download_pykrx("133690", period_days=30)

        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == "Date"

    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_filters_zero_close_rows(self, mock_get):
        raw = _make_mock_ohlcv(10)
        # Set one row's close to 0 (non-trading day)
        raw.iloc[3, raw.columns.get_loc("종가")] = 0
        mock_get.return_value = raw

        df = download_pykrx("133690", period_days=30)
        assert len(df) == 9  # one row filtered out

    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_raises_on_empty_response(self, mock_get):
        mock_get.return_value = pd.DataFrame()

        with pytest.raises(ValueError, match="No data returned"):
            download_pykrx("999999", period_days=30)

    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_column_rename_mapping(self, mock_get):
        mock_get.return_value = _make_mock_ohlcv(5)
        df = download_pykrx("360750", period_days=30)

        # Verify Korean columns are gone
        assert "종가" not in df.columns
        assert "시가" not in df.columns
        assert "고가" not in df.columns
        assert "저가" not in df.columns


# ── get_live_price_pykrx tests ──────────────────────────────────────


class TestGetLivePricePykrx:
    """Test get_live_price_pykrx with mocked data."""

    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_returns_latest_close(self, mock_get):
        raw = _make_mock_ohlcv(5)
        mock_get.return_value = raw
        price = get_live_price_pykrx("133690")

        # Last row's 종가 = 102 + 4 = 106
        assert price == 106.0

    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_raises_on_empty_response(self, mock_get):
        mock_get.return_value = pd.DataFrame()

        with pytest.raises(ValueError, match="No recent data"):
            get_live_price_pykrx("999999")
