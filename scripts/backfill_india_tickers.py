#!/usr/bin/env python3
"""Re-resolve Indian-domiciled tickers that lack a real yfinance symbol.

Backfills ``long_name`` and ``yfinance_ticker`` for Zerodha/Indian equity
placeholders in ``data/ticker_cache.json``, then removes successfully-resolved
tickers from the DynamoDB backlog.

Why this exists
---------------

``add_zerodha_ticker_to_cache`` short-circuits when a ticker is already in the
cache, so any ticker that previously failed yfinance resolution (and was stored
as a ``long_name == "...coming soon..."`` placeholder) can never be retried.
This script re-runs the ``.NS`` -> ``.BO`` resolution for those entries,
recovering symbols that a transient yfinance error/rate-limit caused to fail.

Run from project root::

    python scripts/backfill_india_tickers.py [--dry-run]

``--dry-run`` prints what would change without writing.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Allow running as `python scripts/...` from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ticker_cache import TickerCacheStore, build_entry, normalize_entry
from src.ticker_utils import _fetch_india_ticker

CACHE_PATH = "data/ticker_cache.json"
PLACEHOLDER_MARKER = "coming soon..."

SUFFIXES = (".NS", ".BO")


def _resolve(symbol: str, retries: int = 3) -> dict | None:
    """Try .NS then .BO with per-symbol retry/backoff.

    yfinance transiently rate-limits, so a single 404 is not conclusive.
    """
    for attempt in range(1, retries + 1):
        for suffix in SUFFIXES:
            info = _fetch_india_ticker(f"{symbol}{suffix}")
            if info is not None:
                return {
                    "long_name": info["long_name"],
                    "yfinance_ticker": f"{symbol}{suffix}",
                }
        if attempt < retries:
            time.sleep(2 ** attempt)  # 2s, then 4s
    return None


def iter_indian_targets(cache: dict) -> dict[str, dict]:
    """Yield Indian-domiciled entries that need resolution.

    A ticker is targeted if it is India-domiciled (currency INR or domicile IN)
    and either has a placeholder long_name or is missing ``yfinance_ticker``.
    """
    targets = {}
    for symbol, entry in cache.items():
        if entry.get("currency") != "INR" and entry.get("domicile") != "IN":
            continue
        long_name = entry.get("long_name", "")
        if PLACEHOLDER_MARKER in long_name or not entry.get("yfinance_ticker"):
            targets[symbol] = entry
    return targets


def clear_backlog(ticker: str) -> bool:
    """Remove a resolved ticker from the DynamoDB backlog, if available."""
    try:
        from src.api.db import backlog_table
    except Exception:
        return False
    if backlog_table is None:
        return False
    try:
        backlog_table.delete_item(Key={"ticker": ticker.upper()})
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    store = TickerCacheStore(CACHE_PATH)
    cache = store.load()
    targets = iter_indian_targets(cache)

    if not targets:
        print("No Indian tickers needing resolution.")
        return 0

    print(f"{len(targets)} Indian ticker(s) need resolution:")
    resolved, failed = [], []
    for symbol in sorted(targets):
        info = _resolve(symbol)
        if info is None:
            failed.append(symbol)
            print(f"  - {symbol}: unresolved")
            continue
        resolved.append((symbol, info))
        print(f"  + {symbol}: {info['yfinance_ticker']} ({info['long_name']})")

    if not args.dry_run and resolved:
        for symbol, info in resolved:
            entry = normalize_entry(
                {**cache[symbol], "long_name": info["long_name"], "yfinance_ticker": info["yfinance_ticker"]}
            )
            cache[symbol] = entry
            clear_backlog(symbol)
        store.save(cache)
        print(f"\nSaved {len(resolved)} resolution(s) and cleared backlog entries.")
    elif args.dry_run:
        print("\n[--dry-run] no writes made.")

    print(f"\nResolved: {len(resolved)}, still unresolved: {len(failed)}")
    if failed:
        print("Still unresolved:", ", ".join(sorted(failed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())