"""Modelos SQLAlchemy para persistencia del módulo kits."""
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.types import TypeDecorator


class _JsonText(TypeDecorator):
    """Tipo JSON portable: usa JSON nativo en MariaDB/MySQL, TEXT en SQLite (tests)."""

    impl = LONGTEXT
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name in ("mysql", "mariadb"):
            return dialect.type_descriptor(LONGTEXT())
        return dialect.type_descriptor(String())

    def process_bind_param(self, value: Any, dialect) -> str | None:
        if value is None:
            return None
        import json

        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: str | None, dialect) -> Any:
        if value is None:
            return None
        import json

        return json.loads(value)


Base = declarative_base()


class RepositoryModel(Base):
    """Modelo SQLAlchemy para la tabla repositories."""

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    ref: Mapped[str] = mapped_column(String(255), nullable=False)
    credential_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True)
    last_commit_sha: Mapped[str | None] = mapped_column(
        String(40), nullable=True)
    sync_error_message: Mapped[str | None] = mapped_column(
        String(2048), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_repositories_user_id", "user_id"),
        Index("ix_repositories_sync_status", "sync_status"),
        Index("ix_repositories_is_deleted", "is_deleted"),
    )


class KitModel(Base):
    """Modelo SQLAlchemy para la tabla kits."""

    __tablename__ = "kits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    path_in_repo: Mapped[str] = mapped_column(String(1024), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(
        String(2048), nullable=False, default="")
    version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="")
    tags: Mapped[Any] = mapped_column(_JsonText, nullable=False)
    values: Mapped[Any] = mapped_column(_JsonText, nullable=False)
    debug_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info")
    upload_files: Mapped[Any] = mapped_column(
        _JsonText, nullable=False, default="[]")
    pipeline_files: Mapped[Any] = mapped_column(
        _JsonText, nullable=False, default="[]")
    backup_files: Mapped[Any] = mapped_column(
        _JsonText, nullable=False, default="[]")
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True)
    last_commit_sha: Mapped[str | None] = mapped_column(
        String(40), nullable=True)
    sync_error_message: Mapped[str | None] = mapped_column(
        String(2048), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_kits_user_id", "user_id"),
        Index("ix_kits_repository_id", "repository_id"),
        Index("ix_kits_sync_status", "sync_status"),
        Index("ix_kits_is_deleted", "is_deleted"),
    )
