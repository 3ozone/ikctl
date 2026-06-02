"""Modelos SQLAlchemy para persistencia del módulo operations."""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.types import TypeDecorator


class _JsonText(TypeDecorator):
    """Tipo JSON portable: usa LONGTEXT en MariaDB/MySQL, TEXT en SQLite (tests)."""

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


class OperationModel(Base):
    """Modelo SQLAlchemy para la tabla operations."""

    __tablename__ = "operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    server_id: Mapped[str] = mapped_column(String(36), nullable=False)
    kit_id: Mapped[str] = mapped_column(String(36), nullable=False)
    values: Mapped[Any] = mapped_column(_JsonText, nullable=False, default="{}")
    sudo: Mapped[bool] = mapped_column(nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    debug_level: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    output: Mapped[str] = mapped_column(String, nullable=False, default="")
    backup_files: Mapped[Any] = mapped_column(_JsonText, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_operations_user_id", "user_id"),
        Index("ix_operations_server_id", "server_id"),
        Index("ix_operations_kit_id", "kit_id"),
        Index("ix_operations_status", "status"),
    )


class ServerKitFileCacheModel(Base):
    """Modelo SQLAlchemy para la tabla server_kit_file_cache."""

    __tablename__ = "server_kit_file_cache"

    server_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kit_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(500), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_server_kit_file_cache_server_kit", "server_id", "kit_id"),
    )
