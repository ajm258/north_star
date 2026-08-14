# API Boundary

All portfolio and import endpoints require the initial single-user HTTP Basic authentication dependency. Deployment must terminate HTTPS before the API is exposed. Health is intentionally public and contains no financial data.

## Current endpoints

- `GET /health`
- `POST /api/v1/portfolios`
- `POST /api/v1/portfolios/{portfolio_id}/accounts`
- `GET /api/v1/portfolios/{portfolio_id}/accounts`
- `POST /api/v1/accounts/{account_id}/imports`
- `GET /api/v1/imports/{import_id}`
- `GET /api/v1/imports/{import_id}/reconciliation`
- `POST /api/v1/imports/{import_id}/rows/{row_id}/resolve-listing`
- `POST /api/v1/imports/{import_id}/confirm`
- `POST /api/v1/transactions/{transaction_id}/reverse`
- `GET /api/v1/imports/ui`

Provider payloads are never API contracts. Future portfolio-state, reports, and signal endpoints must return deterministic internal results plus provenance/freshness metadata.
