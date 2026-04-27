import asyncio
import logging
import random
import time
import uuid
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import ExternalFetchRun

logger = logging.getLogger(__name__)

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def should_retry_status(status_code: int) -> bool:
    return status_code in RETRY_STATUS_CODES


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    correlation_id: str,
) -> dict[str, Any]:
    settings = get_settings()
    last_error: str | None = None
    for attempt in range(1, settings.retry_max_attempts + 1):
        started = time.perf_counter()
        try:
            response = await client.get(url, headers={"X-Correlation-ID": correlation_id})
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "httpx_attempt",
                extra={
                    "event": "httpx_attempt",
                    "correlation_id": correlation_id,
                    "url": url,
                    "attempt": attempt,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            if should_retry_status(response.status_code) and attempt < settings.retry_max_attempts:
                await asyncio.sleep(
                    settings.retry_backoff_factor * (2 ** (attempt - 1))
                    + random.uniform(0, settings.retry_jitter_seconds)
                )
                continue
            payload = response.json() if response.content else None
            return {
                "url": url,
                "status": "success" if response.is_success else "failed",
                "status_code": response.status_code,
                "attempts": attempt,
                "payload": payload if response.is_success else None,
                "error": None if response.is_success else response.text[:500],
            }
        except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError) as exc:
            last_error = str(exc)
            logger.warning(
                "httpx_attempt_failed",
                extra={
                    "event": "httpx_attempt_failed",
                    "correlation_id": correlation_id,
                    "url": url,
                    "attempt": attempt,
                    "error": last_error,
                },
            )
            if attempt < settings.retry_max_attempts:
                await asyncio.sleep(
                    settings.retry_backoff_factor * (2 ** (attempt - 1))
                    + random.uniform(0, settings.retry_jitter_seconds)
                )
    return {
        "url": url,
        "status": "failed",
        "status_code": None,
        "attempts": settings.retry_max_attempts,
        "payload": None,
        "error": last_error or "Request failed",
    }


async def aggregate_urls(
    db: AsyncSession, client: httpx.AsyncClient, urls: list[str], requested_by_user_id: str
) -> ExternalFetchRun:
    started = time.perf_counter()
    correlation_id = str(uuid.uuid4())
    results = await asyncio.gather(
        *(fetch_with_retry(client, url, correlation_id) for url in urls)
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    if all(result["status"] == "success" for result in results):
        status = "completed"
    elif any(result["status"] == "success" for result in results):
        status = "partial_failure"
    else:
        status = "failed"
    run = ExternalFetchRun(
        correlation_id=correlation_id,
        requested_by_user_id=requested_by_user_id,
        status=status,
        urls_json=urls,
        results_json=results,
        duration_ms=duration_ms,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    logger.info(
        "external_fetch_run_completed",
        extra={
            "event": "external_fetch_run_completed",
            "run_id": run.id,
            "correlation_id": correlation_id,
            "duration_ms": duration_ms,
            "status": status,
        },
    )
    return run


async def list_fetch_runs(db: AsyncSession, user_id: str, page: int, page_size: int):
    base = select(ExternalFetchRun).where(ExternalFetchRun.requested_by_user_id == user_id)
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    runs = await db.scalars(
        base.order_by(ExternalFetchRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(runs), int(total or 0)
