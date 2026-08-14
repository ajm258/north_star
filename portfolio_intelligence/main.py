from __future__ import annotations

from fastapi import FastAPI

from portfolio_intelligence.api.routers import health, imports, portfolio
from portfolio_intelligence.core.config import get_settings
from portfolio_intelligence.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="Portfolio Intelligence", version="0.1.0")
    app.include_router(health.router)
    app.include_router(portfolio.router)
    app.include_router(imports.router)
    return app


app = create_app()
