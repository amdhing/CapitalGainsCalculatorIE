"""Broker statement parsing layer.

Normalizes Revolut / Trading 212 / Zerodha exports into the canonical schema
consumed by the tax engine. See docs/design/parsing_architecture.md.
"""

from src.parsing.base import StatementParser, ParsedStatement, ParseError, CANONICAL_COLUMNS
from src.parsing.registry import detect_and_parse, PARSERS

__all__ = [
    "StatementParser",
    "ParsedStatement",
    "ParseError",
    "CANONICAL_COLUMNS",
    "detect_and_parse",
    "PARSERS",
]