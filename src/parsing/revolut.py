"""Revolut statement parser (default/fallback).

Wraps the original column layout the calculator was built around. Emits the
canonical schema but preserves the raw ``Type`` column so the calculator's
existing ``classify_transaction_type`` continues to map values such as
``SELL - LIMIT``, ``CUSTODY FEE``, etc.
"""

from typing import Optional

import openpyxl
import pandas as pd

from src.parsing.base import StatementParser, ParsedStatement, ParseError, CANONICAL_COLUMNS

# The original Revolut column set the calculator was built around.
REVOLUT_COLUMNS = [
    "Date",
    "Ticker",
    "Type",
    "Quantity",
    "Price per share",
    "Total Amount",
    "Currency",
    "FX Rate",
]


def _read_df(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def _headers(path: str):
    """Return the list of top-level column names for a CSV or XLSX file."""
    try:
        if path.lower().endswith(".csv"):
            return list(pd.read_csv(path, nrows=0).columns)
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb.worksheets[0]
            first = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
            return [str(c) for c in first if c is not None]
        finally:
            wb.close()
    except Exception:  # noqa: BLE001 - a non-Revolut file simply won't match
        return []


class RevolutParser(StatementParser):
    source = "revolut"

    def can_parse(self, path: str) -> bool:
        headers = _headers(path)
        return all(col in headers for col in REVOLUT_COLUMNS)

    def parse(self, path: str, inr_per_eur: Optional[float] = None) -> ParsedStatement:
        try:
            df = _read_df(path)
        except Exception as exc:  # noqa: BLE001
            raise ParseError(f"Could not read Revolut file: {exc}") from exc

        missing = [col for col in REVOLUT_COLUMNS if col not in df.columns]
        if missing:
            raise ParseError(f"Revolut statement missing columns: {missing}")

        df = df[REVOLUT_COLUMNS].copy()
        df["Source"] = self.source
        df["ISIN"] = None

        return ParsedStatement(
            source=self.source,
            rows=len(df),
            data=df[CANONICAL_COLUMNS],
            warnings=[],
        )