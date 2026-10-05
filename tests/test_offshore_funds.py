"""Tests for the offshore-fund (Case IV) tax regime.

Covers the pure functions in ``src.tax.offshore_funds`` plus the marginal-rate
income tax helper in ``src.tax.tax_calculations``:

- Case IV income tax (no €1,270 exemption, no loss relief).
- Domicile-driven remittance split (s.745(4)).
- No 8-year deemed disposal for offshore funds.
- Input validation.
"""

import os
import sys

import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.tax import offshore_funds
from src.tax.offshore_funds import (
    OffshoreFundsValidationError,
    compute_offshore_taxable_income,
    split_offshore_fund_gains,
    validate_offshore_funds_request,
)
from src.tax.tax_calculations import calculate_marginal_income_tax
from src.improved_calculator import ImprovedCapitalGainsCalculator


# ---------------------------------------------------------------------------
# Marginal-rate income tax helper
# ---------------------------------------------------------------------------

class TestMarginalIncomeTax:
    def test_positive_amount_at_40(self):
        assert calculate_marginal_income_tax(1000.0, 40) == 400.0

    def test_positive_amount_at_20(self):
        assert calculate_marginal_income_tax(1000.0, 20) == 200.0

    def test_positive_amount_at_45(self):
        assert calculate_marginal_income_tax(1000.0, 45) == 450.0

    def test_zero_amount(self):
        assert calculate_marginal_income_tax(0.0, 40) == 0.0

    def test_negative_amount_is_zero(self):
        # Losses are ignored; there is no loss relief or negative tax.
        assert calculate_marginal_income_tax(-500.0, 40) == 0.0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidateOffshoreFundsRequest:
    def test_no_offshore_funds_skips_checks(self):
        # Should not raise.
        validate_offshore_funds_request(False, True, None, None)

    def test_gains_only_skips_checks(self):
        validate_offshore_funds_request(True, False, None, None)

    def test_offshore_funds_require_domicile(self):
        with pytest.raises(OffshoreFundsValidationError):
            validate_offshore_funds_request(True, True, None, None)

    def test_non_domiciled_requires_remittance(self):
        with pytest.raises(OffshoreFundsValidationError):
            validate_offshore_funds_request(True, True, "non_domiciled", None)

    def test_non_domiciled_with_remittance_ok(self):
        validate_offshore_funds_request(True, True, "non_domiciled", 100.0)

    def test_domiciled_does_not_require_remittance(self):
        validate_offshore_funds_request(True, True, "domiciled", None)


# ---------------------------------------------------------------------------
# Split offshore fund gains
# ---------------------------------------------------------------------------

class TestSplitOffshoreFundGains:
    def test_collects_offshore_fund_gains_only(self):
        results = {
            "ticker_detail": {
                "NIFTYBEES": {
                    "asset_type": "offshore_funds",
                    "realized_gains": {2024: 1000.0, 2025: 500.0},
                },
                "AAPL": {
                    "asset_type": "stocks",
                    "realized_gains": {2024: 9999.0},
                },
                "VWCE": {
                    "asset_type": "etfs",
                    "realized_gains": {2024: 8888.0},
                },
            }
        }
        assert split_offshore_fund_gains(results) == {2024: 1000.0, 2025: 500.0}

    def test_sums_across_tickers(self):
        results = {
            "ticker_detail": {
                "NIFTYBEES": {
                    "asset_type": "offshore_funds",
                    "realized_gains": {2024: 1000.0},
                },
                "GOLDETF": {
                    "asset_type": "offshore_funds",
                    "realized_gains": {2024: 2000.0},
                },
            }
        }
        assert split_offshore_fund_gains(results) == {2024: 3000.0}

    def test_empty_results(self):
        assert split_offshore_fund_gains({}) == {}


# ---------------------------------------------------------------------------
# Case IV taxable income (domicile split)
# ---------------------------------------------------------------------------

class TestComputeOffshoreTaxableIncome:
    def test_domiciled_full_gain_ignores_loss(self):
        taxable, unremitted = compute_offshore_taxable_income(
            {2024: 5000.0, 2025: -1000.0}, True, "domiciled", None
        )
        # Arising basis: full positive gain; losses ignored (no relief).
        assert taxable == {2024: 5000.0, 2025: 0.0}
        assert unremitted == 0.0

    def test_non_domiciled_remittance_fifo(self):
        taxable, unremitted = compute_offshore_taxable_income(
            {2023: 1000.0, 2024: 3000.0}, True, "non_domiciled", 2500.0
        )
        assert taxable == {2023: 1000.0, 2024: 1500.0}
        assert unremitted == 1500.0

    def test_non_domiciled_loss_ignored(self):
        gains = {2023: 1000.0, 2024: -500.0, 2025: 2000.0}
        taxable, unremitted = compute_offshore_taxable_income(
            gains, True, "non_domiciled", 2500.0
        )
        # 1000 + 0 (loss skipped) + 1500 = 2500 remitted
        assert taxable == {2023: 1000.0, 2024: 0.0, 2025: 1500.0}
        assert unremitted == 500.0

    def test_gains_only_mode(self):
        taxable, unremitted = compute_offshore_taxable_income(
            {2024: 5000.0}, False, None, None
        )
        assert taxable == {2024: 0.0}
        assert unremitted == 5000.0


# ---------------------------------------------------------------------------
# Engine integration: offshore_fund -> three-way bucket, no deemed disposal
# ---------------------------------------------------------------------------

class TestOffshoreFundClassification:
    def _calc(self):
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache = {
            "NIFTYBEES": {
                "type": "offshore_fund", "currency": "INR",
                "domicile": "IN", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False,
                "long_name": "Nippon India ETF Nifty 50 BeES",
            },
        }
        return calc

    def test_asset_kind_is_offshore_fund(self):
        calc = self._calc()
        assert calc.asset_kind("NIFTYBEES") == "offshore_fund"

    def test_is_etf_false_for_offshore_fund(self):
        calc = self._calc()
        assert calc.is_etf("NIFTYBEES") is False

    def test_offshore_gains_routed_to_offshore_bucket(self):
        calc = self._calc()
        data = {
            "Date": pd_to_datetime(["2024-01-10", "2024-06-10"]),
            "Ticker": ["NIFTYBEES", "NIFTYBEES"],
            "Type": ["BUY", "SELL"],
            "Quantity": [100.0, 100.0],
            "Price per share": [200.0, 250.0],
            "Total Amount": [20000.0, 25000.0],
            "Currency": ["INR", "INR"],
            "FX Rate": [90.0, 90.0],
            "Source": ["zerodha", "zerodha"],
            "ISIN": [None, None],
        }
        results = calc.process_transactions(pd_to_frame(data), source="zerodha")

        # cost 200*100/90 = 222.22; proceeds 250*100/90 = 277.78; gain ~55.56
        gain = results["summary"]["offshore_funds"]["realized_gains"][2024]
        assert round(gain, 2) == round(25000.0 / 90.0 - 20000.0 / 90.0, 2)
        assert gain > 0

        # Not in stocks or etfs buckets
        assert results["summary"]["stocks"]["realized_gains"].get(2024, 0) == 0
        assert results["summary"]["etfs"]["realized_gains"].get(2024, 0) == 0

        # asset_type marker
        assert results["ticker_detail"]["NIFTYBEES"]["asset_type"] == "offshore_funds"

    def test_no_deemed_disposal_for_offshore_fund(self):
        calc = self._calc()
        assert calc.calculate_deemed_disposal_liability("NIFTYBEES", None)[0] == 0


def pd_to_datetime(values):
    import pandas as pd
    return pd.to_datetime(values)


def pd_to_frame(data):
    import pandas as pd
    return pd.DataFrame(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])