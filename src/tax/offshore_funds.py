"""Case IV income tax on non-distributing offshore funds (Chapter 2).

Irish treatment of a disposal of units in a **non-distributing offshore fund**
located outside the EU/EEA/OECD (e.g. Indian SEBI ETFs such as NIFTYBEES,
ITBEES, GOLDBEES) is **Case IV income tax** at the taxpayer's marginal rate —
not CGT and not the 41%/38% exit tax reserved for "equivalent" funds (see
docs/design/offshore_funds.md).

Key differences from the stock (CGT) path:

- **No €1,270 annual exemption** (s.745/Sch 20).
- **No loss relief**: disposal losses are ignored (Sch 20 para 3(2)) — they
  neither offset other offshore gains nor carry forward.
- **No 8-year deemed disposal** (that is a Chapter 4 / equivalent-fund rule).
- **Domicile** determines *when* the gain is assessed, via s.745(4):
    * "domiciled"      -> arising basis: the full gain is income.
    * "non_domiciled"  -> remittance basis: only the portion remitted to
      Ireland is income (applies s.29(4)/(5)).

This module is deliberately broker-agnostic and pure (no FastAPI/framework
imports), mirroring :mod:`src.tax.foreign_gains`.
"""

VALID_DOMICILES = ("domiciled", "non_domiciled")


class OffshoreFundsValidationError(ValueError):
    """Raised when the offshore-fund domicile/remittance inputs are invalid."""


def validate_offshore_funds_request(
    has_offshore_funds: bool,
    apply_irish_tax: bool,
    domicile,
    remitted_offshore_income_eur,
):
    """Raise :class:`OffshoreFundsValidationError` on invalid inputs.

    Args:
        has_offshore_funds: whether any ticker is an ``offshore_fund``.
        apply_irish_tax: whether Irish tax should be computed at all.
        domicile: "domiciled" | "non_domiciled" | None.
        remitted_offshore_income_eur: Case IV income remitted to IE (non-dom).
    """
    if not apply_irish_tax:
        return

    if not has_offshore_funds:
        return

    if domicile not in VALID_DOMICILES:
        raise OffshoreFundsValidationError(
            "Offshore-fund (Case IV) disposals require 'domicile' to be "
            '"domiciled" or "non_domiciled".'
        )

    if domicile == "non_domiciled" and remitted_offshore_income_eur is None:
        raise OffshoreFundsValidationError(
            "Non-domiciled taxpayers must provide 'remitted_offshore_income_eur' "
            "(the portion of offshore-fund Case IV income remitted to Ireland)."
        )


def split_offshore_fund_gains(results):
    """Collect per-year offshore-fund realized gains into a single dict.

    Offshore funds are, by definition, foreign-situs (Indian ETFs are the seeded
    population), so no Irish/foreign split is required to compute the Case IV
    base — unlike :func:`src.tax.foreign_gains.split_stock_gains_by_situs`.
    Losses are kept as-is here and ignored later (Sch 20 para 3(2)).
    """
    gains: dict = {}
    for _, detail in results.get("ticker_detail", {}).items():
        if detail.get("asset_type") != "offshore_funds":
            continue
        realized = detail.get("realized_gains", {})
        if not isinstance(realized, dict):
            continue
        for year, val in realized.items():
            gains[year] = gains.get(year, 0.0) + val
    return gains


def compute_offshore_taxable_income(
    offshore_gains_by_year,
    apply_irish_tax,
    domicile,
    remitted_offshore_income_eur,
):
    """Determine the Irish-taxable Case IV income per year.

    Returns (taxable: dict[year, float], unremitted_total: float).

    - apply_irish_tax=False -> nothing taxable; all positive gains "unremitted".
    - domiciled           -> full positive gains taxable (arising basis);
      losses are ignored (no relief, no carry-forward).
    - non_domiciled       -> only positive gains up to the remitted amount are
      taxable, allocated FIFO across years (s.745(4)). Losses are ignored and
      never create a remittance credit.
    """
    taxable = {}
    unremitted_total = 0.0
    years = sorted(offshore_gains_by_year.keys())

    if not apply_irish_tax:
        for year in years:
            taxable[year] = 0.0
            unremitted_total += max(0.0, offshore_gains_by_year[year])
        return taxable, unremitted_total

    if domicile == "domiciled":
        for year in years:
            taxable[year] = max(0.0, offshore_gains_by_year[year])
        return taxable, 0.0

    # non_domiciled: remittance basis, positive gains only, FIFO by year.
    remaining_remitted = remitted_offshore_income_eur or 0.0
    for year in years:
        positive = max(0.0, offshore_gains_by_year[year])
        taxed = min(positive, remaining_remitted)
        remaining_remitted = max(0.0, remaining_remitted - taxed)
        taxable[year] = taxed
        unremitted_total += positive - taxed
    return taxable, unremitted_total