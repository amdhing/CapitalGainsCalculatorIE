# Offshore Funds — Taxation of Irish & Foreign Collective Funds

> Status: **IMPLEMENTED** (see §8 checklist)

---

## 1. Problem

The calculator currently models **two** regimes, keyed off each ticker's
`type`:

| `type` | Regime | Rule |
|---|---|---|
| `stock` | CGT | 33% + €1,270 annual exemption + indefinite loss carry-forward |
| `etf` | Irish exit tax | 41% → 38% (2026) + 8-year deemed disposal, no cross-fund loss relief |

This is correct for **Irish-situs shares** and **Irish equivalent funds**, but it
cannot represent **foreign collective funds** (e.g. Indian SEBI-regulated ETFs
such as `NIFTYBEES`, `ITBEES`, `GOLDBEES`), which under Irish law are *offshore
funds* — a statutory category that is neither ordinary shares nor
equivalent-to-Irish funds.

## 2. Authoritative sources

**Statute (TCA 1997):**

| Section | Subject |
|---|---|
| s.743 | "offshore fund" / "material interest" definitions |
| s.741 | Disposal of material interests in **non-qualifying** (non-distributing) offshore funds |
| s.741(3) | deemed disposal on **death** for non-qualifying funds |
| s.744 | "non-qualifying fund" is the **default** (certified distributing funds are the exception) |
| s.745 + Sch 20 | offshore income gain charged to **Case IV**; **no indexation**; **losses ignored** (Sch 20 para 3(2)) |
| s.745(4) | non-domiciled individuals → remittance basis (applies s.29(4)/(5)) |
| s.747A | CGT rate of charge (**40%**) for distributing-fund disposals (Chapter 3) |
| s.747B / s.747E | Chapter 4 (EU/EEA/OECD) regime, 8-year deemed disposal, **38% flat rate** |

**Revenue Tax & Duty Manuals:**

- Part 27-02-01 — funds *outside* EU/EEA/OECD (Chapters 2 & 3)
- Part 27-04-01 — funds *inside* EU/EEA/OECD (Chapter 4)
- Part 27-01A-03 — ETFs (referenced in the frontend HowToGuide)

**Treaty:**

- Ireland–India DTAA **Art. 13(6)** — gains on alienation of movable property
  (incl. ETF units) taxable only in the resident state.
- Ireland–India DTAA **Art. 10(2) / Art. 23(3)** — Indian dividend WHT (≤10%)
  **is** creditable; only India's *underlying corporate tax* on the profits
  behind the dividend is excluded (and is creditable solely to ≥25% corporate
  holders under Art. 23(3)(b)).

**Practitioner commentary:** Saffery Ireland ("Non-domiciled tax"), Chartered
Accountants Ireland (Feb 2021), CPA Accountancy Plus (Sep 2023).

---

## 3. Complete tax classification

There are **four** distinct outcomes for an Irish-resident individual.

### 3.1 Ordinary shares (domicile-agnostic) → CGT 33%

An equity interest in an **operating company** (whose value reflects market
sentiment, not the NAV of an underlying pool) is **not** a "material interest
in an offshore fund". Gains → **CGT 33%** + €1,270 exemption + loss
carry-forward. For foreign-situs shares, DTAA Art. 13(6) assigns the taxing
right to the resident state; the existing `src/foreign_gains.py` situs +
domicile split applies (arising for domiciled; remittance for non-domiciled).

**Key test (TDM 27-02-01 §3.2):** does the investment's value "closely mirror"
the value of the underlying assets? An Indian operating company (Reliance,
Infosys) → *no* → ordinary shares → CGT. An Indian ETF / wrapper → *yes* →
offshore fund.

### 3.2 Equivalent offshore funds (EU/EEA/OECD) → Irish exit tax

A fund "similar in all material respects" to an Irish regulated fund, located in
an **EU/EEA/OECD** state with which Ireland has a DTA → **41% → 38% (2026)**,
8-year deemed disposal (s.747E(6)), no cross-fund loss relief, losses forfeited
(s.747E(3)(a)); s.747E(3)(b) caps total tax across deemed + actual disposals.

### 3.3 Non-equivalent offshore funds (EU/EEA/OECD) → general principles

A fund in EU/EEA/OECD that is *not* equivalent → taxed on **general principles**:
dividends → Case III income tax; gains → **CGT** (33%) (TDM 27-04-01 §4.2).

### 3.4 Offshore funds outside EU/EEA/OECD (e.g. India) → Chapter 2

> India is **not** an OECD member (it is an "OECD Key Partner" since 2007) and
> is outside the EU/EEA, so the 2001+ Chapter 4 regime does **not** apply.

For a fund outside EU/EEA/OECD, the pre-2001 **Chapter 2** rules apply:

| Fund type | Dividends | Disposal gain | Notes |
|---|---|---|---|
| **Distributing** (Revenue-certified, ≥85% income distributed) | Case III income tax | **CGT 40%** (s.747A) | USC/PRSI not on the disposal |
| **Non-distributing** (default; accumulating) | Case III income tax (accrual-based, look-through) | **Case IV income tax** (s.745/Sch 20) | gain on CGT basis but **no indexation**; **losses ignored** (Sch 20 para 3(2)); USC + PRSI apply |

**Indian SEBI ETFs are non-distributing** (s.744 default; accumulating ETFs
never seek Revenue certification). Their disposal gains are **income tax under
Case IV**, not CGT and not the 38% exit-tax rate.

**FTC note (simplifies the build):** under Art. 13(6), ETF units are movable
property (not "shares" within Art. 13(4)/(5) — Indian BeES are trust structures),
so India has **no taxing right on the disposal** — no FTC input is required for
the disposal path. For the (deferred) income path, Indian dividend WHT (≤10%
under Art. 10(2)) **is** creditable under Art. 23(3)(a); only the underlying
corporate tax on the dividend's source profits is excluded (and is creditable
solely to ≥25% corporate holders under Art. 23(3)(b), not to individuals).
Art. 23(3)(a) credits only against "any Irish tax computed by reference to the
same profits", so the credit is **capped at the Irish income tax on that
income** and cannot go negative. Noted because USC/PRSI are out of scope; a
naive credit could otherwise over-credit against a liability that (in the app)
is understated.

> *Domestic Indian-law nuance:* Finance (No. 2) Act 2024 removed gold/silver
> ETFs from the s.50AA "specified mutual fund" definition, so India would levy
> 12.5% LTCG on `GOLDBEES` domestically after 12 months — but Art. 13(6)
> overrides this, so no Irish credit/cost applies. Recorded for completeness.

### 3.5 Domicile — only the remittance basis, not income-vs-CGT

The offshore-fund regime attaches to **residence** + the fund's **location +
distributing status**, not domicile. Domicile determines *when* the foreign
income/gain is taxable:

- **Domiciled** → **arising basis**: full gain/income taxable as it arises.
- **Non-domiciled** → **remittance basis**: foreign-situs income/gains taxable
  only to the extent **remitted** to Ireland.

**Statutory pin:** s.745(4) provides that for "individuals resident or
ordinarily resident but not domiciled in the State", the remittance rules
(s.29(4)/(5)) apply to the offshore income gain. CAI 2021 states the same for
non-distributing funds ("a gain on disposal of units **can qualify for the Irish
remittance regime**").

> **Disambiguation (caution):** CAI 2021 *also* says the remittance basis "does
> not apply" — but that passage concerns **equivalent (Chapter 4)** funds, which
> are excluded from the remittance basis. Indian ETFs are Chapter 2, so the
> remittance basis **does** apply to them.

---

## 4. Design

### 4.1 New cache `type` value

Introduce a single new **`offshore_fund`** type for **non-distributing offshore
funds outside EU/EEA/OECD**. Applicable tickers:

| Ticker | yfinance symbol | domicile |
|---|---|---|
| `NIFTYBEES` | `NIFTYBEES.NS` | `IN` |
| `ITBEES` | `ITBEES.NS` | `IN` |
| `LIQUIDBEES` | `LIQUIDBEES.NS` | `IN` |
| `GOLDETF` | `GOLDBEES.NS` | `IN` |
| `ALPHA` | `ALPHA.NS` | `IN` |

> **Corrected:** `ALPHA` maps to **`ALPHA.NS`** ("Kotak Nifty Alpha 50 ETF").
> `ALPL30IETF.NS` is **ICICI Prudential Life** (a listed insurer, which passes
> the `country=="India"` gate) — a *different* vehicle and **not** this ticker.
> All five return `country=None` from yfinance, which is why the strict gate in
> `ticker_utils._fetch_india_ticker` misses them.

*(An `offshore_fund_equivalent` type for Chapter 4 equivalent funds is deferred
— not required for the Indian scope; those funds are treated as `etf` today.)*

### 4.2 Tax computation — `offshore_fund` (Case IV income tax)

For a disposal of a non-distributing offshore fund:

| Item | Domiciled (arising) | Non-domiciled (remittance) |
|---|---|---|
| Disposal gain | Case IV income tax @ marginal rate (USC + PRSI not modelled — §7) | Only remitted portion taxed |
| Gain basis | CGT-style but **no indexation** | same |
| Losses | **Ignored** (Sch 20 para 3(2)) | same |
| €1,270 exemption | ❌ not available | ❌ |
| CGT loss carry-forward | ❌ | ❌ |
| 8-year deemed disposal | ❌ (Chapter 2 has none) | ❌ |
| Death | deemed disposal (s.741(3)) | same |

> **Corrected:** the 8-year deemed disposal is a **Chapter 4 (equivalent)**
> concept only. Chapter 2 non-distributing funds have a deemed disposal on
> **death** (s.741(3)), not every 8 years. Do **not** reuse the ETF
> deemed-disposal engine for `offshore_fund`.

**Tax rate:** income tax at the user's `margin_rate` (existing input).

### 4.3 Inputs

- `domicile` (`"domiciled" | "non_domiciled"`) — existing.
- `margin_rate` — existing; a pre-computed income-tax slab (**20/40/45**), per
  `src/tax_calculations.py:157`. Applying it to offshore income does **not**
  double-count USC/PRSI — those are unmodelled and out of scope (§7).
- `remitted_offshore_income_eur` — **new, dedicated field** for the Case IV
  income remitted to Ireland (non-domiciled only).

#### Why a dedicated remittance field

`remitted_foreign_gains_eur` already drives the CGT remittance pool in
`src/foreign_gains.py:119-127` via a **single FIFO-draining pool**. Reusing it
for a *different* regime (Case IV income vs CGT gains) would silently share the
pool and make it impossible to express which amounts were remitted. A separate
`remitted_offshore_income_eur` field removes the ambiguity (cheaper than
documenting drain precedence).

For `non_domiciled`, only the remitted portion of the Case IV income is taxable,
consistent with s.745(4).

### 4.4 Distinct from the other regimes

- **vs `stock`**: Case IV income tax (not CGT), no exemption, no loss relief,
  taxed at marginal rate.
- **vs `etf`**: no 8-year deemed disposal; taxed at marginal rate (not 38%);
  eligible for remittance basis for non-doms (whereas equivalent Chapter 4
  funds are **not** remittance-eligible — CAI 2021; Saffery).

---

## 5. Files to touch (implementation)

- `src/ticker_cache.py` — allow `type: "offshore_fund"`.
- `src/improved_calculator.py` — `is_etf` → three-way bucket; add
  `offshore_funds` summary bucket; do **not** reuse ETF deemed disposal.
- `src/tax/offshore_funds.py` — Case IV income-tax path with remittance split
  (see §8 for the `src/tax/` package being introduced).
- `src/tax_calculations.py` — marginal-rate income tax for the offshore bucket.
- `src/api/models.py` / `src/api/routers/calculations.py` — new `TaxLine`
  `asset_type` value.
- `frontend/src/api/client.ts`, `ResultsPane.tsx`, `UploadPane.tsx` — render the
  third bucket; reuse domicile/remittance controls.
- **`frontend/src/components/HowToGuide.tsx`** — currently states Indian ETFs
  are "taxed under ordinary CGT (33%...), like shares" and uses "offshore ETF"
  as a synonym for exit-tax ETFs (citing TDM 27-01a-03). This **contradicts
  §3.4** and must be updated as part of the regime change.
- `data/ticker_cache.json` + `scripts/resolve_remaining_india_tickers.py` —
  retag the five ETFs `type: "offshore_fund"` with correct `yfinance_ticker`
  (incl. `ALPHA → ALPHA.NS`), and finalise corporate actions (Zomato→Eternal,
  3IINFOLTD family, SINTEX delisting, TATAMOTORS demerger, `-RE` entitlements).
- `docs/tax_rules_spec.md`, `docs/design/parsing_architecture.md` — update the
  two-regime descriptions.
- Tests: `tests/test_offshore_funds.py`.

## 6. Resolved open questions

| Question | Answer | Source |
|---|---|---|
| Rate on non-equivalent fund disposal? | Not 38%. Outside EU/EEA/OECD → non-distributing → **Case IV @ marginal rate** (USC + PRSI apply). 38% is Chapter 4 equivalent funds only. | TDM 27-02-01 §5.3; TDM 27-04-01 §4.1.4 |
| Is India an OECD member? | No (OECD Key Partner). | OECD "Members and partners" |
| Is an Indian ETF an "offshore fund"? | Yes — s.743(1) covers any non-Irish company/unit trust with a material interest. | TDM 27-02-01 §3.1 |
| Distributing or non-distributing? | Non-distributing (s.744 default; accumulating ETFs). | s.744; TDM 27-02-01 §3.3 |
| 8-year deemed disposal for Indian ETFs? | **No** — death only (s.741(3)); 8-year rule is Chapter 4. | s.741(3); TDM 27-02-01 §5.3.1 |
| Losses on disposal? | **Ignored** (Sch 20 para 3(2)). | s.745/Sch 20; TDM 27-02-01 §5.3 |
| Remittance basis for non-doms? | **Yes, applies** — s.745(4) (s.29(4)/(5)); CAI's "does not apply" is about Chapter 4 only. | s.745(4); CAI 2021 |
| How are Indian *stocks* taxed? | **CGT 33%** (ordinary shares, value doesn't track NAV). | TDM 27-02-01 §3.2 Ex.2; DTAA Art 13(6) |
| Disposal FTC needed for Indian ETFs? | **No** — Art 13(6) gives India no taxing right on movable-property gains. | DTAA Art 13(6) |
| Indian dividend WHT creditable? | **Yes** (≤10%, Art 10(2)) under Art 23(3)(a); only the underlying corporate tax is excluded (receivable only by ≥25% corporate holders, Art 23(3)(b)). | DTAA Art 10(2), 23(3) |

## 7. Out of scope / simplifications

- **Income (Case III) on non-distributing funds** — taxed on accrual
  (look-through), requiring NAV + fund-income data the transaction pipeline does
  not collect. **Deferred**; the MVP covers disposal gains only, and the UI
  flags this gap.
- **USC and PRSI** on Case IV income (not modelled; understates liability —
  flagged in UI).
- **Distributing-fund** path (CGT via s.747A) — rare; Indian ETFs are
  non-distributing.
- The s.743(2) "reasonably expected to realise within 7 years" / "value tracks
  NAV" determinations — approximated: exchange-traded collective funds →
  `offshore_fund`; operating companies → `stock`.
- Establishing domicile status itself (taken from the user's assertion).

## 8. Implementation checklist

- [x] Allow `type: "offshore_fund"` in `src/ticker_cache.py`
- [x] Replace the `is_etf` boolean with a **three-way classifier**
      (`stock`/`etf`/`offshore_fund`) in `src/improved_calculator.py`.

      > `is_etf` was used at ~7 call sites (`df['IsETF']`, `asset_type =
      > 'etfs' if is_etf else 'stocks'`, and several `if is_etf:`
      > deemed-disposal blocks). A new `asset_kind()` classifier now returns
      > `stock`/`etf`/`offshore_fund`; `is_etf` is `asset_kind == 'etf'`, so
      > offshore funds do **not** reuse the ETF deemed-disposal engine.
      > The placeholder fallthrough remains source-dependent (Revolut → `etf`,
      > Zerodha → `stock`); the five target tickers now carry explicit
      > `type: "offshore_fund"` cache entries so they never reach the fallthrough.
- [x] New `src/tax/offshore_funds.py` — Case IV income-tax path + remittance
      split (s.745(4)) using the dedicated `remitted_offshore_income_eur` field
- [x] `src/tax/tax_calculations.py` — marginal-rate income tax for the offshore bucket
- [x] API: add `remitted_offshore_income_eur` to `CalculateRequest` + validation;
      new `TaxLine` `asset_type` value (and update the `TaxLine` schema table in
      `docs/project_spec.md`)
- [x] Frontend: render the third bucket in `ResultsPane.tsx` + `client.ts`;
      add the new remittance input in `UploadPane.tsx`; correct
      `HowToGuide.tsx`'s "Indian ETFs → CGT" statement
- [x] Add the two UI disclaimers promised in §7 — (a) look-through income
      (Case III) not yet modelled, and (b) USC/PRSI understated — to the
      offshore bucket in `ResultsPane.tsx`
- [x] Retag `NIFTYBEES`/`ITBEES`/`LIQUIDBEES`/`GOLDETF`/`ALPHA` as
      `offshore_fund` with correct `yfinance_ticker` (incl. `ALPHA → ALPHA.NS`),
      and apply corporate actions (Zomato→Eternal, 3IINFOLTD family, SINTEX
      delisting, TATAMOTORS demerger, `-RE` entitlements)
- [x] Tests: add `tests/test_offshore_funds.py` (Case IV, no loss relief,
      remittance split, no 8-year deemed disposal) **and** update the existing
      two-way assertions in `tests/test_calculator_methods.py` +
      `tests/test_calculator_integration.py` (`is_etf` mocks/assertions), and
      fix the already-stale placeholder mock
- [x] Update `docs/tax_rules_spec.md` + `docs/design/parsing_architecture.md`
      **and the two extra stale docs** `docs/README.md:19` ("Indian ETFs… treated
      as stocks") + `docs/project_spec.md` (Indian ETF classification)
- [x] **Create `src/tax/` package** and move the pure tax-domain modules
      (`tax_calculations.py`, `foreign_gains.py`) into it, alongside the new
      `offshore_funds.py` (created directly in `src/tax/`). Leave
      `improved_calculator.py` (engine/CLI) and `ticker_*` at `src/` root.
      - `src/tax/__init__.py` re-exports the three modules.
      - Update importers: `src/improved_calculator.py`,
        `src/api/routers/calculations.py`.
      - Update tests that import via `sys.path.insert(0, src)` to the
        `src.tax.*` path.
      - Update doc references (`docs/*`, `docs/design/*`) to the new paths.
- [x] Verify: `python -m pytest` → **213 passed / 1 known pre-existing failure**
      (`test_final_sale_after_deemed_disposal_with_uplift` — the ETF cost-basis
      uplift bug, out of scope); `npx tsc --noEmit` → clean. The three stale
      `add_missing_ticker_to_cache`-signature mocks were fixed as part of this
      work. The offshore work introduces no new failures.