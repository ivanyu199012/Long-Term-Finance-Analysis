"""Tests for the Naver Finance real-time price scraper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.fetchers.naver import LivePrice, get_realtime_price_etf, get_realtime_price_gold


# ── Sample data ──────────────────────────────────────────────────────

_ETF_JSON_RESPONSE = {
    "isSuccess": True,
    "result": {
        "datas": [
            {
                "itemCode": "360750",
                "stockName": "TIGER 미국S&P500",
                "closePrice": "26,340",
                "localTradedAt": "2026-05-07T14:36:31.862301+09:00",
            }
        ]
    }
}

_ETF_JSON_EMPTY = {
    "isSuccess": True,
    "result": {"datas": []}
}

_ETF_HTML_NO_PRICE = """
<html><body>
<div class="other_class">
    <em><span class="blind">26,340</span></em>
</div>
</body></html>
"""

_GOLD_JSON_RESPONSE = {
    "isSuccess": True,
    "result": {
        "mainList": [
            {"name": "국제 금", "closePrice": "4,708.90", "localTradedAt": "2026-05-07T00:12:37-05:00"},
            {"name": "국내 금", "closePrice": "219,280", "localTradedAt": "2026-05-07T14:21:56"},
            {"name": "은", "closePrice": "78.40", "localTradedAt": "2026-05-07T00:12:57-05:00"},
        ]
    }
}

_GOLD_JSON_NO_DOMESTIC = {
    "isSuccess": True,
    "result": {
        "mainList": [
            {"name": "국제 금", "closePrice": "4,708.90"},
        ]
    }
}


def _mock_response(html: str = "", status_code: int = 200, json_data: dict | None = None):
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = html
    mock.raise_for_status.return_value = None
    if json_data is not None:
        mock.json.return_value = json_data
    return mock


# ── ETF tests ───────────────────────────────────────────────────────


class TestGetRealtimePriceEtf:
    """Test ETF price from JSON API."""

    @patch("src.fetchers.naver.requests.get")
    def test_returns_price_on_success(self, mock_get):
        mock_get.return_value = _mock_response(json_data=_ETF_JSON_RESPONSE)
        result = get_realtime_price_etf("360750")
        assert result is not None
        assert result.price == 26340.0
        assert result.traded_at == "05/07 14:36"

    @patch("src.fetchers.naver.requests.get")
    def test_returns_none_when_no_data(self, mock_get):
        mock_get.return_value = _mock_response(json_data=_ETF_JSON_EMPTY)
        result = get_realtime_price_etf("360750")
        assert result is None

    @patch("src.fetchers.naver.requests.get")
    def test_returns_none_on_network_error(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        result = get_realtime_price_etf("360750")
        assert result is None

    @patch("src.fetchers.naver.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock = _mock_response(status_code=500)
        mock.raise_for_status.side_effect = Exception("500 Server Error")
        mock_get.return_value = mock
        result = get_realtime_price_etf("360750")
        assert result is None


# ── Gold tests ──────────────────────────────────────────────────────


class TestGetRealtimePriceGold:
    """Test gold price from JSON API."""

    @patch("src.fetchers.naver.requests.get")
    def test_returns_price_on_success(self, mock_get):
        mock_get.return_value = _mock_response(json_data=_GOLD_JSON_RESPONSE)
        result = get_realtime_price_gold()
        assert result is not None
        assert result.price == 219280.0
        assert result.traded_at == "05/07 14:21"

    @patch("src.fetchers.naver.requests.get")
    def test_returns_none_when_no_domestic_gold(self, mock_get):
        mock_get.return_value = _mock_response(json_data=_GOLD_JSON_NO_DOMESTIC)
        result = get_realtime_price_gold()
        assert result is None

    @patch("src.fetchers.naver.requests.get")
    def test_returns_none_on_network_error(self, mock_get):
        mock_get.side_effect = Exception("Timeout")
        result = get_realtime_price_gold()
        assert result is None
