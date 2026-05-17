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


def get_etf_exit_tax_rate(year):
    """
    Get the Irish ETF exit tax rate for a given year.
    
    Until 31 Dec 2025: 41%
    From 1 Jan 2026 onward: 38%
    
    Args:
        year (int): The tax year
        
    Returns:
        float: The applicable exit tax rate
    """
    if year >= 2026:
        return 0.38  # 38% from 2026 onward
    return 0.41  # 41% up to and including 2025


def calculate_etf_exit_tax(etf_realized, etf_dividends, etf_deemed, year=2025):
    """
    Calculate Irish ETF exit tax with year-appropriate rate.
    
    Tax rate changes:
    - Until 31 Dec 2025: 41% on all gains and dividends
    - From 1 Jan 2026 onward: 38% on all gains and dividends
    
    NOTE: This function aggregates gains/dividends/deemed across all ETFs.
    For per-ticker calculation (where losses on one ETF cannot offset
    gains on another), use calculate_etf_exit_tax_per_ticker() instead.
    
    Args:
        etf_realized (float): Realized gains from ETF sales
        etf_dividends (float): ETF dividend income
        etf_deemed (float): Deemed disposal gains (8-year rule)
        year (int): The tax year to determine the applicable rate
        
    Returns:
        tuple: (total_taxable, exit_tax_liability)
    """
    total_taxable = etf_realized + etf_dividends + etf_deemed
    rate = get_etf_exit_tax_rate(year)
    exit_tax_liability = total_taxable * rate
    return total_taxable, exit_tax_liability


def calculate_etf_exit_tax_per_ticker(per_ticker_etf_data, year):
    """
    Calculate Irish ETF exit tax respecting that losses on one ETF
    cannot offset gains on another ETF.
    
    Irish tax rule: "Any losses on other ETFs are not available for offset.
    So if you make a loss of €5,000 on one ETF over 8 years – but make a
    gain of €10,000 on another over the same period – you will be liable
    for 38% tax on €10,000." - MoneyGuideIreland
    
    Each ETF ticker is taxed independently. Losses are forfeited (no loss
    carry forward or offset between different ETFs).
    
    Args:
        per_ticker_etf_data (dict): Dictionary mapping ticker -> dict with keys:
            'realized_gains' (float), 'dividends' (float), 'deemed_gains' (float)
        year (int): The tax year to determine the applicable rate
        
    Returns:
        dict: {
            'per_ticker': {ticker: {total_taxable, exit_tax}},
            'total_taxable': float,
            'total_exit_tax': float
        }
    """
    rate = get_etf_exit_tax_rate(year)
    per_ticker = {}
    total_taxable = 0.0
    total_exit_tax = 0.0
    
    for ticker, data in per_ticker_etf_data.items():
        realized = data.get('realized_gains', 0)
        dividends = data.get('dividends', 0)
        deemed = data.get('deemed_gains', 0)
        
        # Each ticker's taxable amount is the sum of its components
        ticker_taxable = realized + dividends + deemed
        
        # CRITICAL: Only positive amounts are taxable.
        # If a ticker has a net loss (negative total), the loss is forfeited.
        # It does NOT offset gains from other tickers.
        ticker_exit_tax = max(0, ticker_taxable) * rate
        
        per_ticker[ticker] = {
            'realized': realized,
            'dividends': dividends,
            'deemed': deemed,
            'total_taxable': ticker_taxable,
            'forfeited_loss': min(0, ticker_taxable),  # negative = loss, 0 = no loss
            'exit_tax': ticker_exit_tax
        }
        total_taxable += max(0, ticker_taxable)  # Only gains count toward total
        total_exit_tax += ticker_exit_tax
    
    return {
        'per_ticker': per_ticker,
        'total_taxable': total_taxable,
        'total_exit_tax': total_exit_tax,
        'rate': rate
    }


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
