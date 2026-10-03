"""Base classes for broker statement parsers.

Each parser normalizes a specific broker export into the canonical
transaction schema consumed by the tax engine (documented in
docs/design/parsing_architecture.md).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd


# Columns every parser must emit (canonical schema). The tax engine reads the
# first eight; Source and ISIN are additive and enable per-source behaviour.
CANONICAL_COLUMNS = [
    "Date",
    "Ticker",
    "Type",
    "Quantity",
    "Price per share",
    "Total Amount",
    "Currency",
    "FX Rate",
    "Source",
    "ISIN",
]


class ParseError(Exception):
    """Raised when a file cannot be parsed (invalid or missing data)."""


@dataclass
class ParsedStatement:
    """The normalized output of a parser: a canonical-schema DataFrame."""

    source: str
    rows: int
    data: pd.DataFrame
    warnings: List[str] = field(default_factory=list)


class StatementParser(ABC):
    """Base class for all broker statement parsers."""

    source: str = ""

    @abstractmethod
    def can_parse(self, path: str) -> bool:
        """Return True if this parser owns the file format at ``path``.

        Must never raise; return False for anything it cannot confidently match.
        """

    @abstractmethod
    def parse(
        self, path: str, inr_per_eur: Optional[float] = None
    ) -> ParsedStatement:
        """Parse ``path`` into a canonical :class:`ParsedStatement`.

        Raises :class:`ParseError` when the file cannot be parsed.
        """