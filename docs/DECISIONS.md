# Architecture Decision Log

This file records decisions that affect product semantics or architecture.

## ADR-001 — Decision-support, not automated trading

Status: Accepted

The system will provide evidence and context for human portfolio decisions. It will not execute trades or make binary Buy/Sell decisions as its primary function.

Reason:
The portfolio is long/medium-term and the goal is to avoid information blind spots rather than trade short-term movements.

## ADR-002 — Deterministic analytics before LLM

Status: Accepted

All financial calculations and signal thresholds are deterministic. The LLM interprets structured evidence.

Reason:
Financial correctness and reproducibility.

## ADR-003 — Transactions as accounting source of truth

Status: Accepted

Transaction history is preserved and used to reconstruct holdings and P&L.

Reason:
Historical P&L and portfolio state must remain reconstructable.

## ADR-004 — CSV as primary initial portfolio ingress

Status: Accepted

The first ingestion mechanism is CSV upload, including mobile upload.

Reason:
Simple, broker-agnostic, easy to use from a phone.

## ADR-005 — Preserve both upside and downside detection

Status: Accepted

The signal system must be directionally symmetric.

Reason:
The system should surface accumulation opportunities and improving theses as actively as deterioration.

## ADR-006 — Progressive analysis

Status: Accepted

One-day movements get concise context; persistent/material movements receive deeper analysis.

Reason:
Avoid LLM cost and report noise while still catching meaningful trends.

## ADR-007 — Modular monolith initially

Status: Accepted

Start with one application with modular internal components.

Reason:
Reduces operational complexity until scaling or isolation requirements are demonstrated.

## Open decisions

The following require explicit decisions before production use:

1. Database engine: SQLite initially vs PostgreSQL from the beginning.
2. Cost-basis method: FIFO, average cost, or other.
3. Tax treatment and whether tax calculations are in scope.
4. Currency conversion methodology and FX data source.
5. Exact initial market/data providers.
6. Supported exchanges/markets.
7. Exact signal thresholds.
8. Benchmark selection.
9. Corporate-action handling details.
10. Dividend and withholding-tax semantics.
11. Authentication/deployment design.
12. Exact report delivery times.
13. Target allocation semantics, if enabled.

## Sprint 0 accepted decisions

### ADR-008 — PostgreSQL is the authoritative structured store

Status: Accepted

### ADR-009 — Initial scope is US/NSE/BSE listed equities only

Status: Accepted

### ADR-010 — Security identity and listing identity are separate

Status: Accepted

Tickers are time-bound listing attributes, not canonical identities.

### ADR-011 — FIFO is used for internal investment P&L

Status: Accepted

The application is not a tax engine.

### ADR-012 — Cash, fees, taxes, dividends, and FX are explicit

Status: Accepted

Cash is part of portfolio value. Buy costs enter lot cost basis, sell costs reduce proceeds, and dividends retain gross/tax/net values.

### ADR-013 — Opening positions are accounting boundaries

Status: Accepted

They create opening lots with explicit unknown acquisition dates when needed and do not create historical BUY transactions.

### ADR-014 — Raw and adjusted prices have distinct semantics

Status: Accepted

### ADR-015 — Imports require explicit reconciliation confirmation

Status: Accepted

### ADR-016 — Jobs are idempotent and freshness-aware

Status: Accepted

## Deferred decisions

- Initial provider stack pending empirical US/NSE/BSE tests and licence review.
- Portfolio TWR/XIRR methodology.
- Benchmarks and target allocations.
- Economic treatment rules for bonus issues, rights issues, mergers, and spin-offs.
