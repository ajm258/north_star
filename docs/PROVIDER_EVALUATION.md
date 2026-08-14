# Provider Evaluation

Provider selection is deliberately open. No market-data, FX, event, or filing collector is implemented in Sprint 0 or Sprint 1.

## Required acceptance exercise

Before selecting a production provider, test representative US/NSE/BSE listings, including a dual-listed Indian company, for:

- security identity and exchange/MIC resolution;
- five years of raw daily OHLCV;
- adjusted analytical series clearly distinct from raw prices;
- dividends, splits, and identifier changes;
- USD/EUR, USD/INR, and EUR/INR historical FX;
- freshness, missing data, rate limits, retry behaviour, licensing, and internal-display rights.

Candidate adapters are `MarketDataProvider`, `FundamentalsProvider`, `CorporateActionsProvider`, `NewsProvider`, `FilingsProvider`, `EarningsProvider`, `FXProvider`, and `MacroProvider`.

The interfaces and canonical data classes are defined in `portfolio_intelligence/providers/protocols.py`. They contain no external HTTP implementation or provider-specific response model.

Twelve Data, Alpha Vantage, SEC EDGAR, licensed NSE/BSE data, ECB/FBIL FX, and other appropriately licensed providers remain evaluation candidates. Exchange websites must not be scraped where their terms prohibit automated collection. Provider responses must be normalised into internal observations and retain source and retrieved timestamps.
