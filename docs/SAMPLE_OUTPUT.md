# Sample Irish Capital Gains Calculator Output

This is an example output from the Irish Capital Gains Calculator showing anonymized data for demonstration purposes.

**Command used:**
```bash
python improved_calculator.py trading_2023.xlsx trading_2024.xlsx --margin-rate 40
```

---

## Console Output

```
Loading file: trading_2023.xlsx
Loading file: trading_2024.xlsx
================================================================================
IRISH TAX COMPLIANCE REPORT - CAPITAL GAINS & EXIT TAX
================================================================================

Note: Marginal tax rate used: 40% (use --margin-rate to change)

==================== FINANCIAL YEAR 2023 ====================

IRISH TAX SUMMARY FOR 2023:

--- STOCKS (Capital Gains Tax @ 33%) ---
  Realized Gains (Gross):     € -425.63
  Less: Annual Exemption:     €    0.00
  Taxable Gains (Net):        €    0.00
  CGT Liability (33%):        €    0.00
  Losses Carried Forward:     €  425.63
  Dividends (Irish):          €    0.00
  Dividends (Foreign):        €   28.45

--- ETFs (Exit Tax @ 41%) ---
  Realized Gains:             €    0.00
  Dividends:                  €    0.00
  Deemed Disposal Gains:      €    0.00
  Total Taxable (ETF):        €    0.00
  Exit Tax Liability (41%):   €    0.00

--- TOTAL TAX LIABILITY ---
  Total Tax Due:              €    0.00

--- DIVIDEND INCOME TAX FOR 2023 ---
  Gross Dividend Income:      €   28.45
    Irish Dividends:          €    0.00
    Foreign Dividends:        €   28.45
  Income Tax Due (40%):       €   11.38
  Tax Credits Available:      €    4.27
    Irish DWT Credit (25%):   €    0.00
    Foreign Withholding (15%):€    4.27
  Additional Tax Due:         €    7.11

REALIZED GAINS BREAKDOWN FOR 2023:
------------------------------------------------------------

STOCKS:
  MSFT     | Realized: €  234.67 | Dividends: €  1.23 (IE: €0.00, Foreign: €1.23)
  AAPL     | Realized: €  189.32 | Dividends: €  0.89 (IE: €0.00, Foreign: €0.89)
  GOOGL    | Realized: €   87.45 | Dividends: €  0.00
  NVDA     | Realized: €   45.23 | Dividends: €  0.00
  TSLA     | Realized: €   12.34 | Dividends: €  0.00
  AMD      | Realized: €    0.00 | Dividends: €  2.15 (IE: €0.00, Foreign: €2.15)
  INTC     | Realized: €    0.00 | Dividends: €  1.67 (IE: €0.00, Foreign: €1.67)
  META     | Realized: €   -45.78 | Dividends: €  0.00
  NFLX     | Realized: €  -123.45 | Dividends: €  0.00
  AMZN     | Realized: €  -234.56 | Dividends: €  0.00
  CRM      | Realized: €  -345.67 | Dividends: €  0.00
  PYPL     | Realized: €  -245.18 | Dividends: €  22.51 (IE: €0.00, Foreign: €22.51)

==================== FINANCIAL YEAR 2024 ====================

IRISH TAX SUMMARY FOR 2024:

--- STOCKS (Capital Gains Tax @ 33%) ---
  Realized Gains (Gross):     € 2156.78
  Less: Annual Exemption:     € 1270.00
  Less: Carry Forward Loss:   €  425.63
  Taxable Gains (Net):        €  461.15
  CGT Liability (33%):        €  152.18
  Losses Carried Forward:     €    0.00
  Dividends (Irish):          €    0.00
  Dividends (Foreign):        €   92.34

--- ETFs (Exit Tax @ 41%) ---
  Realized Gains:             €  234.56
  Dividends:                  €   45.78
  Deemed Disposal Gains:      €    0.00
  Total Taxable (ETF):        €  280.34
  Exit Tax Liability (41%):   €  114.94

--- TOTAL TAX LIABILITY ---
  Total Tax Due:              €  267.12

--- DIVIDEND INCOME TAX FOR 2024 ---
  Gross Dividend Income:      €   92.34
    Irish Dividends:          €    0.00
    Foreign Dividends:        €   92.34
  Income Tax Due (40%):       €   36.94
  Tax Credits Available:      €   13.85
    Irish DWT Credit (25%):   €    0.00
    Foreign Withholding (15%):€   13.85
  Additional Tax Due:         €   23.09

REALIZED GAINS BREAKDOWN FOR 2024:
------------------------------------------------------------

STOCKS:
  NVDA     | Realized: €  892.45 | Dividends: €  0.00
  AAPL     | Realized: €  456.78 | Dividends: €  3.45 (IE: €0.00, Foreign: €3.45)
  MSFT     | Realized: €  323.67 | Dividends: €  4.23 (IE: €0.00, Foreign: €4.23)
  GOOGL    | Realized: €  234.89 | Dividends: €  2.78 (IE: €0.00, Foreign: €2.78)
  TSLA     | Realized: €  189.45 | Dividends: €  0.00
  META     | Realized: €  123.78 | Dividends: €  0.00
  AMD      | Realized: €   89.23 | Dividends: €  5.67 (IE: €0.00, Foreign: €5.67)
  NFLX     | Realized: €   67.34 | Dividends: €  0.00
  AMZN     | Realized: €   45.67 | Dividends: €  0.00
  INTC     | Realized: €    0.00 | Dividends: €  8.95 (IE: €0.00, Foreign: €8.95)
  VZ       | Realized: €    0.00 | Dividends: € 15.67 (IE: €0.00, Foreign: €15.67)
  KO       | Realized: €    0.00 | Dividends: € 12.34 (IE: €0.00, Foreign: €12.34)
  PFE      | Realized: €    0.00 | Dividends: € 18.45 (IE: €0.00, Foreign: €18.45)
  T        | Realized: €    0.00 | Dividends: € 16.23 (IE: €0.00, Foreign: €16.23)
  JNJ      | Realized: €    0.00 | Dividends: €  4.57 (IE: €0.00, Foreign: €4.57)
  CRM      | Realized: €  -267.48 | Dividends: €  0.00

ETFs:
  VWCE     | Realized: €  156.78 | Dividends: € 23.45 | Exit Tax: €73.87
  IWDA     | Realized: €   78.45 | Dividends: € 12.67 | Exit Tax: €37.32
  EUNL     | Realized: €   -0.67 | Dividends: €  9.66 | Exit Tax: €3.69

==================== CURRENT HOLDINGS & TAX IMPLICATIONS ====================

CURRENT STOCK HOLDINGS (Subject to CGT @ 33%):
  AAPL     | Shares:    12.50 | Avg Cost: $178.45
  MSFT     | Shares:     8.75 | Avg Cost: $342.67
  GOOGL    | Shares:     3.25 | Avg Cost: $145.89
  NVDA     | Shares:     2.40 | Avg Cost: $267.34
  TSLA     | Shares:     5.60 | Avg Cost: $189.67
  META     | Shares:     4.80 | Avg Cost: $234.56
  AMD      | Shares:    15.30 | Avg Cost: $ 89.45
  INTC     | Shares:    25.70 | Avg Cost: $ 34.67
  VZ       | Shares:    18.50 | Avg Cost: $ 42.78
  KO       | Shares:    22.40 | Avg Cost: $ 56.89
  PFE      | Shares:    35.60 | Avg Cost: $ 28.45
  T        | Shares:    48.90 | Avg Cost: $ 18.67

CURRENT ETF HOLDINGS (Subject to Exit Tax @ 41%):
  VWCE     | Shares:   125.50 | Avg Cost: € 89.45
  IWDA     | Shares:    89.75 | Avg Cost: € 67.89
  EUNL     | Shares:   156.80 | Avg Cost: € 45.67
  VXUS     | Shares:    78.40 | Avg Cost: $ 56.78
  VTI      | Shares:    45.60 | Avg Cost: $234.56

Irish tax summary exported to: irish_tax_report_tax_summary.csv
Ticker-level exported to: irish_tax_report_by_ticker.csv
```

---

## CSV Output Sample

**irish_tax_report_tax_summary.csv:**

| Year | Asset_Type | Realized_Gains_Gross_EUR | CGT_Exemption_Applied_EUR | Carry_Forward_Loss_Used_EUR | Taxable_Gains_Net_EUR | Tax_Rate | Tax_Liability_EUR | Losses_Carried_Forward_EUR | Dividends_Irish_EUR | Dividends_Foreign_EUR |
|------|------------|-------------------------|--------------------------|----------------------------|---------------------|----------|------------------|--------------------------|-------------------|---------------------|
| 2023 | Stocks | -425.63 | 0.00 | 0.00 | 0.00 | 33% | 0.00 | 425.63 | 0.00 | 28.45 |
| 2023 | ETFs | 0.00 | | | 0.00 | 41% | 0.00 | | | |
| 2024 | Stocks | 2156.78 | 1270.00 | 425.63 | 461.15 | 33% | 152.18 | 0.00 | 0.00 | 92.34 |
| 2024 | ETFs | 234.56 | | | 280.34 | 41% | 114.94 | | | |

**irish_tax_report_by_ticker.csv:**

| Year | Ticker | Asset_Type | Realized_Gains_EUR | Dividends_EUR | Dividends_Irish_EUR | Dividends_Foreign_EUR |
|------|--------|------------|-------------------|---------------|-------------------|---------------------|
| 2023 | MSFT | Stocks | 234.67 | 1.23 | 0.00 | 1.23 |
| 2023 | AAPL | Stocks | 189.32 | 0.89 | 0.00 | 0.89 |
| 2023 | PYPL | Stocks | -245.18 | 22.51 | 0.00 | 22.51 |
| 2024 | NVDA | Stocks | 892.45 | 0.00 | 0.00 | 0.00 |
| 2024 | VWCE | Etfs | 156.78 | 23.45 | 0.00 | 0.00 |

---

## Key Features Demonstrated

1. **Multi-year Processing**: Shows 2023 and 2024 data with proper FIFO accounting
2. **Loss Carry Forward**: 2023 loss of €425.63 applied against 2024 gains
3. **Irish Tax Compliance**: 
   - €1,270 annual CGT exemption applied
   - 33% CGT on stocks, 41% exit tax on ETFs
   - Dividend income tax with withholding credits
4. **Professional Output**: Clean formatting ready for tax filing
5. **CSV Export**: Structured data for accountants and tax advisors

**Total Tax Due for 2024**: €267.12 (CGT + Exit Tax) + €23.09 (Additional dividend tax) = €290.21
