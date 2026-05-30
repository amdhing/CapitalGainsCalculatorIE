"""API router for calculation endpoints."""

import uuid
import tempfile
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from src.api.models import (
    CalculateRequest, CalculateResponse, UploadResponse,
    PriorTaxPaid, TaxLine, TickerBreakdown,
)
from src.api.db import save_result, get_result, list_results, is_backlogged, add_to_backlog_atomic, add_parse_error
from src.improved_calculator import ImprovedCapitalGainsCalculator
from src.ticker_utils import add_missing_ticker_to_cache


def _resolve_long_name(ticker: str) -> str:
    """Resolve the long name for a ticker: cache -> backlog -> yfinance."""
    ticker = ticker.upper()
    # Check local JSON cache — return immediately if we have a long name
    cache_file = "data/ticker_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            cache = json.load(f)
        info = cache.get(ticker)
        if info and info.get("long_name"):
            return info["long_name"]
    # Check backlog — don't retry yfinance if already backlogged
    if is_backlogged(ticker):
        return ""
    # Try yfinance (cache miss, or cache entry with empty long_name)
    result, _ = add_missing_ticker_to_cache(ticker)
    if result and result.get("long_name"):
        return result["long_name"]
    # Unresolvable — add to backlog
    add_to_backlog_atomic(ticker, app_source="revolut")

    return ""

router = APIRouter(prefix="/api", tags=["calculations"])
UPLOAD_DIR = Path(tempfile.gettempdir()) / "capgains_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix if file.filename else ".csv"
    dest = UPLOAD_DIR / f"{file_id}{ext}"
    content = await file.read()
    dest.write_bytes(content)
    try:
        import pandas as pd
        if ext.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(dest, dtype=str)
        else:
            df = pd.read_csv(dest, dtype=str)
        rows = len(df)
        preview = json.loads(df.head(5).to_json(orient="records"))
        for row in preview:
            for k, v in row.items():
                if isinstance(v, float) and (v != v):
                    row[k] = None
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")
    return UploadResponse(
        file_id=file_id, filename=file.filename or "unknown",
        rows=rows, preview=preview,
    )


@router.post("/calculate", response_model=CalculateResponse)
async def calculate(request: CalculateRequest):
    if not request.files:
        raise HTTPException(status_code=400, detail="No files provided")
    file_paths = []
    for fid in request.files:
        matches = list(UPLOAD_DIR.glob(f"{fid}.*"))
        if not matches:
            raise HTTPException(status_code=404, detail=f"Uploaded file {fid} not found")
        file_paths.append(str(matches[0]))

    calc_id = str(uuid.uuid4())
    try:
        import pandas as pd

        # Load and combine all files
        dfs = []
        for fp in file_paths:
            if fp.lower().endswith(".csv"):
                df = pd.read_csv(fp)
            else:
                df = pd.read_excel(fp)
            dfs.append(df)
        combined = pd.concat(dfs, ignore_index=True)

        calculator = ImprovedCapitalGainsCalculator()
        results = calculator.process_transactions(combined)

        # Persist any skipped rows for later inspection
        for skipped in results.get('skipped_rows', []):
            add_parse_error(calc_id, skipped)

        # Build tax summary from results
        margin_rate = request.margin_rate
        all_years = set()
        for asset_type in results["summary"].values():
            all_years.update(asset_type["realized_gains"].keys())
            all_years.update(asset_type["dividends"].keys())
            all_years.update(asset_type.get("deemed_disposal_gains", {}).keys())

        accumulated_losses = 0
        tax_summary = []
        cgt_exemption = 1270
        tax_lines = {}

        for year in sorted(all_years):
            stock_realized = results["summary"]["stocks"]["realized_gains"].get(year, 0)
            # Apply CGT with loss carry forward
            after_exemption = stock_realized - min(stock_realized, cgt_exemption) if stock_realized > 0 else stock_realized
            carry_forward_used = 0
            if after_exemption > 0 and accumulated_losses > 0:
                carry_forward_used = min(after_exemption, accumulated_losses)
                accumulated_losses -= carry_forward_used
                after_exemption -= carry_forward_used
            stock_taxable = max(0, after_exemption)
            stock_cgt = stock_taxable * 0.33
            if after_exemption < 0:
                accumulated_losses += abs(after_exemption)

            stock_dividends_irish = results["summary"]["stocks"]["dividends_irish"].get(year, 0)
            stock_dividends_foreign = results["summary"]["stocks"]["dividends_foreign"].get(year, 0)

            tax_lines[year] = {
                "stock": {
                    "gross": float(stock_realized),
                    "exemption": float(min(stock_realized, cgt_exemption) if stock_realized > 0 else 0),
                    "loss_used": float(carry_forward_used),
                    "taxable": float(stock_taxable),
                    "tax": float(stock_cgt),
                    "loss_cf": float(accumulated_losses),
                    "div_irish": float(stock_dividends_irish),
                    "div_foreign": float(stock_dividends_foreign),
                }
            }

            # ETF exit tax
            from src.tax_calculations import get_etf_exit_tax_rate, calculate_etf_exit_tax_per_ticker

            per_ticker_etf = {}
            for ticker, td in results["ticker_detail"].items():
                if td["asset_type"] == "etfs":
                    yr_r = td["realized_gains"].get(year, 0)
                    yr_d = td["dividends"].get(year, 0)
                    if yr_r != 0 or yr_d != 0:
                        per_ticker_etf[ticker] = {"realized_gains": yr_r, "dividends": yr_d, "deemed_gains": 0}
            etf_tax = calculate_etf_exit_tax_per_ticker(per_ticker_etf, year)
            etf_deemed = results["summary"]["etfs"]["deemed_disposal_gains"].get(year, 0)
            etf_total_taxable = etf_tax["total_taxable"] + etf_deemed
            exit_rate = get_etf_exit_tax_rate(year)
            etf_tax_liability = etf_tax["total_exit_tax"] + (etf_deemed * exit_rate)

            tax_lines[year]["etf"] = {
                "gross": float(results["summary"]["etfs"]["realized_gains"].get(year, 0)),
                "taxable": float(etf_total_taxable),
                "tax": float(etf_tax_liability),
            }

        # Build lookup for prior tax paid: (year, asset_type) -> amount
        prior_lookup = {}
        for ptp in request.prior_tax_paid:
            prior_lookup[(ptp.year, ptp.asset_type)] = ptp.amount_eur

        for year in sorted(tax_lines):
            sl = tax_lines[year]["stock"]
            stock_already = prior_lookup.get((year, "Stocks"), 0.0)
            stock_net_due = sl["tax"] - stock_already
            tax_summary.append(
                TaxLine(
                    year=year,
                    asset_type="Stocks",
                    realized_gains_gross_eur=sl["gross"],
                    cgt_exemption_applied_eur=sl["exemption"],
                    carry_forward_loss_used_eur=sl["loss_used"],
                    taxable_gains_net_eur=sl["taxable"],
                    tax_rate="33%",
                    tax_liability_eur=sl["tax"],
                    already_paid_eur=stock_already,
                    net_due_eur=stock_net_due,
                    losses_carried_forward_eur=sl["loss_cf"],
                    dividends_irish_eur=sl["div_irish"],
                    dividends_foreign_eur=sl["div_foreign"],
                )
            )
            el = tax_lines[year]["etf"]
            etf_already = prior_lookup.get((year, "ETFs"), 0.0)
            exit_rate = get_etf_exit_tax_rate(year)
            etf_rate_display = f"{int(exit_rate * 100)}%"
            etf_net_due = el["tax"] - etf_already
            tax_summary.append(
                TaxLine(
                    year=year,
                    asset_type="ETFs",
                    realized_gains_gross_eur=el["gross"],
                    taxable_gains_net_eur=el["taxable"],
                    tax_rate=etf_rate_display,
                    tax_liability_eur=el["tax"],
                    already_paid_eur=etf_already,
                    net_due_eur=etf_net_due,
                    deemed_disposal_eur=float(etf_deemed),
                    deemed_already_paid_eur=0.0,
                )
            )


        # Per-ticker breakdown
        ticker_breakdown = []
        resolved_info = {}  # ticker -> {"long_name": ..., "currency": ...}
        cache_file = "data/ticker_cache.json"
        ticker_cache = {}
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                ticker_cache = json.load(f)

        for ticker, td in results["ticker_detail"].items():
            asset_label = "Stocks" if td["asset_type"] == "stocks" else "ETFs"
            # Resolve long name & currency once per ticker
            if ticker not in resolved_info:
                resolved_info[ticker] = {
                    "long_name": _resolve_long_name(ticker),
                    "currency": ticker_cache.get(ticker, {}).get("currency", "EUR"),
                }
            info = resolved_info[ticker]
            # Collect years from realized gains AND dividends (dividends-only years were being missed)
            ticker_years = set(td["realized_gains"].keys()) | set(td["dividends"].keys())
            for yr in sorted(ticker_years):
                ticker_breakdown.append(
                    TickerBreakdown(
                        year=yr,
                        ticker=ticker,
                        asset_type=asset_label,
                        currency=info["currency"],
                        realized_gains_eur=float(td["realized_gains"].get(yr, 0)),
                        dividends_eur=float(td["dividends"].get(yr, 0)),
                        dividends_irish_eur=float(td.get("dividends_irish", {}).get(yr, 0)),
                        dividends_foreign_eur=float(td.get("dividends_foreign", {}).get(yr, 0)),
                        long_name=info["long_name"],
                    )
                )

        total_tax = sum(t.tax_liability_eur for t in tax_summary)

        save_result(
            calculation_id=calc_id,
            input_data=request.model_dump(),
            results={
                "tax_summary": [t.model_dump() for t in tax_summary],
                "ticker_breakdown": [t.model_dump() for t in ticker_breakdown],
                "total_tax_due_eur": total_tax,
            },
        )

        return CalculateResponse(
            calculation_id=calc_id,
            tax_summary=tax_summary,
            ticker_breakdown=ticker_breakdown,
            total_tax_due_eur=total_tax,
            console_output="",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation failed: {e}")


@router.get("/results/{calc_id}")
async def get_calculation(calc_id: str):
    result = get_result(calc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@router.get("/results")
async def list_calculations(limit: int = 20):
    return list_results(limit=limit)
