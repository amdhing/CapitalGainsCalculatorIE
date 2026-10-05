"""Tests for Zerodha parsing and the situs/domicile-driven CGT engine.

Covers the genuinely new behaviour from the Zerodha work:

- Zerodha tradebook detection + canonical normalization (INR, derived total,
  BUY/SELL mapping, source tagging).
- The situs split (Irish vs foreign) that drives CGT treatment.
- Domicile-status tax computation: arising basis (domiciled) vs remittance
  basis (non-dom) vs gains-only.
- Input validation for the domicile/remittance fields.

Deliberately does NOT hit yfinance: parser tests read the checked-in sample,
and the tax engine tests use pure functions with inline result dicts.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.parsing.base import ParseError
from src.parsing.zerodha import ZerodhaParser
from src.parsing.registry import detect_and_parse
from src.improved_calculator import ImprovedCapitalGainsCalculator
from src.tax.foreign_gains import (
    ForeignGainsValidationError,
    compute_effective_stock_gains,
    compute_foreign_taxable_gains,
    split_stock_gains_by_situs,
    validate_foreign_gains_request,
)


SAMPLE = os.path.join(
    os.path.dirname(__file__), "..", "samples", "zerodha_fy24.xlsx"
)
REVOLUT_SAMPLE = os.path.join(
    os.path.dirname(__file__), "..", "samples", "sample_revolut_transactions.csv"
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class TestZerodhaParser:
    def test_detects_zerodha_tradebook(self):
        assert ZerodhaParser().can_parse(SAMPLE) is True

    def test_does_not_detect_revolut(self):
        assert ZerodhaParser().can_parse(REVOLUT_SAMPLE) is False

    def test_parses_canonical_schema(self):
        parsed = ZerodhaParser().parse(SAMPLE, inr_per_eur=90.0)
        assert parsed.source == "zerodha"
        assert parsed.rows > 0
        for col in (
            "Date", "Ticker", "Type", "Quantity", "Price per share",
            "Total Amount", "Currency", "FX Rate", "Source", "ISIN",
        ):
            assert col in parsed.data.columns

    def test_currency_is_inr_and_total_derived(self):
        parsed = ZerodhaParser().parse(SAMPLE, inr_per_eur=90.0)
        df = parsed.data
        assert set(df["Currency"].unique()) == {"INR"}
        assert set(df["Type"].unique()) <= {"BUY", "SELL"}
        assert set(df["Source"].unique()) == {"zerodha"}
        # Total Amount = Quantity × Price
        assert (df["Total Amount"] - df["Quantity"] * df["Price per share"]).abs().max() < 1e-9

    def test_fx_rate_applied(self):
        parsed = ZerodhaParser().parse(SAMPLE, inr_per_eur=90.0)
        assert set(parsed.data["FX Rate"].unique()) == {90.0}

    def test_raises_when_no_inr_rate_available(self, monkeypatch):
        # No explicit rate and the yfinance FX fetch fails -> ParseError.
        from src.parsing import zerodha as zerodha_module
        monkeypatch.setattr(zerodha_module, "fetch_inr_per_eur", lambda: None)
        with pytest.raises(ParseError):
            ZerodhaParser().parse(SAMPLE, inr_per_eur=None)
        with pytest.raises(ParseError):
            ZerodhaParser().parse(SAMPLE, inr_per_eur=0)

    def test_auto_fetches_inr_rate(self, monkeypatch):
        from src.parsing import zerodha as zerodha_module
        monkeypatch.setattr(zerodha_module, "fetch_inr_per_eur", lambda: 108.0)
        parsed = ZerodhaParser().parse(SAMPLE, inr_per_eur=None)
        assert set(parsed.data["FX Rate"].unique()) == {108.0}


class TestDetectionRegistry:
    def test_detects_zerodha_via_registry(self):
        parsed = detect_and_parse(SAMPLE, inr_per_eur=90.0)
        assert parsed.source == "zerodha"

    def test_detects_revolut_via_registry(self):
        parsed = detect_and_parse(REVOLUT_SAMPLE)
        assert parsed.source == "revolut"


# ---------------------------------------------------------------------------
# Situs split + domicile-driven CGT
# ---------------------------------------------------------------------------

def _detail(asset_type, domicile, realized):
    return {"asset_type": asset_type, "domicile": domicile, "realized_gains": realized}


class TestSplitStockGainsBySitus:
    def test_splits_irish_vs_foreign(self):
        results = {
            "ticker_detail": {
                "IE_STOCK": _detail("stocks", "IE", {2024: 1000.0}),
                "US_STOCK": _detail("stocks", "US", {2024: 2000.0}),
                "IN_STOCK": _detail("stocks", "IN", {2024: 3000.0}),
            }
        }
        irish, foreign = split_stock_gains_by_situs(results)
        assert irish == {2024: 1000.0}
        assert foreign == {2024: 5000.0}

    def test_ignores_etfs(self):
        results = {
            "ticker_detail": {
                "VWCE": _detail("etfs", "IE", {2024: 999.0}),
            }
        }
        irish, foreign = split_stock_gains_by_situs(results)
        assert irish == {}
        assert foreign == {}


class TestComputeForeignTaxableGains:
    def test_domiciled_full_gain(self):
        taxable, unremitted = compute_foreign_taxable_gains(
            {2024: 5000.0, 2025: -1000.0}, True, "domiciled", None
        )
        # Arising basis: full gain AND loss included (flows into loss relief)
        assert taxable == {2024: 5000.0, 2025: -1000.0}
        assert unremitted == 0.0

    def test_non_domiciled_remittance_fifo(self):
        gains = {2023: 1000.0, 2024: 3000.0}
        taxable, unremitted = compute_foreign_taxable_gains(
            gains, True, "non_domiciled", 2500.0
        )
        assert taxable == {2023: 1000.0, 2024: 1500.0}
        assert unremitted == 1500.0

    def test_non_domiciled_loss_not_taxed(self):
        gains = {2023: 1000.0, 2024: -500.0, 2025: 2000.0}
        taxable, unremitted = compute_foreign_taxable_gains(
            gains, True, "non_domiciled", 2500.0
        )
        # 1000 + 0 (loss skipped) + 1500 = 2500 remitted
        assert taxable == {2023: 1000.0, 2024: 0.0, 2025: 1500.0}
        assert unremitted == 500.0

    def test_gains_only_mode(self):
        taxable, unremitted = compute_foreign_taxable_gains(
            {2024: 5000.0}, False, None, None
        )
        assert taxable == {2024: 0.0}
        assert unremitted == 5000.0


class TestComputeEffectiveStockGains:
    def test_irish_always_taxable_foreign_follows_domicile(self):
        irish = {2024: 1000.0}
        foreign = {2024: 3000.0}
        effective, _ = compute_effective_stock_gains(
            irish, foreign, True, "non_domiciled", 2000.0
        )
        # Irish 1000 always + foreign 2000 (remitted) = 3000
        assert effective == {2024: 3000.0}


class TestInrToEurConversion:
    """End-to-end: the calculator converts INR to EUR and tags source/domicile."""

    def test_inr_gain_converts_to_eur_and_tags(self):
        calc = ImprovedCapitalGainsCalculator()
        # Seed the cache so no yfinance call is attempted.
        calc.ticker_cache["RELIANCE"] = {
            "type": "stock", "currency": "INR", "domicile": "IN",
            "active": True, "merged_into": None, "conversion_ratio": 1.0,
            "withholding_tax_deducted": False, "long_name": "Reliance Industries",
        }
        df = pd.DataFrame({
            "Date": ["2024-01-10", "2024-02-10"],
            "Ticker": ["RELIANCE", "RELIANCE"],
            "Type": ["BUY", "SELL"],
            "Quantity": [100.0, 100.0],
            "Price per share": [900.0, 1350.0],
            "Total Amount": [90000.0, 135000.0],
            "Currency": ["INR", "INR"],
            "FX Rate": [90.0, 90.0],
            "Source": ["zerodha", "zerodha"],
            "ISIN": [None, None],
        })
        results = calc.process_transactions(df, source="zerodha")

        # cost 900*100/90 = 1000; proceeds 1350*100/90 = 1500; gain = 500 EUR
        gain = results["summary"]["stocks"]["realized_gains"][2024]
        assert round(gain, 2) == 500.0

        detail = results["ticker_detail"]["RELIANCE"]
        assert detail["source"] == "zerodha"
        assert detail["domicile"] == "IN"


class TestValidation:
    def test_no_foreign_situs_skips_domicile_check(self):
        # Should not raise
        validate_foreign_gains_request(False, True, None, None)

    def test_foreign_situs_requires_domicile(self):
        with pytest.raises(ForeignGainsValidationError):
            validate_foreign_gains_request(True, True, None, None)

    def test_non_domiciled_requires_remittance(self):
        with pytest.raises(ForeignGainsValidationError):
            validate_foreign_gains_request(True, True, "non_domiciled", None)

    def test_non_domiciled_with_remittance_ok(self):
        validate_foreign_gains_request(True, True, "non_domiciled", 100.0)

    def test_gains_only_skips_domicile_check(self):
        validate_foreign_gains_request(True, False, None, None)