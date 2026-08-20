import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DeveloperProfile(Base):
    __tablename__ = "developer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Free-form structured data — languages, domains, preferences, goals.
    # Stored as JSON rather than rigid columns because this shape will
    # evolve a lot early on; we don't want a migration for every tweak.
    skills: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_full_name: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )  # e.g. "astral-sh/ruff"

    description: Mapped[str | None] = mapped_column(String, nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    primary_language: Mapped[str | None] = mapped_column(String, nullable=True)

    # The deterministic RepositoryScore breakdown, stored so we can see
    # WHY a repo was ranked the way it was — not just the final number.
    score: Mapped[float] = mapped_column(Float, default=0.0)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    issues: Mapped[list["Issue"]] = relationship(back_populates="repository")


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"), nullable=False)

    github_issue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(String, nullable=True)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)

    score: Mapped[float] = mapped_column(Float, default=0.0)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    repository: Mapped["Repository"] = relationship(back_populates="issues")
