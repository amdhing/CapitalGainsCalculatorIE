# Irish ETF Tax Rules - Specification

Based on authoritative sources (etf.ie, Revenue.ie, Finance Act 2025, MoneyGuideIreland, Fairstone, KPMG).

## 1. ETF Exit Tax

| Period | Rate | Source |
|--------|------|--------|
| Up to 31 Dec 2025 | 41% | Finance Act |
| From 1 Jan 2026 | 38% | Finance Act 2025 |

- Applied to: realized gains, dividends, and deemed disposal gains
- No annual CGT exemption applies (unlike stocks)
- No indexation relief

## 2. No Loss Offsetting Between ETFs ⚠️ CRITICAL

> "Any losses on other ETFs are not available for offset. So if you make a loss of €5,000 on one ETF over 8 years – but make a gain of €10,000 on another over the same period – you will be liable for 38% tax on €10,000."
> — MoneyGuideIreland

- Realized losses on one ETF **cannot** offset realized gains on a different ETF
- Each ETF ticker is taxed independently
- Losses on an ETF are simply forfeited (no loss relief)
- Exception: losses on the **same** ETF ticker can offset gains on that same ticker (net within ticker)

## 3. Deemed Disposal (8-Year Rule) ⚠️ CRITICAL

> "The tax paid [on deemed disposal] acts as a credit against the final tax due when you eventually sell."
> — FinanceTool.ie / DeemedDisposalCalculator.ie

- After 8 years, a "deemed disposal" event occurs
- Tax is calculated on the gain up to that point at the exit tax rate
- The cost basis is **uplifted** to the market value at the 8-year anniversary
- When the shares are later sold, only the gain **since the last deemed disposal** is taxed
- The tax already paid through deemed disposals is credited against the final liability

### Calculation example:
```
Year 0: Buy €10,000
Year 8: Value €12,000 → Deemed gain €2,000 → Tax @ 38% = €760
        Cost basis uplifted to €12,000
Year 10: Sell €13,000 → Remaining gain €1,000 → Tax @ 38% = €380
        Total tax = €760 + €380 = €1,140 = 38% of €3,000 total gain ✓
```

## 4. Dividend Taxation

- **Stock dividends**: Income tax at marginal rate (20%/40%/45%) with withholding credits
  - Irish dividends: 25% DWT credit
  - Foreign dividends: 15% withholding credit (US treaty rate)
- **ETF dividends**: Taxed at exit tax rate (41%/38%), not income tax

## 5. Domicile-Based Dividend Classification

The calculator uses ticker domicile to classify dividends:
- `IE` → Irish dividend (25% DWT credit assumed)
- All other domiciles → Foreign dividend (15% withholding credit assumed)

**Known simplification:** Luxembourg-domiciled ETFs (domicile `LU`) are treated as Foreign dividends with 15% withholding, but in practice Luxembourg funds are tax-transparent with 0% withholding at fund level. This is a conservative overestimate — the actual tax credit due may be lower.

## 6. Offshore funds (Case IV) — non-distributing, outside EU/EEA/OECD

Indian SEBI ETFs (`*BEES`, `GOLDETF`, `ALPHA`) are non-distributing offshore
funds outside the EU/EEA/OECD (India is not an OECD member), so the Chapter 4
"equivalent fund" exit-tax regime does **not** apply. Their disposal gains are
**Case IV income tax** at the marginal rate:

- No €1,270 annual exemption.
- Losses are ignored (Sch 20 para 3(2)) — no offset, no carry-forward.
- No 8-year deemed disposal (that is a Chapter 4 / equivalent-fund rule).
- Non-domiciled taxpayers: only the portion remitted to Ireland is taxable
  (s.745(4)).
- Dividend/look-through (Case III) income is deferred and flagged in the UI.

See `docs/design/offshore_funds.md` for the full classification.

## 7. Current Implementation Status

| Priority | Gap | Impact | Status |
|----------|-----|--------|--------|
| 🔴 High | ETF losses offset gains across tickers | Understates tax liability | ✅ **FIXED** — Each ticker taxed independently via `calculate_etf_exit_tax_per_ticker()` |
| 🔴 High | No cost basis uplift after deemed disposal | Overstates final sale gain | ✅ **FIXED** — Per-lot `uplifted_cost_basis` applied on SELL; historical close prices from yfinance |
| 🟡 Medium | Deemed disposal uses 20% placeholder gain | Inaccurate liability estimate | ✅ **FIXED** — Uses yfinance historical close on anniversary date; falls back to `.DE` suffix for EUR securities; logs `price_unavailable` to backlog on failure |
| 🟡 Medium | No per-lot deemed disposal tracking | Affects partial sells | ✅ **FIXED** — Each buy lot tracks `deemed_years_applied` and `uplifted_cost_basis` |
| 🟢 Low | Deemed disposal year attribution | Liability in wrong year | ✅ **FIXED** — Gain attributed to anniversary year (purchase_date.year + cycles_completed × 8) |

### Status Legend

- ✅ **FIXED** — Issue has been resolved in current codebase
- ⏳ **Still open** — Known limitation, tracked for future improvement
- 🟢 Low / 🟡 Medium / 🔴 High — Priority for resolution
