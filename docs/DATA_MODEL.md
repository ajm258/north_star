# Data Model

## Sprint 0 schema contract

The PostgreSQL migration introduces `portfolios`, `portfolio_accounts`, `securities`, `security_listings`, `transactions`, `opening_positions`, `opening_cash_balances`, `lots`, `lot_allocations`, `cash_ledger`, `corporate_actions`, `imports`, `import_rows`, `broker_mappings`, `holdings`, historical market/FX/snapshot models, intelligence/report models, and `job_runs`.

Financial amounts and quantities use `NUMERIC(28, 10)`. IDs are immutable UUID-shaped strings. Timestamps are timezone-aware. The exact implemented model is in `portfolio_intelligence/domain/models.py`; this document remains the conceptual reference.

`security_listings` holds ticker, exchange, MIC, currency, and active dates. A ticker is never used as a portfolio-accounting foreign key. `lots` may originate from a transaction or an explicit opening position; a sale records allocations to consumed lots.

This is the initial conceptual model. Exact schema and database technology can be decided during Sprint 0.

## portfolio_accounts

- id
- name
- broker
- base_currency
- created_at
- updated_at

## transactions

Immutable financial events where practical.

- id
- account_id
- transaction_date
- ticker/security_id
- action
- quantity
- price
- gross_amount
- fees
- tax
- currency
- external_reference
- source
- imported_at

## lots

Purchase lots used for cost-basis and realised-P&L calculations.

- id
- originating_transaction_id
- ticker/security_id
- acquisition_date
- original_quantity
- remaining_quantity
- unit_cost
- currency

## holdings

Derived current state.

- ticker/security_id
- quantity
- cost_basis
- average_cost (if useful)
- current_price
- market_value
- unrealised_pnl
- unrealised_pnl_pct
- portfolio_weight
- as_of

## portfolio_snapshots

Portfolio-level historical state.

- snapshot_date
- portfolio_value
- invested_capital
- cash
- realised_pnl
- unrealised_pnl
- total_pnl
- currency

## holding_snapshots

Per-holding historical state.

- snapshot_date
- ticker/security_id
- quantity
- market_value
- cost_basis
- realised_pnl_to_date where appropriate
- unrealised_pnl
- portfolio_weight
- price

## price_history

- security_id
- date
- open
- high
- low
- close
- adjusted_close
- volume
- currency
- provider
- retrieved_at

## fundamentals

Versioned/time-aware financial observations.

Potential fields:
- period
- revenue
- revenue_growth
- eps
- eps_growth
- gross_margin
- operating_margin
- free_cash_flow
- debt
- cash
- shares_outstanding
- provider
- source_date
- retrieved_at

## investment_theses

- ticker/security_id
- thesis_text
- key_growth_drivers
- competitive_advantages
- key_risks
- valuation_rationale
- created_at
- updated_at

Prefer structured fields where practical, while allowing free text.

## signals

- id
- security_id or portfolio_id
- detected_at
- signal_type
- direction
- severity
- metric
- observed_value
- baseline_value
- description
- evidence_reference
- status

## events

- security_id or market scope
- event_date
- event_type
- title
- summary
- source
- source_url
- retrieved_at

## llm_assessments

- id
- scope (security/portfolio/market)
- scope_id
- analysis_type
- created_at
- model
- provider
- prompt_version
- input_hash
- structured_output
- confidence
- status

## reports

- report_type
- period_start
- period_end
- created_at
- report_version
- content
- delivery_status

## imports

- id
- filename
- import_type
- source
- imported_at
- row_count
- accepted_count
- rejected_count
- reconciliation_summary
- status

## Design rule

Historical records should be append-only or versioned wherever practical. Corrections should create auditable changes rather than silently mutating the past.
