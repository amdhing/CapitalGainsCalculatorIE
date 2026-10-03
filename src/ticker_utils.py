#!/usr/bin/env python3

import json
import os
import yfinance as yf


def _load_cache(cache_file):
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def add_missing_ticker_to_cache(ticker, cache_file='ticker_cache.json'):
    """Add missing ticker to cache with yfinance classification.
    
    Returns tuple of (ticker_data: dict | None, is_new: bool)
    If ticker can't be resolved, returns (None, False).
    """
    cache = _load_cache(cache_file)

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
    
    # Add ticker with determined values, including any known stock-split events.
    cache[ticker] = {
        "type": "etf" if is_etf else "stock",
        "currency": currency,
        "active": True,
        "merged_into": None,
        "conversion_ratio": 1.0,
        "withholding_tax_deducted": False,
        "domicile": domicile,
        "long_name": long_name,
        "splits": _fetch_splits(ticker),
    }
    
    # Save updated cache
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)
    
    return cache[ticker], True


def fetch_inr_per_eur():
    """Retrieve the current INR-per-EUR rate from yfinance (EURINR=X).

    Returns float (INR units per 1 EUR), or None if the fetch fails.
    Used as the default conversion rate for INR-denominated (Zerodha) files
    when the caller doesn't supply an explicit override.
    """
    try:
        hist = yf.Ticker("EURINR=X").history(period="5d")
        if hist is None or hist.empty:
            return None
        rate = float(hist["Close"].iloc[-1])
        return rate if rate > 0 else None
    except Exception:
        return None


def _fetch_splits(yf_symbol):
    """Fetch stock-split events for a ticker as JSON-serializable dicts.

    Returns a list of ``{"date": "YYYY-MM-DD", "ratio": float}`` (oldest first),
    or an empty list if none are available. yfinance exposes splits as a
    ``{Timestamp: ratio}`` Series (e.g. ratio 2.0 = a 2-for-1 split).
    """
    try:
        splits = yf.Ticker(yf_symbol).splits
    except Exception:
        return []
    if splits is None or len(splits) == 0:
        return []

    events = []
    for ts, ratio in splits.items():
        ratio_f = float(ratio)
        if ratio_f <= 0:
            continue
        events.append({"date": str(ts.date()), "ratio": ratio_f})
    return sorted(events, key=lambda e: e["date"])


def _fetch_india_ticker(yf_symbol):
    """Fetch yfinance .info for an Indian-listed symbol and validate it.

    Returns {'long_name': str} if the symbol is an India-domiciled, INR-traded
    equity; otherwise None. The bare Zerodha symbol is ambiguous on Yahoo
    (may 404, or resolve to a US ADR or a different company), so only a
    country == India and currency == INR match is accepted.
    """
    try:
        info = yf.Ticker(yf_symbol).info
    except Exception:
        return None
    if not info or not info.get('quoteType'):
        return None
    if info.get('country') != 'India' or info.get('currency') != 'INR':
        return None
    name = info.get('longName') or info.get('shortName') or yf_symbol
    return {'long_name': name}


def add_zerodha_ticker_to_cache(ticker, cache_file='ticker_cache.json'):
    """Classify a Zerodha (Indian NSE/BSE) ticker.

    Zerodha tradebook symbols are Indian equities. We append the exchange
    suffix and validate country==India / currency==INR, falling back from
    NSE (.NS) to BSE (.BO).

    Returns (ticker_data dict | None, is_new bool).
    """
    cache = _load_cache(cache_file)

    if ticker in cache:
        return cache[ticker], False

    for suffix in ('.NS', '.BO'):
        symbol = f'{ticker}{suffix}'
        india = _fetch_india_ticker(symbol)
        if india is None:
            continue

        data = {
            "type": "stock",
            "currency": "INR",
            "active": True,
            "merged_into": None,
            "conversion_ratio": 1.0,
            "withholding_tax_deducted": False,
            "domicile": "IN",
            "long_name": india["long_name"],
            "yfinance_ticker": symbol,
            "splits": _fetch_splits(symbol),
        }
        cache[ticker] = data
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
        print(f"Added Zerodha ticker '{ticker}' -> {symbol} ({india['long_name']})")
        return data, True

    return None, False
