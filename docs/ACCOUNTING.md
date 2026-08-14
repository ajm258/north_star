# Accounting Model

## Scope and boundary

Portfolio Intelligence performs deterministic investment-performance accounting. It uses FIFO internally and is not a tax engine, tax adviser, or jurisdiction-specific tax calculator.

Transactions are the accounting source of truth. Derived lots, cash entries, holdings, and snapshots can be rebuilt from posted events and must never silently replace the ledger.

## Immutable ledger

Posted financial values are immutable. A correction creates a linked `REVERSAL` or future `AMENDMENT` event. The initial reversal workflow is intentionally conservative: it allows only the latest posted transaction in its account and rejects corporate-action or dependency-unsafe reversals.

Supported initial transaction types are `BUY`, `SELL`, `DIVIDEND`, `DEPOSIT`, `WITHDRAWAL`, `FEE`, `TAX`, `STOCK_SPLIT`, `BONUS_ISSUE`, and `SECURITY_IDENTIFIER_CHANGE`.

## FIFO lots and realised P&L

A `BUY` creates one lot. Its native-currency unit cost is:

```text
(gross purchase amount + applicable buy fees + applicable buy taxes) / quantity
```

A `SELL` consumes available lots ordered by `fifo_sort_at`, then immutable lot allocations record consumed quantity, allocated cost, allocated net proceeds, and realised P&L.

```text
net sale proceeds = gross sale amount - sell fees - sell taxes
realised P&L = allocated net proceeds - FIFO allocated cost
```

## Cash, dividends, and P&L components

Cash is tracked per account and currency. Deposits and withdrawals change portfolio value but are external capital flows, not investment return.

Dividends retain gross amount, withholding/tax, net cash, currency, and source metadata, including declaration/ex/payment dates where supplied. In the current transaction schema the three dates are preserved in source metadata; a later reporting sprint may promote them to dedicated fields.

```text
net dividend cash = gross dividend - withholding/tax - any dividend fees
net total investment P&L = realised P&L + unrealised P&L
                          + gross dividends - recorded fees - recorded taxes
```

Raw prices are used for valuation. Adjusted prices are analytical series only and must never be combined with separately booked dividends or processed splits to calculate accounting return.

## Opening positions

A current-holdings CSV is an opening-position boundary record, not a historical `BUY`. It creates an `opening_positions` record and an explicitly `acquisition_date_unknown` opening lot. Earlier realised P&L cannot be reconstructed from it. To avoid overwriting history, an opening-position import can only be confirmed into an account with no ledger or prior opening-position records.

## Corporate actions

Corporate actions are explicit events. Stock splits/reverse splits transform open lot quantities and unit costs without creating P&L. Bonus issues, identifier changes, rights issues, mergers, and spin-offs have explicit models; their economic transformation rules beyond stock splits are deferred until an approved accounting rule exists.
