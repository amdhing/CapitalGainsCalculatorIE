"""
Tests for tax_calculations.py — core Irish tax calculation functions.

Covers:
- get_etf_exit_tax_rate() — rate boundaries (2025 → 41%, 2026+ → 38%)
- apply_cgt_with_loss_carry_forward() — exemption, loss offset, carry forward
- calculate_etf_exit_tax() — aggregated ETF tax (basic)
- calculate_etf_exit_tax_per_ticker() — per-ticker with loss forfeiture
- calculate_dividend_income_tax() — marginal rate, withholding credits
- format_currency_display() — € / $ / other
- get_exemption_applied() — helper
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tax_calculations import (
    get_etf_exit_tax_rate,
    apply_cgt_with_loss_carry_forward,
    calculate_etf_exit_tax,
    calculate_etf_exit_tax_per_ticker,
    calculate_dividend_income_tax,
    format_currency_display,
    get_exemption_applied,
)


# ==============================================================================
# ETF Exit Tax Rate
# ==============================================================================

class TestGetEtfExitTaxRate:
    """Rate changes at year boundaries: 41% up to 2025, 38% from 2026."""

    def test_rate_2024(self):
        assert get_etf_exit_tax_rate(2024) == 0.41

    def test_rate_2025(self):
        """2025 is the last year at 41%."""
        assert get_etf_exit_tax_rate(2025) == 0.41

    def test_rate_2026(self):
        """2026 is the first year at 38%."""
        assert get_etf_exit_tax_rate(2026) == 0.38

    def test_rate_2027_and_beyond(self):
        assert get_etf_exit_tax_rate(2027) == 0.38
        assert get_etf_exit_tax_rate(2030) == 0.38
        assert get_etf_exit_tax_rate(2050) == 0.38

    def test_rate_historical(self):
        assert get_etf_exit_tax_rate(2020) == 0.41
        assert get_etf_exit_tax_rate(2018) == 0.41


# ==============================================================================
# CGT Loss Carry Forward
# ==============================================================================

class TestApplyCgtWithLossCarryForward:
    """Irish CGT: 33% rate, €1,270 exemption, indefinite loss carry forward."""

    def test_basic_gain_no_losses(self):
        """Straightforward gain with no losses to carry forward."""
        taxable, cgt, used, remaining = apply_cgt_with_loss_carry_forward(5000, 0)
        expected_taxable = 5000 - 1270  # €3,730
        assert taxable == expected_taxable
        assert cgt == expected_taxable * 0.33
        assert used == 0
        assert remaining == 0

    def test_gain_below_exemption(self):
        """If gain is <= €1,270, no tax due."""
        taxable, cgt, used, remaining = apply_cgt_with_loss_carry_forward(1000, 0)
        assert taxable == 0
        assert cgt == 0
        assert used == 0
        assert remaining == 0

    def test_exemption_not_applied_to_losses(self):
        """If no realized gain, exemption does not apply."""
        taxable, cgt, used, remaining = apply_cgt_with_loss_carry_forward(0, 500)
        assert taxable == 0
        assert cgt == 0
        assert used == 0
        assert remaining == 500  # existing losses remain

    def test_loss_carried_forward_used(self):
        """Gain of €5,000 with €2,000 loss carry forward. Exemption + loss applied."""
        taxable, cgt, used, remaining = apply_cgt_with_loss_carry_forward(5000, 2000)
        # Step 1: 5000 - 1270 = 3730
        # Step 2: 3730 - 2000 = 1730
        assert taxable == 1730
        assert cgt == 1730 * 0.33
        assert used == 2000
        assert remaining == 0

    def test_loss_larger_than_gain(self):
        """Loss carry forward exceeds gain after exemption. Remaining loss persists."""
        taxable, cgt, used, remaining = apply_cgt_with_loss_carry_forward(3000, 5000)
        # Step 1: 3000 - 1270 = 1730
        # Step 2: 1730 - 1730 = 0 (can only use up to the gain amount)
        assert taxable == 0
        assert cgt == 0
        # 5000 - 1730 = 3270 losses remaining
        assert remaining == 5000 - 1730

    def test_net_loss_increases_accumulated_losses(self):
        """If stock_realized is negative, add to accumulated losses."""
        taxable, cgt, used, remaining = apply_cgt_with_loss_carry_forward(-2000, 1000)
        # after_exemption = -2000 (exemption doesn't apply to losses)
        # losses accumulated: 1000 + 2000 = 3000
        assert taxable == 0
        assert cgt == 0
        assert used == 0
        assert remaining == 3000

    def test_zero_everything(self):
        """Zero gain, zero losses — nothing happens."""
        taxable, cgt, used, remaining = apply_cgt_with_loss_carry_forward(0, 0)
        assert taxable == 0
        assert cgt == 0
        assert used == 0
        assert remaining == 0

    def test_partial_loss_used(self):
        """Only enough loss to bring gain to zero."""
        taxable, cgt, used, remaining = apply_cgt_with_loss_carry_forward(5000, 3000)
        # Step 1: 5000 - 1270 = 3730
        # Step 2: 3730 - 3000 = 730
        assert taxable == 730
        assert cgt == 730 * 0.33
        assert used == 3000
        assert remaining == 0


# ==============================================================================
# ETF Exit Tax (Aggregated — basic, pre-per-ticker)
# ==============================================================================

class TestCalculateEtfExitTax:
    """Basic aggregate ETF exit tax calculation."""

    def test_gains_only(self):
        taxable, tax = calculate_etf_exit_tax(10000, 0, 0, 2026)
        assert taxable == 10000
        assert tax == 10000 * 0.38  # €3,800

    def test_gains_and_dividends(self):
        taxable, tax = calculate_etf_exit_tax(5000, 2000, 0, 2026)
        assert taxable == 7000
        assert tax == 7000 * 0.38

    def test_all_three_components(self):
        taxable, tax = calculate_etf_exit_tax(5000, 1000, 3000, 2026)
        assert taxable == 9000
        assert tax == 9000 * 0.38

    def test_2025_rate(self):
        taxable, tax = calculate_etf_exit_tax(5000, 0, 0, 2025)
        assert tax == 5000 * 0.41

    def test_zero(self):
        taxable, tax = calculate_etf_exit_tax(0, 0, 0, 2026)
        assert taxable == 0
        assert tax == 0


# ==============================================================================
# ETF Exit Tax Per-Ticker (No Cross-Ticker Loss Offsetting)
# ==============================================================================

class TestCalculateEtfExitTaxPerTicker:
    """Each ETF taxed independently. Losses on one cannot offset gains on another."""

    def test_single_ticker_gain(self):
        per_ticker = {
            "ETF_A": {"realized_gains": 5000, "dividends": 0, "deemed_gains": 0},
        }
        result = calculate_etf_exit_tax_per_ticker(per_ticker, 2026)

        assert result["per_ticker"]["ETF_A"]["exit_tax"] == 5000 * 0.38
        assert result["total_taxable"] == 5000
        assert result["total_exit_tax"] == 5000 * 0.38
        assert result["per_ticker"]["ETF_A"]["forfeited_loss"] == 0

    def test_single_ticker_loss_forfeited(self):
        per_ticker = {
            "ETF_A": {"realized_gains": -3000, "dividends": 0, "deemed_gains": 0},
        }
        result = calculate_etf_exit_tax_per_ticker(per_ticker, 2026)

        assert result["per_ticker"]["ETF_A"]["exit_tax"] == 0
        assert result["per_ticker"]["ETF_A"]["forfeited_loss"] == -3000
        assert result["total_taxable"] == 0
        assert result["total_exit_tax"] == 0

    def test_two_tickers_one_gain_one_loss(self):
        """
        CRITICAL: Loss on ETF_B must NOT offset gain on ETF_A.
        Each ticker is taxed independently. Loss is forfeited.
        """
        per_ticker = {
            "ETF_A": {"realized_gains": 5000, "dividends": 0, "deemed_gains": 0},
            "ETF_B": {"realized_gains": -2000, "dividends": 0, "deemed_gains": 0},
        }
        result = calculate_etf_exit_tax_per_ticker(per_ticker, 2026)

        # Correct: ETF_A pays on full €5,000, ETF_B loss forfeited
        assert result["per_ticker"]["ETF_A"]["exit_tax"] == 1900.0
        assert result["per_ticker"]["ETF_B"]["exit_tax"] == 0.0
        assert result["per_ticker"]["ETF_B"]["forfeited_loss"] == -2000.0
        assert result["total_taxable"] == 5000.0
        assert result["total_exit_tax"] == 1900.0

        # Wrong (old behavior): aggregate first
        assert max(0, 5000 - 2000) * 0.38 == 1140.0  # Understates tax by €760

    def test_two_tickers_both_gains(self):
        """Both tickers have gains — both taxed independently."""
        per_ticker = {
            "ETF_A": {"realized_gains": 3000, "dividends": 0, "deemed_gains": 0},
            "ETF_B": {"realized_gains": 4000, "dividends": 0, "deemed_gains": 0},
        }
        result = calculate_etf_exit_tax_per_ticker(per_ticker, 2026)

        assert result["per_ticker"]["ETF_A"]["exit_tax"] == 3000 * 0.38
        assert result["per_ticker"]["ETF_B"]["exit_tax"] == 4000 * 0.38
        assert result["total_taxable"] == 7000
        assert result["total_exit_tax"] == 7000 * 0.38

    def test_two_tickers_both_losses(self):
        """Both tickers have losses — both forfeited."""
        per_ticker = {
            "ETF_A": {"realized_gains": -1000, "dividends": 0, "deemed_gains": 0},
            "ETF_B": {"realized_gains": -500, "dividends": 0, "deemed_gains": 0},
        }
        result = calculate_etf_exit_tax_per_ticker(per_ticker, 2026)

        assert result["per_ticker"]["ETF_A"]["exit_tax"] == 0
        assert result["per_ticker"]["ETF_B"]["exit_tax"] == 0
        assert result["total_taxable"] == 0
        assert result["total_exit_tax"] == 0

    def test_ticker_with_dividends(self):
        """ETF dividends are included in per-ticker taxable amount."""
        per_ticker = {
            "ETF_A": {"realized_gains": 3000, "dividends": 500, "deemed_gains": 0},
        }
        result = calculate_etf_exit_tax_per_ticker(per_ticker, 2026)

        assert result["per_ticker"]["ETF_A"]["total_taxable"] == 3500
        assert result["per_ticker"]["ETF_A"]["exit_tax"] == 3500 * 0.38

    def test_empty_data(self):
        """Empty per-ticker data should return zeros."""
        result = calculate_etf_exit_tax_per_ticker({}, 2026)
        assert result["total_taxable"] == 0
        assert result["total_exit_tax"] == 0
        assert result["per_ticker"] == {}

    def test_rate_in_result(self):
        """The rate used should be returned in the result."""
        result = calculate_etf_exit_tax_per_ticker({"A": {"realized_gains": 100, "dividends": 0, "deemed_gains": 0}}, 2025)
        assert result["rate"] == 0.41

        result = calculate_etf_exit_tax_per_ticker({"A": {"realized_gains": 100, "dividends": 0, "deemed_gains": 0}}, 2026)
        assert result["rate"] == 0.38


# ==============================================================================
# Dividend Income Tax
# ==============================================================================

class TestCalculateDividendIncomeTax:
    """Stock dividends taxed at marginal rate with withholding credits."""

    def test_no_dividends(self):
        result = calculate_dividend_income_tax(0, 40, 0, 0)
        assert result is None

    def test_negative_dividends(self):
        result = calculate_dividend_income_tax(-100, 40, 0, 0)
        assert result is None

    def test_foreign_only_marginal_rate_40(self):
        """€1,000 foreign dividends @ 40% marginal rate, 15% withholding."""
        result = calculate_dividend_income_tax(1000, 40, 0, 1000)

        assert result["gross_dividend_income"] == 1000
        assert result["irish_dividends"] == 0
        assert result["foreign_dividends"] == 1000
        assert result["foreign_withholding_credit"] == 150  # 15% of 1000
        assert result["total_credits"] == 150
        assert result["income_tax_due"] == 400  # 40% of 1000
        assert result["net_tax_due"] == 250  # 400 - 150
        assert result["refund_due"] == 0
        assert result["margin_rate"] == 40

    def test_irish_only_marginal_rate_40(self):
        """€1,000 Irish dividends @ 40% marginal rate, 25% DWT."""
        result = calculate_dividend_income_tax(1000, 40, 1000, 0)

        assert result["irish_dwt_credit"] == 250  # 25% of 1000
        assert result["total_credits"] == 250
        assert result["income_tax_due"] == 400
        assert result["net_tax_due"] == 150

    def test_mixed_irish_and_foreign(self):
        """€500 Irish + €500 foreign @ 40%."""
        result = calculate_dividend_income_tax(1000, 40, 500, 500)

        assert result["irish_dwt_credit"] == 125  # 25% of 500
        assert result["foreign_withholding_credit"] == 75  # 15% of 500
        assert result["total_credits"] == 200
        assert result["income_tax_due"] == 400
        assert result["net_tax_due"] == 200

    def test_lower_marginal_rate(self):
        """€1,000 foreign dividends @ 20% marginal rate."""
        result = calculate_dividend_income_tax(1000, 20, 0, 1000)

        assert result["income_tax_due"] == 200
        assert result["net_tax_due"] == 50  # 200 - 150

    def test_higher_marginal_rate_45(self):
        """€1,000 foreign dividends @ 45% marginal rate."""
        result = calculate_dividend_income_tax(1000, 45, 0, 1000)

        assert result["income_tax_due"] == 450
        assert result["net_tax_due"] == 300  # 450 - 150

    def test_credits_exceed_tax_due(self):
        """If withholding credits exceed income tax, refund is due."""
        result = calculate_dividend_income_tax(500, 20, 500, 0)

        assert result["income_tax_due"] == 100  # 20% of 500
        assert result["irish_dwt_credit"] == 125  # 25% of 500
        assert result["net_tax_due"] == 0
        assert result["refund_due"] == 25


# ==============================================================================
# Formatting helpers
# ==============================================================================

class TestFormatCurrencyDisplay:
    def test_eur(self):
        assert format_currency_display(1234.50, "EUR") == "€1234.50"

    def test_usd(self):
        assert format_currency_display(500.00, "USD") == "$500.00"

    def test_other(self):
        assert format_currency_display(1000, "GBP") == "1000.00 GBP"

    def test_zero_eur(self):
        assert format_currency_display(0, "EUR") == "€0.00"


class TestGetExemptionApplied:
    def test_positive_gain_above_exemption(self):
        assert get_exemption_applied(5000, 1270) == 1270

    def test_positive_gain_below_exemption(self):
        assert get_exemption_applied(1000, 1270) == 1000

    def test_zero_gain(self):
        assert get_exemption_applied(0, 1270) == 0

    def test_negative_gain(self):
        assert get_exemption_applied(-500, 1270) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
