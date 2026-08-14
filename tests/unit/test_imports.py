from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_intelligence.domain.enums import ImportRowStatus, ImportStatus, TransactionStatus
from portfolio_intelligence.domain.models import (
    CashLedgerEntry,
    ImportRow,
    Lot,
    LotAllocation,
    OpeningPosition,
    Security,
    SecurityListing,
    Transaction,
)
from portfolio_intelligence.services.imports import CorrectionService, DuplicateImportError, ImportService


def _transactions_csv(rows: str) -> bytes:
    return (
        "date,action,ticker,exchange,quantity,price,currency,fees,tax,gross_amount,"
        "ratio_numerator,ratio_denominator\n"
        + rows
    ).encode()


def test_transaction_import_posts_fifo_lots_and_cash(
    session: Session, account, listing: SecurityListing
) -> None:
    service = ImportService()
    staged = service.stage_csv(
        session,
        account_id=account.id,
        filename="transactions.csv",
        content=_transactions_csv(
            "2025-01-01,BUY,EXM,NASDAQ,100,10,USD,5,0,\n"
            "2025-01-02,BUY,EXM,NASDAQ,50,12,USD,3,0,\n"
            "2025-01-03,SELL,EXM,NASDAQ,120,15,USD,6,0,\n"
        ),
    )

    assert staged.status == ImportStatus.READY_FOR_CONFIRMATION
    service.confirm(session, staged.import_id)

    lots = list(session.scalars(select(Lot).order_by(Lot.fifo_sort_at)))
    allocations = list(session.scalars(select(LotAllocation).order_by(LotAllocation.id)))
    cash = sum(session.scalars(select(CashLedgerEntry.amount)), Decimal("0"))
    assert [lot.remaining_quantity for lot in lots] == [Decimal("0"), Decimal("30")]
    assert sum((allocation.realised_pnl for allocation in allocations), Decimal("0")) == Decimal("547.8")
    assert cash == Decimal("186")


def test_opening_positions_create_opening_lots_not_historical_buys(
    session: Session, account, listing: SecurityListing
) -> None:
    csv_content = (
        b"as_of_date,ticker,exchange,quantity,cost_basis,currency\n"
        b"2025-01-01,EXM,NASDAQ,10,125,USD\n"
    )
    service = ImportService()
    staged = service.stage_csv(
        session, account_id=account.id, filename="opening.csv", content=csv_content
    )

    service.confirm(session, staged.import_id)

    opening = session.scalar(select(OpeningPosition))
    lot = session.scalar(select(Lot))
    assert opening is not None
    assert lot is not None
    assert lot.originating_transaction_id is None
    assert lot.opening_position_id == opening.id
    assert lot.acquisition_date_unknown is True
    assert session.scalar(select(Transaction)) is None


def test_duplicate_file_is_rejected(session: Session, account, listing: SecurityListing) -> None:
    content = _transactions_csv("2025-01-01,BUY,EXM,NASDAQ,1,10,USD,0,0,\n")
    service = ImportService()
    service.stage_csv(session, account_id=account.id, filename="one.csv", content=content)

    with pytest.raises(DuplicateImportError):
        service.stage_csv(session, account_id=account.id, filename="two.csv", content=content)


def test_ambiguous_listing_requires_explicit_resolution(session: Session, account, listing: SecurityListing) -> None:
    second_security = Security(legal_name="Example India", isin="IN0000000001")
    session.add(second_security)
    session.flush()
    session.add(
        SecurityListing(
            security_id=second_security.id,
            ticker="EXM",
            exchange="NSE",
            mic="XNSE",
            currency="INR",
        )
    )
    session.commit()
    service = ImportService()
    staged = service.stage_csv(
        session,
        account_id=account.id,
        filename="ambiguous.csv",
        content=_transactions_csv("2025-01-01,BUY,EXM,,1,10,USD,0,0,\n"),
    )
    row = session.scalar(select(ImportRow).where(ImportRow.import_id == staged.import_id))
    assert staged.status == ImportStatus.VALIDATION_FAILED
    assert row is not None and row.status == ImportRowStatus.AMBIGUOUS_SECURITY

    resolved = service.resolve_listing(session, row.id, listing.id)

    assert resolved.status == ImportStatus.READY_FOR_CONFIRMATION


def test_latest_cash_transaction_can_be_reversed_without_mutating_financial_values(
    session: Session, account
) -> None:
    service = ImportService()
    staged = service.stage_csv(
        session,
        account_id=account.id,
        filename="deposit.csv",
        content=_transactions_csv("2025-01-01,DEPOSIT,,,0,,USD,0,0,100\n"),
    )
    service.confirm(session, staged.import_id)
    original = session.scalar(select(Transaction).where(Transaction.transaction_type == "DEPOSIT"))
    assert original is not None

    reversal = CorrectionService().reverse_latest_transaction(session, original.id)

    refreshed_original = session.get(Transaction, original.id)
    amounts = list(session.scalars(select(CashLedgerEntry.amount)))
    assert refreshed_original is not None and refreshed_original.status == TransactionStatus.REVERSED
    assert reversal.correction_of_transaction_id == original.id
    assert sum(amounts, Decimal("0")) == Decimal("0")


def test_stock_split_is_explicit_and_updates_open_lots(session: Session, account, listing: SecurityListing) -> None:
    service = ImportService()
    staged = service.stage_csv(
        session,
        account_id=account.id,
        filename="split.csv",
        content=_transactions_csv(
            "2025-01-01,BUY,EXM,NASDAQ,10,100,USD,0,0,\n"
            "2025-01-02,STOCK_SPLIT,EXM,NASDAQ,,,USD,0,0,,2,1\n"
        ),
    )
    assert staged.status == ImportStatus.READY_FOR_CONFIRMATION

    service.confirm(session, staged.import_id)

    lot = session.scalar(select(Lot))
    assert lot is not None
    assert lot.remaining_quantity == Decimal("20")
    assert lot.unit_cost == Decimal("50")
