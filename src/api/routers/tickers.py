"""API router for ticker info lookups.

Lookup flow:
1. Check local JSON cache (data/ticker_cache.json)
2. Check DynamoDB backlog (if ticker is already known as unresolvable)
3. Query yfinance, cache the result, or add to backlog if unresolvable
"""

import json
import os
from fastapi import APIRouter, HTTPException
from src.api.models import TickerInfoResponse
from src.api.db import is_backlogged, add_to_backlog_atomic, list_backlog, list_parse_errors
from src.ticker_utils import add_missing_ticker_to_cache

router = APIRouter(prefix="/api", tags=["tickers"])


def _load_cache():
    """Load ticker cache from JSON file."""
    cache_file = "data/ticker_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)
    return {}


@router.get("/ticker/{symbol}", response_model=TickerInfoResponse)
async def get_ticker_info(symbol: str, app_source: str = "manual"):
    symbol = symbol.upper().strip()
    cache = _load_cache()

    # 1. Check local cache — if we have a long_name, return immediately
    info = cache.get(symbol)
    if info is not None and info.get("long_name"):
        return TickerInfoResponse(
            symbol=symbol,
            type=info.get("type", "stock"),
            currency=info.get("currency", "USD"),
            active=info.get("active", True),
            domicile=info.get("domicile", "US"),
            withholding_tax_deducted=info.get("withholding_tax_deducted", True),
            merged_into=info.get("merged_into"),
            long_name=info["long_name"],
        )

    # 2. Check DynamoDB backlog (already known as unresolvable)
    if is_backlogged(symbol):
        return TickerInfoResponse(
            symbol=symbol,
            type="stock",
            currency="USD",
            active=True,
            domicile="US",
            withholding_tax_deducted=False,
            merged_into=None,
            long_name="",
            unresolvable=True,
        )

    # 3. Try yfinance (cache miss, or cache hit with empty long_name)
    result, is_new = add_missing_ticker_to_cache(symbol)
    if result is not None and result.get("long_name"):
        return TickerInfoResponse(
            symbol=symbol,
            type=result.get("type", "stock"),
            currency=result.get("currency", "USD"),
            active=result.get("active", True),
            domicile=result.get("domicile", "US"),
            withholding_tax_deducted=result.get("withholding_tax_deducted", False),
            merged_into=result.get("merged_into"),
            long_name=result["long_name"],
        )

    # 4. Unresolvable — add to backlog
    add_to_backlog_atomic(symbol, app_source=app_source)
    return TickerInfoResponse(
        symbol=symbol,
        type="stock",
        currency="USD",
        active=True,
        domicile="US",
        withholding_tax_deducted=False,
        merged_into=None,
        long_name="",
        unresolvable=True,
    )



@router.get("/backlog")
async def get_backlog():
    """List all unresolvable tickers in the backlog."""
    items = list_backlog()
    return {"backlog": items, "total": len(items)}


@router.delete("/backlog/{symbol}")
async def remove_from_backlog(symbol: str):
    """Remove a ticker from the backlog so it can be retried."""
    from src.api.db import backlog_table
    if backlog_table is None:
        raise HTTPException(status_code=503, detail="Backlog not available")
    try:
        backlog_table.delete_item(Key={"ticker": symbol.upper()})
        return {"status": "removed", "ticker": symbol.upper()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickers")
async def list_tickers(search: str = "", limit: int = 50):
    cache = _load_cache()

    result = []
    for symbol, info in cache.items():
        if search and search.upper() not in symbol:
            continue
        result.append({
            "symbol": symbol,
            "type": info.get("type", "stock"),
            "currency": info.get("currency", "USD"),
            "long_name": info.get("long_name", ""),
        })
        if len(result) >= limit:
            break
    return {"tickers": result, "total": len(result)}


@router.get("/parse-errors")
async def get_parse_errors(limit: int = 50):
    """List rows that could not be parsed (e.g. unparseable dates)."""
    items = list_parse_errors(limit=limit)
    return {"parse_errors": items, "total": len(items)}
