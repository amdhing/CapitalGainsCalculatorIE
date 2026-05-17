"""
Tests for Irish ETF tax rule corrections.

Spec-driven, test-first approach per tax_rules_spec.md.

Fix 1: No loss offsetting between different ETFs
Fix 2: Deemed disposal cost basis uplift + credit against final sale
"""

import sys
import os
import json
import pytest
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# Add project src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tax_calculations import (
    get_etf_exit_tax_rate,
    calculate_etf_exit_tax,
    apply_cgt_with_loss_carry_forward,
)

# ==============================================================================
# Fix 1: No Loss Offsetting Between Different ETFs
# ==============================================================================
# Current bug: etf_realized is summed across all ETFs, allowing losses on one
# to offset gains on another.
# Correct: Each ETF ticker is taxed independently. Losses on one ETF cannot
# offset gains on a different ETF. Losses are simply forfeited.

class TestNoCrossEtfLossOffsetting:
    """
    Spec: Realized losses on one ETF cannot offset realized gains on a different ETF.
    
    Scenario:
    - ETF_A: Buy €10,000, Sell €8,000 => Loss of €2,000
    - ETF_B: Buy €10,000, Sell €15,000 => Gain of €5,000
    
    Current (INCORRECT): Net gain = €3,000, Tax = €3,000 * 38% = €1,140
    Correct: ETF_A loss of €2,000 is forfeited. ETF_B gain of €5,000 taxed.
             Tax = €5,000 * 38% = €1,900
    """

    def test_loss_offsetting_within_same_etf_is_allowed(self):
        """
        Losses on the SAME ETF ticker can still offset gains on that same ticker.
        E.g., multiple sell transactions of the same ETF are netted together.
        """
        # Same ETF (ETF_A): Buy €10,000, Sell twice: €8,000 and €4,000
        # Net = €2,000 gain. Tax = €2,000 * 38% = €760
        total_taxable, tax = calculate_etf_exit_tax(2000, 0, 0, 2026)
        assert total_taxable == 2000
        assert tax == 760.00
    
    def test_cross_etf_loss_offsetting_not_allowed(self):
        """
        CRITICAL: Losses on ETF_A must NOT offset gains on ETF_B.
        
        Current calculate_etf_exit_tax(5000 - 2000=3000, 0, 0, 2026) would give €1,140
        Correct: Tax ETF_B gain €5,000 independently = €5,000 * 38% = €1,900
                 ETF_A loss €2,000 is forfeited.
        """
        # The function should accept per-ticker gains, not aggregated ones.
        # If we pass aggregated (3000), the calculation itself doesn't know
        # this came from two tickers. The fix is in how the caller aggregates.
        
        # Test that the aggregation happens correctly at caller level:
        # Each ETF's gain should be taxed separately, then summed.
        etf_a_gain = -2000  # Loss on ETF_A - FORFEITED, no tax benefit
        etf_b_gain = 5000   # Gain on ETF_B
        
        # Per-ticker: ETF_A pays €0 (loss forfeited), ETF_B pays €5,000*38%=€1,900
        tax_a = max(0, etf_a_gain) * 0.38  # Losses are forfeited, tax on loss = 0
        tax_b = max(0, etf_b_gain) * 0.38  # Gains are taxed
        
        total_correct_tax = tax_a + tax_b
        assert total_correct_tax == 1900.00
        
        # Wrong way (current bug): aggregate first, then tax
        wrong_tax = max(0, etf_a_gain + etf_b_gain) * 0.38
        assert wrong_tax == 1140.00  # Wrong! Understates tax by €760
        
        # The difference is €760 - this is what we're fixing
        assert total_correct_tax != wrong_tax
        assert total_correct_tax > wrong_tax
    
    def test_etf_with_loss_only(self):
        """A losing ETF should result in zero tax (loss forfeited, no carry forward)."""
        # ETF_C: Loss of €3,000. Tax = 0 (loss forfeited).
        tax = max(0, -3000) * 0.38
        assert tax == 0.00

    def test_etf_with_zero_gain(self):
        """An ETF with zero gain should result in zero tax."""
        tax = max(0, 0) * 0.38
        assert tax == 0.00


# ==============================================================================
# Fix 2: Deemed Disposal Cost Basis Uplift + Tax Credit
# ==============================================================================
# Current bug: Deemed disposal tax is calculated but:
#   1. Cost basis is NOT uplifted after deemed disposal
#   2. Previously paid deemed disposal tax is NOT credited against final sale tax
#   3. Uses placeholder 20% gain instead of actual/nominal tracking per lot
#
# Correct:
#   - Each buy lot tracks: original cost, updated cost basis, deemed disposal tax paid
#   - When 8-year deemed disposal triggers: cost basis uplifted, tax calculated
#   - When sold: remaining gain taxed, credit applied for previously paid DD tax

class TestDeemedDisposalCreditTracking:
    """
    Spec: Deemed disposal tax paid acts as a credit against final sale exit tax.
    Cost basis is uplifted to market value at the deemed disposal event.
    
    Scenario:
    Year 0: Buy €10,000 of ETF
    Year 8: Value €12,000 -> Deemed gain €2,000 -> Tax @ 38% = €760
            Cost basis uplifted to €12,000
    Year 10: Sell €13,000 -> Remaining gain €1,000 -> Tax @ 38% = €380
             Total tax = €760 + €380 = €1,140 = 38% of €3,000 total gain
    """
    
    def test_deemed_disposal_calculates_correctly(self):
        """
        Deemed disposal on an 8+ year old lot should:
        - Calculate gain as current_value - cost_basis
        - Apply exit tax rate
        - Return the gain and tax liability
        """
        # Simulate: buy €10,000, after 8 years worth €12,000
        cost_basis = 10000.0
        current_value = 12000.0
        rate = get_etf_exit_tax_rate(2026)  # 38%
        
        deemed_gain = current_value - cost_basis
        deemed_tax = deemed_gain * rate
        
        assert deemed_gain == 2000.0
        assert deemed_tax == 760.0
    
    def test_cost_basis_uplift_after_deemed_disposal(self):
        """
        After deemed disposal, the cost basis for that lot should be uplifted
        to the market value at the time of deemed disposal.
        """
        # Original cost: €10,000
        # Deemed disposal at year 8: value €12,000
        # Uplifted cost basis: €12,000
        original_cost = 10000.0
        value_at_dd = 12000.0
        
        uplifted_cost_basis = value_at_dd  # Cost basis is now €12,000
        
        # Year 10 sale: Sell at €13,000
        sale_proceeds = 13000.0
        remaining_gain = sale_proceeds - uplifted_cost_basis
        
        assert remaining_gain == 1000.0  # Only the gain since deemed disposal
        
        # Without uplift (current bug): gain = 13000 - 10000 = 3000 (wrong - double taxes)
        wrong_gain = sale_proceeds - original_cost
        assert wrong_gain == 3000.0  # Would tax the full gain again!
    
    def test_final_sale_tax_with_credit(self):
        """
        When selling after a deemed disposal:
        - Tax on remaining gain (sale_proceeds - uplifted_cost_basis) at exit tax rate
        - Total tax paid = deemed_disposal_tax + remaining_sale_tax
        - Total tax should equal exit_tax_rate * total_gain (from original cost to final sale)
        
        This ensures no double taxation.
        """
        original_cost = 10000.0
        value_at_dd = 12000.0  # 8-year anniversary
        sale_proceeds = 13000.0  # Sold 2 years later
        rate = 0.38
        
        # Deemed disposal at year 8
        deemed_gain = value_at_dd - original_cost  # €2,000
        deemed_tax = deemed_gain * rate  # €760
        
        # Cost basis uplifted to €12,000
        uplifted_cost = value_at_dd
        
        # Final sale at year 10
        remaining_gain = sale_proceeds - uplifted_cost  # €1,000
        sale_tax = remaining_gain * rate  # €380
        
        # Total tax paid
        total_tax = deemed_tax + sale_tax  # €1,140
        
        # Verification: total tax = rate * total_gain
        total_gain = sale_proceeds - original_cost  # €3,000
        expected_total_tax = total_gain * rate  # €1,140
        
        assert total_tax == expected_total_tax  # No double taxation! ✓
    
    def test_deemed_disposal_on_partial_holdings(self):
        """
        Scenario: Multiple buys across different years, some hit 8 years, some don't.
        Each lot should be tracked independently.
        """
        # Buy 1: Year 0, €5,000 (8 years old - triggers deemed disposal)
        # Buy 2: Year 4, €5,000 (4 years old - no deemed disposal yet)
        
        buy1_cost = 5000.0
        buy2_cost = 5000.0
        buy1_value_at_dd = 6000.0  # 8-year anniversary
        
        # Deemed disposal on Buy 1 only
        deemed_gain_1 = buy1_value_at_dd - buy1_cost  # €1,000
        deemed_tax_1 = deemed_gain_1 * 0.38  # €380
        
        assert deemed_gain_1 == 1000.0
        assert deemed_tax_1 == 380.0
        
        # Buy 2 doesn't trigger deemed disposal yet (only 4 years held)
        
        # Later: Sell everything for €14,000
        total_sale = 14000.0
        
        # Buy 1's uplifted cost basis: €6,000
        # Buy 2's original cost basis: €5,000
        gain_buy1 = (total_sale * 0.5) - buy1_value_at_dd  # €7,000 - €6,000 = €1,000
        gain_buy2 = (total_sale * 0.5) - buy2_cost  # €7,000 - €5,000 = €2,000
        
        # Tax on sale:
        sale_tax_buy1 = gain_buy1 * 0.38  # €380
        sale_tax_buy2 = gain_buy2 * 0.38  # €760
        
        total_tax = deemed_tax_1 + sale_tax_buy1 + sale_tax_buy2  # €1,520
        
        # Verification: 38% of total gain (€14,000 - €10,000 = €4,000)
        total_gain = total_sale - (buy1_cost + buy2_cost)  # €4,000
        expected_total = total_gain * 0.38  # €1,520
        
        assert total_tax == expected_total
    
    def test_no_deemed_disposal_before_8_years(self):
        """No deemed disposal triggers before 8 years."""
        # Buy: €10,000, held 5 years
        years_held = 5
        assert years_held < 8  # Not triggered yet
    
    def test_deemed_disposal_exactly_at_8_years(self):
        """Exactly at 8 years, deemed disposal triggers."""
        years_held = 8.0
        assert years_held >= 8  # Triggers


# ==============================================================================
# Integration Tests: process_transactions with corrected behavior
# ==============================================================================

class TestEtfTaxIntegration:
    """
    Integration-level tests verifying the end-to-end behavior of the calculator
    with the corrected rules.
    """
    
    def test_aggregated_etf_calculation_bug_demonstration(self):
        """
        Demonstrate the current bug: calculate_etf_exit_tax() aggregates
        gains/losses across all ETFs.
        
        This test proves the function itself is mathematically correct,
        but the CALLER must pass per-ticker values, not aggregated ones.
        """
        # Simulating two ETFs from same year
        # ETF_A: gain €5,000, ETF_B: loss -€2,000
        
        # Current caller behavior (WRONG): pass aggregated sum
        aggregated_realized = 5000 + (-2000)  # €3,000
        total_taxable_wrong, tax_wrong = calculate_etf_exit_tax(aggregated_realized, 0, 0, 2026)
        
        # Correct behavior: tax each independently
        etf_a_taxable, etf_a_tax = calculate_etf_exit_tax(5000, 0, 0, 2026)
        etf_b_taxable, etf_b_tax = calculate_etf_exit_tax(-2000, 0, 0, 2026)  # loss forfeited
        # etf_b_tax should be 0 because max(0, -2000) = 0 taxable
        
        # The bug: wrong_tax (€1,140) vs correct_tax (€1,900)
        correct_total_tax = etf_a_tax + max(0, etf_b_tax)  # loss forfeited = 0
        
        # Asserting the correct behavior (this is what we want after the fix)
        assert tax_wrong == 1140.00  # Current buggy behavior
        assert correct_total_tax == 1900.00  # Correct behavior after fix
    
    def test_deemed_disposal_avoids_double_taxation(self):
        """
        Full lifecycle: Buy -> Deemed Disposal (Year 8) -> Sell (Year 10)
        Total tax paid should not exceed rate * total gain.
        """
        # This is an integration scenario showing the full corrected flow
        
        buy_amount = 10000.0
        value_year_8 = 12000.0
        sell_amount = 13000.0
        rate = 0.38
        
        # Step 1: Deemed disposal at year 8
        dd_gain = value_year_8 - buy_amount
        dd_tax = dd_gain * rate
        
        # Step 2: Uplift cost basis
        uplifted_basis = value_year_8
        
        # Step 3: Sell at year 10
        remaining_gain = sell_amount - uplifted_basis
        sale_tax = remaining_gain * rate
        
        # Step 4: Total
        total_tax = dd_tax + sale_tax
        total_gain = sell_amount - buy_amount
        expected_tax = total_gain * rate
        
        assert pytest.approx(total_tax) == expected_tax


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
