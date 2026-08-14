from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from portfolio_intelligence.db.base import Base
from portfolio_intelligence.domain.models import Portfolio, PortfolioAccount, Security, SecurityListing


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db_session = factory()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def account(session: Session) -> PortfolioAccount:
    portfolio = Portfolio(name="Test portfolio", base_currency="EUR", report_timezone="Europe/London")
    session.add(portfolio)
    session.flush()
    account = PortfolioAccount(
        portfolio_id=portfolio.id,
        name="Test account",
        broker="Test broker",
        base_currency="EUR",
    )
    session.add(account)
    session.commit()
    return account


@pytest.fixture()
def listing(session: Session) -> SecurityListing:
    security = Security(legal_name="Example Incorporated", isin="US0000000001")
    session.add(security)
    session.flush()
    listing = SecurityListing(
        security_id=security.id,
        ticker="EXM",
        exchange="NASDAQ",
        mic="XNAS",
        currency="USD",
    )
    session.add(listing)
    session.commit()
    return listing
