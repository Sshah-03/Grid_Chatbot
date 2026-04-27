import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.models.base import Base


class ExternalFetchRun(Base):
    __tablename__ = "external_fetch_runs"
    __table_args__ = (
        Index("idx_external_fetch_runs_user_created", "requested_by_user_id", "created_at"),
        Index("idx_external_fetch_runs_correlation", "correlation_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    requested_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30))
    urls_json: Mapped[list[str]] = mapped_column(JSON)
    results_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    duration_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
