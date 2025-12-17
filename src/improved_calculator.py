#!/usr/bin/env python3
"""
Irish Capital Gains Calculator

A comprehensive tool for calculating Irish capital gains tax, ETF exit tax,
and dividend income tax from trading transaction data.

Features:
- FIFO (First In, First Out) cost basis calculation
- Loss carry forward (indefinite for stocks)
- Multi-year processing with proper tax calculations
- ETF exit tax (41%) vs stock CGT (33%) classification
- Dividend income tax with withholding tax credits
- CSV export for tax filing
- Merger and corporate action handling

Author: Built for Irish tax compliance
License: Educational and personal use
"""

import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict, deque
import sys
import os
import argparse
import json
import re
from ticker_utils import add_missing_ticker_to_cache
from tax_calculations import (
    apply_cgt_with_loss_carry_forward,
    calculate_etf_exit_tax, 
    calculate_dividend_income_tax,
    format_currency_display,
    get_exemption_applied
)

class ImprovedCapitalGainsCalculator:
    def __init__(self):
        self.ticker_cache_file = 'data/ticker_cache.json'
        self.ticker_cache = self.load_ticker_cache()
    
    def load_ticker_cache(self):
        """Load ticker cache from JSON file"""
        if os.path.exists(self.ticker_cache_file):
            try:
                with open(self.ticker_cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_ticker_cache(self):
        """Save ticker cache to JSON file"""
        with open(self.ticker_cache_file, 'w') as f:
            json.dump(self.ticker_cache, f, indent=2)
    
    def get_ticker_info(self, ticker):
        """Get ticker info from cache, auto-add if missing"""
        if pd.isna(ticker) or ticker == '' or ticker is None:
            return None
        
        ticker_str = str(ticker).upper()
        
        # Handle string 'None' or 'NAN'
        if ticker_str in ['NONE', 'NAN']:
            return None
        
        # Check cache first
        if ticker_str in self.ticker_cache:
            return self.ticker_cache[ticker_str]
        
        # Auto-add missing ticker
        ticker_info = add_missing_ticker_to_cache(ticker_str, self.ticker_cache_file)
        self.ticker_cache[ticker_str] = ticker_info
        return ticker_info
    
    def normalize_ticker(self, ticker):
        """Normalize ticker to handle mergers"""
        if pd.isna(ticker) or ticker == '' or str(ticker).upper() == 'NAN':
            return None
        
        ticker = str(ticker).upper()
        ticker_info = self.get_ticker_info(ticker)
        
        if ticker_info is None:
            return None
        
        # If ticker was merged into another, use the new ticker
        if ticker_info.get('merged_into'):
            return ticker_info['merged_into']
        
        return ticker
    
    def get_conversion_ratio(self, ticker):
        """Get conversion ratio for merged tickers"""
        ticker_info = self.get_ticker_info(ticker)
        if ticker_info is None:
            raise ValueError(f"Ticker '{ticker}' not found in cache")
        return ticker_info.get('conversion_ratio', 1.0)
    
    def is_etf(self, ticker):
        """Determine if a ticker is an ETF"""
        ticker_info = self.get_ticker_info(ticker)
        if ticker_info is None:
            raise ValueError(f"Ticker '{ticker}' not found in cache")
        return ticker_info['type'] == 'etf'
    
    def is_active(self, ticker):
        """Check if ticker is active"""
        ticker_info = self.get_ticker_info(ticker)
        if ticker_info is None:
            raise ValueError(f"Ticker '{ticker}' not found in cache")
        return ticker_info.get('active', True)
    
    def has_withholding_tax_deducted(self, ticker):
        """Check if withholding tax is already deducted by broker"""
        return self.get_ticker_info(ticker).get('withholding_tax_deducted', False)
    
    def get_domicile(self, ticker):
        """Get domicile of ticker"""
        ticker_info = self.get_ticker_info(ticker)
        if ticker_info is None:
            raise ValueError(f"Ticker '{ticker}' not found in cache")
        return ticker_info.get('domicile', 'Unknown')
    
    def calculate_deemed_disposal_liability(self, ticker, buy_transactions, current_date=None):
        """Calculate deemed disposal tax liability for ETFs (8-year rule)"""
        if not self.is_etf(ticker):
            return 0, 0, []
        
        if current_date is None:
            current_date = datetime.now()
        
        deemed_disposals = []
        total_taxable_gain = 0
        
        for _, tx in buy_transactions.iterrows():
            purchase_date = tx['Date']
            # Handle timezone-aware vs naive datetime objects
            if hasattr(purchase_date, 'tz_localize'):
                purchase_date = purchase_date.tz_localize(None) if purchase_date.tz is not None else purchase_date
            if hasattr(current_date, 'tz_localize'):
                current_date = current_date.tz_localize(None) if current_date.tz is not None else current_date
            years_held = (current_date - purchase_date).days / 365.25
            
            if years_held >= 8:
                # This holding triggers deemed disposal
                # For simplicity, assume current value = cost basis + some gain
                # In practice, you'd need current market value
                cost_basis = tx['PricePerShareEUR'] * tx['Quantity']
                # Placeholder: assume 20% gain for deemed disposal calculation
                estimated_current_value = cost_basis * 1.2
                taxable_gain = estimated_current_value - cost_basis
                
                deemed_disposals.append({
                    'ticker': ticker,
                    'purchase_date': purchase_date,
                    'years_held': years_held,
                    'cost_basis': cost_basis,
                    'estimated_value': estimated_current_value,
                    'taxable_gain': taxable_gain
                })
                total_taxable_gain += taxable_gain
        
        tax_liability = total_taxable_gain * 0.41  # 41% exit tax
        return total_taxable_gain, tax_liability, deemed_disposals
    
    def classify_transaction_type(self, type_str):
        """Classify transaction types"""
        if pd.isna(type_str):
            return 'ignore'
        
        type_str = str(type_str).upper()
        
        if 'BUY' in type_str:
            return 'buy'
        elif 'SELL' in type_str:
            return 'sell'
        elif 'DIVIDEND' in type_str:
            return 'dividend'
        elif 'MERGER' in type_str:
            if 'STOCK' in type_str:
                return 'merger_stock'
            elif 'CASH' in type_str:
                return 'merger_cash'
            else:
                return 'merger'
        elif 'TRANSFER' in type_str and 'REVOLUT TRADING LTD TO REVOLUT SECURITIES EUROPE UAB' in type_str:
            return 'transfer_broker'
        elif 'TRANSFER' in type_str:
            return 'ignore'
        elif any(ignore_type in type_str for ignore_type in [
            'TRANSFER', 'CASH TOP-UP', 'CASH WITHDRAWAL', 'CUSTODY FEE'
        ]):
            return 'ignore'
        else:
            return 'ignore'
    
    def parse_amount(self, amount_str):
        """Parse amount string to float"""
        if pd.isna(amount_str):
            return 0.0
        
        # Extract numeric value using regex
        import re
        amount_str = str(amount_str)
        
        # Remove various currency symbols and encodings
        # Handle different Euro symbol encodings
        amount_str = re.sub(r'[€$£¥₹]', '', amount_str)  # Standard currency symbols
        amount_str = re.sub(r'â[^\d]*¬', '', amount_str)  # Various Euro encodings
        amount_str = re.sub(r'_x[0-9A-Fa-f]+_', '', amount_str)  # Hex encodings
        
        # Find all numeric patterns (including decimals and negative numbers)
        matches = re.findall(r'-?\d+\.?\d*', amount_str)
        
        if matches:
            try:
                return float(matches[0])
            except ValueError:
                return 0.0
        
        return 0.0
    
    def convert_to_eur(self, amount, currency, fx_rate):
        """Convert amount to EUR using FX rate"""
        if currency == 'EUR':
            return amount
        elif currency == 'USD' and not pd.isna(fx_rate) and fx_rate > 0:
            return amount / fx_rate
        else:
            raise ValueError(f"Invalid FX rate for {currency}: {fx_rate}")
    
    def get_weighted_fx_rate(self, ticker_transactions):
        """Calculate weighted average FX rate from transactions"""
        total_amount_original = 0
        total_amount_eur = 0
        
        for _, tx in ticker_transactions.iterrows():
            if tx['TransactionType'] in ['buy', 'sell'] and tx['Currency'] != 'EUR':
                fx_rate = tx['FX Rate']
                if not pd.isna(fx_rate) and fx_rate > 0:
                    amount_eur = tx['TotalAmountEUR']
                    amount_original = amount_eur * fx_rate
                    total_amount_original += amount_original
                    total_amount_eur += amount_eur
        
        if total_amount_eur > 0:
            return total_amount_original / total_amount_eur
        # No fallback - require actual FX rates
        raise ValueError(f"No valid FX rates found for ticker transactions")
    
    def process_transactions(self, df, store_transactions=False):
        """Process transactions and calculate realized/unrealized gains"""
        df = df.copy()
        df['Date'] = pd.to_datetime(df['Date'], format='mixed')
        df['Year'] = df['Date'].dt.year
        df['TransactionType'] = df['Type'].apply(self.classify_transaction_type)
        # Identify tickers that had merger transactions
        merger_tickers = set()
        for _, row in df.iterrows():
            if row['TransactionType'] in ['merger_stock', 'merger_cash', 'merger']:
                ticker = self.normalize_ticker(row['Ticker'])
                if ticker:
                    merger_tickers.add(ticker)
        
        # Classify broker transfers based on whether ticker had mergers
        def classify_transfer(row):
            if row['TransactionType'] == 'transfer_broker':
                ticker = self.normalize_ticker(row['Ticker'])
                if ticker in merger_tickers:
                    return 'transfer_merger'
                else:
                    return 'ignore'
            return row['TransactionType']
        
        df['TransactionType'] = df.apply(classify_transfer, axis=1)
        
        # Only normalize tickers for relevant transactions
        df['NormalizedTicker'] = df.apply(
            lambda row: self.normalize_ticker(row['Ticker']) if row['TransactionType'] in ['buy', 'sell', 'dividend', 'merger_stock', 'merger_cash', 'merger', 'transfer_merger'] else None, 
            axis=1
        )
        # Only apply ETF/active checks to valid tickers
        df['IsETF'] = df['NormalizedTicker'].apply(lambda x: self.is_etf(x) if x is not None and pd.notna(x) else False)
        df['IsActive'] = df['NormalizedTicker'].apply(lambda x: self.is_active(x) if x is not None and pd.notna(x) else True)
        df['TotalAmountFloat'] = df['Total Amount'].apply(self.parse_amount)
        df['PricePerShareFloat'] = df['Price per share'].apply(self.parse_amount)
        
        df['TotalAmountEUR'] = df.apply(
            lambda row: self.convert_to_eur(
                row['TotalAmountFloat'], 
                row['Currency'], 
                row['FX Rate']
            ), axis=1
        )
        
        df['PricePerShareEUR'] = df.apply(
            lambda row: self.convert_to_eur(
                row['PricePerShareFloat'], 
                row['Currency'], 
                row['FX Rate']
            ), axis=1
        )
        
        # Calculate fees (difference between total and price × quantity)
        df['FeesEUR'] = df.apply(
            lambda row: row['TotalAmountEUR'] - (row['PricePerShareEUR'] * row['Quantity']) 
            if row['TransactionType'] in ['buy', 'sell'] and row['Quantity'] > 0 else 0, axis=1
        )
        
        relevant_df = df[df['TransactionType'].isin(['buy', 'sell', 'dividend', 'merger_stock', 'merger_cash', 'merger', 'transfer_merger'])].copy()
        # Filter out rows with None/NaN normalized tickers
        relevant_df = relevant_df[relevant_df['NormalizedTicker'].notna()]
        relevant_df = relevant_df[relevant_df['NormalizedTicker'] != 'None']
        
        # Store transaction history if requested
        if store_transactions:
            self.transaction_history = df  # Store full df with all calculated fields
        
        results = {
            'summary': {
                'stocks': {
                    'realized_gains': defaultdict(float), 
                    'unrealized_gains': defaultdict(float), 
                    'dividends': defaultdict(float),
                    'dividends_irish': defaultdict(float),
                    'dividends_foreign': defaultdict(float)
                },
                'etfs': {
                    'realized_gains': defaultdict(float), 
                    'unrealized_gains': defaultdict(float), 
                    'dividends': defaultdict(float),
                    'dividends_irish': defaultdict(float),
                    'dividends_foreign': defaultdict(float),
                    'deemed_disposal_gains': defaultdict(float)
                }
            },
            'ticker_detail': defaultdict(lambda: {
                'asset_type': '',
                'realized_gains': defaultdict(float),
                'unrealized_gains': defaultdict(float),
                'dividends': defaultdict(float),
                'dividends_irish': defaultdict(float),
                'dividends_foreign': defaultdict(float),
                'current_holdings': 0,
                'avg_cost_basis': 0,
                'deemed_disposal_liability': 0,
                'buy_transactions': []
            })
        }
        
        # Process valid tickers
        for ticker in relevant_df['NormalizedTicker'].unique():
            ticker_data = relevant_df[
                (relevant_df['NormalizedTicker'] == ticker) & 
                (relevant_df['NormalizedTicker'].notna())
            ].sort_values('Date')
            is_etf = self.is_etf(ticker)
            asset_type = 'etfs' if is_etf else 'stocks'
            
            results['ticker_detail'][ticker]['asset_type'] = asset_type
            
            buy_queue = deque()
            total_shares = 0
            total_cost = 0
            
            for _, transaction in ticker_data.iterrows():
                year = transaction['Year']
                trans_type = transaction['TransactionType']
                quantity = transaction['Quantity']
                amount_eur = transaction['TotalAmountEUR']
                
                if trans_type == 'dividend':
                    results['summary'][asset_type]['dividends'][year] += amount_eur
                    results['ticker_detail'][ticker]['dividends'][year] += amount_eur
                    
                    # Classify as Irish vs Foreign dividend
                    domicile = self.get_domicile(ticker)
                    if domicile == 'IE':
                        results['summary'][asset_type]['dividends_irish'][year] += amount_eur
                        results['ticker_detail'][ticker]['dividends_irish'][year] += amount_eur
                    else:
                        results['summary'][asset_type]['dividends_foreign'][year] += amount_eur
                        results['ticker_detail'][ticker]['dividends_foreign'][year] += amount_eur
                
                elif trans_type == 'buy':
                    # Use actual price per share, not total/quantity (which includes fees)
                    price_per_share_eur = transaction['PricePerShareEUR']
                    original_ticker = transaction['Ticker']
                    
                    # Apply conversion ratio if this is a merged ticker
                    conversion_ratio = self.get_conversion_ratio(original_ticker)
                    converted_quantity = quantity * conversion_ratio
                    converted_price = price_per_share_eur / conversion_ratio if conversion_ratio > 0 else price_per_share_eur
                    
                    buy_transaction = {
                        'quantity': converted_quantity,
                        'price_per_share_eur': converted_price,
                        'year': year
                    }
                    buy_queue.append(buy_transaction)
                    
                    # Store buy transactions for deemed disposal calculation
                    if is_etf:
                        results['ticker_detail'][ticker]['buy_transactions'].append(transaction)
                    
                    total_shares += converted_quantity
                    # Use actual share cost for cost basis (excluding fees)
                    share_cost = price_per_share_eur * quantity  # Use original values for cost
                    total_cost += share_cost
                
                elif trans_type == 'sell':
                    original_ticker = transaction['Ticker']
                    conversion_ratio = self.get_conversion_ratio(original_ticker)
                    converted_quantity = quantity * conversion_ratio
                    
                    remaining_to_sell = converted_quantity
                    total_cost_basis = 0
                    
                    while remaining_to_sell > 0 and buy_queue:
                        buy_transaction = buy_queue[0]
                        
                        if buy_transaction['quantity'] <= remaining_to_sell:
                            sold_quantity = buy_transaction['quantity']
                            cost_basis = sold_quantity * buy_transaction['price_per_share_eur']
                            total_cost_basis += cost_basis
                            remaining_to_sell -= sold_quantity
                            total_shares -= sold_quantity
                            total_cost -= cost_basis
                            buy_queue.popleft()
                        else:
                            sold_quantity = remaining_to_sell
                            cost_basis = sold_quantity * buy_transaction['price_per_share_eur']
                            total_cost_basis += cost_basis
                            buy_transaction['quantity'] -= sold_quantity
                            remaining_to_sell = 0
                            total_shares -= sold_quantity
                            total_cost -= cost_basis
                    
                    # Realized gain/loss (using actual share proceeds, not including fees)
                    share_proceeds = transaction['PricePerShareEUR'] * quantity  # Use original values
                    realized_gain = share_proceeds - total_cost_basis
                    results['summary'][asset_type]['realized_gains'][year] += realized_gain
                    results['ticker_detail'][ticker]['realized_gains'][year] += realized_gain
                
                elif trans_type in ['merger_stock', 'merger']:
                    # Handle merger transactions - these remove shares from holdings
                    if quantity < 0:  # Negative quantity means shares are being removed
                        original_ticker = transaction['Ticker']
                        shares_to_remove = abs(quantity)
                        
                        # Remove shares using FIFO
                        remaining_to_remove = shares_to_remove
                        while remaining_to_remove > 0 and buy_queue:
                            buy_transaction = buy_queue[0]
                            
                            if buy_transaction['quantity'] <= remaining_to_remove:
                                removed_quantity = buy_transaction['quantity']
                                cost_basis = removed_quantity * buy_transaction['price_per_share_eur']
                                remaining_to_remove -= removed_quantity
                                total_shares -= removed_quantity
                                total_cost -= cost_basis
                                buy_queue.popleft()
                            else:
                                removed_quantity = remaining_to_remove
                                cost_basis = removed_quantity * buy_transaction['price_per_share_eur']
                                buy_transaction['quantity'] -= removed_quantity
                                remaining_to_remove = 0
                                total_shares -= removed_quantity
                                total_cost -= cost_basis
                
                elif trans_type == 'merger_cash':
                    # Handle cash received from merger - treat as dividend income
                    if amount_eur > 0:
                        results['summary'][asset_type]['dividends'][year] += amount_eur
                        results['ticker_detail'][ticker]['dividends'][year] += amount_eur
                        
                        # Classify as foreign dividend (US domicile)
                        results['summary'][asset_type]['dividends_foreign'][year] += amount_eur
                        results['ticker_detail'][ticker]['dividends_foreign'][year] += amount_eur
                
                elif trans_type == 'transfer_merger':
                    # Handle transfer of shares from merger - treat as buy with zero cost basis
                    if quantity > 0:
                        buy_transaction = {
                            'quantity': quantity,
                            'price_per_share_eur': 0.0,  # Zero cost basis from merger
                            'year': year
                        }
                        buy_queue.append(buy_transaction)
                        
                        # Store buy transactions for deemed disposal calculation
                        if is_etf:
                            results['ticker_detail'][ticker]['buy_transactions'].append(transaction)
                        
                        total_shares += quantity
                        # No cost added since these shares came from merger at zero cost basis
            
            # Handle inactive stocks as losses
            if not self.is_active(ticker) and total_shares > 0:
                # Treat remaining holdings as a loss
                loss_amount = total_cost
                current_year = datetime.now().year
                results['summary'][asset_type]['realized_gains'][current_year] -= loss_amount
                results['ticker_detail'][ticker]['realized_gains'][current_year] -= loss_amount
                total_shares = 0
                total_cost = 0
            
            # Calculate deemed disposal liability for ETFs
            if is_etf and results['ticker_detail'][ticker]['buy_transactions']:
                buy_df = pd.DataFrame(results['ticker_detail'][ticker]['buy_transactions'])
                taxable_gain, tax_liability, _ = self.calculate_deemed_disposal_liability(ticker, buy_df)
                results['ticker_detail'][ticker]['deemed_disposal_liability'] = tax_liability
                if taxable_gain > 0:
                    current_year = datetime.now().year
                    results['summary']['etfs']['deemed_disposal_gains'][current_year] += taxable_gain
            
            # Store current holdings for unrealized calculation
            results['ticker_detail'][ticker]['current_holdings'] = total_shares
            
            # For unrealized holdings, show cost basis in original currency
            ticker_info = self.get_ticker_info(ticker)
            if ticker_info is None:
                raise ValueError(f"Ticker '{ticker}' not found in cache")
            original_currency = ticker_info.get('currency', 'USD')
            
            if original_currency == 'EUR':
                results['ticker_detail'][ticker]['avg_cost_basis'] = total_cost / total_shares if total_shares > 0 else 0
                results['ticker_detail'][ticker]['currency'] = 'EUR'
            else:
                # Convert back to original currency for display
                # Calculate average cost basis in original currency
                if total_shares > 0:
                    # Get weighted average FX rate from buy transactions
                    total_original_cost = 0
                    for buy_tx in buy_queue:
                        # Find corresponding original transaction to get FX rate
                        original_cost = buy_tx['price_per_share_eur'] * buy_tx['quantity']
                        total_original_cost += original_cost
                    
                    # Calculate weighted average FX rate from this ticker's transactions
                    try:
                        avg_fx_rate = self.get_weighted_fx_rate(ticker_data)
                        results['ticker_detail'][ticker]['avg_cost_basis'] = (total_cost * avg_fx_rate) / total_shares
                    except ValueError:
                        # If no valid FX rates, show cost in EUR
                        results['ticker_detail'][ticker]['avg_cost_basis'] = total_cost / total_shares
                        results['ticker_detail'][ticker]['currency'] = 'EUR'
                else:
                    results['ticker_detail'][ticker]['avg_cost_basis'] = 0
                results['ticker_detail'][ticker]['currency'] = original_currency
        
        return results
    
    def process_transactions_with_detail(self, df, target_ticker=None):
        """Process transactions with detailed tracking for specific ticker"""
        results = self.process_transactions(df, store_transactions=True)
        
        if target_ticker and hasattr(self, 'transaction_history'):
            # Add transaction details for the target ticker
            normalized_target = self.normalize_ticker(target_ticker)
            ticker_transactions = self.transaction_history[
                self.transaction_history['NormalizedTicker'] == normalized_target
            ].copy()
            
            if not ticker_transactions.empty:
                results['ticker_detail'][normalized_target]['transactions'] = ticker_transactions
        
        return results
    
    def calculate_dividend_taxes(self, results, margin_rate):
        """Calculate dividend taxation breakdown for Irish tax compliance"""
        dividend_tax_summary = {}
        
        all_years = set()
        for asset_type in results['summary'].values():
            all_years.update(asset_type['dividends'].keys())
        
        for year in sorted(all_years):
            # Stock dividends (subject to income tax)
            stock_dividends_irish = results['summary']['stocks']['dividends_irish'][year]
            stock_dividends_foreign = results['summary']['stocks']['dividends_foreign'][year]
            
            # ETF dividends are subject to 41% exit tax, NOT income tax at marginal rates
            # Only stock dividends are subject to income tax at marginal rates
            
            # Total dividend income (STOCKS ONLY - ETFs handled in exit tax section)
            total_irish_dividends = stock_dividends_irish
            total_foreign_dividends = stock_dividends_foreign
            total_dividends = total_irish_dividends + total_foreign_dividends
            
            if total_dividends > 0:
                # Irish dividends: 25% DWT provides tax credit
                irish_dwt_credit = total_irish_dividends * 0.25
                
                # Foreign dividends: 15% withholding provides tax credit  
                foreign_withholding_credit = total_foreign_dividends * 0.15
                
                # Total gross dividend income (what you report)
                gross_dividend_income = total_dividends
                
                # Income tax liability at marginal rate
                income_tax_due = gross_dividend_income * (margin_rate / 100)
                
                # Total tax credits available
                total_credits = irish_dwt_credit + foreign_withholding_credit
                
                # Net additional tax due (or refund if negative)
                net_tax_due = max(0, income_tax_due - total_credits)
                refund_due = max(0, total_credits - income_tax_due)
                
                dividend_tax_summary[year] = {
                    'gross_dividend_income': gross_dividend_income,
                    'irish_dividends': total_irish_dividends,
                    'foreign_dividends': total_foreign_dividends,
                    'irish_dwt_credit': irish_dwt_credit,
                    'foreign_withholding_credit': foreign_withholding_credit,
                    'total_credits': total_credits,
                    'income_tax_due': income_tax_due,
                    'net_tax_due': net_tax_due,
                    'refund_due': refund_due,
                    'margin_rate': margin_rate
                }
        
        return dividend_tax_summary

    def generate_report(self, results, margin_rate=40):
        """Generate detailed report with Irish tax compliance"""
        print("=" * 80)
        print("IRISH TAX COMPLIANCE REPORT - CAPITAL GAINS & EXIT TAX")
        print("=" * 80)
        
        all_years = set()
        for asset_type in results['summary'].values():
            all_years.update(asset_type['realized_gains'].keys())
            all_years.update(asset_type['dividends'].keys())
        
        # Calculate dividend taxes once for all years
        dividend_taxes = self.calculate_dividend_taxes(results, margin_rate)
        
        # Display note about margin rate if there are any dividends
        if dividend_taxes:
            print(f"\nNote: Marginal tax rate used: {margin_rate}% (use --margin-rate to change)\n")
        
        # Calculate carry forward losses for stocks (CGT only, not ETFs)
        accumulated_losses = 0  # Track losses carried forward from previous years
        
        for year in sorted(all_years):
            print(f"{'='*20} FINANCIAL YEAR {year} {'='*20}")
            
            # Summary with Irish tax calculations
            stock_realized = results['summary']['stocks']['realized_gains'][year]
            stock_dividends = results['summary']['stocks']['dividends'][year]
            stock_dividends_irish = results['summary']['stocks']['dividends_irish'][year]
            stock_dividends_foreign = results['summary']['stocks']['dividends_foreign'][year]
            
            etf_realized = results['summary']['etfs']['realized_gains'][year]
            etf_dividends = results['summary']['etfs']['dividends'][year]
            etf_deemed = results['summary']['etfs']['deemed_disposal_gains'][year]
            
            # Apply Irish tax calculations using modularized functions
            cgt_exemption = 1270  # €1,270 annual exemption
            
            # Calculate CGT with loss carry forward
            stock_taxable_gains, stock_cgt_liability, carry_forward_used, accumulated_losses = \
                apply_cgt_with_loss_carry_forward(stock_realized, accumulated_losses, cgt_exemption)
            
            # Calculate ETF exit tax
            etf_total_taxable, etf_exit_tax_liability = \
                calculate_etf_exit_tax(etf_realized, etf_dividends, etf_deemed)
            
            print(f"\nIRISH TAX SUMMARY FOR {year}:")
            print(f"\n--- STOCKS (Capital Gains Tax @ 33%) ---")
            print(f"  Realized Gains (Gross):     €{stock_realized:8.2f}")
            print(f"  Less: Annual Exemption:     €{min(stock_realized, cgt_exemption) if stock_realized > 0 else 0:8.2f}")
            if carry_forward_used > 0:
                print(f"  Less: Carry Forward Loss:   €{carry_forward_used:8.2f}")
            print(f"  Taxable Gains (Net):        €{stock_taxable_gains:8.2f}")
            print(f"  CGT Liability (33%):        €{stock_cgt_liability:8.2f}")
            if accumulated_losses > 0:
                print(f"  Losses Carried Forward:     €{accumulated_losses:8.2f}")
            print(f"  Dividends (Irish):          €{stock_dividends_irish:8.2f}")
            print(f"  Dividends (Foreign):        €{stock_dividends_foreign:8.2f}")
            
            print(f"\n--- ETFs (Exit Tax @ 41%) ---")
            print(f"  Realized Gains:             €{etf_realized:8.2f}")
            print(f"  Dividends:                  €{etf_dividends:8.2f}")
            print(f"  Deemed Disposal Gains:      €{etf_deemed:8.2f}")
            print(f"  Total Taxable (ETF):        €{etf_realized + etf_dividends + etf_deemed:8.2f}")
            print(f"  Exit Tax Liability (41%):   €{etf_exit_tax_liability:8.2f}")
            
            print(f"\n--- TOTAL TAX LIABILITY ---")
            print(f"  Total Tax Due:              €{stock_cgt_liability + etf_exit_tax_liability:8.2f}")
            
            # Dividend taxation breakdown for this year
            if year in dividend_taxes:
                div_tax = dividend_taxes[year]
                print(f"\n--- DIVIDEND INCOME TAX FOR {year} ---")
                print(f"  Gross Dividend Income:      €{div_tax['gross_dividend_income']:8.2f}")
                print(f"    Irish Dividends:          €{div_tax['irish_dividends']:8.2f}")
                print(f"    Foreign Dividends:        €{div_tax['foreign_dividends']:8.2f}")
                print(f"  Income Tax Due ({margin_rate}%):       €{div_tax['income_tax_due']:8.2f}")
                print(f"  Tax Credits Available:      €{div_tax['total_credits']:8.2f}")
                print(f"    Irish DWT Credit (25%):   €{div_tax['irish_dwt_credit']:8.2f}")
                print(f"    Foreign Withholding (15%):€{div_tax['foreign_withholding_credit']:8.2f}")
                
                if div_tax['net_tax_due'] > 0:
                    print(f"  Additional Tax Due:         €{div_tax['net_tax_due']:8.2f}")
                elif div_tax['refund_due'] > 0:
                    print(f"  Tax Refund Due:             €{div_tax['refund_due']:8.2f}")
                else:
                    print(f"  Net Tax Due:                €{0.00:8.2f}")
            
            # Ticker breakdown for this year
            print(f"\nREALIZED GAINS BREAKDOWN FOR {year}:")
            print("-" * 60)
            
            stocks_with_activity = []
            etfs_with_activity = []
            
            for ticker, ticker_data in results['ticker_detail'].items():
                year_realized = ticker_data['realized_gains'][year]
                year_dividends = ticker_data['dividends'][year]
                year_dividends_irish = ticker_data.get('dividends_irish', defaultdict(float))[year]
                year_dividends_foreign = ticker_data.get('dividends_foreign', defaultdict(float))[year]
                
                if year_realized != 0 or year_dividends != 0:
                    ticker_info = {
                        'ticker': ticker,
                        'realized': year_realized,
                        'dividends': year_dividends,
                        'dividends_irish': year_dividends_irish,
                        'dividends_foreign': year_dividends_foreign,
                        'asset_type': ticker_data['asset_type']
                    }
                    
                    if ticker_data['asset_type'] == 'stocks':
                        stocks_with_activity.append(ticker_info)
                    else:
                        etfs_with_activity.append(ticker_info)
            
            if stocks_with_activity:
                print("\nSTOCKS:")
                for ticker_info in sorted(stocks_with_activity, key=lambda x: x['realized'], reverse=True):
                    div_detail = f" (IE: €{ticker_info['dividends_irish']:.2f}, Foreign: €{ticker_info['dividends_foreign']:.2f})" if ticker_info['dividends'] > 0 else ""
                    print(f"  {ticker_info['ticker']:8} | Realized: €{ticker_info['realized']:8.2f} | Dividends: €{ticker_info['dividends']:6.2f}{div_detail}")
            
            if etfs_with_activity:
                print("\nETFs:")
                for ticker_info in sorted(etfs_with_activity, key=lambda x: x['realized'], reverse=True):
                    print(f"  {ticker_info['ticker']:8} | Realized: €{ticker_info['realized']:8.2f} | Dividends: €{ticker_info['dividends']:6.2f} | Exit Tax: €{(ticker_info['realized'] + ticker_info['dividends']) * 0.41:.2f}")
            
            if not stocks_with_activity and not etfs_with_activity:
                print("No trading activity for this year.")
            
            print()  # Add blank line between years
        
        # Current holdings with tax implications
        print(f"\n{'='*20} CURRENT HOLDINGS & TAX IMPLICATIONS {'='*20}")
        current_stocks = []
        current_etfs = []
        total_deemed_disposal_liability = 0
        
        for ticker, ticker_data in results['ticker_detail'].items():
            if ticker_data['current_holdings'] > 0:
                holding_info = {
                    'ticker': ticker,
                    'shares': ticker_data['current_holdings'],
                    'avg_cost': ticker_data['avg_cost_basis'],
                    'asset_type': ticker_data['asset_type'],
                    'deemed_liability': ticker_data.get('deemed_disposal_liability', 0)
                }
                
                if ticker_data['asset_type'] == 'stocks':
                    current_stocks.append(holding_info)
                else:
                    current_etfs.append(holding_info)
                    total_deemed_disposal_liability += holding_info['deemed_liability']
        
        if current_stocks:
            print("\nCURRENT STOCK HOLDINGS (Subject to CGT @ 33%):")
            for holding in current_stocks:
                currency_symbol = '€' if results['ticker_detail'][holding['ticker']].get('currency', 'EUR') == 'EUR' else '$'
                print(f"  {holding['ticker']:8} | Shares: {holding['shares']:8.2f} | Avg Cost: {currency_symbol}{holding['avg_cost']:6.2f}")
        
        if current_etfs:
            print("\nCURRENT ETF HOLDINGS (Subject to Exit Tax @ 41%):")
            for holding in current_etfs:
                currency_symbol = '€' if results['ticker_detail'][holding['ticker']].get('currency', 'EUR') == 'EUR' else '$'
                deemed_status = f" | Deemed Liability: €{holding['deemed_liability']:.2f}" if holding['deemed_liability'] > 0 else ""
                print(f"  {holding['ticker']:8} | Shares: {holding['shares']:8.2f} | Avg Cost: {currency_symbol}{holding['avg_cost']:6.2f}{deemed_status}")
        
        if total_deemed_disposal_liability > 0:
            print(f"\n--- DEEMED DISPOSAL LIABILITY (8-Year Rule) ---")
            print(f"  Total Deemed Disposal Tax Due: €{total_deemed_disposal_liability:.2f}")
            print(f"  Note: This applies to ETF holdings over 8 years old")
    
    def export_to_csv(self, results, base_filename="irish_tax_report"):
        """Export Irish tax report to CSV"""
        summary_rows = []
        all_years = set()
        for asset_type in results['summary'].values():
            all_years.update(asset_type['realized_gains'].keys())
            all_years.update(asset_type['dividends'].keys())
            if 'deemed_disposal_gains' in asset_type:
                all_years.update(asset_type['deemed_disposal_gains'].keys())
        
        cgt_exemption = 1270
        accumulated_losses = 0  # Track carry forward losses for CSV
        
        for year in sorted(all_years):
            # Stock calculations with carry forward losses
            stock_realized = results['summary']['stocks']['realized_gains'][year]
            stock_dividends = results['summary']['stocks']['dividends'][year]
            stock_dividends_irish = results['summary']['stocks']['dividends_irish'][year]
            stock_dividends_foreign = results['summary']['stocks']['dividends_foreign'][year]
            
            # Apply CGT calculation with carry forward losses (same as in report)
            after_exemption = stock_realized - min(stock_realized, cgt_exemption) if stock_realized > 0 else stock_realized
            
            carry_forward_used = 0
            if after_exemption > 0 and accumulated_losses > 0:
                carry_forward_used = min(after_exemption, accumulated_losses)
                accumulated_losses -= carry_forward_used
                after_exemption -= carry_forward_used
            
            stock_taxable = max(0, after_exemption)
            stock_cgt_liability = stock_taxable * 0.33
            
            if after_exemption < 0:
                accumulated_losses += abs(after_exemption)
            
            # ETF calculations
            etf_realized = results['summary']['etfs']['realized_gains'][year]
            etf_dividends = results['summary']['etfs']['dividends'][year]
            etf_deemed = results['summary']['etfs']['deemed_disposal_gains'][year]
            etf_total_taxable = etf_realized + etf_dividends + etf_deemed
            etf_exit_tax_liability = etf_total_taxable * 0.41
            
            summary_rows.extend([
                {
                    'Year': year,
                    'Asset_Type': 'Stocks',
                    'Realized_Gains_Gross_EUR': round(stock_realized, 2),
                    'CGT_Exemption_Applied_EUR': round(min(stock_realized, cgt_exemption) if stock_realized > 0 else 0, 2),
                    'Carry_Forward_Loss_Used_EUR': round(carry_forward_used, 2),
                    'Taxable_Gains_Net_EUR': round(stock_taxable, 2),
                    'Tax_Rate': '33%',
                    'Tax_Liability_EUR': round(stock_cgt_liability, 2),
                    'Losses_Carried_Forward_EUR': round(accumulated_losses, 2),
                    'Dividends_Irish_EUR': round(stock_dividends_irish, 2),
                    'Dividends_Foreign_EUR': round(stock_dividends_foreign, 2),
                    'Total_Dividends_EUR': round(stock_dividends, 2)
                },
                {
                    'Year': year,
                    'Asset_Type': 'ETFs',
                    'Realized_Gains_EUR': round(etf_realized, 2),
                    'Dividends_EUR': round(etf_dividends, 2),
                    'Deemed_Disposal_Gains_EUR': round(etf_deemed, 2),
                    'Total_Taxable_EUR': round(etf_total_taxable, 2),
                    'Tax_Rate': '41%',
                    'Exit_Tax_Liability_EUR': round(etf_exit_tax_liability, 2)
                }
            ])
        
        summary_df = pd.DataFrame(summary_rows)
        summary_filename = f"{base_filename}_tax_summary.csv"
        summary_df.to_csv(summary_filename, index=False)
        print(f"\nIrish tax summary exported to: {summary_filename}")
        
        # Ticker-level CSV
        ticker_rows = []
        for ticker, ticker_data in results['ticker_detail'].items():
            all_ticker_years = set()
            all_ticker_years.update(ticker_data['realized_gains'].keys())
            all_ticker_years.update(ticker_data['dividends'].keys())
            if 'dividends_irish' in ticker_data:
                all_ticker_years.update(ticker_data['dividends_irish'].keys())
            if 'dividends_foreign' in ticker_data:
                all_ticker_years.update(ticker_data['dividends_foreign'].keys())
            
            for year in all_ticker_years:
                realized = ticker_data['realized_gains'][year]
                dividends = ticker_data['dividends'][year]
                dividends_irish = ticker_data.get('dividends_irish', {}).get(year, 0)
                dividends_foreign = ticker_data.get('dividends_foreign', {}).get(year, 0)
                
                if realized != 0 or dividends != 0:
                    ticker_rows.append({
                        'Year': year,
                        'Ticker': ticker,
                        'Asset_Type': ticker_data['asset_type'].title(),
                        'Realized_Gains_EUR': round(realized, 2),
                        'Dividends_EUR': round(dividends, 2),
                        'Dividends_Irish_EUR': round(dividends_irish, 2),
                        'Dividends_Foreign_EUR': round(dividends_foreign, 2)
                    })
        
        ticker_df = pd.DataFrame(ticker_rows)
        ticker_filename = f"{base_filename}_by_ticker.csv"
        if ticker_df is not None and not ticker_df.empty:
            ticker_df.to_csv(ticker_filename, index=False)
            print(f"Ticker-level exported to: {ticker_filename}")
        
        # Export deemed disposal report
        deemed_rows = []
        for ticker, ticker_data in results['ticker_detail'].items():
            if ticker_data.get('deemed_disposal_liability', 0) > 0:
                deemed_rows.append({
                    'Ticker': ticker,
                    'Asset_Type': 'ETF',
                    'Deemed_Disposal_Tax_Liability_EUR': ticker_data['deemed_disposal_liability'],
                    'Note': '8-year deemed disposal rule applied'
                })
        
        if deemed_rows:
            deemed_df = pd.DataFrame(deemed_rows)
            deemed_filename = f"{base_filename}_deemed_disposal.csv"
            deemed_df.to_csv(deemed_filename, index=False)
            print(f"Deemed disposal report exported to: {deemed_filename}")
    
    def process_file(self, file_path):
        """Process single Excel or CSV file"""
        try:
            print(f"Processing file: {file_path}")
            
            # Determine file type and read accordingly
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            required_columns = ['Date', 'Ticker', 'Type', 'Quantity', 'Price per share', 'Total Amount', 'Currency', 'FX Rate']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"Error: Missing required columns: {missing_columns}")
                return None
            
            result = self.process_transactions(df)
            # Save cache after processing
            self.save_ticker_cache()
            return result
            
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return None

    def process_multiple_files(self, file_paths):
        """Process multiple Excel/CSV files with proper FIFO across all files"""
        # Combine all transactions from all files first
        all_transactions = []
        
        for file_path in file_paths:
            try:
                print(f"Loading file: {file_path}")
                
                # Determine file type and read accordingly
                if file_path.lower().endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                
                required_columns = ['Date', 'Ticker', 'Type', 'Quantity', 'Price per share', 'Total Amount', 'Currency', 'FX Rate']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    print(f"Error: Missing required columns in {file_path}: {missing_columns}")
                    continue
                
                all_transactions.append(df)
                
            except Exception as e:
                print(f"Error loading file {file_path}: {e}")
                continue
        
        if not all_transactions:
            return None
        
        # Combine all dataframes and sort by date for proper FIFO
        combined_df = pd.concat(all_transactions, ignore_index=True)
        combined_df = combined_df.sort_values('Date')
        
        # Process the combined transactions with proper FIFO
        result = self.process_transactions(combined_df)
        # Save cache after processing
        self.save_ticker_cache()
        return result

    def generate_ticker_detail_report(self, results, ticker):
        """Generate detailed report for a specific ticker"""
        print("=" * 80)
        print(f"TICKER DETAIL REPORT: {ticker}")
        print("=" * 80)
        
        if ticker not in results['ticker_detail']:
            print(f"No transactions found for ticker: {ticker}")
            return
        
        ticker_data = results['ticker_detail'][ticker]
        asset_type = ticker_data['asset_type']
        
        print(f"\nTicker: {ticker}")
        print(f"Type: {asset_type.upper()}")
        print(f"Current Holdings: {ticker_data['current_holdings']:.2f} shares")
        currency = ticker_data.get('currency', 'EUR')
        currency_symbol = '€' if currency == 'EUR' else '$'
        print(f"Average Cost Basis: {currency_symbol}{ticker_data['avg_cost_basis']:.2f} {currency}")
        
        # Show yearly breakdown
        all_years = set()
        all_years.update(ticker_data['realized_gains'].keys())
        all_years.update(ticker_data['dividends'].keys())
        
        if all_years:
            print(f"\nYEARLY BREAKDOWN:")
            print("-" * 50)
            for year in sorted(all_years):
                realized = ticker_data['realized_gains'][year]
                dividends = ticker_data['dividends'][year]
                if realized != 0 or dividends != 0:
                    print(f"  {year}: Realized Gains: €{realized:.2f}, Dividends: €{dividends:.2f}")
        
        # Show transaction details
        print(f"\nTRANSACTION DETAILS:")
        print("-" * 80)
        self.show_ticker_transactions(ticker)
    
    def show_ticker_transactions(self, target_ticker):
        """Show all transactions for a specific ticker (including merged tickers)"""
        if not hasattr(self, 'transaction_history'):
            print("Transaction history not available. Run with ticker detail mode.")
            return
        
        # Find all tickers that map to this target ticker (including merged ones)
        related_tickers = [target_ticker]
        for ticker, info in self.ticker_cache.items():
            if info.get('merged_into') == target_ticker:
                related_tickers.append(ticker)
        
        # Get transactions for all related tickers, excluding ignored transactions
        ticker_transactions = self.transaction_history[
            ((self.transaction_history['Ticker'].isin(related_tickers)) |
            (self.transaction_history['NormalizedTicker'] == target_ticker)) &
            (self.transaction_history['TransactionType'].isin(['buy', 'sell', 'dividend', 'transfer_merger', 'merger_stock', 'merger_cash']))
        ].copy().sort_values('Date')
        
        if ticker_transactions.empty:
            print(f"No transactions found for {target_ticker}")
            return
        
        # Determine the original currency for this ticker
        ticker_info = self.get_ticker_info(target_ticker)
        if ticker_info is None:
            raise ValueError(f"Ticker '{target_ticker}' not found in cache")
        original_currency = ticker_info.get('currency', 'USD')
        currency_symbol = '€' if original_currency == 'EUR' else '$'
        
        print(f"\nDate       | Ticker   | Type     | Quantity | Price {original_currency} | Fees {original_currency} | Total {original_currency}")
        print("-" * 80)
        
        for _, transaction in ticker_transactions.iterrows():
            original_ticker = transaction['Ticker']
            normalized_ticker = transaction['NormalizedTicker']
            date_str = transaction['Date'].strftime('%Y-%m-%d')
            trans_type = transaction['TransactionType'].upper()
            if trans_type == 'TRANSFER_MERGER':
                trans_type = 'TRANSFER'
            elif trans_type.startswith('MERGER'):
                trans_type = 'MERGER'
            quantity = transaction['Quantity']
            
            if trans_type == 'DIVIDEND':
                if original_currency == 'EUR':
                    price_orig = 0
                    fees_orig = 0
                    total_orig = transaction['TotalAmountEUR']
                else:
                    # Convert back to original currency
                    fx_rate = transaction.get('FX Rate', 1.08)
                    price_orig = 0
                    fees_orig = 0
                    total_orig = transaction['TotalAmountEUR'] * fx_rate if not pd.isna(fx_rate) else transaction['TotalAmountEUR']
            else:
                if original_currency == 'EUR':
                    price_orig = transaction.get('PricePerShareEUR', 0)
                    fees_orig = transaction.get('FeesEUR', 0)
                    total_orig = transaction['TotalAmountEUR']
                else:
                    # Convert back to original currency using FX rate
                    fx_rate = transaction.get('FX Rate', 1.08)
                    price_orig = transaction.get('PricePerShareFloat', 0)
                    fees_orig = transaction.get('FeesEUR', 0) * fx_rate if not pd.isna(fx_rate) else transaction.get('FeesEUR', 0)
                    total_orig = transaction.get('TotalAmountFloat', 0)
            
            ticker_display = original_ticker if original_ticker == normalized_ticker else f"{original_ticker}→{normalized_ticker}"
            
            print(f"{date_str} | {ticker_display:8} | {trans_type:8} | {quantity:8.2f} | {price_orig:9.2f} | {fees_orig:8.2f} | {total_orig:9.2f}")

def main():
    parser = argparse.ArgumentParser(description='Irish Capital Gains Calculator')
    parser.add_argument('files', nargs='+', help='Excel file(s) to process')
    parser.add_argument('--csv', action='store_true', help='Export results to CSV files')
    parser.add_argument('--ticker', type=str, help='Show detailed report for specific ticker')
    parser.add_argument('--margin-rate', type=int, choices=[20, 40, 45], default=40, 
                        help='Irish income tax marginal rate (20%%, 40%%, 45%%) - default: 40%%')
    
    args = parser.parse_args()
    
    # Validate files exist
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
    
    calculator = ImprovedCapitalGainsCalculator()
    
    if len(args.files) == 1:
        results = calculator.process_file(args.files[0])
    else:
        results = calculator.process_multiple_files(args.files)
    
    if results:
        if args.ticker:
            # For ticker detail mode, reprocess with transaction tracking
            if len(args.files) == 1:
                file_path = args.files[0]
                if file_path.lower().endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                results = calculator.process_transactions_with_detail(df, args.ticker)
            else:
                # Combine files for ticker detail
                all_transactions = []
                for file_path in args.files:
                    if file_path.lower().endswith('.csv'):
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path)
                    all_transactions.append(df)
                combined_df = pd.concat(all_transactions, ignore_index=True).sort_values('Date')
                results = calculator.process_transactions_with_detail(combined_df, args.ticker)
            
            # Normalize ticker for lookup
            normalized_ticker = calculator.normalize_ticker(args.ticker)
            calculator.generate_ticker_detail_report(results, normalized_ticker)
        else:
            calculator.generate_report(results, args.margin_rate)
        
        if args.csv:
            calculator.export_to_csv(results)
    else:
        print("No results to display.")

if __name__ == "__main__":
    main()
