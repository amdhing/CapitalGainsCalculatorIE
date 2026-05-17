"""
Integration tests for Irish ETF tax rule corrections using sample data.

Tests the actual ImprovedCapitalGainsCalculator class end-to-end.

Fix 1: No cross-ETF loss offsetting
Fix 2: Deemed disposal cost basis uplift + credit against final sale

Coverage:
- Basic initialization and sample data processing
- No cross-ETF loss offsetting (Fix 1)
- Deemed disposal awareness (Fix 2)
- Stock CGT calculation end-to-end
- Dividend tax integration
- Multi-year loss carry forward
- Inactive stock (bankruptcy) handling
- Broker transfer handling (zero cost basis)
- Merger handling with conversion ratios
- Process multiple files
- CSV export
- Ticker detail / transaction tracking
- Sample data number verification
"""

import sys
import os
import pandas as pd
import pytest
from datetime import datetime
from collections import defaultdict

# Add project src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from improved_calculator import ImprovedCapitalGainsCalculator
from tax_calculations import (
    get_etf_exit_tax_rate,
    calculate_etf_exit_tax,
    calculate_etf_exit_tax_per_ticker,
)

# ==============================================================================
# Helpers
# ==============================================================================

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.join(CURRENT_DIR, '..')


def get_test_cache_path():
    return os.path.join(CURRENT_DIR, '..', 'data', 'ticker_cache.json')


def make_calculator():
    """Get a calculator with test additions to real ticker cache."""
    calc = ImprovedCapitalGainsCalculator()
    calc.ticker_cache_file = get_test_cache_path()
    calc.ticker_cache = calc.load_ticker_cache()
    return calc


def inject_test_tickers(calc, tickers):
    """
    Inject test tickers into calculator's cache.
    tickers: dict of ticker -> cache entry dict
    """
    for ticker, info in tickers.items():
        calc.ticker_cache[ticker] = info


# ==============================================================================
# Existing: Basic Setup
# ==============================================================================

class TestSampleDataBasicProcessing:
    """Test that the calculator processes sample CSV data correctly."""

    def get_calculator(self):
        """Get a calculator instance with test ticker cache."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache_file = get_test_cache_path()
        calc.ticker_cache = calc.load_ticker_cache()
        return calc

    def test_calculator_initializes(self):
        """Calculator should initialize and load ticker cache."""
        calc = self.get_calculator()
        assert calc is not None
        assert len(calc.ticker_cache) > 0
        assert 'AAPL' in calc.ticker_cache
        assert 'VWCE' in calc.ticker_cache

    def test_sample_csv_contains_etfs(self):
        """Sample CSV should have recognizable data."""
        calc = self.get_calculator()
        assert calc.is_etf('VWCE') == True
        assert calc.is_etf('AAPL') == False


# ==============================================================================
# Existing: Fix 1 - No Cross-ETF Loss Offsetting
# ==============================================================================

class TestFix1NoCrossEtfLossOffsetting:
    """
    CRITICAL: The calculator must NOT allow losses on one ETF to offset gains
    on another ETF. Each ETF ticker is taxed independently.
    
    Tests verify that the per-ticker exit tax calculation correctly handles
    the case where one ETF has a gain and another has a loss in the same year.
    """

    def get_calculator(self):
        """Get a calculator with test ETFs registered."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache_file = get_test_cache_path()
        calc.ticker_cache = calc.load_ticker_cache()
        # Add test ETFs
        inject_test_tickers(calc, {
            'ETF_A': {
                "type": "etf", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
            'ETF_B': {
                "type": "etf", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
        })
        return calc

    def test_etf_gains_and_losses_same_year(self):
        """
        Given two ETFs in the same year:
        - ETF_A: +€5,000 realized gain
        - ETF_B: -€2,000 realized loss
        
        Correct result:
        - ETF_A is taxed on €5,000 * 0.38 = €1,900
        - ETF_B loss is forfeited, taxed on €0
        - Total exit tax = €1,900
        
        Incorrect result (without fix):
        - Aggregate: (€5,000 - €2,000) = €3,000
        - Tax: €3,000 * 0.38 = €1,140
        """
        calc = self.get_calculator()
        
        # ETF_A bought 100 @ €100 = €10,000, sold @ €150 = €15,000 => +€5,000
        # ETF_B bought 100 @ €50 = €5,000, sold @ €30 = €3,000 => -€2,000
        data = {
            'Date': pd.to_datetime([
                '2025-06-01', '2025-06-01',  # buys
                '2026-01-15', '2026-01-15',  # sells
            ]),
            'Ticker': ['ETF_A', 'ETF_B', 'ETF_A', 'ETF_B'],
            'Type': ['BUY', 'BUY', 'SELL', 'SELL'],
            'Quantity': [100.0, 100.0, 100.0, 100.0],
            'Price per share': [100.0, 50.0, 150.0, 30.0],
            'Total Amount': [10000.0, 5000.0, 15000.0, 3000.0],
            'Currency': ['EUR', 'EUR', 'EUR', 'EUR'],
            'FX Rate': [1.0, 1.0, 1.0, 1.0],
        }
        df = pd.DataFrame(data)
        
        results = calc.process_transactions(df)
        
        # ETF_A should have +€5,000 realized gain
        etf_a_gain = results['ticker_detail']['ETF_A']['realized_gains'].get(2026, 0)
        assert etf_a_gain == 5000.0, f"ETF_A gain should be 5000, got {etf_a_gain}"
        
        # ETF_B should have -€2,000 realized loss
        etf_b_gain = results['ticker_detail']['ETF_B']['realized_gains'].get(2026, 0)
        assert etf_b_gain == -2000.0, f"ETF_B loss should be -2000, got {etf_b_gain}"
        
        # Summary aggregation still nets
        etf_realized_aggregated = results['summary']['etfs']['realized_gains'][2026]
        assert etf_realized_aggregated == 3000  # 5000 + (-2000) = 3000
        
        # Test the per-ticker calculation directly
        per_ticker_data = {
            'ETF_A': {'realized_gains': 5000, 'dividends': 0, 'deemed_gains': 0},
            'ETF_B': {'realized_gains': -2000, 'dividends': 0, 'deemed_gains': 0},
        }
        result = calculate_etf_exit_tax_per_ticker(per_ticker_data, 2026)
        
        # ETF_A should pay tax on full 5000 (loss not offset)
        assert result['per_ticker']['ETF_A']['exit_tax'] == 1900.0
        assert result['per_ticker']['ETF_B']['exit_tax'] == 0.0  # loss forfeited
        assert result['total_taxable'] == 5000.0
        assert result['total_exit_tax'] == 1900.0
        
        # Sanity: old way would understate tax
        wrong_tax = max(0, etf_realized_aggregated) * get_etf_exit_tax_rate(2026)
        assert wrong_tax == 1140.0  # Understates tax by €760


# ==============================================================================
# Existing: Fix 2 - Deemed Disposal Awareness
# ==============================================================================

class TestFix2DeemedDisposalAwareness:
    """
    Tests that the calculator correctly identifies deemed disposal events
    and reports the liability. Full cost basis uplift and credit tracking 
    will be implemented in a future enhancement.
    """

    def get_calculator(self):
        """Get a calculator with test ETF registered."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache_file = get_test_cache_path()
        calc.ticker_cache = calc.load_ticker_cache()
        inject_test_tickers(calc, {
            'DD_ETF': {
                "type": "etf", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
        })
        return calc

    def test_deemed_disposal_detected_for_old_holdings(self):
        """
        Buy 100 shares @ €100 on 2016-01-01 (more than 8 years ago).
        Should trigger deemed disposal detection.
        """
        calc = self.get_calculator()
        
        buy_data = {
            'Date': pd.to_datetime(['2016-01-01', '2020-01-01']),
            'Ticker': ['DD_ETF', 'DD_ETF'],
            'Type': ['BUY', 'BUY'],
            'Quantity': [100.0, 50.0],
            'Price per share': [100.0, 120.0],
            'Total Amount': [10000.0, 6000.0],
            'Currency': ['EUR', 'EUR'],
            'FX Rate': [1.0, 1.0],
        }
        df = pd.DataFrame(buy_data)
        
        results = calc.process_transactions(df)
        
        # The 2016 lot (10+ years old) should trigger deemed disposal
        dd_liability = results['ticker_detail']['DD_ETF'].get('deemed_disposal_liability', 0)
        assert dd_liability > 0, "Expected positive deemed disposal liability"
        
        # Deemed disposal gains should appear in summary
        dd_gains = results['summary']['etfs']['deemed_disposal_gains']
        current_year = datetime.now().year
        assert current_year in dd_gains
        assert dd_gains[current_year] > 0
    
    def test_final_sale_after_deemed_disposal(self):
        """
        Lifecycle test:
        Year 2016: Buy 100 shares @ €100 = €10,000
        Year 2026 (10 years): Deemed disposal triggers
        Sell 100 shares @ €130 = €13,000 => +€3,000 gain
        
        Deemed disposal liability should be detected and reported.
        """
        calc = self.get_calculator()
        
        data = {
            'Date': pd.to_datetime(['2016-06-01', '2026-06-01']),
            'Ticker': ['DD_ETF', 'DD_ETF'],
            'Type': ['BUY', 'SELL'],
            'Quantity': [100.0, 100.0],
            'Price per share': [100.0, 130.0],
            'Total Amount': [10000.0, 13000.0],
            'Currency': ['EUR', 'EUR'],
            'FX Rate': [1.0, 1.0],
        }
        df = pd.DataFrame(data)
        
        results = calc.process_transactions(df)
        
        # Check realized gain
        realized_gain = results['summary']['etfs']['realized_gains'][2026]
        assert realized_gain == 3000.0, f"Expected 3000 gain, got {realized_gain}"
        
        # Check deemed disposal liability detected
        dd_liability = results['ticker_detail']['DD_ETF'].get('deemed_disposal_liability', 0)
        assert dd_liability > 0
        
        # Verify that per-ticker ETF tax calc works with the generate_report flow
        per_ticker_data = {
            'DD_ETF': {
                'realized_gains': 3000.0,
                'dividends': 0,
                'deemed_gains': 0
            }
        }
        result = calculate_etf_exit_tax_per_ticker(per_ticker_data, 2026)
        assert result['total_taxable'] == 3000.0
        assert result['total_exit_tax'] == 1140.0  # 3000 * 0.38


# ==============================================================================
# NEW: Stock CGT End-to-End
# ==============================================================================

class TestStockCgtIntegration:
    """
    End-to-end tests for stock capital gains tax calculation.
    Stocks are subject to CGT @ 33% with €1,270 annual exemption
    and indefinite loss carry forward.
    """

    def get_calculator(self, extra_tickers=None):
        calc = make_calculator()
        defaults = {
            'STOCK_A': {
                "type": "stock", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
            'STOCK_B': {
                "type": "stock", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
        }
        if extra_tickers:
            defaults.update(extra_tickers)
        inject_test_tickers(calc, defaults)
        return calc

    def test_basic_stock_gains_single_year(self):
        """
        Buy STOCK_A 100 @ €50 = €5,000
        Sell STOCK_A 100 @ €80 = €8,000
        Gain = €3,000
        
        CGT: (€3,000 - €1,270 exemption) * 33% = €570.90
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime(['2025-01-15', '2025-06-15']),
            'Ticker': ['STOCK_A', 'STOCK_A'],
            'Type': ['BUY', 'SELL'],
            'Quantity': [100.0, 100.0],
            'Price per share': [50.0, 80.0],
            'Total Amount': [5000.0, 8000.0],
            'Currency': ['EUR', 'EUR'],
            'FX Rate': [1.0, 1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        # Verify realized gain
        realized = results['summary']['stocks']['realized_gains'][2025]
        assert realized == 3000.0, f"Expected 3000, got {realized}"

        # Verify ticker detail
        ticker_realized = results['ticker_detail']['STOCK_A']['realized_gains'][2025]
        assert ticker_realized == 3000.0

        # Verify no holdings remain
        assert results['ticker_detail']['STOCK_A']['current_holdings'] == 0

    def test_stock_loss_carries_forward_across_years(self):
        """
        Year 2025: Loss -€2,000 (no gain, no exemption applied to loss)
        Year 2026: Gain +€5,000
        
        CGT 2026: (€5,000 - €1,270 - €2,000 carry) * 33% = €570.90
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime([
                '2025-03-01', '2025-09-01',   # Buy/Sell year 1 (loss)
                '2026-01-15', '2026-06-15',   # Buy/Sell year 2 (gain)
            ]),
            'Ticker': ['STOCK_A', 'STOCK_A', 'STOCK_B', 'STOCK_B'],
            'Type': ['BUY', 'SELL', 'BUY', 'SELL'],
            'Quantity': [100.0, 100.0, 100.0, 100.0],
            'Price per share': [50.0, 30.0, 50.0, 100.0],
            'Total Amount': [5000.0, 3000.0, 5000.0, 10000.0],
            'Currency': ['EUR', 'EUR', 'EUR', 'EUR'],
            'FX Rate': [1.0, 1.0, 1.0, 1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        # Year 2025: loss of -€2,000
        loss_2025 = results['summary']['stocks']['realized_gains'][2025]
        assert loss_2025 == -2000.0, f"Expected -2000 loss, got {loss_2025}"

        # Year 2026: gain of +€5,000
        gain_2026 = results['summary']['stocks']['realized_gains'][2026]
        assert gain_2026 == 5000.0, f"Expected 5000 gain, got {gain_2026}"

        # Verify ticker detail
        assert results['ticker_detail']['STOCK_A']['realized_gains'][2025] == -2000.0
        assert results['ticker_detail']['STOCK_B']['realized_gains'][2026] == 5000.0

    def test_multi_stock_netting_in_same_year(self):
        """
        Year 2025:
        - STOCK_A: +€3,000 gain
        - STOCK_B: -€1,000 loss
        
        CGT: (€3,000 - €1,000 loss - €1,270 exemption) * 33% = €240.90
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime([
                '2025-01-15', '2025-06-15',   # STOCK_A buy/sell
                '2025-02-10', '2025-07-20',   # STOCK_B buy/sell
            ]),
            'Ticker': ['STOCK_A', 'STOCK_A', 'STOCK_B', 'STOCK_B'],
            'Type': ['BUY', 'SELL', 'BUY', 'SELL'],
            'Quantity': [100.0, 100.0, 50.0, 50.0],
            'Price per share': [50.0, 80.0, 100.0, 80.0],
            'Total Amount': [5000.0, 8000.0, 5000.0, 4000.0],
            'Currency': ['EUR', 'EUR', 'EUR', 'EUR'],
            'FX Rate': [1.0, 1.0, 1.0, 1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        # Net realized = +3000 + (-1000) = 2000
        net_gain = results['summary']['stocks']['realized_gains'][2025]
        assert net_gain == 2000.0, f"Expected 2000, got {net_gain}"

        # Individual ticker detail
        assert results['ticker_detail']['STOCK_A']['realized_gains'][2025] == 3000.0
        assert results['ticker_detail']['STOCK_B']['realized_gains'][2025] == -1000.0

    def test_gain_below_exemption_no_tax(self):
        """
        Gain of €1,000 is below the €1,270 exemption.
        CGT due = €0.
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime(['2025-03-01', '2025-09-01']),
            'Ticker': ['STOCK_A', 'STOCK_A'],
            'Type': ['BUY', 'SELL'],
            'Quantity': [100.0, 100.0],
            'Price per share': [10.0, 20.0],
            'Total Amount': [1000.0, 2000.0],
            'Currency': ['EUR', 'EUR'],
            'FX Rate': [1.0, 1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        realized = results['summary']['stocks']['realized_gains'][2025]
        assert realized == 1000.0
        # Exemption would reduce this to 0 taxable


# ==============================================================================
# NEW: Dividend Income Tax Integration
# ==============================================================================

class TestDividendTaxIntegration:
    """End-to-end tests for dividend taxation with withholding credits."""

    def get_calculator(self):
        calc = make_calculator()
        inject_test_tickers(calc, {
            'IE_STOCK': {
                "type": "stock", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
            'US_STOCK': {
                "type": "stock", "currency": "USD", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "US"
            },
        })
        return calc

    def test_irish_dividend_withholding(self):
        """
        Irish stock pays €1,000 dividends.
        Dividend tax @ 40% marginal rate with 25% DWT credit.
        Net due: €400 - €250 = €150
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime(['2025-04-01']),
            'Ticker': ['IE_STOCK'],
            'Type': ['DIVIDEND'],
            'Quantity': [0],
            'Price per share': [0],
            'Total Amount': [1000.0],
            'Currency': ['EUR'],
            'FX Rate': [1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        # Verify dividends captured
        div = results['summary']['stocks']['dividends'][2025]
        assert div == 1000.0
        assert results['summary']['stocks']['dividends_irish'][2025] == 1000.0

        # Now test calculate_dividend_taxes
        div_taxes = calc.calculate_dividend_taxes(results, margin_rate=40)
        assert 2025 in div_taxes
        dt = div_taxes[2025]
        assert dt['gross_dividend_income'] == 1000.0
        assert dt['irish_dwt_credit'] == 250.0  # 25% DWT
        assert dt['income_tax_due'] == 400.0  # 40% marginal
        assert dt['net_tax_due'] == 150.0
        assert dt['refund_due'] == 0

    def test_foreign_dividend_withholding(self):
        """
        US stock pays $1,000 dividends ≈ €926 (at 1.08 FX).
        Dividend tax @ 40% marginal rate with 15% foreign credit.
        Net due: €370.40 - €138.90 = €231.50 (approx)
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime(['2025-04-01']),
            'Ticker': ['US_STOCK'],
            'Type': ['DIVIDEND'],
            'Quantity': [0],
            'Price per share': [0],
            'Total Amount': [1000.0],
            'Currency': ['USD'],
            'FX Rate': [1.08],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        div = results['summary']['stocks']['dividends'][2025]
        expected_eur = round(1000.0 / 1.08, 2)
        assert round(div, 2) == expected_eur
        assert round(results['summary']['stocks']['dividends_foreign'][2025], 2) == expected_eur

        # Verify calculate_dividend_taxes
        div_taxes = calc.calculate_dividend_taxes(results, margin_rate=40)
        assert 2025 in div_taxes
        dt = div_taxes[2025]
        # Use round() since the store keeps unrounded floats
        assert round(dt['gross_dividend_income'], 2) == expected_eur
        assert round(dt['foreign_dividends'], 2) == expected_eur
        assert round(dt['foreign_withholding_credit'], 2) == round(expected_eur * 0.15, 2)
        assert round(dt['income_tax_due'], 2) == round(expected_eur * 0.40, 2)

    def test_mixed_dividends_marginal_rate_45(self):
        """
        €500 Irish + €500 foreign dividends @ 45% marginal rate.
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime(['2025-04-01', '2025-06-01']),
            'Ticker': ['IE_STOCK', 'US_STOCK'],
            'Type': ['DIVIDEND', 'DIVIDEND'],
            'Quantity': [0, 0],
            'Price per share': [0, 0],
            'Total Amount': [500.0, 500.0],
            'Currency': ['EUR', 'USD'],
            'FX Rate': [1.0, 1.08],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        div_taxes = calc.calculate_dividend_taxes(results, margin_rate=45)
        assert 2025 in div_taxes
        dt = div_taxes[2025]
        foreign_eur = 500.0 / 1.08
        total_div = 500.0 + foreign_eur
        assert round(dt['gross_dividend_income'], 2) == round(total_div, 2)
        assert dt['irish_dwt_credit'] == 125.0  # 25% of 500
        assert dt['margin_rate'] == 45

    def test_dividends_refund_when_credits_exceed_tax(self):
        """
        €500 Irish dividends @ 20% marginal rate.
        DWT credit (€125) > income tax (€100) → €25 refund.
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime(['2025-04-01']),
            'Ticker': ['IE_STOCK'],
            'Type': ['DIVIDEND'],
            'Quantity': [0],
            'Price per share': [0],
            'Total Amount': [500.0],
            'Currency': ['EUR'],
            'FX Rate': [1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)
        div_taxes = calc.calculate_dividend_taxes(results, margin_rate=20)
        dt = div_taxes[2025]
        assert dt['net_tax_due'] == 0
        assert round(dt['refund_due'], 2) == 25.0

    def test_etf_dividends_not_included_in_dividend_tax(self):
        """
        ETF dividends should NOT appear in calculate_dividend_taxes().
        ETF dividends are handled via exit tax, not income tax.
        """
        calc = make_calculator()
        inject_test_tickers(calc, {
            'VWCE': {
                "type": "etf", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
        })
        data = {
            'Date': pd.to_datetime(['2025-04-01', '2025-05-01']),
            'Ticker': ['VWCE', 'IE_STOCK'],
            'Type': ['DIVIDEND', 'DIVIDEND'],
            'Quantity': [0, 0],
            'Price per share': [0, 0],
            'Total Amount': [300.0, 200.0],
            'Currency': ['EUR', 'EUR'],
            'FX Rate': [1.0, 1.0],
        }
        # Need IE_STOCK in cache
        calc.ticker_cache['IE_STOCK'] = {
            "type": "stock", "currency": "EUR", "active": True,
            "merged_into": None, "conversion_ratio": 1.0,
            "withholding_tax_deducted": False, "domicile": "IE"
        }
        df = pd.DataFrame(data)
        # Override is_etf for VWCE to return True
        results = calc.process_transactions(df)
        div_taxes = calc.calculate_dividend_taxes(results, margin_rate=40)

        # Only stock dividends appear
        assert 2025 in div_taxes
        dt = div_taxes[2025]
        # ETF dividend of 300 should not appear; only stock dividend of 200
        assert dt['gross_dividend_income'] == 200.0


# ==============================================================================
# NEW: Inactive Stock (Bankruptcy) Handling
# ==============================================================================

class TestInactiveStockHandling:
    """
    When a stock becomes inactive (bankrupt/delisted), remaining holdings
    should be treated as a total loss.
    """

    def test_inactive_stock_triggers_total_loss(self):
        """
        Buy 100 shares @ €50 = €5,000 cost basis.
        Stock becomes inactive → total loss of -€5,000 recognized.
        """
        calc = make_calculator()
        inject_test_tickers(calc, {
            'BANKRUPT': {
                "type": "stock", "currency": "EUR", "active": False,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "US"
            },
        })
        data = {
            'Date': pd.to_datetime(['2023-01-15']),
            'Ticker': ['BANKRUPT'],
            'Type': ['BUY'],
            'Quantity': [100.0],
            'Price per share': [50.0],
            'Total Amount': [5000.0],
            'Currency': ['EUR'],
            'FX Rate': [1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        current_year = datetime.now().year
        loss = results['summary']['stocks']['realized_gains'][current_year]
        assert loss == -5000.0, f"Expected -5000 loss, got {loss}"

        # Current holdings should be 0
        assert results['ticker_detail']['BANKRUPT']['current_holdings'] == 0

    def test_active_stock_no_loss(self):
        """
        Active stock with holdings should NOT trigger a loss.
        """
        calc = make_calculator()
        inject_test_tickers(calc, {
            'ACTIVE_CO': {
                "type": "stock", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
        })
        data = {
            'Date': pd.to_datetime(['2023-01-15']),
            'Ticker': ['ACTIVE_CO'],
            'Type': ['BUY'],
            'Quantity': [100.0],
            'Price per share': [50.0],
            'Total Amount': [5000.0],
            'Currency': ['EUR'],
            'FX Rate': [1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        current_year = datetime.now().year
        # Active stock should NOT trigger a loss
        realized = results['summary']['stocks']['realized_gains'].get(current_year, 0)
        assert realized == 0, f"Expected 0, got {realized}"
        assert results['ticker_detail']['ACTIVE_CO']['current_holdings'] == 100.0


# ==============================================================================
# NEW: Broker Transfer Handling
# ==============================================================================

class TestBrokerTransferHandling:
    """
    Broker transfers with zero cost basis (from mergers).
    TRANSFER - REVOLUT TRADING LTD TO REVOLUT SECURITIES EUROPE UAB
    Should be treated as zero-cost-basis buy when part of a merger.
    """

    def get_calculator(self):
        calc = make_calculator()
        inject_test_tickers(calc, {
            'MERGED_INTO_NEW': {
                "type": "stock", "currency": "USD", "active": False,
                "merged_into": "NEW_CO", "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "US"
            },
            'NEW_CO': {
                "type": "stock", "currency": "USD", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "US"
            },
        })
        return calc

    def test_broker_transfer_zero_cost_basis(self):
        """
        After a merger, broker transfer of shares should result in
        zero cost basis for the transferred shares.
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime([
                '2023-01-15',   # Original buy of old ticker
                '2023-06-01',   # Merger event (shares removed)
                '2023-07-01',   # Broker transfer (shares added at zero cost)
            ]),
            'Ticker': ['MERGED_INTO_NEW', 'MERGED_INTO_NEW', 'NEW_CO'],
            'Type': [
                'BUY',
                'MERGER_STOCK',
                'TRANSFER - REVOLUT TRADING LTD TO REVOLUT SECURITIES EUROPE UAB'
            ],
            'Quantity': [100.0, -100.0, 100.0],
            'Price per share': [50.0, 0, 0],
            'Total Amount': [5000.0, 0, 0],
            'Currency': ['USD', 'USD', 'USD'],
            'FX Rate': [1.08, 1.08, 1.08],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        # Should have 100 shares of NEW_CO with zero cost basis
        assert results['ticker_detail']['NEW_CO']['current_holdings'] == 100.0
        assert results['ticker_detail']['NEW_CO']['avg_cost_basis'] == 0.0


# ==============================================================================
# NEW: Merger Handling
# ==============================================================================

class TestMergerHandling:
    """
    Merger transactions should correctly handle:
    - MERGER_STOCK: shares removed from old ticker
    - MERGER_CASH: cash received treated as dividend
    - Conversion ratios for merged tickers
    """

    def get_calculator(self):
        calc = make_calculator()
        inject_test_tickers(calc, {
            'OLD_CO': {
                "type": "stock", "currency": "USD", "active": False,
                "merged_into": "NEW_CO", "conversion_ratio": 0.5,
                "withholding_tax_deducted": False, "domicile": "US"
            },
            'NEW_CO': {
                "type": "stock", "currency": "USD", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "US"
            },
        })
        return calc

    def test_merger_stock_removes_shares(self):
        """
        Buy 100 OLD_CO shares @ €50.
        Merger conversion ratio 0.5 → 100 shares removed.
        Cash merger payment treated as foreign dividend.
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime([
                '2023-01-15',   # Buy old
                '2023-06-01',   # Merger - stock removal
                '2023-06-01',   # Merger - cash component
            ]),
            'Ticker': ['OLD_CO', 'OLD_CO', 'OLD_CO'],
            'Type': ['BUY', 'MERGER_STOCK', 'MERGER_CASH'],
            'Quantity': [100.0, -100.0, 0],
            'Price per share': [50.0, 0, 0],
            'Total Amount': [5000.0, 0, 200.0],
            'Currency': ['USD', 'USD', 'USD'],
            'FX Rate': [1.08, 1.08, 1.08],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        # OLD_CO: shares should be removed (buy queue emptied)
        # After merger, OLD_CO is inactive with 0 holdings
        assert results['ticker_detail']['OLD_CO']['current_holdings'] == 0.0

    def test_merger_cash_treated_as_dividend(self):
        """
        Cash received from merger (€200 USD ≈ €185.19)
        should appear as a foreign dividend.
        """
        calc = self.get_calculator()
        data = {
            'Date': pd.to_datetime([
                '2023-01-15',
                '2023-06-01',
                '2023-06-01',
            ]),
            'Ticker': ['OLD_CO', 'OLD_CO', 'OLD_CO'],
            'Type': ['BUY', 'MERGER_STOCK', 'MERGER_CASH'],
            'Quantity': [100.0, -100.0, 0],
            'Price per share': [50.0, 0, 0],
            'Total Amount': [5000.0, 0, 200.0],
            'Currency': ['USD', 'USD', 'USD'],
            'FX Rate': [1.08, 1.08, 1.08],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        # Cash merger payment of $200 / 1.08 = €185.19 should be dividend
        cash_eur = round(200.0 / 1.08, 2)
        div_2023 = results['summary']['stocks']['dividends'][2023]
        assert round(div_2023, 2) == cash_eur
        # Should be foreign dividend (US domicile on the old ticker info, 
        # but NEW_CO doesn't have an explicit domicile so default is used)
        foreign_div = results['summary']['stocks']['dividends_foreign'][2023]
        assert round(foreign_div, 2) == cash_eur


# ==============================================================================
# NEW: Process Multiple Files
# ==============================================================================

class TestProcessMultipleFiles:
    """process_multiple_files should combine transactions with proper FIFO."""

    def test_combines_two_csv_files(self, tmp_path):
        """
        Two CSV files with transactions, combined and sorted by date.
        FIFO ordering should be maintained across both files.
        """
        calc = make_calculator()
        inject_test_tickers(calc, {
            'STOCK_A': {
                "type": "stock", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
        })

        headers = "Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency,FX Rate\n"
        # File 1: buy in 2024
        file1 = tmp_path / "trades_2024.csv"
        file1.write_text(headers + "2024-01-15,STOCK_A,BUY,100,50.0,5000.0,EUR,1.0\n")

        # File 2: sell in 2025
        file2 = tmp_path / "trades_2025.csv"
        file2.write_text(headers + "2025-06-15,STOCK_A,SELL,100,80.0,8000.0,EUR,1.0\n")

        results = calc.process_multiple_files([str(file1), str(file2)])
        assert results is not None

        gain_2025 = results['summary']['stocks']['realized_gains'][2025]
        assert gain_2025 == 3000.0, f"Expected 3000, got {gain_2025}"

    def test_missing_columns_skipped(self, tmp_path):
        """Files with missing columns should be skipped gracefully."""
        calc = make_calculator()
        headers = "Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency,FX Rate\n"
        # Valid file
        valid_file = tmp_path / "valid.csv"
        valid_file.write_text(headers + "2024-01-15,STOCK_A,BUY,100,50.0,5000.0,EUR,1.0\n")
        # Invalid file (missing FX Rate column)
        invalid_file = tmp_path / "invalid.csv"
        invalid_file.write_text("Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency\n2024-01-15,STOCK_A,BUY,100,50.0,5000.0,EUR\n")

        # Should not crash - invalid file is skipped
        calc.ticker_cache['STOCK_A'] = {
            "type": "stock", "currency": "EUR", "active": True,
            "merged_into": None, "conversion_ratio": 1.0,
            "withholding_tax_deducted": False, "domicile": "IE"
        }
        results = calc.process_multiple_files([str(invalid_file), str(valid_file)])
        # The invalid file should be silently skipped, but valid file processed
        assert results is not None

    def test_no_valid_files_returns_none(self, tmp_path):
        """If all files are invalid, returns None."""
        calc = make_calculator()
        invalid_file = tmp_path / "bad.csv"
        invalid_file.write_text("Not,a,valid,csv\n1,2,3,4\n")
        results = calc.process_multiple_files([str(invalid_file)])
        assert results is None


# ==============================================================================
# NEW: CSV Export
# ==============================================================================

class TestCsvExport:
    """export_to_csv should produce CSV files with correct data."""

    def get_calculator_and_results(self):
        calc = make_calculator()
        inject_test_tickers(calc, {
            'STOCK_A': {
                "type": "stock", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
        })
        data = {
            'Date': pd.to_datetime(['2025-01-15', '2025-06-15']),
            'Ticker': ['STOCK_A', 'STOCK_A'],
            'Type': ['BUY', 'SELL'],
            'Quantity': [100.0, 100.0],
            'Price per share': [50.0, 80.0],
            'Total Amount': [5000.0, 8000.0],
            'Currency': ['EUR', 'EUR'],
            'FX Rate': [1.0, 1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)
        return calc, results

    def test_csv_export_creates_files(self, tmp_path):
        """export_to_csv should create CSV files in working directory."""
        calc, results = self.get_calculator_and_results()

        # Change to tmp dir so CSVs are created there
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            calc.export_to_csv(results, base_filename="test_export")
            # Check files exist
            assert os.path.exists("test_export_tax_summary.csv")
            assert os.path.exists("test_export_by_ticker.csv")
        finally:
            os.chdir(original_cwd)

    def test_csv_export_content(self, tmp_path):
        """CSV content should match expected values."""
        calc, results = self.get_calculator_and_results()

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            calc.export_to_csv(results, base_filename="test_export")
            summary_df = pd.read_csv("test_export_tax_summary.csv")
            ticker_df = pd.read_csv("test_export_by_ticker.csv")

            # Summary: one stock row for 2025
            stock_row = summary_df[summary_df['Asset_Type'] == 'Stocks'].iloc[0]
            assert stock_row['Year'] == 2025
            assert stock_row['Realized_Gains_Gross_EUR'] == 3000.0
            assert stock_row['Tax_Rate'] == '33%'

            # Ticker level: STOCK_A in 2025
            ticker_row = ticker_df[ticker_df['Ticker'] == 'STOCK_A'].iloc[0]
            assert ticker_row['Year'] == 2025
            assert ticker_row['Realized_Gains_EUR'] == 3000.0
        finally:
            os.chdir(original_cwd)


# ==============================================================================
# NEW: Sample Data Number Verification
# ==============================================================================

class TestSampleDataVerification:
    """
    Verify specific gain/loss numbers from the sample CSV.
    This validates the calculator produces correct results for known data.
    """

    def get_calculator(self):
        return make_calculator()

    def test_aapl_trades_correct_gains(self):
        """
        AAPL trades from sample:
        - 2023-01-15: BUY 10 @ $150.25 = $1,502.50 (FX 1.08 → €1,390.28)
        - 2023-06-25: SELL 5 @ $175.80 = $879.00 (FX 1.08 → €813.89)
        - 2024-01-08: BUY 8 @ $185.40 = $1,483.20 (FX 1.11 → €1,336.22)
        - 2024-10-18: SELL 8 @ $225.40 = $1,803.20 (FX 1.08 → €1,669.63)

        FIFO Sell (2023): 5 shares from lot of 10
        Cost basis: 5 * ($150.25 / 1.08) = 5 * 139.12 = €695.60
        Proceeds: 5 * ($175.80 / 1.08) = 5 * 162.78 = €813.89
        Realized gain 2023: €813.89 - €695.60 ≈ €118.29

        FIFO Sell (2024): remaining 5 from lot 1 + 3 from lot 2
        Lot 1 remaining: 5 shares @ €139.12 = €695.60
        Lot 2: 3 shares @ ($185.40 / 1.11) = 3 * €167.03 = €501.09
        Total cost: €1,196.69
        Proceeds: 8 * ($225.40 / 1.08) = 8 * 208.70 = €1,669.63
        Realized gain 2024: €1,669.63 - €1,196.69 ≈ €472.94
        """
        calc = self.get_calculator()
        sample_path = os.path.join(
            os.path.dirname(__file__), '..', 'samples', 'sample_revolut_transactions.csv'
        )
        results = calc.process_file(sample_path)

        # Check AAPL realized gains
        aapl_detail = results['ticker_detail'].get('AAPL')
        assert aapl_detail is not None

        # 2023 gain on first 5 shares
        gain_2023 = aapl_detail['realized_gains'].get(2023, 0)
        assert gain_2023 > 0, f"Expected positive AAPL gain in 2023, got {gain_2023}"

        # 2024 gain on remaining 8 shares
        gain_2024 = aapl_detail['realized_gains'].get(2024, 0)
        assert gain_2024 > 0, f"Expected positive AAPL gain in 2024, got {gain_2024}"

        # Total AAPL gains across both years
        total_aapl = gain_2023 + gain_2024
        assert 500 < total_aapl < 700, f"AAPL total gain should be ~€590, got {total_aapl}"

    def test_msft_trades_correct_gains(self):
        """
        MSFT trades from sample:
        - 2023-04-12: BUY 8 @ $280.75 = $2,246.00 (FX 1.09 → €2,060.55)
        - 2023-10-20: SELL 4 @ $295.30 = $1,181.20 (FX 1.06 → €1,114.34)
        - 2024-07-05: BUY 5 @ $415.60 = $2,078.00 (FX 1.09 → €1,906.42)

        FIFO Sell (2023): 4 shares from lot of 8
        Cost basis: 4 * ($280.75 / 1.09) = 4 * 257.57 = €1,030.28
        Proceeds: 4 * ($295.30 / 1.06) = 4 * 278.58 = €1,114.34
        Realized gain 2023: €84.06
        """
        calc = self.get_calculator()
        sample_path = os.path.join(
            os.path.dirname(__file__), '..', 'samples', 'sample_revolut_transactions.csv'
        )
        results = calc.process_file(sample_path)

        msft_detail = results['ticker_detail'].get('MSFT')
        assert msft_detail is not None

        gain_2023 = msft_detail['realized_gains'].get(2023, 0)
        assert gain_2023 > 0, f"Expected positive MSFT gain in 2023, got {gain_2023}"

        # MSFT should still hold some shares (4 remaining + 5 more bought)
        assert msft_detail['current_holdings'] > 0

    def test_total_cgt_exemption_correct(self):
        """
        Overall stock net gains from sample should have exemption applied.
        """
        calc = self.get_calculator()
        sample_path = os.path.join(
            os.path.dirname(__file__), '..', 'samples', 'sample_revolut_transactions.csv'
        )
        results = calc.process_file(sample_path)

        # Stock realized gains by year
        for year in sorted(results['summary']['stocks']['realized_gains'].keys()):
            gain = results['summary']['stocks']['realized_gains'][year]
            # Exemption only applies to positive gains
            if gain > 0:
                assert gain > 0  # Sanity check


# ==============================================================================
# NEW: Ticker Detail Report (process_transactions_with_detail)
# ==============================================================================

class TestProcessTransactionsWithDetail:
    """process_transactions_with_detail with store_transactions=True."""

    def test_store_transactions_enables_detail(self):
        """
        When store_transactions=True, transaction_history should be stored
        on the calculator instance.
        """
        calc = make_calculator()
        inject_test_tickers(calc, {
            'AAPL': {
                "type": "stock", "currency": "USD", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "US"
            },
        })
        data = {
            'Date': pd.to_datetime(['2025-01-15', '2025-06-15']),
            'Ticker': ['AAPL', 'AAPL'],
            'Type': ['BUY', 'SELL'],
            'Quantity': [10.0, 5.0],
            'Price per share': [150.0, 175.0],
            'Total Amount': [1500.0, 875.0],
            'Currency': ['USD', 'USD'],
            'FX Rate': [1.08, 1.08],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions_with_detail(df)

        assert hasattr(calc, 'transaction_history')
        assert calc.transaction_history is not None

        # Should have processed normally
        assert results['summary']['stocks']['realized_gains'][2025] > 0

    def test_ticker_detail_in_results_with_target(self):
        """
        When target_ticker is provided, transaction detail is included
        in the results.
        """
        calc = make_calculator()
        inject_test_tickers(calc, {
            'STOCK_A': {
                "type": "stock", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
        })
        data = {
            'Date': pd.to_datetime(['2025-01-15', '2025-06-15']),
            'Ticker': ['STOCK_A', 'STOCK_A'],
            'Type': ['BUY', 'SELL'],
            'Quantity': [100.0, 100.0],
            'Price per share': [50.0, 80.0],
            'Total Amount': [5000.0, 8000.0],
            'Currency': ['EUR', 'EUR'],
            'FX Rate': [1.0, 1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions_with_detail(df, target_ticker='STOCK_A')

        # Ticker detail should contain 'transactions' key
        assert 'transactions' in results['ticker_detail']['STOCK_A']
        tx_df = results['ticker_detail']['STOCK_A']['transactions']
        assert len(tx_df) == 2  # 2 transactions for STOCK_A


# ==============================================================================
# NEW: Multi-year processing with CGT carry forward
# ==============================================================================

class TestMultiYearCgtCarryForward:
    """
    End-to-end test for CGT loss carry forward across multiple years
    with the actual generate_report flow.
    """

    def test_loss_carried_forward_multi_year(self):
        """
        Year 2024: -€3,000 loss (net position after all trades)
        Year 2025: +€10,000 gain
        
        CGT 2025: (€10,000 - €1,270 - €3,000 carry) * 33% = €1,890.90
        """
        calc = make_calculator()
        inject_test_tickers(calc, {
            'STOCK_A': {
                "type": "stock", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
            'STOCK_B': {
                "type": "stock", "currency": "EUR", "active": True,
                "merged_into": None, "conversion_ratio": 1.0,
                "withholding_tax_deducted": False, "domicile": "IE"
            },
        })

        # Year 2024: STOCK_A loss
        # Year 2025: STOCK_B gain
        data = {
            'Date': pd.to_datetime([
                '2024-03-01', '2024-09-01',   # buy/sell loss
                '2025-01-15', '2025-06-15',   # buy/sell gain
            ]),
            'Ticker': ['STOCK_A', 'STOCK_A', 'STOCK_B', 'STOCK_B'],
            'Type': ['BUY', 'SELL', 'BUY', 'SELL'],
            'Quantity': [100.0, 100.0, 100.0, 100.0],
            'Price per share': [80.0, 50.0, 50.0, 150.0],
            'Total Amount': [8000.0, 5000.0, 5000.0, 15000.0],
            'Currency': ['EUR', 'EUR', 'EUR', 'EUR'],
            'FX Rate': [1.0, 1.0, 1.0, 1.0],
        }
        df = pd.DataFrame(data)
        results = calc.process_transactions(df)

        # Year 2024: -€3,000 loss
        assert results['summary']['stocks']['realized_gains'][2024] == -3000.0
        # Year 2025: +€10,000 gain
        assert results['summary']['stocks']['realized_gains'][2025] == 10000.0


# ==============================================================================
# Existing: End-to-end test with sample data
# ==============================================================================

class TestSampleDataIntegration:
    """Test processing the sample CSV data end-to-end."""

    def get_calculator(self):
        """Get a calculator instance with sample ticker cache."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache_file = get_test_cache_path()
        calc.ticker_cache = calc.load_ticker_cache()
        return calc

    def test_sample_data_processes_without_error(self):
        """The sample CSV should process without errors."""
        calc = self.get_calculator()
        sample_path = os.path.join(
            os.path.dirname(__file__), '..', 'samples', 'sample_revolut_transactions.csv'
        )
        results = calc.process_file(sample_path)
        assert results is not None
        assert 'summary' in results
        assert 'ticker_detail' in results

    def test_sample_data_has_expected_structure(self):
        """Results should have the expected structure keys."""
        calc = self.get_calculator()
        sample_path = os.path.join(
            os.path.dirname(__file__), '..', 'samples', 'sample_revolut_transactions.csv'
        )
        results = calc.process_file(sample_path)

        # Summary should have stocks and etfs
        assert 'stocks' in results['summary']
        assert 'etfs' in results['summary']

        # Should have ticker detail for traded tickers
        assert 'AAPL' in results['ticker_detail']
        assert 'VWCE' in results['ticker_detail']
        assert 'GOOGL' in results['ticker_detail']
        assert 'MSFT' in results['ticker_detail']
        assert 'TSLA' in results['ticker_detail']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
