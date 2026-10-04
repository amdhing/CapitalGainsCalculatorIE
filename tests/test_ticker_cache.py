"""Tests for the canonical ticker cache schema + store.

Covers build_entry / normalize_entry / TickerCacheStore with focus on the
schema-consistency rules: core fields are always present, empty/default optional
fields are omitted, and load/save never drop required identity shape.
"""

import json

import pytest
from pydantic import ValidationError

from src.ticker_cache import (
    TickerCacheStore,
    TickerCacheEntry,
    SplitEvent,
    build_entry,
    normalize_entry,
)


class TestBuildEntry:
    def test_core_fields_always_present(self):
        entry = build_entry(type_="etf", currency="eur", domicile="ie", long_name="A")
        assert set(entry) == {
            "type",
            "currency",
            "active",
            "withholding_tax_deducted",
            "domicile",
            "long_name",
        }
        assert entry["type"] == "etf"
        assert entry["currency"] == "EUR"
        assert entry["domicile"] == "IE"
        assert entry["active"] is True
        assert entry["withholding_tax_deducted"] is False

    def test_omits_empty_optional_fields(self):
        entry = build_entry(type_="stock", currency="USD", domicile="US")
        # merged_into, conversion_ratio, yfinance_ticker, splits all omitted
        for field in ("merged_into", "conversion_ratio", "yfinance_ticker", "splits"):
            assert field not in entry

    def test_includes_populated_optional_fields(self):
        entry = build_entry(
            type_="stock",
            currency="INR",
            domicile="IN",
            long_name="Reliance",
            yfinance_ticker="RELIANCE.NS",
            splits=[{"date": "2020-01-01", "ratio": 2.0}],
        )
        assert entry["yfinance_ticker"] == "RELIANCE.NS"
        assert entry["splits"] == [{"date": "2020-01-01", "ratio": 2.0}]

    def test_merged_and_conversion_ratio_kept_only_when_meaningful(self):
        entry = build_entry(
            type_="stock",
            currency="USD",
            domicile="US",
            merged_into="NEW",
            conversion_ratio=0.5,
        )
        assert entry["merged_into"] == "NEW"
        assert entry["conversion_ratio"] == 0.5

    def test_conversion_ratio_1_0_is_omitted(self):
        entry = build_entry(
            type_="stock", currency="USD", domicile="US", conversion_ratio=1.0
        )
        assert "conversion_ratio" not in entry

    def test_explicit_withholding_tax_deducted_passthrough(self):
        entry = build_entry(
            type_="stock",
            currency="USD",
            domicile="US",
            withholding_tax_deducted=True,
        )
        assert entry["withholding_tax_deducted"] is True

    def test_uppercases_codes_and_type(self):
        entry = build_entry(type_="ETF", currency="eur", domicile="de")
        assert entry["type"] == "etf"
        assert entry["currency"] == "EUR"
        assert entry["domicile"] == "DE"


class TestNormalizeEntry:
    def test_drops_unknown_keys(self):
        raw = {
            "type": "stock",
            "currency": "USD",
            "domicile": "US",
            "long_name": "X",
            "bogus_field": "drop me",
        }
        out = normalize_entry(raw)
        assert "bogus_field" not in out

    def test_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            normalize_entry({"type": "mutual_fund", "currency": "USD", "domicile": "US"})

    def test_coerces_none_long_name_to_empty(self):
        out = normalize_entry({"type": "stock", "currency": "USD", "domicile": "US", "long_name": None})
        assert out["long_name"] == ""

    def test_empty_splits_omitted(self):
        out = normalize_entry(
            {"type": "stock", "currency": "USD", "domicile": "US", "splits": []}
        )
        assert "splits" not in out

    def test_preserves_non_empty_splits(self):
        out = normalize_entry(
            {
                "type": "stock",
                "currency": "INR",
                "domicile": "IN",
                "splits": [{"date": "2020-01-01", "ratio": 3.0}],
            }
        )
        assert out["splits"] == [{"date": "2020-01-01", "ratio": 3.0}]


class TestTickerCacheStore:
    def test_load_normalizes_and_uppercases_keys(self, tmp_path):
        path = tmp_path / "cache.json"
        path.write_text(
            json.dumps(
                {
                    "aapl": {
                        "type": "stock",
                        "currency": "usd",
                        "domicile": "US",
                        "long_name": "Apple",
                        "merged_into": None,
                        "conversion_ratio": 1.0,
                        "splits": [],
                    }
                }
            )
        )
        loaded = TickerCacheStore(path).load()
        assert "AAPL" in loaded
        entry = loaded["AAPL"]
        assert entry["currency"] == "USD"
        assert "merged_into" not in entry
        assert "conversion_ratio" not in entry
        assert "splits" not in entry

    def test_load_skips_null_and_invalid_entries(self, tmp_path):
        path = tmp_path / "cache.json"
        path.write_text(
            json.dumps(
                {
                    "NULL_ONE": None,
                    "BAD_TYPE": {"type": "crypto", "currency": "USD"},
                    "GOOD": {"type": "etf", "currency": "EUR", "domicile": "IE"},
                }
            )
        )
        loaded = TickerCacheStore(path).load()
        assert set(loaded) == {"GOOD"}

    def test_load_missing_file_returns_empty(self, tmp_path):
        store = TickerCacheStore(tmp_path / "missing.json")
        assert store.load() == {}

    def test_load_invalid_json_returns_empty(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{ not json")
        assert TickerCacheStore(path).load() == {}

    def test_save_writes_canonical_entries(self, tmp_path):
        path = tmp_path / "cache.json"
        store = TickerCacheStore(path)
        store.save(
            {
                "aapl": {
                    "type": "stock",
                    "currency": "usd",
                    "domicile": "US",
                    "long_name": "Apple",
                    "conversion_ratio": 1.0,
                    "splits": [],
                    "bogus": "x",
                }
            }
        )
        written = json.loads(path.read_text())
        entry = written["AAPL"]
        assert entry["currency"] == "USD"
        assert "conversion_ratio" not in entry
        assert "splits" not in entry
        assert "bogus" not in entry

    def test_save_sorts_keys(self, tmp_path):
        path = tmp_path / "cache.json"
        store = TickerCacheStore(path)
        store.save({"ZZZ": {"type": "stock", "currency": "USD", "domicile": "US"}})
        raw = path.read_text()
        assert raw.index('"ZZZ"') < raw.index('"active"')