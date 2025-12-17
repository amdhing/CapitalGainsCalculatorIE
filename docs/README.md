# Irish Capital Gains Calculator

Calculate capital gains and dividend taxes for Irish tax compliance from trading spreadsheets. Handles stocks, ETFs, and complex scenarios like mergers and loss carry forward.

## Documentation

- **📊 [Sample Output](SAMPLE_OUTPUT.md)** - See example calculator output with anonymized data
- **📋 [Project Specification](project_spec.md)** - Technical details and implementation guide

## What it does

- **Calculates Irish taxes**: 33% CGT on stocks, 41% exit tax on ETFs, income tax on dividends
- **FIFO accounting**: Proper cost basis calculation across multiple years
- **Loss carry forward**: Indefinite carry forward for stock losses (Irish law compliant)
- **Smart classification**: Auto-detects stocks vs ETFs using yfinance API
- **Multi-currency**: Converts everything to EUR using your FX rates
- **Handles complexity**: Mergers, inactive stocks, broker transfers

## Quick start

```bash
# Set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Basic calculation
python improved_calculator.py samples/revolut_fy23.xlsx

# Multiple years with CSV export
python improved_calculator.py samples/revolut_fy23.xlsx samples/revolut_fy24.xlsx --csv

# With dividend tax at your marginal rate
python improved_calculator.py samples/revolut_fy23.xlsx --margin-rate 40
```

## Input format

Your Excel/CSV needs these columns:
- **Date**: Transaction date
- **Ticker**: Stock/ETF symbol (AAPL, VWCE, etc.)
- **Type**: BUY, SELL, DIVIDEND, etc.
- **Quantity**: Number of shares
- **Price per share**: In original currency
- **Total Amount**: Total transaction value
- **Currency**: EUR, USD, etc.
- **FX Rate**: Exchange rate to EUR

**Designed for Revolut exports** - This calculator is specifically tested with Revolut transaction format. Other brokers (Trading 212, etc.) may require format adjustments.

## Irish tax calculations

### Stocks (Capital Gains Tax)
- **Rate**: 33%
- **Exemption**: €1,270 per year
- **Loss relief**: Carry forward losses indefinitely
- **Dividends**: Income tax at your marginal rate (20%/40%/45%)

### ETFs (Exit Tax)
- **Rate**: 41% on everything (gains + dividends)
- **No exemption**: No annual exemption
- **Deemed disposal**: 8-year rule applies
- **No loss relief**: Losses can't be carried forward

### Dividend taxation
- **Stock dividends**: Income tax at marginal rate with withholding credits
- **ETF dividends**: 41% exit tax (not income tax)
- **Irish companies**: 25% DWT provides tax credit
- **Foreign companies**: 15% withholding provides credit (US/treaty countries)

## Command options

```bash
python improved_calculator.py [files] [options]

--csv                    Export to CSV files
--margin-rate {20,40,45} Your income tax rate (default: 40%)
--ticker SYMBOL          Analyze specific ticker in detail
```

## Output

**Console report** shows year-by-year:
- Tax liability breakdown (CGT + exit tax + dividend tax)
- Realized gains by ticker
- Current holdings with cost basis

**CSV files** include:
- `irish_tax_report_tax_summary.csv`: Tax calculations by year
- `irish_tax_report_by_ticker.csv`: Detailed ticker breakdown

**Ticker analysis** shows:
- Complete transaction history
- FIFO matching visualization
- Cost basis calculations

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

## Troubleshooting

**"Missing ticker"**: New tickers auto-added to cache via yfinance API.

**Wrong gains**: Check your transaction files have all years - FIFO needs complete history.

**Currency errors**: Ensure FX rates provided for non-EUR transactions.

**Merger issues**: Edit `data/ticker_cache.json` to configure ticker mappings.

## Files created

- `data/ticker_cache.json`: Stores ticker classifications and merger info
- `irish_tax_report_*.csv`: Tax calculations (if using --csv)

## Future plans

Building a web version where you can:
- Upload transactions through a browser
- Get instant tax calculations
- Download tax reports
- No local setup required

## Legal note

This tool calculates taxes based on Irish Revenue guidelines. Always verify with a tax advisor before filing. The tool is for educational purposes and personal use.

## Requirements

- Python 3.9+
- pandas, openpyxl, numpy, yfinance
- Works on macOS, Linux, Windows

Built for Irish residents trading through modern brokers.
