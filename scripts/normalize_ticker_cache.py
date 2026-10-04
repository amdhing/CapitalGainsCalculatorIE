#!/usr/bin/env python3
"""One-shot normalization of ``data/ticker_cache.json`` into the canonical schema.

Loads the raw cache, validates every entry through
:class:`src.ticker_cache.TickerCacheEntry`, reports any entry that cannot be
normalized (never silently drops data), then writes the canonical form back.

Run from project root::

    python scripts/normalize_ticker_cache.py [path]

Defaults to ``data/ticker_cache.json``. The write is done through
:class:`TickerCacheStore` so the on-disk JSON is the same canonical form every
producer produces going forward.
"""

import json
import os
import sys

# Allow running as `python scripts/normalize_ticker_cache.py` from anywhere;
# ensure the project root (parent of scripts/) is importable for `src.*`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ticker_cache import TickerCacheStore, normalize_entry, DEFAULT_CACHE_PATH


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CACHE_PATH

    with open(path) as f:
        raw = json.load(f)

    if not isinstance(raw, dict):
        print(f"ERROR: {path} does not contain a top-level JSON object")
        return 1

    normalized = {}
    failures = []
    changed = 0
    for symbol, entry in raw.items():
        if entry is None:
            failures.append((symbol, "entry is null"))
            continue
        try:
            norm = normalize_entry(entry)
        except Exception as exc:  # noqa: BLE001 - report rather than drop
            failures.append((symbol, str(exc)))
            continue
        if norm != entry:
            changed += 1
        normalized[str(symbol).upper()] = norm

    if failures:
        print(f"ERROR: {len(failures)} of {len(raw)} entries could not be normalized:")
        for sym, why in failures:
            print(f"  {sym}: {why}")
        return 1

    TickerCacheStore(path).save(normalized)
    print(f"Normalized {len(raw)} tickers ({changed} changed) -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())