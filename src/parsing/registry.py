"""Parser detection registry.

``detect_and_parse`` tries each registered parser in order and delegates to the
first one whose ``can_parse`` returns True. This keeps the tax engine decoupled
from any specific broker format.
"""

from typing import List, Optional

from src.parsing.base import StatementParser, ParsedStatement, ParseError
from src.parsing.revolut import RevolutParser
from src.parsing.trading212 import Trading212Parser
from src.parsing.zerodha import ZerodhaParser

# Order matters: most specific/first-match wins. Zerodha and Revolut are
# unambiguous by header; keep Revolut (the generic CSV/XLSX) last.
PARSERS: List[StatementParser] = [
    ZerodhaParser(),
    Trading212Parser(),
    RevolutParser(),
]


def detect_and_parse(path: str, inr_per_eur: Optional[float] = None) -> ParsedStatement:
    """Detect the broker format of ``path`` and return a parsed statement.

    Raises :class:`ParseError` if no parser claims the file.
    """
    for parser in PARSERS:
        if parser.can_parse(path):
            return parser.parse(path, inr_per_eur=inr_per_eur)
    raise ParseError(
        f"Unrecognized statement format for {path!r}: no parser matched"
    )