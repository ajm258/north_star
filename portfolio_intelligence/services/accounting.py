from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from decimal import Decimal

from portfolio_intelligence.domain.enums import TransactionType

ZERO = Decimal("0")


class AccountingError(ValueError):
    """Raised when an immutable ledger event cannot be applied safely."""


@dataclass
class OpenLot:
    id: str
    listing_key: str
    remaining_quantity: Decimal
    unit_cost: Decimal
    currency: str
    fifo_sort_at: datetime
    fifo_sequence: int = 0
    acquisition_date_unknown: bool = False


@dataclass(frozen=True)
class SaleAllocation:
    lot_id: str
    quantity: Decimal
    allocated_cost: Decimal
    allocated_proceeds: Decimal
    realised_pnl: Decimal


@dataclass(frozen=True)
class FifoSaleResult:
    allocations: tuple[SaleAllocation, ...]
    net_proceeds: Decimal
    realised_pnl: Decimal


def allocate_fifo_sale(
    lots: Iterable[OpenLot],
    quantity: Decimal,
    gross_proceeds: Decimal,
    fees: Decimal = ZERO,
    taxes: Decimal = ZERO,
) -> FifoSaleResult:
    """Consume open lots in FIFO order and allocate sell proceeds exactly once."""

    if quantity <= ZERO:
        raise AccountingError("Sale quantity must be greater than zero.")
    if gross_proceeds < ZERO or fees < ZERO or taxes < ZERO:
        raise AccountingError("Proceeds, fees, and taxes must be non-negative.")

    ordered = sorted(lots, key=lambda lot: (lot.fifo_sort_at, lot.fifo_sequence, lot.id))
    available = sum((lot.remaining_quantity for lot in ordered), ZERO)
    if available < quantity:
        raise AccountingError(f"Insufficient quantity for sale: requested {quantity}, available {available}.")

    remaining_to_allocate = quantity
    remaining_proceeds = gross_proceeds - fees - taxes
    allocations: list[SaleAllocation] = []

    for lot in ordered:
        if remaining_to_allocate == ZERO:
            break
        if lot.remaining_quantity == ZERO:
            continue
        consumed = min(lot.remaining_quantity, remaining_to_allocate)
        is_last = consumed == remaining_to_allocate
        proceeds = remaining_proceeds if is_last else (gross_proceeds - fees - taxes) * consumed / quantity
        allocated_cost = lot.unit_cost * consumed
        lot.remaining_quantity -= consumed
        remaining_to_allocate -= consumed
        remaining_proceeds -= proceeds
        allocations.append(
            SaleAllocation(
                lot_id=lot.id,
                quantity=consumed,
                allocated_cost=allocated_cost,
                allocated_proceeds=proceeds,
                realised_pnl=proceeds - allocated_cost,
            )
        )

    realised_pnl = sum((allocation.realised_pnl for allocation in allocations), ZERO)
    return FifoSaleResult(tuple(allocations), gross_proceeds - fees - taxes, realised_pnl)


def apply_split(lots: Iterable[OpenLot], numerator: Decimal, denominator: Decimal) -> None:
    """Apply a cost-neutral split or reverse split to all open lots for one listing."""

    if numerator <= ZERO or denominator <= ZERO:
        raise AccountingError("Corporate-action ratio components must be greater than zero.")
    multiplier = numerator / denominator
    for lot in lots:
        lot.remaining_quantity *= multiplier
        lot.unit_cost /= multiplier


@dataclass(frozen=True)
class LedgerEvent:
    transaction_type: TransactionType
    effective_at: datetime
    currency: str
    listing_key: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    gross_amount: Decimal = ZERO
    fees: Decimal = ZERO
    tax: Decimal = ZERO
    ratio_numerator: Decimal | None = None
    ratio_denominator: Decimal | None = None
    effective_sequence: int = 0
    event_id: str = ""


@dataclass
class HistoricalState:
    lots: list[OpenLot] = field(default_factory=list)
    cash_by_currency: dict[str, Decimal] = field(default_factory=dict)
    realised_pnl_by_currency: dict[str, Decimal] = field(default_factory=dict)
    dividends_by_currency: dict[str, Decimal] = field(default_factory=dict)
    fees_by_currency: dict[str, Decimal] = field(default_factory=dict)
    taxes_by_currency: dict[str, Decimal] = field(default_factory=dict)

    def add_cash(self, currency: str, amount: Decimal) -> None:
        self.cash_by_currency[currency] = self.cash_by_currency.get(currency, ZERO) + amount

    def add_metric(self, metric: dict[str, Decimal], currency: str, amount: Decimal) -> None:
        metric[currency] = metric.get(currency, ZERO) + amount


def start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def reconstruct_ledger(events: Iterable[LedgerEvent], as_of: datetime) -> HistoricalState:
    """Rebuild quantities, cash, realised P&L, and income from active ledger events."""

    state = HistoricalState()
    ordered_events = sorted(
        (event for event in events if event.effective_at <= as_of),
        key=lambda event: (event.effective_at, event.effective_sequence, event.event_id),
    )
    for event in ordered_events:
        _apply_event(state, event)
    return state


def _apply_event(state: HistoricalState, event: LedgerEvent) -> None:
    if event.transaction_type == TransactionType.BUY:
        _require_security_trade(event)
        quantity = event.quantity or ZERO
        cost = event.gross_amount + event.fees + event.tax
        state.lots.append(
            OpenLot(
                id=event.event_id,
                listing_key=event.listing_key or "",
                remaining_quantity=quantity,
                unit_cost=cost / quantity,
                currency=event.currency,
                fifo_sort_at=event.effective_at,
                fifo_sequence=event.effective_sequence,
            )
        )
        state.add_cash(event.currency, -cost)
        state.add_metric(state.fees_by_currency, event.currency, event.fees)
        state.add_metric(state.taxes_by_currency, event.currency, event.tax)
    elif event.transaction_type == TransactionType.SELL:
        _require_security_trade(event)
        result = allocate_fifo_sale(
            (lot for lot in state.lots if lot.listing_key == event.listing_key),
            event.quantity or ZERO,
            event.gross_amount,
            event.fees,
            event.tax,
        )
        state.add_cash(event.currency, result.net_proceeds)
        state.add_metric(state.realised_pnl_by_currency, event.currency, result.realised_pnl)
        state.add_metric(state.fees_by_currency, event.currency, event.fees)
        state.add_metric(state.taxes_by_currency, event.currency, event.tax)
    elif event.transaction_type == TransactionType.DIVIDEND:
        net_amount = event.gross_amount - event.tax - event.fees
        state.add_cash(event.currency, net_amount)
        state.add_metric(state.dividends_by_currency, event.currency, event.gross_amount)
        state.add_metric(state.fees_by_currency, event.currency, event.fees)
        state.add_metric(state.taxes_by_currency, event.currency, event.tax)
    elif event.transaction_type == TransactionType.DEPOSIT:
        state.add_cash(event.currency, event.gross_amount)
    elif event.transaction_type == TransactionType.WITHDRAWAL:
        state.add_cash(event.currency, -event.gross_amount)
    elif event.transaction_type in {TransactionType.FEE, TransactionType.TAX}:
        state.add_cash(event.currency, -event.gross_amount)
        target = state.fees_by_currency if event.transaction_type == TransactionType.FEE else state.taxes_by_currency
        state.add_metric(target, event.currency, event.gross_amount)
    elif event.transaction_type == TransactionType.STOCK_SPLIT:
        if event.listing_key is None or event.ratio_numerator is None or event.ratio_denominator is None:
            raise AccountingError("Split events require a listing and a ratio.")
        apply_split(
            (lot for lot in state.lots if lot.listing_key == event.listing_key),
            event.ratio_numerator,
            event.ratio_denominator,
        )


def _require_security_trade(event: LedgerEvent) -> None:
    if event.listing_key is None or event.quantity is None or event.quantity <= ZERO:
        raise AccountingError("Security trades require a listing and positive quantity.")
    if event.gross_amount < ZERO:
        raise AccountingError("Security-trade gross amounts must be non-negative.")
