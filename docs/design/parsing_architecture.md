# Transaction Parsing Architecture — Target State

> Status: **IMPLEMENTED** (core Zerodha work complete)
>
> Source of truth for how multi-broker transaction statements are ingested, normalized, and fed to the tax engine. Revolut is fully supported; Trading 212 explored but deferred; Zerodha is implemented.

---

## 1. Problem

The tax engine (`src/improved_calculator.py::process_transactions`) originally assumed **Revolut's** column layout:

```
Date, Ticker, Type, Quantity, Price per share, Total Amount, Currency, FX Rate
```

Every new broker (Trading 212, Zerodha, Degiro, …) has a different layout. A normalization layer decouples the tax engine from any specific broker format.

## 2. Goal

A **parser layer** turns any broker statement into a single **canonical schema**. The tax engine consumes only the canonical schema and is broker-agnostic.

```
[revolut.csv] ──► RevolutParser ──┐
[trading212.csv] ► Trading212Parser ─┼──► canonical DataFrame ──► tax engine
[zerodha.xlsx] ──► ZerodhaParser ──┘
```

## 3. Canonical schema (normalized internal format)

Every parser emits a `pandas.DataFrame` with these columns:

| Column | Type | Notes |
|---|---|---|
| `Date` | datetime (tz-aware UTC) | transaction date |
| `Ticker` | str | raw broker symbol (uppercased) |
| `Type` | str | canonical: `BUY`, `SELL`, `DIVIDEND`, `MERGER`, `MERGER_STOCK`, `MERGER_CASH`, `TRANSFER` |
| `Quantity` | float | shares |
| `Price per share` | float | in `Currency` units |
| `Total Amount` | float | in `Currency` units (signed) |
| `Currency` | str | ISO code (`EUR`, `USD`, `GBP`, `INR`, …) |
| `FX Rate` | float | units of `Currency` per **1 EUR** (1.0 if EUR) |
| `Source` | str | broker id: `revolut`, `trading212`, `zerodha` |
| `ISIN` | str (nullable) | international security id |

**FX Rate convention:** `convert_to_eur` divides by `FX Rate` for non-EUR. `FX Rate = 90` for INR means €1 = ₹90.

## 4. Parser abstraction

```python
# src/parsing/base.py
class ParsedStatement:
    source: str
    rows: int
    data: pd.DataFrame          # canonical schema
    warnings: list[str]

class StatementParser(ABC):
    source: str
    def can_parse(self, path: str) -> bool: ...
    def parse(self, path: str, inr_per_eur: float | None = None) -> ParsedStatement: ...
```

- `can_parse` returns True iff this parser owns the format (never raises).
- `parse` raises `ParseError` on unparseable input; `warnings` for soft issues.

| Parser | File | Source id | Status |
|---|---|---|---|
| `RevolutParser` | `revolut.py` | `revolut` | ✅ implemented |
| `Trading212Parser` | `trading212.py` | `trading212` | 🟡 stub / deferred |
| `ZerodhaParser` | `zerodha.py` | `zerodha` | ✅ implemented |
| `ZerodhaDividendParser` | `zerodha.py` | `zerodha` | ⏳ deferred (separate report) |

## 5. Detection registry

```python
# src/parsing/registry.py
PARSERS = [ZerodhaParser(), Trading212Parser(), RevolutParser()]

def detect_and_parse(path) -> ParsedStatement: ...
```

Most-specific first; Revolut is the generic CSV/XLSX fallback. Zerodha is detected by an `.xlsx` with header containing `Symbol`, `ISIN`, `Trade Date`, `Trade Type`.

## 6. Zerodha tradebook format (observed)

Five files (`zerodha_fy21.xlsx` … `zerodha_fy25.xlsx`):

- Single sheet `Equity`, header row at ~row 15, first column blank (`None`).
- Columns: `(blank), Symbol, ISIN, Trade Date, Exchange, Segment, Series, Trade Type, Auction, Quantity, Price, Trade ID, Order ID, Order Execution Time`.
- `Trade Type` ∈ `{buy, sell}` (lowercase); `Segment` = `EQ`.
- `Price`/`Quantity` in INR; `Total Amount` = `Quantity × Price`; no FX, no dividends.

**Mapping:**

| Zerodha | Canonical |
|---|---|
| `Symbol` | `Ticker` |
| `Trade Date` | `Date` |
| `Trade Type` | `Type` → `BUY`/`SELL` |
| `Quantity` | `Quantity` |
| `Price` | `Price per share` |
| `Quantity × Price` | `Total Amount` |
| `ISIN` | `ISIN` |
| `"INR"` | `Currency` |
| auto-fetched | `FX Rate` (INR per 1 EUR) |
| `"zerodha"` | `Source` |

## 7. Zerodha asset classification

Zerodha is **Indian equity** (NSE/BSE). Under Irish law:

- Indian stocks → CGT (33%, €1,270 exemption, loss carry-forward) → `type: "stock"`.
- Indian ETFs (`*BEES`, `GOLDETF`, …) are **non-equivalent foreign funds**, generally
  outside the exit-tax regime → CGT (33%, not 41%/38%).

**Classification method (source-aware):** Zerodha symbols are resolved via **`.NS` then `.BO`** suffix with `country == "India"` and `currency == "INR"` validation (bare symbols are ambiguous — e.g. `CUB`→Lionheart Holdings, `WIPRO`→404). On miss, fall back to `type: "stock"`, `currency: "INR"`, `domicile: "IN"`. Non-Zerodha sources keep the existing Revolut fallback (`etf`/`EUR`/`IE`).

**Stock splits:** both backfill paths record `splits` on the cache entry (a list of `{"date", "ratio"}` from yfinance `Ticker.splits`, e.g. `INFY.NS` → 8 events, `RELIANCE.NS` → 4). This feeds future corporate-action handling (adjusting share quantities across a split date); it has no effect on current FIFO math.

## 8. Irish tax applicability — SITUS + DOMICILE driven (broker-agnostic)

> **KEY DESIGN DECISION (revised):** CGT treatment is driven by **security situs**
> (country of the asset) + the **taxpayer's domicile**, *not* the broker.
> Zerodha/Groww/INDMoney are all INR sources of India-situs stock; Revolut /
> Trading 212 carry both Irish-situs and foreign-situs securities. The tax engine
> keys off each ticker's `domicile`, then applies the user's domicile status to
> the *foreign-situs* bucket. No per-broker tax calculators.

> **Legal basis (researched):** Irish law distinguishes by **domicile**, not
> citizenship:
> - **Domiciled** residents → **arising basis**: Irish CGT on worldwide gains.
> - **Non-domiciled** residents → **remittance basis**: foreign-situs gains taxable
>   only to the extent remitted to Ireland.
> - Ireland–India DTAA **Art. 13(6)**: gains from share alienation taxable only in
>   the resident state; Indian CGT withheld is relieved via "prior tax paid" credit.
>
> Sources: PwC Tax Summaries (Ireland), Saffery, Revenue TDM Part 05-01-21a, Ireland–India DTAA Art. 13.

### Inputs

| Input | Type | Meaning |
|---|---|---|
| `tax_residency` | enum | `"irish_resident"` (future: `"non_resident"`) |
| `domicile` | enum | `"domiciled"` \| `"non_domiciled"` |
| `apply_irish_tax` | bool | whether to compute Irish CGT on foreign-situs gains |
| `remitted_foreign_gains_eur` | float | foreign-situs gains remitted to IE (non-dom only) |

### Situs split (core of the tax engine)

`src/foreign_gains.py` splits per-year stock realized gains into:

- **Irish-situs** (domicile == `IE`) → always arising-basis taxable.
- **Foreign-situs** (domicile != `IE`) → domicile-status driven:
  - `domiciled` → full gain taxable (losses flow into normal CGT relief).
  - `non_domiciled` → only gains up to `remitted_foreign_gains_eur` taxable,
    allocated FIFO across years.
- `apply_irish_tax == false` → gains-only report (no Irish CGT).

### Validation rules

- `apply_irish_tax == true` with foreign-situs gains but invalid `domicile` → `400`.
- `non_domiciled` with foreign-situs gains but no `remitted_foreign_gains_eur` → `400`.

## 9. INR → EUR FX conversion

The Zerodha tradebook carries no FX rate. The parser fetches a single current
INR-per-EUR rate from yfinance (`EURINR=X`) and applies it to all Zerodha rows.
Future: per-year (or per-buy-date) RBI reference rates.

## 10. Dividends (Zerodha)

Tradebook contains only buy/sell. Dividends come in a separate corporate-action report — deferred (`ZerodhaDividendParser`).

## 11. Backlog / app_source propagation

`app_source` now reflects the actual `Source` from the parsed statement (e.g. `zerodha`), not a hardcoded `"revolut"`.

## 12. API changes

- `UploadResponse`: unchanged.
- `CalculateRequest` gains optional: `tax_residency`, `domicile`, `apply_irish_tax`,
  `remitted_foreign_gains_eur`.
- `CalculateResponse`: unchanged shape.

## 13. Implementation checklist

- [x] Add `src/parsing/` package (`base.py`, `revolut.py`, `trading212.py`, `zerodha.py`, `registry.py`)
- [x] Implement `ZerodhaParser`
- [x] Make `get_ticker_info` source-aware (`.NS`/`.BO` for Zerodha; placeholder defaults per source)
- [x] Wire `process_file` / `process_multiple_files` to `detect_and_parse`
- [x] Propagate `Source` into backlog/parse-error `app_source`
- [x] Add domicile/remittance inputs to API + validation; auto-fetch INR→EUR from yfinance
- [x] Implement situs split + arising (domiciled) / remittance (non-dom) / gains-only
- [x] Tests: parser unit, detection, situs split, both domicile cases, remittance isolation, validation, source propagation
- [x] Record `splits` on cache entries during ticker backfill (with tests)
- [x] Update `docs/project_spec.md` project structure / input-format sections

## 14. Out of scope (explicit)

- Trading 212 full parser (stub only)
- Zerodha dividends / corporate actions (reserved `ZerodhaDividendParser`)
- Per-year INR FX reference rates
- Automated broker API import (per `future_direction.md` anti-goals)
- Establishing domicile status itself (we take the user's assertion)