# 🇮🇪 Irish Capital Gains Calculator

**A comprehensive Python tool for calculating Irish capital gains tax, ETF exit tax, and dividend income tax from Revolut trading transaction data.**

Perfect for Irish tax residents who need to calculate their annual tax obligations from stock and ETF trading. Handles complex scenarios like loss carry forward, mergers, multi-currency transactions, and the 8-year ETF deemed disposal rule.

## 🎯 Why This Tool?

Irish tax law is complex for investors:
- **Stocks**: 33% capital gains tax with €1,270 exemption and indefinite loss carry forward
- **ETFs**: 41% exit tax on everything (gains + dividends) with 8-year deemed disposal
- **Dividends**: Income tax at marginal rate with withholding tax credits
- **Multi-currency**: FX conversions required for EUR reporting

This calculator handles all these complexities automatically using your Revolut transaction exports.

## 🚀 Quick Start

```bash
# Set up environment (one time only)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run with your Revolut export file
python improved_calculator.py revolut_transactions.xlsx

# Try the demo with sample data
python improved_calculator.py samples/sample_revolut_transactions.csv
```

## 📚 Documentation

- **📖 [Full Documentation](docs/README.md)** - Complete user guide and features
- **📊 [Sample Output](docs/SAMPLE_OUTPUT.md)** - See example calculator output
- **📋 [Technical Specification](docs/project_spec.md)** - Implementation details

## 🏗️ Project Structure

```
CapitalGainsCalculatorIE/
├── 📄 README.md                     # This file
├── 🧮 improved_calculator.py        # Main entry point
├── 📦 requirements.txt              # Python dependencies
├── 📄 LICENSE                       # CC BY-NC-SA 4.0 License
├── 🚫 .gitignore                    # Git ignore patterns
├── 📁 src/                          # Source code
│   ├── improved_calculator.py       # Core calculator logic
│   ├── tax_calculations.py          # Irish tax functions
│   └── ticker_utils.py              # Ticker utilities
├── 📁 data/                         # Data files
│   └── ticker_cache.json            # Ticker classification cache
├── 📁 docs/                         # Documentation
│   ├── README.md                    # Full user guide
│   ├── project_spec.md              # Technical specification
│   └── SAMPLE_OUTPUT.md             # Example output
└── 📁 samples/                      # Sample transaction files
    └── sample_revolut_transactions.csv  # Anonymized demo data
```

## ✨ Key Features

- **Irish Tax Compliance**: 33% CGT on stocks, 41% exit tax on ETFs
- **FIFO Accounting**: Proper cost basis calculation across multiple years
- **Loss Carry Forward**: Indefinite carry forward for stock losses
- **Smart Classification**: Auto-detects stocks vs ETFs using yfinance API
- **Multi-currency**: Converts everything to EUR using your FX rates
- **Complex Scenarios**: Handles mergers, inactive stocks, broker transfers

## 🔧 Usage Examples

```bash
# Basic calculation (with Revolut export file)
python improved_calculator.py revolut_transactions.xlsx

# Multiple years with CSV export
python improved_calculator.py revolut_2022.xlsx revolut_2023.xlsx revolut_2024.xlsx --csv

# With dividend tax at your marginal rate
python improved_calculator.py revolut_transactions.xlsx --margin-rate 40

# Analyze specific ticker in detail
python improved_calculator.py revolut_transactions.xlsx --ticker VWCE

# Try with sample Revolut-format data
python improved_calculator.py samples/sample_revolut_transactions.csv
```

## 📋 Input Format (Revolut Transaction Export)

**Note**: This calculator is specifically designed and tested with Revolut transaction exports. Other brokers may have different formats.

Your Revolut Excel/CSV export needs these columns:
- **Date**: Transaction date
- **Ticker**: Stock/ETF symbol (AAPL, VWCE, etc.)
- **Type**: BUY, SELL, DIVIDEND, etc.
- **Quantity**: Number of shares
- **Price per share**: In original currency
- **Total Amount**: Total transaction value
- **Currency**: EUR, USD, etc.
- **FX Rate**: Exchange rate to EUR

## 🇮🇪 Irish Tax Rules Implemented

- **Stock CGT**: 33% rate with €1,270 annual exemption and indefinite loss carry forward
- **ETF Exit Tax**: 41% rate on gains and dividends, 8-year deemed disposal rule
- **Dividend Tax**: Income tax at marginal rate with withholding tax credits

## 📋 Requirements

- Python 3.9+
- Dependencies: pandas, openpyxl, numpy, yfinance
- Works on macOS, Linux, Windows

## 🤝 Contributing

Contributions are welcome! This project uses the Creative Commons BY-NC-SA 4.0 license which allows:
- ✅ Contributions and improvements
- ✅ Personal and educational use
- ❌ Commercial use

Please feel free to:
- Report bugs and issues
- Suggest new features
- Submit pull requests
- Improve documentation

## 📜 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

- ✅ You can use, modify, and share this software
- ✅ You can contribute improvements back to the project
- ❌ You cannot use this software for commercial purposes
- 📄 See [LICENSE](LICENSE) file for full details

## ⚖️ Legal Notice

This tool calculates taxes based on Irish Revenue guidelines. Always verify with a qualified tax advisor before filing. For educational and personal use only.

---

Built for Irish residents trading through modern brokers 🇮🇪
