"""Local ticker cache: canonical schema + normalized store.

This module is the single source of truth for the shape of
``data/ticker_cache.json``. Every ticker in the cache must conform to
:class:`TickerCacheEntry`; all producers of new entries should build them via
:func:`build_entry` (or at least :func:`normalize_entry`) so their schema can
never drift from the curated entries.

Producers that should go through this module:

* ``ticker_utils.add_missing_ticker_to_cache`` (Revolut/Trading 212 fallback)
* ``ticker_utils.add_zerodha_ticker_to_cache`` (Indian equity)
* ``ImprovedCapitalGainsCalculator._build_placeholder_ticker`` (unresolvable)
* Manual edits per ``docs/runbooks/runbook_backlog.md`` (kept canonical by
  :class:`TickerCacheStore` on the next load/save)

Schema rules
------------

**Core fields** (always present, tax/identity relevant):

    type                    ``"stock"`` | ``"etf"`` | ``"offshore_fund"``
    currency                ISO code (``EUR``, ``USD``, ``INR``, ...)
    active                  still trading?
    withholding_tax_deducted  broker already withheld dividend tax
    domicile                2-letter country code (``IE``, ``US``, ...)
    long_name               display name ("" => unresolved placeholder)

**Optional fields** (omitted when empty/default; consistency *of shape*, not
presence of empty placeholders):

    merged_into             present only when the ticker was merged into another
    conversion_ratio        present only when != 1.0 (merger conversion factor)
    yfinance_ticker         present only when an exchange-suffixed symbol is set
    splits                  present only when non-empty (list of split events)

``withholding_tax_deducted`` is a core field (always present). Its value is
passed explicitly by the caller (``False`` for auto-added/Indian/placeholder
tickers; ``True`` for curated US stocks per the runbook).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_CACHE_PATH = "data/ticker_cache.json"


class SplitEvent(BaseModel):
    """A single stock-split event: date + ratio (e.g. ratio 2.0 = 2-for-1)."""

    date: str
    ratio: float = Field(gt=0)


class TickerCacheEntry(BaseModel):
    """Canonical schema for one ticker in ``data/ticker_cache.json``.

    Unknown keys are dropped on (de)serialization so the on-disk file never
    accumulates stray fields. Missing keys fall back to the documented defaults.
    Optional fields default to ``None`` and are omitted from the serialized form
    when empty/default.
    """

    model_config = ConfigDict(extra="ignore")

    type: str = "stock"
    currency: str = "USD"
    active: bool = True
    merged_into: Optional[str] = None
    conversion_ratio: float = 1.0
    withholding_tax_deducted: bool = False
    domicile: str = "US"
    long_name: str = ""
    yfinance_ticker: Optional[str] = None
    splits: Optional[List[SplitEvent]] = None

    @field_validator("type")
    @classmethod
    def _check_type(cls, v: Any) -> str:
        v = v.lower() if isinstance(v, str) else v
        if v not in ("stock", "etf", "offshore_fund"):
            raise ValueError(
                f"type must be 'stock', 'etf' or 'offshore_fund', got {v!r}"
            )
        return v

    @field_validator("currency", "domicile")
    @classmethod
    def _upper_code(cls, v: Any) -> str:
        return v.upper() if isinstance(v, str) else v

    @field_validator("long_name", mode="before")
    @classmethod
    def _coerce_long_name(cls, v: Any) -> str:
        return "" if v is None else v

    @field_validator("splits", mode="before")
    @classmethod
    def _empty_splits_to_none(cls, v: Any) -> Optional[Any]:
        if v is None or v == [] or (isinstance(v, list) and len(v) == 0):
            return None
        return v


def _canonical_dump(entry: TickerCacheEntry) -> Dict[str, Any]:
    """Serialize an entry, omitting empty/default optional fields."""
    data = entry.model_dump(exclude_none=True)
    # conversion_ratio is only meaningful when it differs from the 1.0 default.
    if data.get("conversion_ratio") == 1.0:
        data.pop("conversion_ratio", None)
    return data


def build_entry(
    *,
    type_: str,
    currency: str,
    domicile: str,
    long_name: str = "",
    active: bool = True,
    withholding_tax_deducted: bool = False,
    merged_into: Optional[str] = None,
    conversion_ratio: float = 1.0,
    yfinance_ticker: Optional[str] = None,
    splits: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a canonical cache entry.

    Optional fields (``merged_into``, ``conversion_ratio``,
    ``yfinance_ticker``, ``splits``) are omitted from the result when empty;
    core fields are always present. ``withholding_tax_deducted`` is explicit so
    producers remain the source of truth for its value.
    """
    entry = TickerCacheEntry(
        type=type_,
        currency=currency,
        active=active,
        merged_into=merged_into,
        conversion_ratio=conversion_ratio,
        withholding_tax_deducted=withholding_tax_deducted,
        domicile=domicile,
        long_name=long_name,
        yfinance_ticker=yfinance_ticker,
        splits=splits,
    )
    return _canonical_dump(entry)


def normalize_entry(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce/validate a raw cache entry into the canonical shape.

    Raises ``pydantic.ValidationError`` if the entry cannot be normalized.
    """
    return _canonical_dump(TickerCacheEntry.model_validate(raw))


class TickerCacheStore:
    """Load/save the ticker cache, normalizing every entry through the model."""

    def __init__(self, path: str | os.PathLike = DEFAULT_CACHE_PATH):
        self.path = str(path)

    def load(self) -> Dict[str, Dict[str, Any]]:
        """Load and normalize the cache. Missing/unreadable returns ``{}``."""
        raw: Any = {}
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    raw = json.load(f)
            except (ValueError, OSError):
                raw = {}
        if not isinstance(raw, dict):
            raw = {}

        normalized: Dict[str, Dict[str, Any]] = {}
        for symbol, entry in raw.items():
            if entry is None:
                continue
            try:
                normalized[str(symbol).upper()] = normalize_entry(entry)
            except Exception:
                # Skip entries that can't be canonicalized rather than failing
                # the whole load. The migration script reports these.
                continue
        return normalized

    def save(self, cache: Dict[str, Dict[str, Any]]) -> None:
        """Normalize + write every entry so the on-disk JSON stays canonical."""
        normalized: Dict[str, Dict[str, Any]] = {}
        for symbol, entry in cache.items():
            normalized[str(symbol).upper()] = normalize_entry(entry)
        with open(self.path, "w") as f:
            json.dump(normalized, f, indent=2, sort_keys=True)
            f.write("\n")