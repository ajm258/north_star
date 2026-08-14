from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from portfolio_intelligence.api.schemas import AccountCreate, PortfolioCreate
from portfolio_intelligence.core.security import require_authenticated
from portfolio_intelligence.db.session import get_db
from portfolio_intelligence.domain.models import Portfolio, PortfolioAccount

router = APIRouter(prefix="/api/v1", tags=["portfolios"], dependencies=[Depends(require_authenticated)])
DbSession = Annotated[Session, Depends(get_db)]


def _currency(code: str) -> str:
    currency = code.upper()
    if currency not in {"EUR", "USD", "INR"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Initial supported base currencies are EUR, USD, and INR.",
        )
    return currency


@router.post("/portfolios", status_code=status.HTTP_201_CREATED)
def create_portfolio(payload: PortfolioCreate, session: DbSession) -> dict[str, str]:
    portfolio = Portfolio(
        name=payload.name,
        base_currency=_currency(payload.base_currency),
        report_timezone=payload.report_timezone,
    )
    session.add(portfolio)
    session.commit()
    return {"id": portfolio.id, "name": portfolio.name}


@router.post("/portfolios/{portfolio_id}/accounts", status_code=status.HTTP_201_CREATED)
def create_account(portfolio_id: str, payload: AccountCreate, session: DbSession) -> dict[str, str]:
    if session.get(Portfolio, portfolio_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found.")
    account = PortfolioAccount(
        portfolio_id=portfolio_id,
        name=payload.name,
        broker=payload.broker,
        base_currency=_currency(payload.base_currency),
    )
    session.add(account)
    session.commit()
    return {"id": account.id, "name": account.name}


@router.get("/portfolios/{portfolio_id}/accounts")
def list_accounts(portfolio_id: str, session: DbSession) -> list[dict[str, str | None]]:
    if session.get(Portfolio, portfolio_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found.")
    return [
        {"id": account.id, "name": account.name, "broker": account.broker}
        for account in session.query(PortfolioAccount).filter_by(portfolio_id=portfolio_id).order_by("name")
    ]
