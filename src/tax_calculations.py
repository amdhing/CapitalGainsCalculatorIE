"""
Irish tax calculation utilities for capital gains and dividend taxation.

This module contains the core tax calculation logic separated from the main calculator.
All calculations follow Irish Revenue guidelines.
"""

from collections import defaultdict


def apply_cgt_with_loss_carry_forward(stock_realized, accumulated_losses, cgt_exemption=1270):
    """
    Apply Irish Capital Gains Tax calculation with loss carry forward.
    
    Args:
        stock_realized (float): Gross realized gains for the year
        accumulated_losses (float): Losses carried forward from previous years
        cgt_exemption (float): Annual CGT exemption (€1,270 for individuals)
        
    Returns:
        tuple: (taxable_gains, cgt_liability, carry_forward_used, remaining_losses)
    """
    # Step 1: Apply annual exemption (only if positive gains)
    after_exemption = stock_realized - min(stock_realized, cgt_exemption) if stock_realized > 0 else stock_realized
    
    # Step 2: Apply carry forward losses
    carry_forward_used = 0
    if after_exemption > 0 and accumulated_losses > 0:
        carry_forward_used = min(after_exemption, accumulated_losses)
        accumulated_losses -= carry_forward_used
        after_exemption -= carry_forward_used
    
    # Step 3: Calculate final taxable gains and liability
    taxable_gains = max(0, after_exemption)
    cgt_liability = taxable_gains * 0.33  # 33% CGT rate
    
    # Step 4: If net loss after exemption, add to accumulated losses
    if after_exemption < 0:
        accumulated_losses += abs(after_exemption)
    
    return taxable_gains, cgt_liability, carry_forward_used, accumulated_losses


def calculate_etf_exit_tax(etf_realized, etf_dividends, etf_deemed):
    """
    Calculate Irish ETF exit tax (41% on all gains and dividends).
    
    Args:
        etf_realized (float): Realized gains from ETF sales
        etf_dividends (float): ETF dividend income
        etf_deemed (float): Deemed disposal gains (8-year rule)
        
    Returns:
        tuple: (total_taxable, exit_tax_liability)
    """
    total_taxable = etf_realized + etf_dividends + etf_deemed
    exit_tax_liability = total_taxable * 0.41  # 41% exit tax rate
    return total_taxable, exit_tax_liability


def calculate_dividend_income_tax(dividend_income, margin_rate, irish_dividends, foreign_dividends):
    """
    Calculate Irish dividend income tax with withholding tax credits.
    
    Args:
        dividend_income (float): Total dividend income (stocks only, not ETFs)
        margin_rate (int): Taxpayer's marginal income tax rate (20, 40, or 45)
        irish_dividends (float): Dividends from Irish companies
        foreign_dividends (float): Dividends from foreign companies
        
    Returns:
        dict: Complete dividend tax calculation breakdown
    """
    if dividend_income <= 0:
        return None
    
    # Tax credits available
    irish_dwt_credit = irish_dividends * 0.25  # 25% DWT on Irish dividends
    foreign_withholding_credit = foreign_dividends * 0.15  # 15% withholding on foreign dividends
    total_credits = irish_dwt_credit + foreign_withholding_credit
    
    # Income tax liability at marginal rate
    income_tax_due = dividend_income * (margin_rate / 100)
    
    # Net additional tax due (or refund if negative)
    net_tax_due = max(0, income_tax_due - total_credits)
    refund_due = max(0, total_credits - income_tax_due)
    
    return {
        'gross_dividend_income': dividend_income,
        'irish_dividends': irish_dividends,
        'foreign_dividends': foreign_dividends,
        'irish_dwt_credit': irish_dwt_credit,
        'foreign_withholding_credit': foreign_withholding_credit,
        'total_credits': total_credits,
        'income_tax_due': income_tax_due,
        'net_tax_due': net_tax_due,
        'refund_due': refund_due,
        'margin_rate': margin_rate
    }


def format_currency_display(amount, currency):
    """Format amount with appropriate currency symbol."""
    if currency == 'EUR':
        return f"€{amount:.2f}"
    elif currency == 'USD':
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"


def get_exemption_applied(realized_gains, exemption_amount):
    """Calculate how much of the annual exemption is actually applied."""
    return min(realized_gains, exemption_amount) if realized_gains > 0 else 0
