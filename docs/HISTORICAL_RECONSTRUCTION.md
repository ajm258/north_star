# Historical Reconstruction

The system answers “what did the portfolio look like at date X?” by replaying immutable ledger and opening-boundary records, not by trusting today’s holdings.

For an `as_of` timestamp, the reconstruction engine will:

1. Select accepted opening positions and posted, non-reversed events on or before the cutoff.
2. Sort by effective timestamp, persisted same-day effective sequence, and immutable event identifier.
3. Replay cash, FIFO lots, sales, dividends, and supported corporate actions.
4. Select the latest eligible raw close and FX observation for valuation.
5. Calculate quantities, cash, cost basis, realised P&L, unrealised P&L, total value, and allocation.
6. Record freshness and source versions alongside any persisted snapshot.

If required raw prices or FX rates are stale, a valuation report is blocked rather than silently labelled current. A report timezone is configurable per portfolio; exchange-local market session dates remain part of the market observation.

Snapshots and `holdings` are materialised derived state for efficient reporting. They include calculation/source-version metadata and do not replace the ledger.
