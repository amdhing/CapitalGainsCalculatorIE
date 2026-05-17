# Product Future Direction

This document defines where the product is headed. Every feature, PR, or design decision should be evaluated against this document to ensure we move toward the destination, not away from it.

---

## 1. Product Vision

A fast, accurate, stateless capital gains and ETF exit tax calculator for Irish residents. The user uploads their transaction files and gets a clear tax liability breakdown per year, per ticker — ready to fill into their Revenue.ie CGT/ETF forms. We calculate, the user files.

---

## 2. Design Principles

| # | Principle | Why |
|---|-----------|-----|
| 1 | **Stateless-first** | Users get results without creating an account, managing a password, or trusting us with personal data. |
| 2 | **GDPR-minimal** | Don't collect personal data unless there is a clear, revenue-backed justification. Anonymized data is preferred. |
| 3 | **Calculation accuracy over features** | The core job is correct Irish CGT/ETF tax. Every feature must serve that job. |
| 4 | **Exportable results** | Users must always be able to take their data out (CSV, PDF). No vendor lock-in. |
| 5 | **Progressive enhancement** | Start simple. Add complexity only when users ask for it or when the data shows it's needed. |
| 6 | **Transparency** | Show the math — every line item, every rate, every deduction. Users should be able to verify the calculation manually. |

---

## 3. Phased Roadmap

### Phase 1 — Current (Stateless Calculator)
- [x] File upload (CSV/XLSX)
- [x] Per-ticker breakdown with tooltip long names
- [x] Stock CGT calculation (33%, €1,270 exemption, loss carry-forward)
- [x] ETF exit tax calculation (41%/38% deemed disposal)
- [x] Per-year and per-ticker filtering on results
- [x] Currency symbols on monetary values (€ / $)
- [x] Ticker backlog triage for unresolvable symbols
- [x] API-first architecture (FastAPI backend, React frontend)

### Phase 2 — Next (Prior-Year Tax & Shareability)
- [x] Inline prior-year CGT/exit tax paid inputs
- [x] "Already paid" vs "Net due" display after accounting for prior payments
- [ ] Shareable calculation links (`/results/{id}`) — bookmarkable
- [ ] CSV export of calculation results
- [ ] PDF export (optional, low effort using browser print-to-PDF)
- [ ] Loading states and better error handling on frontend

### Phase 3 — Future (Light Persistence)
- [ ] Magic-link email save (no password, no OAuth — like Medium/Notion)
- [ ] Calculation history page (linked to email token)
- [ ] Deferred deep-linking (upload files → get link → come back later to see results)

### Phase 4 — Stretch (Full Accounts)
- [ ] Google OAuth + email/password auth
- [ ] Persistent prior-year tax paid per user
- [ ] Saved transaction history per user
- [ ] Premium tier (advanced features, multiple portfolios, PDF reports)
- [ ] Full GDPR compliance (DPIA, DPA with processors, DPC registration)

---

## 4. Decision Framework

For every new feature or change, ask these questions in order:

1. **Does this improve calculation accuracy?** — If yes, it's high priority. If no, it's a feature request, not a core improvement.
2. **Does this require collecting personal data?** — If yes, is there a clear revenue or retention justification? If not, reject or defer.
3. **Does this work without an account?** — If not, it belongs in Phase 3 or 4, not now.
4. **Can we remove this without breaking the core calculation?** — If no, we've coupled too tightly. Design for optionality.
5. **Are users explicitly asking for this?** — Build for observed demand, not speculative demand. Watch for patterns in support requests, backlog items, and analytics (if any).
6. **Does this increase maintenance burden significantly?** — If yes, the benefit must clearly outweigh the ongoing cost. A solo developer's time is the scarcest resource.

---

## 5. Anti-Goals (What We Won't Do)

These are explicitly out of scope to prevent scope creep:

- **Tax filing / submission to Revenue** — We calculate liability. The user files manually on Revenue.ie. Filing has legal liability implications that require professional tax advisor involvement.
- **Portfolio tracking / management** — We're a transaction-based tax calculator, not a portfolio dashboard. No real-time P&L, no watchlists, no rebalancing advice.
- **Real-time market data** — Ticker information (long name, currency) is a best-effort cache. No live pricing, no exchange rate feeds.
- **Multi-currency conversion** — All calculations are in EUR. Ticker currency (USD, EUR) is informational only on the per-ticker breakdown.
- **Automated transaction import from broker APIs** — Users upload files. We don't connect to Revolut, Trading 212, Degiro, etc. via API. Scope and reliability issues are outsized for a solo project.
- **Tax advice / financial advisory** — We display calculated numbers and the math behind them. We don't advise on tax strategy, relief eligibility, or filing deadlines.

---

## 6. Data Model Evolution

```
Phase 1 (now)         Phase 2            Phase 3              Phase 4
┌──────────────┐     ┌──────────────┐   ┌──────────────┐     ┌──────────────┐
│ calculation  │     │ calculation  │   │ calculation  │     │   user       │
│   - id       │     │   - id       │   │   - id       │     │   - id       │
│   - result   │     │   - prior_   │   │   - email_   │     │   - email    │
│   - timestamp│     │     tax_paid │   │     token    │     │   - name     │
│              │     │   - year     │   │              │     │   - oauth    │
│              │     │   - type     │   │  email_token │     └──────┬───────┘
│              │     │   - amount   │   │   - email    │            │
│              │     └──────────────┘   │   - token    │     ┌──────┴───────┐
│              │                       │   - expires  │     │  user_calcs  │
└──────────────┘                       └──────────────┘     │   - user_id  │
                                                             │   - calcs[]  │
                                                             └──────────────┘
```

Each phase is additive. Phase 2 adds a `prior_tax_paid` input to the calculation request — no new storage. Phase 3 adds a lightweight email token table. Phase 4 adds full user tables with FK relationships.

---

## 7. GDPR Boundary (Current Phase 1)

Since Phase 1 collects **no personal data**:
- No emails
- No names
- No IP logging (beyond what the hosting platform does inherently)
- No cookies beyond the session

**Phase 1 does not trigger GDPR controller obligations.** The calculation data (ticker symbols, amounts, dates) is stored by `calculation_id` — a UUID with no link to a natural person. This is consistent with GDPR Recital 26 (anonymized data is not personal data).

Any Phase 3 or 4 feature that introduces personal data (email, OAuth identity) triggers GDPR compliance requirements:
- Data Protection Impact Assessment (DPIA)
- Privacy Policy
- DPC registration (~€85/year for small controllers)
- Data Processor Agreements (DPAs) with AWS, Auth0 (if used), email provider
- Right to erasure mechanism
- Data breach notification procedure (72-hour)
- Age of consent compliance (16 in Ireland)

These should be costed and scoped before any Phase 3 feature is begun.

---

## Appendix: How to Use This Document

1. **When proposing a feature** — open this doc and check which phase it belongs in. If it's a Phase 3 idea, don't build it now. Write it up as a future consideration.
2. **When reviewing a PR** — ensure the change doesn't violate an anti-goal or add personal data collection without justification.
3. **When evaluating tech choices** — prioritize simplicity, low maintenance, and statelessness. A new dependency should earn its keep.

*Last updated: 17 May 2026*
