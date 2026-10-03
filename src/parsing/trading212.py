"""Trading 212 statement parser (deferred stub).

The Trading 212 CSV order-export format has been researched and a sample exists
at ``samples/sample_trading212_orders.csv``, but full parsing is deferred. This
stub reserves the source id and documents the expected direction so the registry
has a stable slot for it.
"""

from typing import Optional

from src.parsing.base import StatementParser, ParsedStatement, ParseError


class Trading212Parser(StatementParser):
    source = "trading212"

    def can_parse(self, path: str) -> bool:
        # Not yet implemented — reserved for the order export format.
        return False

    def parse(self, path: str, inr_per_eur: Optional[float] = None) -> ParsedStatement:
        raise ParseError("Trading 212 parsing is not yet implemented")