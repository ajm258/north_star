from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.mark.postgres
def test_postgres_migrations_apply_when_database_is_configured() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured for PostgreSQL integration testing.")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        table_names = set(inspect(engine).get_table_names())
        assert {"portfolio_accounts", "security_listings", "transactions", "lots", "imports", "job_runs"} <= table_names
    finally:
        engine.dispose()
