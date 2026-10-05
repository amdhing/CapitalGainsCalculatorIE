"""Situs-driven Irish CGT logic for foreign-situs stock gains.

Irish CGT treatment of a stock gain depends on the **security's situs**
(the country of the underlying asset), not the broker it came through:

- **Irish-situs** assets (domicile == "IE") are always taxable in Ireland on
  the arising basis for an Irish tax resident.
- **Foreign-situs** assets (domicile != "IE") are taxable depending on the
  taxpayer's **domicile status** (see docs/design/parsing_architecture.md):
    * "domiciled"      -> arising basis: full worldwide gain taxable.
    * "non_domiciled"  -> remittance basis: only gains remitted to Ireland
      are taxable.

This is deliberately broker-agnostic and framework-agnostic (pure functions,
no FastAPI import). Zerodha, Groww, INDMoney, etc. are just INR-denominated
sources of Indian-situs stock; Revolut / Trading 212 can carry both
Irish-situs and foreign-situs securities. New brokers or countries plug into
the same parser layer + this same situs split — no per-broker tax engine.
"""

# Securities domiciled in these jurisdictions are "Irish-situs" (taxable on the
# arising basis regardless of the taxpayer's own domicile).
IRISH_SITUS_DOMICILES = {"IE"}

VALID_DOMICILES = ("domiciled", "non_domiciled")


class ForeignGainsValidationError(ValueError):
    """Raised when the domicile/remittance inputs are invalid."""


def validate_foreign_gains_request(
    has_foreign_situs: bool,
    apply_irish_tax: bool,
    domicile,
    remitted_foreign_gains_eur,
):
    """Raise :class:`ForeignGainsValidationError` on invalid inputs.

    Args:
        has_foreign_situs: whether any stock is non-IE domiciled.
        apply_irish_tax: whether Irish CGT should be computed at all.
        domicile: "domiciled" | "non_domiciled" | None.
        remitted_foreign_gains_eur: portion of foreign gains remitted to IE.
    """
    if not apply_irish_tax:
        # Gains-only report: no domicile assertion required.
        return

    if not has_foreign_situs:
        # No foreign-situs assets: domicile status is irrelevant.
        return

    if domicile not in VALID_DOMICILES:
        raise ForeignGainsValidationError(
            "Foreign-situs stock gains require 'domicile' to be "
            '"domiciled" or "non_domiciled".'
        )

    if domicile == "non_domiciled" and remitted_foreign_gains_eur is None:
        raise ForeignGainsValidationError(
            "Non-domiciled taxpayers must provide 'remitted_foreign_gains_eur' "
            "(the portion of foreign gains remitted to Ireland)."
        )


def split_stock_gains_by_situs(results):
    """Split per-year stock realized gains into (irish, foreign) buckets.

    Returns (irish: dict[year, float], foreign: dict[year, float]).
    Uses the `domicile` tag stamped on each stock ticker in
    ``results['ticker_detail']`` (not the broker source).
    """
    irish = {}
    foreign = {}
    for ticker, detail in results.get("ticker_detail", {}).items():
        if detail.get("asset_type") != "stocks":
            continue
        domicile = (detail.get("domicile") or "").upper()
        realized = detail.get("realized_gains", {})
        if not isinstance(realized, dict):
            continue
        target = irish if domicile in IRISH_SITUS_DOMICILES else foreign
        for year, val in realized.items():
            target[year] = target.get(year, 0.0) + val
    return irish, foreign


def compute_foreign_taxable_gains(
    foreign_gains_by_year, apply_irish_tax, domicile, remitted_foreign_gains_eur
):
    """Determine the Irish-taxable portion of foreign-situs gains per year.

    Returns (taxable: dict[year, float], unremitted_total: float).

    - apply_irish_tax=False -> nothing is taxable; all gains "unremitted".
    - domiciled           -> full gains are taxable (arising basis), losses
      included so they flow into normal CGT loss relief.
    - non_domiciled       -> only positive gains up to the remitted amount are
      taxable, allocated FIFO across years. Foreign losses are NOT relievable
      on the remittance basis (conservative).
    """
    taxable = {}
    unremitted_total = 0.0
    years = sorted(foreign_gains_by_year.keys())

    if not apply_irish_tax:
        for year in years:
            taxable[year] = 0.0
            unremitted_total += max(0.0, foreign_gains_by_year[year])
        return taxable, unremitted_total

    if domicile == "domiciled":
        for year in years:
            taxable[year] = foreign_gains_by_year[year]
        return taxable, 0.0

    # non_domiciled: remittance basis, positive gains only, FIFO by year.
    remaining_remitted = remitted_foreign_gains_eur or 0.0
    for year in years:
        gain = foreign_gains_by_year[year]
        positive = max(0.0, gain)
        taxed = min(positive, remaining_remitted)
        remaining_remitted = max(0.0, remaining_remitted - taxed)
        taxable[year] = taxed
        unremitted_total += positive - taxed
    return taxable, unremitted_total


def compute_effective_stock_gains(
    irish_gains_by_year, foreign_gains_by_year,
    apply_irish_tax, domicile, remitted_foreign_gains_eur,
):
    """Combine Irish + foreign gains into the per-year Irish-taxable CGT base.

    Returns (effective: dict[year, float], unremitted_total: float).
    Irish-situs gains are always included (arising basis). Foreign-situs gains
    follow :func:`compute_foreign_taxable_gains`.
    """
    years = sorted(set(irish_gains_by_year) | set(foreign_gains_by_year))
    foreign_taxable, unremitted_total = compute_foreign_taxable_gains(
        foreign_gains_by_year, apply_irish_tax, domicile, remitted_foreign_gains_eur
    )
    effective = {}
    for year in years:
        effective[year] = irish_gains_by_year.get(year, 0.0) + foreign_taxable.get(year, 0.0)
    return effective, unremitted_total