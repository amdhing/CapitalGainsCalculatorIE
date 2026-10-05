# 🇮🇪 Irish Capital Gains Calculator

**Calculate Irish capital gains tax, ETF exit tax, and dividend income tax from trading data across brokers.** Available as a CLI tool and a web app (FastAPI + React).

Supports Revolut (CSV/XLSX) and Zerodha (Indian NSE/BSE tradebook) transaction files, with a broker-agnostic tax engine. Handles complex scenarios like loss carry forward, mergers, multi-currency, domicile/remittance basis, and the 8-year ETF deemed disposal rule with Revenue.ie-compliant calculations.

## 🚀 Quick Start

### CLI
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python improved_calculator.py samples/sample_revolut_transactions.csv
```

### Web App
```bash
# Terminal 1 — backend (run from project root)
uvicorn src.api.main:app --reload --port 8000
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
| **[🧩 Parsing Architecture](docs/design/parsing_architecture.md)** | Multi-broker parsing & situs/domicile tax design |
| **[🔮 Future Direction](docs/design/future_direction.md)** | Product roadmap, design principles |
| **[🏗️ Contributing](CONTRIBUTING.md)** | How to contribute, dev setup, PR process |

## 🏗️ Project Structure

```
CapitalGainsCalculatorIE/
├── improved_calculator.py        # CLI entry point
├── src/                          # Python source
│   ├── improved_calculator.py    # Core calculator logic
│   ├── tax/                      # Pure tax-domain modules
│   │   ├── tax_calculations.py   # CGT / ETF exit-tax / income-tax primitives
│   │   ├── foreign_gains.py      # Situs/domicile-driven CGT logic
│   │   └── offshore_funds.py     # Case IV income tax on offshore funds
│   ├── ticker_utils.py           # Ticker cache + yfinance
│   ├── parsing/                  # Broker parsers (revolut, trading212, zerodha)
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
├── samples/                      # Sample Revolut & Zerodha data
└── tests/                        # Python unit tests
```

## ✨ Key Features

- **Irish Tax Compliance**: 33% CGT on stocks, 41%/38% exit tax on equivalent funds, Case IV income tax on offshore funds
- **FIFO Accounting**: Proper cost basis across multiple years
- **Loss Carry Forward**: Indefinite for stock losses (Irish law compliant)
- **Deemed Disposal**: 8-year rule with per-anniversary-year attribution
- **Prior Tax Paid**: Editable inputs for already-paid and deemed-paid amounts
- **Smart Classification**: Auto-detects stocks vs ETFs via yfinance API
- **Multi-currency**: Converts to EUR (INR auto-fetched for Zerodha)
- **Multi-broker**: Revolut + Zerodha (Trading 212 planned)
- **Domicile-aware**: arising vs remittance basis for foreign-situs gains
- **Web App**: Interactive tax tables, per-source summaries & charts, per-ticker filtering, recalculate with prior tax

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
