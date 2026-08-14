# Portfolio Intelligence

A long-term portfolio intelligence and early-warning system.

## Purpose

Portfolio Intelligence continuously monitors an investment portfolio, its holdings, and the surrounding market/business environment. It identifies meaningful positive and negative changes early and presents concise, evidence-based context so the investor can make informed portfolio decisions.

The system is **decision support**, not an automated trading system.

It does not attempt to predict short-term prices or issue binary Buy/Sell instructions.

## Core principle

> Observe → Detect change → Understand cause → Assess significance → Surface early → Human decides.

## Reporting horizons

- **Daily:** What happened today that I should know about?
- **Weekly:** What has been developing and why?
- **Monthly:** How is the portfolio and each investment evolving?
- **Ad hoc:** Surface genuinely significant events immediately.

## Major pillars

1. Portfolio lifecycle and accounting
2. Portfolio health and performance
3. Investment-thesis monitoring
4. Early-warning and opportunity detection
5. Market/sector/macro context
6. Portfolio management intelligence
7. Concise daily/weekly/monthly communication

## Development philosophy

Deterministic calculations and data processing come first. The LLM is used for interpretation, explanation, synthesis, and contextual analysis—not arithmetic or authoritative investment decisions.

See `AGENTS.md` for repository instructions and `docs/` for the detailed specification.

## Development foundation

The initial implementation uses Python, FastAPI, PostgreSQL, Alembic, Docker Compose, and fixed-precision decimal accounting. Copy `.env.example` to `.env`, set a non-default `ADMIN_PASSWORD`, then run `docker compose up --build` in a Docker-enabled development environment. Run `pytest` and `ruff check .` before changes are accepted.
