# CSV Import Design

## Workflow

```text
Upload -> identify/select type -> parse -> validate -> match listing
       -> reconcile -> explicit confirmation -> immutable posting
```

The responsive `/api/v1/imports/ui` surface is authenticated and supports phone-sized screens. It stages a CSV and displays the API preview; confirmation remains a separate explicit API action.

## Import types

### Transaction history

Required fields vary by action. Standard headers include `date`, `action`, `ticker`, `exchange`, `quantity`, `price`, `currency`, `fees`, `tax`, and `gross_amount`. `STOCK_SPLIT` additionally requires `ratio_numerator` and `ratio_denominator`.

Transaction rows are validated before any ledger posting. A `SELL` must have sufficient FIFO lots when the import is confirmed.

Date-only rows receive a UTC start-of-day effective timestamp. When source timestamps are absent, CSV row order is persisted as an effective sequence and is the deterministic same-day ordering rule. Future broker mappings may supply full timestamps instead.

### Opening positions

Opening-position rows require `as_of_date`, `ticker`, `quantity`, `cost_basis`, and `currency`; `exchange` is strongly recommended. They create explicit opening records/lots and never fake historical purchases. An optional `asset_type=CASH` row establishes an opening cash balance.

## Matching and reconciliation

Ticker alone is not canonical. A row is matched to one listing only when its ticker/exchange combination is unique. Ambiguous or unknown matches keep the import unconfirmable until a user selects an existing listing. The preview reports new, increased, reduced, removed, unchanged, cash changes, rejected rows, and warnings.

The generic mapping is versioned as `generic-v1`; `broker_mappings` stores future broker-specific header mappings. File hashes prevent accidental duplicate imports to the same account.

## Safety rules

- No staged import is posted automatically.
- Opening imports cannot replace an existing ledger-derived account.
- Confirmed rows and imports are retained for audit.
- Reversal is a linked ledger event, not a destructive edit.
