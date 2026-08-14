# Test Strategy

Financial rules use deterministic fixed-precision decimal fixtures. Unit tests cover pure accounting and import validation; database tests cover staging, matching, confirmation, cash entries, lots, allocations, corrections, and job persistence.

Golden scenarios include:

1. Multiple buys and FIFO partial sale with buy/sell fees.
2. Complete sale and insufficient-lot rejection.
3. Dividend gross/withholding/net treatment.
4. Deposit and withdrawal separation from P&L.
5. Opening position without a fake historical buy.
6. Duplicate file rejection and ambiguous listing resolution.
7. Explicit stock split lot transformation.
8. Linked transaction reversal.
9. Idempotent job creation and stale-FX valuation blocking.

`pytest` runs unit tests locally. PostgreSQL migration integration is marked `postgres` and runs when `TEST_DATABASE_URL` points to a disposable PostgreSQL database. CI provisions that database service.
