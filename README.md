# 🇮🇪 Irish Capital Gains Calculator

**Calculate Irish capital gains tax, ETF exit tax, and dividend income tax from Revolut trading transaction data.** Available as a CLI tool and a web app (FastAPI + React).

Handles complex scenarios like loss carry forward, mergers, multi-currency, and the 8-year ETF deemed disposal rule with proper Revenue.ie-compliant calculations.

## 🚀 Quick Start

### CLI
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python improved_calculator.py samples/sample_revolut_transactions.csv
```

### Web App
```bash
# Terminal 1 — backend
cd src/api && uvicorn main:app --reload --port 8000
# Terminal 2 — frontend
cd frontend && npm install && npm run dev
```
Open `http://localhost:5173`

## 📚 Documentation

| Document | What it covers |
|----------|----------------|
| **[📖 User Guide](docs/README.md)** | Full CLI & web app usage, input format, tax rules, advanced features, troubleshooting |
| **[📊 Sample Output](docs/SAMPLE_OUTPUT.md)** | Example console output with Deemed/Deemed Pd columns |
| **[📋 Technical Spec](docs/project_spec.md)** | Architecture, API models, project structure |
| **[📜 Tax Rules Spec](docs/tax_rules_spec.md)** | ETF exit tax rules, implementation status |
| **[🔮 Future Direction](docs/design/future_direction.md)** | Product roadmap, design principles |
| **[🏗️ Contributing](CONTRIBUTING.md)** | How to contribute, dev setup, PR process |

## 🏗️ Project Structure

```
CapitalGainsCalculatorIE/
├── improved_calculator.py        # CLI entry point
├── src/                          # Python source
│   ├── improved_calculator.py    # Core calculator logic
│   ├── tax_calculations.py       # Irish tax functions
│   ├── ticker_utils.py           # Ticker cache + yfinance
│   └── api/                      # FastAPI backend
│       ├── main.py, models.py, db.py
│       └── routers/calculations.py, tickers.py
├── frontend/                     # React (Mantine UI) web app
│   └── src/
│       ├── App.tsx, main.tsx
│       ├── api/client.ts
│       └── components/UploadPane, ResultsPane, HowToGuide
├── data/ticker_cache.json        # Ticker classification cache
├── docs/                         # All documentation
├── samples/                      # Sample Revolut transaction data
└── tests/                        # 143 unit tests
```

## ✨ Key Features

- **Irish Tax Compliance**: 33% CGT on stocks, 41%/38% exit tax on ETFs
- **FIFO Accounting**: Proper cost basis across multiple years
- **Loss Carry Forward**: Indefinite for stock losses (Irish law compliant)
- **Deemed Disposal**: 8-year rule with per-anniversary-year attribution
- **Prior Tax Paid**: Editable inputs for already-paid and deemed-paid amounts
- **Smart Classification**: Auto-detects stocks vs ETFs via yfinance API
- **Multi-currency**: Converts to EUR using your FX rates
- **Web App**: Interactive tax tables, per-ticker filtering, recalculate with prior tax

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for bug reports, feature requests, and pull request guidelines.

## 📜 License

[CC BY-NC-SA 4.0](LICENSE) — personal and educational use permitted, commercial use prohibited.

## ⚖️ Legal Notice

This tool calculates taxes based on Irish Revenue guidelines. Always verify with a qualified tax advisor before filing. For educational and personal use only.
