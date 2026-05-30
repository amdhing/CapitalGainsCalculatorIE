"""Pydantic models for the API request/response schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field


class PriorTaxPaid(BaseModel):
    """Prior tax already paid for a given year and asset type."""

    year: int
    asset_type: str  # "Stocks" or "ETFs"
    amount_eur: float = 0.0


class CalculateRequest(BaseModel):
    """Request body for the /api/calculate endpoint."""

    files: List[str] = Field(
        ..., description="List of uploaded file IDs to process"
    )
    margin_rate: float = Field(
        default=40.0, ge=0, le=100,
        description="Your income tax marginal rate (20, 40, or 45)"
    )
    csv_export: bool = Field(
        default=False,
        description="Whether to export CSV files alongside console output"
    )
    prior_tax_paid: List[PriorTaxPaid] = Field(
        default=[],
        description="Prior tax already paid per year and asset type"
    )


class TickerInfoResponse(BaseModel):
    """Response for a ticker lookup."""

    symbol: str
    type: str
    currency: str
    active: bool
    domicile: str
    withholding_tax_deducted: bool
    merged_into: Optional[str] = None
    long_name: str = ""
    unresolvable: bool = False


class TaxLine(BaseModel):
    """A single line in the tax summary."""

    year: int
    asset_type: str
    realized_gains_gross_eur: float = 0.0
    cgt_exemption_applied_eur: float = 0.0
    carry_forward_loss_used_eur: float = 0.0
    taxable_gains_net_eur: float = 0.0
    tax_rate: str = ""
    tax_liability_eur: float = 0.0
    already_paid_eur: float = 0.0
    net_due_eur: float = 0.0
    losses_carried_forward_eur: float = 0.0
    dividends_irish_eur: float = 0.0
    dividends_foreign_eur: float = 0.0
    deemed_disposal_eur: float = 0.0
    deemed_already_paid_eur: float = 0.0



class TickerBreakdown(BaseModel):
    """Per-ticker breakdown of gains and dividends."""

    year: int
    ticker: str
    asset_type: str
    currency: str = "EUR"
    realized_gains_eur: float = 0.0
    dividends_eur: float = 0.0
    dividends_irish_eur: float = 0.0
    dividends_foreign_eur: float = 0.0
    long_name: str = ""


class CalculateResponse(BaseModel):
    """Response from the /api/calculate endpoint."""

    calculation_id: str
    tax_summary: List[TaxLine] = []
    ticker_breakdown: List[TickerBreakdown] = []
    total_tax_due_eur: float = 0.0
    console_output: str = ""


class UploadResponse(BaseModel):
    """Response from a file upload."""

    file_id: str
    filename: str
    rows: int
    preview: List[dict] = []
