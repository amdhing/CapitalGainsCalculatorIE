# Irish Capital Gains Calculator - Project Spec

## What it does
Calculates Irish capital gains tax and dividend income tax from trading spreadsheets. Built for Irish tax compliance with proper FIFO accounting and Revenue.ie guidelines.

## Key features
- **FIFO cost basis** across multiple years
- **Loss carry forward** (indefinite, as per Irish law)
- **Stock CGT** at 33% with €1,270 annual exemption
- **ETF exit tax** at 41% (gains + dividends + 8-year deemed disposal)
- **Dividend income tax** at your marginal rate (20%/40%/45%)
- **Multi-currency** support with EUR conversion
- **Smart ticker detection** using yfinance API with local caching
- **Merger handling** for ticker changes and corporate actions
- **CSV export** for tax filing

## Input format
Excel/CSV files with columns:
- Date, Ticker, Type, Quantity, Price per share, Total Amount, Currency, FX Rate

Handles transaction types: BUY, SELL, DIVIDEND, MERGER, TRANSFER
Ignores: CASH TOP-UP, CASH WITHDRAWAL, CUSTODY FEE

## Tax calculations

### Stocks (CGT @ 33%)
1. Apply €1,270 annual exemption
2. Apply carried forward losses from previous years
3. Calculate 33% tax on remaining gains
4. Carry forward any net losses to future years

### ETFs (Exit Tax @ 41%)
- 41% tax on all gains, dividends, and deemed disposals
- 8-year deemed disposal rule applies
- No annual exemption, no loss relief

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

## Usage
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

## Output
- **Console**: Year-by-year tax breakdown with ticker details
- **CSV**: Tax summary and ticker-level data for tax filing
- **Ticker detail**: Transaction history and FIFO matching

## Future scope
Web application where users can:
- Create accounts
- Upload transaction files
- Get automated tax calculations
- Download tax reports

## Dependencies
- pandas, openpyxl, numpy, yfinance
- Python 3.9+ recommended

Built for Irish residents trading stocks and ETFs through brokers like Revolut, Trading 212, etc.
