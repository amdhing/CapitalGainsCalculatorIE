# Irish Capital Gains Calculator

Calculate capital gains and dividend taxes for Irish tax compliance from trading spreadsheets. Handles stocks, ETFs, and complex scenarios like mergers and loss carry forward.

Available as both a **CLI tool** and a **web application** with a FastAPI backend and React frontend.

## Documentation

- **📊 [Sample Output](SAMPLE_OUTPUT.md)** - See example calculator output with anonymized data
- **📋 [Project Specification](project_spec.md)** - Technical details and implementation guide
- **📜 [Tax Rules Spec](tax_rules_spec.md)** - ETF exit tax rules and implementation gaps
- **🧩 [Parsing Architecture](design/parsing_architecture.md)** - Multi-broker parsing & situs/domicile tax design

## What it does

- **Calculates Irish taxes**: 33% CGT on stocks, 41%/38% exit tax on ETFs, income tax on dividends
- **FIFO accounting**: Proper cost basis calculation across multiple years
- **Loss carry forward**: Indefinite carry forward for stock losses (Irish law compliant)
- **Smart classification**: Auto-detects stocks vs ETFs (yfinance); Indian ETFs (*BEES, GOLDETF) classified as offshore funds (Case IV income tax)
- **Multi-currency**: Converts everything to EUR (INR auto-fetched for Zerodha)
- **Domicile-aware CGT**: arising vs remittance basis for foreign-situs (non-Irish) gains
- **Handles complexity**: Mergers, inactive stocks, broker transfers, 8-year deemed disposal
- **Multi-broker**: Revolut + Zerodha (Trading 212 planned) via a broker-agnostic parsing layer
- **Web app**: Upload files via browser, per-source summaries + charts, interactive tax tables with Deemed/Deemed Pd columns and prior-tax-paid inputs

## Quick start (CLI)

```bash
# Set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Basic calculation (CLI)
python improved_calculator.py samples/sample_revolut_transactions.csv

# Multiple years with CSV export
python improved_calculator.py samples/revolut_fy23.xlsx samples/revolut_fy24.xlsx --csv

# With dividend tax at your marginal rate
python improved_calculator.py samples/revolut_fy23.xlsx --margin-rate 40
```

## Quick start (Web App)

```bash
# Terminal 1: Start the FastAPI backend (run from project root)
pip install -r requirements.txt  # if not already done
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Start the React frontend
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173` in your browser.

## Input format

The app auto-detects the broker format and normalises it into one internal schema before calculating.

### Supported brokers

| Broker | Format | Notes |
|--------|--------|-------|
| **Revolut** | CSV / XLSX | Columns: `Date, Ticker, Type, Quantity, Price per share, Total Amount, Currency, FX Rate` |
| **Zerodha** | XLSX (NSE/BSE tradebook) | Indian equity — `Symbol, ISIN, Trade Date, Trade Type, Quantity, Price`. Auto-detected; INR converted to EUR automatically. |
| **Trading 212** | CSV | Format researched; full parsing is on the roadmap. |

### Canonical columns (what the tax engine consumes)
- **Date**: Transaction date
- **Ticker**: Stock/ETF symbol (AAPL, VWCE, RELIANCE, …)
- **Type**: BUY, SELL, DIVIDEND, MERGER, TRANSFER
- **Quantity**: Number of shares
- **Price per share**: In the transaction's currency
- **Total Amount**: Total transaction value
- **Currency**: EUR, USD, INR, …
- **FX Rate**: Units of "currency" per 1 EUR

Zerodha tradebooks contain only BUY/SELL in INR; dividends arrive in a separate corporate-action report (not yet parsed).

## Irish tax calculations

### Stocks (Capital Gains Tax)
- **Rate**: 33%
- **Exemption**: €1,270 per year
- **Loss relief**: Carry forward losses indefinitely
- **Dividends**: Income tax at your marginal rate (20%/40%/45%)

### ETFs (Exit Tax)
- **Rate**: 41% (up to 2025) / 38% (from 2026) on everything (gains + dividends)
- **No exemption**: No annual exemption
- **Deemed disposal**: 8-year rule applies, gain attributed to anniversary year
- **No loss relief**: Losses can't be carried forward or offset across different ETFs
- **Deemed Pd column**: Separate input field for deemed disposal tax already paid

### Offshore funds (Case IV income tax)
- **Indian ETFs** (`*BEES`, `GOLDETF`, `ALPHA`) are non-distributing offshore funds outside the EU/EEA/OECD.
- **Disposal gains** are Case IV income taxed at your marginal rate (20%/40%/45%)
- **No €1,270 exemption** and **losses are ignored** (no carry-forward)
- **No 8-year deemed disposal** (that is an equivalent-fund / Chapter 4 rule only)
- Non-domiciled taxpayers: only the portion remitted to Ireland is taxable

### Dividend taxation
- **Stock dividends**: Income tax at marginal rate with withholding credits
- **ETF dividends**: 41% exit tax (not income tax)
- **Irish companies**: 25% DWT provides tax credit
- **Foreign companies**: 15% withholding provides credit (US/treaty countries)

## CLI command options

```bash
python improved_calculator.py [files] [options]

--csv                    Export to CSV files
--margin-rate {20,40,45} Your income tax rate (default: 40%)
--ticker SYMBOL          Analyze specific ticker in detail
```

## Output (CLI)

**Console report** shows year-by-year:
- Tax liability breakdown (CGT + exit tax + dividend tax)
- Realized gains by ticker with Deemed disposal column
- Current holdings with cost basis and deemed liability

**CSV files** include:
- `irish_tax_report_tax_summary.csv`: Tax calculations by year
- `irish_tax_report_by_ticker.csv`: Detailed ticker breakdown

**Ticker analysis** shows:
- Complete transaction history
- FIFO matching visualization
- Cost basis calculations

## Output (Web App)

**Stock CGT table** per year:
- Gross, Exemption, Loss Used, Taxable, Rate, Tax Due
- **Already Paid** (editable NumberInput), **Net Due**

**ETF Tax table** per year:
- Gross, Taxable, **Deemed**, **Deemed Pd** (editable NumberInput), Rate, Tax Due
- **Already Paid** (editable), **Net Due**

**Per-Ticker Breakdown**: Sortable, filterable table with year/ticker filters, pagination, and long-name tooltips

**Recalculate button** — applies prior-tax-paid values and refreshes calculations server-side.

## Examples

### Basic tax report
```bash
python improved_calculator.py my_trades.xlsx
```
Shows capital gains tax, exit tax, and dividend tax for all years.

### Multi-year analysis with export
```bash
python improved_calculator.py 2022.xlsx 2023.xlsx 2024.xlsx --csv --margin-rate 40
```
Processes multiple years with proper FIFO and exports results.

### Ticker deep-dive
```bash
python improved_calculator.py my_trades.xlsx --ticker VWCE
```
Shows every VWCE transaction and how gains were calculated.

## Advanced features

### Loss carry forward
Stock losses automatically carry forward to future years:
- 2023: €2,000 loss → carried forward
- 2024: €3,000 gain - €1,270 exemption - €2,000 loss = €0 taxable

### Merger handling
Automatically handles ticker changes:
- CBLAQ → CBL merger with share conversion
- Zero cost basis transfers
- Maintains FIFO continuity

### Inactive stocks
Auto-recognizes bankruptcies and delistings as total losses.

### Multi-currency display
Shows cost basis in original currency for current holdings.

### Prior tax paid
In the web app, enter already-paid amounts per year/asset type. Net Due is recalculated on the server. ETF rows also have a separate **Deemed Pd** input field for deemed disposal tax already paid.

## Troubleshooting

**"Missing ticker"**: New tickers auto-added to cache via yfinance API.

**Wrong gains**: Check your transaction files have all years - FIFO needs complete history.

**Currency errors**: Ensure FX rates provided for non-EUR transactions.

**Merger issues**: Edit `data/ticker_cache.json` to configure ticker mappings.

## Files created

- `data/ticker_cache.json`: Stores ticker classifications and merger info
- `irish_tax_report_*.csv`: Tax calculations (if using --csv)

## Legal note

This tool calculates taxes based on Irish Revenue guidelines. Always verify with a tax advisor before filing. The tool is for educational purposes and personal use.

## Requirements

- **CLI**: Python 3.9+, pandas, openpyxl, numpy, yfinance
- **Web App**: Additional: fastapi, uvicorn, pydantic, boto3; Node.js 18+ for frontend
- Works on macOS, Linux, Windows

Built for Irish residents trading through modern brokers.
