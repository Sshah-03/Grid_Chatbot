from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import ExternalFetchRun, User
from app.schemas.integrations import (
    AggregateRequest,
    AggregateResponse,
    FetchRunDetail,
    FetchRunListItem,
    FetchRunListResponse,
)
from app.services.auth_service import get_current_user
from app.services.integration_service import aggregate_urls, list_fetch_runs

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/aggregate-sample", response_model=AggregateResponse)
async def aggregate_sample(
    payload: AggregateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    urls = [str(url) for url in payload.urls]
    run = await aggregate_urls(db, request.app.state.http_client, urls, user.id)
    return AggregateResponse(
        run_id=run.id,
        correlation_id=run.correlation_id,
        status=run.status,
        duration_ms=run.duration_ms,
        results=run.results_json,
    )


@router.get("/fetch-runs", response_model=FetchRunListResponse)
async def fetch_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runs, total = await list_fetch_runs(db, user.id, page, page_size)
    return FetchRunListResponse(
        items=[
            FetchRunListItem(
                id=run.id,
                correlation_id=run.correlation_id,
                status=run.status,
                duration_ms=run.duration_ms,
                created_at=run.created_at,
            )
            for run in runs
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/fetch-runs/{run_id}", response_model=FetchRunDetail)
async def fetch_run_detail(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await db.get(ExternalFetchRun, run_id)
    if not run or run.requested_by_user_id != user.id:
        raise HTTPException(status_code=404, detail="Fetch run not found")
    return FetchRunDetail(
        id=run.id,
        correlation_id=run.correlation_id,
        requested_by_user_id=run.requested_by_user_id,
        status=run.status,
        urls=run.urls_json,
        results=run.results_json,
        duration_ms=run.duration_ms,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )
