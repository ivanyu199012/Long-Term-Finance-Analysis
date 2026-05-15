"""Tests for the pykrx fetcher using mocked data."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.fetchers.pykrx import _download_via_naver, download_pykrx, get_live_price_pykrx


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


# ── Naver fallback helpers ──────────────────────────────────────────


def _make_naver_response(n_rows: int = 4) -> list:
    """Create a synthetic Naver chart API response (list-of-lists format).

    Format:
        [
            ["날짜", "시가", "고가", "저가", "종가", "거래량", "외국인소진율"],
            ["20260102", 24535, 24630, 24480, 24620, 9724082, 0.0],
            ...
        ]
    """
    header = ["날짜", "시가", "고가", "저가", "종가", "거래량", "외국인소진율"]
    rows = [header]
    base_date = 20260102
    for i in range(n_rows):
        rows.append([
            str(base_date + i),
            24535 + i * 100,  # open
            24630 + i * 100,  # high
            24480 + i * 100,  # low
            24620 + i * 100,  # close
            9000000 + i * 100000,  # volume
            0.0,  # 외국인소진율
        ])
    return rows


def _make_naver_mock_resp(data) -> MagicMock:
    """Create a mock response object with .text set to JSON-serialized data."""
    import json

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(data, ensure_ascii=False)
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ── _download_via_naver tests ───────────────────────────────────────


class TestDownloadViaNaver:
    """Test the Naver chart API parser directly."""

    @patch("src.fetchers.pykrx.requests.get")
    def test_parses_list_of_lists_format(self, mock_get):
        mock_get.return_value = _make_naver_mock_resp(_make_naver_response(4))

        df = _download_via_naver("360750", period_days=30)

        assert len(df) == 4
        assert "Close" in df.columns
        assert "Open" in df.columns
        assert "High" in df.columns
        assert "Low" in df.columns
        assert "Volume" in df.columns

    @patch("src.fetchers.pykrx.requests.get")
    def test_has_datetime_index(self, mock_get):
        mock_get.return_value = _make_naver_mock_resp(_make_naver_response(3))

        df = _download_via_naver("360750", period_days=30)

        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == "Date"

    @patch("src.fetchers.pykrx.requests.get")
    def test_correct_values_parsed(self, mock_get):
        naver_data = [
            ["날짜", "시가", "고가", "저가", "종가", "거래량", "외국인소진율"],
            ["20260102", 24535, 24630, 24480, 24620, 9724082, 0.0],
        ]
        mock_get.return_value = _make_naver_mock_resp(naver_data)

        df = _download_via_naver("360750", period_days=30)

        assert df.iloc[0]["Open"] == 24535.0
        assert df.iloc[0]["High"] == 24630.0
        assert df.iloc[0]["Low"] == 24480.0
        assert df.iloc[0]["Close"] == 24620.0
        assert df.iloc[0]["Volume"] == 9724082.0

    @patch("src.fetchers.pykrx.requests.get")
    def test_raises_on_empty_response(self, mock_get):
        # Only header, no data rows — len < 2 triggers the check
        mock_get.return_value = _make_naver_mock_resp(
            [["날짜", "시가", "고가", "저가", "종가", "거래량", "외국인소진율"]]
        )

        with pytest.raises(ValueError, match="Unexpected Naver chart API response"):
            _download_via_naver("360750", period_days=30)

    @patch("src.fetchers.pykrx.requests.get")
    def test_raises_on_unexpected_format(self, mock_get):
        mock_get.return_value = _make_naver_mock_resp({"error": "not found"})

        with pytest.raises(ValueError, match="Unexpected Naver chart API response"):
            _download_via_naver("360750", period_days=30)

    @patch("src.fetchers.pykrx.requests.get")
    def test_skips_rows_with_zero_close(self, mock_get):
        naver_data = [
            ["날짜", "시가", "고가", "저가", "종가", "거래량", "외국인소진율"],
            ["20260102", 24535, 24630, 24480, 24620, 9724082, 0.0],
            ["20260103", 0, 0, 0, 0, 0, 0.0],  # zero close — should be skipped
            ["20260105", 24605, 24685, 24595, 24595, 8570935, 0.0],
        ]
        mock_get.return_value = _make_naver_mock_resp(naver_data)

        df = _download_via_naver("360750", period_days=30)
        assert len(df) == 2

    @patch("src.fetchers.pykrx.requests.get")
    def test_parses_single_quoted_js_literal(self, mock_get):
        """Verify ast.literal_eval fallback handles single-quoted responses."""
        # Simulate the actual Naver response format with single quotes
        js_literal = (
            "[['날짜', '시가', '고가', '저가', '종가', '거래량', '외국인소진율'],\n"
            ' ["20260102", 24535, 24630, 24480, 24620, 9724082, 0.0]\n'
            "]"
        )
        mock_resp = MagicMock()
        mock_resp.text = js_literal
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        df = _download_via_naver("360750", period_days=30)

        assert len(df) == 1
        assert df.iloc[0]["Close"] == 24620.0


# ── Fallback integration tests ──────────────────────────────────────


class TestNaverFallback:
    """Test that download_pykrx falls back to Naver when pykrx fails."""

    @patch("src.fetchers.pykrx.requests.get")
    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_falls_back_to_naver_on_pykrx_exception(self, mock_pykrx, mock_requests):
        mock_pykrx.side_effect = Exception("Connection timeout")
        mock_requests.return_value = _make_naver_mock_resp(_make_naver_response(4))

        df = download_pykrx("360750", period_days=30)

        assert len(df) == 4
        assert "Close" in df.columns

    @patch("src.fetchers.pykrx.requests.get")
    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_falls_back_to_naver_on_empty_pykrx(self, mock_pykrx, mock_requests):
        mock_pykrx.return_value = pd.DataFrame()
        mock_requests.return_value = _make_naver_mock_resp(_make_naver_response(3))

        df = download_pykrx("360750", period_days=30)

        assert len(df) == 3

    @patch("src.fetchers.pykrx.requests.get")
    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_raises_when_both_fail(self, mock_pykrx, mock_requests):
        mock_pykrx.side_effect = Exception("pykrx down")
        mock_requests.side_effect = Exception("Naver down")

        with pytest.raises(ValueError, match="No data returned from pykrx or Naver"):
            download_pykrx("360750", period_days=30)

    @patch("src.fetchers.pykrx.requests.get")
    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_prefers_pykrx_when_available(self, mock_pykrx, mock_requests):
        mock_pykrx.return_value = _make_mock_ohlcv(10)

        df = download_pykrx("360750", period_days=30)

        # Naver should not be called
        mock_requests.assert_not_called()
        assert len(df) == 10

    @patch("src.fetchers.pykrx.requests.get")
    @patch("src.fetchers.pykrx.stock.get_market_ohlcv_by_date")
    def test_live_price_falls_back_to_naver(self, mock_pykrx, mock_requests):
        mock_pykrx.side_effect = Exception("pykrx down")

        naver_data = [
            ["날짜", "시가", "고가", "저가", "종가", "거래량", "외국인소진율"],
            ["20260514", 25000, 25100, 24900, 25050, 5000000, 0.0],
        ]
        mock_requests.return_value = _make_naver_mock_resp(naver_data)

        price = get_live_price_pykrx("360750")
        assert price == 25050.0
