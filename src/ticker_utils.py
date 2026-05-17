#!/usr/bin/env python3

import json
import os
import yfinance as yf


def add_missing_ticker_to_cache(ticker, cache_file='ticker_cache.json'):
    """Add missing ticker to cache with yfinance classification.
    
    Returns tuple of (ticker_data: dict | None, is_new: bool)
    If ticker can't be resolved, returns (None, False).
    """
    # Load existing cache
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        except:
            cache = {}
    else:
        cache = {}
    
    # Skip if ticker already exists
    if ticker in cache:
        return cache[ticker], False
    
    # Use yfinance to get ticker info
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
    except Exception:
        return None, False
    
    # Check if we got meaningful data
    quote_type = info.get('quoteType', '')
    if not quote_type:
        return None, False
    
    is_etf = quote_type.upper() == 'ETF'
    
    # Get currency and country info
    currency = info.get('currency', 'USD')
    country = info.get('country', 'United States')
    long_name = info.get('longName') or info.get('shortName') or ticker
    
    # Map country to domicile code
    domicile_map = {
        'Ireland': 'IE',
        'United States': 'US', 
        'Germany': 'DE',
        'United Kingdom': 'GB',
        'Netherlands': 'NL',
        'France': 'FR',
        'Switzerland': 'CH'
    }
    domicile = domicile_map.get(country, 'US')
    
    print(f"Added ticker '{ticker}' to cache as {'ETF' if is_etf else 'stock'} ({currency}, {country}) — {long_name}")
    
    # Add ticker with determined values
    cache[ticker] = {
        "type": "etf" if is_etf else "stock",
        "currency": currency,
        "active": True,
        "merged_into": None,
        "conversion_ratio": 1.0,
        "withholding_tax_deducted": False,
        "domicile": domicile,
        "long_name": long_name,
    }
    
    # Save updated cache
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)
    
    return cache[ticker], True
