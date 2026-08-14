# Architecture

## 1. Initial architecture

Use a modular monolith.

Do not split the application into many services until there is a demonstrated operational reason.

Recommended conceptual layers:

1. API/UI
2. Portfolio/accounting domain
3. Data collectors/providers
4. Deterministic analytics
5. Signal engine
6. LLM analysis
7. Reporting/notifications
8. Persistence

## 2. High-level flow

```text
Portfolio CSV / manual transactions
        ↓
Import + validation + reconciliation
        ↓
Transaction ledger
        ↓
Derived holdings + lots + historical snapshots

External data providers
        ↓
Normalisation + validation + caching
        ↓
Historical market/fundamental/event data
        ↓
Deterministic analytics
        ↓
Signal detection
        ↓
Context gathering
        ↓
LLM interpretation
        ↓
Daily / weekly / monthly reports
        ↓
Human decision
```

## 3. Source of truth

Transactions are the source of truth for portfolio accounting when available.

Holdings are derived state.

Historical snapshots are persisted for efficient reporting and auditability, but must not replace the underlying transaction history.

## 4. Provider abstraction

Use interfaces/protocols such as:
- MarketDataProvider
- FundamentalsProvider
- NewsProvider
- FilingsProvider
- EarningsProvider
- MacroProvider

Providers should return canonical internal models.

Provider-specific response formats must not leak into business logic.

## 5. LLM boundary

The deterministic engine creates a structured analysis context.

The LLM receives that context plus relevant source material.

The LLM returns a structured schema.

Example:

```json
{
  "summary": "...",
  "primary_driver": "...",
  "direction": "positive|negative|mixed|neutral",
  "company_specific": true,
  "thesis_impact": "strengthening|stable|monitor|potential_deterioration",
  "portfolio_relevance": "low|medium|high",
  "facts": [],
  "interpretation": [],
  "uncertainties": [],
  "items_to_watch": []
}
```

The application must validate this output before using it in reports.

## 6. Historical data

Important data should be timestamped and source-attributed.

Never overwrite historical observations just because a newer observation exists.

Where provider restatements are expected, preserve appropriate source/update metadata.

## 7. Security

The application contains sensitive financial information.

Initial deployment should use authenticated HTTPS access. Do not expose unauthenticated portfolio endpoints.

Secrets belong in environment/configuration secret storage, never source control.

## 8. Configuration

Thresholds and provider configuration should be externalised.

Examples:
- daily movement threshold
- weekly movement threshold
- persistence window
- relative-volume threshold
- report schedule
- benchmark
- portfolio currency
- notification configuration

Avoid embedding investor-specific thresholds throughout the codebase.
