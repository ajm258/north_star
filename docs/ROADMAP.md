# Development Roadmap

## Sprint 0 — Foundation

Goal:
- repository skeleton
- runtime
- configuration
- logging
- database choice
- migrations
- API skeleton
- testing framework
- Docker/Compose
- CI

Acceptance:
- application starts
- health endpoint works
- tests run
- migration workflow works

---

## Sprint 1 — Portfolio ingestion

Goal:
- CSV import from mobile
- current holdings import
- transaction import
- validation
- reconciliation preview
- import history
- broker mapping abstraction

Acceptance:
- upload CSV
- show detected additions/increases/reductions/removals
- confirm and persist
- reject invalid input safely

---

## Sprint 2 — Portfolio accounting and P&L

Goal:
- transaction ledger
- lots
- cost basis
- realised P&L
- unrealised P&L
- dividends
- deposits/withdrawals
- historical reconstruction
- snapshots

Acceptance:
- deterministic test cases reproduce expected historical holdings and P&L

This sprint is high-risk and requires strong tests.

---

## Sprint 3 — Historical market data

Goal:
- provider abstraction
- initial free provider(s)
- OHLC/adjusted close
- volume
- caching
- rate-limit handling
- retries
- historical data persistence

Acceptance:
- portfolio holdings can be valued for historical dates

---

## Sprint 4 — Analytics

Goal:
- returns
- drawdowns
- volume analytics
- allocation
- concentration
- contribution
- P&L trend
- benchmarks

Acceptance:
- deterministic analytics available without an LLM

---

## Sprint 5 — Signal engine

Goal:
- price signals
- volume signals
- persistence
- drawdown
- portfolio signals
- configurable thresholds

Acceptance:
- synthetic datasets trigger expected signals and do not trigger false signals outside thresholds

---

## Sprint 6 — Fundamentals/events/news

Goal:
- provider abstractions
- initial free data sources
- fundamentals
- earnings
- filings
- news
- market/sector context
- macro

Acceptance:
- normalized data stored with source/timestamp metadata
- provider failures do not corrupt the portfolio database

---

## Sprint 7 — LLM intelligence

Goal:
- LLM client abstraction
- provider fallback
- structured prompts/output
- movement explanation
- persistent trend explanation
- thesis analysis
- market analysis
- output validation

Acceptance:
- representative signals produce structured, concise, evidence-grounded assessments

---

## Sprint 8 — Daily and weekly reports

Goal:
- daily report
- weekly report
- Telegram delivery
- report persistence/archive

Acceptance:
- reports are generated deterministically from known test fixtures
- LLM is invoked only where expected

---

## Sprint 9 — Monthly portfolio intelligence

Goal:
- monthly performance
- P&L evolution
- allocation/concentration
- thesis review
- valuation
- opportunities
- risks
- market wrap

Acceptance:
- monthly report explains portfolio evolution and changes since previous month

---

## Sprint 10 — Dashboard and production hardening

Goal:
- responsive dashboard
- mobile CSV upload
- charts
- report archive
- authentication
- monitoring
- backups
- operational documentation

Acceptance:
- safe everyday use from desktop and phone

## Task workflow

For every sprint:
1. Break sprint into small implementation tasks.
2. Ask Codex to inspect relevant docs and propose a plan.
3. Review plan before implementation.
4. Implement one logical task at a time.
5. Run tests.
6. Perform Codex self-review.
7. Perform independent review where appropriate.
8. Human review/acceptance.
9. Merge.
10. Update roadmap and decision records.

Do not ask an agent to implement an entire sprint blindly.
