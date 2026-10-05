# Irish Capital Gains Calculator - Project Spec

## What it does
Calculates Irish capital gains tax and dividend income tax from trading spreadsheets. Built for Irish tax compliance with proper FIFO accounting and Revenue.ie guidelines.

Available as both a **CLI tool** and a **web application** (FastAPI backend + React frontend).

## Key features
- **FIFO cost basis** across multiple years
- **Loss carry forward** (indefinite, as per Irish law)
- **Stock CGT** at 33% with €1,270 annual exemption
- **ETF exit tax** at 41%/38% (gains + dividends + 8-year deemed disposal)
- **Deemed disposal** (8-year rule) with per-anniversary-year attribution
- **Prior tax paid** input per year/asset type for net-due display
- **Deemed paid** (Deemed Pd) input for ETF rows
- **Dividend income tax** at your marginal rate (20%/40%/45%)
- **Multi-currency** support with EUR conversion
- **Smart ticker detection** using yfinance API with local caching
- **Merger handling** for ticker changes and corporate actions
- **CSV export** for tax filing
- **Web app**: FastAPI backend API + React frontend (Mantine UI) with file upload, per-ticker breakdown, and inline prior-tax editing

## Input format

The app auto-detects the broker format and normalises it into one internal schema.

| Broker | Format | Notes |
|--------|--------|-------|
| **Revolut** | CSV / XLSX | `Date, Ticker, Type, Quantity, Price per share, Total Amount, Currency, FX Rate` |
| **Zerodha** | XLSX (NSE/BSE tradebook) | `Symbol, ISIN, Trade Date, Trade Type, Quantity, Price`; INR auto-converted to EUR |
| **Trading 212** | CSV | Researched; full parsing on the roadmap |

Canonical (internal) columns: Date, Ticker, Type, Quantity, Price per share, Total Amount, Currency, FX Rate, Source, ISIN.

Handles transaction types: BUY, SELL, DIVIDEND, MERGER, TRANSFER
Ignores: CASH TOP-UP, CASH WITHDRAWAL, CUSTODY FEE

## Tax calculations

### Stocks (CGT @ 33%)
1. Apply €1,270 annual exemption
2. Apply carried forward losses from previous years
3. Calculate 33% tax on remaining gains
4. Carry forward any net losses to future years

**Domicile-aware CGT on foreign-situs gains** (see `src/foreign_gains.py` and
`docs/design/parsing_architecture.md`): Irish-situs (IE-domiciled) securities are
always taxed; foreign-situs gains follow the taxpayer's domicile status — arising
basis (domiciled) or remittance basis (non-domiciled).

**Indian (Zerodha) equity**: ordinary shares → CGT 33%. **Indian ETFs**
(`*BEES`, `GOLDETF`, `ALPHA`) are non-distributing offshore funds outside the
EU/EEA/OECD → **Case IV income tax** at the marginal rate, not CGT and not the
38% exit tax (see `docs/design/offshore_funds.md`).

### ETFs (Exit Tax - Per-Ticker)
- **41%** on gains, dividends, and deemed disposals (up to 31 Dec 2025)
- **38%** from 1 Jan 2026 onward
- 8-year deemed disposal rule applies
- No annual exemption, no loss relief
- **CRITICAL: Losses on one ETF cannot offset gains on another ETF** — each ticker taxed independently
  - e.g., ETF_A +€5,000 and ETF_B -€2,000 → tax on €5,000 not €3,000
  - ETF losses are forfeited, not carried forward
- **Deemed disposal gain** attributed to the anniversary year (purchase_date.year + cycles_completed × 8), not the current year
- **Prior tax paid** can be entered per year/asset type; **Deemed Paid** (Deemed Pd) has its own separate input field
- **Net Due** = tax_liability_eur - already_paid_eur - deemed_paid_amount

### Dividends (Income Tax @ Marginal Rate)
- **Stock dividends**: Income tax at 20%/40%/45% with withholding credits
- **ETF dividends**: 41% exit tax only (not income tax)
- Irish dividends: 25% DWT credit
- Foreign dividends: 15% withholding credit (US treaties)

## Technical details
- **FIFO accounting**: Proper first-in-first-out across all years
- **Ticker normalization**: Handles mergers (e.g., CBLAQ → CBL)
- **Currency conversion**: Uses provided FX rates
- **Inactive stocks**: Auto-recognized as total loss
- **Cache system**: Stores ticker info locally for speed
- **API-first**: FastAPI backend with Pydantic models exposing calculation endpoints
- **Frontend**: React (Mantine UI v7) with file upload, interactive tax tables, per-ticker filtering

## CLI Usage
```bash
# Basic calculation
python improved_calculator.py transactions.xlsx

# Multiple years with CSV export
python improved_calculator.py fy22.xlsx fy23.xlsx fy24.xlsx --csv

# Different margin rate
python improved_calculator.py transactions.xlsx --margin-rate 20

# Ticker analysis
python improved_calculator.py transactions.xlsx --ticker AAPL
```

## Web App Quick Start
```bash
# Backend — run from project root (absolute imports require this)
uvicorn src.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Output (CLI)
- **Console**: Year-by-year tax breakdown with ticker details including Deemed/Deemed Pd columns
- **CSV**: Tax summary and ticker-level data for tax filing
- **Ticker detail**: Transaction history and FIFO matching

## Output (Web App)
- **Tax Summary tables**: Stock CGT and ETF exit tax tables per year
- **Deemed/Deemed Pd columns**: Separate columns for deemed disposal gains and deemed-already-paid input
- **Already Paid / Net Due**: Editable NumberInput fields, recalculate button
- **Per-Ticker Breakdown**: Sortable, filterable table with pagination, long-name tooltips

## Data model (API)

### TaxLine
| Field | Type | Description |
|-------|------|-------------|
| year | int | Tax year |
| asset_type | str | "Stocks" or "ETFs" |
| realized_gains_gross_eur | float | Gross realized gains |
| cgt_exemption_applied_eur | float | €1,270 exemption (stocks only) |
| carry_forward_loss_used_eur | float | Loss carry forward applied |
| taxable_gains_net_eur | float | Net taxable amount |
| tax_rate | str | "33%", "41%", "38%", or the marginal income tax rate (e.g. "40%") for offshore funds |
| tax_liability_eur | float | Calculated tax due |
| already_paid_eur | float | Prior tax paid input |
| net_due_eur | float | Net amount after prior payments |
| losses_carried_forward_eur | float | Loss forward to next year |
| dividends_irish_eur | float | Irish-domiciled dividends |
| dividends_foreign_eur | float | Foreign dividends |
| deemed_disposal_eur | float | Deemed disposal gain (ETFs) |
| deemed_already_paid_eur | float | Deemed disposal tax already paid |

### PriorTaxPaid
| Field | Type | Description |
|-------|------|-------------|
| year | int | Tax year |
| asset_type | str | "Stocks" or "ETFs" |
| amount_eur | float | Amount already paid |

## Project structure

```
CapitalGainsCalculatorIE/
├── improved_calculator.py        # CLI entry point
├── requirements.txt              # Python dependencies
├── LICENSE                       # CC BY-NC-SA 4.0 License
├── .gitignore                    # Git ignore patterns
├── scripts/                      # Utility scripts
│   └── backfill_long_names.py    # Backfill ticker names from yfinance
├── src/                          # Python source code
│   ├── improved_calculator.py    # Core calculator logic
│   ├── tax/                      # Pure tax-domain modules
│   │   ├── tax_calculations.py   # CGT / ETF exit-tax / income-tax primitives
│   │   ├── foreign_gains.py      # Situs/domicile-driven CGT logic
│   │   └── offshore_funds.py     # Case IV income tax on offshore funds
│   ├── ticker_utils.py           # Ticker utilities (cache + yfinance)
│   ├── parsing/                  # Broker statement parsers (revolut, trading212, zerodha)
│   └── api/                      # FastAPI web API
│       ├── main.py               # FastAPI app entry point
│       ├── models.py             # Pydantic request/response models
│       ├── db.py                 # DynamoDB persistence layer
│       └── routers/              # API route handlers
│           ├── calculations.py   # /api/upload, /api/calculate, /api/results
│           └── tickers.py        # /api/ticker/{symbol} lookups
├── frontend/                     # React (Mantine UI) web frontend
│   ├── src/
│   │   ├── App.tsx               # Main app component
│   │   ├── main.tsx              # Entry point
│   │   ├── api/client.ts         # API client (upload, calculate, etc.)
│   │   └── components/
│   │       ├── UploadPane.tsx     # File upload UI
│   │       ├── ResultsPane.tsx    # Tax results with tables
│   │       └── HowToGuide.tsx     # Usage guide
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── data/                         # Data files
│   └── ticker_cache.json         # Ticker classification cache
├── docs/                         # Documentation
│   ├── README.md                 # Full user guide
│   ├── project_spec.md           # Technical specification
│   ├── SAMPLE_OUTPUT.md          # Example output
│   ├── tax_rules_spec.md         # ETF tax rule specs
│   ├── design/                   # Design docs
│   │   └── future_direction.md   # Product roadmap
│   └── runbooks/                 # Operations runbooks
│       └── runbook_backlog.md    # Ticker triage runbook
├── samples/                      # Sample transaction files
│   └── sample_revolut_transactions.csv  # Anonymized demo data
└── tests/                        # Python unit tests
    ├── test_tax_rules.py
    ├── test_tax_calculations.py
    ├── test_calculator_integration.py
    ├── test_calculator_methods.py
    └── test_ticker_utils.py
```

## Dependencies
- **Python**: pandas, openpyxl, numpy, yfinance, fastapi, uvicorn, pydantic, boto3
- **Frontend**: React 18, Mantine UI v7, Vite, @tabler/icons-react
- Python 3.9+ recommended

Built for Irish residents trading stocks and ETFs through brokers like Revolut, Trading 212, etc.
