# Runbook: Ticker Backlog Triage

This runbook describes how an operator or automated agent resolves tickers that the app could not identify via yfinance. The goal is to correct `data/ticker_cache.json` entries, clear the backlog, and verify the changes propagate to the frontend.

---

## Overview of the flow

```
User uploads trades ──► Calculator runs ──► Lookup ticker
                                                │
                                    ┌───────────┴───────────┐
                                    ▼                       ▼
                           Cache hit (long_name)    Cache miss or
                           ───► return directly      empty long_name
                                                      │
                                                      ▼
                                              Check backlog (DynamoDB)
                                                      │
                                          ┌───────────┴───────────┐
                                          ▼                       ▼
                                    Backlogged ──► return       Try yfinance
                                    unresolvable                  │
                                                      ┌───────────┴───────────┐
                                                      ▼                       ▼
                                                Success ──► update        404 / error
                                                cache + return         ──► add to backlog
```

When a ticker lands in the backlog, it means:
- yfinance returned a 404 or error
- The cache either has no entry, or has an entry with an empty `long_name`
- The DynamoDB `ticker-backlog` table records it with an `encounter_count` (incremented each time the app hits it)

---

## Step 1: View the backlog

### Via API

```bash
curl http://localhost:8000/api/backlog
```

Returns:
```json
{
  "backlog": [
    {
      "ticker": "EXI2",
      "encounter_count": 3,
      "app_source": "revolut",
      "status": "unresolvable",
      "timestamp": 1779029072,
      "last_seen": 1779029130
    }
  ],
  "total": 13
}
```

### Via DynamoDB directly

```bash
python3 -c "
from src.api.db import list_backlog
for item in sorted(list_backlog(), key=lambda x: x['encounter_count'], reverse=True):
    print(f\"{item['ticker']}  count={item['encounter_count']}  last_seen={item['last_seen']}  source={item['app_source']}\")
"
```

**Fields:**
- `ticker` — the symbol that couldn't be resolved
- `encounter_count` — number of times the app has hit this ticker (higher = more impactful to fix)
- `last_seen` — Unix timestamp of the most recent encounter
- `app_source` — where the ticker came from (e.g. `revolut`)
- `status` — always `unresolvable` initially

---

## Step 2: Research the ticker

Determine the correct details for the ticker:

| Field | Purpose | Example |
|---|---|---|
| `long_name` | Display name for tooltips in frontend | `"iShares MSCI World UCITS ETF"` |
| `type` | `"stock"` or `"etf"` | Controls CGT (33%) vs exit tax (41%/38%) |
| `currency` | Trading currency | `"EUR"`, `"USD"` |
| `domicile` | Country of incorporation | `"IE"`, `"US"`, `"DE"` |
| `withholding_tax_deducted` | Whether withholding tax applies | `true` for US stocks, `false` for Irish ETFs |
| `active` | Whether the ticker is still trading | `true` or `false` |
| `merged_into` | If inactive, what it merged into | `null` or target ticker |

### Useful data sources

- **For ETFs:** Check the provider's factsheet (iShares, Xtrackers, Vanguard, etc.)
  - Example: `IS3Q` → iShares website → "iShares MSCI World UCITS ETF"
  - Xetra & Deutsche Börse listings often use ISIN-based symbols
- **For stocks:** Yahoo Finance, company investor relations
- **Ticker symbols on Xetra/Tradegate:** Often ISIN-derived codes like `LYP6`, `2B72`
  - Search the ISIN on the ETF provider's site to find the full name
- **ISIN lookup:** Search the ISIN on a financial data site to identify the product

---

## Step 3: Update the cache

### Option A — Manual edit (fast for one-off fixes)

Edit `data/ticker_cache.json` directly. Find or add the ticker entry:

```json
{
  "EXI2": {
    "type": "etf",
    "currency": "EUR",
    "active": true,
    "merged_into": null,
    "conversion_ratio": 1.0,
    "withholding_tax_deducted": false,
    "domicile": "IE",
    "long_name": "iShares MSCI Europe UCITS ETF"
  }
}
```

**Important:** The `long_name` field is what the frontend shows. Without it, the ticker will keep falling through to yfinance and re-enter the backlog.

### Option B — Programmatic update (for agent automation)

```python
import json

cache = json.load(open("data/ticker_cache.json"))

# Example: update an ETF ticker with correct info
cache["EXI2"] = {
    "type": "etf",
    "currency": "EUR",
    "active": True,
    "merged_into": None,
    "conversion_ratio": 1.0,
    "withholding_tax_deducted": False,
    "domicile": "IE",
    "long_name": "iShares MSCI Europe UCITS ETF",
}

json.dump(cache, open("data/ticker_cache.json", "w"), indent=2)
```

---

## Step 4: Clear the backlog entry

Once the cache is updated, remove the ticker from the DynamoDB backlog so the app will retry the lookup (which will now hit the cache and succeed).

### Via API

```bash
# Remove a single ticker
curl -X DELETE http://localhost:8000/api/backlog/EXI2

# Remove all tickers (iterate over the list)
python3 -c "
from src.api.db import list_backlog, backlog_table
for item in list_backlog():
    backlog_table.delete_item(Key={'ticker': item['ticker']})
    print(f'Removed {item[\"ticker\"]} from backlog')
"
```

### Via DynamoDB directly

```python
from src.api.db import backlog_table
backlog_table.delete_item(Key={"ticker": "EXI2"})
```

---

## Step 5: Verify the fix

### Check the API returns the updated info

```bash
curl http://localhost:8000/api/ticker/EXI2
```

Expected:
```json
{
  "symbol": "EXI2",
  "type": "etf",
  "currency": "EUR",
  "active": true,
  "domicile": "IE",
  "withholding_tax_deducted": false,
  "merged_into": null,
  "long_name": "iShares MSCI Europe UCITS ETF",
  "unresolvable": false
}
```

### Verify the backend is using the local cache (no yfinance call)

The response comes from `data/ticker_cache.json` directly — no yfinance involved. The `long_name` field confirms the cache entry is being used.

### Check the backlog is empty for this ticker

```bash
curl http://localhost:8000/api/backlog | python3 -m json.tool
```

### Re-run a calculation to confirm the frontend shows the name

Upload a file containing the fixed ticker via the UI. The ticker breakdown table should now show the `long_name` in the tooltip instead of "unavailable".

---

## Batch processing workflow

For an agent processing the entire backlog:

```python
import json
from src.api.db import list_backlog, backlog_table

# 1. Get all backlogged tickers
backlog = list_backlog()

# 2. For each ticker, determine the correct info
for item in backlog:
    ticker = item["ticker"]
    # ... research and determine correct values ...

    # 3. Update cache
    cache = json.load(open("data/ticker_cache.json"))
    cache[ticker]["long_name"] = resolved_name
    json.dump(cache, open("data/ticker_cache.json", "w"), indent=2)

    # 4. Remove from backlog
    backlog_table.delete_item(Key={"ticker": ticker})

    # 5. (optional) Verify via API
```

---

## Common patterns

| Situation | Cache update needed | Notes |
|---|---|---|
| **ETF trading on Xetra with ISIN-based code** | Set `type: "etf"`, `currency: "EUR"`, `domicile: "IE"` or `"LU"` | Many Xetra-listed ETFs have codes like LYP6, 2B72, LGQK |
| **US stock trading on Revolut** | Set `type: "stock"`, `currency: "USD"`, `domicile: "US"`, `withholding_tax_deducted: true` | Standard for NYSE/Nasdaq stocks |
| **German stock (e.g. Deutsche Börse)** | Set `type: "stock"`, `currency: "EUR"`, `domicile: "DE"`, `withholding_tax_deducted: false` | German withholding tax (26.375%) may apply depending on broker setup |
| **Inactive/merged ticker** | Set `active: false`, `merged_into: "NEW_TICKER"`, set `conversion_ratio` | Calculator uses this for FIFO continuity |
| **Ticker that no longer exists (bankruptcy)** | Set `active: false`, leave `merged_into: null` | Calculator treats as a total loss |

---

## Key files & their roles

| File | Role | When to update |
|---|---|---|
| `data/ticker_cache.json` | Primary ticker data source | Every time you resolve a ticker |
| DynamoDB `ticker-backlog` | Tracks unresolvable tickers | Remove entry after cache update |
| `src/ticker_utils.py` | Logic for adding new tickers to cache | Only if changing lookup behaviour |
| `src/api/routers/tickers.py` | API endpoint for ticker info | Only if changing response format |
| `src/api/routers/calculations.py` | Resolves long_name during calculations | Only if changing resolution logic |

## Verification checklist

- [ ] Cache entry has the correct `long_name`, `type`, `currency`, `domicile`, and `withholding_tax_deducted`
- [ ] Backlog entry for this ticker has been deleted
- [ ] `GET /api/ticker/{symbol}` returns the expected data with `unresolvable: false`
- [ ] Frontend tooltip shows the long name (not "unavailable")
- [ ] Tax rate is correct for the asset type (CGT vs exit tax)
