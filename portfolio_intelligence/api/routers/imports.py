from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from portfolio_intelligence.api.schemas import ResolveListingRequest
from portfolio_intelligence.core.config import Settings, get_settings
from portfolio_intelligence.core.security import require_authenticated
from portfolio_intelligence.db.session import get_db
from portfolio_intelligence.domain.enums import ImportType
from portfolio_intelligence.domain.models import Import, ImportRow, PortfolioAccount
from portfolio_intelligence.services.imports import (
    CorrectionService,
    DuplicateImportError,
    ImportService,
    ImportWorkflowError,
)

router = APIRouter(prefix="/api/v1", tags=["imports"], dependencies=[Depends(require_authenticated)])
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def _payload(import_record: Import, rows: list[ImportRow] | None = None) -> dict:
    data = {
        "id": import_record.id,
        "account_id": import_record.account_id,
        "import_type": import_record.import_type.value,
        "status": import_record.status.value,
        "filename": import_record.filename,
        "row_count": import_record.row_count,
        "accepted_count": import_record.accepted_count,
        "rejected_count": import_record.rejected_count,
        "reconciliation": import_record.reconciliation_summary,
    }
    if rows is not None:
        data["rows"] = [
            {
                "id": row.id,
                "row_number": row.row_number,
                "status": row.status.value,
                "normalized": row.normalized_data,
                "errors": row.validation_errors,
                "security_listing_id": row.security_listing_id,
            }
            for row in rows
        ]
    return data


def _workflow_error(error: Exception) -> HTTPException:
    if isinstance(error, DuplicateImportError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


@router.get("/imports/ui", response_class=HTMLResponse, include_in_schema=False)
def import_ui() -> str:
    """A dependency-free responsive upload surface for the initial authenticated workflow."""

    return IMPORT_UI_HTML


@router.post("/accounts/{account_id}/imports", status_code=status.HTTP_201_CREATED)
async def stage_import(
    account_id: str,
    session: DbSession,
    settings: AppSettings,
    file: UploadFile = File(...),
    import_type: str | None = Form(default=None),
    default_as_of_date: date | None = Form(default=None),
) -> dict:
    if session.get(PortfolioAccount, account_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio account not found.")
    content = await file.read(settings.upload_max_bytes + 1)
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Uploaded CSV is too large.")
    try:
        parsed_type = ImportType(import_type) if import_type else None
        staged = ImportService().stage_csv(
            session,
            account_id=account_id,
            filename=file.filename or "upload.csv",
            content=content,
            import_type=parsed_type,
            default_as_of_date=default_as_of_date,
        )
    except (ImportWorkflowError, ValueError) as error:
        raise _workflow_error(error) from error
    return {
        "id": staged.import_id,
        "status": staged.status.value,
        "reconciliation": staged.reconciliation,
    }


@router.get("/imports/{import_id}")
def get_import(import_id: str, session: DbSession) -> dict:
    import_record = session.get(Import, import_id)
    if import_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found.")
    rows = list(
        session.scalars(select(ImportRow).where(ImportRow.import_id == import_id).order_by(ImportRow.row_number))
    )
    return _payload(import_record, rows)


@router.get("/imports/{import_id}/reconciliation")
def get_reconciliation(import_id: str, session: DbSession) -> dict:
    import_record = session.get(Import, import_id)
    if import_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found.")
    return {"import_id": import_id, "reconciliation": import_record.reconciliation_summary}


@router.post("/imports/{import_id}/rows/{row_id}/resolve-listing")
def resolve_listing(import_id: str, row_id: str, payload: ResolveListingRequest, session: DbSession) -> dict:
    row = session.get(ImportRow, row_id)
    if row is None or row.import_id != import_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import row not found.")
    try:
        staged = ImportService().resolve_listing(session, row_id, payload.listing_id)
    except ImportWorkflowError as error:
        raise _workflow_error(error) from error
    return {"id": staged.import_id, "status": staged.status.value, "reconciliation": staged.reconciliation}


@router.post("/imports/{import_id}/confirm")
def confirm_import(import_id: str, session: DbSession) -> dict:
    try:
        import_record = ImportService().confirm(session, import_id)
    except ImportWorkflowError as error:
        session.rollback()
        raise _workflow_error(error) from error
    return _payload(import_record)


@router.post("/transactions/{transaction_id}/reverse")
def reverse_transaction(transaction_id: str, session: DbSession) -> dict[str, str]:
    try:
        reversal = CorrectionService().reverse_latest_transaction(session, transaction_id)
    except ImportWorkflowError as error:
        session.rollback()
        raise _workflow_error(error) from error
    return {"id": reversal.id, "reversal_of": transaction_id, "status": "POSTED"}


IMPORT_UI_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Portfolio CSV import</title><style>
body { font-family: system-ui, sans-serif; max-width: 42rem; margin: auto; padding: 1rem;
       background: #f6f8fa; color: #1f2328; }
main { background: #fff; padding: 1.25rem; border-radius: .75rem; box-shadow: 0 1px 4px #0002; }
label, input, select, button { display: block; width: 100%; box-sizing: border-box; margin: .5rem 0; }
input, select, button { font: inherit; padding: .7rem; }
button { background: #0969da; color: #fff; border: 0; border-radius: .4rem; font-weight: 600; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f6f8fa; padding: .75rem; }
</style></head><body><main>
<h1>Import portfolio CSV</h1>
<p>Files are staged and validated; nothing is posted until confirmation.</p>
<form id="upload"><label>Portfolio account ID<input name="account_id" required></label>
<label>Import type<select name="import_type"><option value="">Detect automatically</option>
<option value="TRANSACTIONS">Transaction history</option>
<option value="OPENING_POSITIONS">Opening positions</option></select></label>
<label>CSV file<input type="file" name="file" accept=".csv,text/csv" required></label>
<button>Validate and preview</button></form><pre id="result" aria-live="polite"></pre>
<script>
document.querySelector('#upload').addEventListener('submit', async event => {
  event.preventDefault(); const form = new FormData(event.target); const accountId = form.get('account_id');
  form.delete('account_id');
  const endpoint = '/api/v1/accounts/' + encodeURIComponent(accountId) + '/imports';
  const response = await fetch(endpoint, { method: 'POST', body: form });
  document.querySelector('#result').textContent = JSON.stringify(await response.json(), null, 2);
});
</script></main></body></html>"""
