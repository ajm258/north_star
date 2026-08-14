from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_intelligence.domain.enums import TransactionType
from portfolio_intelligence.services.accounting import (
    AccountingError,
    LedgerEvent,
    OpenLot,
    allocate_fifo_sale,
    apply_split,
    reconstruct_ledger,
)

D = Decimal
T0 = datetime(2025, 1, 1, tzinfo=UTC)


def test_fifo_partial_sale_includes_buy_fees_and_sell_costs() -> None:
    lots = [
        OpenLot("first", "EXM", D("100"), D("10.05"), "USD", T0),
        OpenLot("second", "EXM", D("50"), D("12.06"), "USD", datetime(2025, 1, 2, tzinfo=UTC)),
    ]

    result = allocate_fifo_sale(lots, D("120"), D("1800"), D("6"))

    assert [allocation.quantity for allocation in result.allocations] == [D("100"), D("20")]
    assert [allocation.allocated_cost for allocation in result.allocations] == [D("1005"), D("241.20")]
    assert result.net_proceeds == D("1794")
    assert result.realised_pnl == D("547.80")
    assert lots[0].remaining_quantity == D("0")
    assert lots[1].remaining_quantity == D("30")


def test_complete_sell_consumes_all_open_lots() -> None:
    lot = OpenLot("only", "EXM", D("10"), D("5"), "USD", T0)

    result = allocate_fifo_sale([lot], D("10"), D("70"))

    assert result.realised_pnl == D("20")
    assert lot.remaining_quantity == D("0")


def test_insufficient_quantity_is_rejected() -> None:
    lot = OpenLot("only", "EXM", D("10"), D("5"), "USD", T0)

    with pytest.raises(AccountingError, match="Insufficient quantity"):
        allocate_fifo_sale([lot], D("11"), D("70"))


def test_dividend_withholding_deposit_and_withdrawal_remain_separate() -> None:
    state = reconstruct_ledger(
        [
            LedgerEvent(TransactionType.DEPOSIT, T0, "USD", gross_amount=D("10000"), event_id="deposit"),
            LedgerEvent(
                TransactionType.BUY,
                datetime(2025, 1, 2, tzinfo=UTC),
                "USD",
                listing_key="EXM",
                quantity=D("100"),
                gross_amount=D("1000"),
                fees=D("5"),
                event_id="buy",
            ),
            LedgerEvent(
                TransactionType.DIVIDEND,
                datetime(2025, 1, 3, tzinfo=UTC),
                "USD",
                listing_key="EXM",
                gross_amount=D("30"),
                tax=D("4.5"),
                event_id="dividend",
            ),
            LedgerEvent(
                TransactionType.WITHDRAWAL,
                datetime(2025, 1, 4, tzinfo=UTC),
                "USD",
                gross_amount=D("100"),
                event_id="withdrawal",
            ),
        ],
        datetime(2025, 1, 4, 23, tzinfo=UTC),
    )

    assert state.cash_by_currency["USD"] == D("8920.5")
    assert state.dividends_by_currency["USD"] == D("30")
    assert state.taxes_by_currency["USD"] == D("4.5")
    assert state.lots[0].unit_cost == D("10.05")


def test_stock_split_is_cost_neutral() -> None:
    lot = OpenLot("split", "EXM", D("10"), D("100"), "USD", T0)

    apply_split([lot], D("2"), D("1"))

    assert lot.remaining_quantity == D("20")
    assert lot.unit_cost == D("50")


def test_same_day_effective_sequence_is_deterministic() -> None:
    state = reconstruct_ledger(
        [
            LedgerEvent(
                TransactionType.BUY,
                T0,
                "USD",
                listing_key="EXM",
                quantity=D("1"),
                gross_amount=D("10"),
                effective_sequence=2,
                event_id="later-row",
            ),
            LedgerEvent(
                TransactionType.BUY,
                T0,
                "USD",
                listing_key="EXM",
                quantity=D("1"),
                gross_amount=D("5"),
                effective_sequence=1,
                event_id="first-row",
            ),
            LedgerEvent(
                TransactionType.SELL,
                datetime(2025, 1, 2, tzinfo=UTC),
                "USD",
                listing_key="EXM",
                quantity=D("1"),
                gross_amount=D("12"),
                event_id="sell",
            ),
        ],
        datetime(2025, 1, 2, 23, tzinfo=UTC),
    )

    assert state.realised_pnl_by_currency["USD"] == D("7")
