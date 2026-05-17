"""Backfill long_name and correct domicile for all unresolvable tickers.

Based on web research conducted 17 May 2026.
Run from project root: python scripts/backfill_long_names.py
"""
import json

CACHE_PATH = "data/ticker_cache.json"

# Ticker resolutions: (long_name, domicile correction if needed)
# None for domicile means keep existing
RESOLUTIONS = {
    # --- Stocks with empty long_name ---
    "ERJ": ("Embraer S.A.", None),
    "BRK.B": ("Berkshire Hathaway Inc.", None),
    "DHER": ("Delivery Hero SE", None),
    "ZAL": ("Zalando SE", None),
    "MBG": ("Mercedes-Benz Group AG", None),
    "VOW3": ("Volkswagen AG (Vorzugsaktien)", None),
    "TWTR": ("Twitter, Inc.", None),
    "CLDR": ("Cloudera, Inc.", None),
    "CBLAQ": ("CBL & Associates Properties, Inc.", None),
    "HTZGQ": ("Hertz Global Holdings, Inc.", None),
    "HTZZW": ("Hertz Global Holdings, Inc. Warrants", None),

    # --- ETFs with empty long_name ---
    "QDVY": ("iShares $ Floating Rate Bond UCITS ETF USD Dist", None),
    "36BZ": ("iShares MSCI China A UCITS ETF USD (Acc)", None),
    "IS3K": ("iShares $ Short Duration High Yield Corp Bond UCITS ETF USD (Dist)", None),
    "AMEM": ("Amundi MSCI Emerging Markets Swap UCITS ETF EUR Acc", "LU"),
    "DBXJ": ("Xtrackers MSCI Japan UCITS ETF 1C", "LU"),
    "XUCD": ("Xtrackers MSCI USA Consumer Discretionary UCITS ETF 1D", None),
    "IS3Q": ("iShares Edge MSCI World Quality Factor UCITS ETF USD (Acc)", None),
    "XDWT": ("Xtrackers MSCI World Information Technology UCITS ETF 1C", None),
    "IUSU": ("iShares S&P 500 Utilities Sector UCITS ETF USD (Acc)", None),
    "VWCE": ("Vanguard FTSE All-World UCITS ETF (USD) Accumulating", None),
    "AMEL": ("Amundi MSCI Emerging Markets Latin America UCITS ETF EUR (C)", "LU"),
    "79U0": ("iShares Core MSCI World UCITS ETF USD (Acc)", None),
    "LEMA": ("Amundi Core MSCI Emerging Markets Swap UCITS ETF Acc", "LU"),
    "LYP6": ("Amundi Core Stoxx Europe 600 UCITS ETF Acc", "LU"),
    "PRAJ": ("Amundi Prime Japan UCITS ETF DR (C)", "LU"),
    "EBUY": ("Amundi MSCI Digital Economy UCITS ETF Acc", "LU"),
    "LYMS": ("Amundi Core Nasdaq-100 Swap UCITS ETF Acc", "LU"),
    "XDWI": ("Xtrackers MSCI World Industrials UCITS ETF 1C", None),
    "2B72": ("iShares MSCI Europe Mid Cap UCITS ETF EUR (Acc)", None),
    "WELK": ("Amundi S&P World Financials Screened UCITS ETF Acc", None),
    "LYP5": ("Amundi Core S&P 500 Swap UCITS ETF Acc", "LU"),
    "UBUD": ("UBS Solactive Global Pure Gold Miners UCITS ETF USD Dis", None),
    "LGQK": ("iShares MSCI World SRI UCITS ETF EUR (Acc)", None),
    "EXI2": ("iShares Dow Jones Global Titans 50 UCITS ETF (DE)", "DE"),
    "EUNA": ("iShares STOXX Europe 50 UCITS ETF EUR Dist", None),
    "IQQC": ("iShares China Large Cap UCITS ETF USD Dist", None),
    "EXW1": ("iShares EURO STOXX 50 UCITS ETF (DE)", None),
    "IBCD": ("iShares iBonds Mar 2020 Term Corporate ex-Financials UCITS ETF", None),
    "IBCC": ("iShares iBonds Mar 2018 Term Corporate ex-Financials UCITS ETF", None),
}


def main():
    with open(CACHE_PATH) as f:
        cache = json.load(f)

    updated = []
    for ticker, (long_name, new_domicile) in sorted(RESOLUTIONS.items()):
        if ticker in cache:
            entry = cache[ticker]
            old_name = entry.get("long_name", "")
            old_dom = entry.get("domicile", "")
            entry["long_name"] = long_name
            if new_domicile:
                entry["domicile"] = new_domicile
            updated.append((ticker, old_name, old_dom, long_name, new_domicile or old_dom))
        else:
            print(f"  WARNING: {ticker} not found in cache!")

    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
        f.write("\n")

    print(f"Updated {len(updated)} tickers in {CACHE_PATH}")
    print()
    for ticker, old_name, old_dom, new_name, new_dom in updated:
        changed = []
        if old_name != new_name:
            changed.append(f"name: '{old_name}' → '{new_name}'")
        if old_dom != new_dom:
            changed.append(f"domicile: {old_dom} → {new_dom}")
        print(f"  {ticker}: {'; '.join(changed)}")


if __name__ == "__main__":
    main()
