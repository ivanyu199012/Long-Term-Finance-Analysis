"""Tests for the KRX Gold fetcher using mocked HTTP requests."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.fetchers.krx_gold import (
    _fetch_single_day,
    _load_cache,
    _save_cache,
    download_krx_gold,
    get_live_price_krx_gold,
)


# ── Helpers ─────────────────────────────────────────────────────────

_SAMPLE_RESPONSE = {
    "OutBlock_1": [
        {
            "BAS_DD": "20250428",
            "ISU_CD": "04020000",
            "ISU_NM": "금 99.99_1Kg",
            "TDD_CLSPRC": "152790",
            "CMPPREVDD_PRC": "-150",
            "FLUC_RT": "-0.10",
            "TDD_OPNPRC": "153030",
            "TDD_HGPRC": "153700",
            "TDD_LWPRC": "151480",
            "ACC_TRDVOL": "218974",
            "ACC_TRDVAL": "33437023870",
        },
        {
            "BAS_DD": "20250428",
            "ISU_CD": "04020100",
            "ISU_NM": "미니금 99.99_100g",
            "TDD_CLSPRC": "153210",
            "CMPPREVDD_PRC": "20",
            "FLUC_RT": "0.01",
            "TDD_OPNPRC": "154900",
            "TDD_HGPRC": "154900",
            "TDD_LWPRC": "152290",
            "ACC_TRDVOL": "10433",
            "ACC_TRDVAL": "1599909740",
        },
    ]
}

_SAMPLE_RESPONSE_LOWERCASE = {
    "OutBlock_1": [
        {
            "BAS_DD": "20251229",
            "ISU_CD": "04020000",
            "ISU_NM": "금 99.99_1kg",  # lowercase 'k'
            "TDD_CLSPRC": "208910",
            "CMPPREVDD_PRC": "-4630",
            "FLUC_RT": "-2.17",
            "TDD_OPNPRC": "214510",
            "TDD_HGPRC": "214580",
            "TDD_LWPRC": "208910",
            "ACC_TRDVOL": "941553",
            "ACC_TRDVAL": "197953354470",
        },
    ]
}

_EMPTY_RESPONSE = {"OutBlock_1": []}


def _mock_response(json_data, status_code=200):
    """Create a mock requests.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


# ── _fetch_single_day tests ─────────────────────────────────────────


class TestFetchSingleDay:
    """Test single-day API fetch with mocked HTTP."""

    @patch("src.fetchers.krx_gold.requests.get")
    def test_returns_price_for_valid_date(self, mock_get):
        mock_get.return_value = _mock_response(_SAMPLE_RESPONSE)
        price = _fetch_single_day("fake_key", "20250428")
        assert price == 152790.0

    @patch("src.fetchers.krx_gold.requests.get")
    def test_returns_none_for_empty_response(self, mock_get):
        mock_get.return_value = _mock_response(_EMPTY_RESPONSE)
        price = _fetch_single_day("fake_key", "20250101")
        assert price is None

    @patch("src.fetchers.krx_gold.requests.get")
    def test_case_insensitive_product_filter(self, mock_get):
        """Should match both '1Kg' and '1kg' variants."""
        mock_get.return_value = _mock_response(_SAMPLE_RESPONSE_LOWERCASE)
        price = _fetch_single_day("fake_key", "20251229")
        assert price == 208910.0

    @patch("src.fetchers.krx_gold.requests.get")
    def test_filters_mini_gold(self, mock_get):
        """Should NOT return 미니금 price."""
        # Response with only mini gold
        mini_only = {
            "OutBlock_1": [
                {
                    "ISU_NM": "미니금 99.99_100g",
                    "TDD_CLSPRC": "153210",
                },
            ]
        }
        mock_get.return_value = _mock_response(mini_only)
        price = _fetch_single_day("fake_key", "20250428")
        assert price is None

    @patch("src.fetchers.krx_gold.requests.get")
    def test_handles_request_exception(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        price = _fetch_single_day("fake_key", "20250428")
        assert price is None


# ── download_krx_gold tests ─────────────────────────────────────────


class TestDownloadKrxGold:
    """Test the full download function with mocked API and cache."""

    def test_raises_on_empty_auth_key(self):
        with pytest.raises(ValueError, match="KRX_AUTH_KEY is not set"):
            download_krx_gold("")

    @patch("src.fetchers.krx_gold._fetch_date_range")
    @patch("src.fetchers.krx_gold._load_cache")
    @patch("src.fetchers.krx_gold._save_cache")
    def test_uses_cache_when_available(self, mock_save, mock_load, mock_fetch):
        """Should only fetch dates after the last cached date."""
        cached = pd.DataFrame(
            {"Close": [150000.0, 151000.0]},
            index=pd.to_datetime(["2025-04-25", "2025-04-28"]),
        )
        cached.index.name = "Date"
        mock_load.return_value = cached
        mock_fetch.return_value = [{"Date": "20250429", "Close": 152000.0}]

        # Use large period_days so the trim doesn't remove test data
        df = download_krx_gold("fake_key", period_days=500)

        # Should have called fetch starting after 2025-04-28
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert call_args[1].date().isoformat() == "2025-04-29"

        # Result should include both cached and new data
        assert len(df) == 3
        assert mock_save.called


# ── get_live_price_krx_gold tests ───────────────────────────────────


class TestGetLivePriceKrxGold:
    """Test live price retrieval."""

    def test_raises_on_empty_auth_key(self):
        with pytest.raises(ValueError, match="KRX_AUTH_KEY is not set"):
            get_live_price_krx_gold("")

    @patch("src.fetchers.krx_gold._fetch_single_day")
    @patch("src.fetchers.krx_gold._load_cache")
    def test_falls_back_to_cache(self, mock_load, mock_fetch):
        """If API returns nothing, should fall back to cache."""
        mock_fetch.return_value = None  # All API calls return None
        cached = pd.DataFrame(
            {"Close": [150000.0, 151000.0]},
            index=pd.to_datetime(["2025-04-25", "2025-04-28"]),
        )
        cached.index.name = "Date"
        mock_load.return_value = cached

        price = get_live_price_krx_gold("fake_key")
        assert price == 151000.0

    @patch("src.fetchers.krx_gold._fetch_single_day")
    def test_returns_first_available_price(self, mock_fetch):
        """Should walk back and return the first non-None price."""
        # Return None for first 3 calls, then a price
        mock_fetch.side_effect = [None, None, None, 155000.0]
        price = get_live_price_krx_gold("fake_key")
        assert price == 155000.0


# ── Cache tests ─────────────────────────────────────────────────────


class TestCache:
    """Test CSV caching logic."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Save then load should return identical data."""
        cache_path = str(tmp_path / "test_gold.csv")
        df = pd.DataFrame(
            {"Close": [100.0, 200.0, 300.0]},
            index=pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        )
        df.index.name = "Date"

        with patch("src.fetchers.krx_gold._CACHE_PATH", cache_path):
            _save_cache(df)
            loaded = _load_cache()

        assert loaded is not None
        assert len(loaded) == 3
        assert loaded["Close"].iloc[-1] == 300.0

    def test_load_returns_none_when_no_file(self):
        with patch("src.fetchers.krx_gold._CACHE_PATH", "/nonexistent/path.csv"):
            result = _load_cache()
        assert result is None
