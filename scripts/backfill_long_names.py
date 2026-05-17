#!/usr/bin/env python3
"""Backfill long_name for all existing tickers in data/ticker_cache.json.

Run this once to augment all current cache entries with long_name.
Usage: python scripts/backfill_long_names.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yfinance as yf

CACHE_FILE = "data/ticker_cache.json"


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def main():
    cache = load_cache()
    if not cache:
        print("No cache entries found.")
        return

    updated = 0
    skipped = 0
    errors = 0

    for symbol, info in cache.items():
        # Skip if long_name already present
        if info.get("long_name"):
            skipped += 1
            continue

        print(f"Fetching long name for {symbol}...", end=" ")
        try:
            yf_ticker = yf.Ticker(symbol)
            yf_info = yf_ticker.info
            long_name = yf_info.get("longName") or yf_info.get("shortName") or ""
            if long_name:
                cache[symbol]["long_name"] = long_name
                updated += 1
                print(long_name)
            else:
                cache[symbol]["long_name"] = ""
                print("(empty)")
                updated += 1
            # Be nice to yfinance rate limits
            time.sleep(0.5)
        except Exception as e:
            print(f"Error: {e}")
            errors += 1

    save_cache(cache)
    print(f"\nDone. Updated: {updated}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    main()
