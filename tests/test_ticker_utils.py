"""
Tests for ticker_utils.py — cache management and yfinance integration.

Covers:
- add_missing_ticker_to_cache with existing cache entries
- add_missing_ticker_to_cache with new ticker (mocked yfinance)
- Edge cases: empty cache, None returns, invalid tickers
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ticker_utils import add_missing_ticker_to_cache


class TestAddMissingTickerToCache:
    """Tests for add_missing_ticker_to_cache()."""

    def test_ticker_already_in_cache(self, tmp_path):
        """If ticker is already in cache, return existing data and is_new=False."""
        cache_file = tmp_path / "ticker_cache.json"
        existing_data = {
            "TEST": {
                "type": "stock", "currency": "USD", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": True, "domicile": "US",
                "long_name": "Test Company, Inc."
            }
        }
        with open(cache_file, "w") as f:
            json.dump(existing_data, f)

        result, is_new = add_missing_ticker_to_cache("TEST", cache_file=str(cache_file))

        assert is_new is False
        assert result["type"] == "stock"
        assert result["long_name"] == "Test Company, Inc."
        assert result["domicile"] == "US"

    def test_new_ticker_is_stock(self, tmp_path):
        """New ticker resolved as stock should be cached with stock properties."""
        cache_file = tmp_path / "ticker_cache.json"
        with open(cache_file, "w") as f:
            json.dump({"EXISTING": {"type": "stock"}}, f)

        mock_info = {
            "quoteType": "EQUITY", "currency": "USD",
            "country": "United States", "longName": "New Stock Corp",
            "shortName": "NEWSTOCK",
        }

        with patch("ticker_utils.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            result, is_new = add_missing_ticker_to_cache("NEW", cache_file=str(cache_file))

        assert is_new is True
        assert result["type"] == "stock"
        assert result["currency"] == "USD"
        assert result["domicile"] == "US"
        assert result["withholding_tax_deducted"] is False
        assert result["long_name"] == "New Stock Corp"
        assert result["active"] is True

        with open(cache_file) as f:
            saved = json.load(f)
        assert "EXISTING" in saved
        assert "NEW" in saved
        assert saved["NEW"]["type"] == "stock"

    def test_new_ticker_is_etf(self, tmp_path):
        """New ticker resolved as ETF should be cached with etf properties."""
        cache_file = tmp_path / "ticker_cache.json"
        with open(cache_file, "w") as f:
            json.dump({}, f)

        mock_info = {
            "quoteType": "ETF", "currency": "EUR",
            "country": "Ireland", "longName": "iShares Test UCITS ETF",
        }

        with patch("ticker_utils.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            result, is_new = add_missing_ticker_to_cache("TEST_ETF", cache_file=str(cache_file))

        assert is_new is True
        assert result["type"] == "etf"
        assert result["currency"] == "EUR"
        assert result["domicile"] == "IE"
        assert result["withholding_tax_deducted"] is False

    def test_empty_cache_new_ticker(self, tmp_path):
        """Adding to an empty/non-existent cache should work."""
        cache_file = tmp_path / "fresh_cache.json"
        assert not os.path.exists(cache_file)

        mock_info = {
            "quoteType": "EQUITY", "currency": "USD",
            "country": "United States", "longName": "Brand New Inc",
        }

        with patch("ticker_utils.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            result, is_new = add_missing_ticker_to_cache("BRAND_NEW", cache_file=str(cache_file))

        assert is_new is True
        assert result["type"] == "stock"

        with open(cache_file) as f:
            saved = json.load(f)
        assert "BRAND_NEW" in saved

    def test_yfinance_returns_empty_data(self, tmp_path):
        """If yfinance returns no quoteType, function should return None."""
        cache_file = tmp_path / "ticker_cache.json"
        with open(cache_file, "w") as f:
            json.dump({}, f)

        mock_info = {}

        with patch("ticker_utils.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            result, is_new = add_missing_ticker_to_cache("UNKNOWN", cache_file=str(cache_file))

        assert result is None
        assert is_new is False

    def test_yfinance_raises_exception(self, tmp_path):
        """If yfinance throws, function should return None gracefully."""
        cache_file = tmp_path / "ticker_cache.json"
        with open(cache_file, "w") as f:
            json.dump({}, f)

        with patch("ticker_utils.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            # Use PropertyMock for 'info' attribute with side_effect
            type(mock_instance).info = PropertyMock(side_effect=Exception("API error"))
            mock_ticker.return_value = mock_instance

            result, is_new = add_missing_ticker_to_cache("BROKEN", cache_file=str(cache_file))

        assert result is None
        assert is_new is False

    def test_country_to_domicile_mapping(self, tmp_path):
        """Countries should map to correct domicile codes."""
        cache_file = tmp_path / "ticker_cache.json"
        test_cases = [
            ("Ireland", "IE"), ("United States", "US"),
            ("Germany", "DE"), ("United Kingdom", "GB"),
            ("Netherlands", "NL"), ("France", "FR"),
            ("Switzerland", "CH"), ("Other", "US"),
        ]

        for country, expected_domicile in test_cases:
            with open(cache_file, "w") as f:
                json.dump({}, f)

            mock_info = {
                "quoteType": "EQUITY", "currency": "USD",
                "country": country, "longName": f"Test {country}",
            }

            with patch("ticker_utils.yf.Ticker") as mock_ticker:
                mock_instance = MagicMock()
                mock_instance.info = mock_info
                mock_ticker.return_value = mock_instance

                result, _ = add_missing_ticker_to_cache(
                    f"COUNTRY_{country}", cache_file=str(cache_file)
                )

            assert result["domicile"] == expected_domicile

    def test_uses_short_name_when_long_name_missing(self, tmp_path):
        """If longName is absent, fall back to shortName."""
        cache_file = tmp_path / "ticker_cache.json"
        with open(cache_file, "w") as f:
            json.dump({}, f)

        mock_info = {
            "quoteType": "EQUITY", "currency": "USD",
            "country": "United States", "shortName": "Shorty Inc",
        }

        with patch("ticker_utils.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            result, _ = add_missing_ticker_to_cache("SHORT", cache_file=str(cache_file))

        assert result["long_name"] == "Shorty Inc"

    def test_falls_back_to_ticker(self, tmp_path):
        """If both longName and shortName are absent, use ticker symbol."""
        cache_file = tmp_path / "ticker_cache.json"
        with open(cache_file, "w") as f:
            json.dump({}, f)

        mock_info = {
            "quoteType": "EQUITY", "currency": "USD",
            "country": "United States",
        }

        with patch("ticker_utils.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.info = mock_info
            mock_ticker.return_value = mock_instance

            result, _ = add_missing_ticker_to_cache("TICK", cache_file=str(cache_file))

        assert result["long_name"] == "TICK"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
