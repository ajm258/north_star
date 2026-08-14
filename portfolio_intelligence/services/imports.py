from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from portfolio_intelligence.domain.enums import (
    CorporateActionType,
    ImportRowStatus,
    ImportStatus,
    ImportType,
    TransactionStatus,
    TransactionType,
)
from portfolio_intelligence.domain.models import (
    CashLedgerEntry,
    CorporateAction,
    Import,
    ImportRow,
    Lot,
    LotAllocation,
    OpeningCashBalance,
    OpeningPosition,
    SecurityListing,
    Transaction,
)
from portfolio_intelligence.services.accounting import AccountingError, OpenLot, allocate_fifo_sale

ZERO = Decimal("0")


class ImportWorkflowError(ValueError):
    """Raised when a staged import cannot safely progress."""


class DuplicateImportError(ImportWorkflowError):
    """Raised when an account has already received the exact same file."""


HEADER_ALIASES = {
    "transaction_at": ("date", "transaction_date", "trade_date", "trade date"),
    "as_of_date": ("as_of_date", "as of date", "snapshot_date", "snapshot date"),
    "action": ("action", "transaction_type", "type"),
    "ticker": ("ticker", "symbol", "security"),
    "exchange": ("exchange", "market"),
    "quantity": ("quantity", "shares", "units"),
    "unit_price": ("price", "unit_price", "trade_price"),
    "gross_amount": ("gross_amount", "gross amount", "amount", "value"),
    "cost_basis": ("cost_basis", "cost basis", "total_cost", "total cost"),
    "currency": ("currency", "ccy"),
    "fees": ("fees", "fee", "commission", "brokerage"),
    "tax": ("tax", "withholding", "withholding_tax", "withholding tax"),
    "asset_type": ("asset_type", "asset type"),
    "ratio_numerator": ("ratio_numerator", "split_numerator", "split numerator"),
    "ratio_denominator": ("ratio_denominator", "split_denominator", "split denominator"),
    "declaration_date": ("declaration_date", "declaration date"),
    "ex_date": ("ex_date", "ex date"),
    "payment_date": ("payment_date", "payment date"),
    "external_reference": ("external_reference", "reference", "transaction_id"),
}


def _canonical_headers(headers: list[str]) -> dict[str, str]:
    normalised = {header.strip().lower(): header for header in headers if header}
    result: dict[str, str] = {}
    for canonical, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalised:
                result[canonical] = normalised[alias]
                break
    return result


def _value(row: dict[str, str], mapping: dict[str, str], field: str) -> str | None:
    header = mapping.get(field)
    value = row.get(header) if header else None
    return value.strip() or None if value else None


def _decimal(value: str | None, field: str, errors: list[str], required: bool = False) -> Decimal | None:
    if value is None:
        if required:
            errors.append(f"{field} is required.")
        return None
    try:
        parsed = Decimal(value.replace(",", ""))
    except InvalidOperation:
        errors.append(f"{field} must be a decimal value.")
        return None
    if parsed < ZERO:
        errors.append(f"{field} cannot be negative.")
    return parsed


def _date(value: str | None, field: str, errors: list[str], required: bool = False) -> date | None:
    if value is None:
        if required:
            errors.append(f"{field} is required.")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} must be an ISO date (YYYY-MM-DD).")
        return None


def _as_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def detect_import_type(headers: list[str]) -> ImportType:
    mapping = _canonical_headers(headers)
    if "action" in mapping:
        return ImportType.TRANSACTIONS
    if "cost_basis" in mapping and "quantity" in mapping:
        return ImportType.OPENING_POSITIONS
    raise ImportWorkflowError(
        "Unable to detect import type. Supply an action column for transactions or quantity and "
        "cost_basis for opening positions."
    )


def _normalise_transaction(row: dict[str, str], mapping: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    action_text = _value(row, mapping, "action")
    try:
        action = TransactionType(action_text.upper()) if action_text else None
    except ValueError:
        action = None
        errors.append(f"Unsupported action: {action_text!r}.")
    event_date = _date(_value(row, mapping, "transaction_at"), "date", errors, required=True)
    currency = _value(row, mapping, "currency")
    if currency is None or len(currency) != 3:
        errors.append("currency must be a three-letter ISO currency code.")
    if currency:
        currency = currency.upper()
    quantity = _decimal(_value(row, mapping, "quantity"), "quantity", errors)
    unit_price = _decimal(_value(row, mapping, "unit_price"), "price", errors)
    gross_amount = _decimal(_value(row, mapping, "gross_amount"), "gross_amount", errors) or ZERO
    fees = _decimal(_value(row, mapping, "fees"), "fees", errors) or ZERO
    tax = _decimal(_value(row, mapping, "tax"), "tax", errors) or ZERO
    ticker = _value(row, mapping, "ticker")
    exchange = _value(row, mapping, "exchange")

    security_actions = {
        TransactionType.BUY,
        TransactionType.SELL,
        TransactionType.DIVIDEND,
        TransactionType.STOCK_SPLIT,
        TransactionType.BONUS_ISSUE,
        TransactionType.SECURITY_IDENTIFIER_CHANGE,
    }
    if action in security_actions and not ticker:
        errors.append("ticker is required for this action.")
    if action in {TransactionType.BUY, TransactionType.SELL}:
        if quantity is None or quantity <= ZERO:
            errors.append("quantity must be greater than zero for a BUY or SELL.")
        if unit_price is None or unit_price < ZERO:
            errors.append("price is required for a BUY or SELL.")
        if quantity is not None and unit_price is not None and _value(row, mapping, "gross_amount") is None:
            gross_amount = quantity * unit_price
    if action in {
        TransactionType.DIVIDEND,
        TransactionType.DEPOSIT,
        TransactionType.WITHDRAWAL,
        TransactionType.FEE,
        TransactionType.TAX,
    }:
        if gross_amount <= ZERO:
            errors.append("gross_amount/amount must be greater than zero for this action.")
    numerator = _decimal(_value(row, mapping, "ratio_numerator"), "ratio_numerator", errors)
    denominator = _decimal(_value(row, mapping, "ratio_denominator"), "ratio_denominator", errors)
    if action == TransactionType.STOCK_SPLIT and (not numerator or not denominator):
        errors.append("STOCK_SPLIT requires ratio_numerator and ratio_denominator.")

    return (
        {
            "action": action.value if action else None,
            "transaction_at": event_date.isoformat() if event_date else None,
            "ticker": ticker.upper() if ticker else None,
            "exchange": exchange.upper() if exchange else None,
            "quantity": str(quantity) if quantity is not None else None,
            "unit_price": str(unit_price) if unit_price is not None else None,
            "gross_amount": str(gross_amount),
            "fees": str(fees),
            "tax": str(tax),
            "currency": currency,
            "ratio_numerator": str(numerator) if numerator is not None else None,
            "ratio_denominator": str(denominator) if denominator is not None else None,
            "external_reference": _value(row, mapping, "external_reference"),
            "declaration_date": _value(row, mapping, "declaration_date"),
            "ex_date": _value(row, mapping, "ex_date"),
            "payment_date": _value(row, mapping, "payment_date"),
        },
        errors,
    )


def _normalise_opening_position(
    row: dict[str, str], mapping: dict[str, str], default_as_of_date: date | None
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    asset_type = (_value(row, mapping, "asset_type") or "LISTED_EQUITY").upper()
    as_of = _date(_value(row, mapping, "as_of_date"), "as_of_date", errors) or default_as_of_date
    if as_of is None:
        errors.append("as_of_date is required for opening positions.")
    currency = _value(row, mapping, "currency")
    if currency is None or len(currency) != 3:
        errors.append("currency must be a three-letter ISO currency code.")
    if currency:
        currency = currency.upper()
    ticker = _value(row, mapping, "ticker")
    exchange = _value(row, mapping, "exchange")
    quantity = _decimal(_value(row, mapping, "quantity"), "quantity", errors)
    cost_basis = _decimal(_value(row, mapping, "cost_basis"), "cost_basis", errors)
    gross_amount = _decimal(_value(row, mapping, "gross_amount"), "gross_amount", errors)
    if asset_type == "CASH":
        amount = gross_amount if gross_amount is not None else cost_basis
        if amount is None or amount < ZERO:
            errors.append("cash opening rows require gross_amount/amount or cost_basis.")
    else:
        if not ticker:
            errors.append("ticker is required for an opening equity position.")
        if quantity is None or quantity <= ZERO:
            errors.append("quantity must be greater than zero for an opening equity position.")
        if cost_basis is None or cost_basis < ZERO:
            errors.append("cost_basis is required for an opening equity position.")
    return (
        {
            "asset_type": asset_type,
            "as_of_date": as_of.isoformat() if as_of else None,
            "ticker": ticker.upper() if ticker else None,
            "exchange": exchange.upper() if exchange else None,
            "quantity": str(quantity) if quantity is not None else None,
            "cost_basis": str(cost_basis) if cost_basis is not None else None,
            "gross_amount": str(gross_amount) if gross_amount is not None else None,
            "currency": currency,
        },
        errors,
    )


def _requires_listing(data: dict[str, Any], import_type: ImportType) -> bool:
    if import_type == ImportType.OPENING_POSITIONS:
        return data.get("asset_type") != "CASH"
    return data.get("action") in {
        TransactionType.BUY.value,
        TransactionType.SELL.value,
        TransactionType.DIVIDEND.value,
        TransactionType.STOCK_SPLIT.value,
        TransactionType.BONUS_ISSUE.value,
        TransactionType.SECURITY_IDENTIFIER_CHANGE.value,
    }


def _match_listing(
    session: Session, ticker: str | None, exchange: str | None
) -> tuple[str | None, ImportRowStatus, list[str]]:
    if not ticker:
        return None, ImportRowStatus.UNRESOLVED_SECURITY, ["ticker is required for a security match."]
    statement = select(SecurityListing).where(SecurityListing.ticker == ticker)
    if exchange:
        statement = statement.where(SecurityListing.exchange == exchange)
    matches = list(session.scalars(statement))
    if len(matches) == 1:
        return matches[0].id, ImportRowStatus.VALID, []
    if len(matches) > 1:
        return None, ImportRowStatus.AMBIGUOUS_SECURITY, [
            "Ticker matches multiple active listings; choose an exchange."
        ]
    return None, ImportRowStatus.UNRESOLVED_SECURITY, ["No matching security listing was found."]


@dataclass(frozen=True)
class StagedImport:
    import_id: str
    status: ImportStatus
    reconciliation: dict[str, Any]


class ImportService:
    def stage_csv(
        self,
        session: Session,
        *,
        account_id: str,
        filename: str,
        content: bytes,
        import_type: ImportType | None = None,
        mapping_override: dict[str, str] | None = None,
        default_as_of_date: date | None = None,
    ) -> StagedImport:
        if not content:
            raise ImportWorkflowError("The uploaded file is empty.")
        content_hash = hashlib.sha256(content).hexdigest()
        duplicate = session.scalar(
            select(Import).where(
                Import.account_id == account_id,
                Import.content_hash == content_hash,
                Import.status.in_([ImportStatus.READY_FOR_CONFIRMATION, ImportStatus.CONFIRMED]),
            )
        )
        if duplicate:
            raise DuplicateImportError(f"This exact file is already recorded as import {duplicate.id}.")
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ImportWorkflowError("CSV must be UTF-8 encoded.") from error
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ImportWorkflowError("CSV must include a header row.")
        mapping = _canonical_headers(reader.fieldnames)
        if mapping_override:
            mapping.update(mapping_override)
        resolved_type = import_type or detect_import_type(reader.fieldnames)
        import_record = Import(
            account_id=account_id,
            import_type=resolved_type,
            status=ImportStatus.STAGED,
            filename=filename,
            content_hash=content_hash,
            mapping_version="generic-v1",
        )
        session.add(import_record)
        session.flush()

        for row_number, raw_row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in raw_row.values()):
                continue
            if resolved_type == ImportType.TRANSACTIONS:
                normalized, errors = _normalise_transaction(raw_row, mapping)
            else:
                normalized, errors = _normalise_opening_position(raw_row, mapping, default_as_of_date)
            listing_id: str | None = None
            status = ImportRowStatus.VALID if not errors else ImportRowStatus.REJECTED
            if not errors and _requires_listing(normalized, resolved_type):
                listing_id, status, matching_errors = _match_listing(
                    session, normalized.get("ticker"), normalized.get("exchange")
                )
                errors.extend(matching_errors)
            row = ImportRow(
                import_id=import_record.id,
                row_number=row_number,
                raw_data=raw_row,
                normalized_data=normalized,
                status=status,
                validation_errors=errors,
                security_listing_id=listing_id,
            )
            session.add(row)

        session.flush()
        rows = list(session.scalars(select(ImportRow).where(ImportRow.import_id == import_record.id)))
        import_record.row_count = len(rows)
        import_record.accepted_count = sum(row.status == ImportRowStatus.VALID for row in rows)
        import_record.rejected_count = len(rows) - import_record.accepted_count
        import_record.reconciliation_summary = self._build_reconciliation(session, account_id, resolved_type, rows)
        import_record.status = (
            ImportStatus.READY_FOR_CONFIRMATION
            if import_record.rejected_count == 0
            else ImportStatus.VALIDATION_FAILED
        )
        session.commit()
        return StagedImport(import_record.id, import_record.status, import_record.reconciliation_summary)

    def resolve_listing(self, session: Session, import_row_id: str, listing_id: str) -> StagedImport:
        row = session.get(ImportRow, import_row_id)
        listing = session.get(SecurityListing, listing_id)
        if row is None or listing is None:
            raise ImportWorkflowError("Import row or selected listing was not found.")
        import_record = session.get(Import, row.import_id)
        if import_record is None or import_record.status == ImportStatus.CONFIRMED:
            raise ImportWorkflowError("This import can no longer be changed.")
        ticker = row.normalized_data.get("ticker")
        if ticker != listing.ticker:
            raise ImportWorkflowError("Selected listing does not match the row ticker.")
        row.security_listing_id = listing.id
        row.status = ImportRowStatus.VALID
        row.validation_errors = []
        rows = list(session.scalars(select(ImportRow).where(ImportRow.import_id == import_record.id)))
        import_record.accepted_count = sum(item.status == ImportRowStatus.VALID for item in rows)
        import_record.rejected_count = len(rows) - import_record.accepted_count
        import_record.reconciliation_summary = self._build_reconciliation(
            session, import_record.account_id, import_record.import_type, rows
        )
        import_record.status = (
            ImportStatus.READY_FOR_CONFIRMATION
            if import_record.rejected_count == 0
            else ImportStatus.VALIDATION_FAILED
        )
        session.commit()
        return StagedImport(import_record.id, import_record.status, import_record.reconciliation_summary)

    def confirm(self, session: Session, import_id: str) -> Import:
        import_record = session.get(Import, import_id)
        if import_record is None:
            raise ImportWorkflowError("Import not found.")
        if import_record.status != ImportStatus.READY_FOR_CONFIRMATION:
            raise ImportWorkflowError("Only fully validated imports can be confirmed.")
        rows = list(
            session.scalars(
                select(ImportRow).where(ImportRow.import_id == import_id).order_by(ImportRow.row_number)
            )
        )
        if import_record.import_type == ImportType.OPENING_POSITIONS:
            existing_events = session.scalar(
                select(func.count()).select_from(Transaction).where(Transaction.account_id == import_record.account_id)
            )
            existing_opening = session.scalar(
                select(func.count())
                .select_from(OpeningPosition)
                .where(OpeningPosition.account_id == import_record.account_id)
            )
            if existing_events or existing_opening:
                raise ImportWorkflowError(
                    "Opening-position imports are only allowed for an account without existing ledger history. "
                    "Use a reversal/amendment workflow instead of replacing history."
                )
            for row in rows:
                self._post_opening_row(session, import_record, row)
        else:
            posting = LedgerPostingService()
            for row in rows:
                posting.post_row(session, import_record, row)
        for row in rows:
            row.status = ImportRowStatus.CONFIRMED
        import_record.status = ImportStatus.CONFIRMED
        import_record.confirmed_at = datetime.now(UTC)
        session.commit()
        return import_record

    def _post_opening_row(self, session: Session, import_record: Import, row: ImportRow) -> None:
        data = row.normalized_data
        as_of = date.fromisoformat(data["as_of_date"])
        currency = data["currency"]
        if data["asset_type"] == "CASH":
            amount = Decimal(data.get("gross_amount") or data.get("cost_basis") or "0")
            opening_cash = OpeningCashBalance(
                account_id=import_record.account_id,
                import_id=import_record.id,
                as_of_date=as_of,
                currency=currency,
                amount=amount,
            )
            session.add(opening_cash)
            session.flush()
            session.add(
                CashLedgerEntry(
                    account_id=import_record.account_id,
                    opening_cash_balance_id=opening_cash.id,
                    effective_at=_as_datetime(as_of),
                    currency=currency,
                    amount=amount,
                    entry_type="OPENING_CASH",
                )
            )
            return
        quantity = Decimal(data["quantity"])
        cost_basis = Decimal(data["cost_basis"])
        opening = OpeningPosition(
            account_id=import_record.account_id,
            import_id=import_record.id,
            listing_id=row.security_listing_id,
            as_of_date=as_of,
            quantity=quantity,
            total_cost_basis=cost_basis,
            currency=currency,
            acquisition_date_unknown=True,
        )
        session.add(opening)
        session.flush()
        session.add(
            Lot(
                account_id=import_record.account_id,
                listing_id=row.security_listing_id,
                opening_position_id=opening.id,
                acquisition_date=None,
                acquisition_date_unknown=True,
                fifo_sort_at=_as_datetime(as_of),
                original_quantity=quantity,
                remaining_quantity=quantity,
                unit_cost=cost_basis / quantity,
                currency=currency,
            )
        )

    def _build_reconciliation(
        self, session: Session, account_id: str, import_type: ImportType, rows: list[ImportRow]
    ) -> dict[str, Any]:
        existing = {
            listing_id: quantity
            for listing_id, quantity in session.execute(
                select(Lot.listing_id, func.coalesce(func.sum(Lot.remaining_quantity), ZERO)).where(
                    Lot.account_id == account_id
                ).group_by(Lot.listing_id)
            )
        }
        changes: list[dict[str, str]] = []
        warnings: list[str] = []
        if import_type == ImportType.OPENING_POSITIONS and existing:
            warnings.append(
                "This account already has ledger-derived holdings. An opening-position snapshot cannot replace them."
            )
        quantities: dict[str, Decimal] = {}
        for row in rows:
            if row.status != ImportRowStatus.VALID or row.security_listing_id is None:
                continue
            data = row.normalized_data
            if import_type == ImportType.OPENING_POSITIONS:
                quantities[row.security_listing_id] = Decimal(data["quantity"])
            elif data["action"] == TransactionType.BUY.value:
                quantities[row.security_listing_id] = quantities.get(row.security_listing_id, ZERO) + Decimal(
                    data["quantity"]
                )
            elif data["action"] == TransactionType.SELL.value:
                quantities[row.security_listing_id] = quantities.get(row.security_listing_id, ZERO) - Decimal(
                    data["quantity"]
                )
        for listing_id, imported_quantity in quantities.items():
            before = Decimal(existing.get(listing_id, ZERO))
            after = imported_quantity if import_type == ImportType.OPENING_POSITIONS else before + imported_quantity
            if before == ZERO and after > ZERO:
                kind = "new"
            elif after > before:
                kind = "increased"
            elif after < before and after > ZERO:
                kind = "reduced"
            elif before > ZERO and after == ZERO:
                kind = "removed"
            else:
                kind = "unchanged"
            changes.append({"listing_id": listing_id, "before": str(before), "after": str(after), "change": kind})
        return {"holdings": changes, "cash_changes": [], "warnings": warnings}


class LedgerPostingService:
    """Persist validated rows using FIFO lot allocations and explicit cash postings."""

    def post_row(self, session: Session, import_record: Import, row: ImportRow) -> Transaction:
        data = row.normalized_data
        transaction_type = TransactionType(data["action"])
        transaction = Transaction(
            account_id=import_record.account_id,
            listing_id=row.security_listing_id,
            import_id=import_record.id,
            transaction_type=transaction_type,
            transaction_at=_as_datetime(date.fromisoformat(data["transaction_at"])),
            effective_sequence=self._next_effective_sequence(
                session,
                import_record.account_id,
                _as_datetime(date.fromisoformat(data["transaction_at"])),
            ),
            quantity=Decimal(data["quantity"]) if data.get("quantity") else None,
            unit_price=Decimal(data["unit_price"]) if data.get("unit_price") else None,
            gross_amount=Decimal(data["gross_amount"]),
            fees=Decimal(data["fees"]),
            tax=Decimal(data["tax"]),
            currency=data["currency"],
            external_reference=data.get("external_reference"),
            source="CSV_IMPORT",
            source_metadata={
                key: data.get(key) for key in ("declaration_date", "ex_date", "payment_date") if data.get(key)
            },
        )
        session.add(transaction)
        session.flush()
        if transaction_type == TransactionType.BUY:
            self._post_buy(session, transaction)
        elif transaction_type == TransactionType.SELL:
            self._post_sell(session, transaction)
        elif transaction_type == TransactionType.STOCK_SPLIT:
            self._post_split(session, transaction, data)
        else:
            self._post_cash_only(session, transaction)
        return transaction

    def _post_buy(self, session: Session, transaction: Transaction) -> None:
        assert transaction.quantity is not None and transaction.listing_id is not None
        total_cost = transaction.gross_amount + transaction.fees + transaction.tax
        session.add(
            Lot(
                account_id=transaction.account_id,
                listing_id=transaction.listing_id,
                originating_transaction_id=transaction.id,
                acquisition_date=transaction.transaction_at.date(),
                fifo_sort_at=transaction.transaction_at,
                fifo_sequence=transaction.effective_sequence,
                original_quantity=transaction.quantity,
                remaining_quantity=transaction.quantity,
                unit_cost=total_cost / transaction.quantity,
                currency=transaction.currency,
            )
        )
        self._cash(session, transaction, -total_cost, "BUY")

    def _post_sell(self, session: Session, transaction: Transaction) -> None:
        assert transaction.quantity is not None and transaction.listing_id is not None
        lots = list(
            session.scalars(
                select(Lot)
                .where(
                    Lot.account_id == transaction.account_id,
                    Lot.listing_id == transaction.listing_id,
                    Lot.remaining_quantity > ZERO,
                )
                .order_by(Lot.fifo_sort_at, Lot.id)
                .with_for_update()
            )
        )
        open_lots = [
            OpenLot(
                id=lot.id,
                listing_key=lot.listing_id,
                remaining_quantity=lot.remaining_quantity,
                unit_cost=lot.unit_cost,
                currency=lot.currency,
                fifo_sort_at=lot.fifo_sort_at,
                fifo_sequence=lot.fifo_sequence,
                acquisition_date_unknown=lot.acquisition_date_unknown,
            )
            for lot in lots
        ]
        try:
            result = allocate_fifo_sale(
                open_lots, transaction.quantity, transaction.gross_amount, transaction.fees, transaction.tax
            )
        except AccountingError as error:
            raise ImportWorkflowError(str(error)) from error
        lots_by_id = {lot.id: lot for lot in lots}
        for open_lot in open_lots:
            lots_by_id[open_lot.id].remaining_quantity = open_lot.remaining_quantity
        for allocation in result.allocations:
            session.add(
                LotAllocation(
                    sale_transaction_id=transaction.id,
                    lot_id=allocation.lot_id,
                    quantity=allocation.quantity,
                    allocated_cost=allocation.allocated_cost,
                    allocated_proceeds=allocation.allocated_proceeds,
                    realised_pnl=allocation.realised_pnl,
                    currency=transaction.currency,
                )
            )
        self._cash(session, transaction, result.net_proceeds, "SELL")

    def _post_cash_only(self, session: Session, transaction: Transaction) -> None:
        if transaction.transaction_type == TransactionType.DIVIDEND:
            self._cash(session, transaction, transaction.gross_amount - transaction.tax - transaction.fees, "DIVIDEND")
        elif transaction.transaction_type == TransactionType.DEPOSIT:
            self._cash(session, transaction, transaction.gross_amount, "DEPOSIT")
        elif transaction.transaction_type in {TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TAX}:
            self._cash(session, transaction, -transaction.gross_amount, transaction.transaction_type.value)
        elif transaction.transaction_type in {
            TransactionType.BONUS_ISSUE,
            TransactionType.SECURITY_IDENTIFIER_CHANGE,
        }:
            action_type = CorporateActionType(transaction.transaction_type.value)
            session.add(
                CorporateAction(
                    account_id=transaction.account_id,
                    listing_id=transaction.listing_id,
                    transaction_id=transaction.id,
                    action_type=action_type,
                    effective_at=transaction.transaction_at,
                    source=transaction.source,
                    terms=transaction.source_metadata,
                )
            )

    def _post_split(self, session: Session, transaction: Transaction, data: dict[str, Any]) -> None:
        assert transaction.listing_id is not None
        numerator = Decimal(data["ratio_numerator"])
        denominator = Decimal(data["ratio_denominator"])
        multiplier = numerator / denominator
        lots = list(
            session.scalars(
                select(Lot).where(
                    Lot.account_id == transaction.account_id,
                    Lot.listing_id == transaction.listing_id,
                    Lot.remaining_quantity > ZERO,
                )
            )
        )
        for lot in lots:
            lot.remaining_quantity *= multiplier
            lot.original_quantity *= multiplier
            lot.unit_cost /= multiplier
        session.add(
            CorporateAction(
                account_id=transaction.account_id,
                listing_id=transaction.listing_id,
                transaction_id=transaction.id,
                action_type=CorporateActionType.STOCK_SPLIT,
                effective_at=transaction.transaction_at,
                ratio_numerator=numerator,
                ratio_denominator=denominator,
                source=transaction.source,
            )
        )

    def _cash(self, session: Session, transaction: Transaction, amount: Decimal, entry_type: str) -> None:
        session.add(
            CashLedgerEntry(
                account_id=transaction.account_id,
                transaction_id=transaction.id,
                effective_at=transaction.transaction_at,
                currency=transaction.currency,
                amount=amount,
                entry_type=entry_type,
            )
        )

    def _next_effective_sequence(self, session: Session, account_id: str, transaction_at: datetime) -> int:
        last_sequence = session.scalar(
            select(func.max(Transaction.effective_sequence)).where(
                Transaction.account_id == account_id,
                Transaction.transaction_at == transaction_at,
            )
        )
        return int(last_sequence or 0) + 1


class CorrectionService:
    """Safe first correction path: linked reversal of the latest posting in its scope."""

    def reverse_latest_transaction(self, session: Session, transaction_id: str) -> Transaction:
        original = session.get(Transaction, transaction_id)
        if original is None or original.status != TransactionStatus.POSTED:
            raise ImportWorkflowError("Only posted transactions can be reversed.")
        later = session.scalar(
            select(func.count()).select_from(Transaction).where(
                Transaction.account_id == original.account_id,
                Transaction.transaction_at > original.transaction_at,
                Transaction.status == TransactionStatus.POSTED,
            )
        )
        if later:
            raise ImportWorkflowError(
                "Only the latest posted transaction in an account can be reversed in the initial workflow. "
                "Use an amendment after dependent history is supported."
            )
        cash = session.scalar(select(CashLedgerEntry).where(CashLedgerEntry.transaction_id == original.id))
        reversal_at = datetime.now(UTC)
        reversal = Transaction(
            account_id=original.account_id,
            listing_id=original.listing_id,
            import_id=original.import_id,
            transaction_type=TransactionType.REVERSAL,
            transaction_at=reversal_at,
            effective_sequence=self._next_effective_sequence(session, original.account_id, reversal_at),
            gross_amount=original.gross_amount,
            fees=original.fees,
            tax=original.tax,
            currency=original.currency,
            source="LEDGER_CORRECTION",
            source_metadata={"reversal_of": original.id},
            correction_of_transaction_id=original.id,
        )
        session.add(reversal)
        session.flush()
        if original.transaction_type == TransactionType.BUY:
            lot = session.scalar(select(Lot).where(Lot.originating_transaction_id == original.id))
            if lot is None or lot.remaining_quantity != lot.original_quantity:
                raise ImportWorkflowError("A BUY with consumed lots cannot be reversed directly.")
            lot.remaining_quantity = ZERO
        elif original.transaction_type == TransactionType.SELL:
            allocations = session.scalars(
                select(LotAllocation).where(LotAllocation.sale_transaction_id == original.id)
            )
            for allocation in allocations:
                lot = session.get(Lot, allocation.lot_id)
                assert lot is not None
                lot.remaining_quantity += allocation.quantity
        elif original.transaction_type in {
            TransactionType.STOCK_SPLIT,
            TransactionType.BONUS_ISSUE,
            TransactionType.SECURITY_IDENTIFIER_CHANGE,
        }:
            raise ImportWorkflowError(
                "Corporate-action reversal is not implemented in the initial correction workflow."
            )
        if cash:
            session.add(
                CashLedgerEntry(
                    account_id=original.account_id,
                    transaction_id=reversal.id,
                    effective_at=reversal.transaction_at,
                    currency=original.currency,
                    amount=-cash.amount,
                    entry_type="REVERSAL",
                )
            )
        original.status = TransactionStatus.REVERSED
        session.commit()
        return reversal

    def _next_effective_sequence(self, session: Session, account_id: str, transaction_at: datetime) -> int:
        last_sequence = session.scalar(
            select(func.max(Transaction.effective_sequence)).where(
                Transaction.account_id == account_id,
                Transaction.transaction_at == transaction_at,
            )
        )
        return int(last_sequence or 0) + 1
