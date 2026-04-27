import uuid

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=True)
    profile_bio: Mapped[str] = mapped_column(String(500), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    sessions = relationship("AuthSession", back_populates="user")
    memberships = relationship("RoomMembership", back_populates="user")
    messages = relationship("Message", back_populates="user")
