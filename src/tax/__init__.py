"""Pure tax-domain modules.

``tax_calculations`` — CGT / ETF exit-tax / income-tax primitives.
``foreign_gains``  — situs + domicile-driven CGT split for stocks.
``offshore_funds`` — Chapter 2 Case IV income tax on non-distributing offshore
                   fund disposals (e.g. Indian SEBI ETFs).
"""

from src.tax import tax_calculations, foreign_gains, offshore_funds

__all__ = ["tax_calculations", "foreign_gains", "offshore_funds"]