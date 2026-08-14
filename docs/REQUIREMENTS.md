# Functional Requirements

## P0 — Portfolio lifecycle and accounting

### Portfolio ingress
- Import portfolio data by CSV.
- Upload must work from a mobile browser.
- Support current-holdings CSV import.
- Support transaction CSV import.
- Validate before committing an import.
- Show a reconciliation preview before confirmation.
- Maintain import history.
- Support broker-specific column mappings.
- Allow optional manual transaction entry.

### Transactions
Track at minimum:
- BUY
- SELL
- DIVIDEND
- DEPOSIT
- WITHDRAWAL
- STOCK SPLIT / equivalent corporate action where required by provider/accounting model

Each transaction should retain source/reference metadata when available.

### Historical accounting
- Reconstruct holdings at arbitrary historical dates.
- Calculate cost basis.
- Calculate realised P&L.
- Calculate unrealised P&L.
- Calculate total investment return.
- Preserve historical state.
- Support partial sells.
- Preserve purchase lots.

The exact cost-basis/accounting methodology must be explicitly selected before production use.

## P0 — Market data

Initial implementation should support:
- historical OHLC/adjusted close
- volume
- current/latest available market price appropriate to the daily reporting cadence

Provider interfaces must allow future replacement/addition of providers.

Data collection must support:
- caching
- rate limits
- retries
- missing/stale data detection
- provider/source tracking

## P0 — Analytics

Calculate deterministically:
- daily return
- weekly return
- monthly return
- YTD return
- 1Y return
- portfolio value
- portfolio allocation
- holding weight
- realised/unrealised P&L
- P&L trend
- drawdown
- historical highs/lows
- average volume
- relative volume
- persistent positive/negative sessions
- portfolio contribution
- benchmark comparison where supported

## P1 — Fundamentals and events

Collect where freely available and legally/technically appropriate:
- revenue
- revenue growth
- EPS
- EPS growth
- margins
- free cash flow
- debt
- cash
- earnings dates/results
- guidance
- filings
- material corporate events
- company news
- sector/market context
- selected macro indicators

Provider choice is a separate architecture decision and must be validated against current availability, coverage, licensing, and rate limits.

## P0 — Signal engine

Detect:
- notable daily gain
- notable daily decline
- persistent gain
- persistent decline
- high relative volume
- repeated high-volume movement
- material drawdown
- significant fundamental improvement
- significant fundamental deterioration
- thesis change
- portfolio concentration change
- position drift from target, if targets are configured

Thresholds must be configurable.

## P0 — Reporting

### Daily
- portfolio snapshot
- notable gainers
- notable decliners
- brief reason/context for notable movements
- volume context
- sector/market context
- important events
- early warnings
- upcoming events
- concise overall status

### Weekly
- portfolio performance
- persistent gainers
- persistent decliners
- explanation of persistent moves
- volume persistence
- fundamental developments
- thesis strengthening/weakening
- price/fundamental divergence
- potential opportunities to investigate
- portfolio allocation/concentration changes
- market wrap
- relevant reference levels

### Monthly
- portfolio performance and P&L evolution
- realised vs unrealised P&L
- allocation evolution
- concentration evolution
- performance contribution
- investment-thesis review
- valuation review
- positive opportunities
- risks / items requiring investigation
- broader market environment
- changes since previous month
- concise executive summary

## P0 — LLM

LLM may:
- explain notable price movements
- synthesize news/filings/fundamentals
- assess whether a move appears company/sector/market driven
- explain persistent trends
- assess thesis impact
- summarize market conditions
- identify information that deserves investigation

LLM must not:
- calculate financial metrics
- invent missing facts
- silently turn speculation into fact
- issue autonomous trade execution
- be the source of truth for accounting

LLM output must distinguish evidence from interpretation and uncertainty.

## P1 — UI

Responsive web UI:
- portfolio overview
- holdings
- transaction history
- P&L history
- allocation
- signals
- thesis
- reports
- CSV upload/reconciliation
- historical charts

## P1 — Notifications

Initial:
- Telegram daily report
- Telegram weekly report
- Telegram monthly report

Optional high-priority alerts for exceptional events.

## P2 — Future enhancements

- multiple broker integrations
- advanced benchmarking
- portfolio optimization
- richer macro data
- deeper valuation models
- backtesting of signal usefulness
- additional notification channels
