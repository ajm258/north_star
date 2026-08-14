from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from portfolio_intelligence.core.security import require_authenticated
from portfolio_intelligence.db.session import get_db
from portfolio_intelligence.main import app


def test_authenticated_api_creates_portfolio_and_stages_mobile_import(
    session: Session, account, listing
) -> None:
    def override_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_authenticated] = lambda: "test-user"
    try:
        with TestClient(app) as client:
            health = client.get("/health")
            ui = client.get("/api/v1/imports/ui")
            portfolio = client.post(
                "/api/v1/portfolios",
                json={"name": "API portfolio", "base_currency": "EUR", "report_timezone": "Europe/London"},
            )
            staged = client.post(
                f"/api/v1/accounts/{account.id}/imports",
                files={
                    "file": (
                        "transactions.csv",
                        b"date,action,ticker,exchange,quantity,price,currency,fees,tax,gross_amount\n"
                        b"2025-01-01,BUY,EXM,NASDAQ,1,10,USD,0,0,\n",
                        "text/csv",
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert health.status_code == 200
    assert ui.status_code == 200
    assert "Validate and preview" in ui.text
    assert portfolio.status_code == 201
    assert staged.status_code == 201
    assert staged.json()["status"] == "READY_FOR_CONFIRMATION"
