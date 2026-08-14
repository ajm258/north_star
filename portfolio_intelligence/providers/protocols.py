from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ProviderSecurity:
    ticker: str
    exchange: str
    mic: str | None
    legal_name: str
    isin: str | None
    currency: str


@dataclass(frozen=True)
class MarketBar:
    observed_at: datetime
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    adjusted_close: Decimal | None
    volume: Decimal | None
    currency: str
    provider: str
    retrieved_at: datetime


@dataclass(frozen=True)
class FxRate:
    base_currency: str
    quote_currency: str
    rate: Decimal
    observed_at: datetime
    provider: str
    retrieved_at: datetime


class MarketDataProvider(Protocol):
    def resolve_security(self, ticker: str, exchange: str) -> ProviderSecurity | None: ...

    def daily_bars(self, security: ProviderSecurity, start: date, end: date) -> list[MarketBar]: ...


class FundamentalsProvider(Protocol):
    def fundamentals(self, security: ProviderSecurity) -> list[dict]: ...


class CorporateActionsProvider(Protocol):
    def corporate_actions(self, security: ProviderSecurity, start: date, end: date) -> list[dict]: ...


class NewsProvider(Protocol):
    def news(self, security: ProviderSecurity, since: datetime) -> list[dict]: ...


class FilingsProvider(Protocol):
    def filings(self, security: ProviderSecurity, since: datetime) -> list[dict]: ...


class EarningsProvider(Protocol):
    def earnings(self, security: ProviderSecurity) -> list[dict]: ...


class FXProvider(Protocol):
    def rates(self, base_currency: str, quote_currency: str, start: date, end: date) -> list[FxRate]: ...


class MacroProvider(Protocol):
    def observations(self, series_id: str, start: date, end: date) -> list[dict]: ...
