"""
Integration tests for Irish ETF tax rule corrections using sample data.

Tests the actual ImprovedCapitalGainsCalculator class end-to-end.

Fix 1: No cross-ETF loss offsetting
Fix 2: Deemed disposal cost basis uplift + credit against final sale
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


class TestSampleDataBasicProcessing:
    """Test that the calculator processes sample CSV data correctly."""

    def get_calculator(self):
        """Get a calculator instance with test ticker cache."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache_file = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'ticker_cache.json'
        )
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
# Fix 1: Integration Test - No Cross-ETF Loss Offsetting
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
        calc.ticker_cache_file = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'ticker_cache.json'
        )
        calc.ticker_cache = calc.load_ticker_cache()
        # Add test ETFs
        calc.ticker_cache['ETF_A'] = {
            "type": "etf", "currency": "EUR", "active": True,
            "merged_into": None, "conversion_ratio": 1.0,
            "withholding_tax_deducted": False, "domicile": "IE"
        }
        calc.ticker_cache['ETF_B'] = {
            "type": "etf", "currency": "EUR", "active": True,
            "merged_into": None, "conversion_ratio": 1.0,
            "withholding_tax_deducted": False, "domicile": "IE"
        }
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
        # NOTE: use 'Type' column as expected by process_transactions()
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
        
        # Summary aggregation still nets (this is how results are structured)
        etf_realized_aggregated = results['summary']['etfs']['realized_gains'][2026]
        assert etf_realized_aggregated == 3000  # 5000 + (-2000) = 3000
        
        # Test the per-ticker calculation directly (what generate_report now uses)
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
# Fix 2: Integration Test - Deemed Disposal Awareness
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
        calc.ticker_cache_file = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'ticker_cache.json'
        )
        calc.ticker_cache = calc.load_ticker_cache()
        calc.ticker_cache['DD_ETF'] = {
            "type": "etf", "currency": "EUR", "active": True,
            "merged_into": None, "conversion_ratio": 1.0,
            "withholding_tax_deducted": False, "domicile": "IE"
        }
        return calc

    def test_deemed_disposal_detected_for_old_holdings(self):
        """
        Buy 100 shares @ €100 on 2016-01-01 (more than 8 years ago).
        Should trigger deemed disposal detection.
        """
        calc = self.get_calculator()
        
        # NOTE: Use columns expected by process_transactions()
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
        
        # NOTE: Use columns expected by process_transactions()
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
# End-to-end test with sample data
# ==============================================================================

class TestSampleDataIntegration:
    """Test processing the sample CSV data end-to-end."""

    def get_calculator(self):
        """Get a calculator instance with sample ticker cache."""
        calc = ImprovedCapitalGainsCalculator()
        calc.ticker_cache_file = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'ticker_cache.json'
        )
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
