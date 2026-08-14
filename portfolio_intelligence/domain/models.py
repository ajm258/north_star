from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from portfolio_intelligence.db.base import Base
from portfolio_intelligence.domain.enums import (
    AssetType,
    CorporateActionType,
    ImportRowStatus,
    ImportStatus,
    ImportType,
    JobStatus,
    TransactionStatus,
    TransactionType,
)

Amount = Numeric(28, 10)
Id = String(36)


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class Portfolio(Timestamped, Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    report_timezone: Mapped[str] = mapped_column(String(64), nullable=False)


class PortfolioAccount(Timestamped, Base):
    __tablename__ = "portfolio_accounts"
    __table_args__ = (UniqueConstraint("portfolio_id", "name", name="uq_account_name_per_portfolio"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    broker: Mapped[str | None] = mapped_column(String(200))
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)


class Security(Timestamped, Base):
    __tablename__ = "securities"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    legal_name: Mapped[str] = mapped_column(String(500), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12), unique=True)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, native_enum=False), default=AssetType.LISTED_EQUITY, nullable=False
    )
    active_from: Mapped[date | None] = mapped_column(Date)
    active_to: Mapped[date | None] = mapped_column(Date)


class SecurityListing(Timestamped, Base):
    __tablename__ = "security_listings"
    __table_args__ = (
        UniqueConstraint("ticker", "exchange", "active_from", name="uq_listing_ticker_exchange_active"),
        Index("ix_listing_ticker_exchange", "ticker", "exchange"),
    )

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    security_id: Mapped[str] = mapped_column(ForeignKey("securities.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(64), nullable=False)
    exchange: Mapped[str] = mapped_column(String(64), nullable=False)
    mic: Mapped[str | None] = mapped_column(String(4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    active_from: Mapped[date | None] = mapped_column(Date)
    active_to: Mapped[date | None] = mapped_column(Date)


class Import(Timestamped, Base):
    __tablename__ = "imports"
    __table_args__ = (Index("ix_import_account_content_hash", "account_id", "content_hash"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False, index=True)
    import_type: Mapped[ImportType] = mapped_column(Enum(ImportType, native_enum=False), nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, native_enum=False), default=ImportStatus.STAGED, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_version: Mapped[str | None] = mapped_column(String(100))
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reconciliation_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    corrected_by_import_id: Mapped[str | None] = mapped_column(ForeignKey("imports.id"))


class ImportRow(Timestamped, Base):
    __tablename__ = "import_rows"
    __table_args__ = (UniqueConstraint("import_id", "row_number", name="uq_import_row_number"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    import_id: Mapped[str] = mapped_column(ForeignKey("imports.id"), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    normalized_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[ImportRowStatus] = mapped_column(
        Enum(ImportRowStatus, native_enum=False), nullable=False
    )
    validation_errors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    security_listing_id: Mapped[str | None] = mapped_column(ForeignKey("security_listings.id"))


class BrokerMapping(Timestamped, Base):
    __tablename__ = "broker_mappings"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    broker: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mapping: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("quantity IS NULL OR quantity >= 0", name="ck_transaction_quantity_nonnegative"),
        CheckConstraint("fees >= 0", name="ck_transaction_fees_nonnegative"),
        CheckConstraint("tax >= 0", name="ck_transaction_tax_nonnegative"),
        UniqueConstraint(
            "account_id", "transaction_at", "effective_sequence", name="uq_transaction_effective_order"
        ),
        Index("ix_transaction_account_effective", "account_id", "transaction_at"),
    )

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False, index=True)
    listing_id: Mapped[str | None] = mapped_column(ForeignKey("security_listings.id"))
    import_id: Mapped[str | None] = mapped_column(ForeignKey("imports.id"), index=True)
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False), nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, native_enum=False), default=TransactionStatus.POSTED, nullable=False
    )
    transaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    settlement_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[Decimal | None] = mapped_column(Amount)
    unit_price: Mapped[Decimal | None] = mapped_column(Amount)
    gross_amount: Mapped[Decimal] = mapped_column(Amount, default=Decimal("0"), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Amount, default=Decimal("0"), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Amount, default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate_to_base: Mapped[Decimal | None] = mapped_column(Amount)
    external_reference: Mapped[str | None] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    correction_of_transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class OpeningPosition(Timestamped, Base):
    """An accounting boundary record, intentionally not a historical BUY transaction."""

    __tablename__ = "opening_positions"
    __table_args__ = (UniqueConstraint("import_id", "listing_id", name="uq_opening_position_listing"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False, index=True)
    import_id: Mapped[str] = mapped_column(ForeignKey("imports.id"), nullable=False, index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("security_listings.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    total_cost_basis: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    acquisition_date_unknown: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OpeningCashBalance(Timestamped, Base):
    __tablename__ = "opening_cash_balances"
    __table_args__ = (UniqueConstraint("import_id", "currency", name="uq_opening_cash_currency"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False, index=True)
    import_id: Mapped[str] = mapped_column(ForeignKey("imports.id"), nullable=False, index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Amount, nullable=False)


class Lot(Timestamped, Base):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint("original_quantity >= 0", name="ck_lot_original_quantity_nonnegative"),
        CheckConstraint("remaining_quantity >= 0", name="ck_lot_remaining_quantity_nonnegative"),
        Index("ix_lot_fifo", "account_id", "listing_id", "fifo_sort_at", "fifo_sequence"),
    )

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False, index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("security_listings.id"), nullable=False, index=True)
    originating_transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"))
    opening_position_id: Mapped[str | None] = mapped_column(ForeignKey("opening_positions.id"))
    acquisition_date: Mapped[date | None] = mapped_column(Date)
    acquisition_date_unknown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fifo_sort_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fifo_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    original_quantity: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    unit_cost_base: Mapped[Decimal | None] = mapped_column(Amount)


class LotAllocation(Timestamped, Base):
    __tablename__ = "lot_allocations"
    __table_args__ = (UniqueConstraint("sale_transaction_id", "lot_id", name="uq_sale_lot_allocation"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    sale_transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    allocated_cost: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    allocated_proceeds: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    realised_pnl: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)


class CashLedgerEntry(Timestamped, Base):
    __tablename__ = "cash_ledger"
    __table_args__ = (Index("ix_cash_account_date", "account_id", "effective_at"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False, index=True)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"), unique=True)
    opening_cash_balance_id: Mapped[str | None] = mapped_column(ForeignKey("opening_cash_balances.id"))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(64), nullable=False)


class CorporateAction(Timestamped, Base):
    __tablename__ = "corporate_actions"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False, index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("security_listings.id"), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"), unique=True)
    action_type: Mapped[CorporateActionType] = mapped_column(
        Enum(CorporateActionType, native_enum=False), nullable=False
    )
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ratio_numerator: Mapped[Decimal | None] = mapped_column(Amount)
    ratio_denominator: Mapped[Decimal | None] = mapped_column(Amount)
    successor_listing_id: Mapped[str | None] = mapped_column(ForeignKey("security_listings.id"))
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    terms: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Holding(Timestamped, Base):
    """Materialised derived state; the transaction ledger remains authoritative."""

    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("account_id", "listing_id", name="uq_holding_account_listing"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False, index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("security_listings.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortfolioSnapshot(Timestamped, Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    portfolio_value: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    cash_value: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    realised_pnl: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    unrealised_pnl: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(100), nullable=False)
    source_versions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class HoldingSnapshot(Timestamped, Base):
    __tablename__ = "holding_snapshots"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("portfolio_accounts.id"), nullable=False, index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("security_listings.id"), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    market_value: Mapped[Decimal | None] = mapped_column(Amount)
    cost_basis: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    realised_pnl_to_date: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    unrealised_pnl: Mapped[Decimal | None] = mapped_column(Amount)
    price_observation_id: Mapped[str | None] = mapped_column(ForeignKey("price_history.id"))


class PriceObservation(Timestamped, Base):
    __tablename__ = "price_history"
    __table_args__ = (UniqueConstraint("listing_id", "observed_at", "provider", name="uq_price_observation"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    listing_id: Mapped[str] = mapped_column(ForeignKey("security_listings.id"), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal | None] = mapped_column(Amount)
    high: Mapped[Decimal | None] = mapped_column(Amount)
    low: Mapped[Decimal | None] = mapped_column(Amount)
    close: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Amount)
    volume: Mapped[Decimal | None] = mapped_column(Amount)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class FxObservation(Timestamped, Base):
    __tablename__ = "fx_history"
    __table_args__ = (
        UniqueConstraint("base_currency", "quote_currency", "observed_at", "provider", name="uq_fx_observation"),
    )

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Amount, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class FundamentalObservation(Timestamped, Base):
    __tablename__ = "fundamentals"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    security_id: Mapped[str] = mapped_column(ForeignKey("securities.id"), nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    values: Mapped[dict] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    source_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Event(Timestamped, Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    security_id: Mapped[str | None] = mapped_column(ForeignKey("securities.id"), index=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))


class InvestmentThesis(Timestamped, Base):
    __tablename__ = "investment_theses"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    security_id: Mapped[str] = mapped_column(ForeignKey("securities.id"), nullable=False, index=True)
    thesis_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_claims: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    active_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Signal(Timestamped, Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    portfolio_id: Mapped[str | None] = mapped_column(ForeignKey("portfolios.id"), index=True)
    security_id: Mapped[str | None] = mapped_column(ForeignKey("securities.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_value: Mapped[Decimal | None] = mapped_column(Amount)
    baseline_value: Mapped[Decimal | None] = mapped_column(Amount)
    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)


class LLMAssessment(Timestamped, Base):
    __tablename__ = "llm_assessments"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str] = mapped_column(Id, nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    structured_output: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_references: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)


class Report(Timestamped, Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_versions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class JobRun(Timestamped, Base):
    __tablename__ = "job_runs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_job_idempotency_key"),)

    id: Mapped[str] = mapped_column(Id, primary_key=True, default=new_id)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_id: Mapped[str] = mapped_column(Id, nullable=False)
    logical_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False), default=JobStatus.QUEUED, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    freshness: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[dict | None] = mapped_column(JSON)
