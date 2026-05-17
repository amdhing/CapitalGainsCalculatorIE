"""
Tests for ImprovedCapitalGainsCalculator — utility and helper methods.

Covers:
- parse_amount() — currency symbols, negative values, edge cases
- convert_to_eur() — EUR passthrough, USD conversion, error cases
- classify_transaction_type() — buy, sell, dividend, merger, transfer, ignore
- normalize_ticker() — merger resolution, None/NaN handling
- is_etf(), is_active(), has_withholding_tax_deducted(), get_domicile()
- get_conversion_ratio() — merged ticker ratios
- load/save ticker cache
"""

import sys
import os
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from improved_calculator import ImprovedCapitalGainsCalculator


class TestImprovedCapitalGainsCalculatorSetup:
    """Calculator initialization and cache management."""

    def test_initialization(self):
        """Calculator should initialize with default cache path."""
        calc = ImprovedCapitalGainsCalculator()
        assert calc.ticker_cache_file == 'data/ticker_cache.json'
        assert hasattr(calc, 'ticker_cache')

    def test_load_ticker_cache_nonexistent_file(self, tmp_path):
        """If cache file doesn't exist, return empty dict."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache_file = str(tmp_path / "nonexistent.json")
        cache = calc.load_ticker_cache()
        assert cache == {}

    def test_load_ticker_cache_invalid_json(self, tmp_path):
        """If cache file has invalid JSON, return empty dict."""
        cache_file = tmp_path / "invalid.json"
        with open(cache_file, "w") as f:
            f.write("not json")
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache_file = str(cache_file)
        cache = calc.load_ticker_cache()
        assert cache == {}

    def test_save_and_load_ticker_cache(self, tmp_path):
        """Round-trip save/load should preserve data."""
        calc = ImprovedCapitalGainsCalculator()
        cache_file = str(tmp_path / "test_cache.json")
        calc.ticker_cache_file = cache_file
        calc.ticker_cache = {"TEST": {"type": "stock"}}
        calc.save_ticker_cache()

        calc2 = ImprovedCapitalGainsCalculator()
        calc2.ticker_cache_file = cache_file
        loaded = calc2.load_ticker_cache()
        assert loaded["TEST"]["type"] == "stock"


class TestGetTickerInfo:
    """get_ticker_info — cache lookup with auto-add fallback."""

    def test_ticker_in_cache(self):
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {"AAPL": {"type": "stock", "long_name": "Apple Inc."}}
        info = calc.get_ticker_info("AAPL")
        assert info["type"] == "stock"
        assert info["long_name"] == "Apple Inc."

    def test_ticker_not_in_cache_auto_adds(self, tmp_path):
        """Missing ticker should trigger yfinance lookup."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache_file = str(tmp_path / "auto_cache.json")
        calc.ticker_cache = {}

        with patch("improved_calculator.add_missing_ticker_to_cache") as mock_add:
            mock_add.return_value = {
                "type": "stock", "currency": "USD", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "US",
                "long_name": "Auto Added Inc"
            }
            info = calc.get_ticker_info("AUTO")
            assert info["long_name"] == "Auto Added Inc"

    def test_nan_ticker_returns_none(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.get_ticker_info(None) is None
        assert calc.get_ticker_info('') is None

    def test_na_ticker_returns_none(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.get_ticker_info('NAN') is None
        assert calc.get_ticker_info('None') is None

    def test_ticker_uppercased(self):
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {"AAPL": {"type": "stock"}}
        info = calc.get_ticker_info("aapl")
        assert info["type"] == "stock"


class TestParseAmount:
    """parse_amount — extract numbers from string amounts."""

    def test_simple_float(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.parse_amount("1234.56") == 1234.56

    def test_integer(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.parse_amount("1000") == 1000.0

    def test_negative_float(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.parse_amount("-500.25") == -500.25

    def test_with_euro_symbol(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.parse_amount("€1234.56") == 1234.56

    def test_with_dollar_symbol(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.parse_amount("$500.00") == 500.0

    def test_with_pound_symbol(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.parse_amount("£999.99") == 999.99

    def test_na_nan_input(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.parse_amount(None) == 0.0

    def test_non_numeric_string(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.parse_amount("N/A") == 0.0

    def test_encoded_symbols(self):
        """Handle various symbol encodings gracefully."""
        calc = ImprovedCapitalGainsCalculator()
        assert calc.parse_amount("_x001F_123") == 123.0


class TestConvertToEur:
    """convert_to_eur — currency conversion to EUR."""

    def test_eur_passthrough(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.convert_to_eur(100, "EUR", 1.0) == 100

    def test_usd_conversion(self):
        calc = ImprovedCapitalGainsCalculator()
        result = calc.convert_to_eur(100, "USD", 1.08)
        assert round(result, 2) == 92.59

    def test_usd_zero_rate_raises(self):
        calc = ImprovedCapitalGainsCalculator()
        with pytest.raises(ValueError):
            calc.convert_to_eur(100, "USD", 0)

    def test_usd_nan_rate_raises(self):
        calc = ImprovedCapitalGainsCalculator()
        with pytest.raises(ValueError):
            calc.convert_to_eur(100, "USD", float('nan'))

    def test_unknown_currency_raises(self):
        calc = ImprovedCapitalGainsCalculator()
        with pytest.raises(ValueError):
            calc.convert_to_eur(100, "GBP", 1.0)


class TestClassifyTransactionType:
    """classify_transaction_type — map string types to internal categories."""

    def test_buy(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.classify_transaction_type("BUY") == "buy"
        assert calc.classify_transaction_type("buy") == "buy"

    def test_sell(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.classify_transaction_type("SELL") == "sell"

    def test_dividend(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.classify_transaction_type("DIVIDEND") == "dividend"

    def test_merger(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.classify_transaction_type("MERGER") == "merger"
        assert calc.classify_transaction_type("MERGER_STOCK") == "merger_stock"
        assert calc.classify_transaction_type("MERGER_CASH") == "merger_cash"

    def test_broker_transfer(self):
        calc = ImprovedCapitalGainsCalculator()
        result = calc.classify_transaction_type(
            "TRANSFER - REVOLUT TRADING LTD TO REVOLUT SECURITIES EUROPE UAB"
        )
        assert result == "transfer_broker"

    def test_ignore_types(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.classify_transaction_type("CASH TOP-UP") == "ignore"
        assert calc.classify_transaction_type("CASH WITHDRAWAL") == "ignore"
        assert calc.classify_transaction_type("CUSTODY FEE") == "ignore"

    def test_nan_type(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.classify_transaction_type(None) == "ignore"

    def test_unknown_type(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.classify_transaction_type("BONUS SHARES") == "ignore"


class TestNormalizeTicker:
    """normalize_ticker — resolve mergers to target ticker."""

    def test_no_merge(self):
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {"AAPL": {"type": "stock", "merged_into": None}}
        assert calc.normalize_ticker("AAPL") == "AAPL"

    def test_merged_ticker_resolves(self):
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {
            "OLD": {"type": "stock", "merged_into": "NEW"},
            "NEW": {"type": "stock", "merged_into": None}
        }
        assert calc.normalize_ticker("OLD") == "NEW"
        assert calc.normalize_ticker("NEW") == "NEW"

    def test_none_ticker(self):
        calc = ImprovedCapitalGainsCalculator()
        assert calc.normalize_ticker(None) is None
        assert calc.normalize_ticker("") is None
        assert calc.normalize_ticker("NAN") is None

    def test_ticker_uppercased(self):
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {"TEST": {"type": "stock", "merged_into": None}}
        assert calc.normalize_ticker("test") == "TEST"

    def test_ticker_not_in_cache_returns_none(self):
        """If ticker can't be added, normalize returns None."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {}
        with patch("improved_calculator.add_missing_ticker_to_cache", return_value=None):
            assert calc.normalize_ticker("UNKNOWN") is None


class TestTickerClassificationHelpers:
    """is_etf, is_active, has_withholding_tax_deducted, get_domicile, get_conversion_ratio."""

    def setup_calc(self):
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {
            "STOCK_A": {
                "type": "stock", "active": True, "currency": "USD",
                "withholding_tax_deducted": True, "domicile": "US",
                "merged_into": None, "conversion_ratio": 1.0
            },
            "ETF_A": {
                "type": "etf", "active": True, "currency": "EUR",
                "withholding_tax_deducted": False, "domicile": "IE",
                "merged_into": None, "conversion_ratio": 1.0
            },
            "INACTIVE": {
                "type": "stock", "active": False, "currency": "USD",
                "withholding_tax_deducted": True, "domicile": "US",
                "merged_into": None, "conversion_ratio": 1.0
            },
            "MERGED": {
                "type": "stock", "active": False, "currency": "USD",
                "withholding_tax_deducted": True, "domicile": "US",
                "merged_into": "NEW", "conversion_ratio": 0.5
            },
        }
        return calc

    def test_is_etf(self):
        calc = self.setup_calc()
        assert calc.is_etf("STOCK_A") is False
        assert calc.is_etf("ETF_A") is True

    def test_is_etf_unknown_ticker_raises(self):
        calc = self.setup_calc()
        # Mock add_missing_ticker_to_cache to return None so ValueError is raised
        with patch("improved_calculator.add_missing_ticker_to_cache", return_value=None):
            with pytest.raises(ValueError, match="Ticker 'UNKNOWN' not found in cache"):
                calc.is_etf("UNKNOWN")

    def test_is_active(self):
        calc = self.setup_calc()
        assert calc.is_active("STOCK_A") is True
        assert calc.is_active("INACTIVE") is False

    def test_has_withholding_tax_deducted(self):
        calc = self.setup_calc()
        assert calc.has_withholding_tax_deducted("STOCK_A") is True
        assert calc.has_withholding_tax_deducted("ETF_A") is False

    def test_get_domicile(self):
        calc = self.setup_calc()
        assert calc.get_domicile("STOCK_A") == "US"
        assert calc.get_domicile("ETF_A") == "IE"

    def test_get_conversion_ratio(self):
        calc = self.setup_calc()
        assert calc.get_conversion_ratio("MERGED") == 0.5

    def test_get_conversion_ratio_default(self):
        calc = self.setup_calc()
        assert calc.get_conversion_ratio("STOCK_A") == 1.0


class TestDeemedDisposalLiability:
    """calculate_deemed_disposal_liability — 8-year rule."""

    def test_no_deemed_disposal_for_stock(self):
        """Stocks should not have deemed disposal liability."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {"STOCK_A": {"type": "stock"}}
        gain, liability, details = calc.calculate_deemed_disposal_liability(
            "STOCK_A", pd.DataFrame()
        )
        assert gain == 0
        assert liability == 0
        assert details == []

    def test_deemed_disposal_triggers_for_old_holdings(self):
        """ETF held 10+ years should trigger deemed disposal."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {"ETF_A": {"type": "etf"}}
        buy_df = pd.DataFrame({
            "Date": pd.to_datetime(["2014-01-01"]),
            "PricePerShareEUR": [100.0],
            "Quantity": [100.0],
        })
        gain, liability, details = calc.calculate_deemed_disposal_liability(
            "ETF_A", buy_df
        )

        assert len(details) == 1
        assert details[0]["years_held"] >= 8
        assert gain > 0
        assert liability > 0

    def test_no_deemed_disposal_for_recent_buy(self):
        """ETF held only 1 year should not trigger deemed disposal."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {"ETF_A": {"type": "etf"}}
        buy_df = pd.DataFrame({
            "Date": pd.to_datetime(["2025-01-01"]),
            "PricePerShareEUR": [100.0],
            "Quantity": [100.0],
        })
        gain, liability, details = calc.calculate_deemed_disposal_liability(
            "ETF_A", buy_df
        )

        assert len(details) == 0
        assert gain == 0
        assert liability == 0


class TestWeightedFxRate:
    """get_weighted_fx_rate — average FX rate from transactions."""

    def test_simple_weighted_average(self):
        calc = ImprovedCapitalGainsCalculator()
        tx_data = {
            "TransactionType": ["buy", "buy"],
            "Currency": ["USD", "USD"],
            "FX Rate": [1.08, 1.12],
            "TotalAmountEUR": [100.0, 200.0],
        }
        df = pd.DataFrame(tx_data)
        rate = calc.get_weighted_fx_rate(df)
        # weighted: (100*1.08 + 200*1.12) / (100 + 200) = 332/300 = 1.1067
        assert round(rate, 4) == 1.1067

    def test_eur_only_transactions_raises(self):
        """When all transactions are in EUR, function should raise."""
        calc = ImprovedCapitalGainsCalculator()
        tx_data = {
            "TransactionType": ["buy", "sell"],
            "Currency": ["EUR", "EUR"],
            "FX Rate": [1.0, 1.0],
            "TotalAmountEUR": [100.0, 50.0],
        }
        df = pd.DataFrame(tx_data)
        with pytest.raises(ValueError, match="No valid FX rates found"):
            calc.get_weighted_fx_rate(df)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
