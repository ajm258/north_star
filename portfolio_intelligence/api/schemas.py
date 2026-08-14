from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    base_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    report_timezone: str = Field(default="Europe/London", min_length=1, max_length=64)


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    broker: str | None = Field(default=None, max_length=200)
    base_currency: str = Field(pattern=r"^[A-Za-z]{3}$")


class ResolveListingRequest(BaseModel):
    listing_id: str


class ImportUploadOptions(BaseModel):
    import_type: str | None = None
    default_as_of_date: date | None = None
