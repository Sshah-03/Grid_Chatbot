from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class AggregateRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=10)


class FetchResult(BaseModel):
    url: str
    status: str
    status_code: int | None = None
    attempts: int
    payload: Any = None
    error: str | None = None


class AggregateResponse(BaseModel):
    run_id: str
    correlation_id: str
    status: str
    duration_ms: int
    results: list[FetchResult]


class FetchRunListItem(BaseModel):
    id: str
    correlation_id: str
    status: str
    duration_ms: int
    created_at: datetime


class FetchRunListResponse(BaseModel):
    items: list[FetchRunListItem]
    page: int
    page_size: int
    total: int


class FetchRunDetail(BaseModel):
    id: str
    correlation_id: str
    requested_by_user_id: str
    status: str
    urls: list[str]
    results: list[FetchResult]
    duration_ms: int
    created_at: datetime
    updated_at: datetime
